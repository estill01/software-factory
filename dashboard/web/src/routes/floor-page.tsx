import { useAtom } from "jotai"
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Circle,
  CirclePause,
  Clock3,
  RefreshCw,
  X,
} from "lucide-react"
import { useEffect, useMemo, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router"

import {
  CountFilterChips,
  OperationalDisclosure,
  type CountFilterChip,
} from "@/components/factory-floor-patterns"
import { Button } from "@/components/ui/button"
import { RunCheckAction } from "@/features/admin/factory-workflow-actions"
import {
  fetchFactoryFloor,
  type FactoryFloorAttention,
  type FactoryFloorData,
  type FactoryFloorRow,
} from "@/lib/floor-api"
import {
  floorActivityFilterAtom,
  floorInspectorAtom,
  floorPostureFilterAtom,
  floorProjectFilterAtom,
  floorSeverityFilterAtom,
  floorTimeFilterAtom,
  type FloorActivityFilter,
  type FloorPostureFilter,
  type FloorSeverityFilter,
  type FloorTimeFilter,
} from "@/lib/floor-state"

const metricKeys = new Set([
  "active-projects",
  "active-tasks",
  "active-implementations",
  "supervision-runs",
  "unmonitored-implementations",
  "degraded-groups",
  "orphaned-supervisors",
  "accepted-blocks",
  "blocks-in-progress",
  "blocks-not-started",
  "open-items",
  "supervisor-checks",
  "semantic-conclusions",
  "api-equivalent",
])

const postureLabels = {
  red: "Action required",
  amber: "Watch",
  green: "On track",
  neutral: "Neutral",
} as const

function parseTime(value: string | null): number | null {
  if (!value) return null
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? null : parsed
}

function withinTime(value: string | null, filter: FloorTimeFilter, now: number): boolean {
  if (filter === "all") return true
  const parsed = parseTime(value)
  if (parsed === null) return false
  const window = filter === "24h" ? 24 * 60 * 60 * 1_000 : 7 * 24 * 60 * 60 * 1_000
  return now - parsed <= window
}

function formatTime(value: string | null): string {
  if (!value) return "Unavailable"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.valueOf())) return "Unavailable"
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed)
}

function shortId(value: string | null): string {
  if (!value) return "Unavailable"
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-5)}` : value
}

function blockLabel(value: string | null): string {
  if (!value) return "Block unavailable"
  return /^block\b/i.test(value) ? value : `Block ${value}`
}

function activeBlockLabel(block: FactoryFloorRow["work"]["block_claims"]["claims"][number]["blocks"][number]): string {
  return `Block ${block.number}${block.title ? ` — ${block.title}` : " — title unavailable"}`
}

function claimLabel(claim: FactoryFloorRow["work"]["block_claims"]["claims"][number]): string {
  if (claim.blocks.length) return claim.blocks.map(activeBlockLabel).join("; ")
  if (claim.range) return `Blocks ${claim.range.start}–${claim.range.end} assigned; active Block unavailable`
  if (claim.status === "none") return "None active"
  if (claim.status === "conflict") return "Conflict"
  if (claim.status === "partial") return "Partial"
  return "Unavailable"
}

function rowMatchesActivity(row: FactoryFloorRow, filter: FloorActivityFilter): boolean {
  if (filter === "all") return true
  if (filter === "active") {
    return row.implementation.status === "active" || row.supervision.status === "active"
  }
  if (filter === "attention") {
    return row.issues.total > 0
      || row.disagreements.length > 0
      || row.work.block_claims.posture === "conflict"
      || row.light.posture === "red"
      || row.light.posture === "amber"
  }
  if (filter === "blocked") {
    return row.implementation.status === "terminal"
      || row.supervision.status === "blocked"
      || row.supervision.status === "failed"
  }
  return row.supervision.status === "completed"
}

function countChip(
  key: FloorActivityFilter,
  label: string,
  tone: CountFilterChip<FloorActivityFilter>["tone"],
  count: number,
  options: { truncated: boolean; partial: boolean; unavailable: boolean },
): CountFilterChip<FloorActivityFilter> {
  if (options.unavailable) {
    return { key, label, tone, countLabel: "—", accessibleCount: "unavailable" }
  }
  if (options.truncated) {
    return {
      key,
      label,
      tone,
      countLabel: `≥${count}${options.partial ? "*" : ""}`,
      accessibleCount: `${count} returned, lower bound${options.partial ? ", source coverage partial" : ""}`,
    }
  }
  if (options.partial) {
    return {
      key,
      label,
      tone,
      countLabel: `${count}*`,
      accessibleCount: `${count} returned, source coverage partial`,
    }
  }
  return { key, label, tone, countLabel: String(count), accessibleCount: `${count} exact` }
}

function inspectKey(route: string): string {
  return new URL(route, window.location.origin).searchParams.get("inspect") ?? route
}

function setInspectRoute(value: string | null): void {
  const url = new URL(window.location.href)
  if (value) url.searchParams.set("inspect", value)
  else url.searchParams.delete("inspect")
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`)
}

