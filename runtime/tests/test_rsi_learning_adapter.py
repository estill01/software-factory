from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rsi_core import RSIKernel

from software_factory.learning import LearningService


class HypothesisStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE missions(id TEXT PRIMARY KEY);
            INSERT INTO missions(id) VALUES('mission-1');

            CREATE TABLE reflections_v2(
                id TEXT PRIMARY KEY, mission_id TEXT, reflection_type TEXT,
                source_type TEXT, source_id TEXT, prompt_root TEXT,
                evidence_ids_json TEXT, observations_json TEXT, conclusions_json TEXT,
                proposed_actions_json TEXT, confidence REAL, status TEXT, created_at TEXT
            );
            CREATE TABLE hypotheses_v2(
                id TEXT PRIMARY KEY, mission_id TEXT, statement TEXT,
                causal_model_json TEXT, prediction_json TEXT, status TEXT,
                confidence REAL, created_from_reflection_id TEXT,
                created_at TEXT, updated_at TEXT
            );
            CREATE TABLE hypothesis_evidence_v2(
                id TEXT PRIMARY KEY, hypothesis_id TEXT, evidence_type TEXT,
                evidence_id TEXT, weight REAL, rationale_json TEXT, created_at TEXT
            );
            CREATE TABLE experiments_v2(
                id TEXT PRIMARY KEY, mission_id TEXT, hypothesis_id TEXT,
                experiment_type TEXT, design_json TEXT, success_criteria_json TEXT,
                safety_constraints_json TEXT, status TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE experiment_runs_v2(
                id TEXT PRIMARY KEY, experiment_id TEXT, exact_input_root TEXT,
                command_json TEXT, cwd TEXT, exit_code INTEGER, stdout_text TEXT,
                stderr_text TEXT, measurement_json TEXT, evidence_root TEXT,
                disposition TEXT, started_at TEXT, completed_at TEXT
            );
            """
        )

    @contextmanager
    def transaction(self, *, mode: str = "IMMEDIATE") -> Iterator[sqlite3.Connection]:
        self.connection.execute(f"BEGIN {mode}")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def one(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        row = self.connection.execute(sql, parameters).fetchone()
        if row is None:
            if required:
                raise LookupError(sql)
            return None
        return dict(row)

    def all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, parameters).fetchall()]


def service() -> LearningService:
    return LearningService(HypothesisStore(), rsi=RSIKernel())  # type: ignore[arg-type]


def test_learning_service_persists_kernel_hypothesis_and_experiment_decisions() -> None:
    learning = service()
    reflection = learning.create_reflection(
        mission_id="mission-1",
        reflection_type="checkpoint",
        source_type="incident",
        source_id="incident-1",
        evidence_ids=["trace-1"],
        observations={"recurrence": 2},
        conclusions={"candidate_cause": "generation reuse"},
        confidence=0.7,
    )
    hypothesis = learning.create_hypothesis(
        mission_id="mission-1",
        reflection_id=reflection["id"],
        statement="A generation check prevents callback reuse",
        causal_model={"cause": "stale callback"},
        prediction={"stdout_contains": "FACTORY_OK"},
    )
    experiment = learning.design_experiment(
        mission_id="mission-1",
        hypothesis_id=hypothesis["id"],
        experiment_type="command",
        design={"isolation": "subprocess"},
        success_criteria={"accepted_exit_codes": [0], "stdout_contains": ["FACTORY_OK"]},
    )
    run = learning.run_command_experiment(
        experiment["id"],
        command=[sys.executable, "-c", "print('FACTORY_OK')"],
        cwd=Path.cwd(),
    )

    updated = learning.store.one(
        "SELECT status,confidence FROM hypotheses_v2 WHERE id=?", (hypothesis["id"],)
    )
    assert run is not None and run["disposition"] == "passed"
    assert updated is not None and updated["confidence"] > 0.5
    assert learning.store.all(
        "SELECT evidence_type FROM hypothesis_evidence_v2 WHERE hypothesis_id=?",
        (hypothesis["id"],),
    ) == [{"evidence_type": "support"}]


def test_invalid_command_is_persisted_as_null_not_counterevidence() -> None:
    learning = service()
    hypothesis = learning.create_hypothesis(
        mission_id="mission-1",
        statement="The candidate satisfies the invariant",
        causal_model={"candidate": "v2"},
        prediction={"exit_code": 0},
    )
    experiment = learning.design_experiment(
        mission_id="mission-1",
        hypothesis_id=hypothesis["id"],
        experiment_type="command",
        design={"isolation": "subprocess"},
        success_criteria={"accepted_exit_codes": [0]},
    )
    run = learning.run_command_experiment(
        experiment["id"],
        command=["/definitely/not/an/executable"],
        cwd=Path.cwd(),
    )

    updated = learning.store.one(
        "SELECT status,confidence FROM hypotheses_v2 WHERE id=?", (hypothesis["id"],)
    )
    evidence = learning.store.one(
        "SELECT evidence_type,weight FROM hypothesis_evidence_v2 WHERE hypothesis_id=?",
        (hypothesis["id"],),
    )
    assert run is not None and run["disposition"] == "invalid"
    assert updated == {"status": "testing", "confidence": 0.5}
    assert evidence == {"evidence_type": "null", "weight": 0.0}
