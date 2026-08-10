import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

import { makeFactoryFloorEnvelope } from "../src/test/factory-floor-fixture"

const catalogFingerprint = "a".repeat(64)

const integrationEnvelope = {
  data: {
    integration: {
      status: "available",
      protocol_status: "compatible",
      cli: { command: ["/usr/local/bin/codex"], version: "codex-cli 0.145.0", expected_version: "codex-cli 0.145.0" },
      schema: { semantic_manifest_sha256: "e".repeat(64), expected_semantic_manifest_sha256: "e".repeat(64), file_count: 273, expected_file_count: 273 },
      transport: { kind: "stdio", child_running: true },
      reconnect: { failure_count: 0, retry_after_ms: 0, maximum_delay_ms: 30_000 },
      features: [
        { capability: "task_list", status: "supported", exposure: "read", reason: null },
        { capability: "raw_protocol", status: "unavailable", exposure: "unavailable", reason: "Never exposed." },
      ],
      pending_requests: 0,
      last_error: null,
      restart_count: 0,
      connection_generation: 1,
      ignored_protocol_messages: 0,
      observed_at: "2026-08-09T10:00:00.000Z",
      revision: "f".repeat(64),
    },
  },
  source: { kind: "codex-app-server", identity: "software-factory-dashboard/task-integration", revision: "f".repeat(64) },
  observed_at: "2026-08-09T10:00:00.000Z",
  fingerprint: "1".repeat(64),
  coverage: { status: "complete", observed: ["codex-app-server"], missing: [] },
  limitations: [],
  error: null,
}

function project(id: string, status: "available" | "unavailable", archived = false) {
  const available = status === "available"
  return {
    id,
    label: `${id[0].toUpperCase()}${id.slice(1)}`,
    root: `/work/${id}`,
    tracker_patterns: [],
    description: `${id} project`,
    archived,
    observed_at: "2026-08-09T10:00:00.000Z",
    discovery: {
      status,
      fingerprint: available ? "b".repeat(64) : null,
      git: {
        status,
        revision: available ? "c".repeat(40) : null,
        branch: available ? "main" : null,
      },
      trackers: {
        status,
        candidates: available ? [`docs/${id}-implementation-tracker.md`] : [],
      },
      source_families: {
        supervision: { status: "unavailable", reason: "Use the source-owning run API." },
        codex_tasks: { status: "unavailable", reason: "Use the source-owning task API." },
      },
      coverage: available ? "partial" : "unavailable",
      limitations: ["Tracker paths only."],
      errors: available ? [] : [{ code: "missing_project_root", message: "Registered project root is missing." }],
    },
  }
}

function catalog(projects: ReturnType<typeof project>[]) {
  return {
    data: {
      catalog_fingerprint: catalogFingerprint,
      recovered_from_previous: false,
      projects,
    },
    source: {
      kind: "dashboard-catalog",
      identity: "software-factory-dashboard/project-catalog",
      revision: catalogFingerprint,
    },
    observed_at: "2026-08-09T10:00:00.000Z",
    fingerprint: "d".repeat(64),
    coverage: { status: "partial", observed: ["catalog"], missing: ["tracker-content"] },
    limitations: ["Tracker paths only."],
    error: null,
  }
}

test("factory shell exposes honest state and working navigation", async ({ page }) => {
  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Factory Floor", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  await expect(page.getByRole("status", { name: /Local runtime online/ })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Implementations & supervisors" })).toBeVisible()

  const themeToggle = page.getByRole("button", { name: /Switch to (light|dark) mode/ })
  const initialTheme = await page.locator("html").getAttribute("data-theme")
  await themeToggle.click()
  await expect(page.locator("html")).toHaveAttribute(
    "data-theme",
    initialTheme === "dark" ? "light" : "dark",
  )

  await page.getByRole("link", { name: "Trackers", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Trackers", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  await expect(page.getByRole("heading", { name: "Tracker workspace unavailable" })).toBeVisible()
  await expect(page).toHaveURL(/\/trackers$/)

})

