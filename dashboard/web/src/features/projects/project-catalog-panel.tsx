import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Archive,
  ArchiveRestore,
  CircleAlert,
  FolderGit2,
  Pencil,
  Plus,
  RefreshCw,
  X,
} from "lucide-react"
import { type FormEvent, useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  archiveProject,
  fetchProject,
  fetchProjects,
  type ProjectInput,
  type ProjectListEnvelope,
  type ProjectProjection,
  projectInputSchema,
  registerProject,
  unarchiveProject,
  updateProjectPresentation,
} from "@/lib/projects-api"

const catalogQueryKey = ["projects", true] as const

type EditState = {
  id: string
  label: string
  description: string
  patterns: string
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The catalog operation failed."
}

function splitPatterns(value: string): string[] {
  return [...new Set(value.split("\n").map((pattern) => pattern.trim()).filter(Boolean))]
}

function CatalogStatus({
  catalog,
  refreshing,
  onRefresh,
}: {
  catalog: ProjectListEnvelope
  refreshing: boolean
  onRefresh: () => void
}) {
  const archived = catalog.data.projects.filter((project) => project.archived).length
  return (
    <div className="catalog-summary">
      <div className="catalog-status" role="group" aria-label="Catalog status">
        <div><span>Registered</span><strong>{catalog.data.projects.length}</strong></div>
        <div><span>Visible</span><strong>{catalog.data.projects.length - archived}</strong></div>
        <div><span>Archived</span><strong>{archived}</strong></div>
        <div><span>Revision</span><code>{catalog.data.catalog_fingerprint.slice(0, 10)}</code></div>
      </div>
      <div className="catalog-summary-action">
        <Button variant="outline" size="compact" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw aria-hidden="true" /> Refresh catalog
        </Button>
      </div>
    </div>
  )
}

type ProjectRowProps = {
  project: ProjectProjection
  editing: EditState | null
  archiveConfirmation: string | null
  busy: boolean
  mutationsDisabled: boolean
  onBeginEdit: (project: ProjectProjection) => void
  onCancelEdit: () => void
  onEditChange: (edit: EditState) => void
  onSaveEdit: (event: FormEvent<HTMLFormElement>) => void
  onBeginArchive: (projectId: string) => void
  onCancelArchive: () => void
  onConfirmArchive: (projectId: string) => void
  onRestore: (projectId: string) => void
  onRefresh: (project: ProjectProjection) => void
}

