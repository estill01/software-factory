import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

test("factory shell exposes honest state and working navigation", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: /Know what is moving/ })).toBeVisible()
  await expect(page.getByRole("status", { name: /Local runtime online/ })).toBeVisible()
  await expect(page.getByText("No implementation lanes can be established yet.")).toBeVisible()

  await page.getByRole("link", { name: "Trackers", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Tracker truth has not been projected." })).toBeVisible()
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
  await expect(page.getByRole("heading", { name: /Know what is moving/ })).toBeVisible()
  const results = await new AxeBuilder({ page }).analyze()
  const material = results.violations.filter(({ impact }) =>
    impact === "serious" || impact === "critical",
  )
  expect(material).toEqual([])
})

test("maintained viewport has no horizontal page overflow", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: /Know what is moving/ })).toBeVisible()
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test("unknown client routes render the bounded not-found state", async ({ page }) => {
  await page.goto("/does-not-exist")
  await expect(page.getByRole("heading", { name: "That factory workspace does not exist." })).toBeVisible()
  await expect(page.getByText("No operation was attempted.")).toBeVisible()
})