function Time({ value }: { value: string | null }) {
  return value
    ? <time dateTime={value} title={value}>{formatTime(value)}</time>
    : <span>Unavailable</span>
}

function LightIcon({ posture }: { posture: FactoryFloorRow["light"]["posture"] }) {
  if (posture === "green") return <CheckCircle2 aria-hidden="true" />
  if (posture === "red" || posture === "amber") return <AlertTriangle aria-hidden="true" />
  return <CirclePause aria-hidden="true" />
}

function Inspector({ data, selected, close }: {
  data: FactoryFloorData
  selected: string
  close: () => void
}) {
  const row = data.rows.find((item) => `${item.detail.kind}:${item.detail.id}` === selected)
  const attention = data.attention.find((item) => inspectKey(item.source.route) === selected)
  const conclusion = data.conclusions.find((item) => inspectKey(item.source.route) === selected)
  const outcome = data.accepted_outcomes.find((item) => inspectKey(item.source.route) === selected)
  const source = data.source_health.find((item) => `source:${item.family}` === selected)
  const project = data.projects.find((item) => `project:${item.id}` === selected)
  const metric = data.metrics.find((item) => `metric:${item.key}` === selected)
  const facts: Array<[string, string | number | null]> = []
  let title = "Source detail"
  let identity: string | null = null
  let revision: string | null = null
  let path: string | null = null

  if (row) {
    title = row.implementation.name ?? shortId(row.implementation.task_id)
    facts.push(
      ["Project", row.project.label],
      ["Task", row.implementation.task_id],
      ["Task state", row.implementation.status_label],
      ["Supervision", row.supervision.status_label],
      ["Supervisor group", row.supervision.group_id],
      ["Roles", row.supervision.role_count],
      ["Binding", row.supervision.binding_integrity],
      ["Tracker", row.work.tracker.title ?? row.work.tracker.status],
      [
        "Tracker Blocks",
        row.work.block_claims.tracker_total.value === null
          ? row.work.block_claims.tracker_total.posture
          : `${row.work.block_claims.tracker_total.value} · ${row.work.block_claims.tracker_total.posture}`,
      ],
      ["Active claim posture", row.work.block_claims.posture],
      ["Checkpoint", row.work.checkpoint],
      ["Open items", row.issues.total],
      ["Posture", row.light.label],
      ["Reason", row.light.reason],
      ["Observed", row.light.observed_at],
    )
    row.supervision.roles.forEach((role, index) => {
      const roleName = role.label ?? role.role ?? `Role ${index + 1}`
      facts.push([
        `Role · ${roleName}`,
        [
          role.role ?? "type unavailable",
          role.thread_id ?? "task unavailable",
          `binding ${role.binding_status ?? "unavailable"}`,
          `task ${role.task_status}`,
          `automation ${role.automation_status ?? "unavailable"}`,
        ].join(" · "),
      ])
    })
    row.work.block_claims.claims.forEach((claim) => {
      facts.push([
        `Active Blocks · ${claim.label}`,
        `${claimLabel(claim)} · ${claim.status} · ${claim.reason}`,
      ])
    })
    const preferred = row.detail.source_refs[0]
    identity = preferred?.identity ?? row.detail.id
    revision = preferred?.revision ?? null
    path = preferred?.path ?? null
  } else if (attention) {
    title = attention.rule?.replaceAll("-", " ") ?? "Attention item"
    facts.push(
      ["Rank", attention.rank],
      ["Severity", attention.severity],
      ["Target", attention.target_thread_id],
      ["Reason", attention.reason],
      ["Safe frontier", attention.safe_frontier],
      ["Observed", attention.observed_at],
    )
    identity = attention.source.identity
    path = attention.source.path
  } else if (conclusion) {
    title = conclusion.summary ?? "Supervisor conclusion"
    facts.push(
      ["Target", conclusion.target_label],
      ["Disposition", conclusion.disposition],
      ["Author", conclusion.author ?? "Unavailable from owner"],
      ["Current", conclusion.current ? "Yes" : "No"],
      ["Open work retained", conclusion.retained_open_work],
      ["Next action", conclusion.next_action],
      ["Observed", conclusion.observed_at],
    )
    identity = conclusion.source.identity
    revision = conclusion.source.revision
    path = conclusion.source.path
  } else if (outcome) {
    title = `Block ${outcome.block} · ${outcome.title}`
    facts.push(
      ["Project", outcome.project_id],
      ["Tracker", outcome.tracker_title],
      ["Status", outcome.status],
      ["Currentness", outcome.currentness],
      ["Open work retained", outcome.retained_open_work],
      ["Observed", outcome.observed_at],
    )
    identity = outcome.source.identity
    revision = outcome.source.revision
    path = outcome.source.path
  } else if (source) {
    title = source.label
    facts.push(
      ["Status", source.status],
      ["Reason", source.reason],
      ["Coverage", source.coverage.status],
      ["Observed", source.observed_at],
      ["Missing", source.coverage.missing.join(", ") || "None"],
    )
    identity = source.identity
    revision = source.revision
  } else if (project) {
    title = project.label
    facts.push(["Project ID", project.id])
    identity = `project-catalog/${project.id}`
  } else if (metric) {
    title = metric.label
    facts.push(
      ["Value", metric.available ? `${metric.value} ${metric.unit}` : "Unavailable"],
      ["Period", metric.period],
      ["Coverage", metric.coverage],
      ["Estimate", metric.estimate ? "Yes" : "No"],
    )
    identity = metric.source_identity
  } else {
    facts.push(["Reference", selected])
  }

  return (
    <aside className="floor-inspector" aria-label="Factory source inspector">
      <div className="floor-inspector-heading">
        <div>
          <span className="eyebrow">Inspector</span>
          <strong>{title}</strong>
        </div>
        <Button variant="ghost" size="icon" onClick={close} aria-label="Close inspector">
          <X aria-hidden="true" />
        </Button>
      </div>
      <dl className="floor-inspector-facts">
        {facts.map(([label, value], index) => (
          <div key={`${label}:${index}`}>
            <dt>{label}</dt>
            <dd>{value === null || value === "" ? "Unavailable" : String(value)}</dd>
          </div>
        ))}
      </dl>
      <div className="floor-inspector-source">
        <span>Source</span>
        <code>{identity ?? "Unavailable"}</code>
        {revision && <code title={revision}>{shortId(revision)}</code>}
        {path && <code title={path}>{path}</code>}
      </div>
    </aside>
  )
}

