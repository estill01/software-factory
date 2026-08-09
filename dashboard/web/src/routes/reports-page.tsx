import { FileChartColumn } from "lucide-react"

import { PageState } from "@/components/page-state"

export function Component() {
  return (
    <div className="page-stack reports-page">
      <PageState
        icon={FileChartColumn}
        title="Report source unavailable"
        status="Not connected"
      />
    </div>
  )
}
