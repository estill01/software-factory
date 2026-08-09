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
          { index: true, element: <div>Floor view</div> },
          { path: "projects", element: <div>Project view</div> },
          { path: "trackers", element: <div>Tracker view</div> },
          { path: "reports", element: <div>Report view</div> },
          { path: "admin", element: <div>Admin view</div> },
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
    expect(await screen.findByRole("heading", { name: "Projects", level: 1 })).toBeVisible()
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1)
    expect(await screen.findByText("Project view")).toBeVisible()
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
