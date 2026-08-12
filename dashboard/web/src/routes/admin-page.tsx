import { CodexIntegrationPanel } from "@/features/admin/codex-integration-panel"
import { FactoryEvolutionPanel } from "@/features/admin/factory-evolution-panel"
import { OperationFrameworkPanel } from "@/features/admin/operation-framework-panel"
import { ProjectCatalogPanel } from "@/features/projects/project-catalog-panel"

export function Component() {
  return (
    <div className="page-stack admin-page">
      <CodexIntegrationPanel />
      <FactoryEvolutionPanel />
      <OperationFrameworkPanel />
      <ProjectCatalogPanel />
    </div>
  )
}
