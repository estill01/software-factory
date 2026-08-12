import { afterEach, describe, expect, it, vi } from "vitest"

import {
  fetchTask,
  fetchTaskIntegration,
  restartTaskIntegration,
  streamTaskEvents,
  taskIntegrationEnvelopeSchema,
  taskListEnvelopeSchema,
} from "@/lib/task-api"

const fingerprint = (character: string) => character.repeat(64)

const integration = {
  status: "available",
  protocol_status: "compatible",
  cli: {
    command: ["/usr/local/bin/codex"],
    version: "codex-cli 0.145.0",
    expected_version: "codex-cli 0.145.0",
  },
  schema: {
    semantic_manifest_sha256: fingerprint("a"),
    expected_semantic_manifest_sha256: fingerprint("a"),
    file_count: 273,
    expected_file_count: 273,
  },
  transport: { kind: "stdio", child_running: true },
  reconnect: { failure_count: 0, retry_after_ms: 0, maximum_delay_ms: 30_000 },
  features: [
    { capability: "task_list", status: "supported", exposure: "read", reason: null },
    {
      capability: "raw_protocol",
      status: "unavailable",
      exposure: "unavailable",
      reason: "Never exposed.",
    },
  ],
  pending_requests: 0,
  last_error: null,
  restart_count: 0,
  connection_generation: 1,
  ignored_protocol_messages: 0,
  observed_at: "2026-08-09T12:00:00.000Z",
  revision: fingerprint("b"),
} as const

const metadata = {
  source: {
    kind: "codex-app-server",
    identity: "software-factory-dashboard/task-integration",
    revision: fingerprint("b"),
  },
  observed_at: "2026-08-09T12:00:00.000Z",
  fingerprint: fingerprint("c"),
  coverage: { status: "complete", observed: ["codex-app-server"], missing: [] },
  limitations: [],
  error: null,
} as const

const integrationEnvelope = {
  data: { integration },
  ...metadata,
} as const

const task = {
  id: "task-fake-001",
  session_id: "task-fake-001",
  parent_task_id: null,
  forked_from_id: null,
  name: "Fake task",
  preview: "Bounded fake task",
  cwd: "/work/demo",
  project_binding: { status: "bound", project_id: "demo", candidates: ["demo"] },
  status: { type: "active", active_flags: [] },
  created_at: "2026-08-09T11:00:00.000Z",
  updated_at: "2026-08-09T12:00:00.000Z",
  recency_at: null,
  source: "appServer",
  model_provider: "openai",
  cli_version: "0.145.0",
  ephemeral: false,
  git: { revision: null, branch: null, origin: null },
  turns: [
    {
      id: "turn-fake-001",
      status: "inProgress",
      started_at: "2026-08-09T12:00:00.000Z",
      completed_at: null,
      duration_ms: null,
      items_view: "full",
      items: [{ id: "item-fake-001", type: "agentMessage", status: null, summary: "Working" }],
      items_truncated: false,
      error: null,
    },
  ],
  turns_truncated: false,
} as const

afterEach(() => {
  document.querySelector('meta[name="software-factory-mutation-nonce"]')?.remove()
  vi.unstubAllGlobals()
})

