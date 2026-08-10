import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, X } from "lucide-react"
import { type FormEvent, type ReactNode, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Identity, StatusMark } from "@/components/workspace-ui"
import {
  OperationConfirmationDialog,
  OperationFollowUp,
  OperationTruthFacts,
} from "@/features/admin/operation-framework-panel"
import {
  cancelOperation,
  executeOperation,
  previewOperation,
  type OperationPreviewEnvelope,
  type OperationPreviewRequest,
  type OperationRecord,
} from "@/lib/admin-operations-api"
import { DashboardApiError } from "@/lib/api"
import type { ProjectProjection } from "@/lib/projects-api"
import type { TaskDetailEnvelope } from "@/lib/task-api"
import type { TrackerDetail, TrackerSummary } from "@/lib/trackers-api"

type PreparedOperation = {
  request: OperationPreviewRequest
  suppliedFacts: Array<[string, string]>
}

type Task = TaskDetailEnvelope["data"]["task"]
type PendingRequest = TaskDetailEnvelope["data"]["pending_requests"][number]
type InputQuestion = Extract<PendingRequest, { family: "user_input" }>["details"]["questions"][number]
type ListedRun = { target_thread_id: string } | undefined
type TrackerBlock = TrackerDetail["blocks"][number]

type ImplementationBinding = {
  kind: "implement-blocks"
  source_fingerprint: string
  project_id: string
  tracker_id: string
  block_start: number
  block_end: number
  mission_root: string
  mission_source_record: string
}

const defaultReviewScope = "Full tracker contract, dependency order, acceptance, negative tests, Stops, source currentness, and implementation readiness."
const missionMarkerPrefix = "SOFTWARE_FACTORY_DASHBOARD_MISSION "
const fingerprintPattern = /^[0-9a-f]{64}$/
const missionSourcePattern = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$/

function implementationBinding(task: Task): ImplementationBinding | null {
  const candidates = [
    ...task.turns.slice().reverse().flatMap((turn) => (
      turn.items.slice().reverse().filter((item) => item.type === "userMessage").map((item) => item.summary)
    )),
    task.preview,
  ]
  for (const candidate of candidates) {
    const firstLine = candidate?.split(/\r?\n/, 1)[0]
    if (!firstLine?.startsWith(missionMarkerPrefix)) continue
    try {
      const value = JSON.parse(firstLine.slice(missionMarkerPrefix.length)) as Record<string, unknown>
      if (
        value.kind === "implement-blocks"
        && typeof value.source_fingerprint === "string"
        && fingerprintPattern.test(value.source_fingerprint)
        && typeof value.project_id === "string"
        && typeof value.tracker_id === "string"
        && fingerprintPattern.test(value.tracker_id)
        && Number.isInteger(value.block_start)
        && Number.isInteger(value.block_end)
        && (value.block_start as number) >= 0
        && (value.block_end as number) >= (value.block_start as number)
        && typeof value.mission_root === "string"
        && fingerprintPattern.test(value.mission_root)
        && typeof value.mission_source_record === "string"
        && missionSourcePattern.test(value.mission_source_record)
      ) return value as ImplementationBinding
    } catch {
      // A malformed marker is unavailable binding evidence, never a UI authority.
    }
  }
  return null
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The operation could not be prepared."
}

