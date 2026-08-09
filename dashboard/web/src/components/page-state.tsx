import type { LucideIcon } from "lucide-react"

type PageStateProps = {
  icon: LucideIcon
  eyebrow: string
  title: string
  description: string
  availableAfter: string
}

export function PageState({ icon: Icon, eyebrow, title, description, availableAfter }: PageStateProps) {
  return (
    <section className="page-state" aria-labelledby="page-state-title">
      <div className="page-state-icon"><Icon aria-hidden="true" /></div>
      <p className="eyebrow">{eyebrow}</p>
      <h1 id="page-state-title">{title}</h1>
      <p>{description}</p>
      <div className="availability-note">
        <span className="status-dot status-neutral" />
        <span>{availableAfter}</span>
      </div>
    </section>
  )
}
