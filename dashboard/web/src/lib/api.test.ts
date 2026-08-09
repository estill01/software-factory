import { describe, expect, it, vi } from "vitest"

import {
  apiErrorEnvelopeSchema,
  DashboardApiError,
  fetchHealth,
  healthEnvelopeSchema,
} from "@/lib/api"

const validHealth = {
  data: {
    status: "ok",
    service: { name: "software-factory-dashboard", version: "0.1.0" },
    integrations: {
      frontend: { status: "available", reason: null },
      project_sources: { status: "unavailable", reason: "Block 2" },
      tracker_sources: { status: "unavailable", reason: "Block 3" },
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

const errorEnvelope = {
  data: null,
  source: {
    kind: "runtime",
    identity: "software-factory-dashboard/http",
    revision: "0.1.0",
  },
  observed_at: "2026-08-09T08:00:00.000Z",
  fingerprint: "b".repeat(64),
  coverage: { status: "partial", observed: ["runtime"], missing: [] },
  limitations: [],
  error: { code: "not_found", message: "API route was not found.", retryable: false },
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

  it("validates the server's structured error envelope", () => {
    expect(apiErrorEnvelopeSchema.parse(errorEnvelope).error.code).toBe("not_found")
  })

  it("parses a non-success response before surfacing its structured error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => errorEnvelope,
      }),
    )

    const request = fetchHealth()
    await expect(request).rejects.toBeInstanceOf(DashboardApiError)
    await expect(request).rejects.toMatchObject({
      name: "DashboardApiError",
      code: "not_found",
      retryable: false,
      status: 404,
    })
  })
})
