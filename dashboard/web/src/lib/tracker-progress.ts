import type { FactoryFloorEnvelope, FactoryFloorRow } from "@/lib/floor-api"
import type { TrackerListEnvelope, TrackerSummary } from "@/lib/trackers-api"

export type TrackerActivityFilter = "all" | "active" | "attention" | "blocked" | "completed"
export type TrackerProgressPosture = "exact" | "none" | "conflict" | "partial" | "unavailable"
export type TrackerClaimStatus = "exact" | "none" | "conflict" | "partial" | "unavailable"

export interface TrackerProgressBlock {
  number: number
  title: string | null
  status: string | null
  line: number | null
  route: string
}

export interface TrackerProgressClaim {
  key: string
  label: string
  status: TrackerClaimStatus
  blocks: TrackerProgressBlock[]
  range: { start: number; end: number } | null
  reason: string
  sourceIdentity: string
  sourceRoute: string
}

export interface TrackerTotalProjection {
  value: number | null
  posture: "exact" | "unavailable"
  reason: string
}

export interface TrackerProgressProjection {
  total: TrackerTotalProjection
  posture: TrackerProgressPosture
  claims: TrackerProgressClaim[]
  exactMappedRows: FactoryFloorRow[]
  excludedCandidateRows: number
  floorCoverage: "complete" | "partial" | "unavailable"
  running: boolean
  failed: boolean
}

export interface TrackerCountProjection {
  value: number
  posture: "exact" | "partial" | "unavailable"
  accessibleCount: string
  countLabel: string
}

type AvailableTracker = Extract<TrackerSummary, { status: "available" }>
type FloorClaim = FactoryFloorRow["work"]["block_claims"]["claims"][number]

function sameNumbers(left: number[], right: number[]): boolean {
  if (left.length !== right.length) return false
  const leftSorted = [...left].sort((a, b) => a - b)
  const rightSorted = [...right].sort((a, b) => a - b)
  return leftSorted.every((number, index) => number === rightSorted[index])
}

function exactTotal(tracker: AvailableTracker): TrackerTotalProjection {
  const verifierBlocks = tracker.verifier.blocks
  const total = tracker.counts.total
  const exact = tracker.verifier.valid
    && total > 0
    && verifierBlocks.length === total
    && new Set(verifierBlocks).size === total
  return exact
    ? {
        value: total,
        posture: "exact",
        reason: "Exact nonzero Block set from the maintained tracker verifier.",
      }
    : {
        value: null,
        posture: "unavailable",
        reason: "Verifier validity or its nonzero Block set cannot establish an exact total.",
      }
}

function trackerClaim(tracker: AvailableTracker, total: TrackerTotalProjection): TrackerProgressClaim {
  const details = tracker.current_block_details
  const currentSet = new Set(tracker.current_blocks)
  const detailSet = new Set(details.map((block) => block.number))
  const detailsMatch = sameNumbers(
    tracker.current_blocks,
    details.map((block) => block.number),
  )
    && currentSet.size === tracker.current_blocks.length
    && detailSet.size === details.length
    && details.every(
      (block) => block.status === "in-progress" && tracker.verifier.blocks.includes(block.number),
    )
  const blocks = details.map((block) => ({
    number: block.number,
    title: block.title,
    status: block.status,
    line: block.line,
    route: `/trackers/${tracker.id}/blocks?block=${block.number}`,
  }))
  const status: TrackerClaimStatus = total.posture !== "exact" || !detailsMatch
    ? "unavailable"
    : blocks.length
      ? "exact"
      : "none"
  return {
    key: "tracker",
    label: "Tracker status",
    status,
    blocks: status === "unavailable" ? [] : blocks,
    range: null,
    reason: status === "exact"
      ? "Maintained tracker status identifies this complete current Block set."
      : status === "none"
        ? "The maintained tracker records no Block in progress."
        : "Current Block details disagree with the maintained verifier or status projection.",
    sourceIdentity: tracker.source.identity,
    sourceRoute: `/trackers/${tracker.id}/blocks`,
  }
}

function mappedClaim(row: FactoryFloorRow, claim: FloorClaim): TrackerProgressClaim {
  const identity = claim.source === "task"
    ? row.implementation.task_id
    : row.supervision.run_id ?? row.supervision.target_thread_id
  const status = claim.status === "exact" && claim.blocks.length === 0
    ? "partial"
    : claim.status
  return {
    key: `${row.id}:${claim.source}`,
    label: `${claim.label} · ${identity}`,
    status,
    blocks: claim.blocks.map((block) => ({ ...block })),
    range: claim.range,
    reason: status === claim.status
      ? claim.reason
      : `${claim.reason} Exact Block identity is absent, so the claim remains partial.`,
    sourceIdentity: claim.source_identity,
    sourceRoute: claim.route,
  }
}

