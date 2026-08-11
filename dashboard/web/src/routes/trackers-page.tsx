import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, GitCompareArrows, ListChecks } from "lucide-react"
import { Link, useSearchParams } from "react-router"

import {
  CountFilterChips,
  type CountFilterChip,
} from "@/components/factory-floor-patterns"
import { TrackerProgressView } from "@/components/tracker-progress-view"
import { Identity, QueryState, StatusMark, TimeValue } from "@/components/workspace-ui"
import { fetchFactoryFloor } from "@/lib/floor-api"
import {
  projectTrackerProgress,
  trackerAttentionReasons,
  trackerCountProjection,
  trackerMatchesActivity,
  type TrackerActivityFilter,
} from "@/lib/tracker-progress"
import { fetchTrackers } from "@/lib/trackers-api"

const activityFilters: Array<{
  key: TrackerActivityFilter
  label: string
  tone: CountFilterChip<TrackerActivityFilter>["tone"]
}> = [
  { key: "all", label: "All", tone: "neutral" },
  { key: "active", label: "Active / Running", tone: "active" },
  { key: "attention", label: "Attention", tone: "attention" },
  { key: "blocked", label: "Blocked / Failed", tone: "blocked" },
  { key: "completed", label: "Completed", tone: "completed" },
]

function activityFilter(value: string | null): TrackerActivityFilter {
  return activityFilters.some((filter) => filter.key === value)
    ? value as TrackerActivityFilter
    : "all"
}

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const trackers = useQuery({ queryKey: ["trackers"], queryFn: ({ signal }) => fetchTrackers(signal) })
  const floor = useQuery({ queryKey: ["factory-floor"], queryFn: ({ signal }) => fetchFactoryFloor(signal) })
  const projectFilter = searchParams.get("project") ?? "all"
  const selectedActivity = activityFilter(searchParams.get("activity"))

  if (trackers.isPending) return <QueryState kind="loading" message="Loading trackers" />
  if (trackers.isError) return <QueryState kind="error" message={trackers.error.message} retry={() => void trackers.refetch()} />

  const floorEnvelope = floor.data
  const projectOptions = [...new Map(trackers.data.data.trackers.map((tracker) => [tracker.project_id, tracker.project_label])).entries()]
    .sort((left, right) => left[1].localeCompare(right[1]))
  const projectTrackers = trackers.data.data.trackers.filter(
    (tracker) => projectFilter === "all" || tracker.project_id === projectFilter,
  )
  const progressById = new Map(
    projectTrackers.map((tracker) => [tracker.id, projectTrackerProgress(tracker, floorEnvelope)]),
  )
  const visible = projectTrackers.filter((tracker) =>
    trackerMatchesActivity(tracker, progressById.get(tracker.id)!, selectedActivity),
  )
  const countItems: Array<CountFilterChip<TrackerActivityFilter>> = activityFilters.map((filter) => {
    const count = projectTrackers.filter((tracker) =>
      trackerMatchesActivity(tracker, progressById.get(tracker.id)!, filter.key),
    ).length
    const projection = trackerCountProjection(trackers.data, floorEnvelope, filter.key, count)
    return {
      key: filter.key,
      label: filter.label,
      tone: filter.tone,
      countLabel: projection.countLabel,
      accessibleCount: projection.accessibleCount,
    }
  })
  const updateFilter = (name: "project" | "activity", value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value === "all") next.delete(name)
    else next.set(name, value)
    setSearchParams(next)
  }

  return (
    <div className="page-stack trackers-page">
      <div className="workspace-toolbar tracker-toolbar">
        <span>{visible.length} of {projectTrackers.length} represented trackers</span>
        <label>Project
          <select aria-label="Project" value={projectFilter} onChange={(event) => updateFilter("project", event.target.value)}>
            <option value="all">All</option>
            {projectOptions.map(([id, label]) => <option value={id} key={id}>{label}</option>)}
          </select>
        </label>
      </div>

      <CountFilterChips
        label="Tracker status"
        value={selectedActivity}
        items={countItems}
        onChange={(value) => updateFilter("activity", value)}
      />

      {visible.length === 0 ? <QueryState kind="empty" message="No trackers match the current filters" /> : (
        <div className="tracker-index-list">
          {visible.map((tracker) => {
            const progress = progressById.get(tracker.id)!
            const attention = trackerAttentionReasons(tracker, progress)
            const available = tracker.status === "available"
            const exactMappedRuns = progress.exactMappedRows.filter(
              (row) => row.supervision.run_id !== null,
            )
            return (
              <article
                className={`tracker-index-row tracker-progress-${progress.posture}`}
                key={tracker.id}
              >
                <div className="tracker-index-identity">
                  <span className="tracker-index-mark"><ListChecks aria-hidden="true" /></span>
                  <div>
                    {available ? <Link to={`/trackers/${tracker.id}`}>{tracker.title}</Link> : <strong>{tracker.relative_path}</strong>}
                    <span>{tracker.project_label} · {tracker.relative_path}</span>
                    <Identity value={tracker.id} />
                  </div>
                </div>

                <div className="tracker-index-posture">
                  {available ? (
                    <>
                      <StatusMark status={tracker.verifier.valid ? tracker.tracker_status ?? "available" : "invalid"} />
                      <span>{tracker.profile} profile · verifier {tracker.verifier.valid ? "valid" : "failed"}</span>
                      <span>Git {tracker.progress_posture} · {tracker.git.durability}</span>
                    </>
                  ) : <><StatusMark status="unavailable" /><span>{tracker.error.message}</span></>}
                </div>

                <TrackerProgressView
                  progress={progress}
                  accepted={available ? tracker.counts.accepted : null}
                  compact
                />

                {available ? (
                  <dl className="tracker-status-counts">
                    {Object.entries(tracker.counts.by_status).map(([status, count]) => <div key={status}><dt>{status}</dt><dd>{count}</dd></div>)}
                  </dl>
                ) : <div className="tracker-index-unavailable"><AlertTriangle aria-hidden="true" />Status counts unavailable</div>}

                <div className="tracker-index-run">
                  <span>Exact mapped run</span>
                  {exactMappedRuns.length ? exactMappedRuns.map((row) => (
                    <Link to={`/runs/${encodeURIComponent(row.supervision.run_id!)}`} key={row.id}>
                      <Identity value={row.supervision.run_id!} />
                    </Link>
                  )) : <strong>{progress.floorCoverage === "complete" ? "None exact" : "Unavailable"}</strong>}
                  <small>
                    {progress.excludedCandidateRows
                      ? `${progress.excludedCandidateRows} noncanonical candidate claim${progress.excludedCandidateRows === 1 ? "" : "s"} excluded`
                      : `${progress.floorCoverage} composed coverage`}
                  </small>
                </div>

                <div className={`tracker-index-attention ${attention.length ? "" : "tracker-index-attention-clear"}`}>
                  {attention.length ? <AlertTriangle aria-hidden="true" /> : <GitCompareArrows aria-hidden="true" />}
                  <div>
                    <span>Attention</span>
                    <strong>{attention[0] ?? "None"}</strong>
                    {attention.length > 1 && <small>+{attention.length - 1} more</small>}
                    <TimeValue value={available ? tracker.git.last_commit?.committed_at ?? tracker.observed_at : tracker.observed_at} />
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}

      {(floor.isError || trackers.data.coverage.status === "partial") && (
        <div className="workspace-partial" role="status">
          <AlertTriangle aria-hidden="true" />Tracker and composed-owner coverage remain independent; counts and claims are marked exact, partial, or unavailable.
        </div>
      )}
    </div>
  )
}
