import { FolderKanban } from "lucide-react"

import { PageState } from "@/components/page-state"

export function Component() {
  return (
    <PageState
      icon={FolderKanban}
      eyebrow="Projects"
      title="No project catalog is connected."
      description="Projects will become bounded local repository roots with explicit discovery metadata—not copied operational truth."
      availableAfter="Project registration and discovery arrive in Block 2."
    />
  )
}
