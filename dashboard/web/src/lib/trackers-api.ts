import { z } from "zod"

import {
  apiErrorEnvelopeSchema,
  coverageSchema,
  DashboardApiError,
  sourceSchema,
} from "@/lib/api"

export const trackerIdSchema = z.string().regex(/^[0-9a-f]{64}$/)
const fingerprintSchema = trackerIdSchema
const gitObjectIdSchema = z.string().regex(/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/)
const nonnegativeInteger = z.number().int().nonnegative()
const positiveLine = z.number().int().positive()
const stringMapSchema = z.record(z.string(), z.string())
const countMapSchema = z.record(z.string(), nonnegativeInteger)

const sourceAnchorSchema = z
  .object({
    title: z.string(),
    normalized_title: z.string(),
    line: positiveLine,
    end_line: positiveLine,
    anchor: z.string().min(1),
  })
  .strict()

const sectionIdentitySchema = sourceAnchorSchema.omit({ normalized_title: true })

const sectionContentSchema = sourceAnchorSchema
  .extend({
    markdown_preview: z.string(),
    preview_truncated: z.boolean(),
    content_sha256: fingerprintSchema,
  })
  .strict()

const tableSchema = z
  .object({
    line: positiveLine,
    headers: z.array(z.string()),
    rows: z.array(z.array(z.string())),
    truncated: z.boolean(),
  })
  .strict()

const verifierOwnerSchema = z
  .object({
    identity: z.literal("author-implementation-trackers/verify_tracker.py"),
    path: z.string().min(1),
    sha256: fingerprintSchema,
    owning_revision: gitObjectIdSchema.nullable(),
  })
  .strict()

export const trackerVerifierSchema = z
  .object({
    profile: z.enum(["full", "core"]),
    valid: z.boolean(),
    exit_status: z.union([z.literal(0), z.literal(1)]),
    blocks: z.array(nonnegativeInteger),
    errors: z.array(z.string()),
    warnings: z.array(z.string()),
    command: z.array(z.string()).min(1),
    owner: verifierOwnerSchema,
  })
  .strict()

const gitErrorSchema = z
  .object({ code: z.string().min(1), message: z.string().min(1) })
  .strict()

const lastCommitSchema = z
  .object({
    revision: gitObjectIdSchema,
    committed_at: z.iso.datetime({ offset: true }),
    subject: z.string(),
  })
  .strict()

export const trackerDiffSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    changed: z.boolean().nullable(),
    base: z.enum(["HEAD", "empty"]).nullable(),
    added_lines: nonnegativeInteger.nullable(),
    removed_lines: nonnegativeInteger.nullable(),
    preview: z.string().nullable(),
    truncated: z.boolean(),
    error: gitErrorSchema.nullable(),
  })
  .strict()

export const trackerGitSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    repository_head: gitObjectIdSchema.nullable(),
    branch: z.string().nullable(),
    tracked: z.boolean().nullable(),
    untracked: z.boolean().nullable(),
    worktree_changed: z.boolean().nullable(),
    porcelain: z.array(z.string()),
    git_blob: gitObjectIdSchema.nullable(),
    index_blob: gitObjectIdSchema.nullable(),
    committed_content_sha256: fingerprintSchema.nullable(),
    content_matches_head: z.boolean().nullable(),
    last_commit: lastCommitSchema.nullable(),
    upstream: z.string().nullable(),
    ahead: nonnegativeInteger.nullable(),
    behind: nonnegativeInteger.nullable(),
    durability: z.enum(["unavailable", "matched", "diverged", "ahead", "behind"]),
    bound_content_sha256: fingerprintSchema.nullable(),
    binding_status: z.enum(["unavailable", "unknown", "current", "stale"]),
    diff: trackerDiffSchema,
    errors: z.array(gitErrorSchema),
  })
  .strict()

const rawFileSchema = z
  .object({
    path: z.string().min(1),
    line: z.literal(1),
    read_only: z.literal(true),
    content_sha256: fingerprintSchema,
    size: nonnegativeInteger,
    mtime_ns: z.string().regex(/^\d+$/),
  })
  .strict()

