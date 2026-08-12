import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  previewOperation: vi.fn(),
  executeOperation: vi.fn(),
  cancelOperation: vi.fn(),
}))

vi.mock("@/lib/admin-operations-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/admin-operations-api")>()),
  previewOperation: mocks.previewOperation,
  executeOperation: mocks.executeOperation,
  cancelOperation: mocks.cancelOperation,
}))

import {
  ProjectWorkflowActions,
  RunCheckAction,
  RunSupervisionActions,
  TaskWorkflowActions,
  TrackerWorkflowActions,
} from "@/features/admin/factory-workflow-actions"
import type { OperationPreviewEnvelope } from "@/lib/admin-operations-api"
import { DashboardApiError } from "@/lib/api"
import type { RunDetail } from "@/lib/operations-api"
import type { ProjectProjection } from "@/lib/projects-api"
import type { TaskDetailEnvelope } from "@/lib/task-api"
import type { TrackerDetail, TrackerSummary } from "@/lib/trackers-api"

const hash = "a".repeat(64)
const head = "b".repeat(40)

const policy = {
  version: 5,
  sha256: hash,
  schedule: { routine_minutes: 20, meta_review_hours: 4 },
  reports: {},
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
      ["routine_minutes", "integer", 15, 60, "watcher"],
      ["meta_review_hours", "integer", 2, 24, "reviewer"],
      ["max_sample_denominator", "integer", 4, 10, null],
      ["cooldown_minutes", "integer", 30, 120, null],
      ["max_escalations_per_hour", "integer", 1, 2, null],
      ["gmail_quiet_minutes", "integer", 2, 10, "gmail_gate"],
      ["gmail_active_minutes", "integer", 1, 9, "gmail_gate"],
      ["gmail_active_window_minutes", "integer", 5, 120, "gmail_gate"],
      ["skill_maintenance_mode", "enum", null, null, null],
    ].map(([field, kind, minimum, maximum, automation_role]) => ({
      field,
      kind,
      minimum,
      maximum,
      automation_role,
    })),
    skill_maintenance_modes: [
      "apply-allowlisted-skill-maintenance-with-review",
      "apply-supervision-maintenance",
      "propose-only",
    ],
  },
  automation_reconciliation: [
    {
      field: "routine_minutes",
      role: "watcher",
      automation_id: "watcher-automation",
      expected_rrule: "RRULE:FREQ=MINUTELY;INTERVAL=20",
      actual_rrule: "RRULE:FREQ=MINUTELY;INTERVAL=20",
      owner_status: "ACTIVE",
      target_thread_id: "watcher-task",
      actual_timezone: "not-applicable-to-interval-schedule",
      duplicate_coverage: "exact",
      active_target_owner_ids: ["watcher-automation"],
      mode: null,
      state: "reconciled",
      reason: "Policy cadence and actual active automation agree.",
    },
    {
      field: "meta_review_hours",
      role: "reviewer",
      automation_id: "reviewer-automation",
      expected_rrule: "RRULE:FREQ=HOURLY;INTERVAL=4",
      actual_rrule: "RRULE:FREQ=HOURLY;INTERVAL=4",
      owner_status: "ACTIVE",
      target_thread_id: "reviewer-task",
      actual_timezone: "not-applicable-to-interval-schedule",
      duplicate_coverage: "exact",
      active_target_owner_ids: ["reviewer-automation"],
      mode: null,
      state: "reconciled",
      reason: "Policy cadence and actual active automation agree.",
    },
  ],
  source_path: "/supervision/task-demo/policy.json",
  read_only: true,
} as unknown as NonNullable<RunDetail["policy"]>

const weeklyReportWorkflow = {
  status: "available",
  stage: "delivery",
  next_action: "deliver",
  actionable: true,
  report_id: "weekly-20260801-20260808-test",
  coverage: {
    start: "2026-08-01T00:00:00+00:00",
    end: "2026-08-08T00:00:00+00:00",
    timezone: "America/Los_Angeles",
    calendar_days: ["2026-08-01"],
    elapsed_hours: 168,
    partial_week: false,
  },
  coverage_days: 7,
  timezone: "America/Los_Angeles",
  source_root: hash,
  manifest_root: hash,
  fingerprint: hash,
  writer_role: "roundup_writer",
  writer_task_id: "roundup-writer-task",
  expected_members: ["metrics.json", "review-packet.json", "review.json", "report.json", "report.md", "report.pdf", "manifest.json"],
  members: [],
  stages: [
    { id: "prepare", label: "Prepare", status: "complete", owner: "weekly owner" },
    { id: "source-currentness", label: "Source", status: "complete", owner: "source owner" },
    { id: "cognitive-review", label: "Review", status: "complete", owner: "roundup writer" },
    { id: "finalize", label: "Finalize", status: "complete", owner: "weekly owner" },
    { id: "verify", label: "Verify", status: "complete", owner: "weekly owner" },
    { id: "display", label: "Display", status: "complete", owner: "dashboard" },
    { id: "delivery", label: "Delivery", status: "current", owner: "delivery owner" },
  ],
  delivery: {
    status: "pending",
    configured: true,
    retryable: true,
    record_id: null,
    message_id: null,
    thread_id: null,
    reason: "Verified report awaits configured delivery.",
  },
  limitations: ["Delivery is a separate postcondition."],
  error: null,
} satisfies RunDetail["weekly_report_workflow"]

