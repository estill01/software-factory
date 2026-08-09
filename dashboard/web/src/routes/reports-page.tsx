import { FileChartColumn } from "lucide-react"

import { PageState } from "@/components/page-state"

export function Component() {
  return (
    <PageState
      icon={FileChartColumn}
      eyebrow="Reports"
      title="Verified report history is not connected."
      description="Reports and metrics will retain their manifests, source roots, definitions, periods, limitations, and estimated-versus-measured posture."
      availableAfter="Report projection arrives in Block 4; the full workspace arrives in Block 9."
    />
  )
}
