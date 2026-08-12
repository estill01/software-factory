import { useQueries, useQuery } from "@tanstack/react-query"
import {
  AlertTriangle,
  Download,
  ExternalLink,
  FileJson,
  FileText,
  Printer,
} from "lucide-react"
import { useMemo } from "react"
import { Link, useSearchParams } from "react-router"

import { SafeMarkdown } from "@/components/safe-markdown"
import { Button } from "@/components/ui/button"
import { Identity, QueryState, StatusMark, TimeValue } from "@/components/workspace-ui"
import { FactoryEvolutionEvidence } from "@/features/admin/factory-evolution-evidence"
import {
  MetricHistoryChart,
  type MetricTrendPoint,
  type MetricTrendSource,
} from "@/features/reports/metric-history-chart"
import {
  fetchMetrics,
  fetchReport,
  fetchReportArtifactText,
  fetchReports,
  type MetricsEnvelope,
  type ReportArtifact,
  type ReportDetail,
} from "@/lib/operations-api"
import { fetchProjects } from "@/lib/projects-api"

type MetricRun = MetricsEnvelope["data"]["per_run"][number]
type AvailableMetricRun = Extract<MetricRun, { status: "available" }>
type MetricAggregateState = "available" | "incompatible" | "unavailable"
type WindowFilter = "all" | "24h" | "7d" | "30d"

const MAX_TREND_POINTS = 90

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function reportKey(report: Pick<ReportArtifact, "target_thread_id" | "family" | "id">): string {
  return `${report.target_thread_id}::${report.family}::${report.id}`
}

function parseReportKey(value: string | null): {
  target: string
  family: ReportArtifact["family"]
  id: string
} | null {
  const [target, family, id, ...rest] = value?.split("::") ?? []
  if (rest.length || !target || !id || !["weekly", "terminal", "factory-evolution"].includes(family ?? "")) {
    return null
  }
  return { target, family: family as ReportArtifact["family"], id }
}

function earliestAllowed(windowFilter: WindowFilter): number | null {
  const duration = windowFilter === "24h" ? 24 : windowFilter === "7d" ? 24 * 7 : windowFilter === "30d" ? 24 * 30 : null
  return duration === null ? null : Date.now() - duration * 60 * 60 * 1_000
}

function inWindow(value: string | null | undefined, windowFilter: WindowFilter): boolean {
  const earliest = earliestAllowed(windowFilter)
  if (earliest === null) return true
  if (!value) return false
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) && parsed >= earliest
}

function aggregateCount(runs: MetricRun[], key: string): number {
  return runs.reduce((total, run) => {
    if (run.status !== "available") return total
    const value = run.metrics.headline[key as keyof typeof run.metrics.headline]
    return total + (typeof value === "number" ? value : 0)
  }, 0)
}

function aggregateResource(runs: MetricRun[], key: string): number {
  return runs.reduce((total, run) => {
    if (run.status !== "available") return total
    const totals = run.metrics.resource_estimate.totals as Record<string, number>
    return total + (typeof totals[key] === "number" ? totals[key] : 0)
  }, 0)
}

function aggregateKindCount(runs: MetricRun[], key: string): number {
  return runs.reduce((total, run) => {
    if (run.status !== "available") return total
    return total + (run.metrics.counts.by_kind[key] ?? 0)
  }, 0)
}

function metricContractKey(run: AvailableMetricRun): string {
  const { coverage, kind, rates, schema_version: schemaVersion } = run.metrics
  return JSON.stringify({
    schemaVersion,
    kind,
    start: coverage.start,
    end: coverage.end,
    timezone: coverage.timezone,
    calendarDays: coverage.calendar_days,
    elapsedHours: coverage.elapsed_hours,
    partialWeek: coverage.partial_week,
    denominator: rates.denominator_note,
  })
}

function metricSource(run: AvailableMetricRun): MetricTrendSource {
  return {
    targetThreadId: run.target_thread_id,
    targetLabel: run.target_label,
    metricId: run.metrics.report_id,
    sourceRoot: run.metrics.source.source_root,
    firstRecordId: run.metrics.source.first_record_id,
    lastRecordId: run.metrics.source.last_record_id,
  }
}

function aggregateDisplay(
  state: MetricAggregateState,
  value: number,
  options: { currency?: boolean } = {},
): string {
  if (state === "unavailable") return "Unavailable"
  if (state === "incompatible") return "Incomparable"
  const formatted = numberFormatter.format(value)
  return options.currency ? `$${formatted}` : formatted
}

function metricTrend(runs: MetricRun[], windowFilter: WindowFilter): MetricTrendPoint[] {
  const points = new Map<string, MetricTrendPoint>()
  for (const run of runs) {
    if (run.status !== "available") continue
    const incidents = new Map(run.metrics.daily_incidents.map((item) => [item.date, item.opened]))
    const resources = new Map(
      run.metrics.resource_estimate.daily.map((item) => [item.date, item.estimated_tokens_base]),
    )
    for (const day of run.metrics.daily_activity) {
      const timestamp = `${day.date}T23:59:59Z`
      if (!inWindow(timestamp, windowFilter)) continue
      const current = points.get(day.date) ?? {
        date: day.date,
        activity: 0,
        incidents: 0,
        estimatedTokens: 0,
        sources: [],
      }
      current.activity += day.mechanical + day.review + day.routing + day.intervention + day.communication + day.maintenance + day.other
      current.incidents += incidents.get(day.date) ?? 0
      current.estimatedTokens += resources.get(day.date) ?? 0
      if (!current.sources.some((source) => source.targetThreadId === run.target_thread_id)) {
        current.sources.push(metricSource(run))
      }
      points.set(day.date, current)
    }
  }
  return [...points.values()].sort((left, right) => left.date.localeCompare(right.date))
}

