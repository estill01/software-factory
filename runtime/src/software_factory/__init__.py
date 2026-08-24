"""Software Factory v2 native runtime."""

from .adaptive import AdaptiveExecutionService
from .audit import CommandEnvelope
from .controller import ControllerService
from .core import CoreService
from .database import Database
from .engine import (
    ENGINE_CONTRACT_VERSION,
    CancelResult,
    EventRecord,
    FactoryEngine,
    MissionOutcome,
    MissionRef,
    MissionSnapshot,
    MissionSubmission,
)
from .errors import (
    AuthorityDenied,
    EvidenceInvalid,
    InvalidTransition,
    LeaseConflict,
    ProviderError,
    RoleConflict,
    StaleLease,
    StaleState,
    StoreError,
)
from .providers import (
    CodexCLIProvider,
    DeterministicProvider,
    ProcessProvider,
    ProviderObservation,
    ProviderRegistry,
    ProviderRequest,
)
from .store import Store
from .supervision import SupervisionService

__all__ = [
    "AdaptiveExecutionService",
    "AuthorityDenied",
    "CommandEnvelope",
    "CoreService",
    "Database",
    "ENGINE_CONTRACT_VERSION",
    "CancelResult",
    "EventRecord",
    "FactoryEngine",
    "MissionOutcome",
    "MissionRef",
    "MissionSnapshot",
    "MissionSubmission",
    "ControllerService",
    "EvidenceInvalid",
    "InvalidTransition",
    "LeaseConflict",
    "ProviderError",
    "RoleConflict",
    "StaleLease",
    "StaleState",
    "Store",
    "SupervisionService",
    "ProviderRegistry",
    "ProviderRequest",
    "ProviderObservation",
    "DeterministicProvider",
    "ProcessProvider",
    "CodexCLIProvider",
    "StoreError",
]
__version__ = "2.0.0.dev6"
