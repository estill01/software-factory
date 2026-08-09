import { useQuery } from "@tanstack/react-query"
import {
  ArrowDownRight,
  CircleAlert,
  CircleDashed,
  Factory,
  ShieldCheck,
  Workflow,
} from "lucide-react"

import { ChartPlaceholder } from "@/components/chart-placeholder"
import { fetchHealth } from "@/lib/api"

const summaryCards = [
  { label: "Registered projects", value: "—", detail: "Catalog unavailable", tone: "neutral" },
  { label: "Active implementations", value: "—", detail: "Task source unavailable", tone: "neutral" },
  { label: "Supervisor groups", value: "—", detail: "Bindings unavailable", tone: "neutral" },
  { label: "Action required", value: "—", detail: "Cannot be determined", tone: "neutral" },
] as const

export function Component() {
  const runtimeHealth = useQuery({
    queryKey: ["runtime-health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    retry: 1,
  })
  const runtimeReadiness = runtimeHealth.isPending
    ? {
        detail: "Awaiting the runtime health response",
        label: "Checking",
        ready: false,
      }
    : runtimeHealth.isError
      ? {
          detail: "Health check failed; readiness is unknown",
          label: "Unavailable",
          ready: false,
        }
      : {
          detail: "Connected and locally constrained",
          label: "Ready",
          ready: true,
        }

  return (
    <div className="page-stack floor-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Factory floor</p>
          <h1>Know what is moving—and what needs you.</h1>
          <p className="page-lede">
            Implementations, supervisors, issues, conclusions, and history will meet here.
            This shell is live; operational sources are not connected yet.
          </p>
        </div>
        <div className="posture-badge posture-neutral">
          <CircleDashed aria-hidden="true" />
          Source state unknown
        </div>
      </header>

      <section className="summary-grid" aria-label="Factory summary placeholders">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.label}>
            <div className="summary-card-topline">
              <span>{card.label}</span>
              <ArrowDownRight aria-hidden="true" />
            </div>
            <strong>{card.value}</strong>
            <span className="summary-detail">
              <span className={`status-dot status-${card.tone}`} />
              {card.detail}
            </span>
          </article>
        ))}
      </section>

      <div className="floor-layout">
        <section className="panel floor-panel" aria-labelledby="floor-panel-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Live operations</p>
              <h2 id="floor-panel-title">Implementation lanes</h2>
            </div>
            <span className="data-state-label">No source coverage</span>
          </div>

          <div className="floor-column-labels" aria-hidden="true">
            <span>Project &amp; implementation</span>
            <span>Supervisor</span>
            <span>Current work</span>
            <span>Posture</span>
          </div>

          <div className="floor-empty">
            <div className="floor-empty-visual" aria-hidden="true">
              <span /><span /><span />
              <Factory />
            </div>
            <div>
              <h3>No implementation lanes can be established yet.</h3>
              <p>
                Project registration begins in Block 2. Unknown is intentionally not shown as
                idle, healthy, or complete.
              </p>
            </div>
          </div>
        </section>

        <aside className="panel readiness-panel" aria-labelledby="readiness-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Integration health</p>
              <h2 id="readiness-title">Source readiness</h2>
            </div>
          </div>
          <ul className="readiness-list">
            <li>
              <span className={`readiness-icon ${runtimeReadiness.ready ? "readiness-ready" : ""}`}>
                {runtimeReadiness.ready
                  ? <ShieldCheck aria-hidden="true" />
                  : <CircleAlert aria-hidden="true" />}
              </span>
              <div><strong>Loopback runtime</strong><span>{runtimeReadiness.detail}</span></div>
              <span className={`readiness-state ${runtimeReadiness.ready ? "state-ready" : ""}`}>
                {runtimeReadiness.label}
              </span>
            </li>
            <li>
              <span className="readiness-icon"><Workflow aria-hidden="true" /></span>
              <div><strong>Project sources</strong><span>Available after Block 2</span></div>
              <span className="readiness-state">Unavailable</span>
            </li>
            <li>
              <span className="readiness-icon"><Factory aria-hidden="true" /></span>
              <div><strong>Codex tasks</strong><span>Available after Block 5</span></div>
              <span className="readiness-state">Unavailable</span>
            </li>
          </ul>
        </aside>
      </div>

      <section className="panel metrics-panel" aria-labelledby="metrics-title">
        <div className="panel-heading metrics-heading">
          <div>
            <p className="eyebrow">Operating signal</p>
            <h2 id="metrics-title">Factory activity</h2>
          </div>
          <p>Every future number will carry period, source coverage, and limitations.</p>
        </div>
        <ChartPlaceholder />
      </section>
    </div>
  )
}
