from __future__ import annotations

from .agents import AgentService
from .capability import CapabilityService
from .continuation import ContinuationService
from .execution import ExecutionService
from .mission import MissionService
from .program import ProgramService
from .qa import QAService
from .work_items import WorkItemService
from .workspaces import WorkspaceService


class CoreService(
    QAService,
    ExecutionService,
    WorkspaceService,
    AgentService,
    ContinuationService,
    WorkItemService,
    ProgramService,
    CapabilityService,
    MissionService,
):
    """Native mission-to-candidate runtime facade."""
