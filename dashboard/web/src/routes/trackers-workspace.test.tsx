import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { FactoryFloorEnvelope } from "@/lib/floor-api"

const mocks = vi.hoisted(() => ({
  fetchFactoryFloor: vi.fn(),
  fetchTracker: vi.fn(),
  fetchTrackerDiff: vi.fn(),
  fetchTrackerSource: vi.fn(),
  fetchTrackers: vi.fn(),
}))

vi.mock("@/lib/floor-api", () => ({ fetchFactoryFloor: mocks.fetchFactoryFloor }))
vi.mock("@/lib/trackers-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/trackers-api")>()),
  fetchTracker: mocks.fetchTracker,
  fetchTrackerDiff: mocks.fetchTrackerDiff,
  fetchTrackerSource: mocks.fetchTrackerSource,
  fetchTrackers: mocks.fetchTrackers,
}))

import { Component as TrackerWorkspace } from "@/routes/tracker-workspace-page"
import { Component as TrackersPage } from "@/routes/trackers-page"

const fingerprint = (character: string) => character.repeat(64)
const revision = (character: string) => character.repeat(40)

const tracker = {
  id: fingerprint("1"),
  project_id: "alpha",
  project_label: "Alpha",
  relative_path: "docs/alpha-implementation-tracker.md",
  status: "available",
  observed_at: "2026-08-09T10:00:00.000Z",
  fingerprint: fingerprint("2"),
  source: { kind: "tracker-markdown", identity: "alpha:tracker", revision: fingerprint("2") },
  raw_file: { path: "/work/alpha/docs/alpha-implementation-tracker.md", line: 1, read_only: true, content_sha256: fingerprint("3"), size: 5000, mtime_ns: "1" },
  title: "Alpha implementation tracker",
  tracker_status: "in-progress",
  profile: "full",
  profile_reason: "Current full-profile frame.",
  verifier: {
    profile: "full",
    valid: true,
    exit_status: 0,
    blocks: [0, 1],
    errors: [],
    warnings: [],
    command: ["python", "verify_tracker.py"],
    owner: { identity: "author-implementation-trackers/verify_tracker.py", path: "/owner/verify_tracker.py", sha256: fingerprint("4"), owning_revision: revision("5") },
  },
  counts: { total: 2, by_status: { accepted: 1, "not-started": 1 }, accepted: 1, open: 1, with_completion_evidence: 1, evidence_by_posture: { recorded: 1, open: 1 } },
  current_blocks: [],
  current_block_details: [],
  eligible_blocks: [1],
  header_block_status_conflict: false,
  git: {
    status: "available",
    repository_head: revision("6"),
    branch: "main",
    tracked: true,
    untracked: false,
    worktree_changed: true,
    porcelain: [" M docs/alpha-implementation-tracker.md"],
    git_blob: revision("7"),
    index_blob: revision("7"),
    committed_content_sha256: fingerprint("8"),
    content_matches_head: false,
    last_commit: { revision: revision("6"), committed_at: "2026-08-09T09:00:00.000Z", subject: "docs: baseline" },
    upstream: "origin/main",
    ahead: 0,
    behind: 0,
    durability: "matched",
    bound_content_sha256: null,
    binding_status: "unavailable",
    diff: { status: "available", changed: true, base: "HEAD", added_lines: 2, removed_lines: 1, preview: null, truncated: false, error: null },
    errors: [],
  },
  progress_posture: "dirty",
  coverage: { status: "complete", observed: ["tracker"], missing: [] },
  limitations: ["Run-bound hash unavailable."],
  tracker_sequence: "Blocks 0–1",
  metadata: { "governing objective": "Keep exact tracker truth." },
  metadata_duplicate_fields: [],
  frames: [{ title: "Target-product capability frame", line: 8, end_line: 18, anchor: "target-product-capability-frame", fields: { "protected capabilities": "Exact evidence and Stops." }, duplicate_fields: [] }],
  owner_source_maps: [{ title: "Source owner map", line: 20, end_line: 24, anchor: "source-owner-map", tables: [{ line: 22, headers: ["Concern", "Owner"], rows: [["Structure", "Tracker Markdown"]], truncated: false }] }],
  supplemental_sections: [],
  document_sections: [{ title: "Final integrated acceptance", normalized_title: "final integrated acceptance", line: 100, end_line: 105, anchor: "final-integrated-acceptance", markdown_preview: "No final completion until every Block is accepted.", preview_truncated: false, content_sha256: fingerprint("9") }],
  blocks: [
    {
      number: 0, title: "Base", line: 30, anchor: "block-0-base", status: "accepted", status_line: 32, dependencies: [], dependency_expression: "—", objective: "Establish the base.", stop: "Stop before Block 1.", capability_delta: { posture: "consequential" }, completion_evidence: { present: true, posture: "recorded", line: 60, preview: "Commit recorded." }, sections: [{ title: "Objective", normalized_title: "objective", line: 34, end_line: 37, anchor: "objective", markdown_preview: "Establish the exact base.", preview_truncated: false, content_sha256: fingerprint("a") }], dependency_statuses: [], blocked_ancestors: [], eligible: false,
    },
    {
      number: 1, title: "Successor", line: 70, anchor: "block-1-successor", status: "not-started", status_line: 72, dependencies: [0], dependency_expression: "0", objective: "Add the review workspace.", stop: "Stop before mutation.", capability_delta: { posture: "consequential" }, completion_evidence: { present: false, posture: "open", line: 95, preview: null }, sections: [{ title: "Required work", normalized_title: "required work", line: 80, end_line: 90, anchor: "required-work", markdown_preview: "- Render safely.\n- <script>SECRET</script>", preview_truncated: true, content_sha256: fingerprint("b") }], dependency_statuses: [{ number: 0, status: "accepted" }], blocked_ancestors: [], eligible: true,
    },
  ],
  parser_limitations: ["Exact source ranges remain authoritative."],
  analysis_cache: { status: "miss", key: fingerprint("c") },
}

