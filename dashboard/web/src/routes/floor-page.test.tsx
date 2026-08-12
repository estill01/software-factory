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
    const alphaDisclosure = screen.getByRole("button", { name: /Alpha implementation/ })
    const betaDisclosure = screen.getByRole("button", { name: /Beta implementation/ })
    const gammaDisclosure = screen.getByRole("button", { name: /Gamma implementation/ })
    expect(alphaDisclosure).toBeVisible()
    expect(betaDisclosure).toBeVisible()
    expect(gammaDisclosure).toBeVisible()
    expect(screen.getByRole("button", { name: "All: 3 returned, source coverage partial" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "Active / Running: 2 returned, source coverage partial" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Attention: 1 returned, source coverage partial" })).toBeVisible()
    const alphaRow = alphaDisclosure.closest("article")
    expect(alphaRow).not.toBeNull()
    expect(alphaRow).toHaveTextContent("Watcher · Reviewer")
    expect(alphaRow).toHaveTextContent("group-ta…alpha")
    expect(alphaRow).toHaveTextContent("26 Blocks")
    expect(alphaRow).toHaveTextContent("5 done · 21 remaining")
    expect(alphaRow).toHaveTextContent("Block 6 — Factory Floor composition")
    const gammaRow = gammaDisclosure.closest("article")
    expect(gammaRow).not.toBeNull()
    expect(gammaRow).toHaveTextContent("Unmonitored")
    expect(gammaRow).toHaveTextContent("2 done · 2 remaining · partial")
    expect(alphaDisclosure).toHaveAttribute("aria-expanded", "false")
    await user.click(alphaDisclosure)
    expect(alphaDisclosure).toHaveAttribute("aria-expanded", "true")
    const alphaRegionId = alphaDisclosure.getAttribute("aria-controls")
    expect(alphaRegionId).not.toBeNull()
    expect(document.getElementById(alphaRegionId!)).toHaveAttribute("role", "region")
    expect(screen.getByText("A current incident remains open.", { selector: ".attention-item strong" })).toBeVisible()
    expect(screen.getByText("The current review accepted the predecessor.", { selector: ".outcome-item strong" })).toBeVisible()
    expect(screen.getByText("Typed owner adapter")).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Attention: 1 returned, source coverage partial" }))
    expect(screen.getByRole("button", { name: /Alpha implementation/ })).toBeVisible()
    expect(screen.queryByRole("button", { name: /Beta implementation/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "All: 3 returned, source coverage partial" }))

    await user.selectOptions(screen.getByLabelText("Project"), "gamma")
    expect(screen.getByRole("button", { name: /Gamma implementation/ })).toBeVisible()
    expect(screen.queryByRole("button", { name: /Alpha implementation/ })).not.toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("1 critical hidden by filters")

    await user.selectOptions(screen.getByLabelText("Project"), "all")
    await user.selectOptions(screen.getByLabelText("Time"), "24h")
    expect(screen.getByRole("button", { name: /Alpha implementation/ })).toBeVisible()
    expect(screen.queryByRole("button", { name: /Gamma implementation/ })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Time"), "all")

    await user.selectOptions(screen.getByLabelText("Posture"), "green")
    expect(screen.getByRole("button", { name: /Beta implementation/ })).toBeVisible()
    expect(screen.queryByRole("button", { name: /Alpha implementation/ })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Posture"), "all")

    await user.selectOptions(screen.getByLabelText("Attention"), "neutral")
    const taskAttention = screen.getByText("A recent task has no exact supervision run.").closest("li")
    expect(taskAttention).not.toBeNull()
    expect(within(taskAttention!).getByRole("link", { name: "Open" }))
      .toHaveAttribute("href", "/tasks/task-gamma?return=%2F%3Fproject%3Dall%26activity%3Dall%26time%3Dall%26posture%3Dall%26severity%3Dneutral")
    expect(screen.queryByText("A current incident remains open.", { selector: ".attention-item strong" })).not.toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("1 critical hidden by filters")
    await user.selectOptions(screen.getByLabelText("Attention"), "all")

    const betaRow = screen.getByRole("button", { name: /Beta implementation/ }).closest("article")
    expect(betaRow).not.toBeNull()
    await user.click(within(betaRow!).getByRole("button", { name: /Beta implementation/ }))
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
    expect(window.location.search).toBe("?project=all&activity=all&time=all&posture=all&severity=all")

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

  it("exposes exact plural Block claims and a keyboard-controlled source region", async () => {
    const user = userEvent.setup()
    const envelope = makeFactoryFloorEnvelope()
    envelope.data.source_health.forEach((source) => {
      source.status = "available"
      source.coverage = { status: "complete", observed: [source.family], missing: [] }
    })
    const trackerClaim = envelope.data.rows[0].work.block_claims.claims[0]
    trackerClaim.blocks.push({
      number: 7,
      title: "A deliberately long tracker-owned heading that stays exact without widening the page",
      status: "in-progress",
      line: 127,
      route: `/trackers/${"a".repeat(64)}/blocks?block=7`,
    })

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    }))
    renderFloor()

    expect(await screen.findByRole("button", { name: "All: 3 exact" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Active / Running: 2 exact" })).toBeVisible()
    const disclosure = screen.getByRole("button", { name: /Alpha implementation.*Block 7 — A deliberately long tracker-owned heading/ })
    disclosure.focus()
    await user.keyboard("{Enter}")
    expect(disclosure).toHaveAttribute("aria-expanded", "true")
    const region = document.getElementById(disclosure.getAttribute("aria-controls")!)
    expect(region).toBeVisible()
    expect(within(region!).getAllByRole("link", { name: /Block 7 — A deliberately long tracker-owned heading/ }))
      .toHaveLength(3)
    expect(within(region!).getAllByRole("link", { name: /Block 7 — A deliberately long tracker-owned heading/ })[0])
      .toHaveAttribute("href", `/trackers/${"a".repeat(64)}/blocks?block=7`)
    expect(within(region!).getAllByRole("link", { name: "Source" })).toHaveLength(3)
  })

  it("keeps conflicting claims separate and labels bounded counts as lower bounds", async () => {
    const envelope = makeFactoryFloorEnvelope()
    envelope.data.rows_truncated = true
    const beta = envelope.data.rows[1]
    beta.work.block_claims.posture = "conflict"
    beta.work.block_claims.claims[1].blocks = [{
      number: 4,
      title: "Different task claim",
      status: "in-progress",
      line: 124,
      route: `/trackers/${"b".repeat(64)}/blocks?block=4`,
    }]
    beta.work.block_claims.claims[1].range = { start: 4, end: 4 }
    beta.work.block_claims.claims[1].status = "conflict"
    beta.work.block_claims.claims[1].reason = "The active task disagrees with tracker and current supervision."
    beta.disagreements.push("Active Block claims disagree across maintained owners.")

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    }))
    renderFloor()

    expect(await screen.findByRole("button", { name: "All: 3 returned, lower bound, source coverage partial" })).toBeVisible()
    const betaDisclosure = screen.getByRole("button", {
      name: /Beta implementation.*Tracker: Block 3.*Implementation task: Block 4 — Different task claim.*Current supervision mission: Block 3/,
    })
    expect(betaDisclosure.closest("article")).toHaveClass("block-claim-conflict")
  })

  it("renders count availability rather than a confident zero", async () => {
    const envelope = makeFactoryFloorEnvelope()
    envelope.data.rows = []
    envelope.data.source_health.forEach((source) => {
      source.status = "unavailable"
      source.coverage = { status: "partial", observed: [], missing: [source.family] }
    })
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    }))
    renderFloor()

    expect(await screen.findByRole("button", { name: "All: unavailable" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Active / Running: unavailable" })).toBeVisible()
    expect(screen.getByText("No rows match the current filters.")).toBeVisible()
  })

  it("makes an exactly completed tracker unmistakable in the collapsed row", async () => {
    const envelope = makeFactoryFloorEnvelope()
    const completed = envelope.data.rows[1]
    completed.implementation.status = "idle"
    completed.implementation.status_label = "Idle"
    completed.supervision.status = "completed"
    completed.supervision.status_label = "Completed"
    completed.work.block_claims.posture = "none"
    completed.work.block_claims.tracker_progress = {
      accepted: 8,
      remaining: 0,
      posture: "exact",
      is_complete: true,
      reason: "Maintained tracker counts for the exact canonical tracker binding.",
    }
    completed.work.block_claims.claims.forEach((claim) => {
      claim.status = "none"
      claim.blocks = []
      claim.range = null
      claim.reason = `${claim.label} reports no active Block.`
    })
    envelope.data.rows = [completed]

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    }))
    renderFloor()

    const disclosure = await screen.findByRole("button", { name: /Beta implementation/ })
    const completedRow = disclosure.closest("article")
    expect(completedRow).toHaveTextContent("8 Blocks")
    expect(completedRow).toHaveTextContent("8 done · 0 remaining")
    expect(completedRow).toHaveTextContent("Tracker complete")
    expect(disclosure).toHaveAccessibleName(/Tracker complete/)
    expect(disclosure).toHaveAccessibleName(/None active/)
  })
})
