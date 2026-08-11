import { describe, expect, it, vi } from "vitest"

import { DashboardApiError } from "@/lib/api"
import {
  fetchTracker,
  fetchTrackerDiff,
  fetchTrackerSource,
  fetchTrackers,
  trackerDetailEnvelopeSchema,
  trackerDiffEnvelopeSchema,
  trackerListEnvelopeSchema,
  trackerSourceUrl,
  trackerSummarySchema,
} from "@/lib/trackers-api"

const observedAt = "2026-08-09T10:00:00.000Z"
const fingerprint = (character: string) => character.repeat(64)
const revision = (character: string) => character.repeat(40)

const source = {
  kind: "tracker-projection",
  identity: "software-factory-dashboard/trackers",
  revision: fingerprint("a"),
} as const

const coverage = {
  status: "partial",
  observed: ["tracker-markdown", "maintained-verifier", "git-currentness"],
  missing: ["run-bound-tracker-hash"],
} as const

const verifier = {
  profile: "full",
  valid: true,
  exit_status: 0,
  blocks: [0, 1],
  errors: [],
  warnings: [],
  command: ["python", "/owner/verify_tracker.py", "/work/docs/tracker.md", "--json"],
  owner: {
    identity: "author-implementation-trackers/verify_tracker.py",
    path: "/owner/verify_tracker.py",
    sha256: fingerprint("b"),
    owning_revision: revision("c"),
  },
} as const

const git = {
  status: "available",
  repository_head: revision("d"),
  branch: "main",
  tracked: true,
  untracked: false,
  worktree_changed: false,
  porcelain: [],
  git_blob: revision("e"),
  index_blob: revision("e"),
  committed_content_sha256: fingerprint("f"),
  content_matches_head: true,
  last_commit: {
    revision: revision("d"),
    committed_at: "2026-08-09T09:00:00.000-07:00",
    subject: "docs: update tracker",
  },
  upstream: "origin/main",
  ahead: 0,
  behind: 0,
  durability: "matched",
  bound_content_sha256: null,
  binding_status: "unavailable",
  diff: {
    status: "available",
    changed: false,
    base: "HEAD",
    added_lines: 0,
    removed_lines: 0,
    preview: null,
    truncated: false,
    error: null,
  },
  errors: [],
} as const

const availableSummary = {
  id: fingerprint("1"),
  project_id: "alpha",
  project_label: "Alpha",
  relative_path: "docs/alpha-implementation-tracker.md",
  status: "available",
  observed_at: observedAt,
  fingerprint: fingerprint("2"),
  source: {
    kind: "tracker-markdown",
    identity: "alpha:docs/alpha-implementation-tracker.md",
    revision: fingerprint("f"),
  },
  raw_file: {
    path: "/work/alpha/docs/alpha-implementation-tracker.md",
    line: 1,
    read_only: true,
    content_sha256: fingerprint("f"),
    size: 2048,
    mtime_ns: "1786279200000000000",
  },
  title: "Alpha Implementation Tracker",
  tracker_status: "in-progress",
  profile: "full",
  profile_reason: "current capability frame present",
  verifier,
  counts: {
    total: 2,
    by_status: { accepted: 1, "not-started": 1 },
    accepted: 1,
    open: 1,
    with_completion_evidence: 1,
    evidence_by_posture: { recorded: 1, open: 1 },
  },
  current_blocks: [],
  current_block_details: [],
  eligible_blocks: [1],
  header_block_status_conflict: false,
  git,
  progress_posture: "current",
  coverage,
  limitations: ["No canonical run-bound tracker hash is available until Block 4 composition."],
} as const

const unavailableSummary = {
  id: fingerprint("3"),
  project_id: "beta",
  project_label: "Beta",
  relative_path: "docs/beta-implementation-tracker.md",
  status: "unavailable",
  observed_at: observedAt,
  fingerprint: null,
  source: {
    kind: "tracker-markdown",
    identity: "beta:docs/beta-implementation-tracker.md",
    revision: "unavailable",
  },
  coverage: { status: "unavailable", observed: [], missing: ["tracker"] },
  limitations: ["This tracker could not be projected; other trackers remain independent."],
  error: { code: "tracker_unavailable", message: "Tracker disappeared.", retryable: false },
} as const

