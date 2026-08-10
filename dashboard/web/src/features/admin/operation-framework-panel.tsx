import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ArrowUpRight, ShieldCheck, X } from "lucide-react"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
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
  busy = false,
  onConfirm,
  onCancel,
  onRefresh,
}: {
  preview: OperationPreviewEnvelope
  request: OperationPreviewRequest
  suppliedFacts?: Array<[string, string]>
  staleReason?: string | null
  busy?: boolean
  onConfirm: (confirmation: { class: string; value: string }) => void
  onCancel: () => void
  onRefresh?: () => void
}) {
  const [value, setValue] = useState("")
  const operation = preview.data.operation
  const confirmation = operation.preview.confirmation
  const matches = value === confirmation.expected_value

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
          <div><dt>Gate</dt><dd><StatusMark status={operation.preview.route_gate.status} /></dd></div>
          <div><dt>Source</dt><dd><Identity value={operation.preview.source_fingerprint} /></dd></div>
          <div><dt>Expires</dt><dd><TimeValue value={operation.preview.expires_at} /></dd></div>
        </dl>

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

        {staleReason ? (
          <div className="operation-stale" role="alert">
            <AlertTriangle aria-hidden="true" />
            <div><strong>Preview is stale</strong><span>{staleReason}</span></div>
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
            disabled={Boolean(staleReason) || !matches || busy}
            onClick={() => onConfirm({ class: confirmation.class, value })}
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