function FloorRow({ row, inspect, returnPath }: {
  row: FactoryFloorRow
  inspect: (route: string) => void
  returnPath: string
}) {
  const tracker = row.work.tracker
  const blockClaims = row.work.block_claims
  const totalLabel = blockClaims.tracker_total.value === null
    ? blockClaims.tracker_total.posture === "partial" ? "Blocks partial" : "Blocks unavailable"
    : `${blockClaims.tracker_total.value} Blocks${blockClaims.tracker_total.posture === "exact" ? "" : " · partial"}`
  const workspacePath = row.detail.kind === "run"
    ? `/runs/${encodeURIComponent(row.detail.id)}?return=${encodeURIComponent(returnPath)}`
    : `/tasks/${encodeURIComponent(row.detail.id)}?return=${encodeURIComponent(returnPath)}`
  const roleSummary = row.supervision.roles
    .map((role) => role.label ?? role.role ?? shortId(role.thread_id))
    .join(" · ")
  const activeSummary = blockClaims.claims
    .map((claim) => `${claim.label}: ${claimLabel(claim)}`)
    .join("; ")
  const accessibleSummary = [
    row.implementation.name ?? row.implementation.task_id,
    `project ${row.project.label}`,
    `task ${row.implementation.task_id} ${row.implementation.status_label}`,
    `supervision ${row.supervision.status_label}`,
    `group ${row.supervision.group_id ?? "unavailable"}`,
    `roles ${roleSummary || "unavailable"}`,
    totalLabel,
    activeSummary,
    `${row.issues.total} open items`,
    `${row.light.label}: ${row.light.reason}`,
    `observed ${row.freshness.observed_at ?? "unavailable"}`,
  ].join(", ")
  return (
    <OperationalDisclosure
      ariaLabel={`${accessibleSummary}. Expand source-backed details`}
      detailLabel={`${row.implementation.name ?? row.implementation.task_id} source-backed operational detail`}
      className={`factory-operational-row posture-${row.light.posture}${blockClaims.posture === "conflict" ? " block-claim-conflict" : ""}`}
      marker={<LightIcon posture={row.light.posture} />}
      summary={(
        <>
          <span className="operational-row-identity">
            <span className="row-project">{row.project.label}</span>
            <strong>{row.implementation.name ?? shortId(row.implementation.task_id)}</strong>
            <span className="row-meta">
              <span className={`status-chip state-${row.implementation.status}`}>
                {row.implementation.status_label}
              </span>
              <code title={row.implementation.task_id}>{shortId(row.implementation.task_id)}</code>
            </span>
          </span>
          <span className="operational-row-supervision">
            <span className="cell-label">Supervision</span>
            <strong>{row.supervision.status_label} · {shortId(row.supervision.group_id)}</strong>
            <span title={roleSummary || undefined}>{roleSummary || "Roles unavailable"}</span>
          </span>
          <span className={`operational-row-blocks claims-${blockClaims.posture}`}>
            <span className="cell-label">{totalLabel}</span>
            {blockClaims.claims.map((claim) => (
              <span className={`collapsed-block-claim claim-${claim.status}`} key={claim.source}>
                <span>{claim.label}</span>
                <strong title={claim.reason}>{claimLabel(claim)}</strong>
              </span>
            ))}
          </span>
        </>
      )}
      trailing={(
        <>
          <span className={`operating-light light-${row.light.posture}`}>
            <strong>{row.light.label}</strong>
          </span>
          <span className={row.issues.total > 0 ? "row-attention-count" : "row-attention-clear"}>
            {row.issues.total > 0 ? `${row.issues.total} open` : "No open items"}
          </span>
          <span className="row-freshness"><Time value={row.freshness.observed_at} /></span>
        </>
      )}
    >
      <div className="factory-row-detail-grid">
        <div className="factory-row-implementation">
          <span className="cell-label">Implementation</span>
          {row.project.project_id ? (
            <Link
              className="row-project row-project-link"
              to={`/projects/${encodeURIComponent(row.project.project_id)}?return=${encodeURIComponent(returnPath)}`}
            >{row.project.label}</Link>
          ) : <span className="row-project">{row.project.label}</span>}
          <strong>{row.implementation.name ?? shortId(row.implementation.task_id)}</strong>
          <span className="row-meta">Task <code title={row.implementation.task_id}>{row.implementation.task_id}</code></span>
          <span>{row.implementation.status_label} · source {row.implementation.source_status}</span>
          {row.disagreements.length > 0 && (
            <ul className="row-disagreement-list">
              {row.disagreements.map((disagreement) => (
                <li key={disagreement}><AlertTriangle aria-hidden="true" />{disagreement}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="factory-row-supervision">
          <span className="cell-label">Supervisor group</span>
          <strong>{row.supervision.status_label}</strong>
          {row.supervision.run_id ? (
            <Link className="row-meta row-detail-link" to={`/runs/${encodeURIComponent(row.supervision.run_id)}/supervisor?return=${encodeURIComponent(returnPath)}`}>
              Group <code title={row.supervision.group_id ?? undefined}>{row.supervision.group_id ?? "Unavailable"}</code>
            </Link>
          ) : <span className="row-meta">Group <code>{row.supervision.group_id ?? "Unavailable"}</code></span>}
          <span className="row-meta">Target <code>{row.supervision.target_thread_id}</code></span>
          <span>Mission <code title={row.work.mission_root ?? undefined}>{shortId(row.work.mission_root)}</code></span>
          <span>{row.supervision.binding_integrity === "valid" ? "Bindings valid" : `Bindings ${row.supervision.binding_integrity}`}</span>
          <div className="operational-role-list">
            {row.supervision.roles.length ? row.supervision.roles.map((role, index) => (
              <span key={`${role.role}:${role.thread_id}:${index}`}>
                <strong>{role.label ?? role.role ?? `Role ${index + 1}`}</strong>
                <code>{role.thread_id ?? "Task unavailable"}</code>
                <small>{role.binding_status ?? "binding unavailable"} · task {role.task_status} · automation {role.automation_status ?? "unavailable"}</small>
              </span>
            )) : <span>Roles unavailable</span>}
          </div>
        </div>

        <div className="factory-row-work">
          <span className="cell-label">Tracker &amp; active claims</span>
          <strong>{totalLabel}</strong>
          <span title={tracker.relative_path ?? undefined}>{tracker.title ?? `Tracker ${tracker.status}`} · {tracker.status}</span>
          <small>{blockClaims.tracker_total.reason}</small>
          <div className="active-claim-list">
            {blockClaims.claims.map((claim) => (
              <div className={`active-claim-row claim-${claim.status}`} key={claim.source}>
                <span><strong>{claim.label}</strong><small>{claim.status}</small></span>
                <span>
                  {claim.blocks.length ? claim.blocks.map((block) => (
                    <Link to={block.route} key={`${claim.source}:${block.number}`}>{activeBlockLabel(block)}</Link>
                  )) : <strong>{claimLabel(claim)}</strong>}
                  <small>{claim.reason}</small>
                </span>
                <Link to={claim.route}>Source</Link>
              </div>
            ))}
          </div>
          <span>{row.work.checkpoint ? `${blockLabel(row.work.active_block)} · ${row.work.checkpoint}` : "Checkpoint unavailable"}</span>
          <span>{row.work.last_action ?? "No current action recorded"}</span>
          {row.conclusion && (
            <span className="row-conclusion">
              <strong>{row.conclusion.summary ?? "Conclusion summary unavailable"}</strong>
              <small>{row.conclusion.action ?? row.conclusion.resolution ?? "No next owner action recorded"}</small>
            </span>
          )}
        </div>

        <div className="factory-row-light">
          <span className="cell-label">Attention &amp; freshness</span>
          <span className={`operating-light light-${row.light.posture}`}>
            <LightIcon posture={row.light.posture} />
            <strong>{row.light.label}</strong>
          </span>
          <span>{row.light.reason}</span>
          <span>{row.issues.incidents} incidents · {row.issues.decisions} decisions · {row.issues.transitions} transitions</span>
          <span>Last check <Time value={row.supervision.last_check?.observed_at ?? null} /></span>
          <span>Next {row.supervision.next_check.at
            ? <Time value={row.supervision.next_check.at} />
            : <span title={row.supervision.next_check.reason}>unavailable</span>}</span>
          <span>Observed <Time value={row.light.observed_at} /></span>
          <span className="factory-row-actions">
            <a
              className="inspect-link"
              href={row.detail.route}
              onClick={(event) => {
                event.preventDefault()
                inspect(row.detail.route)
              }}
            >Inspect <ChevronRight aria-hidden="true" /></a>
            <Link className="inspect-link" to={workspacePath}>Open workspace <ChevronRight aria-hidden="true" /></Link>
          </span>
          {row.supervision.run_id && (
            <RunCheckAction
              targetId={row.supervision.run_id}
              projectId={row.project.project_id}
              inline
            />
          )}
        </div>
      </div>
    </OperationalDisclosure>
  )
}

function AttentionItem({ item, inspect, workspacePath }: {
  item: FactoryFloorAttention
  inspect: (route: string) => void
  workspacePath: string | null
}) {
  return (
    <li className={`attention-item severity-${item.severity}`}>
      <span className="attention-rank">{item.rank}</span>
      <span className="attention-icon" aria-hidden="true">
        {item.severity === "neutral" ? <Circle /> : <AlertTriangle />}
      </span>
      <div>
        <strong>{item.reason ?? item.rule ?? "Attention item"}</strong>
        <span>
          {item.target_thread_id ? `Target ${shortId(item.target_thread_id)} · ` : ""}
          {item.owner ?? "Owner unavailable"}
        </span>
        <span>Safe frontier: {item.safe_frontier ?? "Unavailable from owner"}</span>
      </div>
      <div className="attention-action">
        <Time value={item.observed_at} />
        <a
          href={item.source.route}
          onClick={(event) => {
            event.preventDefault()
            inspect(item.source.route)
          }}
        >Inspect</a>
        {workspacePath && <Link to={workspacePath}>Open</Link>}
      </div>
    </li>
  )
}

function FactoryFloor({ data, isFetching, refresh }: {
  data: FactoryFloorData
  isFetching: boolean
  refresh: () => void
}) {
  const [projectFilter, setProjectFilter] = useAtom(floorProjectFilterAtom)
  const [activityFilter, setActivityFilter] = useAtom(floorActivityFilterAtom)
  const [postureFilter, setPostureFilter] = useAtom(floorPostureFilterAtom)
  const [severityFilter, setSeverityFilter] = useAtom(floorSeverityFilterAtom)
  const [timeFilter, setTimeFilter] = useAtom(floorTimeFilterAtom)
  const [selected, setSelected] = useAtom(floorInspectorAtom)
  const filtersHydrated = useRef(false)
  const now = Date.now()
  const rowProject = new Map(
    data.rows.map((row) => [row.supervision.target_thread_id, row.project.project_id]),
  )
  const rowWorkspace = new Map(data.rows.flatMap((row) => {
    const path = row.detail.kind === "run"
      ? `/runs/${encodeURIComponent(row.detail.id)}`
      : `/tasks/${encodeURIComponent(row.detail.id)}`
    return [
      [row.supervision.target_thread_id, path] as const,
      [row.implementation.task_id, path] as const,
    ]
  }))
  const matchesProject = (projectId: string | null, targetId?: string | null) =>
    projectFilter === "all" || projectId === projectFilter || rowProject.get(targetId ?? "") === projectFilter
  const baseRows = data.rows.filter((row) =>
    matchesProject(row.project.project_id)
    && (postureFilter === "all" || row.light.posture === postureFilter)
    && withinTime(row.freshness.observed_at, timeFilter, now)
  )
  const rows = baseRows.filter((row) => rowMatchesActivity(row, activityFilter))
  const sourceCoveragePartial = data.source_health.some(
    (source) => source.status !== "available" || source.coverage.status !== "complete",
  )
  const sourceCoverageUnavailable = baseRows.length === 0 && data.source_health.every(
    (source) => source.status === "unavailable",
  )
  const countOptions = {
    truncated: data.rows_truncated,
    partial: sourceCoveragePartial,
    unavailable: sourceCoverageUnavailable,
  }
  const activityChips: Array<CountFilterChip<FloorActivityFilter>> = [
    countChip("all", "All", "neutral", baseRows.length, countOptions),
    countChip("active", "Active / Running", "active", baseRows.filter((row) => rowMatchesActivity(row, "active")).length, countOptions),
    countChip("attention", "Attention", "attention", baseRows.filter((row) => rowMatchesActivity(row, "attention")).length, countOptions),
    countChip("blocked", "Blocked / Failed", "blocked", baseRows.filter((row) => rowMatchesActivity(row, "blocked")).length, countOptions),
    countChip("completed", "Completed", "completed", baseRows.filter((row) => rowMatchesActivity(row, "completed")).length, countOptions),
  ]
  const attentionMatches = data.attention.filter((item) =>
    matchesProject(item.project_id, item.target_thread_id)
    && (severityFilter === "all" || item.severity === severityFilter)
    && withinTime(item.observed_at, timeFilter, now)
  )
  const conclusionMatches = data.conclusions.filter((item) =>
    matchesProject(null, item.target_thread_id)
    && withinTime(item.observed_at, timeFilter, now)
  )
  const outcomeMatches = data.accepted_outcomes.filter((item) =>
    matchesProject(item.project_id)
    && withinTime(item.observed_at, timeFilter, now)
  )
  const visibleCritical = attentionMatches.filter((item) => item.severity !== "neutral").length
  const hiddenCritical = Math.max(
    0,
    data.attention_summary.critical_returned - visibleCritical,
  )
  const attention = attentionMatches.slice(0, 10)
  const boundedCritical = attentionMatches
    .slice(attention.length)
    .filter((item) => item.severity !== "neutral").length
  const conclusions = conclusionMatches.slice(0, 6)
  const outcomes = outcomeMatches.slice(0, 6)
  const sourcesIncomplete = data.source_health.filter(
    (source) => source.status !== "available" || source.coverage.status !== "complete",
  )
  const metrics = data.metrics.filter((metric) => metricKeys.has(metric.key))
  const floorParams = new URLSearchParams()
  floorParams.set("project", projectFilter)
  floorParams.set("activity", activityFilter)
  floorParams.set("time", timeFilter)
  floorParams.set("posture", postureFilter)
  floorParams.set("severity", severityFilter)
  const returnPath = `/?${floorParams.toString()}`

  useEffect(() => {
    const params = new URL(window.location.href).searchParams
    const project = params.get("project")
    const activity = params.get("activity")
    const time = params.get("time")
    const posture = params.get("posture")
    const severity = params.get("severity")
    if (project && (project === "all" || data.projects.some((item) => item.id === project))) setProjectFilter(project)
    if (activity === "all" || activity === "active" || activity === "attention" || activity === "blocked" || activity === "completed") setActivityFilter(activity)
    if (time === "all" || time === "24h" || time === "7d") setTimeFilter(time)
    if (posture === "all" || posture === "red" || posture === "amber" || posture === "green" || posture === "neutral") setPostureFilter(posture as FloorPostureFilter)
    if (severity === "all" || severity === "red" || severity === "amber" || severity === "neutral") setSeverityFilter(severity as FloorSeverityFilter)
    filtersHydrated.current = true
  }, [data.projects, setActivityFilter, setPostureFilter, setProjectFilter, setSeverityFilter, setTimeFilter])

  useEffect(() => {
    if (!filtersHydrated.current) return
    const url = new URL(window.location.href)
    url.searchParams.set("project", projectFilter)
    url.searchParams.set("activity", activityFilter)
    url.searchParams.set("time", timeFilter)
    url.searchParams.set("posture", postureFilter)
    url.searchParams.set("severity", severityFilter)
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`)
  }, [activityFilter, postureFilter, projectFilter, severityFilter, timeFilter])

  const inspect = (route: string) => {
    const key = inspectKey(route)
    setSelected(key)
    setInspectRoute(key)
  }
  const closeInspector = () => {
    setSelected(null)
    setInspectRoute(null)
  }

  useEffect(() => {
    const current = new URL(window.location.href).searchParams.get("inspect")
    if (current && current !== selected) setSelected(current)
  }, [selected, setSelected])

  return (
    <div className="page-stack factory-floor-page">
      <section className="panel factory-floor-region" aria-labelledby="factory-floor-heading">
        <div className="floor-region-heading">
          <div>
            <h2 id="factory-floor-heading">Implementations &amp; supervisors</h2>
            <span>{rows.length} of {baseRows.length} represented rows</span>
          </div>
          <div className="floor-refresh">
            <span className={sourcesIncomplete.length ? "freshness-partial" : "freshness-current"}>
              <Clock3 aria-hidden="true" />
              {sourcesIncomplete.length ? `${sourcesIncomplete.length} source${sourcesIncomplete.length === 1 ? "" : "s"} partial` : "Sources current"}
            </span>
            <Button variant="outline" size="compact" onClick={refresh} disabled={isFetching}>
              <RefreshCw className={isFetching ? "spin" : ""} aria-hidden="true" />
              {isFetching ? "Refreshing" : "Refresh"}
            </Button>
          </div>
        </div>

        <div className="floor-summary" role="group" aria-label="Factory summary">
          <div><span>Projects</span><strong>{data.summary.registered_projects}</strong></div>
          <div><span>Active</span><strong>{data.summary.active_implementations ?? "—"}</strong></div>
          <div><span>Supervisors</span><strong>{data.summary.supervisor_groups ?? "—"}</strong></div>
          <div><span>Action required</span><strong>{data.summary.action_required}</strong></div>
          {(["red", "amber", "green", "neutral"] as const).map((posture) => (
            <div className={`summary-posture posture-${posture}`} key={posture}>
              <span>{postureLabels[posture]}</span><strong>{data.summary.postures[posture]}</strong>
            </div>
          ))}
        </div>

        <CountFilterChips
          label="Implementation status"
          value={activityFilter}
          items={activityChips}
          onChange={setActivityFilter}
        />

        <div className="floor-filters" aria-label="Factory Floor filters">
          <label>
            <span>Project</span>
            <select aria-label="Project" value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
              <option value="all">All projects</option>
              {data.projects.map((project) => (
                <option value={project.id} key={project.id}>{project.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Time</span>
            <select aria-label="Time" value={timeFilter} onChange={(event) => setTimeFilter(event.target.value as FloorTimeFilter)}>
              <option value="all">All current</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
            </select>
          </label>
          <label>
            <span>Posture</span>
            <select aria-label="Posture" value={postureFilter} onChange={(event) => setPostureFilter(event.target.value as typeof postureFilter)}>
              <option value="all">All postures</option>
              <option value="red">Action required</option>
              <option value="amber">Watch</option>
              <option value="green">On track</option>
              <option value="neutral">Neutral</option>
            </select>
          </label>
          <label>
            <span>Attention</span>
            <select aria-label="Attention" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as typeof severityFilter)}>
              <option value="all">All severities</option>
              <option value="red">Red</option>
              <option value="amber">Amber</option>
              <option value="neutral">Neutral</option>
            </select>
          </label>
          {hiddenCritical > 0 && (
            <span className="hidden-critical" role="status">
              <AlertTriangle aria-hidden="true" />{hiddenCritical} critical hidden by filters
            </span>
          )}
        </div>

        <div className="factory-rows">
          {rows.length > 0
            ? rows.map((row) => <FloorRow row={row} inspect={inspect} returnPath={returnPath} key={row.id} />)
            : <div className="bounded-empty">No rows match the current filters.</div>}
        </div>
        {data.rows_truncated && <div className="bounded-note">The owner-bounded row limit was reached.</div>}
      </section>

      <section className="panel attention-region" aria-labelledby="attention-heading">
        <div className="floor-region-heading">
          <div><h2 id="attention-heading">Needs attention</h2></div>
          <strong>{attention.length} of {attentionMatches.length}</strong>
        </div>
        {attention.length > 0
          ? <ol className="attention-list">{attention.map((item) => {
            const path = item.target_thread_id ? rowWorkspace.get(item.target_thread_id) : null
            return <AttentionItem item={item} inspect={inspect} workspacePath={path ? `${path}?return=${encodeURIComponent(returnPath)}` : null} key={item.id} />
          })}</ol>
          : <div className="bounded-empty">No attention items match the current filters.</div>}
        {boundedCritical > 0 && (
          <div className="bounded-note critical-note" role="status">
            {boundedCritical} critical item{boundedCritical === 1 ? "" : "s"} outside the bounded view.
          </div>
        )}
        {data.attention_summary.truncated && (
          <div
            className={`bounded-note ${data.attention_summary.critical_omitted ? "critical-note" : ""}`}
            role="status"
          >
            {data.attention_summary.total - data.attention_summary.returned} attention item
            {data.attention_summary.total - data.attention_summary.returned === 1 ? "" : "s"}
            {" omitted by the API bound"}
            {data.attention_summary.critical_omitted > 0
              ? ` · ${data.attention_summary.critical_omitted} critical`
              : ""}.
          </div>
        )}
      </section>

      <section className="panel outcomes-region" aria-labelledby="outcomes-heading">
        <div className="floor-region-heading">
          <div><h2 id="outcomes-heading">Latest conclusions &amp; accepted outcomes</h2></div>
        </div>
        <div className="outcome-columns">
          <div className="outcome-column" aria-label="Supervisor and reviewer conclusions">
            <div className="outcome-column-label"><span>Conclusions</span><strong>{conclusions.length} of {conclusionMatches.length}</strong></div>
            {conclusions.length > 0 ? conclusions.map((item) => (
              <article className="outcome-item" key={item.id}>
                <span className="outcome-kicker">{item.disposition ?? "Disposition unavailable"} · {item.current ? "Current" : "Superseded"}</span>
                <strong>{item.summary ?? "Conclusion summary unavailable"}</strong>
                <span>{item.target_label} · Author {item.author ?? "unavailable"}</span>
                <span>{item.next_action ?? "No next action recorded"}</span>
                <footer>
                  <Time value={item.observed_at} />
                  <span className="floor-action-links"><a href={item.source.route} onClick={(event) => { event.preventDefault(); inspect(item.source.route) }}>Inspect</a><Link to={`/runs/${encodeURIComponent(item.target_thread_id)}?return=${encodeURIComponent(returnPath)}`}>Open</Link></span>
                </footer>
              </article>
            )) : <div className="bounded-empty compact">No current conclusions in range.</div>}
          </div>
          <div className="outcome-column" aria-label="Accepted implementation outcomes">
            <div className="outcome-column-label"><span>Accepted outcomes</span><strong>{outcomes.length} of {outcomeMatches.length}</strong></div>
            {outcomes.length > 0 ? outcomes.map((item) => (
              <article className="outcome-item" key={item.id}>
                <span className="outcome-kicker">Block {item.block} · {item.currentness}</span>
                <strong>{item.title}</strong>
                <span>{item.tracker_title} · {item.project_id}</span>
                <span>Evidence {shortId(item.evidence_revision)} · {item.retained_open_work ?? "—"} open retained</span>
                <footer>
                  <span>Observed <Time value={item.observed_at} /></span>
                  <span className="floor-action-links"><a href={item.source.route} onClick={(event) => { event.preventDefault(); inspect(item.source.route) }}>Inspect</a><Link to={`/projects/${encodeURIComponent(item.project_id)}?return=${encodeURIComponent(returnPath)}`}>Project</Link></span>
                </footer>
              </article>
            )) : <div className="bounded-empty compact">No accepted tracker outcomes in range.</div>}
          </div>
        </div>
      </section>

      <section className="panel metrics-freshness-region" aria-labelledby="metrics-heading">
        <div className="floor-region-heading">
          <div><h2 id="metrics-heading">Metrics &amp; freshness</h2></div>
        </div>
        <div className="source-health-strip">
          {data.source_health.map((source) => (
            <a href={`/?inspect=source:${source.family}`} onClick={(event) => { event.preventDefault(); inspect(`/?inspect=source:${source.family}`) }} key={source.family}>
              <span className={`source-health-dot source-${source.status === "available" && source.coverage.status === "partial" ? "partial" : source.status}`} aria-hidden="true" />
              <strong>{source.label}</strong>
              <span>
                {source.status}
                {source.status === "available" && source.coverage.status === "partial" ? " · partial" : ""}
              </span>
              <Time value={source.observed_at} />
            </a>
          ))}
        </div>
        <div className="floor-metric-grid">
          {metrics.map((metric) => (
            <a
              className="floor-metric"
              href={`/?inspect=metric:${metric.key}`}
              key={metric.key}
              onClick={(event) => {
                event.preventDefault()
                inspect(`/?inspect=metric:${metric.key}`)
              }}
            >
              <span>{metric.label}</span>
              <strong>{metric.available ? metric.value : "—"}</strong>
              <span>{metric.available ? metric.unit : "Unavailable"}{metric.estimate ? " · estimate" : ""}</span>
              <small>{metric.period}</small>
              <small>{metric.coverage}</small>
            </a>
          ))}
        </div>
      </section>

      {selected && <Inspector data={data} selected={selected} close={closeInspector} />}
    </div>
  )
}

export function Component() {
  const floor = useQuery({
    queryKey: ["factory-floor"],
    queryFn: ({ signal }) => fetchFactoryFloor(signal),
    retry: 1,
    refetchOnWindowFocus: true,
    refetchInterval: () => document.visibilityState === "visible" ? 20_000 : false,
  })

  const content = useMemo(() => {
    if (floor.isPending) {
      return (
        <section className="panel floor-query-state" aria-busy="true">
          <RefreshCw className="spin" aria-hidden="true" />
          <span>Loading Factory Floor</span>
        </section>
      )
    }
    if (floor.isError) {
      return (
        <section className="panel floor-query-state" role="alert">
          <AlertTriangle aria-hidden="true" />
          <strong>Factory Floor unavailable</strong>
          <span>{floor.error instanceof Error ? floor.error.message : "The aggregate source could not be read."}</span>
          <Button variant="outline" size="compact" onClick={() => void floor.refetch()}>Retry</Button>
        </section>
      )
    }
    return (
      <FactoryFloor
        data={floor.data.data}
        isFetching={floor.isFetching}
        refresh={() => void floor.refetch()}
      />
    )
  }, [floor.data, floor.error, floor.isError, floor.isFetching, floor.isPending, floor.refetch])

  return content
}