function useOperationRunner() {
  const queryClient = useQueryClient()
  const [prepared, setPrepared] = useState<PreparedOperation | null>(null)
  const [preview, setPreview] = useState<OperationPreviewEnvelope | null>(null)
  const [result, setResult] = useState<OperationRecord | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const [staleReason, setStaleReason] = useState<string | null>(null)

  const refreshSources = () => {
    for (const key of [
      ["administrative-operations"],
      ["factory-floor"],
      ["run"],
      ["runs"],
      ["task"],
      ["tasks"],
      ["task-integration"],
      ["trackers"],
    ]) void queryClient.invalidateQueries({ queryKey: key })
  }

  const previewMutation = useMutation({
    mutationFn: previewOperation,
    onSuccess: (value) => {
      setPreview(value)
      setStaleReason(null)
      setLocalError(null)
    },
    onError: (error) => setLocalError(errorMessage(error)),
  })

  const executeMutation = useMutation({
    mutationFn: executeOperation,
    onSuccess: (value) => {
      setResult(value.data.operation)
      setPreview(null)
      setPrepared(null)
      setStaleReason(null)
      setLocalError(null)
      refreshSources()
    },
    onError: (error) => {
      if (error instanceof DashboardApiError && [
        "preview_stale",
        "route_gate_stale",
        "route_gate_denied",
      ].includes(error.code)) {
        setStaleReason(error.message)
      } else {
        setLocalError(errorMessage(error))
      }
    },
  })

  const cancelMutation = useMutation({ mutationFn: cancelOperation })

  const launch = (value: PreparedOperation) => {
    setPrepared(value)
    setPreview(null)
    setResult(null)
    setLocalError(null)
    setStaleReason(null)
    previewMutation.mutate(value.request)
  }

  const close = () => {
    if (preview) cancelMutation.mutate(preview.data.operation.id)
    setPreview(null)
    setPrepared(null)
    setStaleReason(null)
  }

  const previewAgain = () => {
    if (prepared) previewMutation.mutate(prepared.request)
  }

  const confirmation = preview && prepared ? (
    <OperationConfirmationDialog
      preview={preview}
      request={prepared.request}
      suppliedFacts={prepared.suppliedFacts}
      staleReason={staleReason}
      busy={executeMutation.isPending}
      onCancel={close}
      onRefresh={previewAgain}
      onConfirm={(confirmationValue) => executeMutation.mutate({
        ...prepared.request,
        preview_token: preview.data.preview_token,
        confirmation: confirmationValue,
      })}
    />
  ) : null

  const feedback = localError ? (
    <div className="workflow-action-error" role="alert"><AlertTriangle aria-hidden="true" />{localError}</div>
  ) : result ? (
    <div className="workflow-action-result" role="status">
      <StatusMark status={result.state} />
      <span>{result.type}</span>
      <Identity value={result.id} />
      {result.links.map((link) => <a key={link.href} href={link.href}>{link.label}</a>)}
      <OperationTruthFacts operation={result} />
      <OperationFollowUp operation={result} />
    </div>
  ) : previewMutation.isPending ? (
    <span className="workflow-action-pending" role="status">Resolving current sources…</span>
  ) : null

  return { launch, confirmation, feedback, busy: previewMutation.isPending }
}

function InputDialog({
  title,
  submitLabel = "Preview",
  children,
  submitDisabled = false,
  onClose,
  onSubmit,
}: {
  title: string
  submitLabel?: string
  children: ReactNode
  submitDisabled?: boolean
  onClose: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <div className="operation-dialog-backdrop">
      <form className="operation-dialog workflow-input-dialog" role="dialog" aria-modal="true" aria-label={title} onSubmit={onSubmit}>
        <div className="operation-dialog-heading">
          <h2>{title}</h2>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label={`Close ${title}`}><X aria-hidden="true" /></Button>
        </div>
        <div className="workflow-input-fields">{children}</div>
        <div className="operation-dialog-actions">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={submitDisabled}>{submitLabel}</Button>
        </div>
      </form>
    </div>
  )
}

function TextField({
  label,
  value,
  onChange,
  multiline = false,
  required = true,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  multiline?: boolean
  required?: boolean
  placeholder?: string
}) {
  return (
    <label className="workflow-input-field">
      <span>{label}</span>
      {multiline ? (
        <textarea required={required} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input required={required} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
      )}
    </label>
  )
}

function InputQuestionControl({
  question,
  value,
  onChange,
}: {
  question: InputQuestion
  value: string
  onChange: (value: string) => void
}) {
  const options = question.options.flatMap((option) => (
    option.label ? [{ label: option.label, description: option.description }] : []
  ))
  const label = question.question ?? question.header ?? question.id ?? "Question"
  if (options.length === 0) {
    return <TextField label={label} value={value} onChange={onChange} />
  }
  const selected = options.find((option) => option.label === value)
  return (
    <label className="workflow-input-field">
      <span>{label}</span>
      <select required value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select</option>
        {options.map((option) => (
          <option key={option.label} value={option.label}>
            {option.description ? `${option.label} · ${option.description}` : option.label}
          </option>
        ))}
      </select>
      {selected?.description && <small className="workflow-option-description">{selected.description}</small>}
    </label>
  )
}

