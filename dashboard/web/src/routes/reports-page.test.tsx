import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  fetchMetrics: vi.fn(),
  fetchReport: vi.fn(),
  fetchReportArtifactText: vi.fn(),
  fetchReports: vi.fn(),
  fetchProjects: vi.fn(),
}))

vi.mock("@/lib/operations-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/operations-api")>()),
  fetchMetrics: mocks.fetchMetrics,
  fetchReport: mocks.fetchReport,
  fetchReportArtifactText: mocks.fetchReportArtifactText,
  fetchReports: mocks.fetchReports,
}))
vi.mock("@/lib/projects-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/projects-api")>()),
  fetchProjects: mocks.fetchProjects,
}))

import { Component as ReportsPage } from "@/routes/reports-page"

const hash = (character: string) => character.repeat(64)
const observedAt = "2026-08-10T06:00:00.000Z"

function metricRun(index: number, projectId: string) {
  const target = `target-thread-${index.toString().padStart(4, "0")}`
  return {
    target_thread_id: target,
    target_label: `${projectId} implementation`,
    supervisor_group_id: hash(String(index)),
    project_binding: { status: "bound", project_id: projectId, evidence: [], limitations: [] },
    observed_at: observedAt,
    current_mission_root: hash(String(index)),
    lifecycle: { status: null, record: null },
    light: { posture: index === 2 ? "red" : "amber", label: "Review", facts: [], derived: true, completion_claim: false },
    operating_history: [],
    conclusion_counts: { by_kind: { "meta-review": index }, by_category: { review: index } },
    report_counts: { "weekly:available": 2 },
    status: "available",
    cost_label: "API-equivalent estimate",
    metrics: {
      schema_version: 1,
      kind: "supervision-weekly-review",
      report_id: `current-${index}`,
      target_label: `${projectId} implementation`,
      coverage: { start: "2026-08-09T00:00:00Z", end: observedAt, timezone: "America/Los_Angeles", calendar_days: ["2026-08-09"], elapsed_hours: 30, partial_week: true },
      source: { source_root: hash(String(index)), event_count: 10 * index, first_record_id: `EVT-${index}01`, last_record_id: `EVT-${index}99`, policy_record_count: 1, policy_sha256_at_generation: hash(String(index)), projection_inventory: {} },
      headline: { recorded_events: 10 * index, changed_state_routes: index, incidents_opened: index, incidents_terminal: index - 1, incidents_open_at_end: 1, incidents_open_high_or_critical: index === 2 ? 1 : 0, corrections_issued: index, max_samples: index, roundups: 0, blocks_observed: index, tooling_change_records: 0 },
      rates: { incidents_per_100_changed_state_routes: 100, terminal_share_of_opened_percent: 50, incident_detection_to_terminal_median_hours: 2, incident_detection_to_terminal_p90_hours: 3, denominator_note: "Exact recorded-event denominator." },
      availability: { report_period_hours: 30, observed_event_span_hours: 24, core_heartbeats_scheduled_active_hours: 24, core_heartbeats_explicitly_paused_hours: 0, core_heartbeats_scheduled_active_percent: 80, explicit_pause_intervals: [], recorded_target_read_successes: 1, recorded_target_read_failures: 0, recorded_target_read_availability_percent: 100, continuous_process_uptime_measured: false, interpretation: "Recorded checks only." },
      daily_activity: [{ date: "2026-08-09", mechanical: index, review: index, routing: 0, intervention: 0, communication: 0, maintenance: 0, other: 0 }],
      daily_incidents: [{ date: "2026-08-09", opened: index, terminal: index - 1 }],
      counts: { by_kind: { heartbeat: index, decision: index, resolution: index }, by_status: { completed: index }, by_severity: { low: index }, by_category: { review: index }, by_model_reasoning: { "gpt-5 / high": index } },
      monitoring_roles: { configured_thread_count: 1, core_role_count: 1, support_role_count: 0, roles: [{ role: "reviewer", purpose: "Semantic reviewer", configured: true, recorded_action_count: index, activity_label: "Recorded category only" }], interpretation: "Roles are configured identities, not inferred event actors." },
      limitations: ["Recorded activity is a lower bound."],
      resource_estimate: {
        daily: [{ date: "2026-08-09", estimated_tokens_base: 1_000 * index, projected_cost_usd_base: index }],
        totals: { estimated_tokens_base: 1_000 * index, projected_cost_usd_base: index, recorded_model_attributed_events: index },
      },
    },
    error: null,
  }
}

