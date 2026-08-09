import { AlertTriangle } from "lucide-react"
import { isRouteErrorResponse, Link, useRouteError } from "react-router"

import { Button } from "@/components/ui/button"

export function RouteErrorPage() {
  const error = useRouteError()
  const detail = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : "Unknown route failure"

  return (
    <main className="fatal-state">
      <AlertTriangle aria-hidden="true" />
      <p className="eyebrow">Workspace error</p>
      <h1>This route could not be rendered.</h1>
      <p>{detail}. No Factory operation was attempted.</p>
      <Button asChild><Link to="/">Return to Factory Floor</Link></Button>
    </main>
  )
}
