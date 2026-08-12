import { CodexIntegrationPanel } from "@/features/admin/codex-integration-panel"
import { OperationFrameworkPanel } from "@/features/admin/operation-framework-panel"
import { ProjectCatalogPanel } from "@/features/projects/project-catalog-panel"

export function Component() {
  return (
    <div className="page-stack admin-page">
      <CodexIntegrationPanel />
      <OperationFrameworkPanel />
      <ProjectCatalogPanel />
    </div>
  )
}