const runs = [metricRun(1, "alpha"), metricRun(2, "beta"), metricRun(3, "gamma")]
const projects = ["alpha", "beta", "gamma"].map((id) => ({ id, label: id[0].toUpperCase() + id.slice(1) }))
const factoryHistory = {
  posture_transition_count: 1,
  supervisor_group_count: 3,
  bound_project_count: 3,
  availability: { status: "available", scheduled_active_hours: 72, explicitly_paused_hours: 2 },
  posture_transitions: [{ target_thread_id: runs[1].target_thread_id, target_label: runs[1].target_label, project_id: "beta", from: "amber", to: "red", trigger: "open-high-or-critical-incident", record: { record_id: "EVT-1", timestamp: observedAt } }],
  unsupported: ["Historical concurrent implementation count is unavailable."],
}

function metricsResponse(perRun: Array<Record<string, unknown>> = runs) {
  return {
    coverage: { status: "partial" },
    data: { per_run: perRun, factory_history: factoryHistory },
  }
}

function weeklyReport(id: string, end: string, status: "available" | "unavailable" = "available") {
  return {
    id,
    target_thread_id: "target-thread-0001",
    family: "weekly",
    stage: status === "available" ? "verified" : "partial",
    status,
    source_root: status === "available" ? hash("a") : null,
    manifest_root: status === "available" ? hash("b") : null,
    disposition: status === "available" ? "effective-with-findings" : null,
    coverage: status === "available" ? { start: "2026-08-01T00:00:00Z", end, timezone: "America/Los_Angeles", calendar_days: ["2026-08-01"], elapsed_hours: 24, partial_week: true } : null,
    review_summary: status === "available" ? { headline: "Exact review", assessment: "Evidence-bound assessment." } : null,
    verification: status === "available" ? { valid: true, report_id: id, source_root: hash("a"), manifest_root: hash("b"), page_count: 2, pdf_path: "/report.pdf", report_sha256: hash("c"), review_sha256: hash("d"), pdf_sha256: hash("e") } : null,
    members: [],
    delivery: status === "available"
      ? { status: "delivered", configured: true, retryable: false, record_id: "EVT-DELIVERY", message_id: "gmail-message", thread_id: "gmail-thread", reason: null }
      : { status: "not-ready", configured: false, retryable: false, record_id: null, message_id: null, thread_id: null, reason: "Report is not verified." },
    limitations: ["Recorded activity is a lower bound."],
    error: status === "unavailable" ? { code: "report_verification_failed", message: "Manifest mismatch", retryable: false } : null,
  }
}

const reports = [
  weeklyReport("weekly-one", "2026-08-08T00:00:00Z"),
  weeklyReport("weekly-two", "2026-08-09T00:00:00Z"),
  weeklyReport("weekly-invalid", "2026-08-10T00:00:00Z", "unavailable"),
]

