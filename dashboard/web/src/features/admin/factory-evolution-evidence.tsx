import { Link } from "react-router"

import { Identity, StatusMark } from "@/components/workspace-ui"
import type { RunDetail } from "@/lib/operations-api"

type Workflow = RunDetail["factory_evolution_workflow"]
type Result = NonNullable<Workflow["comparison_results"]>["baseline_results"][number]

function EvidenceLinks({ ids, targetId }: { ids: string[]; targetId: string }) {
  return ids.length ? ids.map((id) => (
    <Link key={id} to={`/runs/${encodeURIComponent(targetId)}#${encodeURIComponent(id)}`}>{id}</Link>
  )) : <span>None recorded</span>
}

function ResultCell({ result, targetId }: { result: Result | undefined; targetId: string }) {
  if (!result) return <span>Unavailable</span>
  return (
    <div className="evolution-result-cell">
      <span><StatusMark status={result.outcome} />{result.evidence_class}</span>
      <p>{result.observed_effect}</p>
      <small>{result.resource_cost}</small>
      {result.regressions.length ? <small className="workspace-error-text">Regressions: {result.regressions.join("; ")}</small> : <small>No case regression recorded</small>}
      <span><Identity value={result.condition_revision} /><Identity value={result.evidence_root} /></span>
      <span className="evolution-source-links">Sources <EvidenceLinks ids={result.evidence_ids} targetId={targetId} /></span>
    </div>
  )
}

export function FactoryEvolutionEvidence({ workflow, targetId }: { workflow: Workflow; targetId: string }) {
  const plan = workflow.comparison_plan
  const results = workflow.comparison_results
  const baseline = new Map(results?.baseline_results.map((result) => [result.case_id, result]))
  const candidate = new Map(results?.candidate_results.map((result) => [result.case_id, result]))
  const caseIds = plan ? [...plan.positive_case_ids, ...plan.exception_case_ids] : []

  return (
    <div className="factory-evolution-evidence">
      {plan ? <>
        <div className="evolution-evidence-summary">
          <span>Experiment <Identity value={plan.experiment_id} /></span>
          <span>Selected <Identity value={plan.selected_candidate.candidate_id} /></span>
          <span>{plan.comparison_mode}</span>
          <span>{results ? "Verified comparison" : "Comparison planned"}</span>
          <span>{workflow.disposition ? `Disposition: ${workflow.disposition}` : "Disposition unavailable"}</span>
        </div>
        <details open={workflow.stage === "verified"}>
          <summary>Comparison evidence</summary>
          <div className="evolution-evidence-body">
            <div className="evolution-evidence-facts">
              <p><strong>Capability gap</strong>{plan.selected_candidate.capability_gap}</p>
              <p><strong>Expected effect</strong>{plan.selected_candidate.effect}</p>
              <p><strong>Selection</strong>{plan.selection_rationale}</p>
              <p><strong>Tradeoffs</strong>{plan.selected_candidate.tradeoffs.join("; ") || "None recorded"}</p>
              <p><strong>Uncertainty</strong>{plan.selected_candidate.uncertainty}</p>
              <p><strong>Protected</strong>{plan.selected_candidate.protected_capabilities.join("; ")}</p>
              <p><strong>Resource bound</strong>{plan.resource_bounds.join("; ")}</p>
              <p><strong>Stop</strong>{plan.stop_condition}</p>
            </div>
            <div className="evolution-rejected-paths">
              <strong>Compared, not selected</strong>
              {plan.rejected_paths.length ? plan.rejected_paths.map((path) => (
                <div key={path.candidate_id}>
                  <span><Identity value={path.candidate_id} /> · {path.candidate_type}</span>
                  <p>{path.effect}</p>
                  <small>{path.tradeoffs.join("; ") || path.uncertainty}</small>
                </div>
              )) : <span>None — the owner evaluated one candidate.</span>}
            </div>
            {results ? <>
              <div className="table-scroll">
                <table className="report-data-table evolution-comparison-table">
                  <caption className="sr-only">Source-backed baseline and candidate comparison</caption>
                  <thead><tr><th>Case</th><th>Baseline</th><th>Candidate</th></tr></thead>
                  <tbody>{caseIds.map((caseId) => <tr key={caseId}><th>{caseId}<small>{plan.exception_case_ids.includes(caseId) ? "Exception" : "Positive"}</small></th><td><ResultCell result={baseline.get(caseId)} targetId={targetId} /></td><td><ResultCell result={candidate.get(caseId)} targetId={targetId} /></td></tr>)}</tbody>
                </table>
              </div>
              <div className="evolution-evidence-facts">
                <p><strong>Evaluation</strong>{results.rationale}</p>
                <p><strong>Regression findings</strong>{results.regression_findings.join("; ") || "None recorded in the verified evaluation"}</p>
                <p><strong>Contrary evidence</strong><span className="evolution-source-links"><EvidenceLinks ids={results.contrary_evidence_ids} targetId={targetId} /></span></p>
              </div>
            </> : <div className="workspace-partial">Baseline/candidate results are unavailable until the separate implementation owner supplies exact evidence and the independent evaluator records every planned case.</div>}
          </div>
        </details>
      </> : <div className="workspace-partial">Comparison plan unavailable at the current source stage.</div>}
      <div className="evolution-recovery"><strong>Recovery · {workflow.recovery.posture}</strong><span>{workflow.recovery.guidance}</span>{workflow.recovery.preserved_roots.map((root) => <Identity key={root} value={root} />)}</div>
      <div className="evolution-limitations">{workflow.limitations.map((limitation) => <small key={limitation}>{limitation}</small>)}</div>
    </div>
  )
}
