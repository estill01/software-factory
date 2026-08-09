import { CodexIntegrationPanel } from "@/features/admin/codex-integration-panel"
import { ProjectCatalogPanel } from "@/features/projects/project-catalog-panel"

export function Component() {
  return (
    <div className="page-stack admin-page">
      <CodexIntegrationPanel />
      <ProjectCatalogPanel />
    </div>
  )
}