const evolutionWorkflows = [{
  target_thread_id: runs[0].target_thread_id,
  target_label: runs[0].target_label,
  project_binding: runs[0].project_binding,
  workflow: {
    status: "available",
    stage: "awaiting-implementation",
    next_action: "evaluate",
    actionable: true,
    evolution_id: "evolution-test-001",
    packet_id: "packet-test-001",
    packet_root: hash("4"),
    review_id: "review-test-001",
    review_root: hash("5"),
    evaluation_id: null,
    evaluation_root: null,
    disposition: null,
    source_report_id: "weekly-one",
    source_report_root: hash("a"),
    event_head_sha256: hash("6"),
    manifest_root: hash("7"),
    fingerprint: hash("8"),
    proposer: { role: "base_reviewer", task_id: "proposer-task" },
    implementer: { status: "awaiting-owner-proof", task_id: runs[0].target_thread_id, baseline_revision: "1".repeat(40), candidate_revision: "2".repeat(40) },
    evaluator: { role: "reviewer", task_id: "evaluator-task" },
    expected_members: [],
    members: [],
    stages: [
      { id: "prepare", label: "Deterministic prepare", status: "complete", owner: "factory owner" },
      { id: "finalize", label: "Cognitive finalize", status: "complete", owner: "proposer-task" },
      { id: "external-implementation", label: "External implementation", status: "current", owner: "Block 11" },
      { id: "evaluate", label: "Independent evaluate", status: "pending", owner: "evaluator-task" },
      { id: "verify", label: "Deterministic verify", status: "pending", owner: "factory owner" },
    ],
    limitations: ["Disposition is not adoption authority."],
    error: null,
  },
}]

function reportDetail(report: ReturnType<typeof weeklyReport>, recordedEvents: number) {
  const run = runs[0]
  return {
    data: {
      report: {
        ...report,
        metric_summary: {
          ...run.metrics,
          report_id: report.id,
          headline: { ...run.metrics.headline, recorded_events: recordedEvents },
        },
        artifacts: report.status === "available" ? [
          { name: "report.md", path: "/source/report.md", media_type: "text/markdown", bytes: 100, sha256: hash("1"), read_only: true, previewable: true, preview_url: `/api/v1/reports/${report.target_thread_id}/weekly/${report.id}/artifacts/report.md`, download_url: `/api/v1/reports/${report.target_thread_id}/weekly/${report.id}/artifacts/report.md?download=true` },
          { name: "report.pdf", path: "/source/report.pdf", media_type: "application/pdf", bytes: 200, sha256: hash("2"), read_only: true, previewable: true, preview_url: `/api/v1/reports/${report.target_thread_id}/weekly/${report.id}/artifacts/report.pdf`, download_url: `/api/v1/reports/${report.target_thread_id}/weekly/${report.id}/artifacts/report.pdf?download=true` },
        ] : [],
      },
    },
  }
}

