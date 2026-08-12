import { ArrowRight, Check, ExternalLink, Minus, Plus } from "lucide-react"

import type { OperationSemanticChanges } from "@/lib/admin-operations-api"

/*
 * Adapted from Beautiful UI's supplied components/DiffTable.tsx source.
 * Source: https://beautiful-ui-five.vercel.app/
 * Supplied-source SHA-256: aef76b9473debb1abf8cb3b8fe9cf71cfacd4b13ba03916932b1dd41f3007ab2
 * Adaptation: builds on the verified local tracker-diff adaptation; removes demo
 * data, timers, and actions, and adds owner/currentness identity plus explicit
 * unavailable and redacted value postures for read-only operation previews.
 */

type SemanticRow = OperationSemanticChanges["rows"][number]
type SemanticValue = SemanticRow["before"]

const changeMeta = {
  added: { label: "Added", icon: Plus },
  removed: { label: "Removed", icon: Minus },
  changed: { label: "Changed", icon: ArrowRight },
  preserved: { label: "Preserved", icon: Check },
} as const

const postureLabel = {
  unavailable: "Unavailable",
  redacted: "Redacted",
  "not-applicable": "Not applicable",
} as const

function SemanticValueCell({ value }: { value: SemanticValue }) {
  if (value.posture !== "exact") {
    return <span className={`semantic-diff-value semantic-diff-value-${value.posture}`}>{postureLabel[value.posture]}</span>
  }
  return <code className="semantic-diff-value semantic-diff-value-exact">{value.value}</code>
}

function SemanticSource({ row }: { row: SemanticRow }) {
  return (
    <div className="operation-semantic-source">
      <strong>{row.owner}</strong>
      <span>{row.source_identity}</span>
      <span>Revision <code>{row.source_revision}</code></span>
      <span>Currentness <code>{row.currentness_fingerprint}</code></span>
      {row.links.length > 0 ? (
        <span className="semantic-diff-links">
          {row.links.map((link) => (
            <a key={`${link.label}:${link.href}`} href={link.href}>
              {link.label} <ExternalLink aria-hidden="true" />
            </a>
          ))}
        </span>
      ) : <span>Source link unavailable</span>}
    </div>
  )
}

export function OperationSemanticDiffTable({
  changes,
  expired = false,
}: {
  changes: OperationSemanticChanges
  expired?: boolean
}) {
  if (changes.status !== "available") {
    return (
      <div className="operation-semantic-unavailable" role="status">
        Change comparison unavailable
      </div>
    )
  }

  return (
    <div className={`operation-semantic-diff${expired ? " operation-semantic-diff-expired" : ""}`}>
      {expired ? (
        <div className="operation-semantic-currentness" role="status">
          Comparison expired · preview again
        </div>
      ) : null}
      <div className="semantic-diff-scroll" tabIndex={0} aria-label="Owner supplied operation changes">
        <table>
          <caption className="sr-only">Read-only owner supplied semantic changes for this exact operation preview</caption>
          <colgroup>
            <col className="semantic-diff-change-column" />
            <col className="semantic-diff-subject-column" />
            <col className="semantic-diff-operation-value-column" />
            <col className="semantic-diff-operation-value-column" />
            <col className="semantic-diff-operation-source-column" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">Change</th>
              <th scope="col">Subject</th>
              <th scope="col">Before</th>
              <th scope="col">After</th>
              <th scope="col">Owner source</th>
            </tr>
          </thead>
          <tbody>
            {changes.rows.map((row) => {
              const meta = changeMeta[row.kind]
              const Icon = meta.icon
              return (
                <tr key={row.id} className={`semantic-diff-row semantic-diff-row-${row.kind}`}>
                  <td>
                    <span className={`semantic-diff-kind semantic-diff-kind-${row.kind}`}>
                      <span className="semantic-diff-dot" aria-hidden="true" />
                      <Icon aria-hidden="true" />
                      {meta.label}
                    </span>
                  </td>
                  <th scope="row">{row.subject}</th>
                  <td><SemanticValueCell value={row.before} /></td>
                  <td><SemanticValueCell value={row.after} /></td>
                  <td><SemanticSource row={row} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <ul className="semantic-diff-limitations" aria-label="Comparison limits">
        {changes.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
      </ul>
    </div>
  )
}