function boundedMetricTrend(points: MetricTrendPoint[]): {
  points: MetricTrendPoint[]
  sourceDays: number
  bucketSize: number
} {
  if (points.length <= MAX_TREND_POINTS) {
    return { points, sourceDays: points.length, bucketSize: 1 }
  }
  const bucketSize = Math.ceil(points.length / MAX_TREND_POINTS)
  const bounded: MetricTrendPoint[] = []
  for (let index = 0; index < points.length; index += bucketSize) {
    const members = points.slice(index, index + bucketSize)
    const first = members[0]!
    const last = members.at(-1)!
    bounded.push({
      date: first.date === last.date ? first.date : `${first.date}…${last.date}`,
      activity: members.reduce((sum, point) => sum + point.activity, 0),
      incidents: members.reduce((sum, point) => sum + point.incidents, 0),
      estimatedTokens: members.reduce((sum, point) => sum + point.estimatedTokens, 0),
      sources: members
        .flatMap((point) => point.sources)
        .filter((source, index, sources) => sources.findIndex(
          (candidate) => candidate.targetThreadId === source.targetThreadId
            && candidate.metricId === source.metricId,
        ) === index),
    })
  }
  return { points: bounded, sourceDays: points.length, bucketSize }
}

function modelReasoningSummary(runs: MetricRun[]): string {
  const counts = new Map<string, number>()
  for (const run of runs) {
    if (run.status !== "available") continue
    for (const [identity, count] of Object.entries(run.metrics.counts.by_model_reasoning)) {
      counts.set(identity, (counts.get(identity) ?? 0) + count)
    }
  }
  return [...counts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([identity, count]) => `${identity} ${numberFormatter.format(count)}`)
    .join("; ") || "no attributed model/reasoning records"
}

function MetricCard({
  label,
  definition,
  values,
  coverage,
}: {
  label: string
  definition: string
  values: readonly [string, string][]
  coverage: string
}) {
  return (
    <section className="report-metric-card" aria-label={label}>
      <strong>{label}</strong>
      <p>{definition}</p>
      <dl>
        {values.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}
      </dl>
      <small>{coverage}</small>
    </section>
  )
}

