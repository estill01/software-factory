import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

const catalogFingerprint = "a".repeat(64)

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
        supervision: { status: "unavailable", reason: "Available after Block 4." },
        codex_tasks: { status: "unavailable", reason: "Available after Block 5." },
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
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Factory Floor", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  await expect(page.getByRole("status", { name: /Local runtime online/ })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Implementation data unavailable" })).toBeVisible()

  await page.getByRole("link", { name: "Trackers", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Trackers", level: 1 })).toBeVisible()
  await expect(page.locator("h1")).toHaveCount(1)
  await expect(page.getByRole("heading", { name: "Tracker source unavailable" })).toBeVisible()
  await expect(page).toHaveURL(/\/trackers$/)

  const themeToggle = page.getByRole("button", { name: /Switch to (light|dark) mode/ })
  const initialTheme = await page.locator("html").getAttribute("data-theme")
  await themeToggle.click()
  await expect(page.locator("html")).toHaveAttribute(
    "data-theme",
    initialTheme === "dark" ? "light" : "dark",
  )
})

test("shell has no serious accessibility violations", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Factory Floor", level: 1 })).toBeVisible()
  const results = await new AxeBuilder({ page }).analyze()
  const material = results.violations.filter(({ impact }) =>
    impact === "serious" || impact === "critical",
  )
  expect(material).toEqual([])
})

test("maintained viewport has no horizontal page overflow", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Factory Floor", level: 1 })).toBeVisible()
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
  await page.goto("/")

  await expect(page.getByRole("status", { name: "Runtime unavailable" })).toBeVisible()
  await expect(page.getByText("Health check failed; readiness is unknown")).toBeVisible()
  await expect(page.getByText("Connected and locally constrained")).toHaveCount(0)
  const runtimeRow = page.getByText("Loopback runtime").locator("..").locator("..")
  await expect(runtimeRow.getByText("Ready", { exact: true })).toHaveCount(0)
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

  await page.goto("/admin")
  await expect(page.getByRole("heading", { name: "Admin", level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Register a repository" })).toBeVisible()
  await expect(page.getByText("Registered project root is missing.")).toBeVisible()
  await expect(page.getByText("3", { exact: true })).toBeVisible()
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

  await page.goto("/projects")
  await expect(page.getByRole("heading", { name: "Projects", level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Alpha" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Beta" })).toBeVisible()
  await expect(page.getByText("Registered project root is missing.")).toBeVisible()
  await expect(page.getByText("cccccccccc")).toBeVisible()

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})
