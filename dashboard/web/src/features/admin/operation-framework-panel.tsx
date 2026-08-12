import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ArrowUpRight, ShieldCheck, X } from "lucide-react"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { OperationSemanticDiffTable } from "@/components/operation-semantic-diff"
import { Identity, QueryState, StatusMark, TimeValue } from "@/components/workspace-ui"
import {
  fetchOperationFramework,
  type OperationPreviewEnvelope,
  type OperationPreviewRequest,
  type OperationRecord,
} from "@/lib/admin-operations-api"

export function OperationDisabledReason({ reason }: { reason: string }) {
  return (
    <div className="operation-disabled-reason" role="status">
      <ShieldCheck aria-hidden="true" />
      <span>{reason}</span>
    </div>
  )
}

export function OperationConfirmationDialog({
  preview,
  request,
  suppliedFacts = [],
  staleReason,
  expiredReason,
  busy = false,
  onConfirm,
  onCancel,
  onRefresh,
}: {
  preview: OperationPreviewEnvelope
  request: OperationPreviewRequest
  suppliedFacts?: Array<[string, string]>
  staleReason?: string | null
  expiredReason?: string | null
  busy?: boolean
  onConfirm: (confirmation: { class: string; value: string }) => void
  onCancel: () => void
  onRefresh?: () => void
}) {
  const [value, setValue] = useState("")
  const [clockNow, setClockNow] = useState(() => Date.now())
  const operation = preview.data.operation
  const confirmation = operation.preview.confirmation
  const sourceEvidence = operation.preview.source_evidence
  const reviewState = typeof sourceEvidence.state_fingerprint === "string"
    ? sourceEvidence.state_fingerprint
    : null
  const reviewSource = typeof sourceEvidence.source_record === "string"
    ? sourceEvidence.source_record
    : null
  const reviewerRole = typeof sourceEvidence.reviewer_role === "string"
    ? sourceEvidence.reviewer_role
    : null
  const expectedKind = typeof sourceEvidence.expected_kind === "string"
    ? sourceEvidence.expected_kind
    : null
  const incidentId = typeof sourceEvidence.incident_id === "string"
    ? sourceEvidence.incident_id
    : null
  const isBindingRepair = operation.type === "factory.supervision-repair-mission-binding"
  const isRoleBindingRepair = operation.type === "factory.supervision-repair-role-task-binding"
  const hasSemanticPreview = operation.preview.semantic_changes.status === "available"
    && operation.preview.semantic_changes.complete
    && operation.preview.semantic_changes.rows.length > 0
  const bindingSourceRecord = isBindingRepair
    && typeof sourceEvidence.mission_source_record === "string"
    ? sourceEvidence.mission_source_record
    : null
  const bindingSourceSha256 = isBindingRepair
    && typeof sourceEvidence.mission_source_sha256 === "string"
    ? sourceEvidence.mission_source_sha256
    : null
  const bindingSourceEnvelopeSha256 = isBindingRepair
    && typeof sourceEvidence.mission_source_envelope_sha256 === "string"
    ? sourceEvidence.mission_source_envelope_sha256
    : null
  const bindingSourceClient = isBindingRepair
    && typeof sourceEvidence.mission_source_client_id === "string"
    ? sourceEvidence.mission_source_client_id
    : null
  const bindingSourceClassification = isBindingRepair
    && typeof sourceEvidence.mission_source_classification === "string"
    ? sourceEvidence.mission_source_classification
    : null
  const bindingSourceAuthority = isBindingRepair
    && typeof sourceEvidence.mission_source_authority_status === "string"
    ? sourceEvidence.mission_source_authority_status
    : null
  const bindingProject = isBindingRepair
    && typeof sourceEvidence.run_project_binding === "object"
    && sourceEvidence.run_project_binding !== null
    && "project_id" in sourceEvidence.run_project_binding
    && typeof sourceEvidence.run_project_binding.project_id === "string"
    ? sourceEvidence.run_project_binding.project_id
    : null
  const roleBindingRole = isRoleBindingRepair && typeof sourceEvidence.role_label === "string"
    ? sourceEvidence.role_label
    : null
  const roleBindingTask = isRoleBindingRepair && typeof sourceEvidence.expected_task_id === "string"
    ? sourceEvidence.expected_task_id
    : null
  const roleBindingStatus = isRoleBindingRepair && typeof sourceEvidence.candidate_task_status === "string"
    ? sourceEvidence.candidate_task_status
    : null
  const roleBindingPurpose = isRoleBindingRepair && typeof sourceEvidence.route_purpose === "string"
    ? sourceEvidence.route_purpose
    : null
  const roleBindingModel = isRoleBindingRepair
    && typeof sourceEvidence.expected_model === "object"
    && sourceEvidence.expected_model !== null
    && "model" in sourceEvidence.expected_model
    && "reasoning" in sourceEvidence.expected_model
    && typeof sourceEvidence.expected_model.model === "string"
    && typeof sourceEvidence.expected_model.reasoning === "string"
    ? `${sourceEvidence.expected_model.model} · ${sourceEvidence.expected_model.reasoning}`
    : null
  const roleBindingObservedModel = isRoleBindingRepair
    && typeof sourceEvidence.observed_model_and_effort === "object"
    && sourceEvidence.observed_model_and_effort !== null
    && "model" in sourceEvidence.observed_model_and_effort
    && "reasoning" in sourceEvidence.observed_model_and_effort
    && typeof sourceEvidence.observed_model_and_effort.model === "string"
    && typeof sourceEvidence.observed_model_and_effort.reasoning === "string"
    ? `${sourceEvidence.observed_model_and_effort.model} · ${sourceEvidence.observed_model_and_effort.reasoning}`
    : null
  const expiresAt = Date.parse(operation.preview.expires_at)
  const expired = Boolean(expiredReason) || clockNow >= expiresAt
  const currentnessReason = expiredReason
    ?? (expired ? "This preview has passed its exact expiry. Request a fresh preview before continuing." : staleReason)
  const matches = value === confirmation.expected_value

  useEffect(() => {
    setValue("")
  }, [preview.data.preview_token])

  useEffect(() => {
    let timer: number | undefined
    const update = () => {
      const now = Date.now()
      setClockNow(now)
      const remaining = expiresAt - now
      if (remaining > 0) {
        timer = window.setTimeout(update, Math.min(remaining, 2_147_483_647))
      }
    }
    update()
    return () => {
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [expiresAt])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel()
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [onCancel])

  return (
    <div className="operation-dialog-backdrop">
      <div
        className="operation-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="operation-confirmation-title"
      >
        <div className="operation-dialog-heading">
          <div>
            <span>Operation preview</span>
            <h2 id="operation-confirmation-title">{operation.preview.effect}</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onCancel} aria-label="Close operation preview">
            <X aria-hidden="true" />
          </Button>
        </div>

        <dl className="operation-preview-facts">
          <div><dt>Target</dt><dd><Identity value={request.target.id} /><Identity value={request.target.project_id} /></dd></div>
          <div><dt>Owner</dt><dd>{operation.owner}</dd></div>
          <div><dt>Recipient</dt><dd>{operation.preview.recipient ? <Identity value={operation.preview.recipient} /> : "No cross-thread recipient"}</dd></div>
          <div>
            <dt>Gate</dt>
            <dd>
              <StatusMark status={operation.preview.route_gate.status} />
              {operation.preview.route_gate.purpose && <span>{operation.preview.route_gate.purpose}</span>}
            </dd>
          </div>
          <div><dt>Source</dt><dd><Identity value={operation.preview.source_fingerprint} /></dd></div>
          {bindingSourceRecord && <div><dt>Source candidate item</dt><dd><code className="operation-exact-value">{bindingSourceRecord}</code></dd></div>}
          {bindingSourceSha256 && <div><dt>Source content root</dt><dd><code className="operation-exact-value">{bindingSourceSha256}</code></dd></div>}
          {bindingSourceEnvelopeSha256 && <div><dt>Source envelope root</dt><dd><code className="operation-exact-value">{bindingSourceEnvelopeSha256}</code></dd></div>}
          {bindingSourceClient && <div><dt>Transport client ID</dt><dd><code className="operation-exact-value">{bindingSourceClient}</code></dd></div>}
          {bindingSourceClassification && <div><dt>Transport classification</dt><dd>{bindingSourceClassification.replaceAll("-", " ")}</dd></div>}
          {bindingSourceAuthority && <div><dt>Source authority</dt><dd>{bindingSourceAuthority.replaceAll("-", " ")}</dd></div>}
          {bindingProject && <div><dt>Canonical run project</dt><dd><Identity value={bindingProject} /></dd></div>}
          {roleBindingRole && <div><dt>Role</dt><dd>{roleBindingRole}</dd></div>}
          {roleBindingTask && <div><dt>Exact prior task</dt><dd><Identity value={roleBindingTask} /></dd></div>}
          {roleBindingStatus && <div><dt>Task lifecycle</dt><dd>{roleBindingStatus}</dd></div>}
          {roleBindingModel && <div><dt>Required role model</dt><dd>{roleBindingModel}</dd></div>}
          {roleBindingObservedModel && <div><dt>Task-observed model</dt><dd>{roleBindingObservedModel}</dd></div>}
          {roleBindingPurpose && <div><dt>Post-bind route</dt><dd>{roleBindingPurpose}</dd></div>}
          {reviewState && <div><dt>State</dt><dd><Identity value={reviewState} /></dd></div>}
          {reviewSource && <div><dt>Source record</dt><dd><Identity value={reviewSource} /></dd></div>}
          {(reviewerRole || expectedKind) && (
            <div><dt>Review binding</dt><dd>{reviewerRole && <span>{reviewerRole}</span>}{expectedKind && <span>{expectedKind}</span>}</dd></div>
          )}
          {incidentId && <div><dt>Incident</dt><dd><Identity value={incidentId} /></dd></div>}
          <div><dt>Expires</dt><dd><TimeValue value={operation.preview.expires_at} /></dd></div>
        </dl>

        {hasSemanticPreview ? (
          <OperationSemanticDiffTable
            changes={operation.preview.semantic_changes}
            expired={expired}
          />
        ) : null}

        <div className="operation-preview-consequences">
          <div><strong>Risk</strong><p>{operation.preview.risk}</p></div>
          <div><strong>Expected postcondition</strong><p>{operation.preview.expected_postcondition}</p></div>
          <div><strong>Failure posture</strong><p>{operation.preview.consequences.failure.join(" ")}</p></div>
        </div>

        {suppliedFacts.length > 0 && (
          <dl className="operation-supplied-facts">
            {suppliedFacts.map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
            ))}
          </dl>
        )}

        {currentnessReason ? (
          <div className="operation-stale" role="alert">
            <AlertTriangle aria-hidden="true" />
            <div><strong>{expired ? "Preview expired" : "Preview is stale"}</strong><span>{currentnessReason}</span></div>
            {onRefresh && <Button variant="outline" size="compact" onClick={onRefresh}>Preview again</Button>}
          </div>
        ) : (
          <label className="operation-confirmation-input">
            <span>{confirmation.prompt}</span>
            <input
              autoFocus
              autoComplete="off"
              spellCheck={false}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          </label>
        )}

        <div className="operation-dialog-actions">
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button
            disabled={Boolean(currentnessReason) || !matches || busy}
            onClick={() => {
              const now = Date.now()
              if (now >= expiresAt) {
                setClockNow(now)
                return
              }
              onConfirm({ class: confirmation.class, value })
            }}
          >
            {busy ? "Requesting" : "Request operation"}
          </Button>
        </div>
      </div>
    </div>
  )
}