const retainedReviewWorkflow = {
  ...weeklyReportWorkflow,
  stage: "finalize-verify",
  next_action: "finalize-verify",
  delivery: {
    ...weeklyReportWorkflow.delivery,
    status: "not-ready",
    configured: false,
    retryable: false,
    reason: "Artifact verification has not completed.",
  },
  stages: weeklyReportWorkflow.stages.map((stage) => (
    stage.id === "finalize"
      ? { ...stage, status: "current" as const }
      : stage.id === "verify" || stage.id === "display"
        ? { ...stage, status: "pending" as const }
        : stage.id === "delivery"
          ? { ...stage, status: "pending" as const }
          : stage
  )),
} satisfies RunDetail["weekly_report_workflow"]

const terminalReportWorkflow = {
  status: "available",
  stage: "delivery",
  next_action: "deliver",
  actionable: true,
  report_set_id: "terminal-task-demo-0011223344556677",
  source_root: hash,
  manifest_root: hash,
  fingerprint: hash,
  state_fingerprint: "terminal-state-001",
  mission_root: hash,
  completion: {
    status: "reconciled",
    record_id: "EVT-TERMINAL-COMPLETION",
    lifecycle_record_id: "EVT-TERMINAL-LIFECYCLE",
    reconciled: true,
  },
  coverage: {
    delta_start: "2026-08-08T00:00:00+00:00",
    full_start: "2026-08-01T00:00:00+00:00",
    end: "2026-08-09T00:00:00+00:00",
    delta_anchor_record_id: "weekly-test-001",
    delta_anchor_kind: "verified-prior-report",
  },
  prior_reports: [{ report_id: "weekly-test-001", source_root: hash, manifest_root: hash, coverage: weeklyReportWorkflow.coverage }],
  writer_role: "base_reviewer",
  writer_task_id: "base-reviewer-task",
  expected_members: ["review-packet.json", "review.json", "delta-report.pdf", "full-report.pdf", "manifest.json"],
  members: [],
  stages: [
    { id: "prepare", label: "Prepare", status: "complete", owner: "terminal owner" },
    { id: "source-currentness", label: "Source", status: "complete", owner: "source owner" },
    { id: "cognitive-review", label: "Review", status: "complete", owner: "base reviewer" },
    { id: "finalize", label: "Finalize", status: "complete", owner: "terminal owner" },
    { id: "verify", label: "Verify", status: "complete", owner: "terminal owner" },
    { id: "display", label: "Display", status: "complete", owner: "dashboard" },
    { id: "delivery", label: "Delivery", status: "current", owner: "Gmail owner" },
  ],
  delivery: {
    status: "pending",
    configured: true,
    required: true,
    retryable: true,
    record_id: null,
    message_id: null,
    thread_id: null,
    readback_root: null,
    reason: "Verified terminal PDFs await configured delivery.",
  },
  shutdown: {
    status: "separate-owner",
    permitted: false,
    reason: "Terminal reporting is not shutdown authority.",
  },
  limitations: ["Derived evidence only."],
  error: null,
} satisfies RunDetail["terminal_report_workflow"]

const factoryEvolutionWorkflow = {
  status: "available",
  stage: "awaiting-implementation",
  next_action: "evaluate",
  actionable: true,
  evolution_id: "evolution-test-001",
  packet_id: "packet-test-001",
  packet_root: hash,
  review_id: "review-test-001",
  review_root: hash,
  evaluation_id: null,
  evaluation_root: null,
  disposition: null,
  comparison_plan: null,
  comparison_results: null,
  source_report_id: "weekly-test-001",
  source_report_root: hash,
  event_head_sha256: hash,
  manifest_root: hash,
  fingerprint: hash,
  proposer: { role: "base_reviewer", task_id: "proposer-task" },
  implementer: {
    status: "awaiting-owner-proof",
    task_id: "task-demo",
    baseline_revision: "1".repeat(40),
    candidate_revision: "2".repeat(40),
  },
  evaluator: { role: "reviewer", task_id: "evaluator-task" },
  expected_members: ["learning-packet.json", "review.json", "evaluation.json", "manifest.json"],
  members: [],
  stages: [
    { id: "prepare", label: "Prepare", status: "complete", owner: "factory owner" },
    { id: "finalize", label: "Finalize", status: "complete", owner: "proposer-task" },
    { id: "external-implementation", label: "External implementation", status: "current", owner: "Block 11" },
    { id: "evaluate", label: "Evaluate", status: "pending", owner: "evaluator-task" },
    { id: "verify", label: "Verify", status: "pending", owner: "factory owner" },
  ],
  limitations: ["Disposition is not adoption authority."],
  recovery: { posture: "blocked", guidance: "Await exact external evidence.", preserved_roots: [hash] },
  error: null,
} satisfies RunDetail["factory_evolution_workflow"]