const floor = {
  coverage: { status: "complete", observed: ["catalog", "operations", "trackers", "tasks"], missing: [] },
  data: {
    rows_truncated: false,
    rows: [{
      id: "run:target-1",
      project: { status: "bound", project_id: "alpha", label: "Alpha", reason: "Exact current source binding." },
      work: {
        tracker: { status: "exact", id: tracker.id, title: tracker.title, relative_path: tracker.relative_path },
        block_claims: {
          posture: "none",
          tracker_total: { value: 2, posture: "exact", reason: "Maintained verifier Block set." },
          claims: [
            { source: "tracker", label: "Tracker", status: "none", blocks: [], range: null, reason: "No Block in progress.", source_identity: "tracker-markdown/status", route: `/trackers/${tracker.id}/blocks` },
            { source: "task", label: "Implementation task", status: "none", blocks: [], range: null, reason: "No active task Block.", source_identity: "codex-app-server/task-workflow-marker", route: "/tasks/target-1" },
            { source: "supervision", label: "Current supervision mission", status: "none", blocks: [], range: null, reason: "No active supervision Block.", source_identity: "supervise-tracker-runs/current-mission-activity", route: "/runs/target-1" },
          ],
        },
      },
      supervision: { run_id: "target-1", target_thread_id: "target-1", status: "active" },
      implementation: { task_id: "target-1", name: "Alpha implementation", status: "active" },
      issues: { incidents: 0, decisions: 0, transitions: 0, total: 0 },
      light: { posture: "green", label: "On track", reason: "No current issue rule is active." },
      freshness: { observed_at: "2026-08-09T10:00:00.000Z" },
    }],
    accepted_outcomes: [{ tracker_id: tracker.id }],
  },
} as unknown as FactoryFloorEnvelope

function renderRoute(initialEntry: string, element: ReactNode, path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider client={client}><Routes><Route path={path} element={element} /></Routes></QueryClientProvider>
    </MemoryRouter>,
  )
}