export function OperationFollowUp({ operation }: { operation: OperationRecord }) {
  if (![
    "awaiting-approval",
    "awaiting-input",
    "requested",
    "verifying",
    "unverified",
    "failed",
  ].includes(operation.state)) return null

  const message = operation.state === "awaiting-approval"
    ? "The owner is awaiting approval. No approval response was inferred or sent."
    : operation.state === "awaiting-input"
      ? "The owner is awaiting input. No answer was inferred or sent."
      : operation.state === "requested" || operation.state === "verifying"
        ? "The owner accepted the request; its canonical postcondition is not yet verified."
        : operation.state === "unverified"
          ? "The owner request may have had an effect, but the canonical postcondition is unverified."
          : operation.failure?.message ?? "The owner operation failed."

  return (
    <div className="operation-follow-up" role={operation.state === "failed" ? "alert" : "status"}>
      <AlertTriangle aria-hidden="true" />
      <span>{message}</span>
    </div>
  )
}

export function OperationTruthFacts({ operation }: { operation: OperationRecord }) {
  const evidence = operation.verification_evidence
  const facts: string[] = []
  if (operation.type === "factory.supervision-check-now") {
    if (operation.request_evidence?.watcher_awakened === true) facts.push("Watcher awakened")
    if (evidence?.check_recorded === true) facts.push("Canonical check recorded")
    else if (operation.request_evidence?.watcher_awakened === true) facts.push("Canonical check not yet verified")
    if (evidence?.changed_state_routed === true) facts.push("Changed state routed for review")
    if (evidence?.semantic_conclusion === false) facts.push("No semantic conclusion inferred")
  }
  if (operation.type.startsWith("factory.supervision-review-")) {
    if (operation.request_evidence?.review_task_started === true) facts.push("Reviewer task started")
    if (evidence?.conclusion_recorded === true) facts.push("Canonical conclusion recorded")
    else if (
      evidence?.reviewer_request_current === false
      && typeof evidence?.matching_record_id === "string"
    ) facts.push("Matching record is not correlated to the exact reviewer turn")
    else if (operation.request_evidence?.review_task_started === true) facts.push("Awaiting canonical conclusion")
    if (typeof evidence?.conclusion_status === "string") facts.push(`Conclusion: ${evidence.conclusion_status}`)
    if (evidence?.conclusion_current === false) facts.push("Conclusion superseded")
    if (evidence?.reviewer_turn_correlated === true) facts.push("Exact reviewer turn correlated")
    if (evidence?.conclusion_actor_attribution === "unavailable") facts.push("Conclusion actor unavailable")
    if (evidence?.request_delivery_is_conclusion === false) facts.push("Delivery is not a conclusion")
    if (evidence?.implementation_accepted_by_dashboard === false) facts.push("Dashboard did not accept implementation")
  }
  if (operation.type === "factory.supervision-adjust") {
    if (operation.request_evidence?.policy_adjust_requested === true) facts.push("Policy diff requested")
    if (evidence?.policy_applied === true) {
      facts.push(typeof evidence.policy_version === "number" ? `Policy v${evidence.policy_version} verified` : "Policy version verified")
    } else if (operation.request_evidence?.policy_adjust_requested === true) facts.push("Policy version not yet verified")
    if (evidence?.automation_reconciled === true) facts.push("Affected automations reconciled")
    else if (evidence?.policy_applied === true) facts.push("Automation reconciliation pending")
    if (evidence?.partial_reconciliation === true) facts.push("Partial reconciliation remains attention")
    if (evidence?.fully_reconciled === true) facts.push("Configuration fully reconciled")
    if (evidence?.direct_policy_write === false) facts.push("Dashboard direct policy writes excluded")
    if (evidence?.direct_automation_write === false) facts.push("Dashboard direct automation writes excluded")
    if (evidence?.fix_executor_actor_attribution === "unavailable") facts.push("Canonical records do not expose the execution actor")
  }
  if (operation.type === "factory.supervision-repair-mission-binding") {
    if (operation.request_evidence?.binding_repair_requested === true) facts.push("Missing-mission repair requested")
    if (operation.request_evidence?.source_authority_status === "unverified-reviewer-verification-required") facts.push("Source authority unverified; independent review required")
    if (evidence?.reviewer_authority_verified === true) facts.push("Independent source authority review verified")
    if (evidence?.binding_repaired === true) facts.push("Canonical mission binding verified")
    else if (operation.request_evidence?.binding_repair_requested === true) facts.push("Canonical binding not yet verified")
    if (evidence?.target_binding_current === true) facts.push("Target identity unchanged")
    if (evidence?.tracker_binding_current === true) facts.push("Tracker identity unchanged")
    if (evidence?.mission_source_current === true) facts.push("Mission source item and content root current")
    if (evidence?.run_project_binding_current === true) facts.push("Canonical run/project claim current")
    if (evidence?.prior_history_preserved === true) facts.push("Prior policy history preserved")
    if (evidence?.single_group_current === true) facts.push("Single canonical group verified")
    if (evidence?.mission_semantics_changed === false) facts.push("Mission semantics unchanged")
    if (evidence?.direct_policy_write === false) facts.push("Dashboard direct policy writes excluded")
    if (evidence?.direct_ledger_write === false) facts.push("Dashboard direct ledger writes excluded")
    if (evidence?.fix_executor_actor_attribution === "unavailable") facts.push("Canonical records do not expose the execution actor")
  }
  if (operation.type === "factory.supervision-repair-role-task-binding") {
    if (operation.request_evidence?.role_binding_requested === true) facts.push("Exact missing-role bind requested")
    if (operation.request_evidence?.task_created === false) facts.push("No task created")
    if (evidence?.task_postcondition_current === true) facts.push("Eligible task identity and lifecycle current")
    else if (operation.request_evidence?.role_binding_requested === true) facts.push("Task postcondition not verified")
    if (evidence?.policy_postcondition_current === true) facts.push("Canonical role binding verified")
    else if (operation.request_evidence?.role_binding_requested === true) facts.push("Policy postcondition not verified")
    if (evidence?.run_project_binding_current === true) facts.push("Canonical run/project claim current")
    else if (operation.request_evidence?.role_binding_requested === true) facts.push("Run/project postcondition not verified")
    if (evidence?.single_role_current === true) facts.push("Single-role assignment verified")
    if (evidence?.unrelated_roles_preserved === true) facts.push("Unrelated roles preserved")
    if (evidence?.automations_preserved === true) facts.push("Automations preserved")
    if (evidence?.route_gate_accepted === true && typeof evidence?.route_purpose === "string") facts.push(`Route accepted: ${evidence.route_purpose}`)
    if (evidence?.direct_policy_write === false) facts.push("Maintained bind owner used")
  }
  if (operation.type === "factory.supervision-repair-automation-binding") {
    if (operation.request_evidence?.automation_binding_requested === true) facts.push("Named automation repair requested")
    if (evidence?.automation_postcondition_current === true) facts.push("Automation owner state verified")
    else if (operation.request_evidence?.automation_binding_requested === true) facts.push("Automation owner state pending")
    if (evidence?.policy_postcondition_current === true) facts.push("Canonical policy binding verified")
    else if (operation.request_evidence?.automation_binding_requested === true) facts.push("Policy binding pending")
    if (evidence?.duplicate_role_absent === true) facts.push("No duplicate canonical role claim")
    if (evidence?.protected_automation_fields_preserved === true) facts.push("Protected automation fields preserved")
    if (evidence?.automation_binding_applied === true) facts.push("Automation binding reconciled")
    if (typeof evidence?.partial_posture === "string" && evidence.partial_posture !== "reconciled") facts.push(`Posture: ${evidence.partial_posture}`)
    if (evidence?.direct_policy_write === false) facts.push("Dashboard direct policy writes excluded")
    if (evidence?.direct_automation_write === false) facts.push("Dashboard direct automation writes excluded")
  }
  if (operation.type === "factory.supervision-mission-successor") {
    if (operation.request_evidence?.mission_successor_requested === true) facts.push("Independent successor review requested")
    if (operation.request_evidence?.source_authority_status === "unverified-reviewer-verification-required") facts.push("Direct authority and material difference unverified")
    if (evidence?.reviewer_authority_verified === true) facts.push("Independent direct-source review verified")
    if (evidence?.policy_postcondition_current === true) facts.push("Successor policy version current")
    if (evidence?.predecessor_history_preserved === true) facts.push("Predecessor history preserved")
    if (evidence?.successor_current_state_isolated === true) facts.push("Successor current state isolated")
    if (evidence?.mission_activation_pending === true) facts.push("First-work activation pending")
    if (evidence?.successor_task_created === false) facts.push("No successor task created")
    if (evidence?.mission_activation_started === false) facts.push("Work-start not claimed")
    if (evidence?.mission_successor_applied !== true && operation.request_evidence?.mission_successor_requested === true) facts.push("Successor owner postcondition pending")
    if (evidence?.direct_policy_write === false) facts.push("Dashboard direct policy writes excluded")
    if (evidence?.direct_ledger_write === false) facts.push("Dashboard direct ledger writes excluded")
  }
  if (!evidence && facts.length === 0) return null
  if (typeof evidence?.task_turn_started === "boolean") {
    facts.push(evidence.task_turn_started ? "Task/turn started" : "Task/turn not verified")
  }
  if (typeof evidence?.block_accepted === "boolean") {
    facts.push(evidence.block_accepted ? "Block accepted" : "Block not accepted")
  }
  if (typeof evidence?.outcome_verified === "boolean") {
    facts.push(evidence.outcome_verified ? "Outcome verified" : "Outcome not verified")
  }
  if (facts.length === 0) return null
  return (
    <div className="operation-truth-facts" aria-label="Operation truth">
      {facts.map((fact) => <span key={fact}>{fact}</span>)}
    </div>
  )
}

