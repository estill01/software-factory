from __future__ import annotations

from dataclasses import dataclass, field

from .checkpoints import CheckpointPolicy
from .experiments import ExperimentPolicy
from .hypotheses import HypothesisPolicy, ReflectionPolicy
from .portfolios import PortfolioPolicy
from .programs import ProgramPolicy
from .reviews import ReviewPolicy
from .selections import SelectionPolicy
from .selector_policies import SelectorPolicy


@dataclass(frozen=True)
class RSIKernel:
    """Composition root for reusable recursive-improvement policies.

    Components are public and independently usable. The composition root is a
    convenience for hosts that want the complete bounded-improvement loop.
    """

    checkpoints: CheckpointPolicy = field(default_factory=CheckpointPolicy)
    reviews: ReviewPolicy = field(default_factory=ReviewPolicy)
    programs: ProgramPolicy = field(default_factory=ProgramPolicy)
    portfolios: PortfolioPolicy = field(default_factory=PortfolioPolicy)
    selections: SelectionPolicy = field(default_factory=SelectionPolicy)
    selector_policies: SelectorPolicy = field(default_factory=SelectorPolicy)
    reflections: ReflectionPolicy = field(default_factory=ReflectionPolicy)
    hypotheses: HypothesisPolicy = field(default_factory=HypothesisPolicy)
    experiments: ExperimentPolicy = field(default_factory=ExperimentPolicy)
