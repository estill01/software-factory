from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .store import InvalidTransition, Store, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now
from collections import defaultdict

def _scope_conflicts(left: list[str], right: list[str]) -> bool:
    for a in left:
        ap = Path(a)
        for b in right:
            bp = Path(b)
            if a == "*" or b == "*":
                return True
            try:
                ap.relative_to(bp)
                return True
            except ValueError:
                pass
            try:
                bp.relative_to(ap)
                return True
            except ValueError:
                pass
    return False

class WorkItemService:

    def create_work_item(
            self,
            *,
            mission_id: str,
            work_type: str,
            title: str,
            description: str,
            obligation_id: str | None = None,
            program_id: str | None = None,
            parent_id: str | None = None,
            priority: int = 0,
            proposed_by: str | None = None,
            expected_effect: dict[str, Any] | None = None,
            acceptance_spec: dict[str, Any] | None = None,
            writable_scope: list[str] | None = None,
            lane_key: str | None = None,
        ) -> str:
            work_id = new_id("wrk")
            now = utc_now()
            revision_id = None
            with self.store.transaction() as db:
                if program_id:
                    revision_id = db.execute(
                        "SELECT current_revision_id FROM programs WHERE id=?", (program_id,)
                    ).fetchone()
                    if revision_id is None:
                        raise StoreError("program not found")
                    revision_id = revision_id["current_revision_id"]
                db.execute(
                    """INSERT INTO work_items(
                        id,mission_id,program_id,program_revision_id,obligation_id,parent_id,
                        work_type,title,description,planning_status,execution_status,
                        qa_status,acceptance_status,priority,proposed_by,
                        expected_effect_json,acceptance_spec_json,writable_scope_json,
                        lane_key,state_version,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        work_id,
                        mission_id,
                        program_id,
                        revision_id,
                        obligation_id,
                        parent_id,
                        work_type,
                        title,
                        description,
                        "proposed",
                        "not_started",
                        "not_started",
                        "pending",
                        priority,
                        proposed_by,
                        canonical_json(expected_effect or {}),
                        canonical_json(acceptance_spec or {}),
                        canonical_json(writable_scope or []),
                        lane_key,
                        1,
                        now,
                        now,
                    ),
                )
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="work",
                    event_type="work.proposed",
                    subject_type="work_item",
                    subject_id=work_id,
                    new_version=1,
                    payload={
                        "type": work_type,
                        "title": title,
                        "obligation_id": obligation_id,
                        "program_id": program_id,
                        "proposed_by": proposed_by,
                        "writable_scope": writable_scope or [],
                    },
                )
            return work_id

    def add_work_dependency(
            self, work_item_id: str, depends_on_id: str, condition: dict[str, Any] | None = None
        ) -> None:
            if work_item_id == depends_on_id:
                raise ValueError("work item cannot depend on itself")
            with self.store.transaction() as db:
                db.execute(
                    """INSERT INTO work_dependencies
                       (work_item_id,depends_on_id,condition_json) VALUES(?,?,?)""",
                    (work_item_id, depends_on_id, canonical_json(condition or {})),
                )
                mission_id = db.execute(
                    "SELECT mission_id FROM work_items WHERE id=?", (work_item_id,)
                ).fetchone()["mission_id"]
                self._assert_acyclic_work(db, mission_id)
                self.store.append_event(
                    db,
                    mission_id=mission_id,
                    stream_key="work",
                    event_type="work.dependency_added",
                    subject_type="work_item",
                    subject_id=work_item_id,
                    payload={"depends_on_id": depends_on_id, "condition": condition or {}},
                )

    def _assert_acyclic_work(self, db: Any, mission_id: str) -> None:
            rows = db.execute(
                """SELECT d.work_item_id,d.depends_on_id
                   FROM work_dependencies d
                   JOIN work_items w ON w.id=d.work_item_id
                   WHERE w.mission_id=?""",
                (mission_id,),
            ).fetchall()
            graph: dict[str, set[str]] = defaultdict(set)
            nodes: set[str] = set()
            for row in rows:
                graph[row["work_item_id"]].add(row["depends_on_id"])
                nodes.update((row["work_item_id"], row["depends_on_id"]))
            visiting: set[str] = set()
            done: set[str] = set()

            def visit(node: str) -> None:
                if node in visiting:
                    raise InvalidTransition("work dependency graph contains a cycle")
                if node in done:
                    return
                visiting.add(node)
                for dep in graph[node]:
                    visit(dep)
                visiting.remove(node)
                done.add(node)

            for node in nodes:
                visit(node)

    def select_work(
            self,
            work_item_id: str,
            *,
            expected_version: int,
            selected_by: str,
            basis: dict[str, Any],
            policy_id: str | None = None,
        ) -> dict[str, Any]:
            with self.store.transaction() as db:
                work = self.store.check_version(
                    db, table="work_items", row_id=work_item_id, expected_version=expected_version
                )
                if work["planning_status"] not in {"proposed", "deferred"}:
                    raise InvalidTransition("only proposed/deferred work can be selected")
                new_version = expected_version + 1
                db.execute(
                    """UPDATE work_items SET planning_status='selected',selected_by=?,
                       selection_policy_id=?,selection_basis_json=?,state_version=?,
                       updated_at=? WHERE id=?""",
                    (
                        selected_by,
                        policy_id,
                        canonical_json(basis),
                        new_version,
                        utc_now(),
                        work_item_id,
                    ),
                )
                self.store.append_event(
                    db,
                    mission_id=work["mission_id"],
                    stream_key="work",
                    event_type="work.selected",
                    subject_type="work_item",
                    subject_id=work_item_id,
                    source_type="selector",
                    source_id=selected_by,
                    prior_version=expected_version,
                    new_version=new_version,
                    payload={"basis": basis, "policy_id": policy_id},
                )
            return self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,))

    def ready_work(self, mission_id: str, limit: int | None = None) -> list[dict[str, Any]]:
            rows = self.store.all(
                """SELECT * FROM work_items
                   WHERE mission_id=? AND planning_status='selected'
                     AND execution_status IN ('not_started','queued','abandoned')
                   ORDER BY priority DESC, created_at ASC""",
                (mission_id,),
            )
            dependencies = self.store.all(
                """SELECT d.work_item_id,d.depends_on_id,w.acceptance_status,w.execution_status
                   FROM work_dependencies d
                   JOIN work_items w ON w.id=d.depends_on_id
                   WHERE d.work_item_id IN (
                       SELECT id FROM work_items WHERE mission_id=?
                   )""",
                (mission_id,),
            )
            blocked: set[str] = set()
            for dep in dependencies:
                if (
                    dep["acceptance_status"]
                    not in {"candidate_accepted", "integrated_accepted", "installed_accepted"}
                    and dep["execution_status"] != "verified"
                ):
                    blocked.add(dep["work_item_id"])

            active_scopes = [
                json_load(row["writable_scope_json"], [])
                for row in self.store.all(
                    """SELECT w.writable_scope_json FROM work_items w
                       WHERE w.mission_id=? AND w.execution_status='running'""",
                    (mission_id,),
                )
            ]
            selected: list[dict[str, Any]] = []
            selected_scopes: list[list[str]] = []
            for row in rows:
                if row["id"] in blocked:
                    continue
                scopes = json_load(row["writable_scope_json"], [])
                if any(_scope_conflicts(scopes, current) for current in active_scopes):
                    continue
                if any(_scope_conflicts(scopes, current) for current in selected_scopes):
                    continue
                selected.append(row)
                selected_scopes.append(scopes)
                if limit is not None and len(selected) >= limit:
                    break
            return selected
