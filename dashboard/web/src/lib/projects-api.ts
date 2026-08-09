import { z } from "zod"

import {
  apiErrorEnvelopeSchema,
  coverageSchema,
  DashboardApiError,
  mutationNonce,
  sourceSchema,
} from "@/lib/api"

const fingerprintSchema = z.string().regex(/^[0-9a-f]{64}$/)

export const trackerPatternSchema = z
  .string()
  .trim()
  .min(1)
  .max(240)
  .endsWith(".md")
  .refine((pattern) => !pattern.startsWith("/") && !pattern.includes("\\"), {
    message: "Use a relative forward-slash Markdown glob.",
  })
  .refine((pattern) => !pattern.split("/").includes(".."), {
    message: "Tracker patterns cannot traverse outside the project.",
  })

export const projectInputSchema = z
  .object({
    id: z.string().regex(/^[a-z0-9][a-z0-9._-]{1,63}$/),
    label: z.string().trim().min(1).max(80),
    root: z
      .string()
      .min(1)
      .refine((root) => root.startsWith("/") && !root.split("/").includes(".."), {
        message: "Use an absolute canonical repository path without traversal.",
      }),
    tracker_patterns: z.array(trackerPatternSchema).max(16),
    description: z.string().trim().max(500).nullable(),
  })
  .strict()

const availabilitySchema = z.object({
  status: z.enum(["available", "unavailable"]),
  reason: z.string().nullable().optional(),
})

export const projectProjectionSchema = z.object({
  id: z.string(),
  label: z.string(),
  root: z.string(),
  tracker_patterns: z.array(z.string()),
  description: z.string().nullable(),
  archived: z.boolean(),
  observed_at: z.iso.datetime({ offset: true }),
  discovery: z.object({
    status: z.enum(["available", "unavailable"]),
    fingerprint: fingerprintSchema.nullable(),
    git: z.object({
      status: z.enum(["available", "unavailable"]),
      revision: z.string().nullable(),
      branch: z.string().nullable(),
    }),
    trackers: z.object({
      status: z.enum(["available", "unavailable"]),
      candidates: z.array(z.string()),
    }),
    source_families: z.object({
      supervision: availabilitySchema,
      codex_tasks: availabilitySchema,
    }),
    coverage: z.enum(["partial", "unavailable"]),
    limitations: z.array(z.string()),
    errors: z.array(z.object({ code: z.string(), message: z.string() })),
  }),
})

const envelopeMetadata = {
  source: sourceSchema,
  observed_at: z.iso.datetime({ offset: true }),
  fingerprint: fingerprintSchema,
  coverage: coverageSchema,
  limitations: z.array(z.string()),
  error: z.null(),
}

export const projectListEnvelopeSchema = z.object({
  data: z.object({
    catalog_fingerprint: fingerprintSchema,
    recovered_from_previous: z.boolean(),
    projects: z.array(projectProjectionSchema),
  }),
  ...envelopeMetadata,
})

export const projectDetailEnvelopeSchema = z.object({
  data: z.object({
    catalog_fingerprint: fingerprintSchema,
    recovered_from_previous: z.boolean(),
    project: projectProjectionSchema,
  }),
  ...envelopeMetadata,
})

export type ProjectInput = z.infer<typeof projectInputSchema>
export type ProjectProjection = z.infer<typeof projectProjectionSchema>
export type ProjectListEnvelope = z.infer<typeof projectListEnvelopeSchema>
export type ProjectDetailEnvelope = z.infer<typeof projectDetailEnvelopeSchema>

async function parsedResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const payload: unknown = await response.json()
  if (!response.ok) {
    throw new DashboardApiError(response.status, apiErrorEnvelopeSchema.parse(payload))
  }
  return schema.parse(payload)
}

async function catalogMutation(path: string, payload: object): Promise<ProjectListEnvelope> {
  const nonce = mutationNonce()
  if (!nonce) throw new Error("The per-launch mutation nonce is unavailable; reload the dashboard.")
  return parsedResponse(
    await fetch(path, {
      method: path === "/api/v1/projects" ? "POST" : "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Software-Factory-Nonce": nonce,
      },
      body: JSON.stringify(payload),
    }),
    projectListEnvelopeSchema,
  )
}

export async function fetchProjects(
  includeArchived: boolean,
  signal?: AbortSignal,
): Promise<ProjectListEnvelope> {
  return parsedResponse(
    await fetch(`/api/v1/projects?include_archived=${includeArchived}`, {
      headers: { Accept: "application/json" },
      signal,
    }),
    projectListEnvelopeSchema,
  )
}

export async function fetchProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectDetailEnvelope> {
  return parsedResponse(
    await fetch(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
      headers: { Accept: "application/json" },
      signal,
    }),
    projectDetailEnvelopeSchema,
  )
}

export function registerProject(
  sourceFingerprint: string,
  input: ProjectInput,
): Promise<ProjectListEnvelope> {
  return catalogMutation("/api/v1/projects", {
    source_fingerprint: sourceFingerprint,
    project: projectInputSchema.parse(input),
  })
}

export function updateProjectPresentation(
  sourceFingerprint: string,
  projectId: string,
  changes: Pick<ProjectInput, "label" | "description" | "tracker_patterns">,
): Promise<ProjectListEnvelope> {
  return catalogMutation(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
    source_fingerprint: sourceFingerprint,
    action: "update_presentation",
    changes,
  })
}

export function archiveProject(
  sourceFingerprint: string,
  projectId: string,
): Promise<ProjectListEnvelope> {
  return catalogMutation(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
    source_fingerprint: sourceFingerprint,
    action: "archive",
    confirmation: `archive:${projectId}`,
  })
}

export function unarchiveProject(
  sourceFingerprint: string,
  projectId: string,
): Promise<ProjectListEnvelope> {
  return catalogMutation(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
    source_fingerprint: sourceFingerprint,
    action: "unarchive",
  })
}
