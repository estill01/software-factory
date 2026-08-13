import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

const target = "019fe547-e054-7ca0-9940-ec4aa146df78"

test("current Block 31 outcome projections preserve terminal counts, task provenance, and lifecycle currentness", async ({ page, request }) => {
  test.setTimeout(90_000)
  const trackerList = await request.get("/api/v1/trackers")
  expect(trackerList.ok()).toBeTruthy()
  const trackerEnvelope = await trackerList.json()
  const tracker = trackerEnvelope.data.trackers.find(
    (candidate: { relative_path?: string }) =>
      candidate.relative_path === "docs/software-factory-operations-dashboard-implementation-tracker.md",
  )
  expect(tracker).toBeTruthy()
  expect(tracker.counts).toMatchObject({ total: 32, accepted: 31, open: 1 })
  expect(tracker.counts.by_status).toMatchObject({ completed: 31, "in-progress": 1 })
  expect(tracker.current_block_details).toEqual([
    expect.objectContaining({ number: 31, status: "in-progress" }),
  ])

  await page.goto("/trackers")
  const trackerRow = page.locator(".tracker-index-row").filter({ hasText: tracker.title })
  await expect(trackerRow).toContainText("32 Blocks")
  await expect(trackerRow).toContainText("31/32 accepted")
  await expect(trackerRow).toContainText("Block 31 — Integrated outcome validation and operator handoff")

  await page.goto(`/tasks/${target}`)
  await expect(
    page.locator(`.task-workspace .workspace-identity-strip code[title="${target}"]`),
  ).toBeVisible()
  await expect(page.getByText(/Turn detail unavailable:/)).toHaveCount(0)
  await expect(page.locator(".task-turns details")).not.toHaveCount(0)
  await page.locator(".task-turns details").last().click()
  await expect(page.locator(".task-turns details").last().locator("article")).not.toHaveCount(0)

  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  expect(runEnvelope.data.run.lifecycle).toEqual({ status: null, record: null })
  expect(runEnvelope.data.run.timeline).toContainEqual(
    expect.objectContaining({ record_id: "EVT-000123", status: "failed" }),
  )
  expect(runEnvelope.data.run.light.facts).not.toContainEqual(
    expect.objectContaining({ rule: "lifecycle-failed" }),
  )
  await page.goto(`/runs/${target}`)
  const runIdentity = page.locator(".run-workspace .workspace-identity-strip")
  await expect(runIdentity).toContainText("in-progress")
  await expect(runIdentity.getByText("failed", { exact: true })).toHaveCount(0)

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(
    accessibility.violations.filter(({ impact }) => impact === "serious" || impact === "critical"),
  ).toEqual([])
})

test("current live corpus reaches an interactive Factory Floor with bounded rows", async ({ page }) => {
  const started = performance.now()
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Factory Floor", level: 1 })).toBeVisible()
  const firstRow = page.locator(".operational-disclosure-trigger").first()
  await expect(firstRow).toBeVisible()
  const interactiveMs = performance.now() - started

  const disclosureStarted = performance.now()
  await firstRow.click()
  await expect(firstRow).toHaveAttribute("aria-expanded", "true")
  const disclosureMs = performance.now() - disclosureStarted
  const renderedRows = await page.locator(".operational-disclosure").count()
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))

  expect(renderedRows).toBeLessThanOrEqual(80)
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  console.log(JSON.stringify({
    measurement: "current-live-floor",
    project: test.info().project.name,
    interactive_ms: Math.round(interactiveMs * 10) / 10,
    disclosure_ms: Math.round(disclosureMs * 10) / 10,
    rendered_rows: renderedRows,
  }))
})

test("deterministic two-times history expansion keeps event DOM paging bounded", async ({ page, request }) => {
  const response = await request.get(`/api/v1/runs/${target}`)
  expect(response.ok()).toBeTruthy()
  const envelope = await response.json()
  const run = envelope.data.run
  const originalTimeline = [...run.timeline]
  const originalEventCount = run.event_count

  const duplicateTimeline = originalTimeline.map((event: Record<string, unknown>, index: number) => ({
    ...event,
    record_id: `${String(event.record_id ?? "event")}-SYNTH-${index}`,
  }))
  run.timeline = [...originalTimeline, ...duplicateTimeline]
  run.event_count = originalEventCount * 2
  run.current_event_count *= 2
  run.mission_segments = run.mission_segments.map(
    (segment: Record<string, unknown> & { event_count: number }) => ({
      ...segment,
      event_count: segment.event_count * 2,
    }),
  )
  envelope.coverage = {
    status: "partial",
    observed: [...envelope.coverage.observed, "deterministic-2x-history"],
    missing: [...envelope.coverage.missing, "live-second-history-copy"],
  }
  envelope.limitations = [
    ...envelope.limitations,
    "Release-performance fixture duplicates retained event records with unique synthetic IDs.",
  ]

  const responseBytes = new TextEncoder().encode(JSON.stringify(envelope)).byteLength
  await page.route(`**/api/v1/runs/${target}`, (route) => route.fulfill({ json: envelope }))

  const started = performance.now()
  await page.goto(`/runs/${target}`)
  await expect(page.getByRole("heading", { name: "Run", level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Events", level: 2 })).toBeVisible()
  const interactiveMs = performance.now() - started

  const eventRows = await page.locator(".event-timeline > li").count()
  const pagination = page.getByRole("navigation", { name: "Event pages" })
  await expect(pagination.getByRole("button", { name: "Older" })).toBeEnabled()
  const pagingStarted = performance.now()
  await pagination.getByRole("button", { name: "Older" }).click()
  await expect(pagination.getByRole("button", { name: "Newer" })).toBeEnabled()
  const pagingMs = performance.now() - pagingStarted
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))

  expect(run.timeline).toHaveLength(originalTimeline.length * 2)
  expect(eventRows).toBeLessThanOrEqual(50)
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  console.log(JSON.stringify({
    measurement: "synthetic-2x-history",
    project: test.info().project.name,
    source_events: originalEventCount,
    projected_events: run.event_count,
    response_bytes: responseBytes,
    interactive_ms: Math.round(interactiveMs * 10) / 10,
    paging_ms: Math.round(pagingMs * 10) / 10,
    rendered_event_rows: eventRows,
  }))
})
