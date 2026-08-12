import { z } from "zod"

import {
  apiErrorEnvelopeSchema,
  coverageSchema,
  DashboardApiError,
  sourceSchema,
} from "@/lib/api"

const timestamp = z.iso.datetime({ offset: true })
const nullableText = z.string().nullable()
const nullableTimestamp = timestamp.nullable()
const nullableRevision = z.string().min(1).nullable()
const nonnegativeInteger = z.number().int().nonnegative()

const recordRefSchema = z
  .object({
    record_id: nullableText,
    kind: nullableText,
    status: nullableText,
    severity: nullableText,
    category: nullableText,
    summary: nullableText,
    action: nullableText,
    resolution: nullableText,
    observed_at: nullableTimestamp,
    source: z.unknown().nullable(),
  })
  .strict()

const sourceRefSchema = z
  .object({
    kind: z.string().min(1),
    identity: z.string().min(1),
    record_id: nullableText,
    path: nullableText,
    line: nonnegativeInteger.nullable(),
    revision: nullableRevision,
    route: z.string().startsWith("/"),
  })
  .strict()

const roleSchema = z
  .object({
    role: nullableText,
    label: nullableText,
    thread_id: nullableText,
    binding_status: nullableText,
    task_status: z.enum(["active", "idle", "terminal", "unavailable", "unknown"]),
    automation_status: nullableText,
  })
  .strict()

const trackerBindingSchema = z
  .object({
    status: z.enum(["exact", "candidate", "ambiguous", "unavailable"]),
    id: nullableText,
    title: nullableText,
    relative_path: nullableText,
    candidates: z.array(z.string()),
  })
  .strict()

const blockSourceRefSchema = z
  .object({
    number: nonnegativeInteger,
    title: nullableText,
    status: nullableText,
    line: z.number().int().positive().nullable(),
    route: z.string().startsWith("/"),
  })
  .strict()

const activeBlockClaimSchema = z
  .object({
    source: z.enum(["tracker", "task", "supervision"]),
    label: z.string().min(1),
    status: z.enum(["exact", "none", "partial", "unavailable", "conflict"]),
    blocks: z.array(blockSourceRefSchema),
    range: z
      .object({ start: nonnegativeInteger, end: nonnegativeInteger })
      .strict()
      .nullable(),
    reason: z.string().min(1),
    source_identity: z.string().min(1),
    route: z.string().startsWith("/"),
  })
  .strict()

const blockClaimsSchema = z
  .object({
    posture: z.enum(["exact", "none", "conflict", "partial", "unavailable"]),
    tracker_total: z
      .object({
        value: nonnegativeInteger.nullable(),
        posture: z.enum(["exact", "partial", "unavailable"]),
        reason: z.string().min(1),
      })
      .strict(),
    tracker_progress: z
      .object({
        accepted: nonnegativeInteger.nullable(),
        remaining: nonnegativeInteger.nullable(),
        posture: z.enum(["exact", "partial", "conflict", "unavailable"]),
        is_complete: z.boolean().nullable(),
        reason: z.string().min(1),
      })
      .strict(),
    claims: z.array(activeBlockClaimSchema).length(3),
  })
  .strict()
  .superRefine((value, context) => {
    if (value.tracker_total.posture !== "unavailable" && (value.tracker_total.value === null || value.tracker_total.value < 1)) {
      context.addIssue({
        code: "custom",
        message: "A displayed tracker total must contain at least one verifier-parsed Block.",
        path: ["tracker_total", "value"],
      })
    }
    if (value.tracker_total.posture === "unavailable" && value.tracker_total.value !== null) {
      context.addIssue({
        code: "custom",
        message: "An unavailable tracker total cannot expose a confident value.",
        path: ["tracker_total", "value"],
      })
    }
    const progress = value.tracker_progress
    if (progress.posture === "unavailable") {
      if (progress.accepted !== null || progress.remaining !== null || progress.is_complete !== null) {
        context.addIssue({
          code: "custom",
          message: "Unavailable tracker progress cannot expose confident counts or completion.",
          path: ["tracker_progress"],
        })
      }
    } else if (progress.accepted === null || progress.remaining === null) {
      context.addIssue({
        code: "custom",
        message: "Available tracker progress requires accepted and remaining Block counts.",
        path: ["tracker_progress"],
      })
    } else if (
      value.tracker_total.value === null
      || progress.accepted + progress.remaining !== value.tracker_total.value
    ) {
      context.addIssue({
        code: "custom",
        message: "Accepted and remaining Blocks must equal the verifier-parsed total.",
        path: ["tracker_progress"],
      })
    }
    if (progress.posture === "exact") {
      if (value.tracker_total.posture !== "exact" || progress.is_complete === null) {
        context.addIssue({
          code: "custom",
          message: "Exact tracker progress requires an exact total and explicit completion state.",
          path: ["tracker_progress"],
        })
      } else if (progress.is_complete !== (progress.remaining === 0)) {
        context.addIssue({
          code: "custom",
          message: "Tracker completion must agree with the exact remaining Block count.",
          path: ["tracker_progress", "is_complete"],
        })
      }
    } else if (progress.is_complete !== null) {
      context.addIssue({
        code: "custom",
        message: "Partial or unavailable progress cannot claim tracker completion.",
        path: ["tracker_progress", "is_complete"],
      })
    }
    const sources = value.claims.map((claim) => claim.source)
    if (new Set(sources).size !== 3 || !["tracker", "task", "supervision"].every((source) => sources.includes(source as typeof sources[number]))) {
      context.addIssue({
        code: "custom",
        message: "Block claims must preserve one tracker, task, and supervision source.",
        path: ["claims"],
      })
    }
  })

