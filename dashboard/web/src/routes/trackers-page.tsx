import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, GitCompareArrows, ListChecks } from "lucide-react"
import { Link, useSearchParams } from "react-router"

import { Identity, QueryState, StatusMark, TimeValue } from "@/components/workspace-ui"
import { fetchFactoryFloor } from "@/lib/floor-api"
import { fetchTrackers, type TrackerSummary } from "@/lib/trackers-api"

function attentionReason(tracker: TrackerSummary): string {
  if (tracker.status === "unavailable") return tracker.error.message
  if (!tracker.verifier.valid) return `${tracker.verifier.errors.length} verifier diagnostic${tracker.verifier.errors.length === 1 ? "" : "s"}`
  if (tracker.header_block_status_conflict) return "Header and Block statuses disagree"
  if (tracker.progress_posture === "dirty") return "Working tree differs from HEAD"
  if (tracker.progress_posture === "untracked") return "Tracker is untracked"
  if (tracker.progress_posture === "stale") return "Run-bound content hash is stale"
  if (tracker.git.durability !== "matched") return `Git durability is ${tracker.git.durability}`
  if (tracker.current_blocks.length > 1) return "Multiple Blocks are in progress"
  if (tracker.counts.open > 0 && tracker.current_blocks.length === 0 && tracker.eligible_blocks.length === 0) {
    return "Open work has no eligible Block"
  }
  return "None"
}

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const trackers = useQuery({ queryKey: ["trackers"], queryFn: ({ signal }) => fetchTrackers(signal) })
  const floor = useQuery({ queryKey: ["factory-floor"], queryFn: ({ signal }) => fetchFactoryFloor(signal) })
  const projectFilter = searchParams.get("project") ?? "all"
  const postureFilter = searchParams.get("posture") ?? "all"

  if (trackers.isPending) return <QueryState kind="loading" message="Loading trackers" />
  if (trackers.isError) return <QueryState kind="error" message={trackers.error.message} retry={() => void trackers.refetch()} />

  const projectOptions = [...new Map(trackers.data.data.trackers.map((tracker) => [tracker.project_id, tracker.project_label])).entries()]
    .sort((left, right) => left[1].localeCompare(right[1]))
  const visible = trackers.data.data.trackers.filter((tracker) => {
    if (projectFilter !== "all" && tracker.project_id !== projectFilter) return false
    if (postureFilter === "attention") return attentionReason(tracker) !== "None"
    if (postureFilter === "invalid") return tracker.status === "unavailable" || !tracker.verifier.valid
    if (postureFilter === "current") return tracker.status === "available" && tracker.progress_posture === "current"
    return true
  })
  const updateFilter = (name: "project" | "posture", value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value === "all") next.delete(name)
    else next.set(name, value)
    setSearchParams(next)
  }

  return (
    <div className="page-stack trackers-page">
      <div className="workspace-toolbar tracker-toolbar">
        <span>{visible.length} of {trackers.data.data.trackers.length} trackers</span>
        <label>Project
          <select value={projectFilter} onChange={(event) => updateFilter("project", event.target.value)}>
            <option value="all">All</option>
            {projectOptions.map(([id, label]) => <option value={id} key={id}>{label}</option>)}
          </select>
        </label>
        <label>Posture
          <select value={postureFilter} onChange={(event) => updateFilter("posture", event.target.value)}>
            <option value="all">All</option>
            <option value="attention">Needs attention</option>
            <option value="invalid">Invalid / unavailable</option>
            <option value="current">Current</option>
          </select>
        </label>
      </div>

      {visible.length === 0 ? <QueryState kind="empty" message="No trackers match the current filters" /> : (
        <div className="tracker-index-list">
          {visible.map((tracker) => {
            const mappedFloorRow = floor.data?.data.rows.find((row) => row.work.tracker.id === tracker.id)
            const attention = attentionReason(tracker)
            return (
              <article className="tracker-index-row" key={tracker.id}>
                <div className="tracker-index-identity">
                  <span className="tracker-index-mark"><ListChecks aria-hidden="true" /></span>
                  <div>
                    {tracker.status === "available" ? <Link to={`/trackers/${tracker.id}`}>{tracker.title}</Link> : <strong>{tracker.relative_path}</strong>}
                    <span>{tracker.project_label} · {tracker.relative_path}</span>
                    <Identity value={tracker.id} />
                  </div>
                </div>

                {tracker.status === "available" ? (
                  <>
                    <div className="tracker-index-posture">
                      <StatusMark status={tracker.verifier.valid ? tracker.tracker_status ?? "available" : "invalid"} />
                      <span>{tracker.profile} profile · verifier {tracker.verifier.valid ? "valid" : "failed"}</span>
                      <span>Git {tracker.progress_posture} · {tracker.git.durability}</span>
                    </div>
                    <dl className="tracker-status-counts">
                      {Object.entries(tracker.counts.by_status).map(([status, count]) => <div key={status}><dt>{status}</dt><dd>{count}</dd></div>)}
                    </dl>
                    <div className="tracker-index-blocks">
                      <span>Current</span><strong>{tracker.current_blocks.length ? tracker.current_blocks.join(", ") : "None"}</strong>
                      <span>Eligible</span><strong>{tracker.eligible_blocks.length ? tracker.eligible_blocks.join(", ") : "None"}</strong>
                    </div>
                    <div className="tracker-index-run">
                      <span>Mapped run</span>
                      {floor.isPending ? <strong>Loading</strong> : floor.isError ? <strong>Unavailable</strong> : mappedFloorRow?.supervision.run_id ? (
                        <Link to={`/runs/${encodeURIComponent(mappedFloorRow.supervision.run_id)}`}><Identity value={mappedFloorRow.supervision.run_id} /></Link>
                      ) : <strong>None exact</strong>}
                      <small>{mappedFloorRow ? `${mappedFloorRow.work.tracker.status} · ${mappedFloorRow.work.tracker.title ?? "Untitled"}` : "No composed tracker/run claim"}</small>
                    </div>
                    <div className={`tracker-index-attention ${attention === "None" ? "tracker-index-attention-clear" : ""}`}>
                      {attention === "None" ? <GitCompareArrows aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}
                      <div><span>Attention</span><strong>{attention}</strong><TimeValue value={tracker.git.last_commit?.committed_at ?? tracker.observed_at} /></div>
                    </div>
                  </>
                ) : (
                  <div className="tracker-index-unavailable" role="alert"><AlertTriangle aria-hidden="true" />{tracker.error.message}</div>
                )}
              </article>
            )
          })}
        </div>
      )}

      {(floor.isError || trackers.data.coverage.status === "partial") && (
        <div className="workspace-partial" role="status">
          <AlertTriangle aria-hidden="true" />Tracker rows remain independent; mapped-run or source coverage is partial where marked.
        </div>
      )}
    </div>
  )
}
