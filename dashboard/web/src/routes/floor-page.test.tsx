import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { Component as FloorPage } from "@/routes/floor-page"

describe("FloorPage runtime readiness", () => {
  it("does not claim runtime readiness when the health request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("runtime offline")))
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, retryDelay: 0 } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <FloorPage />
      </QueryClientProvider>,
    )

    await waitFor(() => {
      expect(screen.getByText("Health check failed; readiness is unknown")).toBeVisible()
    })
    const runtimeRow = screen.getByText("Loopback runtime").closest("li")
    expect(runtimeRow).not.toBeNull()
    expect(within(runtimeRow!).getByText("Unavailable")).toBeVisible()
    expect(within(runtimeRow!).queryByText("Connected and locally constrained")).not.toBeInTheDocument()
    expect(within(runtimeRow!).queryByText("Ready")).not.toBeInTheDocument()
  })
})