const trackerCountsSchema = z
  .object({
    total: nonnegativeInteger,
    by_status: countMapSchema,
    accepted: nonnegativeInteger,
    open: nonnegativeInteger,
    with_completion_evidence: nonnegativeInteger,
    evidence_by_posture: countMapSchema,
  })
  .strict()

const trackerCoverageSchema = z
  .object({
    status: z.enum(["complete", "partial"]),
    observed: z.array(z.string()),
    missing: z.array(z.string()),
  })
  .strict()

const availableTrackerSummarySchema = z
  .object({
    id: trackerIdSchema,
    project_id: z.string().min(1),
    project_label: z.string().min(1),
    relative_path: z.string().min(1),
    status: z.literal("available"),
    observed_at: z.iso.datetime({ offset: true }),
    fingerprint: fingerprintSchema,
    source: sourceSchema.strict(),
    raw_file: rawFileSchema,
    title: z.string().min(1),
    tracker_status: z.string().nullable(),
    profile: z.enum(["full", "core"]),
    profile_reason: z.string().min(1),
    verifier: trackerVerifierSchema,
    counts: trackerCountsSchema,
    current_blocks: z.array(nonnegativeInteger),
    eligible_blocks: z.array(nonnegativeInteger),
    header_block_status_conflict: z.boolean(),
    git: trackerGitSchema,
    progress_posture: z.enum(["current", "dirty", "untracked", "stale", "unavailable"]),
    coverage: trackerCoverageSchema,
    limitations: z.array(z.string()),
  })
  .strict()

const unavailableTrackerSummarySchema = z
  .object({
    id: trackerIdSchema,
    project_id: z.string().min(1),
    project_label: z.string().min(1),
    relative_path: z.string().min(1),
    status: z.literal("unavailable"),
    observed_at: z.iso.datetime({ offset: true }),
    fingerprint: z.null(),
    source: sourceSchema.strict(),
    coverage: z
      .object({
        status: z.literal("unavailable"),
        observed: z.array(z.string()),
        missing: z.array(z.string()),
      })
      .strict(),
    limitations: z.array(z.string()),
    error: gitErrorSchema.extend({ retryable: z.boolean() }).strict(),
  })
  .strict()

export const trackerSummarySchema = z.discriminatedUnion("status", [
  availableTrackerSummarySchema,
  unavailableTrackerSummarySchema,
])

const trackerBlockSchema = z
  .object({
    number: nonnegativeInteger,
    title: z.string(),
    line: positiveLine,
    anchor: z.string().min(1),
    status: z.string().nullable(),
    status_line: positiveLine.nullable(),
    dependencies: z.array(nonnegativeInteger),
    dependency_expression: z.string(),
    objective: z.string().nullable(),
    stop: z.string().nullable(),
    capability_delta: stringMapSchema,
    completion_evidence: z
      .object({
        present: z.boolean(),
        posture: z.enum(["recorded", "missing", "open"]),
        line: positiveLine.nullable(),
        preview: z.string().nullable(),
      })
      .strict(),
    sections: z.array(sectionContentSchema),
    dependency_statuses: z.array(
      z
        .object({ number: nonnegativeInteger, status: z.string().nullable() })
        .strict(),
    ),
    eligible: z.boolean(),
  })
  .strict()

export const trackerDetailSchema = availableTrackerSummarySchema
  .extend({
    tracker_sequence: z.string().nullable(),
    metadata: stringMapSchema,
    metadata_duplicate_fields: z.array(z.string()),
    frames: z.array(
      sectionIdentitySchema
        .extend({
          fields: stringMapSchema,
          duplicate_fields: z.array(z.string()),
        })
        .strict(),
    ),
    owner_source_maps: z.array(
      sectionIdentitySchema.extend({ tables: z.array(tableSchema) }).strict(),
    ),
    supplemental_sections: z.array(
      sectionIdentitySchema
        .extend({ preview: z.string().nullable(), tables: z.array(tableSchema) })
        .strict(),
    ),
    document_sections: z.array(sectionContentSchema),
    blocks: z.array(trackerBlockSchema),
    parser_limitations: z.array(z.string()),
    analysis_cache: z
      .object({ status: z.enum(["hit", "miss"]), key: fingerprintSchema })
      .strict(),
  })
  .strict()

