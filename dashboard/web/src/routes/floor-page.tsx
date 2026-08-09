import { useQuery } from "@tanstack/react-query"
import {
  ArrowDownRight,
  CircleAlert,
  Factory,
  ShieldCheck,
  Workflow,
} from "lucide-react"

import { ChartPlaceholder } from "@/components/chart-placeholder"
import { fetchHealth } from "@/lib/api"
import { fetchProjects } from "@/lib/projects-api"

export function Component() {
  const runtimeHealth = useQuery({
    queryKey: ["runtime-health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    retry: 1,
  })
  const projects = useQuery({
    queryKey: ["projects", false],
    queryFn: ({ signal }) => fetchProjects(false, signal),
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
  const projectReadiness = projects.isPending
    ? { detail: "Awaiting the bounded catalog", label: "Checking", ready: false }
    : projects.isError
      ? { detail: "Catalog or registered roots could not be read", label: "Unavailable", ready: false }
      : {
          detail: `${projects.data.data.projects.length} visible project${projects.data.data.projects.length === 1 ? "" : "s"}`,
          label: "Ready",
          ready: true,
        }
  const summaryCards = [
    {
      label: "Registered projects",
      value: projects.isSuccess ? String(projects.data.data.projects.length) : "—",
      detail: projects.isPending
        ? "Checking catalog"
        : projects.isError
          ? "Catalog unavailable"
          : "Visible catalog records",
      tone: projects.isSuccess ? "green" : "neutral",
    },
    { label: "Active implementations", value: "—", detail: "Task source unavailable", tone: "neutral" },
    { label: "Supervisor groups", value: "—", detail: "Bindings unavailable", tone: "neutral" },
    { label: "Action required", value: "—", detail: "Cannot be determined", tone: "neutral" },
  ] as const

  return (
    <div className="page-stack floor-page">
      <section className="summary-grid" aria-label="Factory summary">
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
            <h2 id="floor-panel-title">Implementation lanes</h2>
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
              <h3>Implementation lanes unavailable</h3>
              <p>Task and supervision sources are not connected.</p>
            </div>
          </div>
        </section>

        <aside className="panel readiness-panel" aria-labelledby="readiness-title">
          <div className="panel-heading">
            <h2 id="readiness-title">Source readiness</h2>
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
              <span className={`readiness-icon ${projectReadiness.ready ? "readiness-ready" : ""}`}>
                <Workflow aria-hidden="true" />
              </span>
              <div><strong>Project catalog</strong><span>{projectReadiness.detail}</span></div>
              <span className={`readiness-state ${projectReadiness.ready ? "state-ready" : ""}`}>
                {projectReadiness.label}
              </span>
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
          <h2 id="metrics-title">Factory activity</h2>
          <span className="data-state-label">Unavailable</span>
        </div>
        <ChartPlaceholder />
      </section>
    </div>
  )
}
