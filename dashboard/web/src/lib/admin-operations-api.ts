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

const internalOperationHrefSchema = z
  .string()
  .max(2_000)
  .regex(/^\/(?:[A-Za-z0-9._~:@-]+(?:\/[A-Za-z0-9._~:@-]+)*)?$/)
  .refine((href) => !href.split("/").some((segment) => segment === "." || segment === ".."), {
    message: "Operation links must remain inside the dashboard.",
  })

const operationLinkSchema = z
  .object({
    label: z.string().min(1).max(120),
    href: internalOperationHrefSchema,
  })
  .strict()

const operationSemanticValueSchema = z
  .object({
    posture: z.enum(["exact", "unavailable", "redacted", "not-applicable"]),
    value: z.string().min(1).max(500).nullable(),
  })
  .strict()
  .superRefine((value, context) => {
    if ((value.posture === "exact") !== (value.value !== null)) {
      context.addIssue({
        code: "custom",
        message: "Only exact semantic values may carry text.",
      })
    }
  })

export const operationSemanticChangeSchema = z
  .object({
    id: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$/),
    subject: z.string().min(1).max(200),
    kind: z.enum(["added", "removed", "changed", "preserved"]),
    before: operationSemanticValueSchema,
    after: operationSemanticValueSchema,
    owner: z.string().min(1).max(300),
    source_identity: z.string().min(1).max(400),
    source_revision: fingerprintSchema,
    currentness_fingerprint: fingerprintSchema,
    links: z.array(operationLinkSchema).max(2),
  })
  .strict()
  .superRefine((row, context) => {
    const same = row.before.posture === row.after.posture
      && row.before.value === row.after.value
    const valid = row.kind === "added"
      ? row.before.posture !== "exact" && row.after.posture === "exact"
      : row.kind === "removed"
        ? row.before.posture === "exact" && row.after.posture !== "exact"
        : row.kind === "preserved"
          ? row.before.posture === "exact" && row.after.posture === "exact" && same
          : !same
    if (!valid) {
      context.addIssue({
        code: "custom",
        message: "Semantic change kind contradicts its before and after values.",
      })
    }
  })

export const operationSemanticChangesSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    complete: z.boolean(),
    rows: z.array(operationSemanticChangeSchema).max(32),
    limitations: z.array(z.string().min(1).max(500)).min(1).max(4),
  })
  .strict()
  .superRefine((value, context) => {
    const available = value.status === "available"
    if (
      available !== value.complete
      || available !== (value.rows.length > 0)
      || new Set(value.rows.map((row) => row.id)).size !== value.rows.length
    ) {
      context.addIssue({
        code: "custom",
        message: "Semantic comparison availability, completeness, and row identity disagree.",
      })
    }
  })

const routeGateSchema = z
  .object({
    status: z.enum(["not-required", "allowed", "unavailable"]),
    target_thread: z.string().nullable(),
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
    semantic_changes: operationSemanticChangesSchema,
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
export type OperationSemanticChanges = z.infer<typeof operationSemanticChangesSchema>
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
