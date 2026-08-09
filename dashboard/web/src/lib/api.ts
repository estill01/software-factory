import { z } from "zod"

export const availabilitySchema = z.object({
  status: z.enum(["available", "unavailable"]),
  reason: z.string().nullable(),
})

export const sourceSchema = z.object({
  kind: z.string().min(1),
  identity: z.string().min(1),
  revision: z.string().min(1),
})

export const coverageSchema = z.object({
  status: z.enum(["complete", "partial"]),
  observed: z.array(z.string()),
  missing: z.array(z.string()),
})

export const errorSchema = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
  retryable: z.boolean(),
})

export const healthDataSchema = z.object({
  status: z.literal("ok"),
  service: z.object({
    name: z.literal("software-factory-dashboard"),
    version: z.string().min(1),
  }),
  integrations: z.object({
    frontend: availabilitySchema,
    project_sources: availabilitySchema,
    codex_app_server: availabilitySchema,
  }),
})

const envelopeMetadataShape = {
  source: sourceSchema,
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: z.string().regex(/^[0-9a-f]{64}$/),
  coverage: coverageSchema,
  limitations: z.array(z.string()),
}

export const healthEnvelopeSchema = z.object({
  data: healthDataSchema,
  ...envelopeMetadataShape,
  error: z.null(),
})

export const apiErrorEnvelopeSchema = z.object({
  data: z.null(),
  ...envelopeMetadataShape,
  error: errorSchema,
})

export type HealthEnvelope = z.infer<typeof healthEnvelopeSchema>
export type ApiErrorEnvelope = z.infer<typeof apiErrorEnvelopeSchema>

export class DashboardApiError extends Error {
  readonly code: string
  readonly retryable: boolean
  readonly status: number

  constructor(status: number, envelope: ApiErrorEnvelope) {
    super(envelope.error.message)
    this.name = "DashboardApiError"
    this.code = envelope.error.code
    this.retryable = envelope.error.retryable
    this.status = status
  }
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthEnvelope> {
  const response = await fetch("/api/v1/health", {
    headers: { Accept: "application/json" },
    signal,
  })
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return healthEnvelopeSchema.parse(payload)
}

export function mutationNonce(): string | null {
  return (
    document
      .querySelector<HTMLMetaElement>('meta[name="software-factory-mutation-nonce"]')
      ?.content.trim() || null
  )
}
