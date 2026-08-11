import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({ fetchOperationFramework: vi.fn() }))
vi.mock("@/lib/admin-operations-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/admin-operations-api")>()),
  fetchOperationFramework: mocks.fetchOperationFramework,
}))

import {
  OperationActivityPanel,
  OperationConfirmationDialog,
  OperationFrameworkPanel,
} from "@/features/admin/operation-framework-panel"

const hash = "a".repeat(64)
const operation = {
  id: "op_example",
  type: "test.fixture-set",
  target: { kind: "test-fixture", id: "fixture-1", project_id: "test" },
  state: "previewed" as const,
  owner: "tests/deterministic-owner",
  authority: ["Block 10 deterministic test owner"],
  preview: {
    effect: "Set fixture-1 to next",
    risk: "Changes only the fixture.",
    recipient: "test-recipient",
    source_fingerprint: hash,
    source_evidence: { version: 1 },
    route_gate: {
      status: "allowed" as const,
      target_thread: "fixture-target",
      recipient: "test-recipient",
      purpose: "deterministic-owner-proof",
      source_record: "TEST-1",
      required_action: "Set fixture-1 to next",
      action_hash: hash,
      policy_fingerprint: hash,
      binding_fingerprint: hash,
    },
    consequences: { ordinary: ["Fixture changes."], failure: ["Verification may fail."] },
    confirmation: {
      class: "typed-phrase",
      prompt: "Type APPLY TEST FIXTURE",
      expected_value: "APPLY TEST FIXTURE",
    },
    expected_postcondition: "The fixture reports next.",
    idempotency: "One request per token.",
    limitations: ["Test only."],
    expires_at: "2026-08-10T08:02:00.000Z",
  },
  history: [{ state: "previewed" as const, observed_at: "2026-08-10T08:00:00.000Z" }],
  request_evidence: null,
  verification_evidence: null,
  links: [],
  failure: null,
}

const frameworkEnvelope = {
  data: {
    framework: {
      ephemeral: true as const,
      registered_operations: [],
      activity: [],
      restart_posture: "Reconstruct from canonical owners.",
    },
  },
  source: { kind: "administrative-operation", identity: "operations", revision: hash },
  observed_at: "2026-08-10T08:00:00.000Z",
  fingerprint: hash,
  coverage: { status: "partial" as const, observed: [], missing: [] },
  limitations: [],
  error: null,
}

function renderFramework() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <OperationFrameworkPanel />
    </QueryClientProvider>,
  )
}

