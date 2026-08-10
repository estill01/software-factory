import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Archive, FolderGit2, RefreshCw } from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router"

import { Button } from "@/components/ui/button"
import { Identity, QueryState, StatusMark, TimeValue } from "@/components/workspace-ui"
import { fetchFactoryFloor } from "@/lib/floor-api"
import { fetchReports, fetchRuns } from "@/lib/operations-api"
import { fetchProjects } from "@/lib/projects-api"
import { fetchTrackers } from "@/lib/trackers-api"
import { newestTimestamp } from "@/lib/workspace-data"

function Count({ value, bounded = false, loading = false }: { value: number | null; bounded?: boolean; loading?: boolean }) {
  return <>{loading ? "…" : value === null ? "Unavailable" : `${bounded ? "≥" : ""}${value}`}</>
}

export function ProjectInventory() {
  const [showArchived, setShowArchived] = useState(false)
  const projects = useQuery({
    queryKey: ["projects", true],
    queryFn: ({ signal }) => fetchProjects(true, signal),
  })
  const trackers = useQuery({
    queryKey: ["trackers"],
    queryFn: ({ signal }) => fetchTrackers(signal),
  })
  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: ({ signal }) => fetchReports(signal),
  })
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: ({ signal }) => fetchRuns(signal),
  })
  const floor = useQuery({
    queryKey: ["factory-floor"],
    queryFn: ({ signal }) => fetchFactoryFloor(signal),
  })

  const visible = useMemo(
    () => projects.data?.data.projects.filter((project) => showArchived || !project.archived) ?? [],
    [projects.data, showArchived],
  )
  const exactlyAssociatedRunIds = new Set([
    ...(floor.data?.data.rows.flatMap((row) => row.supervision.run_id ? [row.supervision.run_id] : []) ?? []),
    ...(runs.data?.data.runs.flatMap((run) => run.project_binding.status === "bound" ? [run.target_thread_id] : []) ?? []),
  ])
  const unresolvedReportAssociation = reports.data?.data.reports.some(
    (report) => !exactlyAssociatedRunIds.has(report.target_thread_id),
  ) ?? false

  if (projects.isPending) return <QueryState kind="loading" message="Loading projects" />
  if (projects.isError) {
    return <QueryState kind="error" message={projects.error.message} retry={() => void projects.refetch()} />
  }

  return (
    <div className="page-stack projects-index">
      <div className="workspace-toolbar">
        <span>{visible.length} of {projects.data.data.projects.length} projects</span>
        <Button
          variant={showArchived ? "default" : "outline"}
          size="compact"
          onClick={() => setShowArchived((value) => !value)}
          aria-pressed={showArchived}
        >
          <Archive aria-hidden="true" />{showArchived ? "Hide archived" : "Show archived"}
        </Button>
      </div>

      {visible.length === 0 ? (
        <QueryState kind="empty" message={showArchived ? "No projects registered" : "No active projects registered"} />
      ) : (
        <div className="project-operations-list">
          {visible.map((project) => {
            const composedRows = floor.data?.data.rows.filter((row) => row.project.project_id === project.id) ?? []
            const composedRunIds = new Set(composedRows.flatMap((row) => row.supervision.run_id ? [row.supervision.run_id] : []))
            const boundRunIds = new Set(runs.data?.data.runs.flatMap((run) =>
              run.project_binding.status === "bound" && run.project_binding.project_id === project.id
                ? [run.target_thread_id]
                : [],
            ) ?? [])
            const projectRunIds = new Set([...composedRunIds, ...boundRunIds])
            const trackerRows = trackers.data?.data.trackers.filter((tracker) => tracker.project_id === project.id) ?? []
            const reportRows = reports.data?.data.reports.filter((report) => projectRunIds.has(report.target_thread_id)) ?? []
            const attention = composedRows.reduce((total, row) => total + row.issues.total, 0)
            const outcome = floor.data?.data.accepted_outcomes.find((item) => item.project_id === project.id)
            const lastActivity = newestTimestamp(composedRows.map((row) => row.freshness.observed_at))
            const activeTaskIds = new Set(composedRows.filter((row) => row.implementation.status === "active").map((row) => row.implementation.task_id))

            return (
              <article className="project-operations-row" key={project.id}>
                <div className="project-row-identity">
                  <span className={`project-mark ${project.discovery.status === "unavailable" ? "project-mark-error" : ""}`}>
                    {project.discovery.status === "unavailable"
                      ? <AlertTriangle aria-hidden="true" />
                      : <FolderGit2 aria-hidden="true" />}
                  </span>
                  <div>
                    <Link to={`/projects/${encodeURIComponent(project.id)}`}>{project.label}</Link>
                    <code title={project.root}>{project.root}</code>
                    {project.archived && <span className="workspace-badge">Archived</span>}
                  </div>
                </div>

                <div className="project-row-health">
                  <StatusMark status={project.discovery.status} />
                  <span>{project.discovery.git.branch ?? "Branch unavailable"}</span>
                  <Identity value={project.discovery.git.revision} />
                  {project.discovery.errors.map((error) => (
                    <span className="workspace-error-text" key={error.code}>{error.message}</span>
                  ))}
                </div>

                <dl className="project-row-counts">
                  <div><dt>Active tasks</dt><dd><Count loading={floor.isPending} value={floor.isError ? null : activeTaskIds.size} bounded={Boolean(floor.data?.data.rows_truncated) && activeTaskIds.size > 0} /></dd></div>
                  <div><dt>Runs</dt><dd><Count loading={floor.isPending || runs.isPending} value={floor.isError && runs.isError ? null : projectRunIds.size} bounded={floor.isError || runs.isError} /></dd></div>
                  <div><dt>Attention</dt><dd><Count loading={floor.isPending} value={floor.isError ? null : attention} /></dd></div>
                  <div><dt>Trackers</dt><dd><Count loading={trackers.isPending} value={trackers.isError ? null : trackerRows.length} /></dd></div>
                  <div><dt>Reports</dt><dd><Count loading={reports.isPending || floor.isPending || runs.isPending} value={reports.isError || (floor.isError && runs.isError) ? null : reportRows.length} bounded={floor.isError || runs.isError || unresolvedReportAssociation} /></dd></div>
                </dl>

                <div className="project-row-recent">
                  <span>Last activity</span>
                  {floor.isPending ? <strong>Loading</strong> : <TimeValue value={lastActivity} />}
                  <span>Last accepted outcome</span>
                  {floor.isPending ? <strong>Loading</strong> : floor.isError ? <strong>Unavailable</strong> : outcome ? (
                    <strong>Block {outcome.block} · {outcome.title}</strong>
                  ) : <strong>None recorded</strong>}
                </div>

                <Button variant="outline" size="compact" asChild>
                  <Link to={`/projects/${encodeURIComponent(project.id)}`}>Open</Link>
                </Button>
              </article>
            )
          })}
        </div>
      )}

      {([trackers, reports, runs, floor].some((query) => query.isError) || unresolvedReportAssociation) && (
        <div className="workspace-partial" role="status">
          <RefreshCw aria-hidden="true" />Some owner panels or exact report-to-project associations are unavailable. Counts remain unavailable or visibly lower-bounded rather than becoming false zeroes.
        </div>
      )}
    </div>
  )
}
