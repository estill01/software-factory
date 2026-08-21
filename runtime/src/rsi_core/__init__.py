"""Host-agnostic primitives for bounded recursive self-improvement.

The package deliberately owns no database, process, filesystem, or provider effects.
Hosts persist its decisions and supply the observations, evidence, and actors used to
drive an improvement loop.
"""

from .kernel import (
    CheckpointDecision,
    PolicyEvaluationUpdate,
    PortfolioTransition,
    RSIKernel,
    RSITransitionError,
)

__all__ = [
    "CheckpointDecision",
    "PolicyEvaluationUpdate",
    "PortfolioTransition",
    "RSIKernel",
    "RSITransitionError",
]

__version__ = "0.1.0"
