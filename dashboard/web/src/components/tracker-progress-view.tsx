import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { Link } from "react-router"

import type {
  TrackerProgressClaim,
  TrackerProgressProjection,
} from "@/lib/tracker-progress"

function claimText(claim: TrackerProgressClaim): string {
  if (claim.blocks.length) {
    return claim.blocks
      .map((block) => `Block ${block.number} — ${block.title ?? "title unavailable"}`)
      .join("; ")
  }
  if (claim.range) return `Blocks ${claim.range.start}–${claim.range.end} assigned; active Block unavailable`
  if (claim.status === "none") return "None active"
  if (claim.status === "conflict") return "Conflict"
  if (claim.status === "partial") return "Partial"
  return "Unavailable"
}

function Claim({ claim }: { claim: TrackerProgressClaim }) {
  return (
    <div
      className={`tracker-progress-claim claim-${claim.status}`}
      aria-label={`${claim.label}: ${claimText(claim)}; ${claim.status}; ${claim.reason}`}
    >
      <span className="tracker-progress-claim-source">
        <strong title={claim.sourceIdentity}>{claim.label}</strong>
        <small>{claim.status}</small>
      </span>
      <span className="tracker-progress-claim-value">
        {claim.blocks.length ? claim.blocks.map((block) => (
          <Link to={block.route} title={block.title ?? undefined} key={`${claim.key}:${block.number}`}>
            Block {block.number} — {block.title ?? "title unavailable"}
          </Link>
        )) : <strong title={claim.reason}>{claimText(claim)}</strong>}
      </span>
      <Link className="tracker-progress-source-link" to={claim.sourceRoute}>Source</Link>
    </div>
  )
}

export function TrackerProgressView({
  progress,
  accepted,
  compact = false,
}: {
  progress: TrackerProgressProjection
  accepted: number | null
  compact?: boolean
}) {
  const total = progress.total.value
  return (
    <div className={`tracker-progress-view${compact ? " tracker-progress-compact" : ""}`}>
      <div className="tracker-progress-total">
        <span>
          {progress.posture === "conflict"
            ? <AlertTriangle aria-hidden="true" />
            : <CheckCircle2 aria-hidden="true" />}
          <strong>{total === null ? "Blocks unavailable" : `${total} Blocks`}</strong>
        </span>
        <small>
          {total !== null && accepted !== null ? `${accepted}/${total} accepted · ` : ""}
          {progress.posture}
        </small>
      </div>
      <div className="tracker-progress-claims">
        {progress.claims.map((claim) => <Claim claim={claim} key={claim.key} />)}
      </div>
    </div>
  )
}
