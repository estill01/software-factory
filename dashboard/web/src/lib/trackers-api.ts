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
    identity: z.literal("runtime/compatibility_owners/tracker/verify_tracker.py"),
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

const semanticVerifierSchema = verifierOwnerSchema
  .extend({
    profile: z.enum(["full", "core"]),
    valid: z.boolean(),
  })
  .strict()

const semanticBlockSchema = z
  .object({
    number: nonnegativeInteger,
    title: z.string().max(160),
    title_truncated: z.boolean(),
    line: positiveLine,
    anchor: z.string().min(1).max(200),
    anchor_truncated: z.boolean(),
  })
  .strict()

const semanticSideSchema = z
  .object({
    text: z.string().max(600),
    text_truncated: z.boolean(),
    line: positiveLine,
    content_sha256: fingerprintSchema,
    block: semanticBlockSchema.nullable(),
  })
  .strict()

export const trackerSemanticDiffSchema = z
  .object({
    status: z.enum(["available", "unavailable"]),
    changed: z.boolean().nullable(),
    base: z
      .object({
        kind: z.enum(["HEAD", "empty"]),
        repository_revision: gitObjectIdSchema.nullable(),
        content_sha256: fingerprintSchema,
      })
      .strict()
      .nullable(),
    target: z
      .object({
        kind: z.literal("working-tree"),
        content_sha256: fingerprintSchema,
      })
      .strict(),
    rows: z.array(
      z
        .object({
          id: fingerprintSchema,
          kind: z.enum(["added", "removed", "changed"]),
          before: semanticSideSchema.nullable(),
          after: semanticSideSchema.nullable(),
        })
        .strict(),
    ).max(200),
    total_rows: nonnegativeInteger.nullable(),
    returned_rows: nonnegativeInteger.max(200),
    row_limit: z.literal(200),
    complete: z.boolean(),
    truncated: z.boolean(),
    path: z.string().min(1),
    owning_revision: gitObjectIdSchema.nullable(),
    owner: z
      .object({
        tracker: z.literal("tracker-markdown/read-only"),
        git: z.literal("git/HEAD-and-working-tree"),
        verifier: semanticVerifierSchema,
      })
      .strict(),
    currentness_fingerprint: fingerprintSchema,
    limitations: z.array(z.string()),
    error: z
      .object({ code: z.string().min(1), message: z.string().min(1) })
      .strict()
      .nullable(),
  })
  .strict()
  .superRefine((value, context) => {
    const issue = (message: string, path: (string | number)[]) => context.addIssue({ code: "custom", message, path })
    if (value.returned_rows !== value.rows.length) {
      issue("Returned semantic row count must match the typed rows.", ["returned_rows"])
    }
    if (new Set(value.rows.map((row) => row.id)).size !== value.rows.length) {
      issue("Semantic row identities must be unique.", ["rows"])
    }
    if (value.status === "unavailable") {
      if (value.changed !== null || value.base !== null || value.total_rows !== null || value.rows.length || value.complete) {
        issue("Unavailable semantic comparisons cannot carry change or completion claims.", ["status"])
      }
      return
    }
    if (value.base === null || value.changed === null || value.total_rows === null) {
      issue("Available semantic comparisons require exact base and change totals.", ["base"])
      return
    }
    if (value.base.kind === "HEAD" && value.base.repository_revision === null) {
      issue("HEAD semantic bases require an exact repository revision.", ["base", "repository_revision"])
    }
    if (value.base.kind === "empty" && value.base.repository_revision !== null) {
      issue("Empty semantic bases cannot claim a repository revision.", ["base", "repository_revision"])
    }
    if (value.returned_rows > value.total_rows) {
      issue("Returned semantic rows cannot exceed the exact total row count.", ["returned_rows"])
    }
    if (value.changed !== (value.total_rows > 0)) {
      issue("Semantic changed posture must match the exact total row count.", ["changed"])
    }
    const boundedRows = value.rows.some((row) => (
      row.before?.text_truncated
      || row.after?.text_truncated
      || row.before?.block?.title_truncated
      || row.after?.block?.title_truncated
      || row.before?.block?.anchor_truncated
      || row.after?.block?.anchor_truncated
    ))
    const subset = value.returned_rows !== value.total_rows || boundedRows
    if (value.complete && (value.truncated || subset)) {
      issue("A bounded semantic subset cannot be labeled complete.", ["complete"])
    }
    if (subset && !value.truncated) {
      issue("A bounded semantic subset must be labeled truncated.", ["truncated"])
    }
    if (!value.changed && (!value.complete || value.truncated || value.returned_rows !== 0 || value.rows.length !== 0)) {
      issue("An exact no-change claim requires a complete, untruncated, empty comparison.", ["changed"])
    }
    value.rows.forEach((row, index) => {
      if (
        (row.kind === "added" && (row.before !== null || row.after === null))
        || (row.kind === "removed" && (row.before === null || row.after !== null))
        || (row.kind === "changed" && (row.before === null || row.after === null))
      ) {
        issue("Semantic change kind does not match its before and after sides.", ["rows", index])
      }
      if (row.before?.content_sha256 !== undefined && row.before.content_sha256 !== value.base?.content_sha256) {
        issue("Before rows must use the exact semantic base root.", ["rows", index, "before", "content_sha256"])
      }
      if (row.after?.content_sha256 !== undefined && row.after.content_sha256 !== value.target.content_sha256) {
        issue("After rows must use the exact semantic target root.", ["rows", index, "after", "content_sha256"])
      }
      if (value.base?.kind === "empty" && row.before !== null) {
        issue("An empty base cannot expose before-source rows.", ["rows", index, "before"])
      }
    })
  })

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
    semantic: trackerSemanticDiffSchema.nullable().default(null),
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

