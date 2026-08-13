import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router"

import { Identity, QueryState, StatusMark } from "@/components/workspace-ui"
import { FactoryEvolutionEvidence } from "@/features/admin/factory-evolution-evidence"
import { fetchReports } from "@/lib/operations-api"

export function FactoryEvolutionPanel() {
  const query = useQuery({
    queryKey: ["reports"],
    queryFn: ({ signal }) => fetchReports(signal),
  })

  if (query.isPending) return <QueryState kind="loading" message="Loading Factory evolution" />
  if (query.isError) return <QueryState kind="error" message={query.error.message} retry={() => void query.refetch()} />

  const workflows = query.data.data.evolution_workflows
  return (
    <section className="workspace-panel factory-evolution-admin" aria-label="Factory evolution">
      <div className="workspace-panel-heading"><strong>Factory evolution</strong><span>{workflows.length} source projection{workflows.length === 1 ? "" : "s"}</span></div>
      {workflows.length ? <div className="workspace-record-list">{workflows.map(({ target_thread_id: targetId, target_label: targetLabel, workflow }) => (
        <article className="workspace-record" key={targetId}>
          <div><Link to={`/runs/${encodeURIComponent(targetId)}`}>{targetLabel}</Link><Identity value={targetId} /></div>
          <StatusMark status={workflow.stage} />
          <span>{workflow.next_action ?? (workflow.disposition ? `Disposition: ${workflow.disposition}` : "No current stage action")}</span>
          <span>{workflow.stages.map((stage) => `${stage.label}: ${stage.status}`).join(" · ") || workflow.error?.message || "Source unavailable"}</span>
          <Identity value={workflow.packet_root} />
          <small>External implementation: {workflow.implementer.status}. Evolution performs no adoption, installation, routing, scheduling, deployment, rollback, or outcome mutation.</small>
          <FactoryEvolutionEvidence workflow={workflow} targetId={targetId} />
        </article>
      ))}</div> : <QueryState kind="empty" message="No Factory-evolution source projection" />}
    </section>
  )
}
