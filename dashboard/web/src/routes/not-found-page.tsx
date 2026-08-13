import { SearchX } from "lucide-react"
import { Link } from "react-router"

import { Button } from "@/components/ui/button"

export function Component() {
  return (
    <section className="page-state" aria-labelledby="not-found-title">
      <div className="page-state-icon"><SearchX aria-hidden="true" /></div>
      <h2 id="not-found-title">Route not found</h2>
      <p>No operation was attempted.</p>
      <Button asChild><Link to="/">Return to Factory Floor</Link></Button>
    </section>
  )
}