function previewEnvelope(type: string): OperationPreviewEnvelope {
  return {
    data: {
      preview_token: "p".repeat(32),
      operation: {
        id: "op_workflow",
        type,
        target: { kind: "project", id: "demo", project_id: "demo" },
        state: "previewed",
        owner: "maintained owner",
        authority: ["explicit operator confirmation"],
        preview: {
          effect: "Create one exact owner task.",
          risk: "The exact owner may change the registered repository.",
          recipient: null,
          semantic_changes: {
            status: "unavailable",
            complete: false,
            rows: [],
            limitations: ["No owner-supplied semantic comparison is registered for this operation."],
          },
          source_fingerprint: hash,
          source_evidence: {},
          route_gate: {
            status: "not-required",
            target_thread: null,
            recipient: null,
            purpose: null,
            source_record: null,
            required_action: null,
            action_hash: null,
            policy_fingerprint: null,
            binding_fingerprint: null,
          },
          consequences: { ordinary: ["One task."], failure: ["No retry."] },
          confirmation: {
            class: "factory-workflow",
            prompt: "Type AUTHOR",
            expected_value: "AUTHOR",
          },
          expected_postcondition: "The exact task and turn are present.",
          idempotency: "One task.",
          limitations: [],
          expires_at: "2099-08-10T10:30:00.000Z",
        },
        history: [{ state: "previewed", observed_at: "2026-08-10T10:29:00.000Z" }],
        request_evidence: null,
        verification_evidence: null,
        links: [],
        failure: null,
      },
    },
    source: { kind: "administrative-operation", identity: "operations", revision: hash },
    observed_at: "2026-08-10T10:29:00.000Z",
    fingerprint: hash,
    coverage: { status: "partial", observed: [], missing: [] },
    limitations: [],
    error: null,
  }
}