function approvalFacts(request: PendingRequest | undefined): Array<[string, string]> {
  if (!request || request.family === "user_input") return []
  if (request.family === "command_approval") {
    return [
      ["Command", request.details.command ?? "Unavailable"],
      ["Working directory", request.details.cwd ?? "Unavailable"],
      ["Reason", request.details.reason ?? "Unavailable"],
    ]
  }
  return [
    ["Grant root", request.details.grant_root ?? "Unavailable"],
    ["Reason", request.details.reason ?? "Unavailable"],
  ]
}

function ActionStrip({ children, feedback }: { children: ReactNode; feedback: ReactNode }) {
  return (
    <div className="workflow-action-strip print-hide" aria-label="Available actions">
      <div className="workflow-action-buttons">{children}</div>
      {feedback}
    </div>
  )
}

export function ProjectWorkflowActions({ project }: { project: ProjectProjection }) {
  const runner = useOperationRunner()
  const [open, setOpen] = useState(false)
  const [objective, setObjective] = useState("")
  const [sources, setSources] = useState("")
  const [nonGoals, setNonGoals] = useState("Do not implement any tracker Block")
  const ready = project.discovery.status === "available" && Boolean(project.discovery.git.revision)

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const sourceRows = sources.split("\n").map((value) => value.trim()).filter(Boolean)
    const nonGoalRows = nonGoals.split("\n").map((value) => value.trim()).filter(Boolean)
    if (!project.discovery.git.revision || !objective.trim() || !sourceRows.length || !nonGoalRows.length) return
    runner.launch({
      request: {
        operation_type: "factory.tracker-author",
        target: { kind: "project", id: project.id, project_id: project.id },
        input: {
          repository_head: project.discovery.git.revision,
          objective: objective.trim(),
          sources: sourceRows,
          non_goals: nonGoalRows,
        },
      },
      suppliedFacts: [
        ["Objective", objective.trim()],
        ["Sources", sourceRows.join(" · ")],
        ["Non-goals", nonGoalRows.join(" · ")],
      ],
    })
    setOpen(false)
  }

  return (
    <>
      <ActionStrip feedback={runner.feedback}>
        <Button size="compact" variant="outline" disabled={!ready || runner.busy} onClick={() => setOpen(true)}>Author tracker</Button>
      </ActionStrip>
      {open && (
        <InputDialog title="Author tracker" submitDisabled={!objective.trim() || !sources.trim() || !nonGoals.trim()} onClose={() => setOpen(false)} onSubmit={submit}>
          <TextField label="Objective" value={objective} onChange={setObjective} multiline />
          <TextField label="Source identities · one per line" value={sources} onChange={setSources} multiline placeholder="Repository paths or exact source records" />
          <TextField label="Non-goals · one per line" value={nonGoals} onChange={setNonGoals} multiline />
        </InputDialog>
      )}
      {runner.confirmation}
    </>
  )
}

export function RunCheckAction({
  targetId,
  projectId,
  inline = false,
}: {
  targetId: string
  projectId: string | null
  inline?: boolean
}) {
  const runner = useOperationRunner()
  const launch = () => {
    if (!projectId) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-check-now",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: {},
      },
      suppliedFacts: [
        ["Run target", targetId],
        ["Project", projectId],
        ["Scope", "One mechanical watcher check · no semantic conclusion"],
      ],
    })
  }
  const button = <Button size="compact" variant="outline" disabled={!projectId || runner.busy} onClick={launch}>Check now</Button>
  return inline ? (
    <>
      <div className="workflow-check-inline print-hide">{button}{runner.feedback}</div>
      {runner.confirmation}
    </>
  ) : (
    <>
      <ActionStrip feedback={runner.feedback}>{button}</ActionStrip>
      {runner.confirmation}
    </>
  )
}

