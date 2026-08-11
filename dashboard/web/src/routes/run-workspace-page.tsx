import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ArrowRight, Filter, ShieldCheck } from "lucide-react"
import { type ReactNode, useState } from "react"
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
import { RunSupervisionActions } from "@/features/admin/factory-workflow-actions"
import { fetchRun, type RunDetail } from "@/lib/operations-api"
import { fetchTask, fetchTasks } from "@/lib/task-api"
import {
  eventsForMission,
  missionEntityIds,
  newestPage,
  runProjectClaims,
  safeReturnPath,
  shortIdentity,
} from "@/lib/workspace-data"

type RunEvent = RunDetail["timeline"][number]

function eventLabel(event: RunEvent): string {
  return event.summary ?? event.action ?? event.resolution ?? event.status ?? "No summary recorded"
}

function policyLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase())
}

function eventMatches(
  event: RunEvent,
  filters: { kind: string; severity: string; block: string; role: string },
): boolean {
  return (filters.kind === "all" || event.kind === filters.kind)
    && (filters.severity === "all" || event.severity === filters.severity)
    && (filters.block === "all" || event.active_block === filters.block)
    && (filters.role === "all" || (filters.role === "unattributed" && event.actor.status === "unavailable"))
}

function latestMissionEntityEvents(
  events: readonly RunEvent[],
  field: "incident_id" | "decision_id" | "transition_id",
): RunEvent[] {
  const latest = new Map<string, RunEvent>()
  events.forEach((event) => {
    const id = event[field]
    if (id) latest.set(id, event)
  })
  return [...latest.values()]
}