function unavailableMappedClaim(source: "task" | "supervision", reason: string): TrackerProgressClaim {
  return {
    key: `unavailable:${source}`,
    label: source === "task" ? "Implementation task" : "Current supervision mission",
    status: "unavailable",
    blocks: [],
    range: null,
    reason,
    sourceIdentity: source === "task"
      ? "codex-app-server/task-workflow-marker"
      : "supervise-tracker-runs/current-mission-activity",
    sourceRoute: source === "task" ? "/tasks" : "/runs",
  }
}

function claimSet(claim: TrackerProgressClaim): string {
  return claim.blocks.map((block) => block.number).sort((a, b) => a - b).join(",")
}

function aggregatePosture(
  claims: TrackerProgressClaim[],
  floorCoverage: TrackerProgressProjection["floorCoverage"],
): TrackerProgressPosture {
  if (claims.some((claim) => claim.status === "conflict")) return "conflict"
  const comparable = claims.filter((claim) => claim.status === "exact" || claim.status === "none")
  if (new Set(comparable.map(claimSet)).size > 1) return "conflict"
  if (floorCoverage !== "complete" || claims.some((claim) => claim.status === "partial")) return "partial"
  if (claims.every((claim) => claim.status === "unavailable")) return "unavailable"
  if (claims.some((claim) => claim.status === "unavailable")) return "partial"
  if (comparable.length && comparable.every((claim) => claim.status === "none")) return "none"
  if (comparable.length && comparable.every((claim) => claim.status === "exact")) return "exact"
  return "partial"
}

export function projectTrackerProgress(
  tracker: TrackerSummary,
  floor: FactoryFloorEnvelope | undefined,
): TrackerProgressProjection {
  if (tracker.status === "unavailable") {
    const reason = "The tracker projection is unavailable, so active work cannot be established."
    const claims = [
      {
        key: "tracker",
        label: "Tracker status",
        status: "unavailable" as const,
        blocks: [],
        range: null,
        reason: tracker.error.message,
        sourceIdentity: tracker.source.identity,
        sourceRoute: "/trackers",
      },
      unavailableMappedClaim("task", reason),
      unavailableMappedClaim("supervision", reason),
    ]
    return {
      total: { value: null, posture: "unavailable", reason },
      posture: "unavailable",
      claims,
      exactMappedRows: [],
      excludedCandidateRows: 0,
      floorCoverage: floor ? "partial" : "unavailable",
      running: false,
      failed: false,
    }
  }

  const total = exactTotal(tracker)
  const claims: TrackerProgressClaim[] = [trackerClaim(tracker, total)]
  const exactMappedRows = floor?.data.rows.filter(
    (row) => row.work.tracker.status === "exact"
      && row.work.tracker.id === tracker.id
      && row.project.status === "bound"
      && row.project.project_id === tracker.project_id,
  ) ?? []
  const excludedCandidateRows = floor?.data.rows.filter(
    (row) => row.work.tracker.id === tracker.id
      && (
        row.work.tracker.status !== "exact"
        || row.project.status !== "bound"
        || row.project.project_id !== tracker.project_id
      ),
  ).length ?? 0
  const floorCoverage = floor === undefined
    ? "unavailable"
    : floor.coverage.status === "complete" && !floor.data.rows_truncated
      ? "complete"
      : "partial"

  if (exactMappedRows.length) {
    exactMappedRows.forEach((row) => {
      row.work.block_claims.claims
        .filter((claim) => claim.source === "task" || claim.source === "supervision")
        .forEach((claim) => claims.push(mappedClaim(row, claim)))
      const floorTrackerClaim = row.work.block_claims.claims.find((claim) => claim.source === "tracker")
      const currentTrackerClaim = claims[0]
      if (floorTrackerClaim) {
        const floorSet = floorTrackerClaim.blocks.map((block) => block.number)
        const currentSet = currentTrackerClaim.blocks.map((block) => block.number)
        if (
          floorTrackerClaim.status !== currentTrackerClaim.status
          || !sameNumbers(floorSet, currentSet)
        ) {
          claims.push({
            ...mappedClaim(row, floorTrackerClaim),
            key: `${row.id}:tracker-snapshot`,
            label: `Tracker Floor snapshot · ${row.id}`,
            status: "conflict",
            reason: "The composed Floor tracker snapshot disagrees with the current tracker projection.",
          })
        }
      }
    })
  } else {
    const associationReason = excludedCandidateRows
      ? `${excludedCandidateRows} noncanonical Floor tracker candidate claim${excludedCandidateRows === 1 ? " was" : "s were"} excluded.`
      : "No exact current tracker/run association is available."
    claims.push(
      unavailableMappedClaim("task", associationReason),
      unavailableMappedClaim("supervision", associationReason),
    )
  }

  const running = tracker.current_blocks.length > 0 || exactMappedRows.some(
    (row) => row.implementation.status === "active" || row.supervision.status === "active",
  )
  const failed = ["blocked", "failed"].some((status) => (tracker.counts.by_status[status] ?? 0) > 0)
    || exactMappedRows.some(
      (row) => row.supervision.status === "blocked"
        || row.supervision.status === "failed",
    )
  return {
    total,
    posture: aggregatePosture(claims, floorCoverage),
    claims,
    exactMappedRows,
    excludedCandidateRows,
    floorCoverage,
    running,
    failed,
  }
}