function renderReports(entry = "/reports") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <QueryClientProvider client={client}>
        <Routes><Route path="/reports" element={<ReportsPage />} /></Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe("metrics and report history workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchProjects.mockResolvedValue({ data: { projects } })
    mocks.fetchMetrics.mockResolvedValue(metricsResponse())
    mocks.fetchReports.mockResolvedValue({ coverage: { status: "partial" }, data: { reports, evolution_workflows: evolutionWorkflows } })
    mocks.fetchReport.mockImplementation((_target: string, _family: string, id: string) => Promise.resolve(reportDetail(reports.find((report) => report.id === id)!, id === "weekly-one" ? 10 : 16)))
    mocks.fetchReportArtifactText.mockResolvedValue("# Exact report\n\n<script>not executable</script>")
  })

  it("shows decision-grade metric groups and filters three exact project/run projections", async () => {
    const user = userEvent.setup()
    renderReports()

    expect(await screen.findByRole("region", { name: "Delivery" })).toHaveTextContent("60")
    expect(screen.getByRole("region", { name: "Resources" })).toHaveTextContent("API-equivalent estimate")
    expect(screen.getByRole("heading", { name: "Trend" })).toBeVisible()
    expect(screen.getByRole("heading", { name: "Runs" })).toBeVisible()
    const contract = screen.getByRole("region", { name: "Metric contract and sources" })
    expect(contract).toHaveTextContent("supervision-weekly-review · schema v1")
    expect(contract).toHaveTextContent("Exact recorded-event denominator.")
    expect(contract).toHaveTextContent("Semantic reviewer (reviewer)")
    expect(contract).toHaveTextContent("review 6")
    const trendTable = screen.getByRole("table", { name: "Exact accessible values and sources for the metric trend" })
    expect(within(trendTable).getAllByRole("link", { name: /metric/ })).toHaveLength(3)
    expect(within(trendTable).getByRole("link", { name: "EVT-101–EVT-199" })).toHaveAttribute(
      "href",
      "/runs/target-thread-0001#EVT-199",
    )
    expect(screen.getByRole("link", { name: "Events EVT-101–EVT-199" })).toHaveAttribute(
      "href",
      "/runs/target-thread-0001#EVT-199",
    )
    expect(screen.getByText("Historical concurrent implementation count is unavailable.")).toBeVisible()
    expect(screen.getAllByRole("link", { name: "alpha implementation" })[0]).toBeVisible()
    expect(screen.getAllByRole("link", { name: "beta implementation" })[0]).toBeVisible()
    expect(screen.getAllByRole("link", { name: "gamma implementation" })[0]).toBeVisible()

    await user.selectOptions(screen.getByLabelText("Project"), "beta")
    expect(screen.queryByRole("link", { name: "alpha implementation" })).not.toBeInTheDocument()
    expect(screen.getAllByRole("link", { name: "beta implementation" })[0]).toBeVisible()
  })

  it("keeps invalid history visible, previews verified content safely, and compares only exact contracts", async () => {
    const user = userEvent.setup()
    renderReports("/reports?view=reports")

    expect(await screen.findByRole("heading", { name: "History" })).toBeVisible()
    const evolution = screen.getByRole("heading", { name: "Evolution" }).closest("section")!
    expect(evolution).toHaveTextContent("awaiting-implementation")
    expect(evolution).toHaveTextContent("External implementation: awaiting-owner-proof")
    expect(evolution).toHaveTextContent("not performed by evolution")
    expect(screen.getByText("Manifest mismatch")).toBeVisible()
    await user.click(screen.getByRole("button", { name: /weekly-one/ }))
    expect(await screen.findByRole("heading", { name: "Detail" })).toBeVisible()
    const markdownRow = screen.getByText("report.md").closest("div")!
    await user.click(within(markdownRow).getByRole("button", { name: "Preview" }))
    expect(await screen.findByText("Exact report")).toBeVisible()
    expect(screen.getByText("<script>not executable</script>")).toBeVisible()
    expect(document.querySelector("script")).toBeNull()
    expect(screen.queryByRole("button", { name: /generate|adopt|accept/i })).not.toBeInTheDocument()

    const selects = screen.getAllByRole("checkbox", { name: "Select" })
    await user.click(selects[0])
    await user.click(selects[1])
    await waitFor(() => expect(screen.getByRole("heading", { name: "Compare" })).toBeVisible())
    expect(screen.getByText("compatible", { exact: false })).toBeVisible()
    expect(screen.getByRole("row", { name: /recorded events 10 16 \+6/i })).toBeVisible()
  })

  it("counts distinct supervisor group identities instead of run rows", async () => {
    const duplicateGroupRuns = [
      runs[0],
      { ...runs[1], supervisor_group_id: runs[0].supervisor_group_id },
      runs[2],
    ]
    mocks.fetchMetrics.mockResolvedValue(metricsResponse(duplicateGroupRuns))
    renderReports()

    const history = (await screen.findByRole("heading", { name: "Factory history" })).closest("section")!
    expect(history).toHaveTextContent("2 supervisor groups")
  })

  it("does not combine source-day buckets across incompatible timezones", async () => {
    const user = userEvent.setup()
    const mixedRuns = runs.map((run, index) => index === 2 && run.status === "available"
      ? { ...run, metrics: { ...run.metrics, coverage: { ...run.metrics.coverage, timezone: "UTC" } } }
      : run)
    mocks.fetchMetrics.mockResolvedValue(metricsResponse(mixedRuns))
    renderReports()

    expect(await screen.findByText("Select one run or an exact shared definition, period, timezone, partial-window, and denominator contract. Incompatible metrics were not combined.")).toBeVisible()
    expect(screen.queryByRole("table", { name: "Exact accessible values and sources for the metric trend" })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Timezone"), "America/Los_Angeles")
    expect(await screen.findByRole("table", { name: "Exact accessible values and sources for the metric trend" })).toBeVisible()
  })

  it("withholds aggregate values when schema or coverage contracts differ", async () => {
    const mixedContracts = runs.map((run, index) => index === 1 && run.status === "available"
      ? { ...run, metrics: { ...run.metrics, schema_version: 2 } }
      : run)
    mocks.fetchMetrics.mockResolvedValue(metricsResponse(mixedContracts))
    renderReports()

    const delivery = await screen.findByRole("region", { name: "Delivery" })
    expect(delivery).toHaveTextContent("Incomparable")
    expect(delivery).not.toHaveTextContent("60")
    expect(screen.getByRole("region", { name: "Metric contract and sources" })).toHaveTextContent("2 incompatible or unavailable contracts")
    expect(screen.queryByRole("table", { name: "Exact accessible values and sources for the metric trend" })).not.toBeInTheDocument()
  })

  it("renders wholly unavailable metrics as unavailable rather than zero", async () => {
    const unavailableRuns = runs.map((run) => ({
      ...run,
      status: "unavailable",
      metrics: null,
      error: { code: "metric_projection_failed", message: "Exact metric unavailable", retryable: false },
    }))
    mocks.fetchMetrics.mockResolvedValue(metricsResponse(unavailableRuns))
    renderReports()

    const delivery = await screen.findByRole("region", { name: "Delivery" })
    const resources = screen.getByRole("region", { name: "Resources" })
    expect(delivery).toHaveTextContent("Unavailable")
    expect(delivery).not.toHaveTextContent(/Recorded events\s*0/)
    expect(resources).not.toHaveTextContent("$0")
    expect(screen.getByText("No available metric projection matches the filters; unavailable values were not rendered as zero")).toBeVisible()
  })

  it("bounds long trend history with transparent contiguous aggregation", async () => {
    const longActivity = Array.from({ length: 120 }, (_, offset) => {
      const date = new Date(Date.UTC(2026, 0, 1 + offset)).toISOString().slice(0, 10)
      return { date, mechanical: 1, review: 0, routing: 0, intervention: 0, communication: 0, maintenance: 0, other: 0 }
    })
    const longRun = {
      ...runs[0],
      metrics: {
        ...runs[0].metrics,
        daily_activity: longActivity,
        daily_incidents: longActivity.map(({ date }) => ({ date, opened: 0, terminal: 0 })),
        resource_estimate: {
          ...runs[0].metrics.resource_estimate,
          daily: longActivity.map(({ date }) => ({ date, estimated_tokens_base: 1, projected_cost_usd_base: 0 })),
        },
      },
    }
    mocks.fetchMetrics.mockResolvedValue(metricsResponse([longRun]))
    renderReports()

    const trend = await screen.findByRole("region", { name: "Trend" })
    expect(within(trend).getByText("60 displayed buckets from 120 source days", { exact: false })).toBeVisible()
    expect(within(trend).getByText("summed into contiguous buckets of at most 2 days", { exact: false })).toBeVisible()
    expect(within(trend).getByRole("table", { name: "Exact accessible values and sources for the metric trend" })).toBeVisible()
  })

  it("rejects raw count deltas when report coverage durations differ", async () => {
    const user = userEvent.setup()
    mocks.fetchReport.mockImplementation((_target: string, _family: string, id: string) => {
      const detail = reportDetail(reports.find((report) => report.id === id)!, id === "weekly-one" ? 10 : 16)
      if (id === "weekly-two" && detail.data.report.metric_summary) {
        detail.data.report.metric_summary.coverage = {
          ...detail.data.report.metric_summary.coverage,
          elapsed_hours: 48,
        }
      }
      return Promise.resolve(detail)
    })
    renderReports("/reports?view=reports")

    expect(await screen.findByRole("heading", { name: "History" })).toBeVisible()
    const selects = screen.getAllByRole("checkbox", { name: "Select" })
    await user.click(selects[0])
    await user.click(selects[1])
    expect(await screen.findByText("Coverage durations or partial-window postures differ. No numeric delta was computed.")).toBeVisible()
    expect(screen.queryByRole("row", { name: /recorded events 10 16 \+6/i })).not.toBeInTheDocument()
  })
})
