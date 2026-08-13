import { afterEach, describe, expect, it, vi } from "vitest"

import {
  fetchFactoryFloor,
  floorEnvelopeSchema,
} from "@/lib/floor-api"
import { makeFactoryFloorEnvelope } from "@/test/factory-floor-fixture"

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("Factory Floor API contract", () => {
  it("validates the composed three-project floor and preserves owner distinctions", () => {
    const parsed = floorEnvelopeSchema.parse(makeFactoryFloorEnvelope())

    expect(parsed.data.projects).toHaveLength(3)
    expect(parsed.data.rows.map((row) => row.light.posture)).toEqual(["red", "green", "neutral"])
    expect(parsed.data.conclusions[0].author_status).toBe("unavailable")
    expect(parsed.data.accepted_outcomes[0].accepted_at).toBeNull()
    expect(parsed.data.attention_summary).toEqual({
      total: 2,
      returned: 2,
      truncated: false,
      critical_total: 1,
      critical_returned: 1,
      critical_omitted: 0,
    })
    expect(parsed.data.metrics.find((metric) => metric.key === "api-equivalent")).toMatchObject({
      label: "API-equivalent estimate",
      unit: "USD estimate",
      estimate: true,
    })
    expect(parsed.data.rows[0].work.block_claims).toMatchObject({
      posture: "exact",
      tracker_total: { value: 26, posture: "exact" },
    })
    expect(parsed.data.rows[0].work.block_claims.claims.map((claim) => claim.source))
      .toEqual(["tracker", "task", "supervision"])
    expect(parsed.data.rows[0].work.block_claims.claims[0].blocks[0]).toMatchObject({
      number: 6,
      title: "Factory Floor composition",
      status: "in-progress",
    })
  })

  it("rejects untyped extra operational fields at the API edge", () => {
    const candidate = makeFactoryFloorEnvelope() as unknown as Record<string, unknown>
    const data = candidate.data as Record<string, unknown>
    const rows = data.rows as Array<Record<string, unknown>>
    rows[0].synthetic_health_score = 98

    expect(() => floorEnvelopeSchema.parse(candidate)).toThrow()
  })

  it("rejects confident malformed Block totals and incomplete claim identities", () => {
    const malformedTotal = makeFactoryFloorEnvelope()
    malformedTotal.data.rows[0].work.block_claims.tracker_total.value = 0
    expect(() => floorEnvelopeSchema.parse(malformedTotal)).toThrow()

    const malformedPartialTotal = makeFactoryFloorEnvelope()
    malformedPartialTotal.data.rows[0].work.block_claims.tracker_total.posture = "partial"
    malformedPartialTotal.data.rows[0].work.block_claims.tracker_total.value = 0
    expect(() => floorEnvelopeSchema.parse(malformedPartialTotal)).toThrow()

    const missingClaim = makeFactoryFloorEnvelope()
    missingClaim.data.rows[0].work.block_claims.claims.pop()
    expect(() => floorEnvelopeSchema.parse(missingClaim)).toThrow()
  })

  it("parses the success envelope and structured failure before returning", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => makeFactoryFloorEnvelope(),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          data: null,
          source: {
            kind: "runtime",
            identity: "software-factory-dashboard/http",
            revision: "0.1.0",
          },
          observed_at: "2026-08-09T17:55:00.000Z",
          fingerprint: "8".repeat(64),
          coverage: { status: "partial", observed: ["runtime"], missing: [] },
          limitations: [],
          error: { code: "floor_unavailable", message: "Floor unavailable.", retryable: true },
        }),
      })
    vi.stubGlobal("fetch", fetchMock)

    await expect(fetchFactoryFloor()).resolves.toMatchObject({
      data: { summary: { registered_projects: 3 } },
    })
    await expect(fetchFactoryFloor()).rejects.toMatchObject({
      code: "floor_unavailable",
      status: 503,
      retryable: true,
    })
  })
})
