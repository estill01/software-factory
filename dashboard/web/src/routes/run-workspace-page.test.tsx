import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  fetchRun: vi.fn(),
  fetchTask: vi.fn(),
  fetchTasks: vi.fn(),
}))

vi.mock("@/lib/operations-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/operations-api")>()),
  fetchRun: mocks.fetchRun,
}))

vi.mock("@/lib/task-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/task-api")>()),
  fetchTask: mocks.fetchTask,
  fetchTasks: mocks.fetchTasks,
}))

import { RunWorkspace } from "@/routes/run-workspace-page"

const hash = (character: string) => character.repeat(64)
const historicalRoot = hash("a")
const currentRoot = hash("b")

const oldEvent = {
  record_id: "EVT-OLD-1",
  timestamp: "2026-08-08T10:00:00Z",
  kind: "check",
  status: "historical-check",
  severity: "info",
  category: "historical-category",
  active_block: "2",
  checkpoint: "historical-checkpoint",
  state_fingerprint: null,
  incident_id: null,
  decision_id: null,
  transition_id: null,
  phase: null,
  classification: null,
  safe_frontier: null,
  outcome: null,
  model: null,
  reasoning: null,
  summary: "HISTORICAL-EVENT-ONLY",
  action: null,
  resolution: null,
  notice_disposition: null,
  resolution_owner: null,
  user_action_required: null,
  policy_sha256: hash("c"),
  record_sha256: hash("d"),
  evidence: [],
  mission_root: historicalRoot,
  actor: { status: "unavailable", role: null, thread_id: null, reason: "No actor owner." },
  source: { path: "/history/events.jsonl", line: 1, read_only: true },
}

