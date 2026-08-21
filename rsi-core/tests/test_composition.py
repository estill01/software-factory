from __future__ import annotations

from rsi_core import (
    CheckpointPolicy,
    ExperimentPolicy,
    HypothesisPolicy,
    PortfolioPolicy,
    ProgramPolicy,
    RSIKernel,
    SelectionPolicy,
    SelectorPolicy,
)


def test_kernel_is_a_small_composition_of_independent_policies() -> None:
    kernel = RSIKernel()

    assert isinstance(kernel.checkpoints, CheckpointPolicy)
    assert isinstance(kernel.programs, ProgramPolicy)
    assert isinstance(kernel.portfolios, PortfolioPolicy)
    assert isinstance(kernel.selections, SelectionPolicy)
    assert isinstance(kernel.selector_policies, SelectorPolicy)
    assert isinstance(kernel.hypotheses, HypothesisPolicy)
    assert isinstance(kernel.experiments, ExperimentPolicy)
