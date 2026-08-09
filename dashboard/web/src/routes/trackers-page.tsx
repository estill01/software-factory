import { ListChecks } from "lucide-react"

import { PageState } from "@/components/page-state"

export function Component() {
  return (
    <div className="page-stack trackers-page">
      <PageState
        icon={ListChecks}
        title="Tracker workspace unavailable"
        status="Read source connected"
      />
    </div>
  )
}
