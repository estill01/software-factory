import { ChevronDown } from "lucide-react"
import { useId, useState, type ReactNode } from "react"

/*
 * Adapted from Beautiful UI's supplied components/TaskRows.tsx source.
 * Source: https://beautiful-ui-five.vercel.app/
 * Frozen source SHA-256: 665e31820b041600662fcffff044d6a4994ecd18059d5e8ef1026251bf996b0e
 * Adaptation: removed demo data, timers, retry state, and autonomous transitions;
 * retained the compact native-button disclosure, status marker, chevron,
 * grid-row transition, and detail rail for typed Factory Floor content.
 */
export function OperationalDisclosure({
  ariaLabel,
  detailLabel,
  className,
  marker,
  summary,
  trailing,
  children,
}: {
  ariaLabel: string
  detailLabel: string
  className?: string
  marker: ReactNode
  summary: ReactNode
  trailing: ReactNode
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const generatedId = useId()
  const regionId = `factory-row-${generatedId.replaceAll(":", "")}`

  return (
    <article className={`operational-disclosure ${className ?? ""}`.trim()}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={regionId}
        aria-label={ariaLabel}
        className="operational-disclosure-trigger"
        onClick={() => setOpen((current) => !current)}
      >
        <span className="operational-disclosure-marker" aria-hidden="true">{marker}</span>
        <span className="operational-disclosure-summary">{summary}</span>
        <span className="operational-disclosure-trailing">{trailing}</span>
        <span className="operational-disclosure-chevron" aria-hidden="true">
          <ChevronDown className={open ? "disclosure-chevron-open" : ""} />
        </span>
      </button>
      <div
        className="operational-disclosure-grid"
        aria-hidden={!open}
        style={{
          gridTemplateRows: open ? "1fr" : "0fr",
          opacity: open ? 1 : 0,
        }}
      >
        <div className="operational-disclosure-overflow">
          <div
            id={regionId}
            role="region"
            aria-label={detailLabel}
            className="operational-disclosure-detail"
            inert={open ? undefined : true}
          >
            <span className="operational-disclosure-rail" aria-hidden="true" />
            <div className="operational-disclosure-content">{children}</div>
          </div>
        </div>
      </div>
    </article>
  )
}

export type CountChipTone = "neutral" | "active" | "attention" | "blocked" | "completed"

export interface CountFilterChip<Key extends string> {
  key: Key
  label: string
  countLabel: string
  accessibleCount: string
  tone: CountChipTone
}

/*
 * Adapted from Beautiful UI's supplied components/FilterTable.tsx source.
 * Source: https://beautiful-ui-five.vercel.app/
 * Frozen source SHA-256: 4a48c51cd6e5c0aa3bab91aab9975005518fd82dd294d059e402c2bb4ce681f4
 * Adaptation: removed sample rows and business statuses; retained the compact
 * aria-pressed chip structure, status dot, count badge, and horizontal overflow
 * behavior for exact/lower-bound Factory Floor counts.
 */
export function CountFilterChips<Key extends string>({
  label,
  value,
  items,
  onChange,
}: {
  label: string
  value: Key
  items: Array<CountFilterChip<Key>>
  onChange: (value: Key) => void
}) {
  return (
    <div className="count-filter-chips" role="group" aria-label={label}>
      {items.map((item) => {
        const active = value === item.key
        return (
          <button
            key={item.key}
            type="button"
            aria-pressed={active}
            aria-label={`${item.label}: ${item.accessibleCount}`}
            className={`count-filter-chip chip-${item.tone}${active ? " count-filter-chip-active" : ""}`}
            onClick={() => onChange(item.key)}
          >
            {item.tone !== "neutral" && <span className="count-filter-dot" aria-hidden="true" />}
            <span>{item.label}</span>
            <span className="count-filter-value" aria-hidden="true">{item.countLabel}</span>
          </button>
        )
      })}
    </div>
  )
}
