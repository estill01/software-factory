import { fireEvent, render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"

import { FactoryEvolutionEvidence } from "@/features/admin/factory-evolution-evidence"
import type { RunDetail } from "@/lib/operations-api"

const hash = "a".repeat(64)

function workflow(
  disposition: "promote" | "advisory" | "revise" | "reject" | null = "advisory",
  withResults = true,
): RunDetail["factory_evolution_workflow"] {
  return {
    status: "available",
    stage: withResults ? "verified" : "awaiting-implementation",
    next_action: withResults ? null : "evaluate",
    actionable: !withResults,
    evolution_id: "evolution-test-001",
    packet_id: "packet-test-001",
    packet_root: hash,
    review_id: "review-test-001",
    review_root: hash,
    evaluation_id: withResults ? "evaluation-test-001" : null,
    evaluation_root: withResults ? hash : null,
    disposition: withResults ? disposition : null,
    comparison_plan: {
      experiment_id: "experiment-test-001",
      selected_candidate: {
        candidate_id: "candidate-selected",
        candidate_type: "skill-method",
        capability_gap: "The workspace omitted the verified comparison.",
        effect: "Expose exact comparison evidence.",
        protected_capabilities: ["Maintained evolution owner"],
        applicability: "Consequential Factory changes.",
        tradeoffs: ["Requires an independent evaluator."],
        uncertainty: "Evidence covers one bounded cycle.",
      },
      rejected_paths: [{
        candidate_id: "candidate-detector",
        candidate_type: "detector",
        capability_gap: "The same workspace gap.",
        effect: "Detect the omission without exposing evidence.",
        protected_capabilities: ["Maintained evolution owner"],
        applicability: "Detection only.",
        tradeoffs: ["Leaves the operator without a comparison."],
        uncertainty: "Underreach remains.",
      }],
      selection_rationale: "The selected path provides the bounded operator capability.",
      dimensions_considered: ["effect", "recurrence", "reach", "compounding_value", "reliability", "product_gain", "evidence_strength", "cost", "regression_risk", "complexity", "reversibility", "time_to_evidence"],
      comparison_mode: "improvement",
      positive_case_ids: ["case-positive"],
      exception_case_ids: ["case-exception"],
      expected_effects: ["Both exact cases become inspectable."],
      resource_bounds: ["Two paired cases and one evaluator."],
      rollback_condition: "Do not adopt when regression evidence exists.",
      success_measures: ["Every case has an exact result."],
      regression_measures: ["No second owner or write path."],
      stop_condition: "Stop after one disposition.",
      minimum_expected_delta: "Candidate improves at least one exact case.",
      non_inferiority_justification: "",
    },
    comparison_results: withResults ? {
      baseline_results: [
        { case_id: "case-positive", evidence_class: "observed", evidence_ids: ["EVT-BASE"], outcome: "fail", observed_effect: "Baseline omitted the comparison.", resource_cost: "One bounded case.", regressions: [], condition_revision: "1".repeat(40), evidence_root: "1".repeat(64) },
        { case_id: "case-exception", evidence_class: "observed", evidence_ids: ["EVT-EXCEPTION"], outcome: "mixed", observed_effect: "Baseline exposed only roots.", resource_cost: "One bounded case.", regressions: [], condition_revision: "1".repeat(40), evidence_root: "2".repeat(64) },
      ],
      candidate_results: [
        { case_id: "case-positive", evidence_class: "observed", evidence_ids: ["EVT-CANDIDATE"], outcome: "pass", observed_effect: "Candidate exposed the exact comparison.", resource_cost: "One bounded case.", regressions: [], condition_revision: "2".repeat(40), evidence_root: "3".repeat(64) },
        { case_id: "case-exception", evidence_class: "shadow", evidence_ids: ["EVT-CONTRARY"], outcome: "mixed", observed_effect: "Exception remains advisory.", resource_cost: "One bounded case.", regressions: ["One exception remains."], condition_revision: "2".repeat(40), evidence_root: "4".repeat(64) },
      ],
      contrary_evidence_ids: ["EVT-CONTRARY"],
      regression_findings: ["One exception remains."],
      rationale: "Keep the disposition non-adoptive while the exception remains.",
    } : null,
    source_report_id: "weekly-test-001",
    source_report_root: hash,
    event_head_sha256: hash,
    manifest_root: hash,
    fingerprint: hash,
    proposer: { role: "base_reviewer", task_id: "proposer-task" },
    implementer: { status: withResults ? "evaluation-evidence-recorded" : "awaiting-owner-proof", task_id: "target-thread-001", baseline_revision: "1".repeat(40), candidate_revision: "2".repeat(40) },
    evaluator: { role: "reviewer", task_id: "evaluator-task" },
    expected_members: [],
    members: [],
    stages: [],
    limitations: ["Evolution does not adopt or deploy the candidate."],
    recovery: { posture: withResults ? "not-required" : "blocked", guidance: withResults ? "Retain the immutable disposition." : "Retain the review and await external evidence.", preserved_roots: [hash] },
    error: null,
  }
}

function renderEvidence(value: RunDetail["factory_evolution_workflow"]) {
  return render(<MemoryRouter><FactoryEvolutionEvidence workflow={value} targetId="target-thread-001" /></MemoryRouter>)
}

describe("FactoryEvolutionEvidence", () => {
  it("keeps a planned comparison explicitly partial while preserving rejected paths and recovery", () => {
    renderEvidence(workflow(null, false))
    expect(screen.getByText("Comparison planned")).toBeVisible()
    expect(screen.getByText("Disposition unavailable")).toBeVisible()
    fireEvent.click(screen.getByText("Comparison evidence"))
    expect(screen.getByText(/Baseline\/candidate results are unavailable/)).toBeVisible()
    expect(screen.getByText("candidate-detector")).toBeVisible()
    expect(screen.getByText(/Recovery · blocked/)).toBeVisible()
  })

  it.each(["advisory", "revise", "reject"] as const)("renders %s evidence without converting it into adoption", (disposition) => {
    renderEvidence(workflow(disposition))
    expect(screen.getByText(`Disposition: ${disposition}`)).toBeVisible()
    const table = screen.getByRole("table", { name: "Source-backed baseline and candidate comparison" })
    expect(within(table).getByText("Baseline omitted the comparison.")).toBeVisible()
    expect(within(table).getByText("Candidate exposed the exact comparison.")).toBeVisible()
    expect(screen.getAllByText("One exception remains.").length).toBeGreaterThan(0)
    expect(screen.getAllByRole("link", { name: "EVT-CONTRARY" })[0]).toHaveAttribute("href", "/runs/target-thread-001#EVT-CONTRARY")
    expect(screen.getByText(/Evolution does not adopt or deploy/)).toBeVisible()
  })

  it("labels a missing plan and unavailable recovery instead of inventing comparison evidence", () => {
    const missing = { ...workflow(null, false), status: "unavailable" as const, stage: "unavailable" as const, next_action: null, actionable: false, comparison_plan: null, recovery: { posture: "unavailable" as const, guidance: "Verified review source is unavailable.", preserved_roots: [] } }
    renderEvidence(missing)
    expect(screen.getByText("Comparison plan unavailable at the current source stage.")).toBeVisible()
    expect(screen.getByText("Verified review source is unavailable.")).toBeVisible()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
  })
})