function renderActions(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const project = {
  id: "demo",
  label: "Demo",
  root: "/private/tmp/demo",
  tracker_patterns: [],
  description: null,
  archived: false,
  observed_at: "2026-08-10T10:00:00.000Z",
  discovery: {
    status: "available",
    fingerprint: hash,
    git: { status: "available", revision: head, branch: "main" },
    trackers: { status: "available", candidates: [] },
    source_families: {
      supervision: { status: "available", reason: null },
      codex_tasks: { status: "available", reason: null },
    },
    coverage: "partial",
    limitations: [],
    errors: [],
  },
} satisfies ProjectProjection

const selectedBlock = {
  number: 1,
  title: "Bounded implementation",
  line: 100,
  anchor: "block-1",
  status: "not-started",
  status_line: 102,
  dependencies: [0],
  dependency_expression: "Block 0",
  objective: "Implement one bounded slice.",
  stop: "Stop before Block 2.",
  capability_delta: {},
  completion_evidence: { present: false, posture: "open", line: null, preview: null },
  sections: [],
  dependency_statuses: [{ number: 0, status: "accepted" }],
  blocked_ancestors: [],
  eligible: true,
} as TrackerDetail["blocks"][number]

const tracker = {
  id: hash,
  status: "available",
  project_id: "demo",
  project_label: "Demo",
  title: "Demo tracker",
  relative_path: "docs/demo-implementation-tracker.md",
  profile: "full",
  raw_file: { content_sha256: hash },
  git: {
    status: "available",
    repository_head: head,
    worktree_changed: false,
  },
  verifier: { valid: true },
  current_blocks: [],
  current_block_details: [],
  eligible_blocks: [1],
  blocks: [
    { ...selectedBlock, number: 0, status: "accepted", eligible: false, dependencies: [], stop: "Stop before Block 1." },
    selectedBlock,
  ],
} as unknown as TrackerDetail

const task = {
  id: "task-demo",
  project_binding: { status: "bound", project_id: "demo", candidates: ["demo"] },
  status: { type: "active", active_flags: [] },
  turns: [{ id: "turn-1", status: "inProgress", items: [] }],
} as unknown as TaskDetailEnvelope["data"]["task"]

describe("Factory workflow action strips", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.previewOperation.mockImplementation((request: { operation_type: string }) => (
      Promise.resolve(previewEnvelope(request.operation_type))
    ))
    mocks.cancelOperation.mockResolvedValue(undefined)
  })

  it("previews authoring with the exact operator wording and source set", async () => {
    const user = userEvent.setup()
    renderActions(<ProjectWorkflowActions project={project} />)

    await user.click(screen.getByRole("button", { name: "Author tracker" }))
    await user.type(screen.getByLabelText("Objective"), "Preserve this exact objective.")
    await user.type(screen.getByLabelText(/Source identities/), "README.md{enter}direct-item-1")
    await user.click(screen.getByRole("button", { name: "Preview" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.tracker-author",
      target: { kind: "project", id: "demo", project_id: "demo" },
      input: {
        repository_head: head,
        objective: "Preserve this exact objective.",
        sources: ["README.md", "direct-item-1"],
        non_goals: ["Do not implement any tracker Block"],
      },
    })
    expect(await screen.findByText("Preserve this exact objective.")).toBeVisible()
    expect(screen.getByText("README.md · direct-item-1")).toBeVisible()
    expect(screen.queryByText(/dashboard lets you/i)).not.toBeInTheDocument()
  })

  it("previews one source-bound watcher check and disables unbound runs", async () => {
    const user = userEvent.setup()
    const { rerender } = renderActions(
      <RunCheckAction targetId="task-demo" projectId={null} />,
    )
    expect(screen.getByRole("button", { name: "Check now" })).toBeDisabled()

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    rerender(
      <QueryClientProvider client={client}>
        <RunCheckAction targetId="task-demo" projectId="demo" />
      </QueryClientProvider>,
    )
    await user.click(screen.getByRole("button", { name: "Check now" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-check-now",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    expect(await screen.findByText("One mechanical watcher check · no semantic conclusion")).toBeVisible()
  })

  it("previews only the first incomplete weekly report stage", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        weeklyReportWorkflow={weeklyReportWorkflow}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Deliver report" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.weekly-supervision-report",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: { coverage_days: 7 },
    })
    expect(await screen.findByText("weekly-20260801-20260808-test")).toBeVisible()
    expect(screen.getByText("delivery → deliver")).toBeVisible()
    expect(screen.getByText(/Advance one stage only/)).toBeVisible()
  })

  it("labels retained-review recovery as finalize without requesting review again", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        weeklyReportWorkflow={retainedReviewWorkflow}
      />,
    )

    expect(screen.queryByRole("button", { name: "Review & finalize" })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Finalize & verify" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toMatchObject({
      operation_type: "factory.weekly-supervision-report",
      input: { coverage_days: 7 },
    })
    expect(await screen.findByText("finalize-verify → finalize-verify")).toBeVisible()
  })

  it("previews one terminal-report delivery stage without stop, pause, or shutdown", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        terminalReportWorkflow={terminalReportWorkflow}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Deliver terminal report" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.terminal-supervision-report",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    expect(await screen.findByText("terminal-task-demo-0011223344556677")).toBeVisible()
    expect(screen.getByText("reconciled · EVT-TERMINAL-COMPLETION · EVT-TERMINAL-LIFECYCLE")).toBeVisible()
    expect(screen.getByText(/Request-stop · automation pause · terminal shutdown/)).toHaveTextContent("separate and not performed")
  })

  it("keeps a stale append-once terminal delivery unavailable and non-retryable", () => {
    const staleWorkflow = {
      ...terminalReportWorkflow,
      stage: "delivery-stale",
      next_action: null,
      actionable: false,
      delivery: {
        ...terminalReportWorkflow.delivery,
        status: "stale",
        retryable: false,
        reason: "The retained receipt no longer matches the verified report set.",
      },
      error: {
        code: "terminal_report_delivery_stale",
        message: "The maintained append-once owner cannot replace this receipt.",
        retryable: false,
      },
    } satisfies RunDetail["terminal_report_workflow"]

    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        terminalReportWorkflow={staleWorkflow}
      />,
    )

    const action = screen.getByRole("button", { name: "Terminal report unavailable" })
    expect(action).toBeDisabled()
    expect(action).toHaveAttribute(
      "title",
      "The maintained append-once owner cannot replace this receipt.",
    )
    expect(mocks.previewOperation).not.toHaveBeenCalled()
  })

  it("previews only the current Factory-evolution stage and keeps adoption outside it", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        factoryEvolutionWorkflow={factoryEvolutionWorkflow}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Evaluate candidate" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.evolution-evaluate",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    expect(await screen.findByText("awaiting-implementation → evaluate")).toBeVisible()
    expect(screen.getByText(/Disposition evidence only/)).toHaveTextContent(
      "no implementation, adoption, installation, routing, scheduling, deployment, rollback, or outcome mutation",
    )
  })

  it("maps a server expiry to the same re-preview posture", async () => {
    const user = userEvent.setup()
    mocks.executeOperation.mockRejectedValueOnce(new DashboardApiError(409, {
      data: null,
      source: { kind: "administrative-operation", identity: "operations", revision: hash },
      observed_at: "2026-08-11T19:30:00.000Z",
      fingerprint: hash,
      coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
      limitations: ["Expired before dispatch."],
      error: { code: "preview_expired", message: "The exact preview expired.", retryable: false },
    }))
    renderActions(<RunCheckAction targetId="task-demo" projectId="demo" />)

    await user.click(screen.getByRole("button", { name: "Check now" }))
    await user.type(await screen.findByLabelText("Type AUTHOR"), "AUTHOR")
    await user.click(screen.getByRole("button", { name: "Request operation" }))

    expect(await screen.findByText("Preview expired")).toBeVisible()
    expect(screen.getByText("The exact preview expired.")).toBeVisible()
    expect(screen.getByRole("button", { name: "Request operation" })).toBeDisabled()
    await user.click(screen.getByRole("button", { name: "Preview again" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledTimes(2))
  })

  it("previews closed checkpoint, meta, and exact-incident review variants", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={["INC-ONE", "INC-TWO"]}
        policy={policy}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Checkpoint review" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledTimes(1))
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-review-checkpoint",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    await user.click(screen.getByRole("button", { name: "Close operation preview" }))

    await user.click(screen.getByRole("button", { name: "Meta-review" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledTimes(2))
    expect(mocks.previewOperation.mock.calls[1][0].operation_type).toBe("factory.supervision-review-meta")
    await user.click(screen.getByRole("button", { name: "Close operation preview" }))

    await user.selectOptions(screen.getByRole("combobox", { name: "Issue for follow-up" }), "INC-TWO")
    await user.click(screen.getByRole("button", { name: "Issue follow-up" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledTimes(3))
    expect(mocks.previewOperation.mock.calls[2][0]).toEqual({
      operation_type: "factory.supervision-review-issue",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: { incident_id: "INC-TWO" },
    })
    expect(await screen.findByText("One exact reviewer task · conclusion remains separate from delivery")).toBeVisible()
  })

  it("offers one missing-mission binding repair without operator-supplied identity fields", async () => {
    const user = userEvent.setup()
    const { rerender } = renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
      />,
    )
    expect(screen.queryByRole("button", { name: "Repair binding" })).not.toBeInTheDocument()

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    rerender(
      <QueryClientProvider client={client}>
        <RunSupervisionActions
          targetId="task-demo"
          projectId="demo"
          openIncidentIds={[]}
          policy={policy}
          missionBindingMissing
        />
      </QueryClientProvider>,
    )
    await user.click(screen.getByRole("button", { name: "Repair binding" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-repair-mission-binding",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    expect(await screen.findByText("Missing mission binding only")).toBeVisible()
    expect(screen.getByText(/authority unverified until independent reviewer proof/)).toBeVisible()
    expect(screen.getByText(/Mission overwrite/)).toBeVisible()
  })

  it("previews one same-target successor with direct-source review and no task claim", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        currentMission={{ root: hash, source_record: "direct-user-item-1", policy_sha256: hash }}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Successor mission" }))
    expect(screen.getByRole("dialog", { name: "Successor mission" })).toBeVisible()
    await user.type(
      screen.getByLabelText("Direct mission source record"),
      "codex:task-demo:turn-source-002:item-source-002",
    )
    await user.selectOptions(screen.getByLabelText("Predecessor disposition"), "superseded")
    await user.type(screen.getByLabelText("First eligible work"), "Block 0 capability review")
    await user.type(
      screen.getByLabelText("Reason"),
      "The direct user requested a materially different mission.",
    )
    await user.click(screen.getByRole("button", { name: "Preview" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-mission-successor",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {
        mission_source_record: "codex:task-demo:turn-source-002:item-source-002",
        predecessor_disposition: "superseded",
        first_eligible_work: "Block 0 capability review",
        reason: "The direct user requested a materially different mission.",
      },
    })
    expect(await screen.findByText(/exact bytes and direct authority require independent review/)).toBeVisible()
    expect(screen.getByText(/pending activation, not proof of work-start/)).toBeVisible()
    expect(screen.getByText(/Bind overwrite · successor task/)).toBeVisible()
  })

  it("advances one exact successor-task phase and fails closed on conflicting heads", async () => {
    const user = userEvent.setup()
    const transitions = [{
      transition_id: "TRANSITION-001",
      open: true,
      phase: "successor-bound",
      head: {
        record_id: "EVT-000101",
        timestamp: "2026-08-12T12:00:00Z",
        kind: "successor-transition",
        status: null,
        severity: null,
        category: null,
        summary: "Successor binding is current; handoff is next.",
      },
      tracker_sha256: hash,
      tracker_source_record: "commit:tracker",
      requested_block_range: "26-31",
      first_eligible_block: "Block 26",
      source_mission_root: hash,
      governing_authority_source_class: "direct-user",
      governing_authority_source_record: "direct-user-item-44",
      successor_thread_id: "successor-task-001",
      successor_mission_root: "b".repeat(64),
      successor_group_id: "successor-task-001",
      handoff_record: null,
      acknowledgement_record: null,
      started_block: null,
      state_fingerprint: "state-successor-bound",
    }] as RunDetail["successor_transitions"]
    const { rerender } = renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        successorTransitions={transitions}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Advance continuity" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.successor-task-transition",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: { transition_id: "TRANSITION-001" },
    })
    expect(await screen.findByText("successor-bound")).toBeVisible()
    expect(screen.getByText("In progress until exact work-started evidence")).toBeVisible()
    await user.click(screen.getByRole("button", { name: "Close operation preview" }))

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    rerender(
      <QueryClientProvider client={client}>
        <RunSupervisionActions
          targetId="task-demo"
          projectId="demo"
          openIncidentIds={[]}
          policy={policy}
          successorTransitions={[
            ...transitions,
            { ...transitions[0], transition_id: "TRANSITION-002" },
          ]}
        />
      </QueryClientProvider>,
    )
    expect(screen.getByRole("button", { name: "Continuity conflict" })).toBeDisabled()
  })

  it("offers only projected missing owner-backed roles and submits one exact role", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        roleRepairRoles={["notice_reviewer", "watcher", "fix_executor"]}
      />,
    )

    const selector = screen.getByRole("combobox", { name: "Role binding to repair" })
    expect(selector).toHaveTextContent("Notice reviewer")
    expect(selector).toHaveTextContent("Fix executor")
    expect(selector).not.toHaveTextContent("Watcher")
    await user.selectOptions(selector, "fix_executor")
    await user.click(screen.getByRole("button", { name: "Repair role" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-repair-role-task-binding",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: { role: "fix_executor" },
    })
    expect(await screen.findByText("Exact prior task ID from canonical policy history")).toBeVisible()
    expect(screen.getByText(/no create, resume, turn, or relabel/i)).toBeVisible()
    expect(screen.getByText(/Task \+ policy record \+ maintained purpose gate/)).toBeVisible()
  })

  it("previews one source-backed automation repair with dual postconditions", async () => {
    const user = userEvent.setup()
    const partialPolicy = {
      ...policy,
      automation_reconciliation: policy.automation_reconciliation.map((row) => (
        row.role === "watcher"
          ? {
              ...row,
              actual_automation_id: "watcher-automation",
              actual_rrule: "RRULE:FREQ=MINUTELY;INTERVAL=45",
              actual_target_thread_id: "wrong-watcher-task",
              purpose: "watcher-action",
              timezone: "not-applicable-to-interval-schedule",
              actual_timezone: "not-applicable-to-interval-schedule",
              duplicate_coverage: "exact" as const,
              active_target_owner_ids: [],
              owner_status: "PAUSED",
              state: "partial" as const,
              repairable: true,
              reason: "Policy cadence and actual automation state do not fully agree.",
            }
          : row
      )),
    } as NonNullable<RunDetail["policy"]>
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={partialPolicy}
      />,
    )

    expect(screen.getByRole("combobox", { name: "Automation binding to repair" })).toHaveTextContent(
      "Routine watcher · watcher-automation",
    )
    await user.click(screen.getByRole("button", { name: "Repair automation" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-repair-automation-binding",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: { role: "watcher" },
    })
    expect(await screen.findByText("Routine watcher · watcher-action")).toBeVisible()
    expect(screen.getByText("wrong-watcher-task → watcher-task")).toBeVisible()
    expect(screen.getByText(/INTERVAL=45.*INTERVAL=20/)).toBeVisible()
    expect(screen.getByText("exact · 0 active owners on target")).toBeVisible()
    expect(screen.getByText(/Named automation \+ canonical policy binding/)).toBeVisible()
    expect(screen.getByText(/No automatic retry or rollback/)).toBeVisible()
  })

  it("keeps semantic pause and resume separate from task or turn controls", async () => {
    const user = userEvent.setup()
    const { rerender } = renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
        lifecycleStatus={null}
      />,
    )

    const resume = screen.getByRole("button", { name: "Resume" })
    expect(resume).toBeDisabled()
    expect(resume).toHaveAttribute(
      "title",
      "Resume is available only for a canonical paused lifecycle.",
    )
    await user.click(screen.getByRole("button", { name: "Pause" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-pause",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    expect(await screen.findByText("Canonical paused lifecycle + every exact bound automation PAUSED")).toBeVisible()
    expect(screen.getByText(/Implementation task and turn state/)).toBeVisible()
    expect(screen.getByText(/Partial owner state stays visible/)).toBeVisible()
    await user.click(screen.getByRole("button", { name: "Close operation preview" }))

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const pausedPolicy = {
      ...policy,
      automation_reconciliation: policy.automation_reconciliation.map((row) => ({
        ...row,
        owner_status: "PAUSED",
      })),
    } as NonNullable<RunDetail["policy"]>
    rerender(
      <QueryClientProvider client={client}>
        <RunSupervisionActions
          targetId="task-demo"
          projectId="demo"
          openIncidentIds={[]}
          policy={pausedPolicy}
          lifecycleStatus="paused"
        />
      </QueryClientProvider>,
    )
    expect(screen.getByRole("button", { name: "Paused" })).toBeDisabled()
    expect(screen.queryByRole("button", { name: "Finish pause" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Resume" })).toBeEnabled()
    await user.click(screen.getByRole("button", { name: "Resume" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledTimes(2))
    expect(mocks.previewOperation.mock.calls[1][0]).toEqual({
      operation_type: "factory.supervision-resume",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {},
    })
    await user.click(screen.getByRole("button", { name: "Close operation preview" }))

    const partialPausedPolicy = {
      ...pausedPolicy,
      automation_reconciliation: [
        ...pausedPolicy.automation_reconciliation,
        {
          field: "weekly_report_schedule",
          role: "weekly_report",
          automation_id: null,
          expected_rrule: "RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=8;BYMINUTE=0",
          actual_rrule: null,
          owner_status: null,
          target_thread_id: "roundup-task",
          actual_timezone: "America/Los_Angeles",
          duplicate_coverage: "unavailable",
          active_target_owner_ids: [],
          mode: null,
          state: "unavailable",
          reason: "The configured weekly automation binding is unavailable.",
        },
      ],
    } as NonNullable<RunDetail["policy"]>
    rerender(
      <QueryClientProvider client={client}>
        <RunSupervisionActions
          targetId="task-demo"
          projectId="demo"
          openIncidentIds={[]}
          policy={partialPausedPolicy}
          lifecycleStatus="paused"
        />
      </QueryClientProvider>,
    )
    expect(screen.getByRole("button", { name: "Finish pause" })).toBeEnabled()
    expect(screen.queryByRole("button", { name: "Paused" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Resume unavailable" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Resume unavailable" })).toHaveAttribute(
      "title",
      "Resume requires complete current automation-owner coverage.",
    )

    const resumedUnavailablePolicy = {
      ...policy,
      automation_reconciliation: policy.automation_reconciliation.map((row, index) => ({
        ...row,
        owner_status: "ACTIVE",
        state: index === 0 ? "unavailable" : "reconciled",
        duplicate_coverage: index === 0 ? "unavailable" : "exact",
        reason: index === 0
          ? "Target-specific owner coverage is unavailable."
          : row.reason,
      })),
    } as NonNullable<RunDetail["policy"]>
    rerender(
      <QueryClientProvider client={client}>
        <RunSupervisionActions
          targetId="task-demo"
          projectId="demo"
          openIncidentIds={[]}
          policy={resumedUnavailablePolicy}
          lifecycleStatus="resumed"
        />
      </QueryClientProvider>,
    )
    expect(screen.queryByRole("button", { name: "Running" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Resume incomplete" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Resume incomplete" })).toHaveAttribute(
      "title",
      "Canonical resume exists, but exact active automation-owner coverage is unavailable or incomplete.",
    )
  })

  it("previews one exact policy diff and keeps unbound Gmail cadence unavailable", async () => {
    const user = userEvent.setup()
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={policy}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Adjust supervision" }))
    expect(screen.getByRole("checkbox", { name: /Gmail quiet minutes/ })).toBeDisabled()
    await user.click(screen.getByRole("checkbox", { name: /Routine minutes/ }))
    const value = screen.getByRole("spinbutton", { name: "New Routine minutes" })
    await user.clear(value)
    await user.type(value, "25")
    await user.type(screen.getByLabelText("Reason"), "Increase the bounded routine interval.")
    await user.click(screen.getByRole("button", { name: "Preview" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-adjust",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {
        reason: "Increase the bounded routine interval.",
        routine_minutes: 25,
      },
    })
    expect(await screen.findByText("Routine minutes: 20 → 25")).toBeVisible()
    expect(screen.getByText(/8 adjustable fields/)).toBeVisible()
    expect(screen.getByText("watcher")).toBeVisible()
  })

  it("maps every bound Gmail cadence field to the one Gmail automation owner", async () => {
    const user = userEvent.setup()
    const boundPolicy = {
      ...policy,
      automation_reconciliation: [
        ...policy.automation_reconciliation,
        {
          field: "gmail_cadence",
          role: "gmail_gate",
          automation_id: "gmail-automation",
          expected_rrule: "RRULE:FREQ=MINUTELY;INTERVAL=1",
          actual_rrule: "RRULE:FREQ=MINUTELY;INTERVAL=1",
          owner_status: "ACTIVE",
          target_thread_id: "gmail-gate-task",
          actual_timezone: "not-applicable-to-interval-schedule",
          duplicate_coverage: "exact",
          active_target_owner_ids: ["gmail-automation"],
          mode: "active",
          state: "reconciled",
          reason: "Maintained active cadence and actual automation agree.",
        },
      ],
    } as NonNullable<RunDetail["policy"]>
    renderActions(
      <RunSupervisionActions
        targetId="task-demo"
        projectId="demo"
        openIncidentIds={[]}
        policy={boundPolicy}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Adjust supervision" }))
    await user.click(screen.getByRole("checkbox", { name: /Gmail active window minutes/ }))
    const value = screen.getByRole("spinbutton", { name: "New Gmail active window minutes" })
    await user.clear(value)
    await user.type(value, "45")
    await user.type(screen.getByLabelText("Reason"), "Extend the bounded active cadence window.")
    await user.click(screen.getByRole("button", { name: "Preview" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-adjust",
      target: { kind: "run", id: "task-demo", project_id: "demo" },
      input: {
        reason: "Extend the bounded active cadence window.",
        gmail_active_window_minutes: 45,
      },
    })
    expect(await screen.findByText("gmail_gate")).toBeVisible()
    expect(screen.queryByText("No schedule owner affected")).not.toBeInTheDocument()
  })

  it("previews only the selected eligible implementation range and exact Stop", async () => {
    const user = userEvent.setup()
    renderActions(<TrackerWorkflowActions tracker={tracker} selectedBlock={selectedBlock} />)

    await user.click(screen.getByRole("button", { name: "Implement" }))
    expect(screen.getByRole("dialog", { name: "Implement Blocks" })).toBeVisible()
    await user.type(screen.getByLabelText("Mission root · SHA-256"), hash)
    await user.type(screen.getByLabelText("Mission source record"), "direct-user-item-1")
    await user.click(screen.getByRole("button", { name: "Preview" }))

    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.blocks-implement",
      target: { kind: "tracker", id: hash, project_id: "demo" },
      input: {
        content_sha256: hash,
        repository_head: head,
        verifier_profile: "full",
        block_start: 1,
        block_end: 1,
        supervision: "none",
        expected_stop: "Stop before Block 2.",
        mission_root: hash,
        mission_source_record: "direct-user-item-1",
      },
    })
    expect(await screen.findByText("Block 1")).toBeVisible()
    expect(screen.getByText("Stop before Block 2.")).toBeVisible()
  })

  it("keeps routed active-turn controls unavailable without an exact supervised run", () => {
    const { rerender } = renderActions(
      <TaskWorkflowActions task={task} pending={[]} trackers={[]} run={undefined} />,
    )
    expect(screen.getByRole("button", { name: "Steer" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Interrupt" })).toBeDisabled()
    expect(screen.queryByRole("button", { name: "Continue" })).not.toBeInTheDocument()

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    rerender(
      <QueryClientProvider client={client}>
        <TaskWorkflowActions task={task} pending={[]} trackers={[]} run={{ target_thread_id: task.id }} />
      </QueryClientProvider>,
    )
    expect(screen.getByRole("button", { name: "Steer" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Interrupt" })).toBeEnabled()
  })

  it("keeps every task mutation unavailable when the task has no exact project binding", () => {
    const unbound = {
      ...task,
      project_binding: { status: "unbound", project_id: null, candidates: [] },
    } as unknown as typeof task
    renderActions(
      <TaskWorkflowActions
        task={unbound}
        pending={[]}
        trackers={[tracker as unknown as TrackerSummary]}
        run={{ target_thread_id: task.id }}
      />,
    )
    expect(screen.getByRole("button", { name: "Steer" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Interrupt" })).toBeDisabled()
  })

  it("offers attachment only from the task's exact implementation binding", async () => {
    const user = userEvent.setup()
    const idleTask = {
      ...task,
      status: { type: "idle" },
      turns: [],
    } as unknown as typeof task
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { rerender } = render(
      <QueryClientProvider client={client}>
        <TaskWorkflowActions task={idleTask} pending={[]} trackers={[]} run={undefined} />
      </QueryClientProvider>,
    )
    expect(screen.queryByRole("button", { name: "Attach supervision" })).not.toBeInTheDocument()

    rerender(
      <QueryClientProvider client={client}>
        <TaskWorkflowActions
          task={idleTask}
          pending={[]}
          trackers={[tracker as unknown as TrackerSummary]}
          run={undefined}
        />
      </QueryClientProvider>,
    )
    expect(screen.queryByRole("button", { name: "Attach supervision" })).not.toBeInTheDocument()

    const marker = {
      kind: "implement-blocks",
      source_fingerprint: hash,
      project_id: "demo",
      tracker_id: hash,
      block_start: 1,
      block_end: 1,
      mission_root: hash,
      mission_source_record: "direct-user-item-1",
    }
    const boundTask = {
      ...idleTask,
      preview: `SOFTWARE_FACTORY_DASHBOARD_MISSION ${JSON.stringify({ ...marker, tracker_id: "f".repeat(64) })}`,
      turns: [{
        id: "turn-binding",
        status: "completed",
        items: [{ id: "item-binding", type: "userMessage", summary: `SOFTWARE_FACTORY_DASHBOARD_MISSION ${JSON.stringify(marker)}` }],
      }],
    } as unknown as typeof task
    rerender(
      <QueryClientProvider client={client}>
        <TaskWorkflowActions
          task={boundTask}
          pending={[]}
          trackers={[tracker as unknown as TrackerSummary]}
          run={undefined}
        />
      </QueryClientProvider>,
    )
    await user.click(await screen.findByRole("button", { name: "Attach supervision" }))
    await waitFor(() => expect(mocks.previewOperation).toHaveBeenCalledOnce())
    expect(mocks.previewOperation.mock.calls[0][0]).toEqual({
      operation_type: "factory.supervision-attach",
      target: { kind: "task", id: "task-demo", project_id: "demo" },
      input: {
        tracker_id: hash,
        content_sha256: hash,
        repository_head: head,
        verifier_profile: "full",
        block_start: 1,
        block_end: 1,
        mission_root: hash,
        mission_source_record: "direct-user-item-1",
      },
    })
  })

  it("offers exact pending response families without treating them as lifecycle controls", async () => {
    const user = userEvent.setup()
    const approval = {
      id: "request-1",
      source_fingerprint: hash,
      family: "command_approval",
      task_id: task.id,
      turn_id: "turn-1",
      item_id: "item-1",
      received_at: "2026-08-10T10:00:00.000Z",
      status: "pending",
      details: { command: "safe command", cwd: "/private/tmp/demo", reason: "test" },
    } as TaskDetailEnvelope["data"]["pending_requests"][number]
    const input = {
      id: "request-2",
      source_fingerprint: hash,
      family: "user_input",
      task_id: task.id,
      turn_id: "turn-1",
      item_id: "item-2",
      received_at: "2026-08-10T10:00:00.000Z",
      status: "pending",
      details: {
        questions: [{
          id: "choice",
          header: "Choice",
          question: "Which exact option?",
          options: [
            { label: "First", description: "Use the first bounded path." },
            { label: "Second", description: "Use the second bounded path." },
          ],
        }],
      },
    } as TaskDetailEnvelope["data"]["pending_requests"][number]
    renderActions(
      <TaskWorkflowActions
        task={task}
        pending={[approval, input]}
        trackers={[] as TrackerSummary[]}
        run={{ target_thread_id: task.id }}
      />,
    )
    expect(screen.getByRole("button", { name: "Approval" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Input" })).toBeEnabled()
    expect(screen.queryByRole("button", { name: /pause|stop|accept work/i })).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Approval" }))
    expect(screen.getByText("safe command")).toBeVisible()
    expect(screen.getByText("/private/tmp/demo")).toBeVisible()
    await user.click(screen.getByRole("button", { name: "Cancel" }))

    await user.click(screen.getByRole("button", { name: "Input" }))
    expect(screen.getByRole("option", { name: "First · Use the first bounded path." })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Which exact option?"), "First")
    expect(screen.getByText("Use the first bounded path.")).toBeVisible()
  })
})
