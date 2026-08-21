from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

PortfolioMode = Literal["sequential", "parallel"]
PortfolioStatus = Literal["planned", "active", "completed", "failed", "cancelled"]
HypothesisStatus = Literal["proposed", "testing", "supported", "weakened", "rejected"]
EvidenceType = Literal["support", "counterexample", "boundary", "confounder", "null"]
ExperimentDisposition = Literal["passed", "failed", "invalid"]


@dataclass(frozen=True)
class CheckpointDecision:
    state_fingerprint: str
    material: bool
    action: Literal["record", "no_change"]


@dataclass(frozen=True)
class PortfolioTransition:
    active_lane_ids: tuple[str, ...]
    completed_lane_ids: tuple[str, ...]
    status: PortfolioStatus


@dataclass(frozen=True)
class PolicyEvaluationUpdate:
    status_field: Literal["historical_status", "forward_status", "review_status"] | None
    normalized_disposition: str


@dataclass(frozen=True)
class ReflectionIdentity:
    prompt_root: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class HypothesisProposal:
    statement: str
    confidence: float
    hypothesis_root: str


@dataclass(frozen=True)
class HypothesisUpdate:
    status: HypothesisStatus
    confidence: float
    evidence_type: EvidenceType
    evidence_id: str
    weight: float


@dataclass(frozen=True)
class CommandExperimentInput:
    exact_input_root: str
    command: tuple[str, ...]
    cwd: str


@dataclass(frozen=True)
class CommandObservation:
    exit_code: int | None
    stdout: str
    stderr: str
    invalid: bool = False


@dataclass(frozen=True)
class ExperimentEvaluation:
    passed: bool
    disposition: ExperimentDisposition
    evidence_root: str
    measurement: Mapping[str, Any]
    hypothesis_evidence_type: EvidenceType
    hypothesis_evidence_weight: float