const listEnvelope = {
  data: {
    catalog_fingerprint: fingerprint("4"),
    recovered_from_previous: false,
    verifier_owner: {
      path: "/owner/verify_tracker.py",
      sha256: fingerprint("b"),
      owning_revision: revision("c"),
    },
    projects: [
      {
        project_id: "alpha",
        status: "available",
        observed_at: observedAt,
        errors: [],
        tracker_candidates: 2,
      },
    ],
    trackers: [availableSummary, unavailableSummary],
  },
  source,
  observed_at: observedAt,
  fingerprint: fingerprint("5"),
  coverage,
  limitations: ["Read API only."],
  error: null,
} as const

const detail = {
  ...availableSummary,
  tracker_sequence: "Blocks 0–1",
  metadata: { "tracker status": "`in-progress`" },
  metadata_duplicate_fields: [],
  frames: [
    {
      title: "Target-product capability frame",
      line: 8,
      end_line: 18,
      anchor: "target-product-capability-frame",
      fields: { applicability: "`consequential`" },
      duplicate_fields: [],
    },
  ],
  owner_source_maps: [
    {
      title: "Source owner map",
      line: 20,
      end_line: 25,
      anchor: "source-owner-map",
      tables: [
        {
          line: 22,
          headers: ["Concern", "Owner"],
          rows: [["Structure", "Tracker Markdown"]],
          truncated: false,
        },
      ],
    },
  ],
  supplemental_sections: [],
  document_sections: [
    {
      title: "Source owner map",
      normalized_title: "source owner map",
      line: 20,
      end_line: 25,
      anchor: "source-owner-map",
      markdown_preview: "| Concern | Owner |",
      preview_truncated: false,
      content_sha256: fingerprint("7"),
    },
  ],
  blocks: [
    {
      number: 0,
      title: "Base",
      line: 30,
      anchor: "block-0-base",
      status: "accepted",
      status_line: 32,
      dependencies: [],
      dependency_expression: "—",
      objective: "Establish the base.",
      stop: "Stop before the next Block.",
      capability_delta: { posture: "`consequential`" },
      completion_evidence: {
        present: true,
        posture: "recorded",
        line: 60,
        preview: "Commit abc accepted.",
      },
      sections: [
        {
          title: "Objective",
          normalized_title: "objective",
          line: 34,
          end_line: 37,
          anchor: "objective",
          markdown_preview: "Establish the base.",
          preview_truncated: false,
          content_sha256: fingerprint("8"),
        },
      ],
      dependency_statuses: [],
      blocked_ancestors: [],
      eligible: false,
    },
  ],
  parser_limitations: ["Exact source ranges remain authoritative."],
  analysis_cache: { status: "miss", key: fingerprint("6") },
} as const

const detailEnvelope = {
  ...listEnvelope,
  data: {
    catalog_fingerprint: listEnvelope.data.catalog_fingerprint,
    recovered_from_previous: false,
    tracker: detail,
  },
} as const

const diffEnvelope = {
  data: {
    tracker_id: availableSummary.id,
    content_sha256: availableSummary.raw_file.content_sha256,
    repository_head: availableSummary.git.repository_head,
    diff: {
      ...availableSummary.git.diff,
      changed: true,
      added_lines: 1,
      preview: "@@ -1 +1 @@\n-old\n+new",
    },
  },
  source: {
    kind: "tracker-git-diff",
    identity: `software-factory-dashboard/trackers/${availableSummary.id}/diff`,
    revision: availableSummary.raw_file.content_sha256,
  },
  observed_at: observedAt,
  fingerprint: fingerprint("d"),
  coverage: { status: "complete", observed: ["tracker-working-content", "git-head-diff"], missing: [] },
  limitations: ["Bounded read-only comparison."],
  error: null,
} as const

const errorEnvelope = {
  data: null,
  source: { kind: "runtime", identity: "software-factory-dashboard/http", revision: "0.1.0" },
  observed_at: observedAt,
  fingerprint: fingerprint("7"),
  coverage: { status: "partial", observed: ["runtime"], missing: [] },
  limitations: [],
  error: { code: "tracker_not_found", message: "Tracker was not found.", retryable: false },
} as const

