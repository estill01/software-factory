"""Host-agnostic policies for bounded recursive self-improvement.

The package deliberately owns no database, process, filesystem, or provider effects.
Hosts persist its decisions and supply the observations, evidence, and actors used to
drive an improvement loop.
"""

from .checkpoints import CheckpointPolicy
from .errors import RSITransitionError
from .experiments import ExperimentPolicy
from .hypotheses import HypothesisPolicy, ReflectionPolicy
from .kernel import RSIKernel
from .models import (
    CheckpointDecision,
    CommandExperimentInput,
    CommandObservation,
    ExperimentEvaluation,
    HypothesisProposal,
    HypothesisUpdate,
    PolicyEvaluationUpdate,
    PortfolioTransition,
)
from .portfolios import PortfolioPolicy
from .ports import ExperimentRunner
from .programs import ProgramPolicy
from .reviews import ReviewPolicy
from .selections import SelectionPolicy
from .selector_policies import SelectorPolicy

__all__ = [
    "CheckpointDecision",
    "CheckpointPolicy",
    "CommandExperimentInput",
    "CommandObservation",
    "ExperimentEvaluation",
    "ExperimentPolicy",
    "ExperimentRunner",
    "HypothesisPolicy",
    "HypothesisProposal",
    "HypothesisUpdate",
    "PolicyEvaluationUpdate",
    "PortfolioPolicy",
    "PortfolioTransition",
    "ProgramPolicy",
    "ReflectionPolicy",
    "RSIKernel",
    "RSITransitionError",
    "ReviewPolicy",
    "SelectionPolicy",
    "SelectorPolicy",
]

__version__ = "0.2.0"
