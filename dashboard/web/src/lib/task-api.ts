import { z } from "zod"

import {
  apiErrorEnvelopeSchema,
  coverageSchema,
  DashboardApiError,
  mutationNonce,
  sourceSchema,
} from "@/lib/api"

const nullableString = z.string().nullable()
const fingerprintSchema = z.string().regex(/^[0-9a-f]{64}$/)

export const featureSchema = z
  .object({
    capability: z.string().min(1),
    status: z.enum(["supported", "unavailable"]),
    exposure: z.enum(["read", "owner-gated", "unavailable"]),
    reason: nullableString,
  })
  .strict()

const integrationErrorSchema = z
  .object({
    code: z.string().min(1),
    message: z.string().min(1),
    retryable: z.boolean(),
    observed_at: z.iso.datetime({ offset: true }),
  })
  .strict()

export const taskIntegrationSchema = z
  .object({
    status: z.enum(["not-started", "starting", "available", "unavailable", "stopped"]),
    protocol_status: z.enum([
      "not-started",
      "checking",
      "compatible",
      "incompatible",
      "disconnected",
      "stopped",
    ]),
    cli: z
      .object({
        command: z.array(z.string()).nullable(),
        version: nullableString,
        expected_version: nullableString,
      })
      .strict(),
    schema: z
      .object({
        semantic_manifest_sha256: fingerprintSchema.nullable(),
        expected_semantic_manifest_sha256: fingerprintSchema.nullable(),
        file_count: z.number().int().nonnegative().nullable(),
        expected_file_count: z.number().int().nonnegative().nullable(),
      })
      .strict(),
    transport: z
      .object({
        kind: z.literal("stdio"),
        child_running: z.boolean(),
      })
      .strict(),
    reconnect: z
      .object({
        failure_count: z.number().int().nonnegative(),
        retry_after_ms: z.number().int().min(0).max(30_000),
        maximum_delay_ms: z.literal(30_000),
      })
      .strict(),
    features: z.array(featureSchema),
    pending_requests: z.number().int().nonnegative(),
    last_error: integrationErrorSchema.nullable(),
    restart_count: z.number().int().nonnegative(),
    connection_generation: z.number().int().nonnegative(),
    ignored_protocol_messages: z.number().int().nonnegative(),
    observed_at: z.iso.datetime({ offset: true }),
    revision: fingerprintSchema,
  })
  .strict()

const taskStatusSchema = z
  .object({
    type: z.enum(["notLoaded", "idle", "systemError", "active", "unknown"]),
    active_flags: z.array(z.string()),
  })
  .strict()

const taskItemSchema = z
  .object({
    id: z.string().min(1),
    type: z.string().min(1),
    status: nullableString,
    summary: nullableString,
  })
  .strict()

export const taskTurnSchema = z
  .object({
    id: z.string().min(1),
    status: z.string().min(1),
    started_at: z.iso.datetime({ offset: true }).nullable(),
    completed_at: z.iso.datetime({ offset: true }).nullable(),
    duration_ms: z.number().int().nonnegative().nullable(),
    items_view: z.string().min(1),
    items: z.array(taskItemSchema),
    items_truncated: z.boolean(),
    error: nullableString,
  })
  .strict()

const projectBindingSchema = z
  .object({
    status: z.enum(["bound", "ambiguous", "unregistered"]),
    project_id: nullableString,
    candidates: z.array(z.string()),
  })
  .strict()

export const taskSchema = z
  .object({
    id: z.string().min(1),
    session_id: nullableString,
    parent_task_id: nullableString,
    forked_from_id: nullableString,
    name: nullableString,
    preview: nullableString,
    cwd: z.string(),
    project_binding: projectBindingSchema,
    status: taskStatusSchema,
    created_at: z.iso.datetime({ offset: true }).nullable(),
    updated_at: z.iso.datetime({ offset: true }).nullable(),
    recency_at: z.iso.datetime({ offset: true }).nullable(),
    source: z.string().min(1),
    model_provider: z.string().min(1),
    cli_version: z.string().min(1),
    ephemeral: z.boolean(),
    git: z
      .object({
        revision: nullableString,
        branch: nullableString,
        origin: nullableString,
      })
      .strict(),
    turns: z.array(taskTurnSchema),
    turns_truncated: z.boolean(),
  })
  .strict()

const commandRequestSchema = z
  .object({
    id: z.string().min(1),
    source_fingerprint: fingerprintSchema,
    family: z.literal("command_approval"),
    task_id: nullableString,
    turn_id: nullableString,
    item_id: nullableString,
    received_at: z.iso.datetime({ offset: true }),
    status: z.enum(["pending", "responded", "stale"]),
    details: z
      .object({
        command: nullableString,
        cwd: nullableString,
        reason: nullableString,
      })
      .strict(),
  })
  .strict()

const fileRequestSchema = z
  .object({
    id: z.string().min(1),
    source_fingerprint: fingerprintSchema,
    family: z.literal("file_approval"),
    task_id: nullableString,
    turn_id: nullableString,
    item_id: nullableString,
    received_at: z.iso.datetime({ offset: true }),
    status: z.enum(["pending", "responded", "stale"]),
    details: z
      .object({
        grant_root: nullableString,
        reason: nullableString,
      })
      .strict(),
  })
  .strict()

const inputRequestSchema = z
  .object({
    id: z.string().min(1),
    source_fingerprint: fingerprintSchema,
    family: z.literal("user_input"),
    task_id: nullableString,
    turn_id: nullableString,
    item_id: nullableString,
    received_at: z.iso.datetime({ offset: true }),
    status: z.enum(["pending", "responded", "stale"]),
    details: z
      .object({
        questions: z.array(
          z
            .object({
              id: nullableString,
              header: nullableString,
              question: nullableString,
              options: z.array(
                z.object({ label: nullableString, description: nullableString }).strict(),
              ),
            })
            .strict(),
        ),
      })
      .strict(),
  })
  .strict()

