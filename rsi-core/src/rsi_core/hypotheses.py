from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .identity import digest, normalize_ids
from .models import (
    EvidenceType,
    HypothesisProposal,
    HypothesisStatus,
    HypothesisUpdate,
    ReflectionIdentity,
)


@dataclass(frozen=True)
class HypothesisPolicy:
    """Evidence update policy for falsifiable causal hypotheses."""

    support_scale: float = 0.2
    counterexample_scale: float = 0.2
    qualification_scale: float = 0.05
    supported_threshold: float = 0.75
    rejected_threshold: float = 0.2

    def propose(
        self,
        *,
        scope_id: str,
        statement: str,
        causal_model: Mapping[str, Any],
        prediction: Mapping[str, Any],
        reflection_id: str | None = None,
        confidence: float = 0.5,
    ) -> HypothesisProposal:
        normalized_statement = statement.strip()
        if not normalized_statement:
            raise ValueError("hypothesis statement is required")
        self._validate_probability(confidence, "hypothesis confidence")
        hypothesis_root = digest(
            {
                "scope_id": scope_id,
                "statement": normalized_statement,
                "causal_model": dict(causal_model),
                "prediction": dict(prediction),
                "reflection_id": reflection_id,
            }
        )
        return HypothesisProposal(normalized_statement, confidence, hypothesis_root)

    def apply_evidence(
        self,
        *,
        current_confidence: float,
        evidence_type: EvidenceType,
        evidence_id: str,
        weight: float,
    ) -> HypothesisUpdate:
        self._validate_probability(current_confidence, "hypothesis confidence")
        self._validate_probability(weight, "evidence weight")
        if not evidence_id:
            raise ValueError("hypothesis evidence requires an exact evidence id")
        if evidence_type == "support":
            delta = weight * self.support_scale
        elif evidence_type == "counterexample":
            delta = -weight * self.counterexample_scale
        elif evidence_type in {"boundary", "confounder", "null"}:
            delta = -weight * self.qualification_scale
        else:
            raise ValueError(f"unsupported hypothesis evidence type: {evidence_type}")
        confidence = min(1.0, max(0.0, current_confidence + delta))
        status: HypothesisStatus
        if confidence >= self.supported_threshold:
            status = "supported"
        elif confidence <= self.rejected_threshold:
            status = "rejected"
        elif evidence_type == "counterexample":
            status = "weakened"
        else:
            status = "testing"
        return HypothesisUpdate(status, confidence, evidence_type, evidence_id, weight)

    @staticmethod
    def _validate_probability(value: float, label: str) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{label} must be between zero and one")


class ReflectionPolicy:
    """Evidence-bound identity and confidence rules for reflective observations."""

    @staticmethod
    def identify(
        *,
        reflection_type: str,
        source_type: str,
        source_id: str,
        evidence_ids: Sequence[str],
        observations: Mapping[str, Any],
        confidence: float,
    ) -> ReflectionIdentity:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("reflection confidence must be between zero and one")
        evidence = normalize_ids(evidence_ids)
        if not evidence:
            raise ValueError("reflection requires exact evidence references")
        prompt_root = digest(
            {
                "reflection_type": reflection_type,
                "source_type": source_type,
                "source_id": source_id,
                "evidence_ids": list(evidence),
                "observations": dict(observations),
            }
        )
        return ReflectionIdentity(prompt_root, evidence)
