import { z } from "zod"

import {
  apiErrorEnvelopeSchema,
  coverageSchema,
  DashboardApiError,
  mutationNonce,
  sourceSchema,
} from "@/lib/api"

const fingerprintSchema = z.string().regex(/^[0-9a-f]{64}$/)
const jsonObjectSchema = z.record(z.string(), z.unknown())

export const operationTargetSchema = z
  .object({
    kind: z.string().min(1),
    id: z.string().min(1),
    project_id: z.string().min(1).nullable(),
  })
  .strict()

const operationLinkSchema = z
  .object({
    label: z.string().min(1),
    href: z.string().startsWith("/"),
  })
  .strict()

const routeGateSchema = z
  .object({
    status: z.enum(["not-required", "allowed", "unavailable"]),
    recipient: z.string().nullable(),
    purpose: z.string().nullable(),
    source_record: z.string().nullable(),
    required_action: z.string().nullable(),
    action_hash: fingerprintSchema.nullable(),
    policy_fingerprint: fingerprintSchema.nullable(),
    binding_fingerprint: fingerprintSchema.nullable(),
  })
  .strict()

const operationPreviewSchema = z
  .object({
    effect: z.string().min(1),
    risk: z.string().min(1),
    recipient: z.string().nullable(),
    source_fingerprint: fingerprintSchema,
    source_evidence: jsonObjectSchema,
    route_gate: routeGateSchema,
    consequences: z
      .object({ ordinary: z.array(z.string()), failure: z.array(z.string()) })
      .strict(),
    confirmation: z
      .object({
        class: z.string().min(1),
        prompt: z.string().min(1),
        expected_value: z.string().min(1),
      })
      .strict(),
    expected_postcondition: z.string().min(1),
    idempotency: z.string().min(1),
    limitations: z.array(z.string()),
    expires_at: z.iso.datetime({ offset: true }),
  })
  .strict()

export const operationStateSchema = z.enum([
  "previewed",
  "confirmed",
  "requested",
  "awaiting-approval",
  "awaiting-input",
  "verifying",
  "applied",
  "failed",
  "unverified",
  "cancelled",
])

export const operationRecordSchema = z
  .object({
    id: z.string().startsWith("op_"),
    type: z.string().min(1),
    target: operationTargetSchema,
    state: operationStateSchema,
    owner: z.string().min(1),
    authority: z.array(z.string()),
    preview: operationPreviewSchema,
    history: z.array(
      z
        .object({
          state: operationStateSchema,
          observed_at: z.iso.datetime({ offset: true }),
        })
        .strict(),
    ),
    request_evidence: jsonObjectSchema.nullable(),
    verification_evidence: jsonObjectSchema.nullable(),
    links: z.array(operationLinkSchema),
    failure: z
      .object({ code: z.string().min(1), message: z.string().min(1) })
      .strict()
      .nullable(),
  })
  .strict()

export const operationDefinitionSchema = z
  .object({
    type: z.string().min(1),
    target_kind: z.string().min(1),
    input_schema: jsonObjectSchema,
    owner: z.string().min(1),
    authority: z.array(z.string()),
    consequences: z
      .object({ ordinary: z.array(z.string()), failure: z.array(z.string()) })
      .strict(),
    confirmation_class: z.string().min(1),
    idempotency: z.string().min(1),
    expected_postcondition: z.string().min(1),
    timeout_seconds: z.number().nonnegative(),
    limitations: z.array(z.string()),
    status: z.enum(["supported", "unavailable"]),
    reason: z.string().nullable(),
  })
  .strict()

const frameworkSchema = z
  .object({
    ephemeral: z.literal(true),
    registered_operations: z.array(operationDefinitionSchema),
    activity: z.array(operationRecordSchema),
    restart_posture: z.string().min(1),
  })
  .strict()

const envelopeMetadata = {
  source: sourceSchema,
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: fingerprintSchema,
  coverage: coverageSchema,
  limitations: z.array(z.string()),
  error: z.null(),
}

export const operationFrameworkEnvelopeSchema = z
  .object({
    data: z.object({ framework: frameworkSchema }).strict(),
    ...envelopeMetadata,
  })
  .strict()

export const operationEnvelopeSchema = z
  .object({
    data: z.object({ operation: operationRecordSchema }).strict(),
    ...envelopeMetadata,
  })
  .strict()

export const operationPreviewEnvelopeSchema = z
  .object({
    data: z
      .object({
        operation: operationRecordSchema,
        preview_token: z.string().min(20),
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const operationPreviewRequestSchema = z
  .object({
    operation_type: z.string().min(1),
    target: operationTargetSchema,
    input: jsonObjectSchema,
  })
  .strict()

export const operationExecuteRequestSchema = operationPreviewRequestSchema
  .extend({
    preview_token: z.string().min(20),
    confirmation: z
      .object({ class: z.string().min(1), value: z.string().min(1) })
      .strict(),
  })
  .strict()

export type OperationRecord = z.infer<typeof operationRecordSchema>
export type OperationPreviewRequest = z.infer<typeof operationPreviewRequestSchema>
export type OperationPreviewEnvelope = z.infer<typeof operationPreviewEnvelopeSchema>
export type OperationFrameworkEnvelope = z.infer<typeof operationFrameworkEnvelopeSchema>

async function parsedResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return schema.parse(payload)
}

async function operationMutation<T>(
  path: string,
  payload: object,
  schema: z.ZodType<T>,
): Promise<T> {
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
    schema,
  )
}

export async function fetchOperationFramework(
  signal?: AbortSignal,
): Promise<OperationFrameworkEnvelope> {
  return parsedResponse(
    await fetch("/api/v1/operations", {
      headers: { Accept: "application/json" },
      signal,
    }),
    operationFrameworkEnvelopeSchema,
  )
}

export function previewOperation(
  request: OperationPreviewRequest,
): Promise<OperationPreviewEnvelope> {
  return operationMutation(
    "/api/v1/operations/preview",
    operationPreviewRequestSchema.parse(request),
    operationPreviewEnvelopeSchema,
  )
}

export function executeOperation(
  request: z.infer<typeof operationExecuteRequestSchema>,
): Promise<z.infer<typeof operationEnvelopeSchema>> {
  return operationMutation(
    "/api/v1/operations/execute",
    operationExecuteRequestSchema.parse(request),
    operationEnvelopeSchema,
  )
}

export function cancelOperation(
  operationId: string,
): Promise<z.infer<typeof operationEnvelopeSchema>> {
  return operationMutation(
    `/api/v1/operations/${encodeURIComponent(operationId)}/cancel`,
    { confirmation: "cancel-before-request" },
    operationEnvelopeSchema,
  )
}