const run = {
  status: "available",
  target_thread_id: "target-thread-1",
  target_label: "Target one",
  observed_at: "2026-08-09T12:00:00Z",
  fingerprint: hash("e"),
  current_mission: { root: currentRoot, source_record: "CURRENT-SOURCE-RECORD", policy_sha256: hash("f") },
  project_binding: { status: "bound", project_id: "CURRENT-PROJECT", evidence: [], limitations: [] },
  event_count: 2,
  current_event_count: 1,
  predecessor_count: 1,
  lifecycle: { status: "CURRENT-LIFECYCLE", record: null },
  counts: { open_incidents: 1, open_decisions: 1, open_successor_transitions: 1, activities: 1, conclusions: 1, reports: {} },
  last_check: null,
  latest_activity: null,
  latest_conclusion: null,
  light: { posture: "red", label: "CURRENT-LIGHT", facts: [], derived: true, completion_claim: false },
  topology: {
    supervisor_group_id: hash("1"),
    implementation: { thread_id: "target-thread-1", status: "unavailable", reason: "CURRENT-IMPLEMENTATION" },
    project_binding: { status: "bound", project_id: "CURRENT-PROJECT", evidence: [], limitations: [] },
    tracker_binding: { status: "unavailable", tracker_path: null, tracker_sha256: null, reason: "CURRENT-TRACKER-BINDING" },
    roles: [{
      role: "watcher",
      label: "CURRENT-ROLE",
      thread_id: "current-role-task",
      binding_status: "bound",
      task_state: { status: "unavailable", reason: "CURRENT-TASK-STATE" },
      automation: {
        id: "CURRENT-AUTOMATION",
        status: "available",
        name: "CURRENT-AUTOMATION",
        kind: "heartbeat",
        owner_status: "ACTIVE",
        rrule: "CURRENT-RRULE",
        target_thread_id: "current-role-task",
        created_at: null,
        updated_at: null,
        next_scheduled_at: null,
        manifest_sha256: null,
        source_path: "/current/automation.toml",
        limitations: [],
        error: null,
      },
      last_activity: null,
      activity_attribution: { status: "unavailable", reason: "CURRENT-ATTRIBUTION" },
    }],
    binding_integrity: "valid",
    anomalies: ["CURRENT-ANOMALY"],
  },
  source: { identity: "supervise-tracker-runs/scripts/supervision_log.py", root: "/current", revision: hash("2"), event_head_sha256: hash("3"), policy_head_sha256: hash("4"), cache_status: "hit" },
  coverage: { status: "complete", observed: ["CURRENT-COVERAGE"], missing: [] },
  limitations: ["CURRENT-LIMITATION"],
  error: null,
  policy: {
    version: 4,
    sha256: hash("f"),
    schedule: { current: "CURRENT-SCHEDULE" },
    reports: { current: "CURRENT-REPORT-POLICY" },
    adjustable: {
      routine_minutes: 20,
      meta_review_hours: 4,
      max_sample_denominator: 6,
      cooldown_minutes: 60,
      max_escalations_per_hour: 1,
      gmail_quiet_minutes: 2,
      gmail_active_minutes: 1,
      gmail_active_window_minutes: 30,
      skill_maintenance_mode: "propose-only",
    },
    adjustment_contract: {
      fields: [
        { field: "routine_minutes", kind: "integer", minimum: 15, maximum: 60, automation_role: "watcher" },
        { field: "meta_review_hours", kind: "integer", minimum: 2, maximum: 24, automation_role: "reviewer" },
        { field: "max_sample_denominator", kind: "integer", minimum: 4, maximum: 10, automation_role: null },
        { field: "cooldown_minutes", kind: "integer", minimum: 30, maximum: 120, automation_role: null },
        { field: "max_escalations_per_hour", kind: "integer", minimum: 1, maximum: 2, automation_role: null },
        { field: "gmail_quiet_minutes", kind: "integer", minimum: 2, maximum: 10, automation_role: "gmail_gate" },
        { field: "gmail_active_minutes", kind: "integer", minimum: 1, maximum: 9, automation_role: "gmail_gate" },
        { field: "gmail_active_window_minutes", kind: "integer", minimum: 5, maximum: 120, automation_role: "gmail_gate" },
        { field: "skill_maintenance_mode", kind: "enum", minimum: null, maximum: null, automation_role: null },
      ],
      skill_maintenance_modes: ["apply-allowlisted-skill-maintenance-with-review", "apply-supervision-maintenance", "propose-only"],
    },
    automation_reconciliation: [],
    source_path: "/current/policy.json",
    read_only: true,
  },
  policy_history: [{ record_id: "POLICY-OLD", timestamp: "2026-08-08T09:00:00Z", kind: "bind", policy_version: 1, policy_sha256: hash("c"), mission_root: historicalRoot }],
  mission_segments: [
    { mission_root: historicalRoot, mission_source_record: "HISTORICAL-SOURCE-RECORD", posture: "predecessor", policy_sha256s: [hash("c")], first_recorded_at: "2026-08-08T09:00:00Z", last_recorded_at: "2026-08-08T10:00:00Z", event_count: 1, incident_count: 0, open_incident_count: 0, conclusion_count: 0, terminal_record: null, superseded_by: currentRoot },
    { mission_root: currentRoot, mission_source_record: "CURRENT-SOURCE-RECORD", posture: "current", policy_sha256s: [hash("f")], first_recorded_at: "2026-08-09T09:00:00Z", last_recorded_at: "2026-08-09T12:00:00Z", event_count: 1, incident_count: 1, open_incident_count: 1, conclusion_count: 1, terminal_record: null, superseded_by: null },
  ],
  incidents: [{ incident_id: "CURRENT-INCIDENT", open: true, head: { record_id: "EVT-CURRENT", timestamp: "2026-08-09T11:00:00Z", kind: "incident", status: "open", severity: "high", category: "CURRENT-INCIDENT-CATEGORY", summary: "CURRENT-INCIDENT-SUMMARY" } }],
  decisions: [],
  successor_transitions: [],
  activities: [oldEvent],
  activities_truncated: false,
  conclusions: [],
  conclusions_truncated: false,
  timeline: [oldEvent],
  timeline_truncated: false,
  operating_history: [{ from: "green", to: "red", trigger: "CURRENT-OPERATING-HISTORY", record: { record_id: "EVT-CURRENT", timestamp: "2026-08-09T11:00:00Z", kind: "incident", status: "open", severity: "high", category: "current", summary: "CURRENT-OPERATING-SUMMARY" } }],
  reports: [{ id: "CURRENT-REPORT", target_thread_id: "target-thread-1", family: "weekly", stage: "verified", status: "available", source_root: hash("5"), manifest_root: hash("6"), disposition: null, coverage: null, review_summary: null, verification: null, members: [], limitations: [], error: null }],
  metrics: { status: "unavailable", definition_owner: "supervise-tracker-runs/scripts/weekly_report.py", metrics: null, error: { code: "CURRENT-METRICS", message: "CURRENT-METRICS", retryable: false } },
}