export function trackerAttentionReasons(
  tracker: TrackerSummary,
  progress: TrackerProgressProjection,
): string[] {
  if (tracker.status === "unavailable") return [tracker.error.message]
  const reasons: string[] = []
  if (!tracker.verifier.valid) reasons.push(`${tracker.verifier.errors.length} verifier diagnostic${tracker.verifier.errors.length === 1 ? "" : "s"}`)
  if (tracker.header_block_status_conflict) reasons.push("Header and Block statuses disagree")
  if (tracker.progress_posture === "dirty") reasons.push("Working tree differs from HEAD")
  if (tracker.progress_posture === "untracked") reasons.push("Tracker is untracked")
  if (tracker.progress_posture === "stale") reasons.push("Run-bound content hash is stale")
  if (tracker.progress_posture === "unavailable") reasons.push("Git currentness is unavailable")
  if (tracker.git.durability !== "matched") reasons.push(`Git durability is ${tracker.git.durability}`)
  if (tracker.current_blocks.length > 1) reasons.push("Multiple Blocks are in progress")
  if (tracker.counts.open > 0 && tracker.current_blocks.length === 0 && tracker.eligible_blocks.length === 0) {
    reasons.push("Open work has no eligible Block")
  }
  if (progress.posture === "conflict") reasons.push("Active Block owner claims conflict")
  if (
    tracker.current_blocks.length > 0
    && (progress.posture === "partial" || progress.posture === "unavailable")
  ) {
    reasons.push("Active Block owner coverage is incomplete")
  }
  if (progress.exactMappedRows.some((row) => row.light.posture === "red")) {
    reasons.push("A mapped Factory Floor row requires action")
  }
  if (progress.excludedCandidateRows) reasons.push("Only noncanonical Floor tracker candidates were excluded")
  return [...new Set(reasons)]
}

export function trackerIsCompleted(tracker: TrackerSummary): boolean {
  return tracker.status === "available"
    && tracker.verifier.valid
    && !tracker.header_block_status_conflict
    && tracker.counts.total > 0
    && tracker.counts.accepted === tracker.counts.total
}

export function trackerMatchesActivity(
  tracker: TrackerSummary,
  progress: TrackerProgressProjection,
  filter: TrackerActivityFilter,
): boolean {
  if (filter === "all") return true
  if (filter === "active") return progress.running
  if (filter === "attention") return trackerAttentionReasons(tracker, progress).length > 0
  if (filter === "blocked") return progress.failed
  return trackerIsCompleted(tracker)
}

function trackerEnumerationExact(envelope: TrackerListEnvelope): boolean {
  return envelope.data.projects.every((project) => project.status === "available")
    && envelope.data.projects.reduce((total, project) => total + project.tracker_candidates, 0)
      === envelope.data.trackers.length
}

function dynamicFloorAssociationExact(
  envelope: TrackerListEnvelope,
  floor: FactoryFloorEnvelope,
): boolean {
  const projectByTracker = new Map(
    envelope.data.trackers.map((tracker) => [tracker.id, tracker.project_id]),
  )
  return floor.data.rows.every((row) => {
    if (row.work.tracker.status === "exact" && row.work.tracker.id) {
      return row.project.status === "bound"
        && projectByTracker.get(row.work.tracker.id) === row.project.project_id
    }
    const couldChangeDynamicCounts = row.implementation.status === "active"
      || row.implementation.status === "terminal"
      || ["active", "blocked", "failed"].includes(row.supervision.status)
      || row.light.posture === "red"
      || row.light.posture === "amber"
      || row.issues.total > 0
    return !couldChangeDynamicCounts
  })
}

export function trackerCountProjection(
  envelope: TrackerListEnvelope,
  floor: FactoryFloorEnvelope | undefined,
  filter: TrackerActivityFilter,
  count: number,
): TrackerCountProjection {
  const enumerationExact = trackerEnumerationExact(envelope)
  const trackerTruthExact = enumerationExact && envelope.data.trackers.every((tracker) => {
    const progress = projectTrackerProgress(tracker, floor)
    return tracker.status === "available"
      && progress.total.posture === "exact"
      && progress.claims[0]?.status !== "unavailable"
  })
  const floorExact = floor !== undefined
    && floor.coverage.status === "complete"
    && !floor.data.rows_truncated
    && dynamicFloorAssociationExact(envelope, floor)
  const exact = filter === "all"
    ? enumerationExact
    : filter === "completed"
      ? trackerTruthExact
      : trackerTruthExact && floorExact
  if (exact) {
    return { value: count, posture: "exact", countLabel: String(count), accessibleCount: `${count} exact` }
  }
  const unavailable = envelope.data.trackers.length === 0 && !enumerationExact
  if (unavailable) {
    return { value: count, posture: "unavailable", countLabel: "—", accessibleCount: "unavailable" }
  }
  return {
    value: count,
    posture: "partial",
    countLabel: `≥${count}`,
    accessibleCount: `${count} returned, lower bound or partial coverage`,
  }
}