const currentBlockDetailSchema = z
  .object({
    number: nonnegativeInteger,
    title: z.string().min(1),
    status: z.string().nullable(),
    line: positiveLine,
    status_line: positiveLine.nullable(),
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
    current_block_details: z.array(currentBlockDetailSchema),
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
    blocked_ancestors: z.array(nonnegativeInteger),
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
        relative_path: z.string().min(1),
        owning_revision: gitObjectIdSchema.nullable(),
        verifier: semanticVerifierSchema,
        diff: trackerDiffSchema,
      })
      .strict(),
    ...envelopeMetadata,
  })
  .strict()
  .superRefine((value, context) => {
    const semantic = value.data.diff.semantic
    if (!semantic) return
    const issue = (message: string, path: (string | number)[]) => context.addIssue({ code: "custom", message, path: ["data", ...path] })
    if (semantic.path !== value.data.relative_path) {
      issue("Semantic path must match the selected tracker path.", ["diff", "semantic", "path"])
    }
    if (semantic.target.content_sha256 !== value.data.content_sha256) {
      issue("Semantic target must match the selected working-content root.", ["diff", "semantic", "target"])
    }
    if (semantic.owning_revision !== value.data.owning_revision) {
      issue("Semantic owning revision must match the selected tracker owner.", ["diff", "semantic", "owning_revision"])
    }
    if (
      semantic.owner.verifier.sha256 !== value.data.verifier.sha256
      || semantic.owner.verifier.owning_revision !== value.data.verifier.owning_revision
      || semantic.owner.verifier.profile !== value.data.verifier.profile
      || semantic.owner.verifier.valid !== value.data.verifier.valid
    ) {
      issue("Semantic verifier posture must match the selected verifier snapshot.", ["diff", "semantic", "owner", "verifier"])
    }
    if (semantic.base?.kind === "HEAD" && semantic.base.repository_revision !== value.data.repository_head) {
      issue("Semantic HEAD base must match the selected repository HEAD.", ["diff", "semantic", "base"])
    }
    if (semantic.status === "available" && semantic.changed !== value.data.diff.changed) {
      issue("Semantic and Git changed postures must agree.", ["diff", "semantic", "changed"])
    }
  })

export type TrackerSummary = z.infer<typeof trackerSummarySchema>
export type TrackerDetail = z.infer<typeof trackerDetailSchema>
export type TrackerListEnvelope = z.infer<typeof trackerListEnvelopeSchema>
export type TrackerDetailEnvelope = z.infer<typeof trackerDetailEnvelopeSchema>
export type TrackerDiffEnvelope = z.infer<typeof trackerDiffEnvelopeSchema>
export type TrackerSemanticDiff = z.infer<typeof trackerSemanticDiffSchema>

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
  identity?: { revision?: string; contentSha256?: string },
): string {
  const validatedId = trackerIdSchema.parse(trackerId)
  if (identity?.revision && identity.contentSha256) {
    throw new Error("Tracker source accepts one exact source identity.")
  }
  const query = new URLSearchParams()
  if (range) {
    const line = positiveLine.parse(range.line)
    const endLine = positiveLine.parse(range.endLine)
    if (endLine < line) throw new Error("Tracker source end line must not precede its start line.")
    query.set("line", String(line))
    query.set("end_line", String(endLine))
  }
  if (identity?.revision) query.set("revision", gitObjectIdSchema.parse(identity.revision))
  if (identity?.contentSha256) query.set("content_sha256", fingerprintSchema.parse(identity.contentSha256))
  const suffix = query.size ? `?${query}` : ""
  return `/api/v1/trackers/${validatedId}/source${suffix}`
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