export function OperationActivityPanel({ operations }: { operations: OperationRecord[] }) {
  return (
    <div className="operation-activity" aria-label="Operation activity">
      <div className="operation-activity-label">
        <span>Activity</span>
        <strong>{operations.length}</strong>
      </div>
      {operations.length === 0 ? (
        <span className="operation-empty">No operations requested in this server session.</span>
      ) : (
        <div className="operation-activity-list">
          {operations.map((operation) => {
            const latest = operation.history.at(-1)
            return (
              <article key={operation.id}>
                <div className="operation-activity-identity">
                  <strong>{operation.type}</strong>
                  <Identity value={operation.id} />
                </div>
                <div><span>{operation.target.kind}</span><strong>{operation.target.id}</strong></div>
                <StatusMark status={operation.state} />
                <TimeValue value={latest?.observed_at} />
                <OperationFollowUp operation={operation} />
                <OperationTruthFacts operation={operation} />
                {operation.state === "applied" && (
                  <span className="operation-postcondition">Owner postcondition verified; eventual workflow outcome remains separate.</span>
                )}
                {operation.links.length > 0 && (
                  <div className="operation-result-links">
                    {operation.links.map((link) => (
                      <a href={link.href} key={`${link.label}:${link.href}`}>
                        {link.label}<ArrowUpRight aria-hidden="true" />
                      </a>
                    ))}
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function OperationFrameworkPanel() {
  const framework = useQuery({
    queryKey: ["administrative-operations"],
    queryFn: ({ signal }) => fetchOperationFramework(signal),
    refetchInterval: 15_000,
  })

  if (framework.isPending) {
    return (
      <section className="panel operation-framework-panel" aria-busy="true" aria-label="Operations">
        <QueryState kind="loading" message="Loading operation state" />
      </section>
    )
  }
  if (framework.isError) {
    return (
      <section className="panel operation-framework-panel" aria-label="Operations">
        <div className="panel-heading"><h2>Operations</h2><span className="data-state-label">Unavailable</span></div>
        <QueryState
          kind="error"
          message={framework.error instanceof Error ? framework.error.message : "Operation state is unavailable."}
          retry={() => void framework.refetch()}
        />
      </section>
    )
  }

  const data = framework.data.data.framework
  const supported = data.registered_operations.filter((item) => item.status === "supported")
  return (
    <section className="panel operation-framework-panel" aria-label="Operations">
      <div className="panel-heading">
        <div className="operation-panel-title"><ShieldCheck aria-hidden="true" /><h2>Operations</h2></div>
        <span className="data-state-label">{supported.length} available</span>
      </div>
      {supported.length === 0 && (
        <OperationDisabledReason reason="No owner-backed administrative operations are currently available." />
      )}
      <OperationActivityPanel operations={data.activity} />
    </section>
  )
}
