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

export const healthEnvelopeSchema = z.object({
  data: healthDataSchema,
  source: sourceSchema,
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: z.string().regex(/^[0-9a-f]{64}$/),
  coverage: coverageSchema,
  limitations: z.array(z.string()),
  error: z.null(),
})

export type HealthEnvelope = z.infer<typeof healthEnvelopeSchema>

export async function fetchHealth(signal?: AbortSignal): Promise<HealthEnvelope> {
  const response = await fetch("/api/v1/health", {
    headers: { Accept: "application/json" },
    signal,
  })
  if (!response.ok) {
    throw new Error(`Runtime health failed with HTTP ${response.status}`)
  }
  return healthEnvelopeSchema.parse(await response.json())
}

export function mutationNonce(): string | null {
  return (
    document
      .querySelector<HTMLMetaElement>('meta[name="software-factory-mutation-nonce"]')
      ?.content.trim() || null
  )
}
