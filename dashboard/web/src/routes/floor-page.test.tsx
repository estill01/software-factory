import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Provider as JotaiProvider } from "jotai"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router"

import { Component as FloorPage } from "@/routes/floor-page"
import { makeFactoryFloorEnvelope } from "@/test/factory-floor-fixture"

function renderFloor() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 } },
  })
  return render(
    <MemoryRouter>
      <JotaiProvider>
        <QueryClientProvider client={queryClient}>
          <FloorPage />
        </QueryClientProvider>
      </JotaiProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.replaceState({}, "", "/")
})

describe("Factory Floor", () => {
  it("shows a bounded error without a false ready, healthy, or green claim", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("runtime offline")))
    renderFloor()

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("Factory Floor unavailable")
    expect(alert).toHaveTextContent("runtime offline")
    expect(screen.queryByText("Sources current")).not.toBeInTheDocument()
    expect(screen.queryByText("On track")).not.toBeInTheDocument()
  })

  it("answers the overview questions, filters honestly, and opens source detail", async () => {
    const user = userEvent.setup()
    const envelope = makeFactoryFloorEnvelope()
    const current = new Date().toISOString()
    const outsideRange = new Date(Date.now() - 8 * 24 * 60 * 60 * 1_000).toISOString()
    envelope.data.rows[0].freshness.observed_at = current
    envelope.data.rows[1].freshness.observed_at = current
    envelope.data.rows[2].freshness.observed_at = outsideRange
    envelope.data.attention[0].observed_at = current
    envelope.data.attention[1].observed_at = outsideRange
    envelope.data.conclusions[0].observed_at = current
    envelope.data.accepted_outcomes[0].observed_at = current
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    })
    vi.stubGlobal("fetch", fetchMock)
    renderFloor()

    expect(await screen.findByRole("heading", { name: "Implementations & supervisors" })).toBeVisible()
    expect(screen.getByRole("heading", { name: "Needs attention" })).toBeVisible()
    expect(screen.getByRole("heading", { name: "Latest conclusions & accepted outcomes" })).toBeVisible()
    expect(screen.getByRole("heading", { name: "Metrics & freshness" })).toBeVisible()
    expect(screen.getByText("Alpha implementation")).toBeVisible()
    expect(screen.getByText("Beta implementation")).toBeVisible()
    expect(screen.getByText("Gamma implementation")).toBeVisible()
    const alphaRow = screen.getByText("Alpha implementation").closest("article")
    expect(alphaRow).not.toBeNull()
    expect(alphaRow).toHaveTextContent("Watcher · Reviewer")
    expect(alphaRow).toHaveTextContent("group-ta…alpha")
    expect(screen.getByText("A current incident remains open.", { selector: ".attention-item strong" })).toBeVisible()
    expect(screen.getByText("The current review accepted the predecessor.", { selector: ".outcome-item strong" })).toBeVisible()
    expect(screen.getByText("Typed owner adapter")).toBeVisible()
    expect(screen.getByText("Block 6 · Implementation")).toBeVisible()

    await user.selectOptions(screen.getByLabelText("Project"), "gamma")
    expect(screen.getByText("Gamma implementation")).toBeVisible()
    expect(screen.queryByText("Alpha implementation")).not.toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("1 critical hidden by filters")

    await user.selectOptions(screen.getByLabelText("Project"), "all")
    await user.selectOptions(screen.getByLabelText("Time"), "24h")
    expect(screen.getByText("Alpha implementation")).toBeVisible()
    expect(screen.queryByText("Gamma implementation")).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Time"), "all")

    await user.selectOptions(screen.getByLabelText("Posture"), "green")
    expect(screen.getByText("Beta implementation")).toBeVisible()
    expect(screen.queryByText("Alpha implementation")).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Posture"), "all")

    await user.selectOptions(screen.getByLabelText("Attention"), "neutral")
    const taskAttention = screen.getByText("A recent task has no exact supervision run.").closest("li")
    expect(taskAttention).not.toBeNull()
    expect(within(taskAttention!).getByRole("link", { name: "Open" }))
      .toHaveAttribute("href", "/tasks/task-gamma?return=%2F%3Fproject%3Dall%26time%3Dall%26posture%3Dall%26severity%3Dneutral")
    expect(screen.queryByText("A current incident remains open.", { selector: ".attention-item strong" })).not.toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("1 critical hidden by filters")
    await user.selectOptions(screen.getByLabelText("Attention"), "all")

    const betaRow = screen.getByText("Beta implementation").closest("article")
    expect(betaRow).not.toBeNull()
    await user.click(within(betaRow!).getByRole("link", { name: "Inspect" }))
    const runInspector = screen.getByRole("complementary", { name: "Factory source inspector" })
    expect(runInspector).toBeVisible()
    expect(runInspector).toHaveTextContent("group-target-beta")
    expect(runInspector).toHaveTextContent("Role · Watcher")
    expect(runInspector).toHaveTextContent("watcher-target-beta")
    expect(runInspector).toHaveTextContent("Role · Reviewer")
    expect(runInspector).toHaveTextContent("reviewer-target-beta")
    expect(window.location.search).toContain("inspect=run%3Atarget-beta")
    await user.click(screen.getByRole("button", { name: "Close inspector" }))
    await waitFor(() => expect(screen.queryByRole("complementary")).not.toBeInTheDocument())
    expect(window.location.search).toBe("?project=all&time=all&posture=all&severity=all")

    const estimate = screen.getByRole("link", { name: /API-equivalent estimate/ })
    expect(estimate).toHaveTextContent("USD estimate · estimate")
    expect(estimate).toHaveTextContent("Current owner period")
    expect(estimate).toHaveTextContent("3 registered projects")
    expect(within(estimate).queryByText(/spend/i)).not.toBeInTheDocument()
    await user.click(estimate)
    const metricInspector = screen.getByRole("complementary", { name: "Factory source inspector" })
    expect(metricInspector).toHaveTextContent("fixture/api-equivalent")
    expect(metricInspector).toHaveTextContent("3 registered projects")

    await user.click(screen.getByRole("button", { name: "Refresh" }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it("keeps API-bound omitted critical attention visible", async () => {
    const envelope = makeFactoryFloorEnvelope()
    envelope.data.attention_summary = {
      total: 3,
      returned: 2,
      truncated: true,
      critical_total: 2,
      critical_returned: 1,
      critical_omitted: 1,
    }
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    }))

    renderFloor()

    expect(await screen.findByText("1 attention item omitted by the API bound · 1 critical."))
      .toBeVisible()
  })
})