function ReportComparison({ reports }: { reports: ReportDetail[] }) {
  if (reports.length !== 2) return null
  const [left, right] = reports
  const bothWeekly = left.family === "weekly" && right.family === "weekly"
  const sameCoverageDuration = Boolean(
    left.metric_summary
    && right.metric_summary
    && left.metric_summary.coverage.partial_week === right.metric_summary.coverage.partial_week
    && Math.abs(
      left.metric_summary.coverage.elapsed_hours
      - right.metric_summary.coverage.elapsed_hours,
    ) <= 1 / 60,
  )
  const compatible = Boolean(
    bothWeekly
    && left.metric_summary
    && right.metric_summary
    && left.metric_summary.schema_version === right.metric_summary.schema_version
    && left.metric_summary.kind === right.metric_summary.kind
    && left.metric_summary.coverage.timezone === right.metric_summary.coverage.timezone
    && sameCoverageDuration
  )
  const reason = !bothWeekly
    ? "Numeric comparison is available only for weekly metric contracts."
    : !left.metric_summary || !right.metric_summary
      ? "One report has no verified metric summary."
      : left.metric_summary.schema_version !== right.metric_summary.schema_version
        ? "Metric schema versions differ."
        : left.metric_summary.coverage.timezone !== right.metric_summary.coverage.timezone
          ? "Coverage time zones differ."
          : !sameCoverageDuration
            ? "Coverage durations or partial-window postures differ."
            : null
  const leftHeadline = left.metric_summary?.headline ?? {}
  const rightHeadline = right.metric_summary?.headline ?? {}
  const keys = compatible
    ? [...new Set([...Object.keys(leftHeadline), ...Object.keys(rightHeadline)])]
    : []

  return (
    <section className="workspace-panel report-comparison" aria-labelledby="report-comparison-heading">
      <div className="workspace-panel-heading">
        <h2 id="report-comparison-heading">Compare</h2>
        <StatusMark status={compatible ? "compatible" : "incompatible"} />
      </div>
      <div className="report-contract-strip">
        <span>Definition</span>
        <code>{left.metric_summary?.kind ?? left.family}</code>
        <code>{right.metric_summary?.kind ?? right.family}</code>
        <span>Version</span>
        <code>{left.metric_summary?.schema_version ?? "—"}</code>
        <code>{right.metric_summary?.schema_version ?? "—"}</code>
        <span>Coverage</span>
        <code>{left.coverage ? `${left.coverage.start} → ${left.coverage.end} · ${left.coverage.elapsed_hours} h · ${left.coverage.timezone}${left.coverage.partial_week ? " · partial" : ""}` : "Unavailable"}</code>
        <code>{right.coverage ? `${right.coverage.start} → ${right.coverage.end} · ${right.coverage.elapsed_hours} h · ${right.coverage.timezone}${right.coverage.partial_week ? " · partial" : ""}` : "Unavailable"}</code>
      </div>
      {reason ? <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />{reason} No numeric delta was computed.</div> : (
        <div className="table-scroll">
          <table className="report-data-table">
            <thead><tr><th>Metric</th><th>{left.id}</th><th>{right.id}</th><th>Delta</th></tr></thead>
            <tbody>
              {keys.map((key) => {
                const leftValue = leftHeadline[key as keyof typeof leftHeadline]
                const rightValue = rightHeadline[key as keyof typeof rightHeadline]
                const delta = Number(rightValue) - Number(leftValue)
                return <tr key={key}><th>{key.replaceAll("_", " ")}</th><td>{leftValue}</td><td>{rightValue}</td><td>{delta > 0 ? "+" : ""}{delta}</td></tr>
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get("view") === "reports" ? "reports" : "metrics"
  const projectFilter = searchParams.get("project") ?? "all"
  const runFilter = searchParams.get("run") ?? "all"
  const windowFilter = (["24h", "7d", "30d"].includes(searchParams.get("window") ?? "") ? searchParams.get("window") : "all") as WindowFilter
  const timezoneFilter = searchParams.get("timezone") ?? "all"
  const familyFilter = searchParams.get("family") ?? "all"
  const postureFilter = searchParams.get("posture") ?? "all"
  const selectedIdentity = parseReportKey(searchParams.get("report"))
  const comparedKeys = (searchParams.get("compare") ?? "").split("~").filter(Boolean).slice(0, 2)

  const metricsQuery = useQuery({ queryKey: ["metrics"], queryFn: ({ signal }) => fetchMetrics(signal) })
  const reportsQuery = useQuery({ queryKey: ["reports"], queryFn: ({ signal }) => fetchReports(signal) })
  const projectsQuery = useQuery({ queryKey: ["projects", false], queryFn: ({ signal }) => fetchProjects(false, signal) })
  const selectedQuery = useQuery({
    queryKey: ["report", selectedIdentity?.target, selectedIdentity?.family, selectedIdentity?.id],
    queryFn: ({ signal }) => fetchReport(selectedIdentity!.target, selectedIdentity!.family, selectedIdentity!.id, signal),
    enabled: Boolean(selectedIdentity),
  })

  const allReports = reportsQuery.data?.data.reports ?? []
  const comparedReports = comparedKeys
    .map((key) => allReports.find((report) => reportKey(report) === key))
    .filter((report): report is ReportArtifact => Boolean(report))
  const comparisonQueries = useQueries({
    queries: comparedReports.map((report) => ({
      queryKey: ["report", report.target_thread_id, report.family, report.id],
      queryFn: ({ signal }: { signal: AbortSignal }) => fetchReport(report.target_thread_id, report.family, report.id, signal),
      enabled: report.status === "available",
    })),
  })

  const artifactName = searchParams.get("artifact")
  const selectedArtifact = selectedQuery.data?.data.report.artifacts.find((artifact) => artifact.name === artifactName)
  const artifactQuery = useQuery({
    queryKey: ["report-artifact", selectedArtifact?.preview_url],
    queryFn: ({ signal }) => fetchReportArtifactText(selectedArtifact!.preview_url!, signal),
    enabled: Boolean(selectedArtifact?.preview_url && selectedArtifact.media_type !== "application/pdf"),
  })

  const updateParam = (name: string, value: string | null) => {
    const next = new URLSearchParams(searchParams)
    if (!value || value === "all") next.delete(name)
    else next.set(name, value)
    if (name === "view") {
      next.delete("report")
      next.delete("artifact")
    }
    setSearchParams(next)
  }

  const projectLabels = new Map(
    (projectsQuery.data?.data.projects ?? []).map((project) => [project.id, project.label]),
  )
  const metricRuns = metricsQuery.data?.data.per_run ?? []
  const timezones = [...new Set(metricRuns.flatMap((run) => run.status === "available" ? [run.metrics.coverage.timezone] : []))].sort()
  const runsMatchingProject = metricRuns.filter((run) => projectFilter === "all" || run.project_binding.project_id === projectFilter)
  const visibleRuns = runsMatchingProject.filter((run) => {
    if (runFilter !== "all" && run.target_thread_id !== runFilter) return false
    if (run.status !== "available") return timezoneFilter === "all"
    if (timezoneFilter !== "all" && run.metrics.coverage.timezone !== timezoneFilter) return false
    return inWindow(run.metrics.coverage.end, windowFilter)
  })
  const availableRuns = visibleRuns.filter((run): run is Extract<MetricRun, { status: "available" }> => run.status === "available")
  const metricContractKeys = new Set(availableRuns.map(metricContractKey))
  const metricAggregateState: MetricAggregateState = availableRuns.length === 0
    ? "unavailable"
    : metricContractKeys.size === 1
      ? "available"
      : "incompatible"
  const aggregateRuns = metricAggregateState === "available" ? availableRuns : []
  const selectedMetric = aggregateRuns[0]?.metrics
  const metricCoverageLabel = metricAggregateState === "available"
    ? `${availableRuns.length}/${visibleRuns.length} runs · one exact definition and coverage contract`
    : metricAggregateState === "incompatible"
      ? `${availableRuns.length}/${visibleRuns.length} runs · ${metricContractKeys.size} incompatible definition or coverage contracts; select one run`
      : `0/${visibleRuns.length} runs · unavailable; no numeric zero substituted`
  const trendProjection = useMemo(
    () => boundedMetricTrend(metricAggregateState === "available" ? metricTrend(aggregateRuns, windowFilter) : []),
    [aggregateRuns, windowFilter, metricAggregateState],
  )
  const trend = trendProjection.points
  const visibleTransitions = (metricsQuery.data?.data.factory_history.posture_transitions ?? []).filter((transition) => {
    if (projectFilter !== "all" && transition.project_id !== projectFilter) return false
    if (runFilter !== "all" && transition.target_thread_id !== runFilter) return false
    return inWindow(transition.record.timestamp, windowFilter)
  })
  const visibleScheduledHours = aggregateRuns.reduce((total, run) => total + run.metrics.availability.core_heartbeats_scheduled_active_hours, 0)
  const visiblePausedHours = aggregateRuns.reduce((total, run) => total + run.metrics.availability.core_heartbeats_explicitly_paused_hours, 0)
  const visibleSupervisorGroups = new Set(
    visibleRuns.flatMap((run) => run.supervisor_group_id ? [run.supervisor_group_id] : []),
  ).size
  const visibleBoundProjects = new Set(visibleRuns.flatMap((run) => run.project_binding.project_id ? [run.project_binding.project_id] : []))
  const visibleConclusionCount = visibleRuns.reduce(
    (sum, run) => sum + Object.values(run.conclusion_counts.by_kind).reduce((left, right) => left + right, 0),
    0,
  )
  const roleRows = availableRuns.flatMap((run) => run.metrics.monitoring_roles.roles)
  const roleSummary = [...new Map(roleRows.map((role) => [role.role, role])).values()]
    .map((role) => `${role.purpose} (${role.role})`)
    .join("; ") || "Unavailable"
  const categoryCounts = new Map<string, number>()
  for (const run of aggregateRuns) {
    for (const [category, count] of Object.entries(run.metrics.counts.by_category)) {
      categoryCounts.set(category || "uncategorized", (categoryCounts.get(category || "uncategorized") ?? 0) + count)
    }
  }
  const categorySummary = metricAggregateState === "available"
    ? [...categoryCounts.entries()]
        .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
        .slice(0, 8)
        .map(([category, count]) => `${category} ${numberFormatter.format(count)}`)
        .join("; ") || "Unavailable"
    : [...new Set(availableRuns.flatMap((run) => Object.keys(run.metrics.counts.by_category).map((category) => category || "uncategorized")))]
        .sort()
        .slice(0, 8)
        .join("; ") + (availableRuns.length ? " · counts withheld across incompatible contracts" : "Unavailable")
  const observedTimes = aggregateRuns.map((run) => run.observed_at).sort()
  const metricLimitations = [...new Set([
    ...(selectedMetric?.limitations ?? []),
    ...(metricsQuery.data?.limitations ?? []),
  ])]
  const projectOptions = [...new Set(metricRuns.flatMap((run) => run.project_binding.project_id ? [run.project_binding.project_id] : []))]
    .sort((left, right) => (projectLabels.get(left) ?? left).localeCompare(projectLabels.get(right) ?? right))

  const reportRunProject = new Map(metricRuns.map((run) => [run.target_thread_id, run.project_binding.project_id]))
  const visibleEvolutionWorkflows = (reportsQuery.data?.data.evolution_workflows ?? []).filter((item) => {
    if (projectFilter !== "all" && item.project_binding.project_id !== projectFilter) return false
    if (runFilter !== "all" && item.target_thread_id !== runFilter) return false
    return true
  })
  const visibleReports = allReports.filter((report) => {
    if (projectFilter !== "all" && reportRunProject.get(report.target_thread_id) !== projectFilter) return false
    if (runFilter !== "all" && report.target_thread_id !== runFilter) return false
    if (familyFilter !== "all" && report.family !== familyFilter) return false
    if (postureFilter === "verified" && report.status !== "available") return false
    if (postureFilter === "partial" && report.status !== "unavailable") return false
    if (!inWindow(report.coverage?.end, windowFilter) && windowFilter !== "all") return false
    return true
  })
  const runByTarget = new Map(metricRuns.map((run) => [run.target_thread_id, run]))

  const toggleComparison = (report: ReportArtifact) => {
    const key = reportKey(report)
    const nextKeys = comparedKeys.includes(key)
      ? comparedKeys.filter((item) => item !== key)
      : [...comparedKeys, key].slice(-2)
    updateParam("compare", nextKeys.length ? nextKeys.join("~") : null)
  }

  const selectReport = (report: ReportArtifact) => {
    const next = new URLSearchParams(searchParams)
    next.set("view", "reports")
    next.set("report", reportKey(report))
    next.delete("artifact")
    setSearchParams(next)
  }

  const compareDetails = comparisonQueries
    .map((query) => query.data?.data.report)
    .filter((report): report is ReportDetail => Boolean(report))

  const renderedArtifact = (() => {
    if (!selectedArtifact) return null
    if (selectedArtifact.media_type === "application/pdf") {
      return <div className="report-pdf-actions"><a href={selectedArtifact.preview_url ?? undefined} target="_blank" rel="noreferrer"><ExternalLink aria-hidden="true" />Open verified PDF</a><a href={selectedArtifact.download_url ?? undefined}><Download aria-hidden="true" />Download</a></div>
    }
    if (artifactQuery.isPending) return <QueryState kind="loading" message="Loading verified artifact" />
    if (artifactQuery.isError) return <QueryState kind="error" message={artifactQuery.error.message} />
    if (selectedArtifact.media_type === "text/markdown") return <SafeMarkdown markdown={artifactQuery.data} />
    try {
      return <pre className="report-json-preview">{JSON.stringify(JSON.parse(artifactQuery.data), null, 2)}</pre>
    } catch {
      return <QueryState kind="error" message="Verified JSON artifact could not be parsed safely" />
    }
  })()

  return (
    <div className="page-stack reports-page">
      <div className="workspace-toolbar report-mode-toolbar">
        <div className="report-mode-switch" role="group" aria-label="Workspace">
          <Button variant={view === "metrics" ? "default" : "ghost"} size="compact" onClick={() => updateParam("view", "metrics")}>Metrics</Button>
          <Button variant={view === "reports" ? "default" : "ghost"} size="compact" onClick={() => updateParam("view", "reports")}>Reports</Button>
        </div>
        <label>Project<select aria-label="Project" value={projectFilter} onChange={(event) => updateParam("project", event.target.value)}><option value="all">All</option>{projectOptions.map((id) => <option value={id} key={id}>{projectLabels.get(id) ?? id}</option>)}</select></label>
        <label>Run<select aria-label="Run" value={runFilter} onChange={(event) => updateParam("run", event.target.value)}><option value="all">All</option>{runsMatchingProject.map((run) => <option value={run.target_thread_id} key={run.target_thread_id}>{run.target_label}</option>)}</select></label>
        <label>Window<select aria-label="Window" value={windowFilter} onChange={(event) => updateParam("window", event.target.value)}><option value="all">All observed</option><option value="24h">24 hours</option><option value="7d">7 days</option><option value="30d">30 days</option></select></label>
        {view === "metrics" ? <label>Timezone<select aria-label="Timezone" value={timezoneFilter} onChange={(event) => updateParam("timezone", event.target.value)}><option value="all">All when compatible</option>{timezones.map((timezone) => <option value={timezone} key={timezone}>{timezone}</option>)}</select></label> : <>
          <label>Type<select aria-label="Type" value={familyFilter} onChange={(event) => updateParam("family", event.target.value)}><option value="all">All</option><option value="weekly">Weekly</option><option value="terminal">Terminal</option><option value="factory-evolution">Evolution</option></select></label>
          <label>Posture<select aria-label="Posture" value={postureFilter} onChange={(event) => updateParam("posture", event.target.value)}><option value="all">All</option><option value="verified">Verified</option><option value="partial">Invalid / partial</option></select></label>
        </>}
        <Button variant="ghost" size="compact" onClick={() => window.print()}><Printer aria-hidden="true" />Print</Button>
      </div>

      {view === "metrics" ? metricsQuery.isPending ? <QueryState kind="loading" message="Loading metrics" /> : metricsQuery.isError ? <QueryState kind="error" message={metricsQuery.error.message} retry={() => void metricsQuery.refetch()} /> : <>
        <div className="report-metric-grid">
          <MetricCard label="Delivery" definition="Recorded canonical supervision events, changed-state routes, and observed Blocks in one exact coverage contract." coverage={metricCoverageLabel} values={[["Recorded events", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "recorded_events"))], ["Changed-state routes", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "changed_state_routes"))], ["Blocks observed", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "blocks_observed"))]]} />
          <MetricCard label="Reliability" definition="Recorded incident openings and terminal heads; this is not continuous process uptime or implementation quality." coverage={metricCoverageLabel} values={[["Incidents opened", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "incidents_opened"))], ["Terminal incidents", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "incidents_terminal"))], ["Open at end", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "incidents_open_at_end"))]]} />
          <MetricCard label="Review" definition="Recorded correction, decision, and resolution events; configured roles are not inferred as event actors." coverage={metricCoverageLabel} values={[["Corrections", aggregateDisplay(metricAggregateState, aggregateCount(aggregateRuns, "corrections_issued"))], ["Decisions", aggregateDisplay(metricAggregateState, aggregateKindCount(aggregateRuns, "decision"))], ["Resolutions", aggregateDisplay(metricAggregateState, aggregateKindCount(aggregateRuns, "resolution"))]]} />
          <MetricCard label="Resources" definition="Versioned content-derived token and API-equivalent estimate; never provider usage or billed cost." coverage={`${metricCoverageLabel} · ${metricAggregateState === "available" ? modelReasoningSummary(aggregateRuns) : "model/reasoning aggregate withheld"}`} values={[["Estimated tokens", aggregateDisplay(metricAggregateState, aggregateResource(aggregateRuns, "estimated_tokens_base"))], ["Estimated cost", aggregateDisplay(metricAggregateState, aggregateResource(aggregateRuns, "projected_cost_usd_base"), { currency: true })], ["Attributed events", aggregateDisplay(metricAggregateState, aggregateResource(aggregateRuns, "recorded_model_attributed_events"))]]} />
        </div>

        <section className="workspace-panel metric-contract-context" aria-label="Metric contract and sources">
          <dl>
            <div><dt>Aggregate</dt><dd><StatusMark status={metricAggregateState} />{metricAggregateState === "available" ? "Exact compatible cohort" : metricAggregateState === "incompatible" ? "Numeric aggregate withheld" : "No available metric projection"}</dd></div>
            <div><dt>Definition</dt><dd>{selectedMetric ? `${selectedMetric.kind} · schema v${selectedMetric.schema_version}` : `${metricContractKeys.size} incompatible or unavailable contracts`}</dd></div>
            <div><dt>Period</dt><dd>{selectedMetric ? <><TimeValue value={selectedMetric.coverage.start} /> → <TimeValue value={selectedMetric.coverage.end} /> · {selectedMetric.coverage.elapsed_hours} h · {selectedMetric.coverage.timezone}{selectedMetric.coverage.partial_week ? " · partial" : ""}</> : "Unavailable until one exact coverage contract is selected"}</dd></div>
            <div><dt>Denominator</dt><dd>{selectedMetric?.rates.denominator_note ?? "No cross-contract denominator was computed."}</dd></div>
            <div><dt>Observed</dt><dd>{observedTimes.length ? <><TimeValue value={observedTimes[0]} />{observedTimes.length > 1 ? <> → <TimeValue value={observedTimes.at(-1)} /></> : null}</> : "Unavailable"}</dd></div>
            <div><dt>Limitations</dt><dd>{metricLimitations.length ? metricLimitations.join(" ") : "Unavailable projections remain independent and are not rendered as zero."}</dd></div>
          </dl>
          <div className="metric-review-context">
            <p><strong>Recorded roles</strong>{roleSummary}. Role activity attribution remains unavailable unless a canonical event names its actor.</p>
            <p><strong>Top categories</strong>{categorySummary}</p>
            <p><strong>Current state</strong>{numberFormatter.format(visibleConclusionCount)} conclusions · {numberFormatter.format(visibleTransitions.length)} matching posture transitions. These are current source records, not weekly metric values.</p>
          </div>
          <div className="metric-source-list" aria-label="Metric source projections">
            {availableRuns.length ? availableRuns.map((run) => <div key={run.target_thread_id}><Link to={`/runs/${encodeURIComponent(run.target_thread_id)}#current-metric`}>{run.target_label}</Link><Identity value={run.metrics.report_id} /><Identity value={run.metrics.source.source_root} />{run.metrics.source.first_record_id ? <Link to={`/runs/${encodeURIComponent(run.target_thread_id)}#${encodeURIComponent(run.metrics.source.last_record_id ?? run.metrics.source.first_record_id)}`}>Events {run.metrics.source.first_record_id}–{run.metrics.source.last_record_id ?? "latest"}</Link> : <span>Canonical record range unavailable</span>}</div>) : <span>No available metric source projection</span>}
          </div>
        </section>

        <section className="workspace-panel report-trend-panel" aria-labelledby="metric-trend-heading">
          <div className="workspace-panel-heading"><h2 id="metric-trend-heading">Trend</h2><span>{metricAggregateState === "available" ? `${trend.length} displayed buckets from ${trendProjection.sourceDays} source days · exact selected contract` : metricAggregateState === "incompatible" ? `${metricContractKeys.size} incompatible contracts` : "Source metrics unavailable"}</span></div>
          {metricAggregateState === "incompatible" ? <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />Select one run or an exact shared definition, period, timezone, partial-window, and denominator contract. Incompatible metrics were not combined.</div> : metricAggregateState === "unavailable" ? <QueryState kind="empty" message="No available metric projection matches the filters; unavailable values were not rendered as zero" /> : trend.length ? <><MetricHistoryChart points={trend} /><div className="table-scroll"><table className="report-data-table"><caption className="sr-only">Exact accessible values and sources for the metric trend</caption><thead><tr><th>Date</th><th>Recorded activity</th><th>Incidents opened</th><th>Estimated tokens</th><th>Sources</th></tr></thead><tbody>{trend.map((point) => <tr key={point.date}><th>{point.date}</th><td>{point.activity}</td><td>{point.incidents}</td><td>{numberFormatter.format(point.estimatedTokens)}</td><td><div className="metric-trend-sources">{point.sources.map((source) => <span key={`${source.targetThreadId}:${source.metricId}`}><Link to={`/runs/${encodeURIComponent(source.targetThreadId)}#current-metric`}>{source.targetLabel} metric</Link><Identity value={source.metricId} />{source.firstRecordId ? <Link to={`/runs/${encodeURIComponent(source.targetThreadId)}#${encodeURIComponent(source.lastRecordId ?? source.firstRecordId)}`}>{source.firstRecordId}–{source.lastRecordId ?? "latest"}</Link> : null}</span>)}</div></td></tr>)}</tbody></table></div></> : <QueryState kind="empty" message="No compatible metric points match the filters" />}
          <p className="workspace-limitation">Daily buckets retain the selected owner contract and source timezone. Different definitions, coverage intervals, timezones, partial-window postures, or denominators are never combined.{trendProjection.bucketSize > 1 ? ` More than ${MAX_TREND_POINTS} source days are summed into contiguous buckets of at most ${trendProjection.bucketSize} days for this display.` : ""}</p>
        </section>

        <section className="workspace-panel" aria-labelledby="metric-runs-heading">
          <div className="workspace-panel-heading"><h2 id="metric-runs-heading">Runs</h2><span>{visibleRuns.length} source projections</span></div>
          <div className="table-scroll"><table className="report-data-table"><thead><tr><th>Project / run</th><th>Posture</th><th>Period</th><th>Coverage</th><th>Incidents / review</th><th>Estimate</th></tr></thead><tbody>{visibleRuns.map((run) => <tr key={run.target_thread_id}><th><span>{run.project_binding.project_id ? projectLabels.get(run.project_binding.project_id) ?? run.project_binding.project_id : "Unassigned"}</span><Link to={`/runs/${encodeURIComponent(run.target_thread_id)}`}>{run.target_label}</Link><Identity value={run.target_thread_id} />{run.status === "available" ? <><Link to={`/runs/${encodeURIComponent(run.target_thread_id)}#current-metric`}>Metric source</Link><Identity value={run.metrics.report_id} /></> : null}</th><td><StatusMark status={run.light.posture} /></td><td>{run.status === "available" ? <><TimeValue value={run.metrics.coverage.start} /> → <TimeValue value={run.metrics.coverage.end} /></> : "Unavailable"}</td><td>{run.status === "available" ? <>{numberFormatter.format(run.metrics.coverage.elapsed_hours)} h · {run.metrics.coverage.timezone}<small>Generated <TimeValue value={run.observed_at} /></small></> : run.error.message}</td><td>{run.status === "available" ? <>{run.metrics.headline.incidents_opened}<small>Median {run.metrics.rates.incident_detection_to_terminal_median_hours ?? "—"} h · P90 {run.metrics.rates.incident_detection_to_terminal_p90_hours ?? "—"} h</small><small>Decisions {run.metrics.counts.by_kind.decision ?? 0} · resolutions {run.metrics.counts.by_kind.resolution ?? 0} · conclusions {Object.values(run.conclusion_counts.by_kind).reduce((sum, count) => sum + count, 0)}</small></> : "—"}</td><td>{run.status === "available" ? `$${numberFormatter.format(run.metrics.resource_estimate.totals.projected_cost_usd_base)}` : "—"}</td></tr>)}</tbody></table></div>
        </section>

        <section className="workspace-panel" aria-labelledby="factory-history-heading">
          <div className="workspace-panel-heading"><h2 id="factory-history-heading">Factory history</h2><span>{Math.min(visibleTransitions.length, 80)} shown · {visibleTransitions.length} retained matches · {metricsQuery.data.data.factory_history.posture_transition_count} total exact transitions{metricsQuery.data.data.factory_history.posture_transitions_truncated ? " · retained window truncated" : ""}</span></div>
          <div className="report-history-summary"><span><strong>{visibleSupervisorGroups}</strong> supervisor groups</span><span><strong>{visibleBoundProjects.size}</strong> bound projects</span><span><strong>{visibleConclusionCount}</strong> current conclusions</span><span><strong>{aggregateDisplay(metricAggregateState, visibleScheduledHours)} / {aggregateDisplay(metricAggregateState, visiblePausedHours)}</strong> scheduled / paused hours</span></div>
          <div className="table-scroll"><table className="report-data-table"><thead><tr><th>Observed</th><th>Run</th><th>Transition</th><th>Trigger / source</th></tr></thead><tbody>{visibleTransitions.slice(-80).reverse().map((transition, index) => <tr key={`${transition.target_thread_id}:${transition.record.record_id}:${index}`}><td><TimeValue value={transition.record.timestamp} /></td><th><Link to={`/runs/${encodeURIComponent(transition.target_thread_id)}`}>{transition.target_label}</Link><Identity value={transition.target_thread_id} /></th><td><StatusMark status={transition.to} /><span>{transition.from} → {transition.to}</span></td><td>{transition.trigger}<Identity value={transition.record.record_id} /></td></tr>)}</tbody></table></div>
          <div className="workspace-warning-list">{metricsQuery.data.data.factory_history.unsupported.map((item) => <span key={item}><AlertTriangle aria-hidden="true" />{item}</span>)}</div>
        </section>
      </> : reportsQuery.isPending ? <QueryState kind="loading" message="Loading report history" /> : reportsQuery.isError ? <QueryState kind="error" message={reportsQuery.error.message} retry={() => void reportsQuery.refetch()} /> : <>
        <section className="workspace-panel evolution-workflow-inventory" aria-labelledby="evolution-workflow-heading">
          <div className="workspace-panel-heading"><h2 id="evolution-workflow-heading">Evolution</h2><span>{visibleEvolutionWorkflows.length} current source projection{visibleEvolutionWorkflows.length === 1 ? "" : "s"}</span></div>
          {visibleEvolutionWorkflows.length ? <div className="workspace-record-list">{visibleEvolutionWorkflows.map(({ target_thread_id: targetId, target_label: targetLabel, project_binding: projectBinding, workflow }) => (
            <article className="workspace-record evolution-workflow-row" key={targetId}>
              <div><Link to={`/runs/${encodeURIComponent(targetId)}`}>{targetLabel}</Link><Identity value={targetId} /></div>
              <StatusMark status={workflow.stage} />
              <span>{projectBinding.project_id ?? "Unassigned"} · {workflow.next_action ?? "No next stage"}</span>
              <span>{workflow.stages.map((stage) => `${stage.label}: ${stage.status}`).join(" · ") || workflow.error?.message || "Stage source unavailable"}</span>
              <span>External implementation: {workflow.implementer.status}{workflow.implementer.candidate_revision ? ` · ${workflow.implementer.baseline_revision} → ${workflow.implementer.candidate_revision}` : ""}</span>
              <span>{workflow.disposition ? `Disposition: ${workflow.disposition}` : "Disposition unavailable"}</span>
              <Identity value={workflow.packet_root} />
              <Identity value={workflow.review_root} />
              <Identity value={workflow.evaluation_root} />
              <small>Adoption, installation, routing, scheduling, deployment, rollback, and outcome: not performed by evolution.</small>
              <FactoryEvolutionEvidence workflow={workflow} targetId={targetId} />
            </article>
          ))}</div> : <QueryState kind="empty" message="No current Factory-evolution projection matches the filters" />}
        </section>

        <section className="workspace-panel report-inventory" aria-labelledby="report-inventory-heading">
          <div className="workspace-panel-heading"><h2 id="report-inventory-heading">History</h2><span>{visibleReports.length} of {allReports.length}</span></div>
          {visibleReports.length ? <div className="table-scroll"><table className="report-data-table"><thead><tr><th>Report</th><th>Project / run</th><th>Posture</th><th>Delivery</th><th>Period</th><th>Compare</th></tr></thead><tbody>{visibleReports.map((report) => { const key = reportKey(report); const run = runByTarget.get(report.target_thread_id); return <tr key={key} className={selectedIdentity && reportKey(report) === searchParams.get("report") ? "report-row-selected" : undefined}><th><button type="button" className="report-row-button" onClick={() => selectReport(report)}><span>{report.family}</span><strong>{report.id}</strong></button></th><td><span>{reportRunProject.get(report.target_thread_id) ? projectLabels.get(reportRunProject.get(report.target_thread_id)!) ?? reportRunProject.get(report.target_thread_id) : "Unassigned"}</span><Link to={`/runs/${encodeURIComponent(report.target_thread_id)}`}>{run?.target_label ?? "Run source"}</Link><Identity value={report.target_thread_id} /></td><td><StatusMark status={report.status === "available" ? report.stage : "invalid"} /><small>{report.disposition ?? report.error?.message ?? "No disposition"}</small></td><td>{report.delivery ? <><StatusMark status={report.delivery.status} /><small>{report.delivery.reason ?? report.delivery.record_id ?? "Current"}</small></> : "Not applicable"}</td><td>{report.coverage ? <><TimeValue value={report.coverage.start} /> → <TimeValue value={report.coverage.end} /></> : "Unavailable"}</td><td><label className="report-compare-check"><input type="checkbox" checked={comparedKeys.includes(key)} disabled={report.status !== "available"} onChange={() => toggleComparison(report)} />Select</label></td></tr>})}</tbody></table></div> : <QueryState kind="empty" message="No reports match the current filters" />}
        </section>

        {comparedKeys.length > 0 && <section className="workspace-panel report-compare-selection" aria-label="Comparison selection"><span>{comparedKeys.length}/2 selected</span>{comparisonQueries.some((query) => query.isPending) ? <span>Loading exact contracts</span> : comparisonQueries.some((query) => query.isError) ? <span className="workspace-error-text">A selected report is unavailable</span> : <span>Exact report details loaded</span>}</section>}
        <ReportComparison reports={compareDetails} />

        {selectedIdentity && (selectedQuery.isPending ? <QueryState kind="loading" message="Loading report detail" /> : selectedQuery.isError ? <QueryState kind="error" message={selectedQuery.error.message} /> : <section className="workspace-panel report-detail" aria-labelledby="report-detail-heading">
          <div className="workspace-panel-heading"><h2 id="report-detail-heading">Detail</h2><StatusMark status={selectedQuery.data.data.report.status === "available" ? selectedQuery.data.data.report.stage : "invalid"} /></div>
          <div className="report-detail-identity"><div><strong>{selectedQuery.data.data.report.id}</strong><span>{selectedQuery.data.data.report.family} · {selectedQuery.data.data.report.disposition ?? "No disposition"}</span><Identity value={selectedQuery.data.data.report.target_thread_id} /></div><div><span>Source root</span><Identity value={selectedQuery.data.data.report.source_root} /><span>Manifest root</span><Identity value={selectedQuery.data.data.report.manifest_root} /></div></div>
          {selectedQuery.data.data.report.delivery && <div className="workspace-partial" role="status"><StatusMark status={selectedQuery.data.data.report.delivery.status} />Delivery · {selectedQuery.data.data.report.delivery.reason ?? selectedQuery.data.data.report.delivery.record_id ?? "Current owner receipt"}</div>}
          {selectedQuery.data.data.report.review_summary && <div className="report-review-summary"><strong>{selectedQuery.data.data.report.review_summary.headline}</strong><p>{selectedQuery.data.data.report.review_summary.assessment}</p></div>}
          {selectedQuery.data.data.report.error && <div className="workspace-partial" role="alert"><AlertTriangle aria-hidden="true" />{selectedQuery.data.data.report.error.message}. Artifacts remain metadata-only.</div>}
          <div className="report-artifact-list">{selectedQuery.data.data.report.artifacts.map((artifact) => <div key={artifact.name}><span>{artifact.media_type === "application/json" ? <FileJson aria-hidden="true" /> : <FileText aria-hidden="true" />}{artifact.name}<small>{numberFormatter.format(artifact.bytes)} bytes · {artifact.sha256.slice(0, 12)}</small></span><div>{artifact.preview_url && <Button variant="ghost" size="compact" onClick={() => updateParam("artifact", artifact.name)}>Preview</Button>}{artifact.media_type === "application/pdf" && artifact.preview_url && <a href={artifact.preview_url} target="_blank" rel="noreferrer"><ExternalLink aria-hidden="true" />Open</a>}{artifact.download_url && <a href={artifact.download_url}><Download aria-hidden="true" />Download</a>}</div></div>)}</div>
          {selectedArtifact && <div className="report-artifact-preview"><div className="workspace-panel-heading"><h2>{selectedArtifact.name}</h2><Button variant="ghost" size="compact" onClick={() => updateParam("artifact", null)}>Close</Button></div>{renderedArtifact}</div>}
          <div className="report-limitations"><strong>Limitations</strong>{selectedQuery.data.data.report.limitations.map((item) => <p key={item}>{item}</p>)}</div>
        </section>)}
      </>}

      {(metricsQuery.data?.coverage.status === "partial" || reportsQuery.data?.coverage.status === "partial") && <div className="workspace-partial" role="status"><AlertTriangle aria-hidden="true" />Partial owner coverage is retained. Missing sources are never rendered as zero, healthy, verified, or comparable.</div>}
    </div>
  )
}
