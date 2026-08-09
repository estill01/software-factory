import { SearchX } from "lucide-react"
import { Link } from "react-router"

import { Button } from "@/components/ui/button"

export function Component() {
  return (
    <section className="page-state" aria-labelledby="not-found-title">
      <div className="page-state-icon"><SearchX aria-hidden="true" /></div>
      <p className="eyebrow">Not found</p>
      <h1 id="not-found-title">That factory workspace does not exist.</h1>
      <p>The local shell did not find a route. No operation was attempted.</p>
      <Button asChild><Link to="/">Return to Factory Floor</Link></Button>
    </section>
  )
}