export const floorRowSchema = z
  .object({
    id: z.string().min(1),
    project: z
      .object({
        status: z.enum(["bound", "run-only", "task-only", "ambiguous", "unassigned"]),
        project_id: nullableText,
        label: z.string().min(1),
        reason: z.string().min(1),
      })
      .strict(),
    implementation: z
      .object({
        task_id: z.string().min(1),
        name: nullableText,
        status: z.enum(["active", "idle", "terminal", "unavailable", "unknown"]),
        status_label: z.string().min(1),
        updated_at: nullableTimestamp,
        source_status: z.enum(["available", "unavailable"]),
      })
      .strict(),
    supervision: z
      .object({
        run_id: nullableText,
        group_id: nullableText,
        target_thread_id: z.string().min(1),
        status: z.enum([
          "active",
          "unmonitored",
          "unavailable",
          "paused",
          "completed",
          "stopped",
          "failed",
          "blocked",
        ]),
        status_label: z.string().min(1),
        binding_integrity: z.string().min(1),
        roles: z.array(roleSchema),
        role_count: nonnegativeInteger,
        last_check: recordRefSchema.nullable(),
        next_check: z
          .object({
            status: z.enum(["available", "unavailable"]),
            at: nullableTimestamp,
            reason: z.string().min(1),
          })
          .strict(),
      })
      .strict(),
    work: z
      .object({
        active_block: nullableText,
        checkpoint: nullableText,
        mission_root: nullableText,
        last_action: nullableText,
        tracker: trackerBindingSchema,
        block_claims: blockClaimsSchema,
      })
      .strict(),
    issues: z
      .object({
        incidents: nonnegativeInteger,
        decisions: nonnegativeInteger,
        transitions: nonnegativeInteger,
        total: nonnegativeInteger,
      })
      .strict(),
    conclusion: recordRefSchema.nullable(),
    light: z
      .object({
        posture: z.enum(["red", "amber", "green", "neutral"]),
        label: z.string().min(1),
        reason: z.string().min(1),
        observed_at: nullableTimestamp,
        source_identity: z.string().min(1),
        completion_claim: z.literal(false),
      })
      .strict(),
    freshness: z
      .object({
        status: z.enum(["current", "unavailable"]),
        observed_at: nullableTimestamp,
        reason: z.string().min(1),
      })
      .strict(),
    disagreements: z.array(z.string().min(1)),
    detail: z
      .object({
        kind: z.enum(["run", "task"]),
        id: z.string().min(1),
        route: z.string().startsWith("/"),
        source_refs: z.array(sourceRefSchema),
      })
      .strict(),
  })
  .strict()

export const floorAttentionSchema = z
  .object({
    id: z.string().min(1),
    rank: nonnegativeInteger,
    rule: nullableText,
    severity: z.enum(["red", "amber", "neutral"]),
    target_thread_id: nullableText,
    project_id: nullableText,
    reason: nullableText,
    owner: nullableText,
    safe_frontier: nullableText,
    observed_at: nullableTimestamp,
    source: z
      .object({
        identity: nullableText,
        record_id: nullableText,
        path: nullableText,
        line: nonnegativeInteger.nullable(),
        route: z.string().startsWith("/"),
      })
      .strict(),
  })
  .strict()

