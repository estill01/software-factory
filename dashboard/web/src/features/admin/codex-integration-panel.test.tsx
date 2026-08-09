import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { CodexIntegrationPanel } from "@/features/admin/codex-integration-panel"
import * as taskApi from "@/lib/task-api"
import type { TaskIntegrationEnvelope, TaskOperationEnvelope } from "@/lib/task-api"

vi.mock("@/lib/task-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/task-api")>()
  return {
    ...original,
    fetchTaskIntegration: vi.fn(),
    restartTaskIntegration: vi.fn(),
    streamTaskEvents: vi.fn(),
  }
})

const fingerprint = (character: string) => character.repeat(64)

function envelope(status: "available" | "unavailable" = "available"): TaskIntegrationEnvelope {
  const available = status === "available"
  return {
    data: {
      integration: {
        status,
        protocol_status: available ? "compatible" : "disconnected",
        cli: {
          command: available ? ["/usr/local/bin/codex"] : null,
          version: available ? "codex-cli 0.145.0" : null,
          expected_version: "codex-cli 0.145.0",
        },
        schema: {
          semantic_manifest_sha256: available ? fingerprint("a") : null,
          expected_semantic_manifest_sha256: fingerprint("a"),
          file_count: available ? 273 : null,
          expected_file_count: 273,
        },
        transport: { kind: "stdio", child_running: available },
        reconnect: {
          failure_count: available ? 0 : 1,
          retry_after_ms: available ? 0 : 2_000,
          maximum_delay_ms: 30_000,
        },
        features: [
          {
            capability: "task_list",
            status: available ? "supported" : "unavailable",
            exposure: "read",
            reason: available ? null : "The exact compatibility gate is unavailable.",
          },
          {
            capability: "raw_protocol",
            status: "unavailable",
            exposure: "unavailable",
            reason: "Raw App Server methods and payloads are never exposed.",
          },
        ],
        pending_requests: 0,
        last_error: available
          ? null
          : {
              code: "app_server_disconnected",
              message: "The adapter disconnected.",
              retryable: true,
              observed_at: "2026-08-09T12:00:00.000Z",
            },
        restart_count: 0,
        connection_generation: 1,
        ignored_protocol_messages: 0,
        observed_at: "2026-08-09T12:00:00.000Z",
        revision: fingerprint("b"),
      },
    },
    source: {
      kind: "codex-app-server",
      identity: "software-factory-dashboard/task-integration",
      revision: fingerprint("b"),
    },
    observed_at: "2026-08-09T12:00:00.000Z",
    fingerprint: fingerprint("c"),
    coverage: {
      status: available ? "complete" : "partial",
      observed: available ? ["codex-app-server"] : [],
      missing: available ? [] : ["codex-app-server"],
    },
    limitations: [],
    error: null,
  }
}

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <CodexIntegrationPanel />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(taskApi.fetchTaskIntegration).mockReset()
  vi.mocked(taskApi.restartTaskIntegration).mockReset()
  vi.mocked(taskApi.streamTaskEvents).mockReset()
  vi.mocked(taskApi.streamTaskEvents).mockResolvedValue()
})

describe("CodexIntegrationPanel", () => {
  it("shows exact compatibility state and unavailable capabilities compactly", async () => {
    vi.mocked(taskApi.fetchTaskIntegration).mockResolvedValue(envelope())
    renderPanel()

    expect(await screen.findByText("Connected")).toBeVisible()
    expect(screen.getByRole("heading", { name: "Codex integration" })).toBeVisible()
    expect(screen.getByText("codex-cli 0.145.0")).toBeVisible()
    expect(screen.getByText("Task List")).toBeVisible()
    expect(screen.getByText("Raw Protocol")).toBeVisible()
    expect(screen.getAllByText("Unavailable")).toHaveLength(1)
    expect(screen.queryByText(/dashboard lets you/i)).not.toBeInTheDocument()
  })

  it("restarts only the adapter and refreshes integration state", async () => {
    const current = envelope()
    vi.mocked(taskApi.fetchTaskIntegration).mockResolvedValue(current)
    vi.mocked(taskApi.restartTaskIntegration).mockResolvedValue({
      ...current,
      data: {
        integration: { ...current.data.integration, restart_count: 1 },
        operation: "adapter_restarted",
      },
    } as TaskOperationEnvelope)
    const user = userEvent.setup()
    renderPanel()

    await user.click(await screen.findByRole("button", { name: "Restart adapter" }))

    await waitFor(() => expect(taskApi.restartTaskIntegration).toHaveBeenCalledTimes(1))
    expect(screen.queryByText(/restart server/i)).not.toBeInTheDocument()
  })

  it("keeps exact adapter failure visible", async () => {
    vi.mocked(taskApi.fetchTaskIntegration).mockResolvedValue(envelope("unavailable"))
    renderPanel()

    expect((await screen.findAllByText("Disconnected")).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByRole("alert")).toHaveTextContent("The adapter disconnected.")
    expect(screen.getByRole("button", { name: "Restart adapter" })).toBeEnabled()
  })

  it("refreshes projections when the stream reports a replay gap", async () => {
    let reportState: Parameters<typeof taskApi.streamTaskEvents>[3]
    vi.mocked(taskApi.fetchTaskIntegration).mockResolvedValue(envelope())
    vi.mocked(taskApi.streamTaskEvents).mockImplementation(
      (_onEvent, signal, _after, onState) => {
        reportState = onState
        return new Promise((resolve) => {
          signal.addEventListener("abort", () => resolve(), { once: true })
        })
      },
    )
    renderPanel()

    expect(await screen.findByText("Connected")).toBeVisible()
    await act(async () => {
      reportState?.({
        status: "connected",
        cursor: 12,
        replay: {
          requested_after: 12,
          oldest_available: 20,
          latest_available: 24,
          truncated: true,
        },
        replay_truncated: true,
        reconnect_attempt: 1,
      })
    })

    await waitFor(() => expect(taskApi.fetchTaskIntegration).toHaveBeenCalledTimes(2))
  })
})