const projectProjectionStateSchema = z
  .object({
    project_id: z.string().min(1),
    status: z.enum(["available", "unavailable"]),
    observed_at: z.iso.datetime({ offset: true }),
    errors: z.array(gitErrorSchema),
    tracker_candidates: nonnegativeInteger,
  })
  .strict()

const verifierRevisionSchema = z.union([
  z
    .object({
      path: z.string().min(1),
      sha256: fingerprintSchema,
      owning_revision: gitObjectIdSchema.nullable(),
    })
    .strict(),
  z
    .object({
      path: z.null(),
      sha256: z.null(),
      owning_revision: z.null(),
      error: gitErrorSchema,
    })
    .strict(),
])

const envelopeMetadata = {
  source: sourceSchema.strict(),
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: fingerprintSchema,
  coverage: coverageSchema.strict(),
  limitations: z.array(z.string()),
  error: z.null(),
}

export const trackerListEnvelopeSchema = z
  .object({
    data: z
      .object({
        catalog_fingerprint: fingerprintSchema,
        recovered_from_previous: z.boolean(),
        verifier_owner: verifierRevisionSchema,
        projects: z.array(projectProjectionStateSchema),
        trackers: z.array(trackerSummarySchema),
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const trackerDetailEnvelopeSchema = z
  .object({
    data: z
      .object({
        catalog_fingerprint: fingerprintSchema,
        recovered_from_previous: z.boolean(),
        tracker: trackerDetailSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export const trackerDiffEnvelopeSchema = z
  .object({
    data: z
      .object({
        tracker_id: trackerIdSchema,
        content_sha256: fingerprintSchema,
        repository_head: gitObjectIdSchema.nullable(),
        diff: trackerDiffSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()

export type TrackerSummary = z.infer<typeof trackerSummarySchema>
export type TrackerDetail = z.infer<typeof trackerDetailSchema>
export type TrackerListEnvelope = z.infer<typeof trackerListEnvelopeSchema>
export type TrackerDetailEnvelope = z.infer<typeof trackerDetailEnvelopeSchema>
export type TrackerDiffEnvelope = z.infer<typeof trackerDiffEnvelopeSchema>

async function parsedResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return schema.parse(payload)
}

export async function fetchTrackers(signal?: AbortSignal): Promise<TrackerListEnvelope> {
  return parsedResponse(
    await fetch("/api/v1/trackers", {
      headers: { Accept: "application/json" },
      signal,
    }),
    trackerListEnvelopeSchema,
  )
}

export async function fetchTracker(
  trackerId: string,
  signal?: AbortSignal,
): Promise<TrackerDetailEnvelope> {
  const validatedId = trackerIdSchema.parse(trackerId)
  return parsedResponse(
    await fetch(`/api/v1/trackers/${validatedId}`, {
      headers: { Accept: "application/json" },
      signal,
    }),
    trackerDetailEnvelopeSchema,
  )
}

export async function fetchTrackerDiff(
  trackerId: string,
  signal?: AbortSignal,
): Promise<TrackerDiffEnvelope> {
  const validatedId = trackerIdSchema.parse(trackerId)
  return parsedResponse(
    await fetch(`/api/v1/trackers/${validatedId}/diff`, {
      headers: { Accept: "application/json" },
      signal,
    }),
    trackerDiffEnvelopeSchema,
  )
}

export function trackerSourceUrl(
  trackerId: string,
  range?: { line: number; endLine: number },
): string {
  const validatedId = trackerIdSchema.parse(trackerId)
  if (!range) return `/api/v1/trackers/${validatedId}/source`
  const line = positiveLine.parse(range.line)
  const endLine = positiveLine.parse(range.endLine)
  if (endLine < line) throw new Error("Tracker source end line must not precede its start line.")
  const query = new URLSearchParams({ line: String(line), end_line: String(endLine) })
  return `/api/v1/trackers/${validatedId}/source?${query}`
}

export async function fetchTrackerSource(
  trackerId: string,
  range: { line: number; endLine: number },
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(trackerSourceUrl(trackerId, range), {
    headers: { Accept: "text/markdown" },
    signal,
  })
  if (!response.ok) {
    const payload: unknown = await response.json()
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return response.text()
}
