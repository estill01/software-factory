from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import RSITransitionError
from .identity import digest
from .models import (
    CommandExperimentInput,
    CommandObservation,
    EvidenceType,
    ExperimentDisposition,
    ExperimentEvaluation,
)


@dataclass(frozen=True)
class ExperimentPolicy:
    """Design validation and evidence interpretation for falsifying experiments.

    Effect execution is deliberately absent. Hosts run commands, simulations, shadow
    traffic, or canaries and return observations for deterministic interpretation.
    """

    conclusive_evidence_weight: float = 0.7

    @staticmethod
    def validate_design(*, design: Mapping[str, Any], success_criteria: Mapping[str, Any]) -> None:
        if not design or not success_criteria:
            raise ValueError("experiment design and success criteria are required")

    @staticmethod
    def command_input(
        *,
        experiment_id: str,
        experiment_type: str,
        status: str,
        design: Mapping[str, Any],
        success_criteria: Mapping[str, Any],
        command: Sequence[str],
        cwd: str,
    ) -> CommandExperimentInput:
        if experiment_type != "command":
            raise RSITransitionError("experiment is not a command experiment")
        if status != "designed":
            raise RSITransitionError("experiment is not awaiting execution")
        normalized_command = tuple(str(part) for part in command)
        if not normalized_command or any(not part for part in normalized_command):
            raise ValueError("command experiment requires a nonempty argv")
        exact_input_root = digest(
            {
                "experiment_id": experiment_id,
                "design": dict(design),
                "success_criteria": dict(success_criteria),
                "command": list(normalized_command),
                "cwd": cwd,
            }
        )
        return CommandExperimentInput(exact_input_root, normalized_command, cwd)

    def evaluate_command_result(
        self,
        *,
        exact_input_root: str,
        success_criteria: Mapping[str, Any],
        observation: CommandObservation,
    ) -> ExperimentEvaluation:
        accepted_codes = success_criteria.get("accepted_exit_codes", [0])
        passed = (
            not observation.invalid
            and isinstance(accepted_codes, list)
            and observation.exit_code in accepted_codes
        )
        required_stdout = success_criteria.get("stdout_contains", [])
        forbidden_stderr = success_criteria.get("stderr_not_contains", [])
        if isinstance(required_stdout, list):
            passed = passed and all(str(value) in observation.stdout for value in required_stdout)
        if isinstance(forbidden_stderr, list):
            passed = passed and all(
                str(value) not in observation.stderr for value in forbidden_stderr
            )
        disposition: ExperimentDisposition = (
            "invalid" if observation.invalid else "passed" if passed else "failed"
        )
        evidence_root = digest(
            {
                "input_root": exact_input_root,
                "exit_code": observation.exit_code,
                "stdout": observation.stdout,
                "stderr": observation.stderr,
                "disposition": disposition,
            }
        )
        evidence_type: EvidenceType
        if disposition == "passed":
            evidence_type = "support"
            evidence_weight = self.conclusive_evidence_weight
        elif disposition == "failed":
            evidence_type = "counterexample"
            evidence_weight = self.conclusive_evidence_weight
        else:
            # Infrastructure failure is not evidence against the hypothesis.
            evidence_type = "null"
            evidence_weight = 0.0
        return ExperimentEvaluation(
            passed=passed,
            disposition=disposition,
            evidence_root=evidence_root,
            measurement={"passed": passed, "criteria": dict(success_criteria)},
            hypothesis_evidence_type=evidence_type,
            hypothesis_evidence_weight=evidence_weight,
        )
