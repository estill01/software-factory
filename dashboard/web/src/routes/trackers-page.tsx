import { ListChecks } from "lucide-react"

import { PageState } from "@/components/page-state"

export function Component() {
  return (
    <div className="page-stack trackers-page">
      <PageState
        icon={ListChecks}
        title="Tracker source unavailable"
        description="No tracker has been parsed for a registered project."
        status="Not connected"
      />
    </div>
  )
}