describe("administrative operation UI", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchOperationFramework.mockResolvedValue(frameworkEnvelope)
  })

  it("keeps the production admin surface sparse when no owner operation is registered", async () => {
    renderFramework()
    expect(await screen.findByText("0 available")).toBeVisible()
    expect(screen.getByRole("region", { name: "Operations" })).toHaveTextContent("0 available")
    expect(screen.getByText("No owner-backed administrative operations are currently available.")).toBeVisible()
    expect(screen.getByText("No operations requested in this server session.")).toBeVisible()
    expect(screen.queryByRole("button", { name: /execute|start|pause|stop|accept/i })).not.toBeInTheDocument()
  })

  it("requires exact typed confirmation and distinguishes request from outcome", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <OperationConfirmationDialog
        preview={{ ...frameworkEnvelope, data: { operation, preview_token: "p".repeat(32) } }}
        request={{
          operation_type: operation.type,
          target: operation.target,
          input: { mode: "success", value: "next" },
        }}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )

    const requestButton = screen.getByRole("button", { name: "Request operation" })
    expect(requestButton).toBeDisabled()
    await user.type(screen.getByLabelText("Type APPLY TEST FIXTURE"), "APPLY TEST FIXTURE")
    expect(requestButton).toBeEnabled()
    await user.click(requestButton)
    expect(onConfirm).toHaveBeenCalledWith({ class: "typed-phrase", value: "APPLY TEST FIXTURE" })
    expect(screen.getByText("The fixture reports next.")).toBeVisible()
    expect(screen.getByText("deterministic-owner-proof")).toBeVisible()
    expect(screen.queryByText(/workflow complete/i)).not.toBeInTheDocument()
  })

  it("shows exact role-task and route facts for a binding repair preview", () => {
    const roleOperation = {
      ...operation,
      type: "factory.supervision-repair-role-task-binding",
      preview: {
        ...operation.preview,
        source_evidence: {
          role_label: "Notice reviewer",
          expected_task_id: "task-notice-001",
          candidate_task_status: "idle",
          expected_model: { model: "gpt-5.6-sol", reasoning: "xhigh" },
          observed_model_and_effort: { model: "gpt-5.6-sol", reasoning: "xhigh" },
          route_purpose: "incident-review",
        },
      },
    }
    render(
      <OperationConfirmationDialog
        preview={{ ...frameworkEnvelope, data: { operation: roleOperation, preview_token: "p".repeat(32) } }}
        request={{ operation_type: roleOperation.type, target: roleOperation.target, input: { role: "notice_reviewer" } }}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    expect(screen.getByText("Notice reviewer")).toBeVisible()
    expect(screen.getByText("task-notice-001")).toBeVisible()
    expect(screen.getByText("idle")).toBeVisible()
    expect(screen.getByText("Required role model")).toBeVisible()
    expect(screen.getByText("Task-observed model")).toBeVisible()
    expect(screen.getAllByText("gpt-5.6-sol · xhigh")).toHaveLength(2)
    expect(screen.getByText("incident-review")).toBeVisible()
  })

  it("offers re-preview for stale tokens and renders approval/input/unverified distinctly", async () => {
    const user = userEvent.setup()
    const refresh = vi.fn()
    render(
      <OperationConfirmationDialog
        preview={{ ...frameworkEnvelope, data: { operation, preview_token: "p".repeat(32) } }}
        request={{ operation_type: operation.type, target: operation.target, input: {} }}
        staleReason="Authoritative source changed."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        onRefresh={refresh}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Preview again" }))
    expect(refresh).toHaveBeenCalledOnce()

    const { rerender } = render(
      <OperationActivityPanel operations={[{
        ...operation,
        state: "awaiting-approval",
        history: [...operation.history, { state: "awaiting-approval", observed_at: "2026-08-10T08:01:00.000Z" }],
      }]} />,
    )
    expect(screen.getByText("The owner is awaiting approval. No approval response was inferred or sent.")).toBeVisible()
    rerender(<OperationActivityPanel operations={[{
      ...operation,
      state: "unverified",
      history: [...operation.history, { state: "unverified", observed_at: "2026-08-10T08:01:00.000Z" }],
      failure: { code: "postcondition_timeout", message: "Timed out." },
    }]} />)
    expect(screen.getByText(/canonical postcondition is unverified/i)).toBeVisible()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      state: "applied",
      history: [...operation.history, { state: "applied", observed_at: "2026-08-10T08:01:00.000Z" }],
      verification_evidence: {
        task_turn_started: true,
        block_accepted: false,
        outcome_verified: false,
      },
    }]} />)
    expect(screen.getByText("Task/turn started")).toBeVisible()
    expect(screen.getByText("Block not accepted")).toBeVisible()
    expect(screen.getByText("Outcome not verified")).toBeVisible()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      type: "factory.supervision-check-now",
      state: "applied",
      history: [...operation.history, { state: "applied", observed_at: "2026-08-10T08:01:00.000Z" }],
      request_evidence: { watcher_awakened: true },
      verification_evidence: {
        check_recorded: true,
        changed_state_routed: true,
        semantic_conclusion: false,
      },
    }]} />)
    expect(screen.getByText("Watcher awakened")).toBeVisible()
    expect(screen.getByText("Canonical check recorded")).toBeVisible()
    expect(screen.getByText("Changed state routed for review")).toBeVisible()
    expect(screen.getByText("No semantic conclusion inferred")).toBeVisible()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      type: "factory.supervision-review-checkpoint",
      state: "applied",
      history: [...operation.history, { state: "applied", observed_at: "2026-08-10T08:02:00.000Z" }],
      request_evidence: { review_task_started: true },
      verification_evidence: {
        conclusion_recorded: true,
        conclusion_status: "accepted",
        conclusion_current: false,
        reviewer_turn_correlated: true,
        conclusion_actor_attribution: "unavailable",
        request_delivery_is_conclusion: false,
        implementation_accepted_by_dashboard: false,
      },
    }]} />)
    expect(screen.getByText("Reviewer task started")).toBeVisible()
    expect(screen.getByText("Canonical conclusion recorded")).toBeVisible()
    expect(screen.getByText("Conclusion: accepted")).toBeVisible()
    expect(screen.getByText("Conclusion superseded")).toBeVisible()
    expect(screen.getByText("Exact reviewer turn correlated")).toBeVisible()
    expect(screen.getByText("Conclusion actor unavailable")).toBeVisible()
    expect(screen.getByText("Delivery is not a conclusion")).toBeVisible()
    expect(screen.getByText("Dashboard did not accept implementation")).toBeVisible()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      type: "factory.supervision-review-checkpoint",
      state: "unverified",
      history: [...operation.history, { state: "unverified", observed_at: "2026-08-10T08:03:00.000Z" }],
      request_evidence: { review_task_started: true },
      verification_evidence: {
        conclusion_recorded: false,
        reviewer_request_current: false,
        matching_record_id: "EVT-000005",
      },
    }]} />)
    expect(screen.getByText("Matching record is not correlated to the exact reviewer turn")).toBeVisible()
    expect(screen.queryByText("Awaiting canonical conclusion")).not.toBeInTheDocument()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      type: "factory.supervision-adjust",
      state: "unverified",
      history: [...operation.history, { state: "unverified", observed_at: "2026-08-10T08:04:00.000Z" }],
      request_evidence: { policy_adjust_requested: true },
      verification_evidence: {
        policy_applied: true,
        policy_version: 6,
        automation_reconciled: false,
        partial_reconciliation: true,
        fully_reconciled: false,
        direct_policy_write: false,
        direct_automation_write: false,
        fix_executor_actor_attribution: "unavailable",
      },
    }]} />)
    expect(screen.getByText("Policy v6 verified")).toBeVisible()
    expect(screen.getByText("Automation reconciliation pending")).toBeVisible()
    expect(screen.getByText("Partial reconciliation remains attention")).toBeVisible()
    expect(screen.getByText("Dashboard direct policy writes excluded")).toBeVisible()
    expect(screen.getByText("Canonical records do not expose the execution actor")).toBeVisible()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      type: "factory.supervision-repair-mission-binding",
      state: "unverified",
      history: [...operation.history, { state: "unverified", observed_at: "2026-08-10T08:05:00.000Z" }],
      request_evidence: {
        binding_repair_requested: true,
        source_authority_status: "unverified-reviewer-verification-required",
      },
      verification_evidence: {
        binding_repaired: false,
        reviewer_authority_verified: false,
      },
    }]} />)
    expect(screen.getByText("Missing-mission repair requested")).toBeVisible()
    expect(screen.getByText("Source authority unverified; independent review required")).toBeVisible()
    expect(screen.queryByText(/attested by operator/i)).not.toBeInTheDocument()

    rerender(<OperationActivityPanel operations={[{
      ...operation,
      type: "factory.supervision-repair-role-task-binding",
      state: "applied",
      history: [...operation.history, { state: "applied", observed_at: "2026-08-10T08:06:00.000Z" }],
      request_evidence: {
        role_binding_requested: true,
        task_created: false,
      },
      verification_evidence: {
        task_postcondition_current: true,
        policy_postcondition_current: true,
        run_project_binding_current: true,
        single_role_current: true,
        unrelated_roles_preserved: true,
        automations_preserved: true,
        route_gate_accepted: true,
        route_purpose: "incident-review",
        direct_policy_write: false,
      },
    }]} />)
    expect(screen.getByText("Exact missing-role bind requested")).toBeVisible()
    expect(screen.getByText("No task created")).toBeVisible()
    expect(screen.getByText("Eligible task identity and lifecycle current")).toBeVisible()
    expect(screen.getByText("Canonical role binding verified")).toBeVisible()
    expect(screen.getByText("Canonical run/project claim current")).toBeVisible()
    expect(screen.getByText("Single-role assignment verified")).toBeVisible()
    expect(screen.getByText("Unrelated roles preserved")).toBeVisible()
    expect(screen.getByText("Automations preserved")).toBeVisible()
    expect(screen.getByText("Route accepted: incident-review")).toBeVisible()
    expect(screen.getByText("Maintained bind owner used")).toBeVisible()
  })
})
