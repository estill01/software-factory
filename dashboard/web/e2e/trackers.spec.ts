import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

import { makeFactoryFloorEnvelope } from "../src/test/factory-floor-fixture"

test("tracker review stays source-grounded, navigable, and read-only", async ({ page, request }) => {
  const listResponse = await request.get("/api/v1/trackers")
  expect(listResponse.ok()).toBeTruthy()
  const listPayload = await listResponse.json()
  const summary = listPayload.data.trackers.find(
    (tracker: { status: string; relative_path?: string }) =>
      tracker.status === "available"
      && tracker.relative_path === "docs/software-factory-operations-dashboard-implementation-tracker.md",
  ) ?? listPayload.data.trackers.find((tracker: { status: string }) => tracker.status === "available")
  expect(summary).toBeTruthy()
  const coreSummary = listPayload.data.trackers.find(
    (tracker: { status: string; profile?: string }) => tracker.status === "available" && tracker.profile === "core",
  )
  expect(coreSummary).toBeTruthy()

  const detailResponse = await request.get(`/api/v1/trackers/${summary.id}`)
  expect(detailResponse.ok()).toBeTruthy()
  const tracker = (await detailResponse.json()).data.tracker
  const expectedBlock = tracker.blocks.find(
    (block: { number: number }) => tracker.current_blocks.includes(block.number),
  ) ?? tracker.blocks.find((block: { number: number }) => tracker.eligible_blocks.includes(block.number))
    ?? tracker.blocks[0]

  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )
  await page.goto("/trackers")

  await expect(page.getByRole("heading", { name: "Trackers", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  const trackerRow = page.locator(".tracker-index-row").filter({ hasText: summary.title })
  await expect(trackerRow).toContainText(`${summary.profile} profile · verifier ${summary.verifier.valid ? "valid" : "failed"}`)
  await expect(trackerRow).toContainText(`${summary.counts.total} Blocks`)
  for (const block of summary.current_block_details) {
    await expect(trackerRow).toContainText(`Block ${block.number} — ${block.title}`)
  }
  const coreRow = page.locator(".tracker-index-row").filter({ hasText: coreSummary.title })
  await expect(coreRow).toContainText(`core profile · verifier ${coreSummary.verifier.valid ? "valid" : "failed"}`)
  const activeFilter = page.getByRole("button", { name: /^Active \/ Running:/ })
  await activeFilter.focus()
  await activeFilter.press("Enter")
  await expect(page).toHaveURL(/activity=active/)
  await page.getByRole("button", { name: /^All:/ }).click()
  await expect(page).not.toHaveURL(/activity=/)

  await page.getByRole("link", { name: coreSummary.title }).click()
  await expect(page.locator(".workspace-status").filter({ hasText: /^core$/ })).toBeVisible()
  await page.goto("/trackers")

  await page.getByRole("link", { name: summary.title }).click()
  await expect(page.getByText(summary.relative_path, { exact: false }).first()).toBeVisible()
  await expect(page.getByRole("link", { name: "Open read-only Markdown" })).toHaveAttribute(
    "href",
    `/api/v1/trackers/${summary.id}/source`,
  )

  await page.getByRole("link", { name: "Blocks", exact: true }).click()
  await expect(page.getByRole("heading", { name: `Block ${expectedBlock.number} · ${expectedBlock.title}` })).toBeVisible()
  const selectedSource = page.locator(`a[href^="/api/v1/trackers/${summary.id}/source?line="]`).first()
  await expect(selectedSource).toHaveAttribute("href", /\/source\?line=\d+&end_line=\d+/)
  await expect(page.getByRole("button", { name: /^(accept|edit|start)( tracker)?$/i })).toHaveCount(0)

  const nextBlock = tracker.blocks.find((block: { number: number }) => block.number !== expectedBlock.number)
  if (nextBlock) {
    await page.getByRole("button", { name: new RegExp(`^Block ${nextBlock.number}\\b`) }).press("Enter")
    await expect(page.getByRole("heading", { name: `Block ${nextBlock.number} · ${nextBlock.title}` })).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`block=${nextBlock.number}`))
  }

  await page.getByRole("link", { name: "Evidence", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Git & currentness" })).toBeVisible()
  await expect(page.getByText("These facts do not accept, edit, validate, or start the tracker.")).toBeVisible()
  await expect(page.getByRole("link", { name: "Raw source" })).toHaveAttribute(
    "href",
    `/api/v1/trackers/${summary.id}/source`,
  )
  await expect(page.getByRole("heading", { name: "Recorded Block evidence" })).toBeVisible()
  await expect(page.getByRole("link", { name: /^Block \d+/ }).first()).toBeVisible()
  const loadDiff = page.getByRole("button", { name: "Load semantic changes" })
  if (await loadDiff.count()) {
    await loadDiff.click()
    await expect(page.locator(".tracker-semantic-diff")).toBeVisible()
    await expect(page.getByRole("button", { name: /^(accept|edit|start)( tracker)?$/i })).toHaveCount(0)
  }

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations.filter(({ impact }) => impact === "serious" || impact === "critical")).toEqual([])

  await page.emulateMedia({ media: "print" })
  await expect(page.locator(".workspace-toolbar.print-hide")).not.toBeVisible()
})

test("semantic tracker rows preserve exact source truth across responsive themes", async ({ page, request }) => {
  const listPayload = await (await request.get("/api/v1/trackers")).json()
  const summary = listPayload.data.trackers.find(
    (candidate: { status: string; relative_path?: string }) =>
      candidate.status === "available"
      && candidate.relative_path === "docs/software-factory-operations-dashboard-implementation-tracker.md",
  ) ?? listPayload.data.trackers.find((candidate: { status: string }) => candidate.status === "available")
  expect(summary).toBeTruthy()
  const detailPayload = await (await request.get(`/api/v1/trackers/${summary.id}`)).json()
  const tracker = detailPayload.data.tracker
  const repositoryHead = tracker.git.repository_head
  const committedRoot = tracker.git.committed_content_sha256
  expect(repositoryHead).toBeTruthy()
  expect(committedRoot).toBeTruthy()

  const detailFixture = structuredClone(detailPayload)
  detailFixture.data.tracker.git.worktree_changed = true
  detailFixture.data.tracker.git.content_matches_head = false
  detailFixture.data.tracker.git.diff = {
    status: "available",
    changed: true,
    base: "HEAD",
    added_lines: 2,
    removed_lines: 2,
    preview: null,
    truncated: false,
    semantic: null,
    error: null,
  }
  const verifierIdentity = {
    ...tracker.verifier.owner,
    profile: tracker.verifier.profile,
    valid: tracker.verifier.valid,
  }
  const block = tracker.blocks[0]
  const boundedLongTitle = `${block.title} ${"long-title ".repeat(15)}`.slice(0, 160)
  const semantic = {
    status: "available",
    changed: true,
    base: { kind: "HEAD", repository_revision: repositoryHead, content_sha256: committedRoot },
    target: { kind: "working-tree", content_sha256: tracker.raw_file.content_sha256 },
    rows: [
      {
        id: "a".repeat(64),
        kind: "changed",
        before: { text: "Status: `not-started`", text_truncated: false, line: block.status_line, content_sha256: committedRoot, block: { number: block.number, title: block.title, title_truncated: false, line: block.line, anchor: block.anchor, anchor_truncated: false } },
        after: { text: "Status: `in-progress`", text_truncated: false, line: block.status_line, content_sha256: tracker.raw_file.content_sha256, block: { number: block.number, title: boundedLongTitle, title_truncated: true, line: block.line, anchor: block.anchor, anchor_truncated: false } },
      },
      {
        id: "b".repeat(64),
        kind: "removed",
        before: { text: "Pending.", text_truncated: false, line: block.line + 2, content_sha256: committedRoot, block: { number: block.number, title: block.title, title_truncated: false, line: block.line, anchor: block.anchor, anchor_truncated: false } },
        after: null,
      },
      {
        id: "c".repeat(64),
        kind: "added",
        before: null,
        after: { text: "<script>alert('literal')</script>", text_truncated: false, line: block.line + 3, content_sha256: tracker.raw_file.content_sha256, block: { number: block.number, title: block.title, title_truncated: false, line: block.line, anchor: block.anchor, anchor_truncated: false } },
      },
    ],
    total_rows: 3,
    returned_rows: 3,
    row_limit: 200,
    complete: false,
    truncated: true,
    path: tracker.relative_path,
    owning_revision: tracker.git.last_commit?.revision ?? null,
    owner: { tracker: "tracker-markdown/read-only", git: "git/HEAD-and-working-tree", verifier: verifierIdentity },
    currentness_fingerprint: "d".repeat(64),
    limitations: [
      "Only the selected tracker path is compared; unrelated repository changes are excluded.",
      "Rows are read-only.",
    ],
    error: null,
  }
  const diffFixture = {
    data: {
      tracker_id: tracker.id,
      content_sha256: tracker.raw_file.content_sha256,
      repository_head: repositoryHead,
      relative_path: tracker.relative_path,
      owning_revision: tracker.git.last_commit?.revision ?? null,
      verifier: verifierIdentity,
      diff: { ...detailFixture.data.tracker.git.diff, preview: "", semantic },
    },
    source: { kind: "tracker-git-diff", identity: `software-factory-dashboard/trackers/${tracker.id}/diff`, revision: tracker.raw_file.content_sha256 },
    observed_at: detailPayload.observed_at,
    fingerprint: "e".repeat(64),
    coverage: { status: "complete", observed: ["tracker-working-content", "git-head-diff", "tracker-semantic-diff"], missing: [] },
    limitations: ["Bounded read-only selected-tracker comparison."],
    error: null,
  }

  await page.route(`**/api/v1/trackers/${tracker.id}`, (route) => route.fulfill({ json: detailFixture }))
  await page.route(`**/api/v1/trackers/${tracker.id}/diff`, (route) => route.fulfill({ json: diffFixture }))
  await page.route("**/api/v1/factory-floor", (route) => route.fulfill({ json: makeFactoryFloorEnvelope() }))
  await page.goto(`/trackers/${tracker.id}/evidence`)
  await page.getByRole("button", { name: "Load semantic changes" }).click()

  const table = page.getByRole("table", { name: "Bounded semantic changes between the tracker at HEAD and its working source" })
  await expect(table).toBeVisible()
  await expect(table.getByText("Added")).toBeVisible()
  await expect(table.getByText("Removed")).toBeVisible()
  await expect(table.getByText("Changed")).toBeVisible()
  await expect(table.getByText("<script>alert('literal')</script>")).toBeVisible()
  await expect(page.locator("script").filter({ hasText: "literal" })).toHaveCount(0)
  await expect(table.getByRole("link", { name: /Before/ }).first()).toHaveAttribute("href", new RegExp(`revision=${repositoryHead}$`))
  await expect(table.getByRole("link", { name: /After/ }).first()).toHaveAttribute("href", new RegExp(`content_sha256=${tracker.raw_file.content_sha256}$`))
  await expect(page.locator(".tracker-semantic-diff button")).toHaveCount(0)
  const scrollRegion = page.getByLabel("Tracker semantic source changes")
  await scrollRegion.focus()
  await expect(scrollRegion).toBeFocused()

  const initialTheme = await page.locator("html").getAttribute("data-theme")
  await page.getByRole("button", { name: /Switch to (light|dark) mode/ }).click()
  await expect(page.locator("html")).toHaveAttribute("data-theme", initialTheme === "dark" ? "light" : "dark")
  await expect(table).toBeVisible()
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations.filter(({ impact }) => impact === "serious" || impact === "critical")).toEqual([])
})