test("shell has no serious accessibility violations", async ({ page }) => {
  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Implementations & supervisors" })).toBeVisible()
  const results = await new AxeBuilder({ page }).analyze()
  const material = results.violations.filter(({ impact }) =>
    impact === "serious" || impact === "critical",
  )
  expect(material).toEqual([])
})

test("maintained viewport has no horizontal page overflow", async ({ page }) => {
  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Implementations & supervisors" })).toBeVisible()
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test("unknown client routes render the bounded not-found state", async ({ page }) => {
  await page.goto("/does-not-exist")
  await expect(page.getByRole("heading", { name: "Not found", level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Route not found" })).toBeVisible()
  await expect(page.getByText("No operation was attempted.")).toBeVisible()
})

test("failed runtime health never leaves a ready claim behind", async ({ page }) => {
  await page.route("**/api/v1/health", (route) => route.abort())
  await page.route("**/api/v1/factory-floor", (route) => route.abort())
  await page.goto("/")

  await expect(page.getByRole("status", { name: "Runtime unavailable" })).toBeVisible()
  await expect(page.getByRole("alert")).toContainText("Factory Floor unavailable")
  await expect(page.getByText("Connected and locally constrained")).toHaveCount(0)
  await expect(page.getByText("Sources current")).toHaveCount(0)
  await expect(page.getByText("On track", { exact: true })).toHaveCount(0)
})

test("loading, empty, and stale-source states remain explicit", async ({ page }) => {
  const empty = makeFactoryFloorEnvelope()
  empty.data.rows = []
  empty.data.attention = []
  empty.data.conclusions = []
  empty.data.accepted_outcomes = []
  empty.data.summary = {
    registered_projects: 3,
    active_implementations: 0,
    supervisor_groups: 0,
    action_required: 0,
    postures: { red: 0, amber: 0, green: 0, neutral: 0 },
  }
  empty.data.source_health[0].status = "partial"
  empty.data.source_health[0].coverage.status = "partial"
  empty.data.source_health[0].reason = "Last successful catalog read is stale."
  empty.data.source_health[0].coverage.missing = ["current-catalog-read"]

  await page.route("**/api/v1/factory-floor", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500))
    await route.fulfill({ json: empty })
  })
  await page.goto("/", { waitUntil: "domcontentloaded" })

  await expect(page.getByText("Loading Factory Floor")).toBeVisible()
  await expect(page.getByText("No rows match the current filters.")).toBeVisible()
  await expect(page.getByText("No attention items match the current filters.")).toBeVisible()
  await expect(page.getByText("No current conclusions in range.")).toBeVisible()
  await expect(page.getByText("No accepted tracker outcomes in range.")).toBeVisible()
  const catalogSource = page.getByRole("link", { name: /Project catalog partial/ })
  await catalogSource.click()
  await expect(page.getByRole("complementary", { name: "Factory source inspector" }))
    .toContainText("Last successful catalog read is stale.")
})

test("three-project floor keeps operations, attention, outcomes, and partial truth actionable", async ({ page }) => {
  await page.route("**/api/v1/factory-floor", (route) =>
    route.fulfill({ json: makeFactoryFloorEnvelope() }),
  )
  await page.goto("/")

  await expect(page.locator("h1")).toHaveCount(1)
  await expect(page.getByRole("heading", { name: "Implementations & supervisors" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Needs attention" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Latest conclusions & accepted outcomes" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Metrics & freshness" })).toBeVisible()
  await expect(page.getByText("Alpha implementation", { exact: true })).toBeVisible()
  await expect(page.getByText("Beta implementation", { exact: true })).toBeVisible()
  await expect(page.getByText("Gamma implementation", { exact: true })).toBeVisible()
  const alphaRow = page.locator("article.factory-row").filter({ hasText: "Alpha implementation" })
  await expect(alphaRow).toContainText("Watcher · Reviewer")
  await expect(alphaRow).toContainText("group-ta…alpha")
  await expect(page.getByText("A current incident remains open.", { exact: true }).last()).toBeVisible()
  await expect(page.getByText("Typed owner adapter")).toBeVisible()
  await expect(page.getByText("Codex tasks").last()).toBeVisible()
  await expect(page.getByText("partial", { exact: true })).toBeVisible()
  await expect(page.getByText(/spend/i)).toHaveCount(0)

  await page.getByRole("link", { name: /API-equivalent estimate/ }).click()
  const metricInspector = page.getByRole("complementary", { name: "Factory source inspector" })
  await expect(metricInspector).toContainText("fixture/api-equivalent")
  await expect(metricInspector).toContainText("3 registered projects")
  await page.getByRole("button", { name: "Close inspector" }).click()

  const projectFilter = page.getByLabel("Project")
  await projectFilter.focus()
  await expect(projectFilter).toBeFocused()
  await projectFilter.selectOption("gamma")
  await expect(page.getByText("Gamma implementation", { exact: true })).toBeVisible()
  await expect(page.getByText("Alpha implementation", { exact: true })).toHaveCount(0)
  await expect(page.locator(".hidden-critical")).toContainText("1 critical hidden by filters")

  await projectFilter.selectOption("all")
  const betaRow = page.locator("article.factory-row").filter({ hasText: "Beta implementation" })
  await betaRow.getByRole("link", { name: "Inspect" }).click()
  const runInspector = page.getByRole("complementary", { name: "Factory source inspector" })
  await expect(runInspector).toBeVisible()
  await expect(runInspector).toContainText("group-target-beta")
  await expect(runInspector).toContainText("Role · Watcher")
  await expect(runInspector).toContainText("watcher-target-beta")
  await expect(runInspector).toContainText("Role · Reviewer")
  await expect(runInspector).toContainText("reviewer-target-beta")
  await expect(page).toHaveURL(/inspect=run%3Atarget-beta/)
  await page.getByRole("button", { name: "Close inspector" }).click()
  await expect(page.getByRole("complementary", { name: "Factory source inspector" })).toHaveCount(0)

  const results = await new AxeBuilder({ page }).analyze()
  expect(
    results.violations.filter(({ impact }) => impact === "serious" || impact === "critical"),
  ).toEqual([])
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test("catalog views preserve bounded discovery, failures, and archive consequences", async ({ page }) => {
  const alpha = project("alpha", "available")
  const beta = project("beta", "unavailable")
  const gamma = project("gamma", "available", true)
  await page.route("**/api/v1/projects?include_archived=true", (route) =>
    route.fulfill({ json: catalog([alpha, beta, gamma]) }),
  )
  await page.route("**/api/v1/projects?include_archived=false", (route) =>
    route.fulfill({ json: catalog([alpha, beta]) }),
  )
  await page.route("**/api/v1/task-integration", (route) =>
    route.fulfill({ json: integrationEnvelope }),
  )

  await page.goto("/admin")
  await expect(page.getByRole("heading", { name: "Admin", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  const integrationPanel = page.locator("section.integration-panel")
  await expect(integrationPanel.getByText("Connected", { exact: true })).toBeVisible()
  await expect(integrationPanel.getByText("codex-cli 0.145.0")).toBeVisible()
  await expect(
    integrationPanel.getByRole("listitem").filter({ hasText: "Raw Protocol" }),
  ).toContainText("Unavailable")
  await expect(integrationPanel.getByRole("alert")).toHaveCount(0)
  await expect(page.getByText(/dashboard (lets|allows|helps) you/i)).toHaveCount(0)
  await expect(page.getByRole("heading", { name: "Register a repository" })).toBeVisible()
  await expect(page.getByText("Registered project root is missing.")).toBeVisible()
  await expect(
    page.getByRole("group", { name: "Catalog status" }).getByText("3", { exact: true }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Archive from dashboard" }).first().click()
  const confirmation = page.getByRole("group", { name: "Archive Alpha" })
  await expect(confirmation).toContainText(
    "never deletes repository files, stops work, or changes the project",
  )
  await confirmation.getByRole("button", { name: "Cancel" }).click()

  const adminAxe = await new AxeBuilder({ page }).analyze()
  expect(
    adminAxe.violations.filter(({ impact }) => impact === "serious" || impact === "critical"),
  ).toEqual([])
  const adminDimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(adminDimensions.scrollWidth).toBeLessThanOrEqual(adminDimensions.clientWidth + 1)

  await page.goto("/projects")
  await expect(page.getByRole("heading", { name: "Projects", level: 1 })).toBeVisible()
  await expect(page.getByRole("link", { name: "Alpha", exact: true })).toBeVisible()
  await expect(page.getByRole("link", { name: "Beta", exact: true })).toBeVisible()
  await expect(page.getByText("Registered project root is missing.")).toBeVisible()
  await expect(page.getByText(/cccccccccc/)).toBeVisible()

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test("live project, run, supervisor, and task drill-downs preserve mission boundaries", async ({ page }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const predecessor = "bc955bd48e01db90aeb98fa27256546e2ce1eaf289fd6f630f36374d3c89d810"
  const returnPath = "/?project=software-factory&time=24h&posture=all&severity=all"
  const projectFloor = makeFactoryFloorEnvelope()
  projectFloor.data.projects = [{ id: "software-factory", label: "Software Factory" }]
  projectFloor.data.rows = [{
    ...projectFloor.data.rows[0],
    id: `run:${target}`,
    project: { status: "task-only", project_id: "software-factory", label: "Software Factory", reason: "Exact target task binding." },
    implementation: { ...projectFloor.data.rows[0].implementation, task_id: target, name: "sf-dashboard-plan" },
    supervision: { ...projectFloor.data.rows[0].supervision, run_id: target, target_thread_id: target },
    detail: { ...projectFloor.data.rows[0].detail, id: target, kind: "run", route: `/?inspect=run:${target}` },
  }]
  projectFloor.data.rows_truncated = false
  await page.route("**/api/v1/factory-floor", (route) => route.fulfill({ json: projectFloor }))

  await page.goto(`/projects/software-factory?return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByRole("heading", { name: "Projects", level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Current work" })).toBeVisible()
  await expect(page.getByRole("link", { name: /sf-dashboard-plan/i })).toBeVisible()
  await expect(page.getByRole("region", { name: "Project summary" })).not.toContainText("…")
  await expect(page.getByRole("link", { name: "Factory Floor" }).last()).toHaveAttribute("href", returnPath)
  await expect(page.locator("h1")).toHaveCount(1)

  await page.unroute("**/api/v1/factory-floor")

  await page.goto(`/runs/${target}?return=${encodeURIComponent(returnPath)}`)
  const eventPages = page.getByRole("navigation", { name: "Event pages" })
  await expect(eventPages.getByRole("button", { name: "Older" })).toBeEnabled()
  await expect(eventPages.getByRole("button", { name: "Newer" })).toBeDisabled()
  await eventPages.getByRole("button", { name: "Older" }).click()
  await expect(eventPages.getByRole("button", { name: "Newer" })).toBeEnabled()

  await page.goto(`/runs/${target}?mission=${predecessor}&return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByText("Historical mission", { exact: true })).toBeVisible()
  await expect(page.getByText(/Current topology, role tasks, automations, checks, and bindings are intentionally suppressed/)).toBeVisible()
  await expect(page.getByText("Suppressed at succession boundary", { exact: true })).toHaveCount(2)
  await expect(page.getByRole("heading", { name: "Roles & routes" })).toHaveCount(0)
  await expect(page.getByText("Tracker watcher - SF dashboard plan", { exact: true })).toHaveCount(0)
  await expect(page.getByText("No mission-isolated historical metric projection")).toBeVisible()

  await page.goto(`/runs/${target}/supervisor?mission=${predecessor}&return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByRole("heading", { name: "Supervisor", level: 1 })).toBeVisible()
  await expect(page.getByText("Historical mission", { exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Recent supervision activity" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Roles & routes" })).toHaveCount(0)

  const runAxe = await new AxeBuilder({ page }).analyze()
  expect(runAxe.violations.filter(({ impact }) => impact === "serious" || impact === "critical"))
    .toEqual([])
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)

  await page.goto(`/tasks/${target}?return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByRole("heading", { name: "Task", level: 1 })).toBeVisible()
  await expect(page.locator("main")).toContainText(/Task|Codex App Server|Loading/)
  await expect(page.getByText(/dashboard (lets|allows|helps) you/i)).toHaveCount(0)
})
