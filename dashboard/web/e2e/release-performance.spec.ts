import { expect, test } from "@playwright/test"

const target = "019fe547-e054-7ca0-9940-ec4aa146df78"

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
