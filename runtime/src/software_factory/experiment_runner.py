from __future__ import annotations

import subprocess

from librsi import CommandExperimentInput, CommandObservation


class SubprocessExperimentRunner:
    """Software Factory adapter for isolated argv-based command experiments."""

    def run(
        self, experiment: CommandExperimentInput, *, timeout_seconds: int
    ) -> CommandObservation:
        try:
            completed = subprocess.run(
                list(experiment.command),
                cwd=experiment.cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return CommandObservation(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CommandObservation(
                exit_code=None,
                stdout="",
                stderr=str(exc),
                invalid=True,
            )
