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
import type { RunDetail } from "@/lib/operations-api"
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
type RunPolicy = NonNullable<RunDetail["policy"]>
type CurrentMission = NonNullable<RunDetail["current_mission"]>
type WeeklyReportWorkflow = RunDetail["weekly_report_workflow"]
type PolicyField = keyof RunPolicy["adjustable"]
type AutomationRepairRow = RunPolicy["automation_reconciliation"][number]
type SuccessorTransition = RunDetail["successor_transitions"][number]
const unavailableWeeklyReportWorkflow: WeeklyReportWorkflow = {
  status: "unavailable",
  stage: "unavailable",
  next_action: null,
  actionable: false,
  report_id: null,
  coverage: null,
  coverage_days: null,
  timezone: null,
  source_root: null,
  manifest_root: null,
  fingerprint: null,
  writer_role: "roundup_writer",
  writer_task_id: null,
  expected_members: [],
  members: [],
  stages: [],
  delivery: {
    status: "unavailable",
    configured: false,
    retryable: false,
    record_id: null,
    message_id: null,
    thread_id: null,
    reason: "Weekly report workflow projection is unavailable.",
  },
  limitations: ["Weekly report workflow projection is unavailable."],
  error: {
    code: "weekly_report_workflow_unavailable",
    message: "Weekly report workflow projection is unavailable.",
    retryable: true,
  },
}
const roleRepairLabels = {
  base_reviewer: "Base reviewer",
  notice_reviewer: "Notice reviewer",
  fix_executor: "Fix executor",
  gmail_processor: "Gmail processor",
  roundup_writer: "Roundup writer",
} as const
type RepairableRole = keyof typeof roleRepairLabels
const automationRepairLabels: Record<AutomationRepairRow["role"], string> = {
  watcher: "Routine watcher",
  reviewer: "Effectiveness reviewer",
  gmail_gate: "Gmail reply gate",
  roundup_writer: "Roundup writer",
  weekly_report: "Weekly report",
}

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
const policyFieldLabels: Record<PolicyField, string> = {
  routine_minutes: "Routine minutes",
  meta_review_hours: "Meta-review hours",
  max_sample_denominator: "Max sample denominator",
  cooldown_minutes: "Escalation cooldown minutes",
  max_escalations_per_hour: "Max escalations per hour",
  gmail_quiet_minutes: "Gmail quiet minutes",
  gmail_active_minutes: "Gmail active minutes",
  gmail_active_window_minutes: "Gmail active window minutes",
  skill_maintenance_mode: "Skill maintenance mode",
}

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
  const [expiredReason, setExpiredReason] = useState<string | null>(null)

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
      setExpiredReason(null)
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
      setExpiredReason(null)
      setLocalError(null)
      refreshSources()
    },
    onError: (error) => {
      if (error instanceof DashboardApiError && error.code === "preview_expired") {
        setExpiredReason(error.message)
        setLocalError(null)
      } else if (error instanceof DashboardApiError && [
        "preview_stale",
        "route_gate_stale",
        "route_gate_denied",
      ].includes(error.code)) {
        setStaleReason(error.message)
        setLocalError(null)
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
    setExpiredReason(null)
    previewMutation.mutate(value.request)
  }

  const close = () => {
    if (preview) cancelMutation.mutate(preview.data.operation.id)
    setPreview(null)
    setPrepared(null)
    setStaleReason(null)
    setExpiredReason(null)
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
      expiredReason={expiredReason}
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
  policy,
  lifecycleStatus = null,
  missionBindingMissing = false,
  roleRepairRoles = [],
  currentMission = null,
  successorTransitions = [],
  weeklyReportWorkflow = unavailableWeeklyReportWorkflow,
}: {
  targetId: string
  projectId: string | null
  openIncidentIds: string[]
  policy: RunPolicy | null
  lifecycleStatus?: string | null
  missionBindingMissing?: boolean
  roleRepairRoles?: string[]
  currentMission?: CurrentMission | null
  successorTransitions?: SuccessorTransition[]
  weeklyReportWorkflow?: WeeklyReportWorkflow
}) {
  const runner = useOperationRunner()
  const [selectedIncident, setSelectedIncident] = useState("")
  const [adjustOpen, setAdjustOpen] = useState(false)
  const [adjustReason, setAdjustReason] = useState("")
  const [adjustEnabled, setAdjustEnabled] = useState<Partial<Record<PolicyField, boolean>>>({})
  const [adjustValues, setAdjustValues] = useState<Partial<Record<PolicyField, string>>>({})
  const [successorOpen, setSuccessorOpen] = useState(false)
  const [successorSource, setSuccessorSource] = useState("")
  const [successorDisposition, setSuccessorDisposition] = useState<"completed" | "superseded">("superseded")
  const [successorFirstWork, setSuccessorFirstWork] = useState("")
  const [successorReason, setSuccessorReason] = useState("")
  const repairableRoles = roleRepairRoles.filter(
    (role): role is RepairableRole => role in roleRepairLabels,
  )
  const [selectedRepairRole, setSelectedRepairRole] = useState<RepairableRole | "">("")
  const repairRole = repairableRoles.includes(selectedRepairRole as RepairableRole)
    ? selectedRepairRole as RepairableRole
    : repairableRoles[0] ?? ""
  const repairableAutomations = policy?.automation_reconciliation.filter((row) => (
    row.state === "partial" && row.repairable === true && Boolean(row.automation_id)
  )) ?? []
  const [selectedAutomationRole, setSelectedAutomationRole] = useState<AutomationRepairRow["role"] | "">("")
  const automationRepair = repairableAutomations.find((row) => row.role === selectedAutomationRole)
    ?? repairableAutomations[0]
  const incidentId = openIncidentIds.includes(selectedIncident)
    ? selectedIncident
    : openIncidentIds[0] ?? ""
  const launchReview = (
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
  const openAdjustment = () => {
    if (!policy) return
    setAdjustEnabled({})
    setAdjustValues(Object.fromEntries(
      Object.entries(policy.adjustable).map(([field, value]) => [field, value === null ? "" : String(value)]),
    ) as Partial<Record<PolicyField, string>>)
    setAdjustReason("")
    setAdjustOpen(true)
  }
  const selectedPolicyFields = policy?.adjustment_contract.fields.filter(
    (contract) => adjustEnabled[contract.field],
  ) ?? []
  const parsedAdjustment = policy
    ? Object.fromEntries(selectedPolicyFields.map((contract) => {
      const value = adjustValues[contract.field] ?? ""
      return [contract.field, contract.kind === "integer" ? Number(value) : value]
    })) as Partial<Record<PolicyField, number | string>>
    : {}
  const mergedGmail = policy ? {
    quiet: typeof parsedAdjustment.gmail_quiet_minutes === "number"
      ? parsedAdjustment.gmail_quiet_minutes
      : policy.adjustable.gmail_quiet_minutes,
    active: typeof parsedAdjustment.gmail_active_minutes === "number"
      ? parsedAdjustment.gmail_active_minutes
      : policy.adjustable.gmail_active_minutes,
    window: typeof parsedAdjustment.gmail_active_window_minutes === "number"
      ? parsedAdjustment.gmail_active_window_minutes
      : policy.adjustable.gmail_active_window_minutes,
  } : null
  const adjustmentValid = Boolean(
    policy
    && adjustReason.trim()
    && adjustReason === adjustReason.trim()
    && selectedPolicyFields.length > 0
    && selectedPolicyFields.every((contract) => {
      const parsed = parsedAdjustment[contract.field]
      const current = policy.adjustable[contract.field]
      if (contract.kind === "enum") return typeof parsed === "string" && parsed.length > 0 && parsed !== current
      return typeof parsed === "number"
        && Number.isInteger(parsed)
        && contract.minimum !== null
        && contract.maximum !== null
        && parsed >= contract.minimum
        && parsed <= contract.maximum
        && parsed !== current
    })
    && mergedGmail
    && typeof mergedGmail.quiet === "number"
    && typeof mergedGmail.active === "number"
    && typeof mergedGmail.window === "number"
    && mergedGmail.active < mergedGmail.quiet
  )
  const submitAdjustment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!policy || !projectId || !adjustmentValid) return
    const changes = Object.fromEntries(
      selectedPolicyFields.map((contract) => [contract.field, parsedAdjustment[contract.field]]),
    )
    const affectedRoles = [...new Set(
      selectedPolicyFields.flatMap((contract) => (
        contract.automation_role ? [contract.automation_role] : []
      )),
    )]
    runner.launch({
      request: {
        operation_type: "factory.supervision-adjust",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: { reason: adjustReason, ...changes },
      },
      suppliedFacts: [
        ["Diff", selectedPolicyFields.map((contract) => (
          `${policyFieldLabels[contract.field]}: ${String(policy.adjustable[contract.field])} → ${String(parsedAdjustment[contract.field])}`
        )).join(" · ")],
        ["Preserved", `${policy.adjustment_contract.fields.length - selectedPolicyFields.length} adjustable fields plus every unlisted policy field`],
        ["Automation owners", affectedRoles.length ? affectedRoles.join(" · ") : "No schedule owner affected"],
        ["Recovery", "No automatic rollback · restore prior values through a new bounded owner request"],
        ["Reason", adjustReason],
      ],
    })
    setAdjustOpen(false)
  }
  const unavailable = !projectId || runner.busy
  const gmailBound = policy?.automation_reconciliation.some((row) => (
    row.role === "gmail_gate" && row.state !== "unavailable"
  )) ?? false
  const pauseAutomationRows = policy?.automation_reconciliation ?? []
  const boundAutomationRows = pauseAutomationRows.filter((row) => Boolean(row.automation_id))
  const pauseComplete = lifecycleStatus === "paused"
    && pauseAutomationRows.length >= 2
    && pauseAutomationRows.every((row) => (
      Boolean(row.automation_id) && row.owner_status === "PAUSED"
    ))
  const resumeSourceAvailable = lifecycleStatus === "paused"
    && pauseAutomationRows.length >= 2
    && pauseAutomationRows.every((row) => (
      Boolean(row.automation_id)
      && row.state !== "unavailable"
      && (row.owner_status === "PAUSED" || row.owner_status === "ACTIVE")
    ))
  const activeAutomationCount = pauseAutomationRows.filter((row) => (
    row.owner_status === "ACTIVE"
  )).length
  const resumeComplete = lifecycleStatus === "resumed"
    && pauseAutomationRows.length >= 2
    && pauseAutomationRows.every((row) => (
      Boolean(row.automation_id)
      && row.owner_status === "ACTIVE"
      && row.state === "reconciled"
      && row.duplicate_coverage === "exact"
    ))
  const launchBindingRepair = () => {
    if (!projectId || !missionBindingMissing) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-repair-mission-binding",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: {},
      },
      suppliedFacts: [
        ["Repair", "Missing mission binding only"],
        ["Source", "Exact complete user item · authority unverified until independent reviewer proof"],
        ["Tracker", "Current path and content root from the registered project"],
        ["Excluded", "Mission overwrite · tracker mutation · role or automation rebinding"],
      ],
    })
  }
  const launchRoleBindingRepair = () => {
    if (!projectId || !repairRole) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-repair-role-task-binding",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: { role: repairRole },
      },
      suppliedFacts: [
        ["Role", roleRepairLabels[repairRole]],
        ["Candidate", "Exact prior task ID from canonical policy history"],
        ["Task effect", "Read only · no create, resume, turn, or relabel"],
        ["Policy effect", "Fill this missing role only · preserve mission, roles, and automations"],
        ["Completion", "Task + policy record + maintained purpose gate must all agree"],
      ],
    })
  }
  const launchAutomationBindingRepair = () => {
    if (!projectId || !automationRepair?.automation_id) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-repair-automation-binding",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: { role: automationRepair.role },
      },
      suppliedFacts: [
        ["Role / purpose", `${automationRepairLabels[automationRepair.role]} · ${automationRepair.purpose ?? "Maintained policy role"}`],
        ["Automation ID", `${automationRepair.actual_automation_id ?? automationRepair.automation_id} → ${automationRepair.automation_id}`],
        ["Target", `${automationRepair.actual_target_thread_id ?? "Unavailable"} → ${automationRepair.target_thread_id ?? "Unavailable"}`],
        ["Schedule", `${automationRepair.actual_rrule ?? "Unavailable"} → ${automationRepair.expected_rrule ?? "Unavailable"}`],
        ["Time zone", `${automationRepair.actual_timezone ?? "Unavailable"} → ${automationRepair.timezone ?? "Unavailable"}`],
        ["Duplicate proof", `${automationRepair.duplicate_coverage} · ${automationRepair.active_target_owner_ids.length} active owner${automationRepair.active_target_owner_ids.length === 1 ? "" : "s"} on target`],
        ["Completion", "Named automation + canonical policy binding + exact role task + no conflicting active owner"],
        ["Recovery", "No automatic retry or rollback · partial owner state stays visible"],
      ],
    })
  }
  const launchPause = () => {
    if (!projectId || pauseComplete) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-pause",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: {},
      },
      suppliedFacts: [
        ["Group", targetId],
        ["Lifecycle", lifecycleStatus ?? "No current lifecycle record"],
        ["Automation owners", `${boundAutomationRows.length}/${pauseAutomationRows.length} exact configured automation owner${pauseAutomationRows.length === 1 ? "" : "s"}`],
        ["Preserved", "Implementation task and turn state · policy · mission · bindings"],
        ["Completion", "Canonical paused lifecycle + every exact bound automation PAUSED"],
        ["Recovery", "Partial owner state stays visible · no automatic retry or rollback"],
      ],
    })
  }
  const launchResume = () => {
    if (!projectId || !resumeSourceAvailable || resumeComplete) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-resume",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: {},
      },
      suppliedFacts: [
        ["Group", targetId],
        ["Lifecycle", "Canonical paused lifecycle"],
        ["Automation owners", `${activeAutomationCount} active · ${pauseAutomationRows.length - activeAutomationCount} paused · ${pauseAutomationRows.length} exact configured`],
        ["Preserved", "Implementation task and turn state · policy · mission · bindings"],
        ["Completion", "Every exact named automation ACTIVE + canonical supervision-resume lifecycle"],
        ["Recovery", "Partial owner state stays visible · no automatic retry or rollback"],
      ],
    })
  }
  const successorValid = Boolean(
    projectId
    && currentMission?.root
    && missionSourcePattern.test(successorSource)
    && successorFirstWork.trim() === successorFirstWork
    && successorFirstWork.length > 0
    && successorFirstWork.length <= 160
    && successorReason.trim() === successorReason
    && successorReason.length > 0
    && successorReason.length <= 480
  )
  const submitSuccessor = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!projectId || !currentMission?.root || !successorValid) return
    runner.launch({
      request: {
        operation_type: "factory.supervision-mission-successor",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: {
          mission_source_record: successorSource,
          predecessor_disposition: successorDisposition,
          first_eligible_work: successorFirstWork,
          reason: successorReason,
        },
      },
      suppliedFacts: [
        ["Target / group", targetId],
        ["Predecessor", `${currentMission.root} · ${successorDisposition}`],
        ["Candidate source", `${successorSource} · exact bytes and direct authority require independent review`],
        ["First eligible work", `${successorFirstWork} · pending activation, not proof of work-start`],
        ["Preserved", "Target · supervision group · roles · automations · predecessor history"],
        ["Excluded", "Bind overwrite · successor task · direct policy or ledger write · completion claim"],
        ["Reason", successorReason],
      ],
    })
    setSuccessorOpen(false)
  }
  const openSuccessorTransitions = successorTransitions.filter((transition) => transition.open)
  const currentTransition = openSuccessorTransitions.length === 1
    ? openSuccessorTransitions[0]
    : null
  const launchSuccessorTransition = () => {
    if (!projectId || !currentTransition) return
    runner.launch({
      request: {
        operation_type: "factory.successor-task-transition",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: { transition_id: currentTransition.transition_id },
      },
      suppliedFacts: [
        ["Transition", currentTransition.transition_id],
        ["Current phase", currentTransition.phase ?? "Unavailable"],
        ["Tracker / range", `${currentTransition.tracker_sha256 ?? "Unavailable"} · ${currentTransition.requested_block_range ?? "Unavailable"}`],
        ["First eligible Block", currentTransition.first_eligible_block ?? "Unavailable"],
        ["Successor", currentTransition.successor_thread_id ?? "Not created"],
        ["Source posture", "In progress until exact work-started evidence"],
        ["Recovery", "One phase only · no retry, phase leap, source stop, or completion claim"],
      ],
    })
  }
  const reportActionLabel = weeklyReportWorkflow.next_action === "prepare"
    ? "Prepare report"
    : weeklyReportWorkflow.next_action === "review-finalize"
      ? "Review & finalize"
      : weeklyReportWorkflow.next_action === "deliver"
        ? "Deliver report"
        : weeklyReportWorkflow.stage === "delivered"
          ? "Report delivered"
          : weeklyReportWorkflow.stage === "verified"
            ? "Report verified"
            : "Report unavailable"
  const launchWeeklyReport = () => {
    if (
      !projectId
      || !weeklyReportWorkflow.actionable
      || weeklyReportWorkflow.coverage_days === null
    ) return
    runner.launch({
      request: {
        operation_type: "factory.weekly-supervision-report",
        target: { kind: "run", id: targetId, project_id: projectId },
        input: { coverage_days: weeklyReportWorkflow.coverage_days },
      },
      suppliedFacts: [
        ["Report", weeklyReportWorkflow.report_id ?? "Current owner-derived report"],
        ["Stage", `${weeklyReportWorkflow.stage} → ${weeklyReportWorkflow.next_action}`],
        ["Period", weeklyReportWorkflow.coverage
          ? `${weeklyReportWorkflow.coverage.start} → ${weeklyReportWorkflow.coverage.end} · ${weeklyReportWorkflow.timezone}`
          : "Unavailable"],
        ["Source root", weeklyReportWorkflow.source_root ?? "Unavailable"],
        ["Writer", weeklyReportWorkflow.writer_task_id ?? "Unavailable"],
        ["Bundle", weeklyReportWorkflow.expected_members.join(" · ")],
        ["Delivery", `${weeklyReportWorkflow.delivery.status} · ${weeklyReportWorkflow.delivery.reason ?? "Current"}`],
        ["Recovery", "Advance one stage only · retain every exact accepted prior stage · no automatic retry"],
      ],
    })
  }
  return (
    <>
      <ActionStrip feedback={runner.feedback}>
        <Button size="compact" variant="outline" disabled={unavailable} onClick={() => launchReview("factory.supervision-check-now", "Mechanical check")}>Check now</Button>
        <Button size="compact" variant="outline" disabled={unavailable} onClick={() => launchReview("factory.supervision-review-checkpoint", "Checkpoint review")}>Checkpoint review</Button>
        <Button size="compact" variant="outline" disabled={unavailable} onClick={() => launchReview("factory.supervision-review-meta", "Meta-review")}>Meta-review</Button>
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
          onClick={() => launchReview(
            "factory.supervision-review-issue",
            "Issue follow-up",
            { incident_id: incidentId },
          )}
        >
          Issue follow-up
        </Button>
        <Button
          size="compact"
          variant="outline"
          disabled={unavailable || !policy || !currentMission?.root}
          onClick={() => setSuccessorOpen(true)}
        >
          Successor mission
        </Button>
        {openSuccessorTransitions.length > 0 && (
          <Button
            size="compact"
            variant="outline"
            disabled={unavailable || currentTransition === null}
            title={
              openSuccessorTransitions.length > 1
                ? "Multiple open transition heads conflict; no phase action is available."
                : "Advance exactly one canonical successor-task continuity phase."
            }
            onClick={launchSuccessorTransition}
          >
            {openSuccessorTransitions.length > 1 ? "Continuity conflict" : "Advance continuity"}
          </Button>
        )}
        <Button
          size="compact"
          variant="outline"
          disabled={unavailable || !weeklyReportWorkflow.actionable}
          title={weeklyReportWorkflow.error?.message ?? weeklyReportWorkflow.delivery.reason ?? undefined}
          onClick={launchWeeklyReport}
        >
          {reportActionLabel}
        </Button>
        <Button size="compact" disabled={unavailable || !policy} onClick={openAdjustment}>Adjust supervision</Button>
        <Button
          size="compact"
          variant="outline"
          disabled={unavailable || !policy || pauseComplete}
          onClick={launchPause}
        >
          {pauseComplete ? "Paused" : lifecycleStatus === "paused" ? "Finish pause" : "Pause"}
        </Button>
        <Button
          size="compact"
          variant="outline"
          disabled={unavailable || !resumeSourceAvailable || resumeComplete}
          title={
            resumeComplete
              ? "Every exact automation and the canonical resume lifecycle are current."
              : lifecycleStatus === "resumed"
                ? "Canonical resume exists, but exact active automation-owner coverage is unavailable or incomplete."
              : lifecycleStatus !== "paused"
                ? "Resume is available only for a canonical paused lifecycle."
                : !resumeSourceAvailable
                  ? "Resume requires complete current automation-owner coverage."
                  : undefined
          }
          onClick={launchResume}
        >
          {resumeComplete
            ? "Running"
            : lifecycleStatus === "resumed"
              ? "Resume incomplete"
            : resumeSourceAvailable && activeAutomationCount > 0
              ? "Finish resume"
              : lifecycleStatus === "paused" && !resumeSourceAvailable
                ? "Resume unavailable"
                : "Resume"}
        </Button>
        {missionBindingMissing && (
          <Button size="compact" disabled={unavailable} onClick={launchBindingRepair}>Repair binding</Button>
        )}
        {repairableRoles.length > 0 && (
          <>
            <select
              aria-label="Role binding to repair"
              value={repairRole}
              disabled={unavailable}
              onChange={(event) => setSelectedRepairRole(event.target.value as RepairableRole)}
            >
              {repairableRoles.map((role) => (
                <option key={role} value={role}>{roleRepairLabels[role]}</option>
              ))}
            </select>
            <Button size="compact" disabled={unavailable || !repairRole} onClick={launchRoleBindingRepair}>Repair role</Button>
          </>
        )}
        {repairableAutomations.length > 0 && (
          <>
            <select
              aria-label="Automation binding to repair"
              value={automationRepair?.role ?? ""}
              disabled={unavailable}
              onChange={(event) => setSelectedAutomationRole(event.target.value as AutomationRepairRow["role"])}
            >
              {repairableAutomations.map((row) => (
                <option key={row.role} value={row.role}>
                  {automationRepairLabels[row.role]} · {row.automation_id}
                </option>
              ))}
            </select>
            <Button
              size="compact"
              disabled={unavailable || !automationRepair?.automation_id}
              onClick={launchAutomationBindingRepair}
            >
              Repair automation
            </Button>
          </>
        )}
      </ActionStrip>
      {adjustOpen && policy && (
        <InputDialog
          title="Adjust supervision"
          submitDisabled={!adjustmentValid}
          onClose={() => setAdjustOpen(false)}
          onSubmit={submitAdjustment}
        >
          <div className="policy-adjust-fields">
            {policy.adjustment_contract.fields.map((contract) => {
              const gmailUnavailable = contract.field.startsWith("gmail_") && !gmailBound
              const enabled = Boolean(adjustEnabled[contract.field])
              return (
                <div className="policy-adjust-field" key={contract.field}>
                  <label>
                    <input
                      type="checkbox"
                      checked={enabled}
                      disabled={gmailUnavailable}
                      onChange={(event) => setAdjustEnabled((current) => ({
                        ...current,
                        [contract.field]: event.target.checked,
                      }))}
                    />
                    <span>{policyFieldLabels[contract.field]}</span>
                    <small>Current {String(policy.adjustable[contract.field] ?? "unavailable")}</small>
                  </label>
                  {contract.kind === "enum" ? (
                    <select
                      aria-label={`New ${policyFieldLabels[contract.field]}`}
                      value={adjustValues[contract.field] ?? ""}
                      disabled={!enabled || gmailUnavailable}
                      onChange={(event) => setAdjustValues((current) => ({ ...current, [contract.field]: event.target.value }))}
                    >
                      {policy.adjustment_contract.skill_maintenance_modes.map((mode) => <option key={mode} value={mode}>{mode}</option>)}
                    </select>
                  ) : (
                    <input
                      aria-label={`New ${policyFieldLabels[contract.field]}`}
                      type="number"
                      min={contract.minimum ?? undefined}
                      max={contract.maximum ?? undefined}
                      value={adjustValues[contract.field] ?? ""}
                      disabled={!enabled || gmailUnavailable}
                      onChange={(event) => setAdjustValues((current) => ({ ...current, [contract.field]: event.target.value }))}
                    />
                  )}
                  {gmailUnavailable && <small>Gmail owner not bound</small>}
                  {contract.automation_role && !gmailUnavailable && <small>{contract.automation_role} schedule</small>}
                </div>
              )
            })}
          </div>
          <TextField label="Reason" value={adjustReason} onChange={setAdjustReason} />
        </InputDialog>
      )}
      {successorOpen && currentMission?.root && (
        <InputDialog
          title="Successor mission"
          submitDisabled={!successorValid}
          onClose={() => setSuccessorOpen(false)}
          onSubmit={submitSuccessor}
        >
          <div className="workflow-exact-fact"><span>Predecessor</span><Identity value={currentMission.root} /></div>
          <TextField label="Direct mission source record" value={successorSource} onChange={setSuccessorSource} placeholder={`codex:${targetId}:turn-id:item-id`} />
          <label className="workflow-input-field">
            <span>Predecessor disposition</span>
            <select value={successorDisposition} onChange={(event) => setSuccessorDisposition(event.target.value as typeof successorDisposition)}>
              <option value="superseded">Superseded</option>
              <option value="completed">Completed</option>
            </select>
          </label>
          <TextField label="First eligible work" value={successorFirstWork} onChange={setSuccessorFirstWork} />
          <TextField label="Reason" value={successorReason} onChange={setSuccessorReason} />
          <div className="workflow-exact-fact"><span>Authority</span><strong>Independent direct-source review required</strong></div>
        </InputDialog>
      )}
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
