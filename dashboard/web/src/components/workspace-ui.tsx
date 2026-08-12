import { AlertTriangle, ArrowLeft, Circle, CircleCheck, CircleMinus } from "lucide-react"
import type { ReactNode } from "react"
import { Link } from "react-router"

import { Button } from "@/components/ui/button"
import { boundedText, shortIdentity } from "@/lib/workspace-data"

export function TimeValue({ value }: { value: string | null | undefined }) {
  if (!value) return <span>Unavailable</span>
  const parsed = new Date(value)
  if (Number.isNaN(parsed.valueOf())) return <span>Unavailable</span>
  return (
    <time dateTime={value} title={value}>
      {new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(parsed)}
    </time>
  )
}

export function WorkspaceBack({ to, label = "Factory Floor" }: { to: string; label?: string }) {
  return (
    <Button variant="ghost" size="compact" asChild>
      <Link to={to}><ArrowLeft aria-hidden="true" /> {label}</Link>
    </Button>
  )
}

export function Breadcrumbs({ children }: { children: ReactNode }) {
  return <nav className="workspace-breadcrumbs" aria-label="Breadcrumb">{children}</nav>
}

export function StatusMark({ status }: { status: string | null | undefined }) {
  const normalized = (status ?? "unavailable").toLowerCase()
  const healthy = ["available", "accepted", "active", "bound", "compatible", "complete", "current", "valid"].includes(normalized)
  const warning = ["partial", "ambiguous", "degraded", "in-progress", "starting", "reconnecting", "unknown"].includes(normalized)
  const danger = ["blocked", "descendant-blocked", "failed", "invalid"].includes(normalized)
  const Icon = healthy ? CircleCheck : warning || danger ? AlertTriangle : normalized === "unavailable" ? CircleMinus : Circle
  return (
    <span className={`workspace-status status-${healthy ? "healthy" : warning ? "warning" : danger ? "danger" : "neutral"}`}>
      <Icon aria-hidden="true" />{status ?? "Unavailable"}
    </span>
  )
}

export function FactGrid({ facts }: { facts: readonly [string, ReactNode][] }) {
  return (
    <dl className="workspace-facts">
      {facts.map(([label, value]) => (
        <div key={label}><dt>{label}</dt><dd>{value ?? "Unavailable"}</dd></div>
      ))}
    </dl>
  )
}

export function QueryState({
  kind,
  message,
  retry,
}: {
  kind: "loading" | "error" | "empty"
  message: string
  retry?: () => void
}) {
  return (
    <div className={`workspace-query-state query-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {kind === "error" && <AlertTriangle aria-hidden="true" />}
      <span>{message}</span>
      {retry && <Button variant="outline" size="compact" onClick={retry}>Retry</Button>}
    </div>
  )
}

export function Identity({ value }: { value: string | null | undefined }) {
  return <code title={value ?? undefined}>{shortIdentity(value)}</code>
}

export function BoundedSummary({ value, limit = 220 }: { value: string | null | undefined; limit?: number }) {
  return <span title={value ?? undefined}>{boundedText(value, limit)}</span>
}
