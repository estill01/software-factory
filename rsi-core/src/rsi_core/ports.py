from __future__ import annotations

from typing import Protocol

from .models import CommandExperimentInput, CommandObservation


class ExperimentRunner(Protocol):
    """Host effect port for executing an exact experiment input."""

    def run(
        self, experiment: CommandExperimentInput, *, timeout_seconds: int
    ) -> CommandObservation: ...