function ProjectRow({
  project,
  editing,
  archiveConfirmation,
  busy,
  mutationsDisabled,
  onBeginEdit,
  onCancelEdit,
  onEditChange,
  onSaveEdit,
  onBeginArchive,
  onCancelArchive,
  onConfirmArchive,
  onRestore,
  onRefresh,
}: ProjectRowProps) {
  const unavailable = project.discovery.status === "unavailable"
  return (
    <article className={`catalog-project ${project.archived ? "catalog-project-archived" : ""}`}>
      <div className="catalog-project-heading">
        <div className={`project-mark ${unavailable ? "project-mark-error" : ""}`}>
          {unavailable ? <CircleAlert aria-hidden="true" /> : <FolderGit2 aria-hidden="true" />}
        </div>
        <div>
          <div className="project-title-line">
            <h3>{project.label}</h3>
            <span className="project-id">{project.id}</span>
            {project.archived && <span className="project-archived-badge">Archived</span>}
          </div>
          <p>{project.description || "No display description."}</p>
        </div>
        <span className={`discovery-badge ${unavailable ? "discovery-unavailable" : ""}`}>
          {unavailable ? "Discovery unavailable" : "Discovery ready"}
        </span>
      </div>

      <dl className="project-facts">
        <div><dt>Repository root</dt><dd><code>{project.root}</code></dd></div>
        <div><dt>Git revision</dt><dd><code>{project.discovery.git.revision?.slice(0, 12) || "Unavailable"}</code></dd></div>
        <div><dt>Branch</dt><dd>{project.discovery.git.branch || "Detached / unavailable"}</dd></div>
        <div><dt>Tracker candidates</dt><dd>{project.discovery.trackers.candidates.length}</dd></div>
      </dl>

      {project.discovery.errors.length > 0 && (
        <div className="catalog-inline-error" role="alert">
          <CircleAlert aria-hidden="true" />
          <span>{project.discovery.errors.map((error) => error.message).join(" ")}</span>
        </div>
      )}

      {editing?.id === project.id && (
        <form className="catalog-edit-form" onSubmit={onSaveEdit}>
          <label>
            Display label
            <input
              value={editing.label}
              maxLength={80}
              required
              onChange={(event) => onEditChange({ ...editing, label: event.target.value })}
            />
          </label>
          <label>
            Description
            <textarea
              value={editing.description}
              maxLength={500}
              rows={2}
              onChange={(event) => onEditChange({ ...editing, description: event.target.value })}
            />
          </label>
          <label className="catalog-form-wide">
            Additional tracker globs <span>one relative `.md` pattern per line</span>
            <textarea
              value={editing.patterns}
              rows={2}
              onChange={(event) => onEditChange({ ...editing, patterns: event.target.value })}
            />
          </label>
          <div className="catalog-form-actions catalog-form-wide">
            <Button type="submit" size="compact" disabled={mutationsDisabled}>Save presentation</Button>
            <Button type="button" variant="ghost" size="compact" onClick={onCancelEdit}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {archiveConfirmation === project.id && (
        <div className="archive-confirmation" role="group" aria-label={`Archive ${project.label}`}>
          <div>
            <strong>Remove this project from normal dashboard views?</strong>
            <p>This archives discovery metadata only. It never deletes repository files, stops work, or changes the project.</p>
          </div>
          <div className="catalog-form-actions">
            <Button size="compact" onClick={() => onConfirmArchive(project.id)} disabled={mutationsDisabled}>
              Confirm archive
            </Button>
            <Button variant="ghost" size="compact" onClick={onCancelArchive}>Cancel</Button>
          </div>
        </div>
      )}

      <div className="catalog-project-actions">
        <Button variant="outline" size="compact" onClick={() => onRefresh(project)} disabled={busy}>
          <RefreshCw aria-hidden="true" /> Refresh project
        </Button>
        <Button variant="ghost" size="compact" onClick={() => onBeginEdit(project)} disabled={mutationsDisabled}>
          <Pencil aria-hidden="true" /> Edit presentation
        </Button>
        {project.archived ? (
          <Button variant="ghost" size="compact" onClick={() => onRestore(project.id)} disabled={mutationsDisabled}>
            <ArchiveRestore aria-hidden="true" /> Restore to views
          </Button>
        ) : (
          <Button variant="ghost" size="compact" onClick={() => onBeginArchive(project.id)} disabled={mutationsDisabled}>
            <Archive aria-hidden="true" /> Archive from dashboard
          </Button>
        )}
      </div>
    </article>
  )
}

export function ProjectCatalogPanel() {
  const queryClient = useQueryClient()
  const catalog = useQuery({
    queryKey: catalogQueryKey,
    queryFn: ({ signal }) => fetchProjects(true, signal),
  })
  const [projectId, setProjectId] = useState("")
  const [label, setLabel] = useState("")
  const [root, setRoot] = useState("")
  const [description, setDescription] = useState("")
  const [patterns, setPatterns] = useState("")
  const [editing, setEditing] = useState<EditState | null>(null)
  const [archiveConfirmation, setArchiveConfirmation] = useState<string | null>(null)
  const [refreshed, setRefreshed] = useState<Record<string, ProjectProjection>>({})
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    setRefreshed({})
  }, [catalog.dataUpdatedAt])

  const acceptMutation = (next: ProjectListEnvelope) => {
    queryClient.setQueryData(catalogQueryKey, next)
    void queryClient.invalidateQueries({ queryKey: ["projects", false] })
    setRefreshed({})
    setLocalError(null)
  }

  const registration = useMutation({
    mutationFn: (input: ProjectInput) =>
      registerProject(catalog.data?.data.catalog_fingerprint ?? "", input),
    onSuccess: (next) => {
      acceptMutation(next)
      setProjectId("")
      setLabel("")
      setRoot("")
      setDescription("")
      setPatterns("")
    },
  })
  const presentation = useMutation({
    mutationFn: (edit: EditState) =>
      updateProjectPresentation(
        catalog.data?.data.catalog_fingerprint ?? "",
        edit.id,
        {
          label: edit.label.trim(),
          description: edit.description.trim() || null,
          tracker_patterns: splitPatterns(edit.patterns),
        },
      ),
    onSuccess: (next) => {
      acceptMutation(next)
      setEditing(null)
    },
  })
  const posture = useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      archived
        ? archiveProject(catalog.data?.data.catalog_fingerprint ?? "", id)
        : unarchiveProject(catalog.data?.data.catalog_fingerprint ?? "", id),
    onSuccess: (next) => {
      acceptMutation(next)
      setArchiveConfirmation(null)
    },
  })
  const busy = registration.isPending || presentation.isPending || posture.isPending
  const operationError = registration.error || presentation.error || posture.error
  const mutationsDisabled = busy || Boolean(catalog.data?.data.recovered_from_previous)

  const submitRegistration = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLocalError(null)
    try {
      const input = projectInputSchema.parse({
        id: projectId.trim(),
        label: label.trim(),
        root: root.trim(),
        tracker_patterns: splitPatterns(patterns),
        description: description.trim() || null,
      })
      registration.mutate(input)
    } catch (error) {
      setLocalError(errorMessage(error))
    }
  }

  const submitEdit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!editing) return
    setLocalError(null)
    try {
      projectInputSchema.pick({ label: true, description: true, tracker_patterns: true }).parse({
        label: editing.label,
        description: editing.description.trim() || null,
        tracker_patterns: splitPatterns(editing.patterns),
      })
      presentation.mutate(editing)
    } catch (error) {
      setLocalError(errorMessage(error))
    }
  }

  const refreshOne = async (project: ProjectProjection) => {
    setLocalError(null)
    try {
      const result = await fetchProject(project.id)
      const current = queryClient.getQueryData<ProjectListEnvelope>(catalogQueryKey)
      if (result.data.catalog_fingerprint !== current?.data.catalog_fingerprint) {
        await catalog.refetch()
        setLocalError("Catalog changed during refresh; the full catalog was refreshed instead.")
        return
      }
      setRefreshed((current) => ({ ...current, [project.id]: result.data.project }))
    } catch (error) {
      setLocalError(errorMessage(error))
    }
  }

  return (
    <section className="catalog-panel" aria-label="Project catalog">
      {catalog.isPending && <div className="catalog-loading" role="status">Loading project catalog…</div>}
      {catalog.isError && (
        <div className="catalog-error" role="alert">
          <CircleAlert aria-hidden="true" />
          <div><strong>Project catalog unavailable</strong><p>{errorMessage(catalog.error)}</p></div>
          <Button variant="outline" size="compact" onClick={() => void catalog.refetch()}>Retry</Button>
        </div>
      )}

      {catalog.data && (
        <>
          <CatalogStatus
            catalog={catalog.data}
            refreshing={catalog.isFetching}
            onRefresh={() => void catalog.refetch()}
          />
          {catalog.data.data.recovered_from_previous && (
            <div className="catalog-warning" role="alert">
              <CircleAlert aria-hidden="true" />
              A valid prior catalog is shown read-only because the current file could not be validated.
            </div>
          )}

          <form className="catalog-register-form" onSubmit={submitRegistration}>
            <div className="catalog-form-title">
              <div className="project-mark"><Plus aria-hidden="true" /></div>
              <div><h3>Register a repository</h3><p>Use the exact canonical Git top-level path. Broad discovery is never attempted.</p></div>
            </div>
            <label>
              Stable project ID
              <input value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="software-factory" minLength={2} maxLength={64} required />
            </label>
            <label>
              Display label
              <input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Software Factory" maxLength={80} required />
            </label>
            <label className="catalog-form-wide">
              Canonical repository root
              <input value={root} onChange={(event) => setRoot(event.target.value)} placeholder="/absolute/path/to/repository" required />
            </label>
            <label className="catalog-form-wide">
              Description <span>optional presentation text</span>
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={2} maxLength={500} />
            </label>
            <label className="catalog-form-wide">
              Additional tracker globs <span>optional, one relative `.md` pattern per line</span>
              <textarea value={patterns} onChange={(event) => setPatterns(event.target.value)} rows={2} placeholder="planning/**/*implementation-tracker.md" />
            </label>
            <div className="catalog-form-actions catalog-form-wide">
              <Button type="submit" disabled={mutationsDisabled}>
                <Plus aria-hidden="true" /> Register project
              </Button>
              <span>Registration does not read tracker contents or change the repository.</span>
            </div>
          </form>

          {(localError || operationError) && (
            <div className="catalog-inline-error" role="alert">
              <CircleAlert aria-hidden="true" />
              <span>{localError || errorMessage(operationError)}</span>
              {localError && <Button variant="ghost" size="icon" aria-label="Dismiss catalog message" onClick={() => setLocalError(null)}><X aria-hidden="true" /></Button>}
            </div>
          )}

          <div className="catalog-project-list">
            {catalog.data.data.projects.length === 0 ? (
              <div className="catalog-empty">
                <FolderGit2 aria-hidden="true" />
                <h3>No repositories are registered.</h3>
                <p>Add exact Git roots above. The dashboard never scans your home directory.</p>
              </div>
            ) : (
              catalog.data.data.projects.map((catalogProject) => {
                const project = refreshed[catalogProject.id] ?? catalogProject
                return (
                  <ProjectRow
                    key={project.id}
                    project={project}
                    editing={editing}
                    archiveConfirmation={archiveConfirmation}
                    busy={busy}
                    mutationsDisabled={mutationsDisabled}
                    onBeginEdit={(selected) => {
                      setArchiveConfirmation(null)
                      setEditing({
                        id: selected.id,
                        label: selected.label,
                        description: selected.description ?? "",
                        patterns: selected.tracker_patterns.join("\n"),
                      })
                    }}
                    onCancelEdit={() => setEditing(null)}
                    onEditChange={setEditing}
                    onSaveEdit={submitEdit}
                    onBeginArchive={(id) => {
                      setEditing(null)
                      setArchiveConfirmation(id)
                    }}
                    onCancelArchive={() => setArchiveConfirmation(null)}
                    onConfirmArchive={(id) => posture.mutate({ id, archived: true })}
                    onRestore={(id) => posture.mutate({ id, archived: false })}
                    onRefresh={(selected) => void refreshOne(selected)}
                  />
                )
              })
            )}
          </div>
        </>
      )}
    </section>
  )
}
