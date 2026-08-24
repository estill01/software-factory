from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from software_factory.recovery import FactoryRecoveryCoordinator, ReleaseRefreshCoordinator


class TestStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE missions(id TEXT PRIMARY KEY);
            CREATE TABLE agent_sessions(
                id TEXT PRIMARY KEY,
                provider_session_id TEXT
            );
            INSERT INTO missions(id) VALUES('mission-1');
            INSERT INTO agent_sessions(id,provider_session_id) VALUES
              ('agent-safe','provider-safe'),
              ('agent-busy','provider-busy');
            """
        )
        migrations = Path(__file__).parents[1] / "src" / "software_factory" / "migrations"
        self.connection.executescript(
            (migrations / "0011_release_recovery_cleanup.sql").read_text(encoding="utf-8")
        )
        self.connection.executescript(
            (migrations / "0014_governance_effects.sql").read_text(encoding="utf-8")
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


def test_factory_repair_closes_loop_and_wakes_target_once(tmp_path: Path) -> None:
    store = TestStore()
    coordinator = FactoryRecoveryCoordinator(store)  # type: ignore[arg-type]
    source = tmp_path / "repair-source"
    source.mkdir()
    (source / "health.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    wake_calls: list[Mapping[str, Any]] = []

    result = coordinator.recover(
        target_mission_id="mission-1",
        defect_class="factory-controller",
        defect_evidence={"occurrence_id": "failure-1", "error": "dispatcher stopped"},
        target_state={"obligation": "open", "work": "stranded"},
        requested_range_root="range-1234567890abcdef",
        tracker_currentness_root="tracker-1234567890abcdef",
        safe_frontier=[{"work_id": "safe-work"}],
        release_root=tmp_path / "releases",
        repair=lambda _: {
            "source_root": str(source),
            "source_revision": "repair-revision-1",
            "source_tree_root": "tree-repair-revision-1",
            "repair_evidence_ids": ["implementation", "qa"],
            "health_command": [sys.executable, "health.py"],
        },
        review=lambda _: {
            "disposition": "accepted",
            "findings": {"blocking": []},
            "evidence_ids": ["independent-review"],
        },
        wake_target=lambda payload: (
            wake_calls.append(dict(payload))
            or {"provider_reference": "target-thread-1", "sent": True}
        ),
        verify_target=lambda _: {
            "target_resumed": True,
            "evidence_ids": ["target-made-progress"],
        },
    )
    assert result["recovery"]["status"] == "resolved"
    assert result["recovery"]["resume_count"] == 1
    assert result["wake_effect"]["status"] == "succeeded"
    assert len(wake_calls) == 1


def test_release_refresh_waits_for_safe_boundary_and_is_idempotent(tmp_path: Path) -> None:
    store = TestStore()
    recovery = FactoryRecoveryCoordinator(store)  # type: ignore[arg-type]
    source = tmp_path / "source"
    source.mkdir()
    (source / "health.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    staged = recovery.operations.stage_release(
        source_root=source,
        release_root=tmp_path / "releases",
        source_revision="revision-1",
        source_tree_root="tree-1",
        implementer_session_id="implementer",
    )
    recovery.operations.review_release(
        staged["id"],
        reviewer_session_id="reviewer",
        disposition="accepted",
        findings={"blocking": []},
        evidence_ids=["review"],
    )
    recovery.operations.activate_release(staged["id"], release_root=tmp_path / "releases")
    recovery.operations.verify_release(
        staged["id"],
        command=[sys.executable, "health.py"],
        release_root=tmp_path / "releases",
    )
    coordinator = ReleaseRefreshCoordinator(store)  # type: ignore[arg-type]
    calls: list[str] = []
    agents = [
        {
            "id": "agent-safe",
            "runtime_revision": "old",
            "safe_boundary": "after_current_effect",
            "at_safe_boundary": True,
        },
        {
            "id": "agent-busy",
            "runtime_revision": "old",
            "safe_boundary": "after_current_effect",
            "at_safe_boundary": False,
        },
    ]
    first = coordinator.refresh(
        staged["id"],
        agents=agents,
        refresh_agent=lambda plan: (
            calls.append(str(plan["agent_session_id"]))
            or {"refreshed": True, "provider_reference": plan["agent_session_id"]}
        ),
    )
    by_agent = {row["agent_session_id"]: row for row in first}
    assert by_agent["agent-safe"]["status"] == "refreshed"
    assert by_agent["agent-busy"]["status"] == "deferred"
    assert calls == ["agent-safe"]
    second = coordinator.refresh(
        staged["id"],
        agents=agents,
        refresh_agent=lambda plan: (
            calls.append(str(plan["agent_session_id"]))
            or {"refreshed": True, "provider_reference": plan["agent_session_id"]}
        ),
    )
    assert {row["agent_session_id"]: row["status"] for row in second} == {
        "agent-safe": "refreshed",
        "agent-busy": "deferred",
    }
    assert calls == ["agent-safe"]
