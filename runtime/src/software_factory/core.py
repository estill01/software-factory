from __future__ import annotations

from .capability import CapabilityService
from .continuation import ContinuationService
from .mission import MissionService
from .program import ProgramService
from .work_items import WorkItemService


class CoreService(
    ContinuationService,
    WorkItemService,
    ProgramService,
    CapabilityService,
    MissionService,
):
    """Mission, capability, program, work, and continuation facade."""
