import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, GitBranch, TerminalSquare } from "lucide-react"
import { useState } from "react"
import { Link, useParams, useSearchParams } from "react-router"

import {
  BoundedSummary,
  Breadcrumbs,
  FactGrid,
  Identity,
  QueryState,
  StatusMark,
  TimeValue,
  WorkspaceBack,
} from "@/components/workspace-ui"
import { Button } from "@/components/ui/button"
import { fetchRuns } from "@/lib/operations-api"
import { fetchTask, fetchTaskIntegration, fetchTasks } from "@/lib/task-api"
import { fetchTrackers } from "@/lib/trackers-api"
import { newestPage, safeGitOrigin, safeReturnPath, safeTaskItemSummary } from "@/lib/workspace-data"

export function Component() {
  const { taskId = "" } = useParams()
  const [searchParams] = useSearchParams()
  const [turnPage, setTurnPage] = useState(0)
  const floorReturn = safeReturnPath(searchParams.get("return"))
  const detail = useQuery({
    queryKey: ["task", taskId, true],
    queryFn: ({ signal }) => fetchTask(taskId, true, signal),
    retry: false,
  })
  const listing = useQuery({
    queryKey: ["tasks", "task-workspace", 100],
    queryFn: ({ signal }) => fetchTasks(undefined, 100, signal),
  })
  const integration = useQuery({
    queryKey: ["task-integration"],
    queryFn: ({ signal }) => fetchTaskIntegration(signal),
    retry: false,
  })
  const runs = useQuery({ queryKey: ["runs"], queryFn: ({ signal }) => fetchRuns(signal) })
  const trackers = useQuery({ queryKey: ["trackers"], queryFn: ({ signal }) => fetchTrackers(signal) })

  if (detail.isPending && listing.isPending) return <QueryState kind="loading" message="Loading task" />

  const task = detail.data?.data.task ?? listing.data?.data.tasks.find((candidate) => candidate.id === taskId)
  const taskIntegration = detail.data?.data.integration ?? integration.data?.data.integration ?? listing.data?.data.integration
  const pending = detail.data?.data.pending_requests
    ?? listing.data?.data.pending_requests.filter((request) => request.task_id === taskId)
    ?? []
  const run = runs.data?.data.runs.find((candidate) => candidate.target_thread_id === taskId)
  const projectId = task?.project_binding.project_id
  const trackerRows = trackers.data?.data.trackers.filter((tracker) => tracker.project_id === projectId) ?? []
  const backQuery = `?return=${encodeURIComponent(floorReturn)}`

  if (!task && detail.isError) {
    return (
      <div className="page-stack workspace-page">
        <div className="workspace-context-bar"><Breadcrumbs><Link to="/projects">Projects</Link><span>/</span><strong>Task</strong></Breadcrumbs><WorkspaceBack to={floorReturn} /></div>
        {taskIntegration && (
          <section className="workspace-identity-strip">
            <TerminalSquare aria-hidden="true" /><div><strong>Codex App Server</strong><Identity value={taskId} /></div><StatusMark status={taskIntegration.protocol_status} /><TimeValue value={taskIntegration.observed_at} />
          </section>
        )}
        <QueryState kind="error" message={detail.error.message} retry={() => void detail.refetch()} />
      </div>
    )
  }
  if (!task) return <QueryState kind="empty" message={listing.data?.data.next_cursor ? "Task is outside the bounded first page" : "Task not found"} />
  const turnWindow = newestPage(task.turns, turnPage, 5)

  return (
    <div className="page-stack workspace-page task-workspace">
      <div className="workspace-context-bar">
        <Breadcrumbs>
          <Link to="/projects">Projects</Link><span>/</span>
          {projectId ? <Link to={`/projects/${encodeURIComponent(projectId)}${backQuery}`}>{projectId}</Link> : <span>Unregistered</span>}
          <span>/</span><strong>Task</strong>
        </Breadcrumbs>
        <WorkspaceBack to={floorReturn} />
      </div>

      <section className="workspace-identity-strip">
        <TerminalSquare aria-hidden="true" />
        <div><strong>{task.name ?? "Unnamed task"}</strong><Identity value={task.id} /></div>
        <StatusMark status={task.status.type} />
        <TimeValue value={task.recency_at ?? task.updated_at} />
      </section>

      {detail.isError && (
        <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />Turn detail unavailable: {detail.error.message}</div>
      )}

      <div className="workspace-split">
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Task</h2><StatusMark status={task.status.type} /></div>
          <FactGrid facts={[
            ["Task ID", <Identity value={task.id} />],
            ["Session", <Identity value={task.session_id} />],
            ["Project", projectId ?? `${task.project_binding.status} · no exact project`],
            ["Working directory", <code>{task.cwd}</code>],
            ["Source", task.source],
            ["CLI", task.cli_version],
            ["Updated", <TimeValue value={task.updated_at} />],
            ["Active flags", task.status.active_flags.join(", ") || "None"],
          ]} />
        </section>
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>App Server</h2><StatusMark status={taskIntegration?.protocol_status} /></div>
          {taskIntegration ? <FactGrid facts={[
            ["Adapter", taskIntegration.status],
            ["Protocol", taskIntegration.protocol_status],
            ["Child", taskIntegration.transport.child_running ? "Running" : "Stopped"],
            ["Version", `${taskIntegration.cli.version ?? "Unavailable"} / expected ${taskIntegration.cli.expected_version ?? "Unavailable"}`],
            ["Schema", taskIntegration.schema.semantic_manifest_sha256 === taskIntegration.schema.expected_semantic_manifest_sha256 ? "Compatible" : "Mismatch or unavailable"],
            ["Generation", taskIntegration.connection_generation],
            ["Reconnect failures", taskIntegration.reconnect.failure_count],
            ["Last error", taskIntegration.last_error?.message ?? "None"],
          ]} /> : <QueryState kind={integration.isError ? "error" : "loading"} message={integration.isError ? integration.error.message : "Loading App Server state"} />}
        </section>
      </div>

      <div className="workspace-split">
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Associations</h2><span>Exact IDs only</span></div>
          <div className="workspace-record-list">
            {run ? (
              <Link className="workspace-record" to={`/runs/${encodeURIComponent(run.target_thread_id)}${backQuery}`}>
                <div><strong>Supervision run</strong><span>{run.target_label}</span></div><StatusMark status={run.light.label} /><Identity value={run.target_thread_id} /><span>Exact target ID</span>
              </Link>
            ) : <div className="workspace-record"><div><strong>Supervision run</strong><span>No exact target match</span></div><StatusMark status={runs.isError ? "unavailable" : "unassigned"} /><span>Not inferred from cwd or label</span></div>}
            {trackerRows.length ? trackerRows.map((tracker) => (
              <article className="workspace-record" key={tracker.id}>
                <div><strong>{tracker.status === "available" ? tracker.title : tracker.relative_path}</strong><Identity value={tracker.id} /></div>
                <StatusMark status="project candidate" />
                <span>No canonical task-to-tracker binding</span>
                <span>{tracker.project_id}</span>
              </article>
            )) : <div className="workspace-record"><div><strong>Tracker</strong><span>No project candidate</span></div><StatusMark status={trackers.isError ? "unavailable" : "unassigned"} /></div>}
          </div>
        </section>
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Git</h2><GitBranch aria-hidden="true" /></div>
          <FactGrid facts={[
            ["Branch", task.git.branch ?? "Unavailable"],
            ["Revision", <Identity value={task.git.revision} />],
            ["Origin", safeGitOrigin(task.git.origin)],
            ["Parent task", <Identity value={task.parent_task_id} />],
            ["Forked from", <Identity value={task.forked_from_id} />],
          ]} />
        </section>
      </div>

      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>Pending requests</h2><span>{pending.length}</span></div>
        {pending.length ? <div className="workspace-record-list">{pending.map((request) => (
          <details className="task-turn" key={request.id}>
            <summary><span>{request.family.replaceAll("_", " ")}</span><StatusMark status={request.status} /><Identity value={request.id} /><TimeValue value={request.received_at} /></summary>
            <div className="task-request-detail">
              {request.family === "command_approval" && <><span>{safeTaskItemSummary("commandExecution", request.details.command)}</span><span>{request.details.cwd ?? "Working directory unavailable"}</span><span>Approval reason retained by the owner; command arguments are withheld here.</span></>}
              {request.family === "file_approval" && <><BoundedSummary value={request.details.grant_root} limit={180} /><span>{request.details.reason ?? "Reason unavailable"}</span></>}
              {request.family === "user_input" && <span>{request.details.questions.length} bounded question{request.details.questions.length === 1 ? "" : "s"}</span>}
            </div>
          </details>
        ))}</div> : <QueryState kind="empty" message="No pending approval or input" />}
      </section>

      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>Turns</h2><span>{turnWindow.start}–{turnWindow.end} of {task.turns.length}{task.turns_truncated ? "+ owner window" : ""}</span></div>
        {task.turns.length ? (
          <div className="task-turns">
            {turnWindow.items.map((turn) => (
              <details className="task-turn" key={turn.id}>
                <summary>
                  <Identity value={turn.id} /><StatusMark status={turn.status} />
                  <span>{turn.items.length} item{turn.items.length === 1 ? "" : "s"}{turn.items_truncated ? " · truncated" : ""}</span>
                  <TimeValue value={turn.started_at} />
                </summary>
                <div className="task-items">
                  {turn.items.map((item) => (
                    <article key={item.id}>
                      <div><strong>{item.type}</strong><Identity value={item.id} /></div>
                      <StatusMark status={item.status} />
                      <BoundedSummary value={safeTaskItemSummary(item.type, item.summary)} limit={280} />
                    </article>
                  ))}
                  {turn.items_truncated && <div className="workspace-bound">Additional items were omitted by the owner-provided bounded view.</div>}
                  {turn.error && <div className="workspace-error-text">Turn error recorded by the App Server; raw detail is withheld.</div>}
                </div>
              </details>
            ))}
          </div>
        ) : <QueryState kind="empty" message={detail.isError ? "Turn source unavailable" : "No turns returned"} />}
        {(turnWindow.hasOlder || turnWindow.hasNewer) && (
          <nav className="workspace-pagination" aria-label="Turn pages">
            <Button variant="outline" size="compact" disabled={!turnWindow.hasOlder} onClick={() => setTurnPage(turnWindow.page + 1)}>Older</Button>
            <span>{turnWindow.start}–{turnWindow.end} of {turnWindow.total}</span>
            <Button variant="outline" size="compact" disabled={!turnWindow.hasNewer} onClick={() => setTurnPage(Math.max(0, turnWindow.page - 1))}>Newer</Button>
          </nav>
        )}
        {task.turns_truncated && <div className="workspace-bound">Earlier turns were not preloaded. This view is not a transcript archive.</div>}
      </section>

      {taskIntegration && (
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Capabilities</h2><span>Read only</span></div>
          <div className="workspace-source-list">
            {taskIntegration.features.map((feature) => (
              <div key={feature.capability}><span>{feature.capability}</span><StatusMark status={feature.status} /><small>{feature.exposure}{feature.reason ? ` · ${feature.reason}` : ""}</small></div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