export function RunSupervisionActions({
  targetId,
  projectId,
  openIncidentIds,
}: {
  targetId: string
  projectId: string | null
  openIncidentIds: string[]
}) {
  const runner = useOperationRunner()
  const [selectedIncident, setSelectedIncident] = useState("")
  const incidentId = openIncidentIds.includes(selectedIncident)
    ? selectedIncident
    : openIncidentIds[0] ?? ""
  const launch = (
    operationType: string,
    label: string,
    input: Record<string, unknown> = {},
  ) => {
    if (!projectId) return
    runner.launch({
      request: {
        operation_type: operationType,
        target: { kind: "run", id: targetId, project_id: projectId },
        input,
      },
      suppliedFacts: [
        ["Run target", targetId],
        ["Review", label],
        ["Scope", "One exact reviewer task · conclusion remains separate from delivery"],
        ...(incidentId && operationType.endsWith("-issue") ? [["Incident", incidentId] as [string, string]] : []),
      ],
    })
  }
  const unavailable = !projectId || runner.busy
  return (
    <>
      <ActionStrip feedback={runner.feedback}>
        <Button size="compact" variant="outline" disabled={unavailable} onClick={() => launch("factory.supervision-check-now", "Mechanical check")}>Check now</Button>
        <Button size="compact" variant="outline" disabled={unavailable} onClick={() => launch("factory.supervision-review-checkpoint", "Checkpoint review")}>Checkpoint review</Button>
        <Button size="compact" variant="outline" disabled={unavailable} onClick={() => launch("factory.supervision-review-meta", "Meta-review")}>Meta-review</Button>
        {openIncidentIds.length > 0 && (
          <select
            aria-label="Issue for follow-up"
            value={incidentId}
            onChange={(event) => setSelectedIncident(event.target.value)}
            disabled={unavailable}
          >
            {openIncidentIds.map((id) => <option value={id} key={id}>{id}</option>)}
          </select>
        )}
        <Button
          size="compact"
          variant="outline"
          disabled={unavailable || !incidentId}
          onClick={() => launch(
            "factory.supervision-review-issue",
            "Issue follow-up",
            { incident_id: incidentId },
          )}
        >
          Issue follow-up
        </Button>
      </ActionStrip>
      {runner.confirmation}
    </>
  )
}