describe("run mission-history boundary", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("does not render current-only supervision projections in predecessor mode", async () => {
    const historicalRun = structuredClone(run)
    historicalRun.mission_segments[0].policy_sha256s = []
    mocks.fetchRun.mockResolvedValue({ data: { run: historicalRun }, source: {}, observed_at: run.observed_at, fingerprint: hash("9"), coverage: {}, limitations: [], error: null })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <MemoryRouter initialEntries={[`/runs/target-thread-1?mission=${historicalRoot}`]}>
        <QueryClientProvider client={client}>
          <Routes><Route path="/runs/:targetId" element={<RunWorkspace />} /></Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText("Historical mission")).toBeVisible()
    expect(screen.getByText("HISTORICAL-EVENT-ONLY")).toBeVisible()
    expect(screen.getAllByText("HISTORICAL-SOURCE-RECORD").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Suppressed at succession boundary").length).toBe(2)
    expect(screen.queryByTitle(hash("f"))).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Checkpoint review" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Meta-review" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Issue follow-up" })).not.toBeInTheDocument()

    for (const sentinel of [
      "CURRENT-LIGHT",
      "CURRENT-PROJECT",
      "CURRENT-ROLE",
      "CURRENT-AUTOMATION",
      "CURRENT-REPORT",
      "CURRENT-OPERATING-HISTORY",
      "CURRENT-INCIDENT-SUMMARY",
      "CURRENT-LIMITATION",
    ]) {
      expect(screen.queryByText(sentinel, { exact: false })).not.toBeInTheDocument()
    }
    await waitFor(() => {
      expect(mocks.fetchTask).not.toHaveBeenCalled()
      expect(mocks.fetchTasks).not.toHaveBeenCalled()
    })
  })

  it("fails closed when a requested mission is not in canonical history", async () => {
    mocks.fetchRun.mockResolvedValue({ data: { run }, source: {}, observed_at: run.observed_at, fingerprint: hash("9"), coverage: {}, limitations: [], error: null })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <MemoryRouter initialEntries={[`/runs/target-thread-1?mission=${hash("9")}`]}>
        <QueryClientProvider client={client}>
          <Routes><Route path="/runs/:targetId" element={<RunWorkspace />} /></Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText("Requested mission is not present in this run's canonical history")).toBeVisible()
    expect(screen.queryByText("CURRENT-LIGHT", { exact: false })).not.toBeInTheDocument()
    expect(screen.queryByText("CURRENT-ROLE", { exact: false })).not.toBeInTheDocument()
    await waitFor(() => {
      expect(mocks.fetchTask).not.toHaveBeenCalled()
      expect(mocks.fetchTasks).not.toHaveBeenCalled()
    })
  })

  it("degrades conflicting run and target-task project claims without choosing either breadcrumb", async () => {
    mocks.fetchRun.mockResolvedValue({ data: { run }, source: {}, observed_at: run.observed_at, fingerprint: hash("9"), coverage: {}, limitations: [], error: null })
    mocks.fetchTask.mockResolvedValue({
      data: {
        task: {
          id: run.target_thread_id,
          project_binding: { status: "bound", project_id: "TASK-PROJECT", candidates: ["TASK-PROJECT"] },
        },
      },
    })
    mocks.fetchTasks.mockResolvedValue({ data: { tasks: [], next_cursor: null } })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <MemoryRouter initialEntries={[`/runs/${run.target_thread_id}`]}>
        <QueryClientProvider client={client}>
          <Routes><Route path="/runs/:targetId" element={<RunWorkspace />} /></Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )

    expect(await screen.findAllByText("Binding disagreement")).not.toHaveLength(0)
    expect(screen.getAllByText("run binding: CURRENT-PROJECT · target task: TASK-PROJECT")).toHaveLength(2)
    expect(screen.getAllByText("degraded").length).toBeGreaterThan(0)
    expect(screen.queryByRole("link", { name: "CURRENT-PROJECT" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "TASK-PROJECT" })).not.toBeInTheDocument()
    expect(screen.queryByText("Valid", { exact: true })).not.toBeInTheDocument()
  })
})
