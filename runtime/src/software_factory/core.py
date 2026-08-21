from __future__ import annotations

from typing import Any

from .adaptive import AdaptiveExecutionService
from .agents import AgentService
from .artifacts import ArtifactService
from .capability import CapabilityService
from .continuation import ContinuationService
from .controller import ControllerService
from .execution import ExecutionService
from .mission import MissionService
from .program import ProgramService
from .providers import ProviderRegistry
from .qa import QAService
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
        self.agents = AgentService(store)
        self.workspaces = WorkspaceService(store)
        self.executions = ExecutionService(store, self.artifact_service)
        self.qa = QAService(store, self.workspaces, self.executions)
        self.continuation = ContinuationService(store, self.work_items)
        self.supervision = SupervisionService(
            store, work_items=self.work_items, continuation=self.continuation
        )
        self.adaptive = AdaptiveExecutionService(
            store,
            work_items=self.work_items,
            continuation=self.continuation,
            supervision=self.supervision,
        )
        self.supervision.bind_adaptive(self.adaptive)
        self.controller = ControllerService(
            store,
            work_items=self.work_items,
            agents=self.agents,
            workspaces=self.workspaces,
            executions=self.executions,
            continuation=self.continuation,
            supervision=self.supervision,
            adaptive=self.adaptive,
            providers=self.providers,
            default_provider=default_provider,
        )
        self._services = (
            self.missions,
            self.capabilities,
            self.programs,
            self.work_items,
            self.agents,
            self.workspaces,
            self.executions,
            self.qa,
            self.continuation,
            self.supervision,
            self.adaptive,
            self.controller,
        )

    @property
    def artifacts(self) -> ArtifactService:
        return self.artifact_service

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        matches = [service for service in self._services if hasattr(service, name)]
        if len(matches) == 1:
            return getattr(matches[0], name)
        if len(matches) > 1:
            raise AttributeError(f"ambiguous service method: {name}")
        raise AttributeError(name)
