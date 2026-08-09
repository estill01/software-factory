import { ListChecks } from "lucide-react"

import { PageState } from "@/components/page-state"

export function Component() {
  return (
    <PageState
      icon={ListChecks}
      eyebrow="Trackers"
      title="Tracker truth has not been projected."
      description="This workspace will preserve exact Block state, dependencies, verifier diagnostics, Git currentness, evidence, and Stop boundaries."
      availableAfter="Tracker projection begins after project discovery in Block 3."
    />
  )
}
