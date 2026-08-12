import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  executeOperation,
  fetchOperationFramework,
  operationFrameworkEnvelopeSchema,
  operationRecordSchema,
  previewOperation,
} from "@/lib/admin-operations-api"

const hash = "a".repeat(64)
const observedAt = "2026-08-10T08:00:00.000Z"

const operation = {
  id: "op_example",
  type: "test.fixture-set",
  target: { kind: "test-fixture", id: "fixture-1", project_id: "test" },
  state: "previewed",
  owner: "tests/deterministic-owner",
  authority: ["Block 10 deterministic test owner"],
  preview: {
    effect: "Set fixture-1 to next",
    risk: "Changes an in-memory fixture.",
    recipient: "test-recipient",
    semantic_changes: {
      status: "available",
      complete: true,
      rows: [{
        id: "fixture-value",
        subject: "Fixture value",
        kind: "changed",
        before: { posture: "exact", value: "initial" },
        after: { posture: "exact", value: "next" },
        owner: "tests/deterministic-owner",
        source_identity: "test-fixture:fixture-1",
        source_revision: hash,
        currentness_fingerprint: hash,
        links: [{ label: "Fixture", href: "/admin" }],
      }],
      limitations: ["Read-only owner-supplied comparison."],
    },
    source_fingerprint: hash,
    source_evidence: { version: 1 },
    route_gate: {
      status: "allowed",
      target_thread: "fixture-target",
      recipient: "test-recipient",
      purpose: "deterministic-owner-proof",
      source_record: "TEST-1",
      required_action: "Set fixture-1 to next",
      action_hash: hash,
      policy_fingerprint: hash,
      binding_fingerprint: hash,
    },
    consequences: { ordinary: ["Fixture changes."], failure: ["Verification may fail."] },
    confirmation: {
      class: "typed-phrase",
      prompt: "Type APPLY TEST FIXTURE",
      expected_value: "APPLY TEST FIXTURE",
    },
    expected_postcondition: "The fixture reports next.",
    idempotency: "One owner request per token.",
    limitations: ["Test only."],
    expires_at: "2026-08-10T08:02:00.000Z",
  },
  history: [{ state: "previewed", observed_at: observedAt }],
  request_evidence: null,
  verification_evidence: null,
  links: [],
  failure: null,
} as const

const envelopeMetadata = {
  source: { kind: "administrative-operation", identity: "operations", revision: hash },
  observed_at: observedAt,
  fingerprint: hash,
  coverage: {
    status: "partial",
    observed: ["ephemeral-operation-state"],
    missing: ["prior-server-session-operation-state"],
  },
  limitations: ["Process-local."],
  error: null,
} as const

describe("administrative operation API", () => {
  beforeEach(() => {
    document.head.innerHTML = '<meta name="software-factory-mutation-nonce" content="launch-nonce">'
    vi.restoreAllMocks()
  })

  it("validates the closed registry/activity contract", () => {
    const parsed = operationFrameworkEnvelopeSchema.parse({
      data: {
        framework: {
          ephemeral: true,
          registered_operations: [],
          activity: [operation],
          restart_posture: "Reconstruct from the canonical owner.",
        },
      },
      ...envelopeMetadata,
    })
    expect(parsed.data.framework.activity[0].state).toBe("previewed")
    expect(parsed.data.framework.activity[0].preview.semantic_changes.rows[0].kind).toBe("changed")
    expect(() => operationRecordSchema.parse({ ...operation, command: "arbitrary" })).toThrow()
  })

  it("rejects contradictory semantic rows, false availability, and unsafe source links", () => {
    const row = operation.preview.semantic_changes.rows[0]
    const withChanges = (semantic_changes: unknown) => ({
      ...operation,
      preview: { ...operation.preview, semantic_changes },
    })

    expect(() => operationRecordSchema.parse(withChanges({
      ...operation.preview.semantic_changes,
      rows: [{ ...row, kind: "preserved", after: { posture: "exact", value: "different" } }],
    }))).toThrow()
    expect(() => operationRecordSchema.parse(withChanges({
      status: "unavailable",
      complete: false,
      rows: [row],
      limitations: ["Unavailable cannot retain rows."],
    }))).toThrow()
    expect(() => operationRecordSchema.parse(withChanges({
      ...operation.preview.semantic_changes,
      rows: [{ ...row, links: [{ label: "Unsafe", href: "/safe/%2e%2e/admin" }] }],
    }))).toThrow()
    expect(() => operationRecordSchema.parse(withChanges({
      ...operation.preview.semantic_changes,
      rows: [{ ...row, currentness_fingerprint: "not-exact" }],
    }))).toThrow()
    expect(() => operationRecordSchema.parse(withChanges({
      ...operation.preview.semantic_changes,
      rows: [row, row],
    }))).toThrow()
  })

  it("sends the nonce and only the typed preview and execution fields", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({
        data: { operation, preview_token: "p".repeat(32) },
        ...envelopeMetadata,
      }), { status: 201, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        data: { operation: { ...operation, state: "applied", history: [
          ...operation.history,
          { state: "applied", observed_at: observedAt },
        ] } },
        ...envelopeMetadata,
      }), { status: 200, headers: { "Content-Type": "application/json" } }))

    const request = {
      operation_type: operation.type,
      target: operation.target,
      input: { mode: "success", value: "next" },
    }
    const preview = await previewOperation(request)
    await executeOperation({
      ...request,
      preview_token: preview.data.preview_token,
      confirmation: { class: "typed-phrase", value: "APPLY TEST FIXTURE" },
    })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    for (const call of fetchMock.mock.calls) {
      expect(new Headers(call[1]?.headers).get("X-Software-Factory-Nonce")).toBe("launch-nonce")
    }
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual(request)
  })

  it("loads the read-only framework without a mutation nonce", async () => {
    document.head.innerHTML = ""
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      data: {
        framework: {
          ephemeral: true,
          registered_operations: [],
          activity: [],
          restart_posture: "Reconstruct from the canonical owner.",
        },
      },
      ...envelopeMetadata,
    }), { status: 200, headers: { "Content-Type": "application/json" } }))

    expect((await fetchOperationFramework()).data.framework.activity).toEqual([])
  })
})
