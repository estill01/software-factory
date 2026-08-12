import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({ fetchReports: vi.fn() }))

vi.mock("@/lib/operations-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/operations-api")>()),
  fetchReports: mocks.fetchReports,
}))

import { FactoryEvolutionPanel } from "@/features/admin/factory-evolution-panel"

const hash = "a".repeat(64)

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <MemoryRouter>
      <QueryClientProvider client={client}><FactoryEvolutionPanel /></QueryClientProvider>
    </MemoryRouter>,
  )
}

describe("FactoryEvolutionPanel", () => {
  beforeEach(() => vi.clearAllMocks())

  it("shows the current source stage without implying candidate adoption", async () => {
    mocks.fetchReports.mockResolvedValue({
      data: {
        evolution_workflows: [{
          target_thread_id: "target-thread-001",
          target_label: "Software Factory",
          project_binding: { status: "bound", project_id: "software-factory", evidence: [], limitations: [] },
          workflow: {
            stage: "finalize",
            next_action: "finalize",
            packet_root: hash,
            implementer: { status: "not-selected" },
            disposition: null,
            stages: [
              { id: "prepare", label: "Deterministic prepare", status: "complete" },
              { id: "finalize", label: "Cognitive finalize", status: "current" },
            ],
            error: null,
          },
        }],
      },
    })
    renderPanel()

    const panel = await screen.findByRole("region", { name: "Factory evolution" })
    expect(panel).toHaveTextContent("finalize")
    expect(panel).toHaveTextContent("Deterministic prepare: complete")
    expect(panel).toHaveTextContent("Evolution performs no adoption, installation, routing, scheduling, deployment, rollback, or outcome mutation")
    expect(screen.queryByRole("button", { name: /adopt|deploy|install/i })).not.toBeInTheDocument()
  })
})
