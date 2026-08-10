import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, FolderGit2 } from "lucide-react"
import { Link, NavLink, useParams, useSearchParams } from "react-router"

import {
  Breadcrumbs,
  FactGrid,
  Identity,
  QueryState,
  StatusMark,
  TimeValue,
  WorkspaceBack,
} from "@/components/workspace-ui"
import { fetchFactoryFloor } from "@/lib/floor-api"
import { fetchReports, fetchRuns } from "@/lib/operations-api"
import { fetchProject } from "@/lib/projects-api"
import { fetchTasks } from "@/lib/task-api"
import { fetchTrackers } from "@/lib/trackers-api"
import {
  exactProjectRunIds,
  newestTimestamp,
  runProjectClaims,
  safeReturnPath,
  taskBelongsToProject,
} from "@/lib/workspace-data"

const tabs = ["overview", "work", "trackers", "reports", "sources"] as const
type ProjectTab = typeof tabs[number]

function isTab(value: string | undefined): value is ProjectTab {
  return tabs.includes(value as ProjectTab)
}

export function Component() {
  const { projectId = "", tab } = useParams()
  const [searchParams] = useSearchParams()
  const activeTab: ProjectTab = isTab(tab) ? tab : "overview"
  const floorReturn = safeReturnPath(searchParams.get("return"))
  const needsFloor = activeTab === "overview" || activeTab === "work" || activeTab === "reports"
  const needsRuns = activeTab === "overview" || activeTab === "work" || activeTab === "reports"
  const needsTasks = activeTab === "work"
  const needsTrackers = activeTab === "overview" || activeTab === "trackers"
  const needsReports = activeTab === "overview" || activeTab === "reports"
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: ({ signal }) => fetchProject(projectId, signal),
  })
  const runs = useQuery({ queryKey: ["runs"], queryFn: ({ signal }) => fetchRuns(signal), enabled: needsRuns })
  const tasks = useQuery({
    queryKey: ["tasks", "project-workspace", 100],
    queryFn: ({ signal }) => fetchTasks(undefined, 100, signal),
    enabled: needsTasks,
  })
  const trackers = useQuery({ queryKey: ["trackers"], queryFn: ({ signal }) => fetchTrackers(signal), enabled: needsTrackers })
  const reports = useQuery({ queryKey: ["reports"], queryFn: ({ signal }) => fetchReports(signal), enabled: needsReports })
  const floor = useQuery({ queryKey: ["factory-floor"], queryFn: ({ signal }) => fetchFactoryFloor(signal), enabled: needsFloor })

  if (project.isPending) return <QueryState kind="loading" message="Loading project" />
  if (project.isError) return <QueryState kind="error" message={project.error.message} retry={() => void project.refetch()} />

  const item = project.data.data.project
  const taskRows = tasks.data?.data.tasks.filter((task) => taskBelongsToProject(task, projectId)) ?? []
  const composedRows = floor.data?.data.rows.filter((row) => row.project.project_id === projectId) ?? []
  const composedRunIds = new Set(composedRows.flatMap((row) => row.supervision.run_id ? [row.supervision.run_id] : []))
  const listedTaskIds = new Set(taskRows.map((task) => task.id))
  const composedOnlyRows = composedRows.filter((row) => !listedTaskIds.has(row.implementation.task_id))
  const allRuns = runs.data?.data.runs ?? []
  const allTasks = tasks.data?.data.tasks ?? []
  const composedRunClaims = floor.data?.data.rows.flatMap((row) =>
    row.supervision.run_id && row.project.project_id
      ? [{ runId: row.supervision.run_id, projectId: row.project.project_id }]
      : [],
  ) ?? []
  const exactRunIds = exactProjectRunIds(allRuns, allTasks, composedRunClaims, projectId)
  const claimsByRun = new Map(allRuns.map((run) => {
    const composedProject = floor.data?.data.rows.find((row) => row.supervision.run_id === run.target_thread_id)?.project.project_id
    return [run.target_thread_id, runProjectClaims(run, allTasks, composedProject)]
  }))
  const disagreements = allRuns.filter((run) => new Set((claimsByRun.get(run.target_thread_id) ?? []).map((claim) => claim.projectId)).size > 1)
  const runRows = allRuns.filter((run) => exactRunIds.has(run.target_thread_id))
  const projectDisagreements = disagreements.filter((run) =>
    (claimsByRun.get(run.target_thread_id) ?? []).some((claim) => claim.projectId === projectId),
  )
  const conflictOnlyRows = projectDisagreements.filter((run) =>
    !runRows.some((candidate) => candidate.target_thread_id === run.target_thread_id),
  )
  const listedRunIds = new Set(allRuns.map((run) => run.target_thread_id))
  const composedOnlyRunRows = composedRows.filter((row) => row.supervision.run_id && exactRunIds.has(row.supervision.run_id) && !listedRunIds.has(row.supervision.run_id))
  const trackerRows = trackers.data?.data.trackers.filter((tracker) => tracker.project_id === projectId) ?? []
  const reportProject = (targetId: string): string | null => {
    const boundRun = runs.data?.data.runs.find((run) => run.target_thread_id === targetId)
    if (boundRun?.project_binding.status === "bound") return boundRun.project_binding.project_id
    const composed = floor.data?.data.rows.find((row) => row.supervision.run_id === targetId)
    if (composed?.project.project_id) return composed.project.project_id
    const targetTask = tasks.data?.data.tasks.find((task) => task.id === targetId)
    return targetTask?.project_binding.status === "bound" ? targetTask.project_binding.project_id : null
  }
  const reportRows = reports.data?.data.reports.filter((report) => reportProject(report.target_thread_id) === projectId) ?? []
  const unresolvedReportAssociation = reports.data?.data.reports.some((report) => reportProject(report.target_thread_id) === null) ?? false
  const outcomes = floor.data?.data.accepted_outcomes.filter((outcome) => outcome.project_id === projectId) ?? []
  const metricRows = floor.data?.data.metrics.filter((metric) =>
    ["active-tasks", "active-implementations", "open-items", "accepted-blocks"].includes(metric.key),
  ) ?? []
  const returnQuery = `?return=${encodeURIComponent(floorReturn)}`
  const taskSourcesPending = needsTasks && (tasks.isPending || floor.isPending)
  const runSourcesPending = needsRuns && (runs.isPending || (needsTasks && tasks.isPending) || floor.isPending)
  const reportsPending = reports.isPending || runs.isPending || floor.isPending
  const reportsUnavailable = reports.isError || (runs.isError && floor.isError)
  const reportsPartial = !reports.isError && (runs.isError || floor.isError || unresolvedReportAssociation)

  const overviewWorkPanel = (
    <section className="workspace-panel" aria-labelledby="project-current-work-heading">
      <div className="workspace-panel-heading"><h2 id="project-current-work-heading">Current work</h2><span>{floor.isPending ? "Loading" : floor.isError ? "Unavailable" : composedRows.length}</span></div>
      {floor.isPending ? <QueryState kind="loading" message="Loading current work" /> : floor.isError ? <QueryState kind="error" message={floor.error.message} retry={() => void floor.refetch()} /> : composedRows.length ? (
        <div className="workspace-record-list">
          {composedRows.map((row) => (
            <Link
              className="workspace-record"
              to={`${row.supervision.run_id ? `/runs/${encodeURIComponent(row.supervision.run_id)}` : `/tasks/${encodeURIComponent(row.implementation.task_id)}`}${returnQuery}`}
              key={row.id}
            >
              <div><strong>{row.implementation.name ?? "Unnamed task"}</strong><Identity value={row.implementation.task_id} /></div>
              <StatusMark status={row.disagreements.length || projectDisagreements.some((run) => run.target_thread_id === row.supervision.run_id) ? "degraded" : row.light.label} />
              <span>{projectDisagreements.some((run) => run.target_thread_id === row.supervision.run_id) ? "Project binding disagreement" : row.work.active_block ? `Block ${row.work.active_block}` : "Block unavailable"} · {row.issues.total} open</span>
              <TimeValue value={row.freshness.observed_at} />
            </Link>
          ))}
          {floor.data?.data.rows_truncated && <div className="workspace-bound">The Factory Floor row window is bounded.</div>}
        </div>
      ) : <QueryState kind="empty" message="No composed work is bound to this project" />}
    </section>
  )

  const workPanel = (
    <div className="workspace-split">
      <section className="workspace-panel" aria-labelledby="project-tasks-heading">
        <div className="workspace-panel-heading"><h2 id="project-tasks-heading">Tasks</h2><span>{taskSourcesPending ? "Loading" : tasks.isError && floor.isError ? "Unavailable" : new Set([...taskRows.map((task) => task.id), ...composedRows.map((row) => row.implementation.task_id)]).size}</span></div>
        {taskSourcesPending ? <QueryState kind="loading" message="Loading task sources" /> : tasks.isError && floor.isError ? <QueryState kind="error" message={tasks.error.message} retry={() => void tasks.refetch()} /> : taskRows.length || composedOnlyRows.length ? (
          <div className="workspace-record-list">
            {taskRows.map((task) => (
              <Link className="workspace-record" to={`/tasks/${encodeURIComponent(task.id)}${returnQuery}`} key={task.id}>
                <div><strong>{task.name ?? "Unnamed task"}</strong><Identity value={task.id} /></div>
                <StatusMark status={task.status.type} />
                <span>{task.cwd}</span>
                <TimeValue value={task.recency_at ?? task.updated_at} />
              </Link>
            ))}
            {composedOnlyRows.map((row) => (
              <Link className="workspace-record" to={`/tasks/${encodeURIComponent(row.implementation.task_id)}${returnQuery}`} key={`composed:${row.implementation.task_id}`}>
                <div><strong>{row.implementation.name ?? "Unnamed task"}</strong><Identity value={row.implementation.task_id} /></div>
                <StatusMark status={row.implementation.status_label} />
                <span>Factory Floor composition · task detail unavailable from current owner page</span>
                <TimeValue value={row.implementation.updated_at} />
              </Link>
            ))}
            {tasks.data?.data.next_cursor && <div className="workspace-bound">First 100 tasks · more are available from the owner</div>}
          </div>
        ) : <QueryState kind="empty" message="No exactly bound tasks" />}
        {(tasks.isError !== floor.isError) && <div className="workspace-bound">One task-association source is unavailable; visible tasks are exact lower-bound records.</div>}
      </section>

      <section className="workspace-panel" aria-labelledby="project-runs-heading">
        <div className="workspace-panel-heading"><h2 id="project-runs-heading">Runs</h2><span>{runSourcesPending ? "Loading" : runs.isError && floor.isError ? "Unavailable" : `${runRows.length + composedOnlyRunRows.length} exact${projectDisagreements.length ? ` · ${projectDisagreements.length} disagreement${projectDisagreements.length === 1 ? "" : "s"}` : ""}`}</span></div>
        {runSourcesPending ? <QueryState kind="loading" message="Loading run sources" /> : runs.isError && floor.isError ? <QueryState kind="error" message={runs.error.message} retry={() => void runs.refetch()} /> : runRows.length || composedOnlyRunRows.length || conflictOnlyRows.length ? (
          <div className="workspace-record-list">
            {runRows.map((run) => {
              const claims = claimsByRun.get(run.target_thread_id) ?? []
              const disagreement = new Set(claims.map((claim) => claim.projectId)).size > 1
              const association = disagreement
                ? `Binding disagreement · ${claims.map((claim) => `${claim.source}: ${claim.projectId}`).join(" · ")}`
                : run.project_binding.status === "bound"
                  ? "Run binding"
                  : composedRunIds.has(run.target_thread_id)
                    ? "Factory Floor composition"
                    : "Exact target task"
              return (
                <Link className="workspace-record" to={`/runs/${encodeURIComponent(run.target_thread_id)}${returnQuery}`} key={run.target_thread_id}>
                  <div><strong>{run.target_label}</strong><Identity value={run.target_thread_id} /></div>
                  <StatusMark status={disagreement ? "degraded" : run.light.label} />
                  <span>{association} · {run.counts ? `${run.counts.open_incidents + run.counts.open_decisions + run.counts.open_successor_transitions} open` : "Open state unavailable"}</span>
                  <TimeValue value={run.latest_activity?.timestamp ?? run.observed_at} />
                </Link>
              )
            })}
            {conflictOnlyRows.map((run) => (
              <Link className="workspace-record" to={`/runs/${encodeURIComponent(run.target_thread_id)}${returnQuery}`} key={`conflict:${run.target_thread_id}`}>
                <div><strong>{run.target_label}</strong><Identity value={run.target_thread_id} /></div>
                <StatusMark status="degraded" />
                <span>Binding disagreement · {(claimsByRun.get(run.target_thread_id) ?? []).map((claim) => `${claim.source}: ${claim.projectId}`).join(" · ")}</span>
                <TimeValue value={run.latest_activity?.timestamp ?? run.observed_at} />
              </Link>
            ))}
            {composedOnlyRunRows.map((row) => (
              <Link className="workspace-record" to={`/runs/${encodeURIComponent(row.supervision.run_id!)}${returnQuery}`} key={`composed-run:${row.supervision.run_id}`}>
                <div><strong>{row.implementation.name ?? "Unnamed run"}</strong><Identity value={row.supervision.run_id} /></div>
                <StatusMark status={row.light.label} />
                <span>Factory Floor composition · run list source unavailable</span>
                <TimeValue value={row.freshness.observed_at} />
              </Link>
            ))}
          </div>
        ) : <QueryState kind="empty" message="No exactly associated runs" />}
        {[runs, tasks, floor].some((query) => query.isError) && !(runs.isError && floor.isError) && <div className="workspace-bound">One association source is unavailable; visible runs are exact lower-bound records.</div>}
      </section>
    </div>
  )

  return (
    <div className="page-stack workspace-page project-workspace">
      <div className="workspace-context-bar">
        <Breadcrumbs>
          <Link to="/projects">Projects</Link><span>/</span><strong>{item.label}</strong>
        </Breadcrumbs>
        <WorkspaceBack to={floorReturn} />
      </div>

      <section className="workspace-identity-strip">
        <span className="project-mark"><FolderGit2 aria-hidden="true" /></span>
        <div><strong>{item.label}</strong><code title={item.root}>{item.root}</code></div>
        <StatusMark status={item.archived ? "archived" : item.discovery.status} />
        <Identity value={item.discovery.git.revision} />
      </section>

      <nav className="workspace-tabs" aria-label="Project views">
        {tabs.map((name) => (
          <NavLink
            key={name}
            end={name === "overview"}
            to={name === "overview" ? `/projects/${encodeURIComponent(projectId)}${returnQuery}` : `/projects/${encodeURIComponent(projectId)}/${name}${returnQuery}`}
          >{name[0].toUpperCase() + name.slice(1)}</NavLink>
        ))}
      </nav>

      {activeTab === "overview" && (
        <>
          <section className="workspace-summary-grid" aria-label="Project summary">
            <div><span>Tasks</span><strong>{floor.isPending ? "…" : floor.isError ? "—" : new Set(composedRows.map((row) => row.implementation.task_id)).size}</strong><small>Factory Floor composition</small></div>
            <div><span>Runs</span><strong>{runs.isPending || floor.isPending ? "…" : runs.isError && floor.isError ? "—" : exactRunIds.size}</strong><small>{projectDisagreements.length ? `${projectDisagreements.length} binding disagreement${projectDisagreements.length === 1 ? "" : "s"} excluded` : "Exact canonical/composed IDs"}</small></div>
            <div><span>Trackers</span><strong>{trackers.isPending ? "…" : trackers.isError ? "—" : trackerRows.length}</strong><small>Catalog discovery</small></div>
            <div><span>Reports</span><strong>{reportsPending ? "…" : reportsUnavailable ? "—" : reportRows.length}</strong><small>{reportsPartial ? "Partial exact associations" : "Exact run target"}</small></div>
          </section>
          {overviewWorkPanel}
          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Recent outcomes</h2><span>{floor.isError ? "Unavailable" : outcomes.length}</span></div>
              {floor.isPending ? <QueryState kind="loading" message="Loading outcomes" /> : floor.isError ? <QueryState kind="error" message={floor.error.message} /> : outcomes.length ? (
                <div className="workspace-record-list">
                  {outcomes.slice(0, 8).map((outcome) => (
                    <article className="workspace-record" key={outcome.id}>
                      <div><strong>Block {outcome.block} · {outcome.title}</strong><span>{outcome.currentness}</span></div>
                      <StatusMark status={outcome.status} />
                      <span>{outcome.tracker_title}</span>
                      <TimeValue value={outcome.observed_at} />
                    </article>
                  ))}
                </div>
              ) : <QueryState kind="empty" message="No accepted outcome recorded" />}
            </section>
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Metric snapshot</h2><span>Factory scope</span></div>
              {floor.isPending ? <QueryState kind="loading" message="Loading metric snapshot" /> : floor.isError ? <QueryState kind="error" message={floor.error.message} /> : (
                <div className="workspace-metrics">
                  {metricRows.map((metric) => <div key={metric.key}><span>{metric.label}</span><strong>{metric.available ? metric.value : "—"}</strong><small>{metric.coverage}</small></div>)}
                </div>
              )}
            </section>
          </div>
          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Source state</h2><StatusMark status={item.discovery.coverage} /></div>
            <FactGrid facts={[
              ["Last activity", <TimeValue value={newestTimestamp(composedRows.map((row) => row.freshness.observed_at))} />],
              ["Git branch", item.discovery.git.branch ?? "Unavailable"],
              ["Tracker discovery", item.discovery.trackers.status],
              ["Task association", item.discovery.source_families.codex_tasks.reason ?? item.discovery.source_families.codex_tasks.status],
              ["Supervision association", item.discovery.source_families.supervision.reason ?? item.discovery.source_families.supervision.status],
            ]} />
          </section>
        </>
      )}

      {activeTab === "work" && workPanel}

      {activeTab === "trackers" && (
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Trackers</h2><span>{trackers.isPending ? "Loading" : trackers.isError ? "Unavailable" : trackerRows.length}</span></div>
          {trackers.isPending ? <QueryState kind="loading" message="Loading trackers" /> : trackers.isError ? <QueryState kind="error" message={trackers.error.message} /> : trackerRows.length ? (
            <div className="workspace-record-list">
              {trackerRows.map((tracker) => (
                <article className="workspace-record" key={tracker.id}>
                  <div><strong>{tracker.status === "available" ? tracker.title : tracker.relative_path}</strong><Identity value={tracker.id} /></div>
                  <StatusMark status={tracker.status === "available" ? tracker.tracker_status : tracker.status} />
                  <span>{tracker.status === "available" ? `${tracker.counts.accepted} accepted · ${tracker.counts.open} open` : tracker.error.message}</span>
                  <TimeValue value={tracker.observed_at} />
                </article>
              ))}
            </div>
          ) : <QueryState kind="empty" message="No tracker discovered" />}
        </section>
      )}

      {activeTab === "reports" && (
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Reports</h2><span>{reportsPending ? "Loading" : reportsUnavailable ? "Unavailable" : reportRows.length}</span></div>
          {reportsPending ? <QueryState kind="loading" message="Loading exact report associations" /> : reportsUnavailable ? <QueryState kind="error" message={reports.isError ? reports.error.message : "Run association sources are unavailable"} /> : reportRows.length ? (
            <div className="workspace-record-list">
              {reportRows.map((report) => (
                <article className="workspace-record" key={report.id}>
                  <div><strong>{report.family} · {report.stage}</strong><Identity value={report.id} /></div>
                  <StatusMark status={report.status} />
                  <span>{report.disposition ?? report.error?.message ?? `${report.members.length} verified members`}</span>
                  <Identity value={report.target_thread_id} />
                </article>
              ))}
            </div>
          ) : <QueryState kind="empty" message="No report associated with an exact run" />}
          {reportsPartial && <div className="workspace-bound">One run-association source is unavailable; the visible report count is a lower bound.</div>}
        </section>
      )}

      {activeTab === "sources" && (
        <div className="workspace-split">
          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Repository</h2><StatusMark status={item.discovery.status} /></div>
            <FactGrid facts={[
              ["Project ID", <Identity value={item.id} />],
              ["Root", <code>{item.root}</code>],
              ["Branch", item.discovery.git.branch ?? "Unavailable"],
              ["Revision", <Identity value={item.discovery.git.revision} />],
              ["Observed", <TimeValue value={item.observed_at} />],
            ]} />
          </section>
          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Coverage</h2><StatusMark status={item.discovery.coverage} /></div>
            <div className="workspace-source-list">
              <div><span>Tracker discovery</span><StatusMark status={item.discovery.trackers.status} /></div>
              <div><span>Supervision</span><StatusMark status={item.discovery.source_families.supervision.status} /></div>
              <div><span>Codex tasks</span><StatusMark status={item.discovery.source_families.codex_tasks.status} /></div>
              {item.discovery.limitations.map((limitation) => <p key={limitation}>{limitation}</p>)}
              {item.discovery.errors.map((error) => <p className="workspace-error-text" key={error.code}><AlertTriangle aria-hidden="true" />{error.message}</p>)}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