test("factory workflow controls stay compact and preview exact owner scope", async ({ page, request }) => {
  const listPayload = await (await request.get("/api/v1/trackers")).json()
  const summary = listPayload.data.trackers.find(
    (tracker: { status: string; relative_path?: string }) =>
      tracker.status === "available"
      && tracker.relative_path === "docs/software-factory-operations-dashboard-implementation-tracker.md",
  ) ?? listPayload.data.trackers.find((tracker: { status: string }) => tracker.status === "available")
  expect(summary).toBeTruthy()

  const sourceFingerprint = "e".repeat(64)
  const observedAt = "2026-08-10T10:30:00.000Z"
  const operation = {
    id: "op_e2e_workflow_preview",
    type: "factory.tracker-review",
    target: { kind: "tracker", id: summary.id, project_id: summary.project_id },
    state: "previewed",
    owner: "$author-implementation-trackers + Codex App Server",
    authority: ["explicit operator confirmation", "exact tracker and Git snapshot"],
    preview: {
      effect: `Create one independent read-only tracker review task for ${summary.relative_path}.`,
      risk: "The task reads exact tracker and Git sources but receives no edit authorization.",
      recipient: null,
      semantic_changes: {
        status: "unavailable",
        complete: false,
        rows: [],
        limitations: ["No owner-supplied semantic comparison is registered for this operation."],
      },
      source_fingerprint: sourceFingerprint,
      source_evidence: { tracker_path: summary.relative_path },
      route_gate: {
        status: "not-required",
        target_thread: null,
        recipient: null,
        purpose: null,
        source_record: null,
        required_action: null,
        action_hash: null,
        policy_fingerprint: null,
        binding_fingerprint: null,
      },
      consequences: {
        ordinary: ["Creates one Codex task in the registered repository."],
        failure: ["Stale or ineligible sources fail before task creation."],
      },
      confirmation: {
        class: "factory-review",
        prompt: "Type REVIEW to create the read-only review task.",
        expected_value: "REVIEW",
      },
      expected_postcondition: "One exact task and first turn request a read-only maintained-skill review; no edit or acceptance is implied.",
      idempotency: "One task per consumed preview; no automatic retry.",
      limitations: ["Task start is separate from tracker status and Block acceptance."],
      expires_at: "2026-08-10T10:35:00.000Z",
    },
    history: [{ state: "previewed", observed_at: observedAt }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  const envelope = (record: typeof operation, previewToken = true) => ({
    data: previewToken
      ? { operation: record, preview_token: "p".repeat(32) }
      : { operation: record },
    source: { kind: "administrative-operation", identity: record.id, revision: sourceFingerprint },
    observed_at: observedAt,
    fingerprint: sourceFingerprint,
    coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
    limitations: ["Fixture isolates the browser contract from live adapter availability."],
    error: null,
  })
  await page.route("**/api/v1/operations/preview", (route) =>
    route.fulfill({ json: envelope(operation) }),
  )
  await page.route("**/api/v1/operations/op_e2e_workflow_preview/cancel", (route) =>
    route.fulfill({
      json: envelope({
        ...operation,
        state: "cancelled",
        history: [...operation.history, { state: "cancelled", observed_at: observedAt }],
      }, false),
    }),
  )

  await page.goto(`/trackers/${summary.id}/blocks`)
  const actions = page.getByLabel("Available actions")
  await expect(actions).toBeVisible()
  await expect(actions.getByRole("button", { name: "Review" })).toBeVisible()
  await expect(actions.getByRole("button", { name: "Revise" })).toBeVisible()
  await expect(actions.getByRole("button", { name: "Implement" })).toBeVisible()

  await actions.getByRole("button", { name: "Review" }).click()
  const preview = page.getByRole("dialog")
  await expect(preview).toBeVisible()
  await expect(preview.getByText("Full tracker contract, dependency order, acceptance, negative tests, Stops, source currentness, and implementation readiness.")).toBeVisible()
  await expect(preview.getByText(summary.relative_path, { exact: false })).toBeVisible()
  const factOverflow = await preview.locator(".operation-preview-facts > div").evaluateAll((cells) =>
    cells.map((cell) => cell.scrollWidth - cell.clientWidth),
  )
  expect(factOverflow.every((overflow) => overflow <= 1)).toBeTruthy()
  await preview.getByRole("button", { name: "Close operation preview" }).click()

  await page.goto("/admin")
  await expect(page.getByText("Preview + confirmation", { exact: true })).toHaveCount(0)
  await expect(page.getByText("Session-local activity", { exact: true })).toHaveCount(0)
  await expect(page.getByText("Canonical postconditions", { exact: true })).toHaveCount(0)
  await expect(page.locator("h1")).toHaveCount(1)

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test("unavailable tracker candidates remain independent and explicit", async ({ page }) => {
  await page.route("**/api/v1/trackers", async (route) => {
    const upstream = await route.fetch()
    const payload = await upstream.json()
    payload.data.trackers.push({
      id: "f".repeat(64),
      project_id: "missing-project",
      project_label: "Missing project",
      relative_path: "docs/missing-implementation-tracker.md",
      status: "unavailable",
      observed_at: "2026-08-09T10:00:00.000Z",
      fingerprint: null,
      source: {
        kind: "tracker-markdown",
        identity: "missing-project:docs/missing-implementation-tracker.md",
        revision: "unavailable",
      },
      coverage: { status: "unavailable", observed: [], missing: ["tracker"] },
      limitations: ["This candidate failed independently."],
      error: {
        code: "tracker_unavailable",
        message: "Tracker disappeared during the bounded read.",
        retryable: false,
      },
    })
    payload.coverage.status = "partial"
    payload.coverage.missing = [...new Set([...payload.coverage.missing, "tracker-projection"])]
    await route.fulfill({ response: upstream, json: payload })
  })
  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )

  await page.goto("/trackers?project=missing-project&activity=attention")
  await expect(page.getByText("docs/missing-implementation-tracker.md", { exact: true }).first()).toBeVisible()
  await expect(page.locator(".tracker-index-row")).toContainText("Tracker disappeared during the bounded read.")
  await expect(page.locator(".workspace-partial")).toContainText("counts and claims are marked exact, partial, or unavailable")
  await expect(page.locator(".tracker-index-row")).toHaveCount(1)
  await expect(page.getByRole("button", { name: /^All: 1 returned, lower bound or partial coverage$/ })).toBeVisible()
})

test("dependency, Git, coverage, and active-run truth remain explicit", async ({ page, request }) => {
  const listPayload = await (await request.get("/api/v1/trackers")).json()
  const summary = listPayload.data.trackers.find(
    (tracker: { status: string; relative_path?: string }) =>
      tracker.status === "available"
      && tracker.relative_path === "docs/software-factory-operations-dashboard-implementation-tracker.md",
  )
  expect(summary).toBeTruthy()
  const detailPayload = await (await request.get(`/api/v1/trackers/${summary.id}`)).json()
  const sourceBlocks = detailPayload.data.tracker.blocks
  expect(sourceBlocks.length).toBeGreaterThanOrEqual(3)
  detailPayload.data.tracker.current_blocks = []
  detailPayload.data.tracker.current_block_details = []
  detailPayload.data.tracker.eligible_blocks = []
  detailPayload.data.tracker.blocks = [
    { ...sourceBlocks[0], status: "blocked", blocked_ancestors: [] },
    { ...sourceBlocks[1], status: "not-started", dependencies: [0], dependency_statuses: [{ number: 0, status: "blocked" }], blocked_ancestors: [0], eligible: false },
    { ...sourceBlocks[2], status: "not-started", dependencies: [1], dependency_statuses: [{ number: 1, status: "not-started" }], blocked_ancestors: [0], eligible: false },
  ]
  detailPayload.data.tracker.git = {
    ...detailPayload.data.tracker.git,
    status: "unavailable",
    repository_head: null,
    binding_status: "unknown",
    diff: {
      status: "unavailable",
      changed: null,
      base: null,
      added_lines: null,
      removed_lines: null,
      preview: null,
      truncated: false,
      error: { code: "git_unavailable", message: "Git owner is unavailable." },
    },
  }
  detailPayload.data.tracker.progress_posture = "unavailable"
  await page.route(`**/api/v1/trackers/${summary.id}`, (route) =>
    route.fulfill({ json: detailPayload }),
  )

  const floor = makeFactoryFloorEnvelope()
  const terminalRow = {
    ...floor.data.rows[0],
    implementation: { ...floor.data.rows[0].implementation, status: "terminal" as const, status_label: "Completed" },
    supervision: { ...floor.data.rows[0].supervision, status: "completed" as const, status_label: "Completed" },
    work: {
      ...floor.data.rows[0].work,
      tracker: {
        status: "exact" as const,
        id: summary.id,
        title: summary.title,
        relative_path: summary.relative_path,
        candidates: [],
      },
    },
  }
  floor.data.rows = [terminalRow]
  floor.data.rows_truncated = false
  floor.coverage = { status: "partial", observed: ["trackers"], missing: ["operations", "tasks"] }
  await page.route("**/api/v1/factory-floor", (route) => route.fulfill({ json: floor }))

  await page.goto(`/trackers/${summary.id}/blocks`)
  await expect(page.locator(".workspace-status.status-danger").filter({ hasText: /^blocked$/i }).first()).toBeVisible()
  await expect(page.getByText("Descendant-blocked · Blocks 0")).toHaveCount(2)

  await page.getByRole("link", { name: "Evidence", exact: true }).click()
  await expect(page.getByText("Unavailable from Git owner")).toBeVisible()
  await expect(page.getByText("Unavailable from run owner")).toBeVisible()
  await expect(page.getByText("Exact absence unavailable · partial coverage")).toBeVisible()
  await expect(page.getByText(/No active claim was observed, but exact absence is unavailable/)).toBeVisible()
  await expect(page.getByText("None observed")).toHaveCount(0)
  await expect(page.getByText(/1 exact active claim/)).toHaveCount(0)
})

test("an invalid zero-Block projection renders an explicit review state", async ({ page, request }) => {
  const listPayload = await (await request.get("/api/v1/trackers")).json()
  const summary = listPayload.data.trackers.find((tracker: { status: string }) => tracker.status === "available")
  expect(summary).toBeTruthy()
  const detailPayload = await (await request.get(`/api/v1/trackers/${summary.id}`)).json()
  detailPayload.data.tracker.blocks = []
  detailPayload.data.tracker.current_blocks = []
  detailPayload.data.tracker.current_block_details = []
  detailPayload.data.tracker.eligible_blocks = []
  detailPayload.data.tracker.verifier = {
    ...detailPayload.data.tracker.verifier,
    valid: false,
    exit_status: 1,
    blocks: [],
    errors: ["No Block headings found."],
  }
  detailPayload.data.tracker.counts = {
    total: 0,
    by_status: {},
    accepted: 0,
    open: 0,
    with_completion_evidence: 0,
    evidence_by_posture: {},
  }
  await page.route(`**/api/v1/trackers/${summary.id}`, (route) =>
    route.fulfill({ json: detailPayload }),
  )
  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )

  await page.goto(`/trackers/${summary.id}/blocks`)

  await expect(page.getByRole("heading", { name: "Block projection" })).toBeVisible()
  await expect(page.getByRole("alert")).toContainText("No Blocks could be projected")
  await expect(page.getByRole("link", { name: "Verifier diagnostics" })).toHaveAttribute(
    "href",
    `/trackers/${summary.id}/evidence`,
  )
})
