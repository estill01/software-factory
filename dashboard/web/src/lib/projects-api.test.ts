import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  archiveProject,
  fetchProject,
  fetchProjects,
  projectDetailEnvelopeSchema,
  projectListEnvelopeSchema,
  registerProject,
} from "@/lib/projects-api"
import { DashboardApiError } from "@/lib/api"

const project = {
  id: "alpha",
  label: "Alpha",
  root: "/work/alpha",
  tracker_patterns: ["planning/**/*implementation-tracker.md"],
  description: "Alpha project",
  archived: false,
  observed_at: "2026-08-09T10:00:00.000Z",
  discovery: {
    status: "available",
    fingerprint: "b".repeat(64),
    git: { status: "available", revision: "c".repeat(40), branch: "main" },
    trackers: {
      status: "available",
      candidates: ["docs/alpha-implementation-tracker.md"],
    },
    source_families: {
      supervision: { status: "unavailable", reason: "Available after Block 4." },
      codex_tasks: { status: "unavailable", reason: "Available after Block 5." },
    },
    coverage: "partial",
    limitations: ["Tracker paths only."],
    errors: [],
  },
} as const

const catalog = {
  data: {
    catalog_fingerprint: "a".repeat(64),
    recovered_from_previous: false,
    projects: [project],
  },
  source: {
    kind: "dashboard-catalog",
    identity: "software-factory-dashboard/project-catalog",
    revision: "a".repeat(64),
  },
  observed_at: "2026-08-09T10:00:00.000Z",
  fingerprint: "d".repeat(64),
  coverage: {
    status: "partial",
    observed: ["catalog", "registered-git-roots"],
    missing: ["tracker-content"],
  },
  limitations: ["Tracker paths only."],
  error: null,
} as const

const errorEnvelope = {
  data: null,
  source: { kind: "runtime", identity: "software-factory-dashboard/http", revision: "0.1.0" },
  observed_at: "2026-08-09T10:00:00.000Z",
  fingerprint: "e".repeat(64),
  coverage: { status: "partial", observed: ["runtime"], missing: [] },
  limitations: [],
  error: {
    code: "stale_catalog_fingerprint",
    message: "Catalog changed after it was observed; refresh before retrying.",
    retryable: true,
  },
} as const

beforeEach(() => {
  document
    .querySelectorAll('meta[name="software-factory-mutation-nonce"]')
    .forEach((element) => element.remove())
  const meta = document.createElement("meta")
  meta.name = "software-factory-mutation-nonce"
  meta.content = "launch-nonce"
  document.head.append(meta)
})

describe("project catalog API contracts", () => {
  it("validates list and detail projections without inventing discovery truth", () => {
    expect(projectListEnvelopeSchema.parse(catalog).data.projects[0].discovery.status).toBe(
      "available",
    )
    expect(
      projectDetailEnvelopeSchema.parse({
        ...catalog,
        data: {
          catalog_fingerprint: catalog.data.catalog_fingerprint,
          recovered_from_previous: false,
          project,
        },
      }).data.project.discovery.trackers.candidates,
    ).toEqual(["docs/alpha-implementation-tracker.md"])

    expect(() =>
      projectListEnvelopeSchema.parse({
        ...catalog,
        data: {
          ...catalog.data,
          projects: [{ ...project, discovery: { ...project.discovery, status: "healthy" } }],
        },
      }),
    ).toThrow()
  })

  it("uses bounded read routes and preserves abort signals", async () => {
    const detail = {
      ...catalog,
      data: {
        catalog_fingerprint: catalog.data.catalog_fingerprint,
        recovered_from_previous: false,
        project,
      },
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => catalog })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => detail })
    vi.stubGlobal("fetch", fetchMock)
    const controller = new AbortController()

    await fetchProjects(true, controller.signal)
    await fetchProject("alpha/beta", controller.signal)

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/projects?include_archived=true",
      expect.objectContaining({ signal: controller.signal }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/projects/alpha%2Fbeta",
      expect.objectContaining({ signal: controller.signal }),
    )
  })

  it("sends the launch nonce and exact catalog-only mutation fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => catalog,
    })
    vi.stubGlobal("fetch", fetchMock)

    await registerProject("a".repeat(64), {
      id: "alpha",
      label: "Alpha",
      root: "/work/alpha",
      tracker_patterns: [],
      description: null,
    })
    await archiveProject("a".repeat(64), "alpha")

    const registration = fetchMock.mock.calls[0][1] as RequestInit
    expect(registration.method).toBe("POST")
    expect(registration.headers).toMatchObject({
      "Content-Type": "application/json",
      "X-Software-Factory-Nonce": "launch-nonce",
    })
    expect(JSON.parse(String(registration.body))).toEqual({
      source_fingerprint: "a".repeat(64),
      project: {
        id: "alpha",
        label: "Alpha",
        root: "/work/alpha",
        tracker_patterns: [],
        description: null,
      },
    })

    const archive = fetchMock.mock.calls[1][1] as RequestInit
    expect(archive.method).toBe("PATCH")
    expect(JSON.parse(String(archive.body))).toEqual({
      source_fingerprint: "a".repeat(64),
      action: "archive",
      confirmation: "archive:alpha",
    })
  })

  it("parses a structured catalog error before throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => errorEnvelope }),
    )

    const request = fetchProjects(false)
    await expect(request).rejects.toBeInstanceOf(DashboardApiError)
    await expect(request).rejects.toMatchObject({
      code: "stale_catalog_fingerprint",
      retryable: true,
      status: 409,
    })
  })
})
