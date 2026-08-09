import { describe, expect, it } from "vitest"

import { healthEnvelopeSchema } from "@/lib/api"

const validHealth = {
  data: {
    status: "ok",
    service: { name: "software-factory-dashboard", version: "0.1.0" },
    integrations: {
      frontend: { status: "available", reason: null },
      project_sources: { status: "unavailable", reason: "Block 2" },
      codex_app_server: { status: "unavailable", reason: "Block 5" },
    },
  },
  source: {
    kind: "runtime",
    identity: "software-factory-dashboard/health",
    revision: "0.1.0",
  },
  observed_at: "2026-08-09T08:00:00.000Z",
  fingerprint: "a".repeat(64),
  coverage: {
    status: "partial",
    observed: ["runtime", "frontend-build"],
    missing: ["project-sources", "codex-app-server"],
  },
  limitations: ["Runtime readiness only"],
  error: null,
} as const

describe("healthEnvelopeSchema", () => {
  it("accepts the shared Block 1 API envelope", () => {
    expect(healthEnvelopeSchema.parse(validHealth).data.status).toBe("ok")
  })

  it("rejects a malformed boundary instead of inventing defaults", () => {
    const malformed = {
      ...validHealth,
      fingerprint: "not-a-fingerprint",
      coverage: { status: "complete", observed: [] },
    }
    expect(() => healthEnvelopeSchema.parse(malformed)).toThrow()
  })
})