export const pendingTaskRequestSchema = z.discriminatedUnion("family", [
  commandRequestSchema,
  fileRequestSchema,
  inputRequestSchema,
])

const envelopeMetadata = {
  source: sourceSchema,
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: fingerprintSchema,
  coverage: coverageSchema,
  limitations: z.array(z.string()),
  error: z.null(),
}

export const taskIntegrationEnvelopeSchema = z
  .object({
    data: z.object({ integration: taskIntegrationSchema }).strict(),
    ...envelopeMetadata,
  })
  .strict()

export const taskListEnvelopeSchema = z
  .object({
    data: z
      .object({
        tasks: z.array(taskSchema),
        next_cursor: nullableString,
        backwards_cursor: nullableString,
        pending_requests: z.array(pendingTaskRequestSchema),
        integration: taskIntegrationSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const taskDetailEnvelopeSchema = z
  .object({
    data: z
      .object({
        task: taskSchema,
        pending_requests: z.array(pendingTaskRequestSchema),
        integration: taskIntegrationSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

const restartOperationSchema = z
  .object({
    integration: taskIntegrationSchema,
    operation: z.literal("adapter_restarted"),
  })
  .strict()

export const taskOperationEnvelopeSchema = z
  .object({
    data: restartOperationSchema,
    ...envelopeMetadata,
  })
  .strict()

export const taskEventSchema = z
  .object({
    sequence: z.number().int().nonnegative(),
    type: z.enum([
      "connection",
      "task_started",
      "task_status",
      "turn_started",
      "turn_completed",
      "item_started",
      "item_completed",
      "error",
      "request",
      "request_resolved",
    ]),
    observed_at: z.iso.datetime({ offset: true }),
    data: z.record(z.string(), z.json()),
  })
  .strict()

export type TaskIntegrationEnvelope = z.infer<typeof taskIntegrationEnvelopeSchema>
export type TaskListEnvelope = z.infer<typeof taskListEnvelopeSchema>
export type TaskDetailEnvelope = z.infer<typeof taskDetailEnvelopeSchema>
export type TaskOperationEnvelope = z.infer<typeof taskOperationEnvelopeSchema>
export type TaskEvent = z.infer<typeof taskEventSchema>

async function parsedResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return schema.parse(payload)
}

async function taskMutation(path: string, payload: object): Promise<TaskOperationEnvelope> {
  const nonce = mutationNonce()
  if (!nonce) throw new Error("The per-launch mutation nonce is unavailable; reload the dashboard.")
  return parsedResponse(
    await fetch(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Software-Factory-Nonce": nonce,
      },
      body: JSON.stringify(payload),
    }),
    taskOperationEnvelopeSchema,
  )
}

export function fetchTaskIntegration(signal?: AbortSignal): Promise<TaskIntegrationEnvelope> {
  return fetch("/api/v1/task-integration", {
    headers: { Accept: "application/json" },
    signal,
  }).then((response) => parsedResponse(response, taskIntegrationEnvelopeSchema))
}

export function fetchTasks(
  cursor?: string,
  limit = 50,
  signal?: AbortSignal,
): Promise<TaskListEnvelope> {
  const query = new URLSearchParams({ limit: String(limit) })
  if (cursor) query.set("cursor", cursor)
  return fetch(`/api/v1/tasks?${query}`, {
    headers: { Accept: "application/json" },
    signal,
  }).then((response) => parsedResponse(response, taskListEnvelopeSchema))
}

export function fetchTask(
  taskId: string,
  includeTurns = true,
  signal?: AbortSignal,
): Promise<TaskDetailEnvelope> {
  return fetch(
    `/api/v1/tasks/${encodeURIComponent(taskId)}?include_turns=${includeTurns}`,
    { headers: { Accept: "application/json" }, signal },
  ).then((response) => parsedResponse(response, taskDetailEnvelopeSchema))
}

export function restartTaskIntegration(): Promise<TaskOperationEnvelope> {
  return taskMutation("/api/v1/task-integration/restart", {
    confirmation: "restart-codex-adapter",
  })
}

export async function streamTaskEvents(
  onEvent: (event: TaskEvent) => void,
  signal: AbortSignal,
  after = 0,
): Promise<void> {
  const nonce = mutationNonce()
  if (!nonce) throw new Error("The per-launch event-stream nonce is unavailable; reload the dashboard.")
  const response = await fetch(`/api/v1/task-events?after=${after}`, {
    headers: {
      Accept: "text/event-stream",
      "X-Software-Factory-Nonce": nonce,
    },
    signal,
  })
  if (!response.ok) {
    throw new DashboardApiError(
      response.status,
      apiErrorEnvelopeSchema.parse(await response.json()),
    )
  }
  if (!response.body) throw new Error("The task event stream has no readable body.")
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (!signal.aborted) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += decoder.decode(value, { stream: true }).replaceAll("\r\n", "\n")
    let boundary = buffer.indexOf("\n\n")
    while (boundary >= 0) {
      const record = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const eventName = record
        .split("\n")
        .find((line) => line.startsWith("event: "))
        ?.slice(7)
      const data = record
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("\n")
      if (eventName !== "ready" && data) onEvent(taskEventSchema.parse(JSON.parse(data)))
      boundary = buffer.indexOf("\n\n")
    }
  }
}
