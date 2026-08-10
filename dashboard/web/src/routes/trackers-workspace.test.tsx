import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

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
      number: 0, title: "Base", line: 30, anchor: "block-0-base", status: "accepted", status_line: 32, dependencies: [], dependency_expression: "—", objective: "Establish the base.", stop: "Stop before Block 1.", capability_delta: { posture: "consequential" }, completion_evidence: { present: true, posture: "recorded", line: 60, preview: "Commit recorded." }, sections: [{ title: "Objective", normalized_title: "objective", line: 34, end_line: 37, anchor: "objective", markdown_preview: "Establish the exact base.", preview_truncated: false, content_sha256: fingerprint("a") }], dependency_statuses: [], eligible: false,
    },
    {
      number: 1, title: "Successor", line: 70, anchor: "block-1-successor", status: "not-started", status_line: 72, dependencies: [0], dependency_expression: "0", objective: "Add the review workspace.", stop: "Stop before mutation.", capability_delta: { posture: "consequential" }, completion_evidence: { present: false, posture: "open", line: 95, preview: null }, sections: [{ title: "Required work", normalized_title: "required work", line: 80, end_line: 90, anchor: "required-work", markdown_preview: "- Render safely.\n- <script>SECRET</script>", preview_truncated: true, content_sha256: fingerprint("b") }], dependency_statuses: [{ number: 0, status: "accepted" }], eligible: true,
    },
  ],
  parser_limitations: ["Exact source ranges remain authoritative."],
  analysis_cache: { status: "miss", key: fingerprint("c") },
}

const floor = {
  data: {
    rows: [{
      id: "run:target-1",
      work: { tracker: { status: "exact", id: tracker.id, title: tracker.title, relative_path: tracker.relative_path } },
      supervision: { run_id: "target-1" },
      implementation: { task_id: "target-1", name: "Alpha implementation" },
      freshness: { observed_at: "2026-08-09T10:00:00.000Z" },
    }],
    accepted_outcomes: [{ tracker_id: tracker.id }],
  },
}

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
    mocks.fetchTrackers.mockResolvedValue({ data: { trackers: [tracker] }, coverage: { status: "complete" } })
    mocks.fetchTracker.mockResolvedValue({ data: { tracker } })
    mocks.fetchTrackerDiff.mockResolvedValue({
      data: {
        tracker_id: tracker.id,
        content_sha256: tracker.raw_file.content_sha256,
        repository_head: tracker.git.repository_head,
        diff: { ...tracker.git.diff, preview: "@@ -1 +1 @@\n-old\n+new" },
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
    await user.selectOptions(screen.getByLabelText("Posture"), "current")
    expect(screen.getByText("No trackers match the current filters")).toBeVisible()
  })

  it("renders contract overview and safe Block sections without mutation controls", async () => {
    const user = userEvent.setup()
    renderRoute(`/trackers/${tracker.id}/blocks`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Block 1 · Successor" })).toBeVisible()
    expect(screen.getByText("Render safely.")).toBeVisible()
    expect(screen.getByText("<script>SECRET</script>")).toBeVisible()
    expect(screen.getByText(/Unavailable in source: Capability delta/)).toBeVisible()
    expect(document.querySelector("script")).toBeNull()
    expect(screen.queryByRole("button", { name: /^(accept|edit|start)( tracker)?$/i })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Load exact source range" }))
    expect(await screen.findByText("Exact loaded source.")).toBeVisible()
    await waitFor(() => expect(mocks.fetchTrackerSource).toHaveBeenCalledWith(tracker.id, { line: 80, endLine: 90 }, expect.any(AbortSignal)))
  })

  it("shows deterministic evidence, lazy diff metadata, and unavailable run-bound hash honestly", async () => {
    const user = userEvent.setup()
    renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Git & currentness" })).toBeVisible()
    expect(screen.getByText("Working tree comparison")).toBeVisible()
    expect(screen.queryByText("@@ -1 +1 @@", { exact: false })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Load textual diff" }))
    expect(await screen.findByText("@@ -1 +1 @@", { exact: false })).toBeVisible()
    expect(mocks.fetchTrackerDiff).toHaveBeenCalledWith(tracker.id, expect.any(AbortSignal))
    expect(screen.getByText(/bound hash unavailable from run owner/)).toBeVisible()
    expect(screen.getByRole("heading", { name: "Recorded Block evidence" })).toBeVisible()
    expect(screen.getByRole("link", { name: /Block 0.*Base/ })).toHaveAttribute("href", `/trackers/${tracker.id}/blocks?block=0`)
    expect(screen.getByText("These facts do not accept, edit, validate, or start the tracker.")).toBeVisible()
  })

  it("keeps pending composed-owner facts unavailable instead of claiming none", async () => {
    mocks.fetchFactoryFloor.mockReturnValue(new Promise(() => undefined))
    renderRoute(`/trackers/${tracker.id}/evidence`, <TrackerWorkspace />, "/trackers/:trackerId/:view?")

    expect(await screen.findByRole("heading", { name: "Mapped execution" })).toBeVisible()
    expect(screen.getByText("Loading mapped run claims")).toBeVisible()
    expect(screen.getAllByText("Unavailable from composed owner")).toHaveLength(2)
    expect(screen.queryByText("No exact composed tracker/run claim")).not.toBeInTheDocument()
  })
})