describe("tracker API contracts", () => {
  it("keeps full, core, invalid, dirty, untracked, stale, and unavailable postures distinct", () => {
    const variants = [
      availableSummary,
      { ...availableSummary, id: fingerprint("8"), profile: "core" as const },
      {
        ...availableSummary,
        id: fingerprint("9"),
        verifier: {
          ...verifier,
          valid: false,
          exit_status: 1 as const,
          errors: ["status table and Block line differ"],
        },
      },
      {
        ...availableSummary,
        id: fingerprint("a"),
        progress_posture: "dirty" as const,
        git: { ...git, worktree_changed: true, porcelain: [" M docs/tracker.md"] },
      },
      {
        ...availableSummary,
        id: fingerprint("b"),
        progress_posture: "untracked" as const,
        git: {
          ...git,
          tracked: false,
          untracked: true,
          worktree_changed: true,
          porcelain: ["?? docs/tracker.md"],
          git_blob: null,
          index_blob: null,
          committed_content_sha256: null,
          content_matches_head: null,
          last_commit: null,
        },
      },
      {
        ...availableSummary,
        id: fingerprint("c"),
        progress_posture: "stale" as const,
        git: {
          ...git,
          bound_content_sha256: fingerprint("0"),
          binding_status: "stale" as const,
        },
      },
      unavailableSummary,
    ]

    expect(variants.map((value) => trackerSummarySchema.parse(value).status)).toEqual([
      "available",
      "available",
      "available",
      "available",
      "available",
      "available",
      "unavailable",
    ])
    const core = trackerSummarySchema.parse(variants[1])
    const invalid = trackerSummarySchema.parse(variants[2])
    const stale = trackerSummarySchema.parse(variants[5])
    expect(core.status).toBe("available")
    expect(invalid.status).toBe("available")
    expect(stale.status).toBe("available")
    if (core.status !== "available" || invalid.status !== "available" || stale.status !== "available") {
      throw new Error("Expected available tracker variants.")
    }
    expect(core.profile).toBe("core")
    expect(invalid.verifier.valid).toBe(false)
    expect(stale.progress_posture).toBe("stale")
  })

  it("validates exact source ranges and preserves completed-with-open-items as open", () => {
    const parsed = trackerDetailEnvelopeSchema.parse(detailEnvelope)
    expect(trackerDiffEnvelopeSchema.parse(diffEnvelope).data.diff.preview).toContain("+new")
    expect(parsed.data.tracker.blocks[0].sections[0]).toMatchObject({
      line: 34,
      anchor: "objective",
    })

    const openSummary = {
      ...availableSummary,
      counts: {
        ...availableSummary.counts,
        by_status: { "completed-with-open-items": 1, "not-started": 1 },
        accepted: 0,
        open: 2,
      },
    }
    const parsedOpen = trackerSummarySchema.parse(openSummary)
    expect(parsedOpen.status).toBe("available")
    if (parsedOpen.status !== "available") throw new Error("Expected an available tracker.")
    expect(parsedOpen.counts.accepted).toBe(0)
  })

  it("uses bounded read routes, validates IDs locally, and preserves abort signals", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => listEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => detailEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => diffEnvelope })
      .mockResolvedValueOnce({ ok: true, status: 200, text: async () => "### Objective\n\nExact source." })
    vi.stubGlobal("fetch", fetchMock)
    const controller = new AbortController()

    await fetchTrackers(controller.signal)
    await fetchTracker(fingerprint("1"), controller.signal)
    await fetchTrackerDiff(fingerprint("1"), controller.signal)
    await fetchTrackerSource(fingerprint("1"), { line: 34, endLine: 37 }, controller.signal)

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/trackers",
      expect.objectContaining({ signal: controller.signal }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/v1/trackers/${fingerprint("1")}`,
      expect.objectContaining({ signal: controller.signal }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `/api/v1/trackers/${fingerprint("1")}/diff`,
      expect.objectContaining({ signal: controller.signal }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `/api/v1/trackers/${fingerprint("1")}/source?line=34&end_line=37`,
      expect.objectContaining({ signal: controller.signal }),
    )
    await expect(fetchTracker("../tracker")).rejects.toThrow()
    expect(() => trackerSourceUrl(fingerprint("1"), { line: 9, endLine: 8 })).toThrow()
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it("parses a structured source-local error before throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => errorEnvelope }),
    )

    const request = fetchTracker(fingerprint("1"))
    await expect(request).rejects.toBeInstanceOf(DashboardApiError)
    await expect(request).rejects.toMatchObject({
      code: "tracker_not_found",
      retryable: false,
      status: 404,
    })
  })

  it("rejects unrecognized envelope fields instead of silently widening the client contract", () => {
    expect(() => trackerListEnvelopeSchema.parse({ ...listEnvelope, copied_status: "green" })).toThrow()
  })
})