describe("task API contracts", () => {
  it("accepts closed integration and task list envelopes", () => {
    expect(taskIntegrationEnvelopeSchema.parse(integrationEnvelope).data.integration.status).toBe(
      "available",
    )
    const listing = {
      data: {
        tasks: [task],
        next_cursor: null,
        backwards_cursor: null,
        pending_requests: [],
        integration,
      },
      ...metadata,
    }
    expect(taskListEnvelopeSchema.parse(listing).data.tasks[0]?.project_binding.project_id).toBe(
      "demo",
    )
    const currentProvenance = {
      ...listing,
      data: {
        ...listing.data,
        tasks: [
          {
            ...task,
            turns: [
              {
                ...task.turns[0],
                items: [
                  {
                    ...task.turns[0].items[0],
                    summary_sha256: fingerprint("d"),
                    summary_truncated: false,
                    client_id: "codex-app",
                    user_content_sha256: null,
                    user_content_truncated: null,
                    user_content_envelope_sha256: null,
                    user_content_part_types: null,
                    user_input_classification: null,
                    user_authority_status: null,
                  },
                ],
              },
            ],
          },
        ],
      },
    }
    expect(
      taskListEnvelopeSchema.parse(currentProvenance).data.tasks[0]?.turns[0]?.items[0]
        ?.summary_sha256,
    ).toBe(fingerprint("d"))
    expect(() =>
      taskListEnvelopeSchema.parse({
        ...currentProvenance,
        data: {
          ...currentProvenance.data,
          tasks: [
            {
              ...currentProvenance.data.tasks[0],
              turns: [
                {
                  ...currentProvenance.data.tasks[0].turns[0],
                  items: [
                    {
                      ...currentProvenance.data.tasks[0].turns[0].items[0],
                      unowned_provenance: "rejected",
                    },
                  ],
                },
              ],
            },
          ],
        },
      }),
    ).toThrow()
    expect(() =>
      taskListEnvelopeSchema.parse({
        ...listing,
        data: { ...listing.data, raw_protocol_method: "thread/list" },
      }),
    ).toThrow()
  })

  it("parses integration health and sends exact restart authority", async () => {
    const nonce = document.createElement("meta")
    nonce.name = "software-factory-mutation-nonce"
    nonce.content = "launch-nonce"
    document.head.append(nonce)
    const restarted = {
      data: { integration: { ...integration, restart_count: 1 }, operation: "adapter_restarted" },
      ...metadata,
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => integrationEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => restarted })
    vi.stubGlobal("fetch", fetchMock)

    await expect(fetchTaskIntegration()).resolves.toEqual(integrationEnvelope)
    await expect(restartTaskIntegration()).resolves.toMatchObject({
      data: { operation: "adapter_restarted" },
    })

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/task-integration/restart",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-Software-Factory-Nonce": "launch-nonce" }),
        body: JSON.stringify({ confirmation: "restart-codex-adapter" }),
      }),
    )
  })

  it("parses bounded SSE records without exposing transport methods", async () => {
    const nonce = document.createElement("meta")
    nonce.name = "software-factory-mutation-nonce"
    nonce.content = "launch-nonce"
    document.head.append(nonce)
    const event = {
      sequence: 2,
      type: "task_status",
      observed_at: "2026-08-09T12:00:01.000Z",
      data: { task_id: "task-fake-001", status: { type: "idle", active_flags: [] } },
    }
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            `event: ready\ndata: {"sequence":0,"type":"ready","observed_at":"2026-08-09T12:00:00.000Z","replay":{"requested_after":0,"oldest_available":1,"latest_available":2,"truncated":false}}\n\nid: 2\nevent: task_status\ndata: ${JSON.stringify(event)}\n\n`,
          ),
        )
        controller.close()
      },
    })
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, body: stream }),
    )
    const received: unknown[] = []
    const states: unknown[] = []
    const controller = new AbortController()

    await streamTaskEvents(
      (value) => {
        received.push(value)
        controller.abort()
      },
      controller.signal,
      0,
      (state) => states.push(state),
    )

    expect(received).toEqual([event])
    expect(states).toContainEqual(
      expect.objectContaining({ status: "connected", cursor: 0, replay_truncated: false }),
    )
    expect(JSON.stringify(received)).not.toContain("thread/status/changed")
  })

  it("reconnects from the last consumed cursor and reports replay truncation", async () => {
    const nonce = document.createElement("meta")
    nonce.name = "software-factory-mutation-nonce"
    nonce.content = "launch-nonce"
    document.head.append(nonce)
    const event = (sequence: number) => ({
      sequence,
      type: "task_status" as const,
      observed_at: `2026-08-09T12:00:0${sequence}.000Z`,
      data: { task_id: "task-fake-001", status: { type: "idle", active_flags: [] } },
    })
    const first = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            `event: ready\ndata: {"sequence":0,"type":"ready","observed_at":"2026-08-09T12:00:00.000Z","replay":{"requested_after":0,"oldest_available":1,"latest_available":2,"truncated":false}}\n\nid: 2\nevent: task_status\ndata: ${JSON.stringify(event(2))}\n\n`,
          ),
        )
        controller.close()
      },
    })
    const second = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            `event: ready\ndata: {"sequence":2,"type":"ready","observed_at":"2026-08-09T12:00:03.000Z","replay":{"requested_after":2,"oldest_available":5,"latest_available":5,"truncated":true}}\n\nid: 5\nevent: task_status\ndata: ${JSON.stringify(event(5))}\n\n`,
          ),
        )
        controller.close()
      },
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, body: first })
      .mockResolvedValueOnce({ ok: true, status: 200, body: second })
    vi.stubGlobal("fetch", fetchMock)
    const received: number[] = []
    const states: unknown[] = []
    const controller = new AbortController()

    await streamTaskEvents(
      (value) => {
        received.push(value.sequence)
        if (value.sequence === 5) controller.abort()
      },
      controller.signal,
      0,
      (state) => states.push(state),
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/task-events?after=2",
      expect.objectContaining({ signal: controller.signal }),
    )
    expect(received).toEqual([2, 5])
    expect(states).toContainEqual(
      expect.objectContaining({ status: "reconnecting", cursor: 2, reconnect_attempt: 1 }),
    )
    expect(states).toContainEqual(
      expect.objectContaining({ status: "connected", cursor: 2, replay_truncated: true }),
    )
  })

  it("parses structured task errors before rejecting", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({
          data: null,
          ...metadata,
          error: {
            code: "task_not_found",
            message: "The requested Codex task is not loaded.",
            retryable: false,
          },
        }),
      }),
    )

    await expect(
      fetchTask("00000000-0000-0000-0000-000000000000"),
    ).rejects.toMatchObject({
      name: "DashboardApiError",
      status: 404,
      code: "task_not_found",
      retryable: false,
    })
  })
})
