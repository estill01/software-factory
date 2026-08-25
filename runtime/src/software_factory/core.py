from __future__ import annotations

from typing import Any

from .acceptance import AcceptanceService
from .acceptance_lifecycle import AcceptanceLifecycleService
from .adaptive import AdaptiveExecutionService
from .advanced import AdvancedServices
from .agents import AgentService
from .artifacts import ArtifactService
from .capability import CapabilityService
from .continuation import ContinuationService
from .controller import ControllerService
from .evolution import EvolutionService
from .execution import ExecutionService
from .governance import GovernanceService
from .integrations.librsi import LibRSIIntegration
from .learning import LearningService
from .migration import MigrationService
from .mission import MissionService
from .operations import OperationsService
from .problem_solving import ProblemSolvingService
from .profiles import SoftwareTargetProfile, TargetProfileRegistry
from .program import ProgramService
from .providers import ProviderRegistry
from .qa import QAService
from .reconciliation import RepositoryReconciliationService
from .recovery import FactoryRecoveryCoordinator, ReleaseRefreshCoordinator
from .reflection import ReflectionService
from .release import GovernedReleaseService
from .reporting import ReportingService
from .store import Store
from .supervision import SupervisionService
from .work_items import WorkItemService
from .workspaces import WorkspaceService


class CoreService:
    """Compatibility facade over explicitly composed native application services.

    The first implementation used a deep multiple-inheritance mixin graph. That made
    dependencies implicit and would have become unmaintainable as supervision,
    learning, release, recovery, and cleanup were added. The facade preserves the
    existing call surface while each service now has explicit dependencies.
    """

    _FACADE_DENIED = frozenset(
        {
            "create_workspace",
            "freeze_workspace",
            "retire_workspace",
            "run_command",
            "stage_release",
            "review_release",
            "activate_release",
            "rollback_release",
        }
    )

    def __init__(
        self,
        store: Store,
        *,
        providers: ProviderRegistry | None = None,
        default_provider: str | None = None,
    ):
        self.store = store
        self.providers = providers or ProviderRegistry()
        self.artifact_service = ArtifactService(store)
        self.missions = MissionService(store)
        self.capabilities = CapabilityService(store)
        self.programs = ProgramService(store)
        self.work_items = WorkItemService(store)
        self.semantic = LibRSIIntegration(store, work_items=self.work_items)
        self.agents = AgentService(store)
        self._workspace_owner = WorkspaceService(store)
        self._executions = ExecutionService(store, self.artifact_service)
        self._operations = OperationsService(store)
        self._reconciliation = RepositoryReconciliationService(
            store,
            operations=self._operations,
        )
        self.governance = GovernanceService(store)
        self.release = GovernedReleaseService(
            store,
            governance=self.governance,
            operations=self._operations,
        )
        self._software_profile = SoftwareTargetProfile(
            store,
            workspaces=self._workspace_owner,
            executions=self._executions,
            operations=self._operations,
            reconciliation=self._reconciliation,
            releases=self.release,
        )
        self.target_profiles = TargetProfileRegistry()
        self.target_profiles.register(self._software_profile)
        self._profile_workspaces = self._software_profile
        self.qa = QAService(store, self._profile_workspaces, self._executions)
        self.continuation = ContinuationService(store, self.work_items)
        self.supervision = SupervisionService(
            store, work_items=self.work_items, continuation=self.continuation
        )
        self.adaptive = AdaptiveExecutionService(
            store,
            work_items=self.work_items,
            continuation=self.continuation,
            supervision=self.supervision,
            semantic_integration=self.semantic,
        )
        self.supervision.bind_adaptive(self.adaptive)
        self.acceptance_lifecycle = AcceptanceLifecycleService(
            store,
            governance=self.governance,
            work_items=self.work_items,
            capabilities=self.capabilities,
            supervision=self.supervision,
        )
        self.controller = ControllerService(
            store,
            work_items=self.work_items,
            agents=self.agents,
            workspaces=self._profile_workspaces,
            executions=self._executions,
            continuation=self.continuation,
            supervision=self.supervision,
            adaptive=self.adaptive,
            governance=self.governance,
            providers=self.providers,
            default_provider=default_provider,
        )
        self.learning = LearningService(store, semantic=self.semantic)
        self.evolution = EvolutionService(store, semantic=self.learning.semantic)
        self.acceptance = AcceptanceService(store)
        self.reporting = ReportingService(store)
        self.migration = MigrationService(store)
        self.reflection = ReflectionService(
            store, work_items=self.work_items, semantic_integration=self.semantic
        )
        self.problem_solving = ProblemSolvingService(
            store, learning=self.learning, semantic=self.semantic
        )
        self.recovery = FactoryRecoveryCoordinator(
            store,
            operations=self._operations,
            governance=self.governance,
        )
        self.release_refresh = ReleaseRefreshCoordinator(
            store,
            operations=self._operations,
            governance=self.governance,
        )
        self.advanced = AdvancedServices(
            store,
            work_items=self.work_items,
            continuation=self.continuation,
            supervision=self.supervision,
            adaptive=self.adaptive,
            learning=self.learning,
            evolution=self.evolution,
            operations=self._operations,
        )
        self._services = (
            self.missions,
            self.capabilities,
            self.programs,
            self.work_items,
            self.agents,
            self._executions,
            self.qa,
            self.acceptance_lifecycle,
            self.continuation,
            self.supervision,
            self.adaptive,
            self.controller,
        )

    @property
    def artifacts(self) -> ArtifactService:
        return self.artifact_service

    def register_software_target(self, repository_id: str, **configuration: Any) -> None:
        """Configure the software adapter without exposing its effect executor."""

        self._software_profile.register_target(repository_id, **configuration)

    def close(self) -> None:
        """Close provider-owned resources exactly once through the registry owner."""

        self.providers.close()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name in self._FACADE_DENIED:
            raise AttributeError(name)
        matches = [service for service in self._services if hasattr(service, name)]
        if len(matches) == 1:
            return getattr(matches[0], name)
        if len(matches) > 1:
            raise AttributeError(f"ambiguous service method: {name}")
        raise AttributeError(name)
