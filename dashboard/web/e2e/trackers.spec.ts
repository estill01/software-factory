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
  const coreRow = page.locator(".tracker-index-row").filter({ hasText: coreSummary.title })
  await expect(coreRow).toContainText(`core profile · verifier ${coreSummary.verifier.valid ? "valid" : "failed"}`)
  await page.getByLabel("Posture").selectOption("current")
  await expect(page).toHaveURL(/posture=current/)
  await page.getByLabel("Posture").selectOption("all")

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
  const selectedSource = page.getByRole("link", { name: "Source", exact: true }).first()
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
  const loadDiff = page.getByRole("button", { name: "Load textual diff" })
  if (await loadDiff.count()) {
    await loadDiff.click()
    await expect(page.locator(".tracker-diff-preview")).toBeVisible()
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

  await page.goto("/trackers?posture=invalid")
  await expect(page.getByText("docs/missing-implementation-tracker.md", { exact: true }).first()).toBeVisible()
  await expect(page.getByRole("alert")).toContainText("Tracker disappeared during the bounded read.")
  await expect(page.locator(".workspace-partial")).toContainText("source coverage is partial")
  await expect(page.locator(".tracker-index-row")).toHaveCount(1)
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
