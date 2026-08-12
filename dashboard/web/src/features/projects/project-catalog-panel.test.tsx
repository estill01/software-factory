import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ProjectCatalogPanel } from "@/features/projects/project-catalog-panel"
import * as projectsApi from "@/lib/projects-api"
import type {
  ProjectDetailEnvelope,
  ProjectListEnvelope,
  ProjectProjection,
} from "@/lib/projects-api"

vi.mock("@/lib/projects-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/projects-api")>()
  return {
    ...original,
    archiveProject: vi.fn(),
    fetchProject: vi.fn(),
    fetchProjects: vi.fn(),
    registerProject: vi.fn(),
    unarchiveProject: vi.fn(),
    updateProjectPresentation: vi.fn(),
  }
})

const fingerprint = (character: string) => character.repeat(64)

function projection(archived = false): ProjectProjection {
  return {
    id: "alpha",
    label: "Alpha",
    root: "/work/alpha",
    tracker_patterns: [],
    description: "Alpha project",
    archived,
    observed_at: "2026-08-09T10:00:00.000Z",
    discovery: {
      status: "available",
      fingerprint: fingerprint("b"),
      git: { status: "available", revision: "c".repeat(40), branch: "main" },
      trackers: { status: "available", candidates: [] },
      source_families: {
        supervision: { status: "unavailable", reason: "Use the source-owning run API." },
        codex_tasks: { status: "unavailable", reason: "Use the source-owning task API." },
      },
      coverage: "partial",
      limitations: ["Tracker paths only."],
      errors: [],
    },
  }
}

function catalog(
  projects: ProjectProjection[],
  revision = fingerprint("a"),
  recovered = false,
): ProjectListEnvelope {
  return {
    data: {
      catalog_fingerprint: revision,
      recovered_from_previous: recovered,
      projects,
    },
    source: {
      kind: "dashboard-catalog",
      identity: "software-factory-dashboard/project-catalog",
      revision,
    },
    observed_at: "2026-08-09T10:00:00.000Z",
    fingerprint: fingerprint("d"),
    coverage: { status: "partial", observed: ["catalog"], missing: ["tracker-content"] },
    limitations: ["Tracker paths only."],
    error: null,
  }
}

function detail(project: ProjectProjection, revision: string): ProjectDetailEnvelope {
  return {
    data: {
      catalog_fingerprint: revision,
      recovered_from_previous: false,
      project,
    },
    source: {
      kind: "dashboard-catalog",
      identity: `software-factory-dashboard/project-catalog/${project.id}`,
      revision,
    },
    observed_at: "2026-08-09T10:01:00.000Z",
    fingerprint: fingerprint("2"),
    coverage: { status: "partial", observed: ["catalog"], missing: ["tracker-content"] },
    limitations: ["Tracker paths only."],
    error: null,
  }
}

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <ProjectCatalogPanel />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(projectsApi.fetchProjects).mockReset()
  vi.mocked(projectsApi.fetchProject).mockReset()
  vi.mocked(projectsApi.registerProject).mockReset()
  vi.mocked(projectsApi.archiveProject).mockReset()
  vi.mocked(projectsApi.unarchiveProject).mockReset()
  vi.mocked(projectsApi.updateProjectPresentation).mockReset()
})

describe("ProjectCatalogPanel", () => {
  it("registers, confirms archive consequences, and restores visibility", async () => {
    const active = projection()
    const archived = projection(true)
    const refreshed = {
      ...active,
      discovery: {
        ...active.discovery,
        git: { ...active.discovery.git, revision: "9".repeat(40) },
      },
    }
    vi.mocked(projectsApi.fetchProjects).mockResolvedValue(catalog([]))
    vi.mocked(projectsApi.registerProject).mockResolvedValue(catalog([active], fingerprint("e")))
    vi.mocked(projectsApi.fetchProject).mockResolvedValue(detail(refreshed, fingerprint("e")))
    vi.mocked(projectsApi.archiveProject).mockResolvedValue(catalog([archived], fingerprint("f")))
    vi.mocked(projectsApi.unarchiveProject).mockResolvedValue(catalog([active], fingerprint("1")))
    const user = userEvent.setup()
    renderPanel()

    expect(await screen.findByText("No repositories are registered.")).toBeVisible()
    await user.type(screen.getByLabelText("Stable project ID"), "alpha")
    await user.type(screen.getByLabelText("Display label"), "Alpha")
    await user.type(screen.getByLabelText("Canonical repository root"), "/work/alpha")
    await user.click(screen.getByRole("button", { name: "Register project" }))

    await waitFor(() =>
      expect(projectsApi.registerProject).toHaveBeenCalledWith(fingerprint("a"), {
        id: "alpha",
        label: "Alpha",
        root: "/work/alpha",
        tracker_patterns: [],
        description: null,
      }),
    )
    expect(await screen.findByRole("heading", { name: "Alpha" })).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Refresh project" }))
    await waitFor(() => expect(projectsApi.fetchProject).toHaveBeenCalledWith("alpha"))
    expect(await screen.findByText("999999999999")).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Archive from dashboard" }))
    const confirmation = screen.getByRole("group", { name: "Archive Alpha" })
    expect(confirmation).toHaveTextContent("never deletes repository files, stops work, or changes the project")
    await user.click(screen.getByRole("button", { name: "Confirm archive" }))
    await waitFor(() =>
      expect(projectsApi.archiveProject).toHaveBeenCalledWith(fingerprint("e"), "alpha"),
    )
    const archivedArticle = screen.getByRole("heading", { name: "Alpha" }).closest("article")
    expect(archivedArticle).not.toBeNull()
    expect(within(archivedArticle!).getByText("Archived")).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Restore to views" }))
    await waitFor(() =>
      expect(projectsApi.unarchiveProject).toHaveBeenCalledWith(fingerprint("f"), "alpha"),
    )
    await waitFor(() => {
      const restoredArticle = screen.getByRole("heading", { name: "Alpha" }).closest("article")
      expect(restoredArticle).not.toBeNull()
      expect(within(restoredArticle!).queryByText("Archived")).not.toBeInTheDocument()
    })
  })

  it("keeps recovered prior state read-only", async () => {
    vi.mocked(projectsApi.fetchProjects).mockResolvedValue(catalog([projection()], undefined, true))
    renderPanel()

    expect(await screen.findByText(/valid prior catalog is shown read-only/i)).toBeVisible()
    expect(screen.getByRole("button", { name: "Register project" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Edit presentation" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Archive from dashboard" })).toBeDisabled()
  })
})
