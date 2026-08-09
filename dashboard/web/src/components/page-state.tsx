import type { LucideIcon } from "lucide-react"

type PageStateProps = {
  icon: LucideIcon
  title: string
  description: string
  status: string
}

export function PageState({ icon: Icon, title, description, status }: PageStateProps) {
  return (
    <section className="page-state" aria-labelledby="page-state-title">
      <div className="page-state-icon"><Icon aria-hidden="true" /></div>
      <h2 id="page-state-title">{title}</h2>
      <p>{description}</p>
      <div className="availability-note">
        <span className="status-dot status-neutral" />
        <span>{status}</span>
      </div>
    </section>
  )
}
