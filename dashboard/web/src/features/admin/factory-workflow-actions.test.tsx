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
          expires_at: "2026-08-10T10:30:00.000Z",
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