export const floorConclusionSchema = z
  .object({
    id: z.string().min(1),
    target_thread_id: z.string().min(1),
    target_label: z.string().min(1),
    author: nullableText,
    author_status: z.literal("unavailable"),
    disposition: nullableText,
    summary: nullableText,
    next_action: nullableText,
    current: z.boolean(),
    superseded: z.boolean(),
    observed_at: nullableTimestamp,
    source: z
      .object({
        identity: z.string().min(1),
        record_id: nullableText,
        path: nullableText,
        line: nonnegativeInteger.nullable(),
        revision: nullableRevision,
        route: z.string().startsWith("/"),
      })
      .strict(),
    retained_open_work: nonnegativeInteger.nullable(),
  })
  .strict()

export const floorOutcomeSchema = z
  .object({
    id: z.string().min(1),
    project_id: z.string().min(1),
    tracker_id: z.string().min(1),
    tracker_title: z.string().min(1),
    block: nonnegativeInteger,
    title: z.string().min(1),
    status: z.literal("accepted"),
    evidence_revision: z.string().min(1),
    accepted_at: z.null(),
    observed_at: timestamp,
    currentness: z.enum(["current", "stale-or-dirty"]),
    retained_open_work: nonnegativeInteger.nullable(),
    source: z
      .object({
        identity: nullableText,
        record_id: z.null(),
        path: nullableText,
        line: nonnegativeInteger.nullable(),
        revision: nullableRevision,
        route: z.string().startsWith("/"),
      })
      .strict(),
  })
  .strict()

export const floorMetricSchema = z
  .object({
    key: z.string().min(1),
    label: z.string().min(1),
    value: z.number().nullable(),
    unit: z.string().min(1),
    period: z.string().min(1),
    coverage: z.string().min(1),
    source_identity: z.string().min(1),
    estimate: z.boolean(),
    available: z.boolean(),
  })
  .strict()

export const floorSourceHealthSchema = z
  .object({
    family: z.enum(["catalog", "operations", "trackers", "tasks"]),
    label: z.string().min(1),
    status: z.enum(["available", "partial", "unavailable"]),
    identity: z.string().min(1),
    revision: nullableRevision,
    observed_at: timestamp,
    reason: z.string().min(1),
    coverage: coverageSchema,
  })
  .strict()

export const floorDataSchema = z
  .object({
    catalog_fingerprint: z.string().regex(/^[0-9a-f]{64}$/).nullable(),
    recovered_from_previous: z.boolean(),
    summary: z
      .object({
        registered_projects: nonnegativeInteger,
        active_implementations: nonnegativeInteger.nullable(),
        supervisor_groups: nonnegativeInteger.nullable(),
        action_required: nonnegativeInteger,
        postures: z
          .object({
            red: nonnegativeInteger,
            amber: nonnegativeInteger,
            green: nonnegativeInteger,
            neutral: nonnegativeInteger,
          })
          .strict(),
      })
      .strict(),
    projects: z.array(
      z.object({ id: z.string().min(1), label: z.string().min(1) }).strict(),
    ),
    rows: z.array(floorRowSchema),
    rows_truncated: z.boolean(),
    attention: z.array(floorAttentionSchema),
    attention_summary: z
      .object({
        total: nonnegativeInteger,
        returned: nonnegativeInteger,
        truncated: z.boolean(),
        critical_total: nonnegativeInteger,
        critical_returned: nonnegativeInteger,
        critical_omitted: nonnegativeInteger,
      })
      .strict(),
    conclusions: z.array(floorConclusionSchema),
    accepted_outcomes: z.array(floorOutcomeSchema),
    metrics: z.array(floorMetricSchema),
    source_health: z.array(floorSourceHealthSchema).length(4),
    fingerprint: z.string().regex(/^[0-9a-f]{64}$/),
  })
  .strict()

export const floorEnvelopeSchema = z
  .object({
    data: floorDataSchema,
    source: sourceSchema,
    observed_at: timestamp,
    fingerprint: z.string().regex(/^[0-9a-f]{64}$/),
    coverage: coverageSchema,
    limitations: z.array(z.string()),
    error: z.null(),
  })
  .strict()

export type FactoryFloorEnvelope = z.infer<typeof floorEnvelopeSchema>
export type FactoryFloorData = z.infer<typeof floorDataSchema>
export type FactoryFloorRow = z.infer<typeof floorRowSchema>
export type FactoryFloorAttention = z.infer<typeof floorAttentionSchema>
export type FactoryFloorConclusion = z.infer<typeof floorConclusionSchema>
export type FactoryFloorOutcome = z.infer<typeof floorOutcomeSchema>

export async function fetchFactoryFloor(signal?: AbortSignal): Promise<FactoryFloorEnvelope> {
  const response = await fetch("/api/v1/factory-floor", {
    headers: { Accept: "application/json" },
    signal,
  })
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return floorEnvelopeSchema.parse(payload)
}
