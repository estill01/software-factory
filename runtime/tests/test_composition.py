from __future__ import annotations

import operator
import tempfile
from pathlib import Path

import pytest

from software_factory import CoreService, Store
from software_factory.agents import AgentService
from software_factory.continuation import ContinuationService
from software_factory.execution import ExecutionService
from software_factory.qa import QAService
from software_factory.work_items import WorkItemService
from software_factory.workspaces import WorkspaceService


def test_core_uses_explicit_composition_not_service_mro() -> None:
    assert CoreService.__bases__ == (object,)
    with tempfile.TemporaryDirectory() as temp:
        core = CoreService(Store(Path(temp) / "factory.db"))
        assert isinstance(core.agents, AgentService)
        assert isinstance(core.work_items, WorkItemService)
        assert isinstance(core.workspaces, WorkspaceService)
        assert isinstance(core.executions, ExecutionService)
        assert isinstance(core.qa, QAService)
        assert isinstance(core.continuation, ContinuationService)
        assert core.qa.workspaces is core.workspaces
        assert core.qa.executions is core.executions
        assert core.continuation.work_items is core.work_items


def test_facade_delegates_unique_public_methods() -> None:
    with tempfile.TemporaryDirectory() as temp:
        core = CoreService(Store(Path(temp) / "factory.db"))
        project = core.create_project("composition")
        mission = core.create_mission(
            project_id=project,
            title="Mission",
            objective="Verify composed facade",
        )
        assert mission.startswith("mis_")
        assert core.next_action(mission)["action"] == "run_terminal_verification"
        with pytest.raises(AttributeError):
            operator.attrgetter("not_a_runtime_method")(core)