function RunWorkspace({ supervisorOnly = false }: { supervisorOnly?: boolean }) {
  const { targetId = "" } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [kindFilter, setKindFilter] = useState("all")
  const [severityFilter, setSeverityFilter] = useState("all")
  const [blockFilter, setBlockFilter] = useState("all")
  const [roleFilter, setRoleFilter] = useState("all")
  const [eventPage, setEventPage] = useState(0)
  const floorReturn = safeReturnPath(searchParams.get("return"))
  const requestedRoot = searchParams.get("mission")
  const runQuery = useQuery({
    queryKey: ["run", targetId],
    queryFn: ({ signal }) => fetchRun(targetId, signal),
  })
  const requestedSegment = runQuery.data?.data.run.mission_segments.find(
    (candidate) => candidate.mission_root === requestedRoot,
  )
  const allowCurrentSources = requestedRoot === null || requestedSegment?.posture === "current"
  const taskQuery = useQuery({
    queryKey: ["task", targetId, false],
    queryFn: ({ signal }) => fetchTask(targetId, false, signal),
    retry: false,
    enabled: allowCurrentSources,
  })
  const roleTasks = useQuery({
    queryKey: ["tasks", "run-roles", 100],
    queryFn: ({ signal }) => fetchTasks(undefined, 100, signal),
    enabled: allowCurrentSources,
  })

  if (runQuery.isPending) return <QueryState kind="loading" message="Loading run" />
  if (runQuery.isError) return <QueryState kind="error" message={runQuery.error.message} retry={() => void runQuery.refetch()} />

  const run = runQuery.data.data.run
  if (requestedRoot !== null && !run.mission_segments.some((candidate) => candidate.mission_root === requestedRoot)) {
    return <QueryState kind="error" message="Requested mission is not present in this run's canonical history" />
  }
  const currentRoot = run.current_mission?.root ?? run.mission_segments.find((segment) => segment.posture === "current")?.mission_root
  const segment = run.mission_segments.find((candidate) => candidate.mission_root === requestedRoot)
    ?? run.mission_segments.find((candidate) => candidate.mission_root === currentRoot)
    ?? run.mission_segments[0]
  const selectedRoot = segment?.mission_root ?? currentRoot ?? "unbound"
  const isCurrent = segment?.posture === "current" && selectedRoot === currentRoot
  const missionEvents = eventsForMission(run.timeline, selectedRoot)
  const missionConclusions = eventsForMission(run.conclusions, selectedRoot)
  const projectClaims = isCurrent
    ? runProjectClaims(run, taskQuery.data?.data.task ? [taskQuery.data.data.task] : [])
    : []
  const projectBindingConflict = new Set(projectClaims.map((claim) => claim.projectId)).size > 1
  const breadcrumbProjectId = projectBindingConflict
    ? null
    : run.project_binding.status === "bound"
      ? run.project_binding.project_id
      : taskQuery.data?.data.task.project_binding.status === "bound"
        ? taskQuery.data.data.task.project_binding.project_id
        : null
  const workspaceBindingIntegrity = projectBindingConflict
    ? "degraded"
    : run.topology?.binding_integrity ?? "unavailable"
  const projectClaimSummary = projectClaims.length
    ? projectClaims.map((claim) => `${claim.source}: ${claim.projectId}`).join(" · ")
    : "No exact project claim"
  const incidentIds = missionEntityIds(missionEvents, "incident_id")
  const decisionIds = missionEntityIds(missionEvents, "decision_id")
  const transitionIds = missionEntityIds(missionEvents, "transition_id")
  const missionIncidents = isCurrent
    ? run.incidents.filter((incident) => incidentIds.has(incident.incident_id))
    : []
  const missionDecisions = isCurrent
    ? run.decisions.filter((decision) => decisionIds.has(decision.decision_id))
    : []
  const missionTransitions = isCurrent
    ? run.successor_transitions.filter((transition) => transitionIds.has(transition.transition_id))
    : []
  const historicalIncidentEvents = isCurrent ? [] : latestMissionEntityEvents(missionEvents, "incident_id")
  const historicalDecisionEvents = isCurrent ? [] : latestMissionEntityEvents(missionEvents, "decision_id")
  const historicalTransitionEvents = isCurrent ? [] : latestMissionEntityEvents(missionEvents, "transition_id")
  const incidentCount = isCurrent ? missionIncidents.length : segment?.incident_count ?? historicalIncidentEvents.length
  const openIncidentCount = isCurrent ? missionIncidents.filter((item) => item.open).length : segment?.open_incident_count ?? 0
  const decisionCount = isCurrent ? missionDecisions.length : historicalDecisionEvents.length
  const transitionCount = isCurrent ? missionTransitions.length : historicalTransitionEvents.length
  const roleTaskById = new Map((roleTasks.data?.data.tasks ?? []).map((task) => [task.id, task]))
  const kinds = [...new Set(missionEvents.flatMap((event) => event.kind ? [event.kind] : []))].sort()
  const severities = [...new Set(missionEvents.flatMap((event) => event.severity ? [event.severity] : []))].sort()
  const blocks = [...new Set(missionEvents.flatMap((event) => event.active_block ? [event.active_block] : []))].sort()
  const filteredEvents = missionEvents.filter((event) => eventMatches(event, {
    kind: kindFilter,
    severity: severityFilter,
    block: blockFilter,
    role: roleFilter,
  }))
  const eventWindow = newestPage(filteredEvents, eventPage, 50)
  const currentPolicyHistory = run.policy_history.filter((entry) => entry.mission_root === selectedRoot)
  const checkpointEvent = [...missionEvents].reverse().find((event) => event.active_block || event.checkpoint)
  const routeGateEvent = [...missionEvents].reverse().find((event) =>
    event.kind?.includes("route") || event.category?.includes("route"),
  )
  const recentSupervisorEvents = [...missionEvents].reverse().filter((event) =>
    ["check", "steer", "escalation", "resolution", "incident", "meta-review"].includes(event.kind ?? ""),
  ).slice(0, 20)
  const backQuery = `?return=${encodeURIComponent(floorReturn)}`

  const chooseMission = (root: string) => {
    const next = new URLSearchParams(searchParams)
    next.set("mission", root)
    setSearchParams(next)
    setKindFilter("all")
    setSeverityFilter("all")
    setBlockFilter("all")
    setRoleFilter("all")
    setEventPage(0)
  }

  const currentSupervisorPanel = (
    <>
      <section className="workspace-panel supervisor-identity-panel">
        <div className="workspace-panel-heading">
          <h2>Supervisor group</h2>
          <StatusMark status={workspaceBindingIntegrity} />
        </div>
        {run.topology ? (
          <>
            <FactGrid facts={[
              ["Group", <Identity value={run.topology.supervisor_group_id} />],
              ["Target", <Identity value={run.topology.implementation.thread_id} />],
              ["Mission", <Identity value={selectedRoot} />],
              ["Policy", isCurrent ? <Identity value={run.policy?.sha256} /> : <Identity value={segment?.policy_sha256s.at(-1)} />],
              ["Project binding", projectBindingConflict ? projectClaimSummary : `${run.topology.project_binding.status}${run.topology.project_binding.project_id ? ` · ${run.topology.project_binding.project_id}` : ""}`],
              ["Tracker binding", run.topology.tracker_binding.reason],
              ["Last check", <TimeValue value={run.last_check?.timestamp} />],
              ["Next check", "Unavailable from automation owner"],
              ["Route gate", routeGateEvent ? `${routeGateEvent.status ?? routeGateEvent.kind} · ${routeGateEvent.record_id}` : "No mission-scoped route-gate record"],
            ]} />
            {run.topology.anomalies.length > 0 && (
              <div className="workspace-warning-list">
                {run.topology.anomalies.map((anomaly) => <span key={anomaly}><AlertTriangle aria-hidden="true" />{anomaly}</span>)}
              </div>
            )}
          </>
        ) : <QueryState kind="empty" message="Supervisor topology unavailable" />}
      </section>

      {run.topology && (
        <section className="workspace-panel">
          <div className="workspace-panel-heading"><h2>Roles &amp; routes</h2><span>{run.topology.roles.length}</span></div>
          <div className="role-grid">
            {run.topology.roles.map((role) => {
              const liveTask = role.thread_id ? roleTaskById.get(role.thread_id) : undefined
              return (
                <article className="role-card" key={`${role.role}:${role.thread_id}`}>
                  <div className="role-card-heading"><strong>{role.label}</strong><StatusMark status={role.binding_status} /></div>
                  <span>{role.role}</span>
                  {role.thread_id ? (
                    <Link to={`/tasks/${encodeURIComponent(role.thread_id)}${backQuery}`}><Identity value={role.thread_id} /></Link>
                  ) : <span>Task unavailable</span>}
                  <dl>
                    <div><dt>Live task</dt><dd>{roleTasks.isError ? "Unavailable" : liveTask ? <StatusMark status={liveTask.status.type} /> : roleTasks.data?.data.next_cursor ? "Outside bounded first page" : role.task_state.reason}</dd></div>
                    <div><dt>Recent action</dt><dd>{role.last_activity?.summary ?? role.activity_attribution.reason}</dd></div>
                    <div><dt>Conclusion</dt><dd>Role attribution unavailable from canonical events</dd></div>
                  </dl>
                  {role.automation ? (
                    <div className="automation-card">
                      <strong>{role.automation.name ?? role.automation.id}</strong>
                      <StatusMark status={role.automation.owner_status ?? role.automation.status} />
                      <span>{role.automation.rrule ?? "Cadence unavailable"}</span>
                      <span>Next: unavailable from owner</span>
                    </div>
                  ) : <span className="workspace-muted">No automation bound</span>}
                </article>
              )
            })}
          </div>
          {roleTasks.data?.data.next_cursor && <div className="workspace-bound">Role task matching is bounded to the first 100 owner rows.</div>}
        </section>
      )}

      <section className="workspace-panel">
        <div className="workspace-panel-heading">
          <h2>Policy</h2>
          <span>{isCurrent && run.policy ? `${run.policy.automation_reconciliation.filter((row) => row.state === "reconciled").length}/${run.policy.automation_reconciliation.length} schedules reconciled` : "Historical hashes only"}</span>
        </div>
        {isCurrent && run.policy ? (
          <>
            <FactGrid facts={[
              ["Version", run.policy.version],
              ["SHA-256", <Identity value={run.policy.sha256} />],
              ["Source", <code>{run.policy.source_path}</code>],
              ["Mission records", currentPolicyHistory.length],
              ...Object.entries(run.policy.adjustable).map(([field, value]) => [
                policyLabel(field),
                value ?? "Unavailable",
              ] as [string, ReactNode]),
            ]} />
            {run.policy.automation_reconciliation.length > 0 && (
              <div className="policy-reconciliation-list" aria-label="Automation reconciliation">
                {run.policy.automation_reconciliation.map((row) => (
                  <div key={`${row.field}:${row.automation_id}`}>
                    <StatusMark status={row.state} />
                    <strong>{policyLabel(row.field)}</strong>
                    <span>{row.mode ? `${row.role} · ${row.mode}` : row.role}</span>
                    <Identity value={row.automation_id} />
                    <code>{row.actual_rrule ?? "Unavailable"}</code>
                    {row.actual_rrule !== row.expected_rrule && <small>Expected {row.expected_rrule ?? "unavailable"}</small>}
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <QueryState kind="empty" message={`Historical policy body is unavailable; ${segment?.policy_sha256s.length ?? 0} exact policy hash${segment?.policy_sha256s.length === 1 ? "" : "es"} retained`} />
        )}
      </section>

      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>Operating history</h2><span>Derived</span></div>
        {!isCurrent ? <QueryState kind="empty" message="Run-level derived posture history is not carried into a predecessor mission" /> : run.operating_history.length ? (
          <ol className="operating-timeline">
            {run.operating_history.map((entry, index) => (
              <li key={`${entry.record.record_id}:${index}`}>
                <span className={`operating-transition posture-${entry.to}`}>{entry.from}<ArrowRight aria-hidden="true" />{entry.to}</span>
                <div><strong>{entry.trigger}</strong><BoundedSummary value={entry.record.summary} /></div>
                <a href={`#${entry.record.record_id}`}><Identity value={entry.record.record_id} /></a>
                <TimeValue value={entry.record.timestamp} />
              </li>
            ))}
          </ol>
        ) : <QueryState kind="empty" message="No derived posture transition recorded" />}
        <div className="workspace-bound">Derived from canonical history; gaps remain unknown and never imply lifecycle completion.</div>
      </section>
    </>
  )

  const historicalSupervisorPanel = (
    <>
      <section className="workspace-panel supervisor-identity-panel">
        <div className="workspace-panel-heading"><h2>Supervisor group</h2><StatusMark status="unavailable" /></div>
        <FactGrid facts={[
          ["Target", <Identity value={run.target_thread_id} />],
          ["Mission", <Identity value={selectedRoot} />],
          ["Policy hashes", segment?.policy_sha256s.map((hash) => shortIdentity(hash)).join(", ") || "Unavailable"],
          ["Group", "Unavailable from mission-scoped records"],
          ["Project binding", "Not carried from the current run"],
          ["Tracker binding", "Not carried from the current run"],
          ["Roles", "Unavailable from mission-scoped records"],
          ["Automations", "Unavailable from mission-scoped records"],
        ]} />
        <div className="workspace-bound">Current topology, role tasks, automations, checks, and bindings are intentionally suppressed at the succession boundary.</div>
      </section>
      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>Policy</h2><span>Historical hashes only</span></div>
        <FactGrid facts={[
          ["Mission records", currentPolicyHistory.length],
          ["Policy versions", segment?.policy_sha256s.length ?? 0],
          ["Latest exact hash", <Identity value={segment?.policy_sha256s.at(-1)} />],
          ["Policy body", "Unavailable for this historical version"],
        ]} />
      </section>
      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>Operating history</h2><span>Unavailable</span></div>
        <QueryState kind="empty" message="Run-level derived posture history is not carried into a predecessor mission" />
      </section>
    </>
  )

  const supervisorPanel = isCurrent ? currentSupervisorPanel : historicalSupervisorPanel

  const supervisorActivityPanel = (
    <>
      <section className="workspace-summary-grid" aria-label={isCurrent ? "Supervisor state" : "Historical mission records"}>
        <div><span>Incidents</span><strong>{incidentCount}</strong><small>{openIncidentCount} open</small></div>
        <div><span>Decisions</span><strong>{decisionCount}</strong><small>{isCurrent ? `${missionDecisions.filter((item) => item.open).length} open` : "Open posture unavailable"}</small></div>
        <div><span>Transitions</span><strong>{transitionCount}</strong><small>{isCurrent ? `${missionTransitions.filter((item) => item.open).length} open` : "Open posture unavailable"}</small></div>
        <div><span>Conclusions</span><strong>{missionConclusions.length}</strong><small>Role attribution unavailable</small></div>
      </section>
      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>Recent supervision activity</h2><span>{recentSupervisorEvents.length} of {missionEvents.length}</span></div>
        {recentSupervisorEvents.length ? <ol className="event-timeline">{recentSupervisorEvents.map((event, index) => (
          <li id={event.record_id ?? `supervisor-event-${index}`} key={`${event.record_id}:${index}`} tabIndex={-1}>
            <div><Identity value={event.record_id} /><StatusMark status={event.status ?? event.kind} /></div>
            <strong>{event.kind ?? "Event"}{event.active_block ? ` · Block ${event.active_block}` : ""}</strong>
            <BoundedSummary value={eventLabel(event)} limit={360} />
            <span>{event.severity ?? "Severity unavailable"} · {event.category ?? "Category unavailable"} · Role unavailable</span>
            <TimeValue value={event.timestamp} />
          </li>
        ))}</ol> : <QueryState kind="empty" message="No recent supervision activity in this mission" />}
        {run.timeline_truncated && <div className="workspace-bound">The maintained owner returned a bounded mission timeline.</div>}
      </section>
      <section className="workspace-panel">
        <div className="workspace-panel-heading"><h2>{isCurrent ? "Current issues & conclusions" : "Mission issues & conclusions"}</h2><span>{isCurrent ? `${missionIncidents.filter((item) => item.open).length + missionDecisions.filter((item) => item.open).length + missionTransitions.filter((item) => item.open).length} open` : `${openIncidentCount} incident open · other posture unavailable`}</span></div>
        <div className="workspace-record-list">
          {missionIncidents.filter((item) => item.open).map((item) => <article className="workspace-record" key={item.incident_id}><div><strong>{item.incident_id}</strong><BoundedSummary value={item.head.summary} /></div><StatusMark status="open" /><span>{item.head.severity ?? "Severity unavailable"}</span><TimeValue value={item.head.timestamp} /></article>)}
          {missionDecisions.filter((item) => item.open).map((item) => <article className="workspace-record" key={item.decision_id}><div><strong>{item.decision_id}</strong><BoundedSummary value={item.head.summary} /></div><StatusMark status="open" /><span>Safe frontier: {item.safe_frontier ?? "Unavailable"}</span><TimeValue value={item.head.timestamp} /></article>)}
          {missionTransitions.filter((item) => item.open).map((item) => <article className="workspace-record" key={item.transition_id}><div><strong>{item.transition_id}</strong><BoundedSummary value={item.head.summary} /></div><StatusMark status="open" /><span>{item.phase ?? "Phase unavailable"}</span><TimeValue value={item.head.timestamp} /></article>)}
          {!isCurrent && [...historicalIncidentEvents, ...historicalDecisionEvents, ...historicalTransitionEvents].map((item, index) => <article className="workspace-record" key={`${item.record_id}:historical-issue:${index}`}><div><strong>{item.incident_id ?? item.decision_id ?? item.transition_id ?? "Issue record"}</strong><BoundedSummary value={eventLabel(item)} /></div><StatusMark status={item.status ?? item.kind} /><span>Mission record · open posture not inferred</span><TimeValue value={item.timestamp} /></article>)}
          {missionConclusions.slice(-8).reverse().map((item, index) => <article className="workspace-record" key={`${item.record_id}:supervisor-conclusion:${index}`}><div><strong>{item.status ?? item.kind ?? "Conclusion"}</strong><BoundedSummary value={eventLabel(item)} /></div><StatusMark status={item.outcome ?? item.status} /><span>Author role unavailable from canonical event</span><TimeValue value={item.timestamp} /></article>)}
        </div>
        {incidentCount === 0 && decisionCount === 0 && transitionCount === 0 && missionConclusions.length === 0 && <QueryState kind="empty" message="No issue or conclusion in this mission" />}
      </section>
    </>
  )

  return (
    <div className="page-stack workspace-page run-workspace">
      <div className="workspace-context-bar">
        <Breadcrumbs>
          <Link to="/projects">Projects</Link><span>/</span>
          {isCurrent && breadcrumbProjectId ? (
            <Link to={`/projects/${encodeURIComponent(breadcrumbProjectId)}${backQuery}`}>
              {breadcrumbProjectId}
            </Link>
          ) : <span>{projectBindingConflict ? "Binding disagreement" : "Unassigned"}</span>}
          <span>/</span><strong>{supervisorOnly ? "Supervisor" : "Run"}</strong>
        </Breadcrumbs>
        <WorkspaceBack to={floorReturn} />
      </div>

      <section className="workspace-identity-strip">
        <span className={`operating-light light-${isCurrent ? run.light.posture : "neutral"}`}><ShieldCheck aria-hidden="true" /><strong>{isCurrent ? run.light.label : "Historical mission"}</strong></span>
        <div><strong>{run.target_label}</strong><Identity value={run.target_thread_id} /></div>
        <StatusMark status={isCurrent ? run.lifecycle.status ?? "in-progress" : segment?.posture} />
        <TimeValue value={isCurrent ? run.observed_at : segment?.last_recorded_at} />
      </section>

      {isCurrent && (
        <RunSupervisionActions
          targetId={run.target_thread_id}
          projectId={projectBindingConflict ? null : breadcrumbProjectId}
          openIncidentIds={missionIncidents.filter((incident) => incident.open).map((incident) => incident.incident_id)}
          policy={run.policy}
        />
      )}

      <div className="mission-selector">
        <label htmlFor="mission-root">Mission</label>
        <select id="mission-root" value={selectedRoot} onChange={(event) => chooseMission(event.target.value)}>
          {run.mission_segments.map((candidate) => (
            <option key={candidate.mission_root} value={candidate.mission_root}>
              {candidate.posture} · {shortIdentity(candidate.mission_root)} · {candidate.event_count} events
            </option>
          ))}
        </select>
        <Identity value={isCurrent ? segment?.policy_sha256s.at(-1) ?? run.current_mission?.policy_sha256 : segment?.policy_sha256s.at(-1)} />
      </div>

      {!isCurrent && (
        <div className="succession-boundary" role="status">
          <AlertTriangle aria-hidden="true" />Historical mission. Current lifecycle, metrics, incidents, and conclusions are not carried across this boundary.
          {segment?.superseded_by && <span>Superseded by <Identity value={segment.superseded_by} /></span>}
        </div>
      )}

      {supervisorOnly ? <>{supervisorPanel}{supervisorActivityPanel}</> : (
        <>
          <section className="workspace-summary-grid" aria-label="Run summary">
            <div><span>Events</span><strong>{segment?.event_count ?? missionEvents.length}</strong><small>{run.timeline_truncated ? "Owner window truncated" : "Mission scoped"}</small></div>
            <div><span>Incidents</span><strong>{incidentCount}</strong><small>{openIncidentCount} open</small></div>
            <div><span>Decisions</span><strong>{decisionCount}</strong><small>{isCurrent ? `${missionDecisions.filter((item) => item.open).length} open` : "Open posture unavailable"}</small></div>
            <div><span>Transitions</span><strong>{transitionCount}</strong><small>{isCurrent ? `${missionTransitions.filter((item) => item.open).length} open` : "Open posture unavailable"}</small></div>
          </section>

          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Mission &amp; binding</h2><StatusMark status={isCurrent ? projectBindingConflict ? "degraded" : run.project_binding.status : "historical"} /></div>
              <FactGrid facts={[
                ["Mission root", <Identity value={selectedRoot} />],
                ["Source record", segment?.mission_source_record ?? "Unavailable"],
                ["Policy versions", segment?.policy_sha256s.length ?? currentPolicyHistory.length],
                ["Project", isCurrent ? projectBindingConflict ? "Binding disagreement" : run.project_binding.project_id ?? "Unassigned" : "Unavailable from mission-scoped records"],
                ["Project claims", isCurrent ? projectClaimSummary : "Unavailable from mission-scoped records"],
                ["Group", isCurrent ? <Identity value={run.topology?.supervisor_group_id} /> : "Unavailable from mission-scoped records"],
                ["Binding integrity", isCurrent ? workspaceBindingIntegrity : "Not carried from the current run"],
              ]} />
            </section>
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Checkpoint &amp; lifecycle</h2><StatusMark status={isCurrent ? run.lifecycle.status : segment?.posture} /></div>
              <FactGrid facts={[
                ["Active Block", checkpointEvent?.active_block || "Unavailable from mission-scoped event"],
                ["Checkpoint", checkpointEvent?.checkpoint || "Unavailable from mission-scoped event"],
                ["Lifecycle", isCurrent ? run.lifecycle.status ?? "No lifecycle record" : segment?.terminal_record?.status ?? "No terminal record"],
                ["Completion evidence", isCurrent ? (run.lifecycle.record?.record_id ?? "No canonical completion record") : (segment?.terminal_record?.record_id ?? "No historical terminal record")],
                ["Last activity", <TimeValue value={segment?.last_recorded_at} />],
                ["Retained open work", isCurrent ? `${missionIncidents.filter((item) => item.open).length + missionDecisions.filter((item) => item.open).length + missionTransitions.filter((item) => item.open).length}` : `${openIncidentCount} open incident${openIncidentCount === 1 ? "" : "s"}; other posture unavailable`],
              ]} />
            </section>
          </div>

          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Incidents &amp; reviews</h2><span>{incidentCount}</span></div>
              {isCurrent && missionIncidents.length ? <div className="workspace-record-list">{missionIncidents.map((incident) => (
                <article className="workspace-record" key={incident.incident_id}>
                  <div><strong>{incident.incident_id}</strong><BoundedSummary value={incident.head.summary} /></div>
                  <StatusMark status={incident.open ? "open" : incident.head.status} />
                  <span>{incident.head.severity ?? "Severity unavailable"} · {incident.head.category ?? "Category unavailable"}</span>
                  <TimeValue value={incident.head.timestamp} />
                </article>
              ))}</div> : !isCurrent && historicalIncidentEvents.length ? <div className="workspace-record-list">{historicalIncidentEvents.map((event, index) => (
                <article className="workspace-record" key={`${event.record_id}:historical-incident:${index}`}>
                  <div><strong>{event.incident_id ?? "Incident record"}</strong><BoundedSummary value={eventLabel(event)} /></div>
                  <StatusMark status={event.status ?? event.kind} />
                  <span>Mission record · open posture from segment only</span>
                  <TimeValue value={event.timestamp} />
                </article>
              ))}</div> : <QueryState kind="empty" message="No incident in this mission segment" />}
            </section>
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Decisions &amp; succession</h2><span>{decisionCount + transitionCount}</span></div>
              {isCurrent && missionDecisions.length + missionTransitions.length ? <div className="workspace-record-list">
                {missionDecisions.map((decision) => <article className="workspace-record" key={decision.decision_id}><div><strong>{decision.decision_id}</strong><BoundedSummary value={decision.head.summary} /></div><StatusMark status={decision.open ? "open" : decision.head.status} /><span>Safe frontier: {decision.safe_frontier ?? "Unavailable"}</span><TimeValue value={decision.head.timestamp} /></article>)}
                {missionTransitions.map((transition) => <article className="workspace-record" key={transition.transition_id}><div><strong>{transition.transition_id}</strong><BoundedSummary value={transition.head.summary} /></div><StatusMark status={transition.open ? "open" : transition.head.status} /><span>{transition.phase ?? "Phase unavailable"}</span><TimeValue value={transition.head.timestamp} /></article>)}
              </div> : !isCurrent && historicalDecisionEvents.length + historicalTransitionEvents.length ? <div className="workspace-record-list">{[...historicalDecisionEvents, ...historicalTransitionEvents].map((event, index) => (
                <article className="workspace-record" key={`${event.record_id}:historical-decision:${index}`}><div><strong>{event.decision_id ?? event.transition_id ?? "Mission record"}</strong><BoundedSummary value={eventLabel(event)} /></div><StatusMark status={event.status ?? event.kind} /><span>Open posture unavailable; no current aggregate carried</span><TimeValue value={event.timestamp} /></article>
              ))}</div> : <QueryState kind="empty" message="No decision or transition in this mission segment" />}
            </section>
          </div>

          {supervisorPanel}

          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Conclusions</h2><span>{missionConclusions.length}</span></div>
            {missionConclusions.length ? <div className="workspace-record-list">{missionConclusions.map((conclusion, index) => (
              <article className="workspace-record" id={conclusion.record_id ?? `conclusion-${index}`} key={`${conclusion.record_id}:${index}`}>
                <div><strong>{conclusion.status ?? conclusion.kind ?? "Conclusion"}</strong><BoundedSummary value={eventLabel(conclusion)} /></div>
                <StatusMark status={conclusion.outcome ?? conclusion.status} />
                <span>Role: {conclusion.actor.status === "unavailable" ? "unavailable from canonical event" : "Unavailable"}</span>
                <TimeValue value={conclusion.timestamp} />
              </article>
            ))}</div> : <QueryState kind="empty" message="No conclusion in this mission segment" />}
          </section>

          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Events</h2><span>{eventWindow.start}–{eventWindow.end} of {filteredEvents.length}{run.timeline_truncated ? "+ owner window" : ""}</span></div>
            <div className="event-filters" aria-label="Event filters">
              <Filter aria-hidden="true" />
              <label><span>Kind</span><select value={kindFilter} onChange={(event) => { setKindFilter(event.target.value); setEventPage(0) }}><option value="all">All</option>{kinds.map((kind) => <option key={kind} value={kind}>{kind}</option>)}</select></label>
              <label><span>Severity</span><select value={severityFilter} onChange={(event) => { setSeverityFilter(event.target.value); setEventPage(0) }}><option value="all">All</option>{severities.map((severity) => <option key={severity} value={severity}>{severity}</option>)}</select></label>
              <label><span>Block</span><select value={blockFilter} onChange={(event) => { setBlockFilter(event.target.value); setEventPage(0) }}><option value="all">All</option>{blocks.map((block) => <option key={block} value={block}>{block}</option>)}</select></label>
              <label><span>Role</span><select value={roleFilter} onChange={(event) => { setRoleFilter(event.target.value); setEventPage(0) }}><option value="all">All</option><option value="unattributed">Unattributed</option></select></label>
            </div>
            {filteredEvents.length ? (
              <ol className="event-timeline">
                {eventWindow.items.map((event, index) => (
                  <li id={event.record_id ?? `event-${index}`} key={`${event.record_id}:${index}`} tabIndex={-1}>
                    <div><Identity value={event.record_id} /><StatusMark status={event.status ?? event.kind} /></div>
                    <strong>{event.kind ?? "Event"}{event.active_block ? ` · Block ${event.active_block}` : ""}</strong>
                    <BoundedSummary value={eventLabel(event)} limit={360} />
                    <span>{event.severity ?? "Severity unavailable"} · {event.category ?? "Category unavailable"} · Role unavailable</span>
                    <TimeValue value={event.timestamp} />
                  </li>
                ))}
              </ol>
            ) : <QueryState kind="empty" message="No event matches the current filters" />}
            {(eventWindow.hasOlder || eventWindow.hasNewer) && (
              <nav className="workspace-pagination" aria-label="Event pages">
                <Button variant="outline" size="compact" disabled={!eventWindow.hasOlder} onClick={() => setEventPage(eventWindow.page + 1)}>Older</Button>
                <span>{eventWindow.start}–{eventWindow.end} of {eventWindow.total}</span>
                <Button variant="outline" size="compact" disabled={!eventWindow.hasNewer} onClick={() => setEventPage(Math.max(0, eventWindow.page - 1))}>Newer</Button>
              </nav>
            )}
            {run.timeline_truncated && <div className="workspace-bound">The maintained owner returned a bounded timeline; earlier records remain in the canonical ledger.</div>}
          </section>

          <div className="workspace-split">
            <section className="workspace-panel">
              <div className="workspace-panel-heading"><h2>Reports</h2><span>{isCurrent ? run.reports.length : "Historical"}</span></div>
              {!isCurrent ? <QueryState kind="empty" message="Report association is not carried into a predecessor mission" /> : run.reports.length ? <div className="workspace-record-list">{run.reports.map((report) => <article className="workspace-record" key={report.id}><div><strong>{report.family} · {report.stage}</strong><Identity value={report.id} /></div><StatusMark status={report.status} /><span>{report.disposition ?? report.error?.message ?? `${report.members.length} members`}</span><Identity value={report.manifest_root} /></article>)}</div> : <QueryState kind="empty" message="No report associated" />}
            </section>
            <section className="workspace-panel" id={isCurrent ? "current-metric" : undefined}>
              <div className="workspace-panel-heading"><h2>Metrics</h2><span>{isCurrent ? run.metrics.status : "Historical"}</span></div>
              {!isCurrent ? <QueryState kind="empty" message="No mission-isolated historical metric projection" /> : run.metrics.status === "available" ? <FactGrid facts={[
                ["Metric projection", run.metrics.metrics.report_id],
                ["Definition", `${run.metrics.metrics.kind} · schema v${run.metrics.metrics.schema_version}`],
                ["Recorded events", run.metrics.metrics.headline.recorded_events],
                ["Changed-state routes", run.metrics.metrics.headline.changed_state_routes],
                ["Incidents opened", run.metrics.metrics.headline.incidents_opened],
                ["Corrections", run.metrics.metrics.headline.corrections_issued],
                ["Coverage", `${run.metrics.metrics.coverage.start} — ${run.metrics.metrics.coverage.end}`],
                ["Denominator", run.metrics.metrics.rates.denominator_note],
                ["Source root", run.metrics.metrics.source.source_root],
                ["Cost posture", run.metrics.metrics.resource_estimate.measurement_posture],
              ]} /> : <QueryState kind="error" message={run.metrics.error.message} />}
            </section>
          </div>

          <section className="workspace-panel">
            <div className="workspace-panel-heading"><h2>Source integrity</h2><StatusMark status={isCurrent ? run.coverage.status : "historical"} /></div>
            {isCurrent ? (
              <>
                <FactGrid facts={[
                  ["Owner", run.source?.identity ?? "Unavailable"],
                  ["Owner revision", <Identity value={run.source?.revision} />],
                  ["Event head", <Identity value={run.source?.event_head_sha256} />],
                  ["Policy head", <Identity value={run.source?.policy_head_sha256} />],
                  ["Observed", <TimeValue value={run.observed_at} />],
                  ["Missing", run.coverage.missing.join(", ") || "None"],
                ]} />
                {run.limitations.map((limitation) => <p className="workspace-limitation" key={limitation}>{limitation}</p>)}
              </>
            ) : <FactGrid facts={[
              ["Mission source record", segment?.mission_source_record ?? "Unavailable"],
              ["First record", <TimeValue value={segment?.first_recorded_at} />],
              ["Last record", <TimeValue value={segment?.last_recorded_at} />],
              ["Policy hashes", segment?.policy_sha256s.map((hash) => shortIdentity(hash)).join(", ") || "Unavailable"],
              ["Current source head", "Suppressed at succession boundary"],
              ["Current owner revision", "Suppressed at succession boundary"],
            ]} />}
          </section>
        </>
      )}
    </div>
  )
}

export function Component() {
  return <RunWorkspace />
}

export { RunWorkspace }