export function TrackerWorkflowActions({
  tracker,
  selectedBlock,
}: {
  tracker: TrackerDetail
  selectedBlock?: TrackerBlock
}) {
  const runner = useOperationRunner()
  const [dialog, setDialog] = useState<"revise" | "implement" | null>(null)
  const [revisionScope, setRevisionScope] = useState("")
  const [endBlock, setEndBlock] = useState(selectedBlock?.number ?? 0)
  const [supervision, setSupervision] = useState<"none" | "already-attached">("none")
  const [missionRoot, setMissionRoot] = useState("")
  const [missionSource, setMissionSource] = useState("")

  const baseInput = useMemo(() => ({
    content_sha256: tracker.raw_file.content_sha256,
    repository_head: tracker.git.repository_head,
    verifier_profile: tracker.profile,
  }), [tracker])
  const sourceReady = tracker.git.status === "available"
    && Boolean(tracker.git.repository_head)
    && ["full", "core"].includes(tracker.profile)
  const implementReady = sourceReady
    && tracker.verifier.valid
    && !tracker.git.worktree_changed
    && selectedBlock !== undefined
    && selectedBlock.stop !== null
    && (selectedBlock.eligible || tracker.current_blocks.includes(selectedBlock.number))

  const launchReview = () => {
    if (!tracker.git.repository_head) return
    runner.launch({
      request: {
        operation_type: "factory.tracker-review",
        target: { kind: "tracker", id: tracker.id, project_id: tracker.project_id },
        input: { ...baseInput, review_scope: defaultReviewScope },
      },
      suppliedFacts: [["Review scope", defaultReviewScope]],
    })
  }

  const submitRevision = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!revisionScope.trim() || !tracker.git.repository_head) return
    runner.launch({
      request: {
        operation_type: "factory.tracker-revise",
        target: { kind: "tracker", id: tracker.id, project_id: tracker.project_id },
        input: { ...baseInput, revision_scope: revisionScope.trim() },
      },
      suppliedFacts: [["Authorized scope", revisionScope.trim()]],
    })
    setDialog(null)
  }

  const submitImplementation = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (
      !selectedBlock
      || !tracker.git.repository_head
      || !fingerprintPattern.test(missionRoot)
      || !missionSourcePattern.test(missionSource)
    ) return
    const finalBlock = tracker.blocks.find((block) => block.number === endBlock)
    if (!finalBlock?.stop) return
    runner.launch({
      request: {
        operation_type: "factory.blocks-implement",
        target: { kind: "tracker", id: tracker.id, project_id: tracker.project_id },
        input: {
          ...baseInput,
          block_start: selectedBlock.number,
          block_end: endBlock,
          supervision,
          expected_stop: finalBlock.stop,
          mission_root: missionRoot,
          mission_source_record: missionSource,
        },
      },
      suppliedFacts: [
        ["Block range", selectedBlock.number === endBlock ? `Block ${endBlock}` : `Blocks ${selectedBlock.number}–${endBlock}`],
        ["Supervision", supervision],
        ["Mission root", missionRoot],
        ["Mission source", missionSource],
        ["Range Stop", finalBlock.stop],
      ],
    })
    setDialog(null)
  }

  const selectableEnds = selectedBlock
    ? tracker.blocks.filter((block) => block.number >= selectedBlock.number && block.number <= selectedBlock.number + 25)
    : []

  return (
    <>
      <ActionStrip feedback={runner.feedback}>
        <Button size="compact" variant="outline" disabled={!sourceReady || runner.busy} onClick={launchReview}>Review</Button>
        <Button size="compact" variant="outline" disabled={!sourceReady || tracker.git.worktree_changed || runner.busy} onClick={() => setDialog("revise")}>Revise</Button>
        <Button size="compact" disabled={!implementReady || runner.busy} onClick={() => {
          setEndBlock(selectedBlock?.number ?? 0)
          setDialog("implement")
        }}>Implement</Button>
      </ActionStrip>
      {dialog === "revise" && (
        <InputDialog title="Revise tracker" submitDisabled={!revisionScope.trim()} onClose={() => setDialog(null)} onSubmit={submitRevision}>
          <TextField label="Authorized revision scope" value={revisionScope} onChange={setRevisionScope} multiline />
        </InputDialog>
      )}
      {dialog === "implement" && selectedBlock && (
        <InputDialog title="Implement Blocks" submitDisabled={!fingerprintPattern.test(missionRoot) || !missionSourcePattern.test(missionSource)} onClose={() => setDialog(null)} onSubmit={submitImplementation}>
          <label className="workflow-input-field"><span>Range end</span><select value={endBlock} onChange={(event) => setEndBlock(Number(event.target.value))}>{selectableEnds.map((block) => <option key={block.number} value={block.number}>Block {block.number} · {block.status}</option>)}</select></label>
          <label className="workflow-input-field"><span>Supervision</span><select value={supervision} onChange={(event) => setSupervision(event.target.value as typeof supervision)}><option value="none">None</option><option value="already-attached">Already attached</option></select></label>
          <TextField label="Mission root · SHA-256" value={missionRoot} onChange={setMissionRoot} />
          <TextField label="Mission source record" value={missionSource} onChange={setMissionSource} />
          <div className="workflow-exact-fact"><span>Start</span><strong>Block {selectedBlock.number}</strong></div>
          <div className="workflow-exact-fact"><span>HEAD</span><Identity value={tracker.git.repository_head} /></div>
        </InputDialog>
      )}
      {runner.confirmation}
    </>
  )
}