describe("tracker review workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchTrackers.mockResolvedValue({
      data: {
        recovered_from_previous: false,
        projects: [{ project_id: "alpha", status: "available", tracker_candidates: 1 }],
        trackers: [tracker],
      },
      coverage: { status: "complete" },
    })
    mocks.fetchTracker.mockResolvedValue({ data: { tracker } })
    mocks.fetchTrackerDiff.mockResolvedValue({
      data: {
        tracker_id: tracker.id,
        content_sha256: tracker.raw_file.content_sha256,
        repository_head: tracker.git.repository_head,
        relative_path: tracker.relative_path,
        owning_revision: tracker.git.last_commit.revision,
        verifier: { ...tracker.verifier.owner, profile: tracker.verifier.profile, valid: tracker.verifier.valid },
        diff: {
          ...tracker.git.diff,
          preview: "@@ -1 +1 @@\n-old\n+new",
          semantic: {
            status: "available",
            changed: true,
            base: { kind: "HEAD", repository_revision: tracker.git.repository_head, content_sha256: tracker.git.committed_content_sha256 },
            target: { kind: "working-tree", content_sha256: tracker.raw_file.content_sha256 },
            rows: [
              {
                id: fingerprint("d"),
                kind: "changed",
                before: { text: "Status: `not-started`", text_truncated: false, line: 72, content_sha256: tracker.git.committed_content_sha256, block: { number: 1, title: "Successor", line: 70, anchor: "block-1-successor" } },
                after: { text: "Status: `in-progress`", text_truncated: false, line: 72, content_sha256: tracker.raw_file.content_sha256, block: { number: 1, title: "Successor", line: 70, anchor: "block-1-successor" } },
              },
              {
                id: fingerprint("e"),
                kind: "added",
                before: null,
                after: { text: "- Candidate `abc123`.", text_truncated: false, line: 96, content_sha256: tracker.raw_file.content_sha256, block: { number: 1, title: "Successor", line: 70, anchor: "block-1-successor" } },
              },
              {
                id: fingerprint("f"),
                kind: "removed",
                before: { text: "Pending.", text_truncated: false, line: 96, content_sha256: tracker.git.committed_content_sha256, block: { number: 1, title: "Successor", line: 70, anchor: "block-1-successor" } },
                after: null,
              },
            ],
            total_rows: 3,
            returned_rows: 3,
            row_limit: 200,
            complete: true,
            truncated: false,
            path: tracker.relative_path,
            owning_revision: tracker.git.last_commit.revision,
            owner: { tracker: "tracker-markdown/read-only", git: "git/HEAD-and-working-tree", verifier: { ...tracker.verifier.owner, profile: tracker.verifier.profile, valid: tracker.verifier.valid } },
            currentness_fingerprint: fingerprint("0"),
            limitations: ["Selected tracker only."],
            error: null,
          },
        },
      },
    })
    mocks.fetchFactoryFloor.mockResolvedValue(floor)
    mocks.fetchTrackerSource.mockResolvedValue("### Required work\n\n- Exact loaded source.")
  })

  it("shows exact index posture, status counts, mapped run, attention, and URL filters", async () => {
    const user = userEvent.setup()
    renderRoute("/trackers", <TrackersPage />, "/trackers")

    expect(await screen.findByRole("link", { name: tracker.title })).toBeVisible()
    expect(screen.getByText("accepted")).toBeVisible()
    expect(screen.getByText("not-started")).toBeVisible()
    expect(screen.getByText("Working tree differs from HEAD")).toBeVisible()
    expect(screen.getByTitle("target-1")).toBeVisible()
    expect(screen.getByText("2 Blocks")).toBeVisible()
    expect(screen.getAllByText("None active")).toHaveLength(3)
    expect(screen.getByRole("button", { name: "All: 1 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Active / Running: 1 exact" })).toBeVisible()
    await user.click(screen.getByRole("button", { name: "Completed: 0 exact" }))
    expect(screen.getByText("No trackers match the current filters")).toBeVisible()
  })

  it("preserves plural tracker/task/supervision claims, conflict, and exact source links", async () => {
    const longTitle = "A long tracker-owned current Block title that remains exact and bounded"
    const activeTracker = {
      ...tracker,
      counts: {
        ...tracker.counts,
        by_status: { "in-progress": 2 },
        accepted: 0,
        open: 2,
      },
      current_blocks: [0, 1],
      current_block_details: [
        { number: 0, title: "Base implementation", status: "in-progress", line: 30, status_line: 32 },
        { number: 1, title: longTitle, status: "in-progress", line: 70, status_line: 72 },
      ],
      eligible_blocks: [],
    }
    const activeFloor = structuredClone(floor)
    const trackerBlocks = [
      { number: 0, title: "Base implementation", status: "in-progress", line: 30, route: `/trackers/${tracker.id}/blocks?block=0` },
      { number: 1, title: longTitle, status: "in-progress", line: 70, route: `/trackers/${tracker.id}/blocks?block=1` },
    ]
    activeFloor.data.rows[0].work.block_claims = {
      posture: "conflict",
      tracker_total: { value: 2, posture: "exact", reason: "Maintained verifier Block set." },
      claims: [
        { ...activeFloor.data.rows[0].work.block_claims.claims[0], status: "exact", blocks: trackerBlocks, reason: "Tracker names two current Blocks." },
        { ...activeFloor.data.rows[0].work.block_claims.claims[1], status: "exact", blocks: [trackerBlocks[1]], range: { start: 1, end: 1 }, reason: "Task names Block 1." },
        { ...activeFloor.data.rows[0].work.block_claims.claims[2], status: "exact", blocks: trackerBlocks, reason: "Supervision names two current Blocks." },
      ],
    }
    mocks.fetchTrackers.mockResolvedValue({
      data: {
        recovered_from_previous: false,
        projects: [{ project_id: "alpha", status: "available", tracker_candidates: 1 }],
        trackers: [activeTracker],
      },
      coverage: { status: "complete" },
    })
    mocks.fetchFactoryFloor.mockResolvedValue(activeFloor)

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    const row = (await screen.findByRole("link", { name: tracker.title })).closest("article")!
    expect(row).toHaveClass("tracker-progress-conflict")
    expect(screen.getByRole("button", { name: "Active / Running: 1 exact" })).toBeVisible()
    expect(row).toHaveTextContent("2 Blocks")
    expect(row).toHaveTextContent("0/2 accepted · conflict")
    expect(row).toHaveTextContent(`Block 1 — ${longTitle}`)
    expect(row.querySelectorAll(`a[href="/trackers/${tracker.id}/blocks?block=1"]`).length).toBeGreaterThanOrEqual(3)
    expect(row.querySelector('a[href="/tasks/target-1"]')).not.toBeNull()
    expect(row.querySelector('a[href="/runs/target-1"]')).not.toBeNull()
    expect(row.querySelector(".tracker-progress-view")).toHaveTextContent("conflict")
    expect(row.querySelector(".tracker-index-attention")).toHaveTextContent("+2 more")
  })

  it("fails malformed totals closed and labels partial active counts as lower bounds", async () => {
    const malformedTracker = {
      ...tracker,
      verifier: { ...tracker.verifier, valid: false, exit_status: 1, blocks: [], errors: ["No Block headings found."] },
      counts: { ...tracker.counts, total: 0, accepted: 0, open: 0, by_status: {}, with_completion_evidence: 0, evidence_by_posture: {} },
      current_blocks: [],
      current_block_details: [],
      eligible_blocks: [],
    }
    const partialFloor = structuredClone(floor)
    partialFloor.coverage = { status: "partial", observed: ["trackers"], missing: ["tasks"] }
    partialFloor.data.rows_truncated = true
    partialFloor.data.rows[0].work.block_claims.posture = "conflict"
    partialFloor.data.rows[0].work.block_claims.claims[1] = {
      ...partialFloor.data.rows[0].work.block_claims.claims[1],
      status: "conflict",
      blocks: [],
      reason: "A predecessor mission claim was excluded.",
    }
    mocks.fetchTrackers.mockResolvedValue({
      data: {
        recovered_from_previous: false,
        projects: [{ project_id: "alpha", status: "available", tracker_candidates: 1 }],
        trackers: [malformedTracker],
      },
      coverage: { status: "partial" },
    })
    mocks.fetchFactoryFloor.mockResolvedValue(partialFloor)

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    const row = (await screen.findByRole("link", { name: tracker.title })).closest("article")!
    expect(row).toHaveTextContent("Blocks unavailable")
    expect(row).not.toHaveTextContent("0 Blocks")
    expect(screen.getByLabelText(/Implementation task.*A predecessor mission claim was excluded/)).toBeVisible()
    expect(screen.getByRole("button", { name: "All: 1 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Active / Running: 1 returned, lower bound or partial coverage" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Completed: 0 returned, lower bound or partial coverage" })).toBeVisible()
  })

  it("does not call a conflicting all-accepted tracker completed and preserves system-error failure", async () => {
    const completedConflict = {
      ...tracker,
      tracker_status: "in-progress",
      header_block_status_conflict: true,
      counts: {
        ...tracker.counts,
        by_status: { accepted: 2 },
        accepted: 2,
        open: 0,
      },
      current_blocks: [],
      current_block_details: [],
      eligible_blocks: [],
    }
    const terminalFloor = structuredClone(floor)
    terminalFloor.data.rows[0].implementation.status = "terminal"
    terminalFloor.data.rows[0].implementation.status_label = "System error"
    terminalFloor.data.rows[0].supervision.status = "completed"
    terminalFloor.data.rows[0].light.posture = "green"
    mocks.fetchTrackers.mockResolvedValue({
      data: {
        recovered_from_previous: false,
        projects: [{ project_id: "alpha", status: "available", tracker_candidates: 1 }],
        trackers: [completedConflict],
      },
      coverage: { status: "complete" },
    })
    mocks.fetchFactoryFloor.mockResolvedValue(terminalFloor)

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    expect(await screen.findByRole("button", { name: "Completed: 0 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Blocked / Failed: 1 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Active / Running: 0 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Attention: 1 exact" })).toBeVisible()
  })

  it("labels attention counts partial when even an idle green row has a noncanonical tracker claim", async () => {
    const candidateFloor = structuredClone(floor)
    candidateFloor.data.rows[0].work.tracker.status = "candidate"
    candidateFloor.data.rows[0].implementation.status = "idle"
    candidateFloor.data.rows[0].supervision.status = "unmonitored"
    candidateFloor.data.rows[0].light.posture = "green"
    mocks.fetchFactoryFloor.mockResolvedValue(candidateFloor)

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    expect(await screen.findByRole("button", { name: "All: 1 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Active / Running: 0 returned, lower bound or partial coverage" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Attention: 1 returned, lower bound or partial coverage" })).toBeVisible()
  })

  it("excludes an inactive completed row from current Block claim comparison", async () => {
    const activeTracker = {
      ...tracker,
      counts: { ...tracker.counts, by_status: { accepted: 1, "in-progress": 1 } },
      current_blocks: [1],
      current_block_details: [
        { number: 1, title: "Successor", status: "in-progress", line: 70, status_line: 72 },
      ],
      eligible_blocks: [],
    }
    const currentFloor = structuredClone(floor)
    const activeBlock = {
      number: 1,
      title: "Successor",
      status: "in-progress",
      line: 70,
      route: `/trackers/${tracker.id}/blocks?block=1`,
    }
    currentFloor.data.rows[0].work.block_claims.claims.forEach((claim) => {
      claim.status = "exact"
      claim.blocks = [activeBlock]
      claim.range = null
    })
    const historicalRows = (["completed", "stopped"] as const).map((status) => {
      const historical = structuredClone(currentFloor.data.rows[0])
      historical.id = `run:historical-${status}`
      historical.implementation.task_id = `historical-${status}`
      historical.implementation.status = "idle"
      historical.implementation.status_label = "Idle"
      historical.supervision.run_id = `historical-${status}`
      historical.supervision.target_thread_id = `historical-${status}`
      historical.supervision.status = status
      historical.work.block_claims.claims.forEach((claim) => {
        claim.status = "none"
        claim.blocks = []
        claim.range = null
      })
      return historical
    })
    currentFloor.data.rows = [currentFloor.data.rows[0], ...historicalRows]
    mocks.fetchTrackers.mockResolvedValue({
      data: {
        recovered_from_previous: false,
        projects: [{ project_id: "alpha", status: "available", tracker_candidates: 1 }],
        trackers: [activeTracker],
      },
      coverage: { status: "complete" },
    })
    mocks.fetchFactoryFloor.mockResolvedValue(currentFloor)

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    const row = (await screen.findByRole("link", { name: tracker.title })).closest("article")!
    expect(row).toHaveClass("tracker-progress-exact")
    expect(row).not.toHaveClass("tracker-progress-conflict")
    expect(row).toHaveTextContent("Block 1 — Successor")
  })

  it("does not present recovered catalog enumeration as an exact count", async () => {
    mocks.fetchTrackers.mockResolvedValue({
      data: {
        recovered_from_previous: true,
        projects: [{ project_id: "alpha", status: "available", tracker_candidates: 1 }],
        trackers: [tracker],
      },
      coverage: { status: "complete" },
    })

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    expect(await screen.findByRole("button", { name: "All: 1 returned, lower bound or partial coverage" })).toBeVisible()
  })

  it("falls back to all represented trackers for an unknown project URL value", async () => {
    renderRoute("/trackers?project=unknown", <TrackersPage />, "/trackers")

    expect(await screen.findByRole("link", { name: tracker.title })).toBeVisible()
    expect(screen.getByRole("combobox", { name: "Project" })).toHaveValue("all")
    expect(screen.getByRole("button", { name: "All: 1 exact" })).toBeVisible()
  })

  it("does not fabricate a run link for an exact task-only tracker association", async () => {
    const taskOnlyFloor = structuredClone(floor)
    taskOnlyFloor.data.rows[0].supervision.run_id = null
    taskOnlyFloor.data.rows[0].supervision.status = "unmonitored"
    mocks.fetchFactoryFloor.mockResolvedValue(taskOnlyFloor)

    renderRoute("/trackers", <TrackersPage />, "/trackers")

    const row = (await screen.findByRole("link", { name: tracker.title })).closest("article")!
    expect(row.querySelector('.tracker-index-run')).toHaveTextContent("None exact")
    expect(row.querySelector('a[href="/runs/null"]')).toBeNull()
  })

  it("renders contract overview and safe Block sections without mutation controls", async () => {
    const user = userEvent.setup()
    renderRoute(`/trackers/${tracker.id}/blocks`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Block 1 · Successor" })).toBeVisible()
    expect(screen.getByText("2 Blocks")).toBeVisible()
    expect(screen.getByText("2 Blocks").closest(".tracker-progress-view")?.querySelectorAll('a[href]')).toHaveLength(3)
    expect(screen.getByText("Render safely.")).toBeVisible()
    expect(screen.getByText("<script>SECRET</script>")).toBeVisible()
    expect(screen.getByText(/Unavailable in source: Capability delta/)).toBeVisible()
    expect(document.querySelector("script")).toBeNull()
    expect(screen.queryByRole("button", { name: /^(accept|edit|start)( tracker)?$/i })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Load exact source range" }))
    expect(await screen.findByText("Exact loaded source.")).toBeVisible()
    await waitFor(() => expect(mocks.fetchTrackerSource).toHaveBeenCalledWith(tracker.id, { line: 80, endLine: 90 }, expect.any(AbortSignal)))
  })

  it("marks blocked and transitively descendant-blocked dependency nodes", async () => {
    const blockedTracker = {
      ...tracker,
      current_blocks: [],
      current_block_details: [],
      eligible_blocks: [],
      blocks: [
        { ...tracker.blocks[0], status: "blocked", completion_evidence: { ...tracker.blocks[0].completion_evidence, posture: "open" } },
        { ...tracker.blocks[1], eligible: false, dependency_statuses: [{ number: 0, status: "blocked" }], blocked_ancestors: [0] },
        { ...tracker.blocks[1], number: 2, title: "Descendant", dependencies: [1], dependency_expression: "1", dependency_statuses: [{ number: 1, status: "not-started" }], blocked_ancestors: [0], eligible: false },
      ],
    }
    mocks.fetchTracker.mockResolvedValue({ data: { tracker: blockedTracker } })

    renderRoute(`/trackers/${tracker.id}/blocks`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Block 0 · Base" })).toBeVisible()
    expect(screen.getAllByText("blocked", { exact: true })[0]).toHaveClass("status-danger")
    expect(screen.getAllByText("Descendant-blocked · Blocks 0")).toHaveLength(2)
    expect(screen.getByText(/Successor · descendant-blocked by 0/)).toBeVisible()
    expect(screen.getByText(/Descendant · descendant-blocked by 0/)).toBeVisible()
  })

  it("shows deterministic semantic source changes, exact anchors, and unavailable run-bound hash honestly", async () => {
    const user = userEvent.setup()
    renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Git & currentness" })).toBeVisible()
    expect(screen.getByText("Working tree comparison")).toBeVisible()
    expect(screen.queryByText("Status: `in-progress`")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Load semantic changes" }))
    expect(await screen.findByText("Status: `in-progress`")).toBeVisible()
    expect(screen.getByText("Added")).toBeVisible()
    expect(screen.getByText("Removed")).toBeVisible()
    expect(screen.getAllByText("Changed")[1]).toBeVisible()
    expect(screen.getAllByRole("link", { name: /Before/ })[0]).toHaveAttribute(
      "href",
      `/api/v1/trackers/${tracker.id}/source?line=72&end_line=72&revision=${tracker.git.repository_head}`,
    )
    expect(screen.getAllByRole("link", { name: /After/ })[0]).toHaveAttribute(
      "href",
      `/api/v1/trackers/${tracker.id}/source?line=72&end_line=72&content_sha256=${tracker.raw_file.content_sha256}`,
    )
    expect(mocks.fetchTrackerDiff).toHaveBeenCalledWith(tracker.id, expect.any(AbortSignal))
    expect(screen.getByText(/bound hash unavailable from run owner/)).toBeVisible()
    expect(screen.getByRole("heading", { name: "Recorded Block evidence" })).toBeVisible()
    expect(screen.getByRole("link", { name: /Block 0.*Base/ })).toHaveAttribute("href", `/trackers/${tracker.id}/blocks?block=0`)
    expect(screen.getByText("These facts do not accept, edit, validate, or start the tracker.")).toBeVisible()
  })

  it("renders bounded hostile semantic text literally with keyboard-readable partial posture", async () => {
    const baseline = await mocks.fetchTrackerDiff()
    const semantic = baseline.data.diff.semantic
    mocks.fetchTrackerDiff.mockClear()
    mocks.fetchTrackerDiff.mockResolvedValue({
      ...baseline,
      data: {
        ...baseline.data,
        diff: {
          ...baseline.data.diff,
          semantic: {
            ...semantic,
            complete: false,
            truncated: true,
            limitations: [...semantic.limitations, "Row text is bounded."],
            rows: [{
              ...semantic.rows[0],
              after: {
                ...semantic.rows[0].after,
                text: '<img src="x" onerror="alert(1)">',
                text_truncated: true,
                block: { ...semantic.rows[0].after.block, title: "L".repeat(300) },
              },
            }],
            total_rows: 400,
            returned_rows: 1,
          },
        },
      },
    })
    const user = userEvent.setup()
    const rendered = renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    await user.click(await screen.findByRole("button", { name: "Load semantic changes" }))
    expect(await screen.findByText('<img src="x" onerror="alert(1)">')).toBeVisible()
    expect(rendered.container.querySelector('img[src="x"]')).toBeNull()
    expect(screen.getByText(/This comparison is partial/)).toBeVisible()
    const scrollRegion = screen.getByLabelText("Tracker semantic source changes")
    scrollRegion.focus()
    expect(scrollRegion).toHaveFocus()
    expect(scrollRegion.closest(".tracker-semantic-diff")?.querySelector("button")).toBeNull()
  })

  it("keeps a missing committed comparison unavailable rather than claiming no change", async () => {
    const baseline = await mocks.fetchTrackerDiff()
    const semantic = baseline.data.diff.semantic
    mocks.fetchTrackerDiff.mockClear()
    mocks.fetchTrackerDiff.mockResolvedValue({
      ...baseline,
      data: {
        ...baseline.data,
        diff: {
          ...baseline.data.diff,
          semantic: {
            ...semantic,
            status: "unavailable",
            changed: null,
            base: null,
            rows: [],
            total_rows: null,
            returned_rows: 0,
            complete: false,
            truncated: false,
            limitations: ["HEAD source is unavailable."],
            error: { code: "committed_tracker_unavailable", message: "The exact HEAD source is unavailable." },
          },
        },
      },
    })
    const user = userEvent.setup()
    renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    await user.click(await screen.findByRole("button", { name: "Load semantic changes" }))
    expect(await screen.findByText("The exact HEAD source is unavailable.")).toBeVisible()
    expect(screen.queryByText(/No semantic tracker changes/)).not.toBeInTheDocument()
  })

  it("keeps pending composed-owner facts unavailable instead of claiming none", async () => {
    mocks.fetchFactoryFloor.mockReturnValue(new Promise(() => undefined))
    renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Mapped execution" })).toBeVisible()
    expect(screen.getByText("Loading mapped run claims")).toBeVisible()
    expect(screen.getAllByText("Unavailable from composed owner")).toHaveLength(2)
    expect(screen.queryByText("No exact composed tracker/run claim")).not.toBeInTheDocument()
  })

  it("keeps unavailable Git, partial Floor coverage, and completed rows non-conclusive", async () => {
    mocks.fetchTracker.mockResolvedValue({
      data: {
        tracker: {
          ...tracker,
          git: {
            ...tracker.git,
            status: "unavailable",
            repository_head: null,
            binding_status: "unknown",
            diff: { status: "unavailable", changed: null, base: null, added_lines: null, removed_lines: null, preview: null, truncated: false, error: { code: "git_unavailable", message: "Git unavailable." } },
          },
          progress_posture: "unavailable",
        },
      },
    })
    mocks.fetchFactoryFloor.mockResolvedValue({
      ...floor,
      coverage: { status: "partial", observed: ["trackers"], missing: ["operations", "tasks"] },
      data: {
        ...floor.data,
        rows: [{
          ...floor.data.rows[0],
          supervision: { ...floor.data.rows[0].supervision, status: "completed" },
          implementation: { ...floor.data.rows[0].implementation, status: "terminal" },
        }],
      },
    })

    renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByText("Unavailable from Git owner")).toBeVisible()
    expect(screen.getByText("Unavailable from run owner")).toBeVisible()
    expect(screen.getByText("Exact absence unavailable · partial coverage")).toBeVisible()
    expect(screen.getByText(/No active claim was observed, but exact absence is unavailable/)).toBeVisible()
    expect(screen.queryByText(/1 exact active claim/)).not.toBeInTheDocument()
    expect(screen.queryByText("None observed")).not.toBeInTheDocument()
  })

  it("renders an explicit invalid state when no Block can be projected", async () => {
    mocks.fetchTracker.mockResolvedValue({
      data: {
        tracker: {
          ...tracker,
          verifier: { ...tracker.verifier, valid: false, exit_status: 1, blocks: [], errors: ["No Block headings found."] },
          counts: { ...tracker.counts, total: 0, accepted: 0, open: 0, by_status: {}, with_completion_evidence: 0, evidence_by_posture: {} },
          current_blocks: [],
          current_block_details: [],
          eligible_blocks: [],
          blocks: [],
        },
      },
    })

    renderRoute(`/trackers/${tracker.id}/blocks`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Block projection" })).toBeVisible()
    expect(screen.getByRole("alert")).toHaveTextContent("No Blocks could be projected")
    expect(screen.getByRole("link", { name: "Verifier diagnostics" })).toHaveAttribute("href", `/trackers/${tracker.id}/evidence`)
  })
})
