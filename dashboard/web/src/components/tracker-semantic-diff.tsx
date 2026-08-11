import { ArrowRight, ExternalLink, Minus, Plus } from "lucide-react"

import { trackerSourceUrl, type TrackerSemanticDiff } from "@/lib/trackers-api"

/*
 * Adapted from Beautiful UI's supplied components/DiffTable.tsx source.
 * Source: https://beautiful-ui-five.vercel.app/
 * Supplied-source SHA-256: aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2
 * Adaptation: removed demo rows, timers, and menu semantics; retained the compact
 * fixed-column table, semantic row tinting, status dots, and explicit change cues
 * for typed, read-only tracker source differences.
 */

type Side = TrackerSemanticDiff["rows"][number]["before"]

const changeMeta = {
  added: { label: "Added", icon: Plus },
  removed: { label: "Removed", icon: Minus },
  changed: { label: "Changed", icon: ArrowRight },
} as const

function SourceSide({ side }: { side: Side }) {
  if (!side) return <span className="semantic-diff-empty" aria-label="No source line">—</span>
  return (
    <div className="semantic-diff-side">
      <code>{side.text || " "}</code>
      <span>
        Line {side.line}
        {side.block ? ` · Block ${side.block.number} — ${side.block.title}` : " · outside a parsed Block"}
        {side.text_truncated ? " · text bounded" : ""}
      </span>
    </div>
  )
}

function SourceLinks({
  trackerId,
  diff,
  before,
  after,
}: {
  trackerId: string
  diff: TrackerSemanticDiff
  before: Side
  after: Side
}) {
  const beforeRevision = diff.base?.kind === "HEAD" ? diff.base.repository_revision : null
  return (
    <span className="semantic-diff-links">
      {before && beforeRevision ? (
        <a
          href={trackerSourceUrl(
            trackerId,
            { line: before.line, endLine: before.line },
            { revision: beforeRevision },
          )}
          target="_blank"
          rel="noreferrer"
        >
          Before <ExternalLink aria-hidden="true" />
        </a>
      ) : null}
      {after ? (
        <a
          href={trackerSourceUrl(
            trackerId,
            { line: after.line, endLine: after.line },
            { contentSha256: diff.target.content_sha256 },
          )}
          target="_blank"
          rel="noreferrer"
        >
          After <ExternalLink aria-hidden="true" />
        </a>
      ) : null}
      {!after && !(before && beforeRevision) ? <span>Unavailable</span> : null}
    </span>
  )
}

export function TrackerSemanticDiffTable({
  trackerId,
  diff,
}: {
  trackerId: string
  diff: TrackerSemanticDiff
}) {
  return (
    <div className="tracker-semantic-diff">
      <div className="semantic-diff-scroll" tabIndex={0} aria-label="Tracker semantic source changes">
        <table>
          <caption className="sr-only">Bounded semantic changes between the tracker at HEAD and its working source</caption>
          <colgroup>
            <col className="semantic-diff-change-column" />
            <col className="semantic-diff-source-column" />
            <col className="semantic-diff-source-column" />
            <col className="semantic-diff-link-column" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">Change</th>
              <th scope="col">Before</th>
              <th scope="col">After</th>
              <th scope="col">Source</th>
            </tr>
          </thead>
          <tbody>
            {diff.rows.map((row) => {
              const meta = changeMeta[row.kind]
              const Icon = meta.icon
              return (
                <tr key={row.id} className={`semantic-diff-row semantic-diff-row-${row.kind}`}>
                  <th scope="row">
                    <span className={`semantic-diff-kind semantic-diff-kind-${row.kind}`}>
                      <span className="semantic-diff-dot" aria-hidden="true" />
                      <Icon aria-hidden="true" />
                      {meta.label}
                    </span>
                  </th>
                  <td><SourceSide side={row.before} /></td>
                  <td><SourceSide side={row.after} /></td>
                  <td><SourceLinks trackerId={trackerId} diff={diff} before={row.before} after={row.after} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="semantic-diff-meta">
        <span>{diff.path}</span>
        <span>{diff.returned_rows} of {diff.total_rows ?? "unavailable"} rows</span>
        <span>Verifier {diff.owner.verifier.valid ? "valid" : "failed"} · {diff.owner.verifier.profile}</span>
        <span>Owner revision {diff.owning_revision ?? "Unavailable"}</span>
        <span>Currentness <code>{diff.currentness_fingerprint}</code></span>
      </div>
      <ul className="semantic-diff-limitations" aria-label="Comparison limits">
        {diff.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
      </ul>
      {!diff.complete ? (
        <div className="workspace-bound">
          This comparison is partial. It cannot support an exact no-change or complete-change claim.
        </div>
      ) : null}
    </div>
  )
}
