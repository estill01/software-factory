import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { describe, expect, it, vi } from "vitest"

import { AppShell } from "@/components/app-shell"

const healthPayload = {
  data: {
    status: "ok",
    service: { name: "software-factory-dashboard", version: "0.1.0" },
    integrations: {
      frontend: { status: "available", reason: null },
      project_sources: { status: "unavailable", reason: "Block 2" },
      codex_app_server: { status: "unavailable", reason: "Block 5" },
    },
  },
  source: { kind: "runtime", identity: "dashboard/health", revision: "0.1.0" },
  observed_at: "2026-08-09T08:00:00.000Z",
  fingerprint: "a".repeat(64),
  coverage: { status: "partial", observed: ["runtime"], missing: ["sources"] },
  limitations: ["Block 1"],
  error: null,
}

function renderShell() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => healthPayload }),
  )
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <AppShell />,
        children: [
          { index: true, element: <h1>Floor view</h1> },
          { path: "projects", element: <h1>Project view</h1> },
          { path: "trackers", element: <h1>Tracker view</h1> },
          { path: "reports", element: <h1>Report view</h1> },
          { path: "admin", element: <h1>Admin view</h1> },
        ],
      },
    ],
    { initialEntries: ["/"] },
  )
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe("AppShell", () => {
  it("provides five working primary destinations and live runtime state", async () => {
    renderShell()

    for (const label of ["Factory Floor", "Projects", "Trackers", "Reports", "Admin"]) {
      expect(screen.getAllByRole("link", { name: label })[0]).toBeVisible()
    }
    await userEvent.click(screen.getAllByRole("link", { name: "Projects" })[0])
    expect(await screen.findByRole("heading", { name: "Project view" })).toBeVisible()
    expect(await screen.findByText("Local runtime online")).toBeVisible()
  })

  it("toggles the document theme with a labelled control", async () => {
    renderShell()
    const toggle = screen.getByRole("button", { name: "Switch to light mode" })
    await waitFor(() => expect(document.documentElement).toHaveClass("dark"))
    await userEvent.click(toggle)
    await waitFor(() => expect(document.documentElement).not.toHaveClass("dark"))
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeVisible()
  })
})