export function TaskWorkflowActions({
  task,
  pending,
  trackers,
  run,
}: {
  task: Task
  pending: PendingRequest[]
  trackers: TrackerSummary[]
  run: ListedRun
}) {
  const runner = useOperationRunner()
  const [dialog, setDialog] = useState<"continue" | "steer" | "approval" | "input" | null>(null)
  const [text, setText] = useState("")
  const [selectedRequestId, setSelectedRequestId] = useState("")
  const [decision, setDecision] = useState("decline")
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const availableTrackers = useMemo(
    () => trackers.filter((tracker) => tracker.status === "available"),
    [trackers],
  )
  const boundImplementation = useMemo(() => implementationBinding(task), [task])
  const boundTracker = boundImplementation
    ? availableTrackers.find((tracker) => (
      tracker.id === boundImplementation.tracker_id
      && tracker.project_id === boundImplementation.project_id
    ))
    : undefined
  const activeTurn = task.turns.find((turn) => turn.status === "inProgress")
  const projectBound = task.project_binding.status === "bound"
    && Boolean(task.project_binding.project_id)
  const routeAvailable = Boolean(run)
  const approvalRequests = pending.filter((request) => request.family !== "user_input")
  const inputRequests = pending.filter((request) => request.family === "user_input")

  const launchContinueOrSteer = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!text.trim() || !projectBound) return
    const steering = dialog === "steer"
    if (steering && !activeTurn) return
    runner.launch({
      request: {
        operation_type: steering ? "task.steer" : "task.continue",
        target: { kind: "task", id: task.id, project_id: task.project_binding.project_id },
        input: steering ? { turn_id: activeTurn!.id, text: text.trim() } : { text: text.trim() },
      },
      suppliedFacts: [
        [steering ? "Steering text" : "New turn", text.trim()],
        ...(steering ? [["Turn", activeTurn!.id] as [string, string]] : []),
      ],
    })
    setDialog(null)
    setText("")
  }

  const launchInterrupt = () => {
    if (!activeTurn || !projectBound) return
    runner.launch({
      request: {
        operation_type: "task.interrupt",
        target: { kind: "task", id: task.id, project_id: task.project_binding.project_id },
        input: { turn_id: activeTurn.id },
      },
      suppliedFacts: [
        ["Task", task.id],
        ["Turn", activeTurn.id],
        ["Semantics", "Interrupt turn only · no lifecycle pause or stop"],
      ],
    })
  }

  const launchApproval = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!projectBound) return
    const request = approvalRequests.find((item) => item.id === selectedRequestId)
    if (!request || !request.task_id) return
    runner.launch({
      request: {
        operation_type: "task.approval-respond",
        target: { kind: "task-request", id: request.id, project_id: task.project_binding.project_id },
        input: {
          source_fingerprint: request.source_fingerprint,
          task_id: request.task_id,
          turn_id: request.turn_id,
          item_id: request.item_id,
          decision,
        },
      },
      suppliedFacts: [
        ["Request", request.id],
        ["Decision", decision],
        ["Turn", request.turn_id ?? "Unavailable"],
        ...approvalFacts(request),
      ],
    })
    setDialog(null)
  }

  const openInput = () => {
    const request = inputRequests[0]
    if (!request || request.family !== "user_input") return
    setSelectedRequestId(request.id)
    setAnswers(Object.fromEntries(request.details.questions.flatMap((question) => question.id ? [[question.id, ""]] : [])))
    setDialog("input")
  }

  const launchInput = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!projectBound) return
    const request = inputRequests.find((item) => item.id === selectedRequestId)
    if (!request || request.family !== "user_input" || !request.task_id) return
    const exactAnswers = Object.fromEntries(Object.entries(answers).map(([key, value]) => [key, [value.trim()]]))
    if (Object.values(exactAnswers).some((value) => !value[0])) return
    runner.launch({
      request: {
        operation_type: "task.input-respond",
        target: { kind: "task-request", id: request.id, project_id: task.project_binding.project_id },
        input: {
          source_fingerprint: request.source_fingerprint,
          task_id: request.task_id,
          turn_id: request.turn_id,
          item_id: request.item_id,
          answers: exactAnswers,
        },
      },
      suppliedFacts: [["Request", request.id], ...Object.entries(answers).map(([key, value]) => [key, value.trim()] as [string, string])],
    })
    setDialog(null)
  }

  const launchAttach = () => {
    if (!projectBound || !boundImplementation || !boundTracker?.git.repository_head) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-attach",
        target: { kind: "task", id: task.id, project_id: task.project_binding.project_id },
        input: {
          tracker_id: boundTracker.id,
          content_sha256: boundTracker.raw_file.content_sha256,
          repository_head: boundTracker.git.repository_head,
          verifier_profile: boundTracker.profile,
          block_start: boundImplementation.block_start,
          block_end: boundImplementation.block_end,
          mission_root: boundImplementation.mission_root,
          mission_source_record: boundImplementation.mission_source_record,
        },
      },
      suppliedFacts: [["Target", task.id], ["Tracker", boundTracker.relative_path], ["Blocks", `${boundImplementation.block_start}–${boundImplementation.block_end}`], ["Mission root", boundImplementation.mission_root], ["Mission source", boundImplementation.mission_source_record]],
    })
  }

  const selectedInputRequest = inputRequests.find((request) => request.id === selectedRequestId)
  const selectedApprovalRequest = approvalRequests.find((request) => request.id === selectedRequestId)

  return (
    <>
      <ActionStrip feedback={runner.feedback}>
        {task.status.type === "idle" && <Button size="compact" variant="outline" disabled={!projectBound || runner.busy} onClick={() => setDialog("continue")}>Continue</Button>}
        {activeTurn && <Button size="compact" variant="outline" disabled={!projectBound || !routeAvailable || runner.busy} title={!routeAvailable ? "Canonical supervision route required" : undefined} onClick={() => setDialog("steer")}>Steer</Button>}
        {activeTurn && <Button size="compact" variant="outline" disabled={!projectBound || !routeAvailable || runner.busy} title={!routeAvailable ? "Canonical supervision route required" : undefined} onClick={launchInterrupt}>Interrupt</Button>}
        {!run && boundImplementation && boundTracker && <Button size="compact" variant="outline" disabled={!projectBound || runner.busy} onClick={launchAttach}>Attach supervision</Button>}
        {approvalRequests.length > 0 && <Button size="compact" variant="outline" disabled={!projectBound || !routeAvailable || runner.busy} onClick={() => {
          setSelectedRequestId(approvalRequests[0].id)
          setDialog("approval")
        }}>Approval</Button>}
        {inputRequests.length > 0 && <Button size="compact" variant="outline" disabled={!projectBound || !routeAvailable || runner.busy} onClick={openInput}>Input</Button>}
      </ActionStrip>
      {(dialog === "continue" || dialog === "steer") && (
        <InputDialog title={dialog === "steer" ? "Steer active turn" : "Continue task"} submitDisabled={!text.trim()} onClose={() => setDialog(null)} onSubmit={launchContinueOrSteer}>
          <TextField label={dialog === "steer" ? "Steering text" : "New turn text"} value={text} onChange={setText} multiline />
        </InputDialog>
      )}
      {dialog === "approval" && (
        <InputDialog title="Respond to approval" onClose={() => setDialog(null)} onSubmit={launchApproval}>
          <label className="workflow-input-field"><span>Request</span><select value={selectedRequestId} onChange={(event) => setSelectedRequestId(event.target.value)}>{approvalRequests.map((request) => <option key={request.id} value={request.id}>{request.family.replaceAll("_", " ")} · {request.id}</option>)}</select></label>
          {approvalFacts(selectedApprovalRequest).length > 0 && (
            <dl className="workflow-request-facts">
              {approvalFacts(selectedApprovalRequest).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
            </dl>
          )}
          <label className="workflow-input-field"><span>Decision</span><select value={decision} onChange={(event) => setDecision(event.target.value)}><option value="decline">Decline</option><option value="cancel">Cancel</option><option value="accept">Accept once</option><option value="acceptForSession">Accept for session</option></select></label>
        </InputDialog>
      )}
      {dialog === "input" && selectedInputRequest?.family === "user_input" && (
        <InputDialog title="Respond to input" submitDisabled={Object.values(answers).some((value) => !value.trim())} onClose={() => setDialog(null)} onSubmit={launchInput}>
          {selectedInputRequest.details.questions.map((question) => question.id && (
            <InputQuestionControl key={question.id} question={question} value={answers[question.id] ?? ""} onChange={(value) => setAnswers((current) => ({ ...current, [question.id!]: value }))} />
          ))}
        </InputDialog>
      )}
      {runner.confirmation}
    </>
  )
}
