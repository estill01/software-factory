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
  await expect(page.getByText("Alpha implementation", { exact: true })).toBeVisible()
  await expect(page.getByText("Beta implementation", { exact: true })).toBeVisible()
  await expect(page.getByText("Gamma implementation", { exact: true })).toBeVisible()
  const alphaRow = page.locator("article.factory-row").filter({ hasText: "Alpha implementation" })
  await expect(alphaRow).toContainText("Watcher · Reviewer")
  await expect(alphaRow).toContainText("group-ta…alpha")
  await expect(alphaRow.getByRole("button", { name: "Check now" })).toBeEnabled()
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
      expires_at: "2026-08-11T03:00:00.000Z",
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
  await page.route("**/api/v1/operations/preview", async (route) => {
    const requestBody = route.request().postDataJSON()
    expect(requestBody).toEqual({
      operation_type: "factory.supervision-repair-mission-binding",
      target: { kind: "run", id: target, project_id: "software-factory" },
      input: {},
    })
    await route.fulfill({
      json: {
        data: { operation, preview_token: "p".repeat(32) },
        source: { kind: "administrative-operation", identity: operation.id, revision: "8".repeat(64) },
        observed_at: "2026-08-11T02:55:00.000Z",
        fingerprint: "8".repeat(64),
        coverage: { status: "partial", observed: ["operation-preview"], missing: ["owner-postcondition"] },
        limitations: ["Fixture stops before mutation."],
        error: null,
      },
    })
  })

  await page.goto(`/runs/${target}`)
  const repair = page.getByRole("button", { name: "Repair binding" })
  await expect(repair).toBeEnabled()
  await repair.click()
  const preview = page.getByRole("dialog")
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
      expires_at: "2026-08-11T04:20:00.000Z",
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
