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

const operationFrameworkEnvelope = {
  data: {
    framework: {
      ephemeral: true,
      registered_operations: [],
      activity: [],
      restart_posture: "Reconstruct prior results from their canonical owners.",
    },
  },
  source: {
    kind: "administrative-operation",
    identity: "software-factory-dashboard/operations",
    revision: "2".repeat(64),
  },
  observed_at: "2026-08-09T10:00:00.000Z",
  fingerprint: "3".repeat(64),
  coverage: {
    status: "partial",
    observed: ["ephemeral-operation-state", "closed-operation-registry"],
    missing: ["prior-server-session-operation-state"],
  },
  limitations: ["Operation activity is process-local."],
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
  await expect(page.locator(".tracker-index-row").first()).toBeVisible()
  await expect(page.getByText("Tracker workspace unavailable")).toHaveCount(0)
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
  const alphaDisclosure = page.getByRole("button", { name: /Alpha implementation/ })
  await expect(alphaDisclosure).toBeVisible()
  await expect(page.getByRole("button", { name: /Beta implementation/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /Gamma implementation/ })).toBeVisible()
  await expect(page.getByRole("button", { name: "All: 3 returned, source coverage partial" })).toHaveAttribute("aria-pressed", "true")
  await expect(page.getByRole("button", { name: "Active / Running: 2 returned, source coverage partial" })).toBeVisible()
  const alphaRow = page.locator("article.operational-disclosure").filter({ has: alphaDisclosure })
  await expect(alphaRow).toContainText("Watcher · Reviewer")
  await expect(alphaRow).toContainText("group-ta…alpha")
  await expect(alphaRow).toContainText("26 Blocks")
  await expect(alphaRow).toContainText("Block 6 — Factory Floor composition")
  await expect(alphaDisclosure).toHaveAttribute("aria-expanded", "false")
  await alphaDisclosure.focus()
  await alphaDisclosure.press("Enter")
  await expect(alphaDisclosure).toHaveAttribute("aria-expanded", "true")
  await expect(alphaRow.getByRole("button", { name: "Check now" })).toBeEnabled()
  await expect(page.getByText("A current incident remains open.", { exact: true }).last()).toBeVisible()
  await expect(page.getByText("Typed owner adapter")).toBeVisible()
  await expect(page.getByText("Codex tasks").last()).toBeVisible()
  await expect(page.getByRole("link", { name: /Codex tasks partial/ })).toBeVisible()
  await expect(page.getByText(/spend/i)).toHaveCount(0)

  await page.getByRole("button", { name: "Attention: 1 returned, source coverage partial" }).click()
  await expect(page.getByRole("button", { name: /Alpha implementation/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /Beta implementation/ })).toHaveCount(0)
  await page.getByRole("button", { name: "All: 3 returned, source coverage partial" }).click()

  await page.getByRole("link", { name: /API-equivalent estimate/ }).click()
  const metricInspector = page.getByRole("complementary", { name: "Factory source inspector" })
  await expect(metricInspector).toContainText("fixture/api-equivalent")
  await expect(metricInspector).toContainText("3 registered projects")
  await page.getByRole("button", { name: "Close inspector" }).click()

  const projectFilter = page.getByLabel("Project", { exact: true })
  await projectFilter.focus()
  await expect(projectFilter).toBeFocused()
  await projectFilter.selectOption("gamma")
  await expect(page.getByRole("button", { name: /Gamma implementation/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /Alpha implementation/ })).toHaveCount(0)
  await expect(page.locator(".hidden-critical")).toContainText("1 critical hidden by filters")

  await projectFilter.selectOption("all")
  const betaDisclosure = page.getByRole("button", { name: /Beta implementation/ })
  const betaRow = page.locator("article.operational-disclosure").filter({ has: betaDisclosure })
  await betaDisclosure.click()
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

test("live metrics and report history remain source-backed and read-only", async ({ page }) => {
  await page.goto("/reports")

  await expect(page.getByRole("heading", { name: "Reports", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  await expect(page.getByRole("region", { name: "Delivery" })).toBeVisible()
  await expect(page.getByRole("region", { name: "Reliability" })).toBeVisible()
  await expect(page.getByRole("region", { name: "Review" })).toBeVisible()
  await expect(page.getByRole("region", { name: "Resources" })).toContainText(
    "API-equivalent estimate",
  )
  await expect(page.getByRole("region", { name: "Delivery" })).toContainText("Incomparable")
  await expect(page.getByRole("region", { name: "Metric contract and sources" })).toContainText(
    "Numeric aggregate withheld",
  )
  await expect(page.getByRole("region", { name: "Trend" })).toContainText(
    "Incompatible metrics were not combined",
  )
  await page.getByLabel("Run", { exact: true }).selectOption({ index: 1 })
  const trend = page.getByRole("region", { name: "Trend" })
  await expect(trend.getByRole("table", { name: "Exact accessible values and sources for the metric trend" })).toBeVisible()
  await expect(trend.getByRole("link", { name: /metric/ }).first()).toHaveAttribute(
    "href",
    /\/runs\/.+#current-metric$/,
  )
  const eventSource = trend.locator(".metric-trend-sources a").nth(1)
  await expect(eventSource).toHaveAttribute("href", /\/runs\/.+#EVT-/)
  const eventSourceHref = await eventSource.getAttribute("href")
  expect(eventSourceHref).not.toBeNull()
  await expect(page.getByRole("region", { name: "Metric contract and sources" })).toContainText(
    "Incident rate uses incident openings",
  )
  await expect(page.getByRole("region", { name: "Factory history" })).toContainText(
    "supervisor groups",
  )

  await page.goto(eventSourceHref!)
  await expect.poll(() => page.evaluate(() => {
    const recordId = decodeURIComponent(window.location.hash.slice(1))
    return recordId.length > 0 && document.getElementById(recordId) !== null
  })).toBe(true)
  await page.goto("/reports")

  await page.getByRole("button", { name: "Reports", exact: true }).click()
  const history = page.getByRole("region", { name: "History" })
  await expect(history).toBeVisible()
  await expect(history.getByText("invalid", { exact: true }).first()).toBeVisible()

  const invalidRow = history.locator("tbody tr").filter({ hasText: "invalid" }).first()
  await invalidRow.getByRole("button").click()
  const invalidDetail = page.getByRole("region", { name: "Detail" })
  await expect(invalidDetail.getByRole("alert")).toContainText("metadata-only")
  await expect(invalidDetail.getByRole("link", { name: "Open" })).toHaveCount(0)

  const verifiedRow = history.locator("tbody tr").filter({ hasText: "verified" }).first()
  await expect(verifiedRow).toBeVisible()
  await verifiedRow.getByRole("button").click()
  const detail = page.getByRole("region", { name: "Detail" })
  await expect(detail).toContainText("Source root")
  await expect(detail).toContainText("Manifest root")
  await expect(detail.getByRole("link", { name: "Open" })).toHaveAttribute(
    "href",
    /\/api\/v1\/reports\/.+\/artifacts\/report\.pdf$/,
  )
  await expect(page.getByRole("button", { name: /generate|adopt|accept/i })).toHaveCount(0)
  const markdownArtifact = detail.locator(".report-artifact-list > div").filter({ hasText: "report.md" })
  await markdownArtifact.getByRole("button", { name: "Preview" }).click()
  await expect(detail.locator(".safe-markdown")).toContainText(
    "Supervision weekly review",
    { timeout: 30_000 },
  )

  const results = await new AxeBuilder({ page }).analyze()
  expect(
    results.violations.filter(({ impact }) => impact === "serious" || impact === "critical"),
  ).toEqual([])
  const themeToggle = page.getByRole("button", { name: /Switch to (light|dark) mode/ })
  const initialTheme = await page.locator("html").getAttribute("data-theme")
  await themeToggle.click()
  await expect(page.locator("html")).toHaveAttribute(
    "data-theme",
    initialTheme === "dark" ? "light" : "dark",
  )
  await page.waitForTimeout(250)
  const alternateThemeResults = await new AxeBuilder({ page }).analyze()
  expect(
    alternateThemeResults.violations.filter(
      ({ impact }) => impact === "serious" || impact === "critical",
    ),
  ).toEqual([])

  await page.emulateMedia({ media: "print" })
  await expect(page.locator(".report-mode-toolbar")).toBeHidden()
  await expect(detail).toBeVisible()
  await page.emulateMedia({ media: "screen" })
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test("wholly unavailable metric projections never render as numeric zero", async ({ page }) => {
  const response = await page.request.get("/api/v1/metrics")
  const payload = await response.json()
  payload.data.per_run = payload.data.per_run.map((run: Record<string, unknown>) => ({
    ...run,
    status: "unavailable",
    metrics: null,
    error: {
      code: "metric_projection_failed",
      message: "Exact metric unavailable",
      retryable: false,
    },
  }))
  payload.data.aggregate = {
    ...payload.data.aggregate,
    status: "unavailable",
    available_run_count: 0,
    contract_count: 0,
    contracts: [],
    headline: null,
    api_equivalent_estimate: {
      ...payload.data.aggregate.api_equivalent_estimate,
      coverage_run_count: 0,
      totals: null,
    },
  }
  await page.route("**/api/v1/metrics", (route) => route.fulfill({ json: payload }))
  await page.goto("/reports")

  const delivery = page.getByRole("region", { name: "Delivery" })
  await expect(delivery).toContainText("Unavailable")
  await expect(delivery).not.toContainText("Recorded events 0")
  await expect(page.getByRole("region", { name: "Resources" })).not.toContainText("$0")
  await expect(page.getByRole("region", { name: "Trend" })).toContainText(
    "unavailable values were not rendered as zero",
  )
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
  await page.route("**/api/v1/operations", (route) =>
    route.fulfill({ json: operationFrameworkEnvelope }),
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
  const operationsPanel = page.getByRole("region", { name: "Operations" })
  await expect(operationsPanel).toContainText("0 available")
  await expect(operationsPanel).toContainText("No owner-backed administrative operations are currently available.")
  await expect(operationsPanel).toContainText("No operations requested in this server session.")
  await expect(operationsPanel.getByRole("button", { name: /execute|start|pause|stop|accept/i })).toHaveCount(0)
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
  test.setTimeout(180_000)
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
  projectFloor.data.rows[0].disagreements = ["Supervision binds project beta; task cwd binds project software-factory."]
  projectFloor.data.rows_truncated = false
  await page.route("**/api/v1/factory-floor", (route) => route.fulfill({ json: projectFloor }))
  await page.route("**/api/v1/runs", (route) => route.abort())

  await page.goto(`/projects/software-factory?return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByRole("heading", { name: "Projects", level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Current work" })).toBeVisible()
  await expect(page.getByRole("link", { name: /sf-dashboard-plan/i })).toBeVisible()
  const projectSummary = page.getByRole("region", { name: "Project summary" })
  await expect(projectSummary).toContainText("Runs≥0")
  await expect(projectSummary).toContainText("1 binding disagreement excluded")
  await expect(projectSummary).toContainText("Run association source unavailable")
  await expect(page.getByText(/disputed Factory Floor claims are not counted as exact/)).toBeVisible()
  await expect(page.getByRole("link", { name: "Factory Floor" }).last()).toHaveAttribute("href", returnPath)
  await expect(page.locator("h1")).toHaveCount(1)

  await page.unroute("**/api/v1/runs")
  await page.unroute("**/api/v1/factory-floor")

  await page.goto(`/runs/${target}?return=${encodeURIComponent(returnPath)}`)
  const checkNow = page.getByRole("button", { name: "Check now" })
  await expect(checkNow).toBeEnabled({ timeout: 60_000 })
  const lifecycleFailed = await page.locator(".workspace-identity-strip").getByText("failed", { exact: true }).count() > 0
  await checkNow.click()
  if (lifecycleFailed) {
    await expect(page.getByRole("alert")).toContainText("Immediate checks are unavailable while the run lifecycle is failed.")
  } else {
    const checkPreview = page.getByRole("dialog")
    await expect(checkPreview).toContainText(/one immediate mechanical check/i)
    await expect(checkPreview).toContainText("watcher-action")
    await checkPreview.getByRole("button", { name: "Close operation preview" }).click()
  }
  const checkpointReview = page.getByRole("button", { name: "Checkpoint review" })
  const metaReview = page.getByRole("button", { name: "Meta-review" })
  await expect(checkpointReview).toBeEnabled()
  await expect(metaReview).toBeEnabled()
  await expect(page.getByRole("button", { name: "Issue follow-up" })).toBeDisabled()
  await checkpointReview.click()
  const checkpointPreview = page.getByRole("dialog")
  await expect(checkpointPreview).toContainText(/one checkpoint review/i)
  await expect(checkpointPreview).toContainText("semantic-escalation")
  await checkpointPreview.getByRole("button", { name: "Close operation preview" }).click()
  await metaReview.click()
  const metaPreview = page.getByRole("dialog")
  await expect(metaPreview).toContainText(/one meta-review/i)
  await expect(metaPreview).toContainText("semantic-escalation")
  await metaPreview.getByRole("button", { name: "Close operation preview" }).click()
  await expect(page.getByText("2/2 schedules reconciled", { exact: true })).toBeVisible()
  const adjustSupervision = page.getByRole("button", { name: "Adjust supervision" })
  await expect(adjustSupervision).toBeEnabled()
  await adjustSupervision.click()
  const adjustDialog = page.getByRole("dialog", { name: "Adjust supervision" })
  await expect(adjustDialog.getByRole("checkbox", { name: /Gmail quiet minutes/ })).toBeDisabled()
  await adjustDialog.getByRole("checkbox", { name: /Routine minutes/ }).check()
  await adjustDialog.getByRole("spinbutton", { name: "New Routine minutes" }).fill("25")
  await adjustDialog.getByLabel("Reason").fill("Block 14 browser preview; do not execute.")
  await adjustDialog.getByRole("button", { name: "Preview" }).click()
  const adjustPreview = page.getByRole("dialog")
  await expect(adjustPreview).toContainText("Routine minutes: 20 → 25")
  await expect(adjustPreview).toContainText("8 adjustable fields")
  await expect(adjustPreview).toContainText("watcher")
  await expect(adjustPreview).toContainText("No automatic rollback")
  await adjustPreview.getByRole("button", { name: "Close operation preview" }).click()
  const eventPages = page.getByRole("navigation", { name: "Event pages" })
  await expect(eventPages.getByRole("button", { name: "Older" })).toBeEnabled({ timeout: 60_000 })
  await expect(eventPages.getByRole("button", { name: "Newer" })).toBeDisabled()
  await eventPages.getByRole("button", { name: "Older" }).click()
  await expect(eventPages.getByRole("button", { name: "Newer" })).toBeEnabled()

  await page.goto(`/runs/${target}?mission=${"9".repeat(64)}&return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByText("Requested mission is not present in this run's canonical history")).toBeVisible()
  await expect(page.getByText("Tracker watcher - SF dashboard plan", { exact: true })).toHaveCount(0)
  await expect(page.getByText("Action required", { exact: true })).toHaveCount(0)

  await page.goto(`/runs/${target}?mission=${predecessor}&return=${encodeURIComponent(returnPath)}`)
  await expect(page.getByText("Historical mission", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Check now" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Checkpoint review" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Meta-review" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Issue follow-up" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Adjust supervision" })).toHaveCount(0)
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

test("missing mission binding exposes only the source-derived repair preview", async ({ page, request }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const sourceClient = `client-${"z".repeat(300)}`
  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  runEnvelope.data.run.current_mission = null
  runEnvelope.data.run.project_binding = {
    status: "bound",
    project_id: "software-factory",
    evidence: [{ source_record: "policy", field: "project_root", value: "/fixture/software_factory" }],
    limitations: [],
  }
  const predecessor = runEnvelope.data.run.mission_segments.find(
    (segment: { posture: string }) => segment.posture === "predecessor",
  )?.mission_root
  expect(predecessor).toBeTruthy()
  const operation = {
    id: "op_e2e_binding_repair_preview",
    type: "factory.supervision-repair-mission-binding",
    target: { kind: "run", id: target, project_id: "software-factory" },
    state: "previewed",
    owner: "maintained reviewer plan + fix executor + supervision bind/policy owner",
    authority: ["operator confirmation requests review; independent reviewer verifies source authority"],
    preview: {
      effect: `Request independent review of one missing mission binding candidate for run ${target}.`,
      risk: "Only after independent authority verification may the maintained owner add one mission binding and next policy-history record; target and tracker identity must remain unchanged.",
      recipient: "019fe54d-acd4-7653-825e-4d710eaeae7b",
      semantic_changes: {
        status: "available",
        complete: true,
        rows: [
          {
            id: "mission-binding",
            subject: "Mission binding",
            kind: "added",
            before: { posture: "unavailable", value: null },
            after: { posture: "exact", value: "7".repeat(64) },
            owner: "maintained supervision bind/policy owner",
            source_identity: `supervision-policy:${target}`,
            source_revision: "8".repeat(64),
            currentness_fingerprint: "8".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "mission-target-task",
            subject: "Target task identity",
            kind: "preserved",
            before: { posture: "exact", value: target },
            after: { posture: "exact", value: target },
            owner: "maintained Codex task reader",
            source_identity: `codex-task:${target}`,
            source_revision: "8".repeat(64),
            currentness_fingerprint: "8".repeat(64),
            links: [{ label: "Target task", href: `/tasks/${target}` }],
          },
        ],
        limitations: ["Rows are owner-supplied from the exact preview snapshot and read-only."],
      },
      source_fingerprint: "8".repeat(64),
      source_evidence: {
        source_record: "EVT-000139",
        tracker_path: "docs/software-factory-operations-dashboard-implementation-tracker.md",
        mission_source_record: `codex:${target}:turn-source-001:item-source-001`,
        mission_source_sha256: "c".repeat(64),
        mission_source_envelope_sha256: "e".repeat(64),
        mission_source_part_types: ["text"],
        mission_source_client_id: sourceClient,
        mission_source_classification: "ordinary-user-message",
        mission_source_authority_status: "unverified-reviewer-verification-required",
        run_project_binding: { status: "bound", project_id: "software-factory" },
      },
      route_gate: {
        status: "allowed",
        target_thread: target,
        recipient: "019fe54d-acd4-7653-825e-4d710eaeae7b",
        purpose: "semantic-escalation",
        source_record: "EVT-000139",
        required_action: "Review one exact missing-mission repair.",
        action_hash: "9".repeat(64),
        policy_fingerprint: "a".repeat(64),
        binding_fingerprint: "b".repeat(64),
      },
      consequences: {
        ordinary: ["Starts one bounded reviewer turn for one exact missing mission binding."],
        failure: ["Healthy, stale, ambiguous, unsupported, or semantically different tuples send no request."],
      },
      confirmation: {
        class: "supervision-binding-repair",
        prompt: "Type REQUEST BINDING REVIEW to request review of this exact candidate. This does not attest source authority.",
        expected_value: "REQUEST BINDING REVIEW",
      },
      expected_postcondition: "One exact next policy-bind record adds only the source-derived mission binding while the live target, complete source item, run/project claim, tracker tuple, history, owner, and single-group identity remain current.",
      idempotency: "One consumed preview starts at most one reviewer turn.",
      limitations: ["Only a missing mission binding is supported."],
      expires_at: "2099-08-11T03:00:00.000Z",
    },
    history: [{ state: "previewed", observed_at: "2026-08-11T02:55:00.000Z" }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  await page.route(`**/api/v1/runs/${target}`, (route) =>
    route.fulfill({ json: runEnvelope }),
  )
  let previewRequests = 0
  await page.route("**/api/v1/operations/preview", async (route) => {
    previewRequests += 1
    const requestBody = route.request().postDataJSON()
    expect(requestBody).toEqual({
      operation_type: "factory.supervision-repair-mission-binding",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: {},
    })
    await route.fulfill({
      json: {
        data: {
          operation: {
            ...operation,
            preview: {
              ...operation.preview,
              expires_at: new Date(Date.now() + (previewRequests === 1 ? -1_000 : 60_000)).toISOString(),
            },
          },
          preview_token: `${previewRequests}`.repeat(32),
        },
        source: { kind: "administrative-operation", identity: operation.id, revision: "8".repeat(64) },
        observed_at: "2026-08-11T02:55:00.000Z",
        fingerprint: "8".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto(`/runs/${target}`)
  const repair = page.getByRole("button", { name: "Repair binding" })
  await expect(repair).toBeEnabled()
  await page.getByRole("button", { name: /Switch to (light|dark) mode/ }).click()
  await repair.click()
  const preview = page.getByRole("dialog")
  await expect(preview.getByText("Preview expired", { exact: true })).toBeVisible()
  await expect(preview.getByText("Comparison expired · preview again", { exact: true })).toBeVisible()
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  await expect(preview.getByLabel("Type REQUEST BINDING REVIEW")).toHaveCount(0)
  await preview.getByRole("button", { name: "Preview again" }).click()
  await expect(preview.getByText("Preview expired", { exact: true })).toHaveCount(0)
  await expect(preview.getByLabel("Type REQUEST BINDING REVIEW")).toBeVisible()
  expect(previewRequests).toBe(2)
  await expect(preview).toContainText("Missing mission binding only")
  await expect(preview).toContainText("authority unverified until independent reviewer proof")
  await expect(preview).toContainText("REQUEST BINDING REVIEW")
  await expect(preview).toContainText(`codex:${target}:turn-source-001:item-source-001`)
  await expect(preview).toContainText("c".repeat(64))
  await expect(preview).toContainText("e".repeat(64))
  await expect(preview).toContainText(sourceClient)
  await expect(preview).toContainText("ordinary user message")
  await expect(preview).toContainText("unverified reviewer verification required")
  await expect(preview).not.toContainText(/attested source|attest the displayed|operator attestation/i)
  await expect(preview).toContainText("Current path and content root")
  await expect(preview).toContainText("semantic-escalation")
  await expect(preview).toContainText("target and tracker identity must remain unchanged")
  const semanticChanges = preview.getByLabel("Owner supplied operation changes")
  await expect(semanticChanges).toContainText("Added")
  await expect(semanticChanges).toContainText("Preserved")
  await expect(semanticChanges).toContainText("maintained supervision bind/policy owner")
  await expect(semanticChanges.getByRole("link", { name: "Target task" })).toHaveAttribute("href", `/tasks/${target}`)
  await expect(semanticChanges.locator("button")).toHaveCount(0)
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  await expect(page.locator("h1")).toHaveCount(1)
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  await preview.getByRole("button", { name: "Close operation preview" }).click()
  await page.goto(`/runs/${target}?mission=${predecessor}`)
  await expect(page.getByText("Historical mission", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Repair binding" })).toHaveCount(0)
})

test("missing role binding exposes one exact prior-task repair preview", async ({ page, request }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const candidate = "019fe5aa-4d5f-75f0-a28d-425367111f3d"
  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  runEnvelope.data.run.project_binding = {
    status: "bound",
    project_id: "software-factory",
    evidence: [{ source_record: "policy", field: "project_root", value: "/fixture/software_factory" }],
    limitations: [],
  }
  runEnvelope.data.run.topology.roles = runEnvelope.data.run.topology.roles.map(
    (role: { role: string; binding_status: string; thread_id: string | null }) => ({
      ...role,
      thread_id: role.role === "notice_reviewer" ? null : role.thread_id,
      binding_status: role.role === "notice_reviewer" ? "missing-thread" : "bound",
    }),
  )
  if (!runEnvelope.data.run.topology.roles.some((role: { role: string }) => role.role === "notice_reviewer")) {
    const roleTemplate = runEnvelope.data.run.topology.roles[0]
    runEnvelope.data.run.topology.roles.push({
      ...roleTemplate,
      role: "notice_reviewer",
      label: "Incident outcome reviewer",
      thread_id: null,
      binding_status: "missing-thread",
      automation: null,
      last_activity: null,
    })
  }
  runEnvelope.data.run.topology.binding_integrity = "degraded"
  if (!runEnvelope.data.run.topology.anomalies.includes("notice reviewer task is missing")) {
    runEnvelope.data.run.topology.anomalies.push("notice reviewer task is missing")
  }
  const predecessor = runEnvelope.data.run.mission_segments.find(
    (segment: { posture: string }) => segment.posture === "predecessor",
  )?.mission_root
  expect(predecessor).toBeTruthy()
  const operation = {
    id: "op_e2e_role_binding_repair_preview",
    type: "factory.supervision-repair-role-task-binding",
    target: { kind: "run", id: target, project_id: "software-factory" },
    state: "previewed",
    owner: "maintained Codex task reader + supervision bind/policy and route-gate owners",
    authority: ["one exact prior canonical role-task binding"],
    preview: {
      effect: `Assign task ${candidate} to the missing Notice reviewer role for run ${target}.`,
      risk: "One canonical policy version may be created; no task or automation is created, resumed, messaged, or relabeled.",
      recipient: null,
      semantic_changes: {
        status: "available",
        complete: true,
        rows: [{
          id: "role-task-binding",
          subject: "Notice reviewer",
          kind: "added",
          before: { posture: "unavailable", value: null },
          after: { posture: "exact", value: candidate },
          owner: "maintained supervision bind/policy owner",
          source_identity: `supervision-policy:${target}`,
          source_revision: "4".repeat(64),
          currentness_fingerprint: "4".repeat(64),
          links: [{ label: "Role task", href: `/tasks/${candidate}` }],
        }],
        limitations: ["Rows are owner-supplied from the exact preview snapshot and read-only."],
      },
      source_fingerprint: "4".repeat(64),
      source_evidence: {
        role: "notice_reviewer",
        role_label: "Notice reviewer",
        current_task_id: null,
        expected_task_id: candidate,
        candidate_task_status: "idle",
        expected_model: { model: "gpt-5.6-sol", reasoning: "xhigh" },
        observed_model_and_effort: {
          model: "gpt-5.6-sol",
          reasoning: "xhigh",
          source_record_sha256: "5".repeat(64),
        },
        identity_source: "canonical-policy-history-exact-task-id",
        title_matching: false,
        route_purpose: "incident-review",
      },
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
        ordinary: ["Invokes the maintained bind owner once for the selected missing role."],
        failure: ["Ambiguous, stale, active, or unsupported tasks send no owner request."],
      },
      confirmation: {
        class: "supervision-role-binding-repair",
        prompt: "Type BIND ROLE to assign this exact prior task to the selected missing role.",
        expected_value: "BIND ROLE",
      },
      expected_postcondition: "The task, canonical role binding, and maintained purpose gate all agree.",
      idempotency: "One consumed preview invokes at most one exact bind.",
      limitations: ["No generic task creation or title matching."],
      expires_at: "2099-08-11T04:20:00.000Z",
    },
    history: [{ state: "previewed", observed_at: "2026-08-11T04:15:00.000Z" }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  await page.route(`**/api/v1/runs/${target}`, (route) =>
    route.fulfill({ json: runEnvelope }),
  )
  await page.route("**/api/v1/operations/preview", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      operation_type: "factory.supervision-repair-role-task-binding",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: { role: "notice_reviewer" },
    })
    await route.fulfill({
      json: {
        data: { operation, preview_token: "q".repeat(32) },
        source: { kind: "administrative-operation", identity: operation.id, revision: "4".repeat(64) },
        observed_at: "2026-08-11T04:15:00.000Z",
        fingerprint: "4".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.goto(`/runs/${target}`)
  await expect(page.getByRole("combobox", { name: "Role binding to repair" })).toHaveValue("notice_reviewer")
  await page.getByRole("button", { name: "Repair role" }).click()
  const preview = page.getByRole("dialog")
  await expect(preview).toContainText("Notice reviewer")
  await expect(preview).toContainText(candidate)
  await expect(preview).toContainText("idle")
  await expect(preview).toContainText("Required role model")
  await expect(preview).toContainText("Task-observed model")
  await expect(preview).toContainText("gpt-5.6-sol · xhigh")
  await expect(preview).toContainText("incident-review")
  await expect(preview).toContainText("no create, resume, turn, or relabel")
  await expect(preview.getByLabel("Owner supplied operation changes")).toContainText("Added")
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  await expect(page.locator("h1")).toHaveCount(1)
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  await preview.getByRole("button", { name: "Close operation preview" }).click()
  await page.goto(`/runs/${target}?mission=${predecessor}`)
  await expect(page.getByRole("button", { name: "Repair role" })).toHaveCount(0)
})

test("automation mismatch exposes one bounded dual-owner repair preview", async ({ page, request }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  runEnvelope.data.run.project_binding = {
    status: "bound",
    project_id: "software-factory",
    evidence: [{ source_record: "policy", field: "project_root", value: "/fixture/software_factory" }],
    limitations: [],
  }
  const watcher = runEnvelope.data.run.policy.automation_reconciliation.find(
    (row: { role: string }) => row.role === "watcher",
  )
  expect(watcher).toBeTruthy()
  Object.assign(watcher, {
    actual_automation_id: watcher.automation_id,
    actual_rrule: "RRULE:FREQ=MINUTELY;INTERVAL=45",
    actual_target_thread_id: "wrong-watcher-task",
    owner_status: "PAUSED",
    purpose: "watcher-action",
    timezone: "not-applicable-to-interval-schedule",
    actual_timezone: "not-applicable-to-interval-schedule",
    duplicate_coverage: "exact",
    active_target_owner_ids: [],
    state: "partial",
    repairable: true,
    reason: "Policy cadence and actual automation state do not fully agree.",
  })
  const predecessor = runEnvelope.data.run.mission_segments.find(
    (segment: { posture: string }) => segment.posture === "predecessor",
  )?.mission_root
  expect(predecessor).toBeTruthy()
  const operation = {
    id: "op_e2e_automation_binding_repair_preview",
    type: "factory.supervision-repair-automation-binding",
    target: { kind: "run", id: target, project_id: "software-factory" },
    state: "previewed",
    owner: "Codex automation owner + maintained supervision policy/bind and route-gate owners",
    authority: ["one exact named automation and canonical role claim"],
    preview: {
      effect: `Repair Routine watcher automation ${watcher.automation_id} for run ${target}.`,
      risk: "One existing automation may change; the canonical policy must remain byte-identical.",
      recipient: "fix-executor-task",
      semantic_changes: {
        status: "available",
        complete: true,
        rows: [
          {
            id: "automation-owner-status",
            subject: "Automation enabled state",
            kind: "changed",
            before: { posture: "exact", value: "PAUSED" },
            after: { posture: "exact", value: "ACTIVE" },
            owner: "maintained Codex automation owner",
            source_identity: `automation:${watcher.automation_id}`,
            source_revision: "a".repeat(64),
            currentness_fingerprint: "a".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "automation-policy-binding",
            subject: "Canonical policy role binding",
            kind: "preserved",
            before: { posture: "exact", value: "c".repeat(64) },
            after: { posture: "exact", value: "c".repeat(64) },
            owner: "maintained supervision policy/bind owner",
            source_identity: `supervision-policy:${target}`,
            source_revision: "c".repeat(64),
            currentness_fingerprint: "a".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
        ],
        limitations: ["Rows are owner-supplied from the exact preview snapshot and read-only."],
      },
      source_fingerprint: "a".repeat(64),
      source_evidence: {
        role: "watcher",
        role_label: "Routine watcher",
        purpose: "watcher-action",
        mismatches: ["enabled state differs", "role target differs", "schedule differs"],
        current_automation: {
          id: watcher.automation_id,
          owner_status: "PAUSED",
          target_thread_id: "wrong-watcher-task",
          rrule: "RRULE:FREQ=MINUTELY;INTERVAL=45",
        },
        expected_automation: {
          id: watcher.automation_id,
          owner_status: "ACTIVE",
          target_thread_id: watcher.target_thread_id,
          rrule: watcher.expected_rrule,
          timezone: "not-applicable-to-interval-schedule",
        },
      },
      route_gate: {
        status: "allowed",
        target_thread: target,
        recipient: "fix-executor-task",
        purpose: "fix-execution",
        source_record: "EVT-000020",
        required_action: "Repair one exact watcher automation binding.",
        action_hash: "b".repeat(64),
        policy_fingerprint: "c".repeat(64),
        binding_fingerprint: "d".repeat(64),
      },
      consequences: {
        ordinary: ["The automation owner may update only enabled state, schedule, or target."],
        failure: ["Partial owner state remains visible without automatic retry."],
      },
      confirmation: {
        class: "automation-binding-repair",
        prompt: "Type REPAIR AUTOMATION to request this exact named automation repair.",
        expected_value: "REPAIR AUTOMATION",
      },
      expected_postcondition: "The named automation and same canonical policy claim both agree.",
      idempotency: "One consumed preview starts at most one fix-executor turn.",
      limitations: ["No direct TOML or policy writes."],
      expires_at: "2099-08-11T09:30:00.000Z",
    },
    history: [{ state: "previewed", observed_at: "2026-08-11T09:25:00.000Z" }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  await page.route(`**/api/v1/runs/${target}`, (route) => route.fulfill({ json: runEnvelope }))
  await page.route("**/api/v1/operations/preview", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      operation_type: "factory.supervision-repair-automation-binding",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: { role: "watcher" },
    })
    await route.fulfill({
      json: {
        data: { operation, preview_token: "r".repeat(32) },
        source: { kind: "administrative-operation", identity: operation.id, revision: "a".repeat(64) },
        observed_at: "2026-08-11T09:25:00.000Z",
        fingerprint: "a".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.goto(`/runs/${target}`)
  await expect(page.getByRole("combobox", { name: "Automation binding to repair" })).toHaveValue("watcher")
  await page.getByRole("button", { name: "Repair automation" }).click()
  const preview = page.getByRole("dialog")
  await expect(preview).toContainText("Routine watcher · watcher-action")
  await expect(preview).toContainText("wrong-watcher-task")
  await expect(preview).toContainText("INTERVAL=45")
  await expect(preview).toContainText("INTERVAL=20")
  await expect(preview).toContainText("exact · 0 active owners on target")
  await expect(preview).toContainText("not-applicable-to-interval-schedule → not-applicable-to-interval-schedule")
  await expect(preview).toContainText("Named automation + canonical policy binding")
  await expect(preview).toContainText("No automatic retry or rollback")
  await expect(preview).toContainText("REPAIR AUTOMATION")
  const semanticChanges = preview.getByLabel("Owner supplied operation changes")
  await expect(semanticChanges).toContainText("Changed")
  await expect(semanticChanges).toContainText("Preserved")
  await expect(semanticChanges).toContainText("maintained Codex automation owner")
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(
    accessibility.violations.filter(({ impact }) => (
      impact === "serious" || impact === "critical"
    )),
  ).toEqual([])
  await expect(page.locator("h1")).toHaveCount(1)
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  await preview.getByRole("button", { name: "Close operation preview" }).click()
  await page.goto(`/runs/${target}?mission=${predecessor}`)
  await expect(page.getByRole("button", { name: "Repair automation" })).toHaveCount(0)
})

test("semantic pause previews both owners and keeps resume lifecycle-gated", async ({ page, request }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  runEnvelope.data.run.project_binding = {
    status: "bound",
    project_id: "software-factory",
    evidence: [{ source_record: "policy", field: "project_root", value: "/fixture/software_factory" }],
    limitations: [],
  }
  runEnvelope.data.run.lifecycle = { status: null, record: null }
  const represented = runEnvelope.data.run.policy.automation_reconciliation.filter(
    (row: { role: string }) => row.role === "watcher" || row.role === "reviewer",
  )
  expect(represented).toHaveLength(2)
  for (const row of represented) {
    row.owner_status = "ACTIVE"
    row.state = "reconciled"
  }
  const predecessor = runEnvelope.data.run.mission_segments.find(
    (segment: { posture: string }) => segment.posture === "predecessor",
  )?.mission_root
  expect(predecessor).toBeTruthy()
  const operation = {
    id: "op_e2e_supervision_pause_preview",
    type: "factory.supervision-pause",
    target: { kind: "run", id: target, project_id: "software-factory" },
    state: "previewed",
    owner: "maintained supervision lifecycle record/gate owner + exact Codex automation owner",
    authority: ["one exact selected supervision group"],
    preview: {
      effect: `Pause supervision group ${target} and 2 exact bound automations.`,
      risk: "Monitoring stops only after both maintained owners agree; partial state remains visible.",
      recipient: "fix-executor-task",
      semantic_changes: {
        status: "available",
        complete: true,
        rows: [
          {
            id: "supervision-lifecycle",
            subject: "Supervision lifecycle",
            kind: "added",
            before: { posture: "unavailable", value: null },
            after: { posture: "exact", value: "paused" },
            owner: "maintained supervision lifecycle record and gate owner",
            source_identity: `supervision-lifecycle:${target}`,
            source_revision: "a".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "supervision-automation-watcher",
            subject: "Routine watcher automation",
            kind: "changed",
            before: { posture: "exact", value: "ACTIVE" },
            after: { posture: "exact", value: "PAUSED" },
            owner: "maintained Codex automation owner",
            source_identity: "automation:watcher-automation",
            source_revision: "c".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "supervision-target-task-state",
            subject: "Implementation task state",
            kind: "preserved",
            before: { posture: "exact", value: "active" },
            after: { posture: "exact", value: "active" },
            owner: "maintained Codex task reader",
            source_identity: `codex-task:${target}`,
            source_revision: "d".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Target task", href: `/tasks/${target}` }],
          },
        ],
        limitations: ["Rows are source-backed and read-only."],
      },
      source_fingerprint: "b".repeat(64),
      source_evidence: {
        group_id: target,
        prior_lifecycle: null,
        automation_ids: ["watcher-automation", "reviewer-automation"],
      },
      route_gate: {
        status: "allowed",
        target_thread: target,
        recipient: "fix-executor-task",
        purpose: "fix-execution",
        source_record: "EVT-000021",
        required_action: "Request one exact semantic supervision pause.",
        action_hash: "e".repeat(64),
        policy_fingerprint: "f".repeat(64),
        binding_fingerprint: "1".repeat(64),
      },
      consequences: {
        ordinary: ["The lifecycle and exact automation owners may record and pause this group."],
        failure: ["Partial owner state remains visible without automatic retry."],
      },
      confirmation: {
        class: "supervision-pause",
        prompt: "Type PAUSE SUPERVISION to request this exact group pause.",
        expected_value: "PAUSE SUPERVISION",
      },
      expected_postcondition: "The canonical paused lifecycle and every exact bound automation agree.",
      idempotency: "One consumed preview starts at most one fix-executor turn.",
      limitations: ["Turn interrupt and semantic resume remain separate."],
      expires_at: "2099-08-11T09:30:00.000Z",
    },
    history: [{ state: "previewed", observed_at: "2026-08-11T09:25:00.000Z" }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  await page.route(`**/api/v1/runs/${target}`, (route) => route.fulfill({ json: runEnvelope }))
  await page.route("**/api/v1/operations/preview", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      operation_type: "factory.supervision-pause",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: {},
    })
    await route.fulfill({
      json: {
        data: { operation, preview_token: "s".repeat(32) },
        source: { kind: "administrative-operation", identity: operation.id, revision: "b".repeat(64) },
        observed_at: "2026-08-11T09:25:00.000Z",
        fingerprint: "b".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.goto(`/runs/${target}`)
  await expect(page.getByRole("button", { name: "Pause" })).toBeEnabled()
  const resume = page.getByRole("button", { name: "Resume" })
  await expect(resume).toBeDisabled()
  await expect(resume).toHaveAttribute(
    "title",
    "Resume is available only for a canonical paused lifecycle.",
  )
  await page.getByRole("button", { name: "Pause" }).click()
  const preview = page.getByRole("dialog")
  await expect(preview).toContainText("Canonical paused lifecycle + every exact bound automation PAUSED")
  await expect(preview).toContainText("Implementation task and turn state")
  await expect(preview).toContainText("Partial owner state stays visible")
  await expect(preview).toContainText("PAUSE SUPERVISION")
  const semanticChanges = preview.getByLabel("Owner supplied operation changes")
  await expect(semanticChanges).toContainText("Supervision lifecycle")
  await expect(semanticChanges).toContainText("Routine watcher automation")
  await expect(semanticChanges).toContainText("Implementation task state")
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(
    accessibility.violations.filter(({ impact }) => (
      impact === "serious" || impact === "critical"
    )),
  ).toEqual([])
  await expect(page.locator("h1")).toHaveCount(1)
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  await preview.getByRole("button", { name: "Close operation preview" }).click()
  await page.goto(`/runs/${target}?mission=${predecessor}`)
  await expect(page.getByRole("button", { name: "Pause" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Resume" })).toHaveCount(0)
})

test("semantic resume previews exact owners without resuming the implementation task", async ({ page, request }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  runEnvelope.data.run.project_binding = {
    status: "bound",
    project_id: "software-factory",
    evidence: [{ source_record: "policy", field: "project_root", value: "/fixture/software_factory" }],
    limitations: [],
  }
  runEnvelope.data.run.lifecycle = {
    status: "paused",
    record: {
      record_id: "EVT-PAUSE-001",
      timestamp: "2026-08-11T09:00:00Z",
      kind: "lifecycle",
      status: "paused",
      severity: "info",
      category: "supervision-pause",
      summary: "Paused exact supervision group.",
    },
  }
  const represented = runEnvelope.data.run.policy.automation_reconciliation.filter(
    (row: { role: string }) => row.role === "watcher" || row.role === "reviewer",
  )
  expect(represented).toHaveLength(2)
  represented[0].owner_status = "PAUSED"
  represented[0].state = "partial"
  represented[1].owner_status = "ACTIVE"
  represented[1].state = "partial"
  const predecessor = runEnvelope.data.run.mission_segments.find(
    (segment: { posture: string }) => segment.posture === "predecessor",
  )?.mission_root
  expect(predecessor).toBeTruthy()
  const operation = {
    id: "op_e2e_supervision_resume_preview",
    type: "factory.supervision-resume",
    target: { kind: "run", id: target, project_id: "software-factory" },
    state: "previewed",
    owner: "maintained canonical supervision-resume lifecycle owner + exact Codex automation owner",
    authority: ["one exact canonically paused supervision group"],
    preview: {
      effect: `Resume supervision group group-${"a".repeat(64)} with 2 exact bound automations.`,
      risk: "Monitoring is current only after every exact automation owner and the canonical resume lifecycle agree; task and turn state remains unchanged.",
      recipient: "fix-executor-task",
      semantic_changes: {
        status: "available",
        complete: true,
        rows: [
          {
            id: "supervision-resume-lifecycle",
            subject: "Supervision lifecycle",
            kind: "changed",
            before: { posture: "exact", value: "paused" },
            after: { posture: "exact", value: "resumed" },
            owner: "maintained canonical supervision-resume lifecycle owner",
            source_identity: `supervision-lifecycle:${target}`,
            source_revision: "a".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "supervision-resume-automation-watcher",
            subject: "Routine watcher automation",
            kind: "changed",
            before: { posture: "exact", value: "PAUSED" },
            after: { posture: "exact", value: "ACTIVE" },
            owner: "maintained Codex automation owner",
            source_identity: "automation:watcher-automation",
            source_revision: "c".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "supervision-resume-automation-reviewer",
            subject: "Effectiveness reviewer automation",
            kind: "preserved",
            before: { posture: "exact", value: "ACTIVE" },
            after: { posture: "exact", value: "ACTIVE" },
            owner: "maintained Codex automation owner",
            source_identity: "automation:reviewer-automation",
            source_revision: "d".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "supervision-resume-target-task-state",
            subject: "Implementation task state",
            kind: "preserved",
            before: { posture: "exact", value: "active" },
            after: { posture: "exact", value: "active" },
            owner: "maintained Codex task reader",
            source_identity: `codex-task:${target}`,
            source_revision: "e".repeat(64),
            currentness_fingerprint: "b".repeat(64),
            links: [{ label: "Target task", href: `/tasks/${target}` }],
          },
        ],
        limitations: ["Rows are source-backed and read-only."],
      },
      source_fingerprint: "b".repeat(64),
      source_evidence: {
        group_id: `group-${"a".repeat(64)}`,
        pause_record: "EVT-PAUSE-001",
        source_record: "EVT-CHECK-002",
        state_fingerprint: "state-resume-001",
        eligibility_root: "f".repeat(64),
        automation_ids: ["watcher-automation", "reviewer-automation"],
      },
      route_gate: {
        status: "allowed",
        target_thread: target,
        recipient: "fix-executor-task",
        purpose: "fix-execution",
        source_record: "EVT-CHECK-002",
        required_action: "Resume exact supervision target through maintained owners.",
        action_hash: "1".repeat(64),
        policy_fingerprint: "2".repeat(64),
        binding_fingerprint: "3".repeat(64),
      },
      consequences: {
        ordinary: ["Only the exact named paused automation owners may be activated, then one canonical resume may be finalized."],
        failure: ["Partial owner state remains visible without automatic retry."],
      },
      confirmation: {
        class: "supervision-resume",
        prompt: "Type RESUME SUPERVISION to request this exact group resume.",
        expected_value: "RESUME SUPERVISION",
      },
      expected_postcondition: "Every exact named automation ACTIVE + canonical supervision-resume lifecycle; implementation task state unchanged.",
      idempotency: "One consumed preview starts at most one fix-executor turn.",
      limitations: ["App Server task and turn resume remain separate."],
      expires_at: "2099-08-11T09:30:00.000Z",
    },
    history: [{ state: "previewed", observed_at: "2026-08-11T09:25:00.000Z" }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  await page.route(`**/api/v1/runs/${target}`, (route) => route.fulfill({ json: runEnvelope }))
  await page.route("**/api/v1/operations/preview", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      operation_type: "factory.supervision-resume",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: {},
    })
    await route.fulfill({
      json: {
        data: { operation, preview_token: "r".repeat(32) },
        source: { kind: "administrative-operation", identity: operation.id, revision: "b".repeat(64) },
        observed_at: "2026-08-11T09:25:00.000Z",
        fingerprint: "b".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.goto(`/runs/${target}`)
  await expect(page.getByRole("button", { name: "Finish resume" })).toBeEnabled()
  await expect(page.getByRole("button", { name: "Finish pause" })).toBeEnabled()
  await page.getByRole("button", { name: "Finish resume" }).click()
  const preview = page.getByRole("dialog")
  await expect(preview).toContainText("Every exact named automation ACTIVE + canonical supervision-resume lifecycle")
  await expect(preview).toContainText("Implementation task state")
  await expect(preview).toContainText("Partial owner state stays visible")
  await expect(preview).toContainText("RESUME SUPERVISION")
  const semanticChanges = preview.getByLabel("Owner supplied operation changes")
  await expect(semanticChanges.getByRole("row", { name: /Supervision lifecycle.*paused.*resumed/ })).toBeVisible()
  await expect(semanticChanges.getByRole("row", { name: /Routine watcher automation.*PAUSED.*ACTIVE/ })).toBeVisible()
  await expect(semanticChanges).toContainText("maintained canonical supervision-resume lifecycle owner")
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(
    accessibility.violations.filter(({ impact }) => (
      impact === "serious" || impact === "critical"
    )),
  ).toEqual([])
  await expect(page.locator("h1")).toHaveCount(1)
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  await preview.getByRole("button", { name: "Close operation preview" }).click()

  runEnvelope.data.run.lifecycle.status = "resumed"
  runEnvelope.data.run.lifecycle.record.status = "resumed"
  runEnvelope.data.run.lifecycle.record.category = "supervision-resume"
  represented.forEach((row: { owner_status: string; state: string; duplicate_coverage: string }) => {
    row.owner_status = "ACTIVE"
    row.state = "reconciled"
    row.duplicate_coverage = "exact"
  })
  represented[0].state = "unavailable"
  represented[0].duplicate_coverage = "unavailable"
  await page.reload()
  await expect(page.getByRole("button", { name: "Running" })).toHaveCount(0)
  const incomplete = page.getByRole("button", { name: "Resume incomplete" })
  await expect(incomplete).toBeDisabled()
  await expect(incomplete).toHaveAttribute(
    "title",
    "Canonical resume exists, but exact active automation-owner coverage is unavailable or incomplete.",
  )

  await page.goto(`/runs/${target}?mission=${predecessor}`)
  await expect(page.getByRole("button", { name: "Finish resume" })).toHaveCount(0)
  await expect(page.getByText("RESUME SUPERVISION", { exact: true })).toHaveCount(0)
})

test("same-target succession preserves history and stops at pending first-work activation", async ({ page, request }) => {
  const target = "019fe547-e054-7ca0-9940-ec4aa146df78"
  const runResponse = await request.get(`/api/v1/runs/${target}`)
  expect(runResponse.ok()).toBeTruthy()
  const runEnvelope = await runResponse.json()
  runEnvelope.data.run.project_binding = {
    status: "bound",
    project_id: "software-factory",
    evidence: [{ source_record: "policy", field: "project_root", value: "/fixture/software_factory" }],
    limitations: [],
  }
  const predecessor = runEnvelope.data.run.current_mission?.root ?? "a".repeat(64)
  runEnvelope.data.run.current_mission = {
    root: predecessor,
    source_record: "direct-user-predecessor",
    policy_sha256: "b".repeat(64),
  }
  const historicalRoot = runEnvelope.data.run.mission_segments.find(
    (segment: { posture: string }) => segment.posture === "predecessor",
  )?.mission_root
  expect(historicalRoot).toBeTruthy()
  const successor = "c".repeat(64)
  const sourceRecord = `codex:${target}:turn-source-002:item-source-002`
  const operation = {
    id: "op_e2e_mission_successor_preview",
    type: "factory.supervision-mission-successor",
    target: { kind: "run", id: target, project_id: "software-factory" },
    state: "previewed",
    owner: "independent reviewer + maintained fix executor + supervision mission-successor/policy/activation owner",
    authority: [
      "explicit operator confirmation to request one bounded review, not mission authority",
      "independent reviewer verification of direct authority and material difference",
    ],
    preview: {
      effect: `Request independent review of one same-target successor mission for run ${target}.`,
      risk: "Only the maintained owner may replace the active binding and preserve predecessor history.",
      recipient: "reviewer-task",
      semantic_changes: {
        status: "available",
        complete: true,
        rows: [
          {
            id: "mission-successor-binding",
            subject: "Active mission binding",
            kind: "changed",
            before: { posture: "exact", value: predecessor },
            after: { posture: "exact", value: successor },
            owner: "maintained supervision mission-successor owner",
            source_identity: `supervision-policy:${target}`,
            source_revision: "b".repeat(64),
            currentness_fingerprint: "d".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "mission-successor-predecessor-history",
            subject: "Predecessor mission segment",
            kind: "preserved",
            before: { posture: "exact", value: predecessor },
            after: { posture: "exact", value: predecessor },
            owner: "maintained policy-history and mission-scoped event projection",
            source_identity: `supervision-mission:${predecessor}`,
            source_revision: "e".repeat(64),
            currentness_fingerprint: "d".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "mission-successor-first-work",
            subject: "Successor first eligible work",
            kind: "added",
            before: { posture: "unavailable", value: null },
            after: { posture: "exact", value: "Block 0 capability review" },
            owner: "maintained same-target mission-activation owner",
            source_identity: `supervision-source:${sourceRecord}`,
            source_revision: "f".repeat(64),
            currentness_fingerprint: "d".repeat(64),
            links: [{ label: "Run", href: `/runs/${target}` }],
          },
          {
            id: "mission-successor-target-task",
            subject: "Target task identity",
            kind: "preserved",
            before: { posture: "exact", value: target },
            after: { posture: "exact", value: target },
            owner: "maintained Codex task reader",
            source_identity: `codex-task:${target}`,
            source_revision: "1".repeat(64),
            currentness_fingerprint: "d".repeat(64),
            links: [{ label: "Target task", href: `/tasks/${target}` }],
          },
        ],
        limitations: ["Rows are source-backed and read-only."],
      },
      source_fingerprint: "d".repeat(64),
      source_evidence: {
        predecessor_mission_root: predecessor,
        successor_mission_root: successor,
        mission_source_record: sourceRecord,
        source_authority_status: "unverified-reviewer-verification-required",
        material_difference_status: "unverified-reviewer-verification-required",
        first_eligible_work: "Block 0 capability review",
      },
      route_gate: {
        status: "allowed",
        target_thread: target,
        recipient: "reviewer-task",
        purpose: "semantic-escalation",
        source_record: "EVT-CURRENT-SOURCE",
        required_action: "Review one same-target successor mission.",
        action_hash: "2".repeat(64),
        policy_fingerprint: "3".repeat(64),
        binding_fingerprint: "4".repeat(64),
      },
      consequences: {
        ordinary: ["One independent review may lead to one successor policy version and pending activation."],
        failure: ["No bind overwrite, retry, rollback, or task creation."],
      },
      confirmation: {
        class: "supervision-mission-successor",
        prompt: "Type BEGIN SUCCESSOR MISSION to request independent review of this exact candidate. This does not attest authority.",
        expected_value: "BEGIN SUCCESSOR MISSION",
      },
      expected_postcondition: "One reviewed direct mission is active on the same target; predecessor history is preserved and first-work activation remains pending.",
      idempotency: "One consumed preview starts at most one reviewer turn.",
      limitations: [
        "Operator confirmation does not prove direct mission authority.",
        "The applied boundary does not create a task or claim first work began.",
      ],
      expires_at: "2099-08-12T09:30:00.000Z",
    },
    history: [{ state: "previewed", observed_at: "2026-08-12T09:25:00.000Z" }],
    request_evidence: null,
    verification_evidence: null,
    links: [],
    failure: null,
  }
  await page.route(`**/api/v1/runs/${target}`, (route) => route.fulfill({ json: runEnvelope }))
  await page.route("**/api/v1/operations/preview", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      operation_type: "factory.supervision-mission-successor",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: {
        mission_source_record: sourceRecord,
        predecessor_disposition: "superseded",
        first_eligible_work: "Block 0 capability review",
        reason: "The direct user requested a materially different mission.",
      },
    })
    await route.fulfill({
      json: {
        data: { operation, preview_token: "m".repeat(32) },
        source: { kind: "administrative-operation", identity: operation.id, revision: "d".repeat(64) },
        observed_at: "2026-08-12T09:25:00.000Z",
        fingerprint: "d".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.goto(`/runs/${target}`)
  await expect(page.getByRole("button", { name: "Successor mission" })).toBeEnabled()
  await page.getByRole("button", { name: "Successor mission" }).click()
  const inputDialog = page.getByRole("dialog", { name: "Successor mission" })
  await inputDialog.getByLabel("Direct mission source record").fill(sourceRecord)
  await inputDialog.getByLabel("Predecessor disposition").selectOption("superseded")
  await inputDialog.getByLabel("First eligible work").fill("Block 0 capability review")
  await inputDialog.getByLabel("Reason").fill("The direct user requested a materially different mission.")
  await inputDialog.getByRole("button", { name: "Preview" }).click()

  const preview = page.getByRole("dialog")
  await expect(preview).toContainText("exact bytes and direct authority require independent review")
  await expect(preview).toContainText("pending activation, not proof of work-start")
  await expect(preview).toContainText("Bind overwrite · successor task")
  await expect(preview).toContainText("BEGIN SUCCESSOR MISSION")
  const semanticChanges = preview.getByLabel("Owner supplied operation changes")
  await expect(semanticChanges.getByRole("row", { name: /Active mission binding/ })).toContainText(predecessor.slice(0, 12))
  await expect(semanticChanges).toContainText("Predecessor mission segment")
  await expect(semanticChanges).toContainText("Block 0 capability review")
  await expect(semanticChanges).toContainText("maintained same-target mission-activation owner")
  await expect(preview.getByRole("button", { name: "Request operation" })).toBeDisabled()
  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(
    accessibility.violations.filter(({ impact }) => impact === "serious" || impact === "critical"),
  ).toEqual([])
  await expect(page.locator("h1")).toHaveCount(1)
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
  await preview.getByRole("button", { name: "Close operation preview" }).click()
  await page.goto(`/runs/${target}?mission=${historicalRoot}`)
  await expect(page.getByRole("button", { name: "Successor mission" })).toHaveCount(0)
})
