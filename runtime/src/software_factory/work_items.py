from __future__ import annotations

from collections import defaultdict
from typing import Any

from .errors import InvalidTransition, StoreError
from .util import (
    canonical_json,
    json_load,
    new_id,
    normalize_relative_path,
    utc_now,
)

_ACCEPTANCE_ORDER = {
    "pending": 0,
    "candidate_accepted": 1,
    "integrated_accepted": 2,
    "installed_accepted": 3,
}


def _normalized_scope(values: list[str]) -> list[str]:
    return sorted({normalize_relative_path(value) for value in values})


def _scope_conflicts(left: list[str], right: list[str]) -> bool:
    if "*" in left or "*" in right:
        return True
    for first in left:
        for second in right:
            if first == second or first.startswith(f"{second}/") or second.startswith(f"{first}/"):
                return True
    return False


class WorkItemService:
    def __init__(self, store: Any):
        self.store = store

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
        repository_id: str | None = None,
        required_role: str = "implementer",
        provider_key: str | None = None,
        strategy_key: str | None = None,
        strategy_revision: int = 1,
    ) -> str:
        work_id = new_id("wrk")
        now = utc_now()
        revision_id = None
        scope = _normalized_scope(writable_scope or [])
        with self.store.transaction() as db:
            if program_id:
                program = db.execute(
                    "SELECT mission_id,current_revision_id FROM programs WHERE id=?",
                    (program_id,),
                ).fetchone()
                if program is None or program["mission_id"] != mission_id:
                    raise StoreError("program not found in mission")
                revision_id = program["current_revision_id"]
            if obligation_id:
                obligation = db.execute(
                    "SELECT mission_id FROM obligations WHERE id=?", (obligation_id,)
                ).fetchone()
                if obligation is None or obligation["mission_id"] != mission_id:
                    raise StoreError("obligation not found in mission")
            if repository_id:
                repository = db.execute(
                    "SELECT project_id FROM repositories WHERE id=?", (repository_id,)
                ).fetchone()
                mission = db.execute(
                    "SELECT project_id FROM missions WHERE id=?", (mission_id,)
                ).fetchone()
                if (
                    repository is None
                    or mission is None
                    or repository["project_id"] != mission["project_id"]
                ):
                    raise StoreError("repository does not belong to the mission project")
            if not required_role:
                raise ValueError("required_role is required")
            db.execute(
                """INSERT INTO work_items(
                    id,mission_id,program_id,program_revision_id,obligation_id,parent_id,
                    work_type,title,description,planning_status,execution_status,
                    qa_status,acceptance_status,priority,proposed_by,
                    expected_effect_json,acceptance_spec_json,writable_scope_json,
                    lane_key,state_version,created_at,updated_at,repository_id,
                    required_role,provider_key,strategy_key,strategy_revision
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                    canonical_json(scope),
                    lane_key,
                    1,
                    now,
                    now,
                    repository_id,
                    required_role,
                    provider_key,
                    strategy_key or f"{work_type}:1",
                    strategy_revision,
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
                    "writable_scope": scope,
                    "repository_id": repository_id,
                    "required_role": required_role,
                    "provider_key": provider_key,
                    "strategy_key": strategy_key or f"{work_type}:1",
                    "strategy_revision": strategy_revision,
                },
            )
        return work_id

    def add_work_dependency(
        self,
        work_item_id: str,
        depends_on_id: str,
        condition: dict[str, Any] | None = None,
    ) -> None:
        if work_item_id == depends_on_id:
            raise ValueError("work item cannot depend on itself")
        condition = condition or {"required_acceptance": "integrated_accepted"}
        required = condition.get("required_acceptance", "integrated_accepted")
        if required not in _ACCEPTANCE_ORDER:
            raise ValueError(f"unsupported required_acceptance: {required}")
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT id,mission_id FROM work_items WHERE id IN (?,?)",
                (work_item_id, depends_on_id),
            ).fetchall()
            if len(rows) != 2 or len({row["mission_id"] for row in rows}) != 1:
                raise InvalidTransition("work dependency must remain in one mission")
            db.execute(
                """INSERT INTO work_dependencies
                   (work_item_id,depends_on_id,condition_json) VALUES(?,?,?)""",
                (work_item_id, depends_on_id, canonical_json(condition)),
            )
            mission_id = rows[0]["mission_id"]
            self._assert_acyclic_work(db, mission_id)
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="work",
                event_type="work.dependency_added",
                subject_type="work_item",
                subject_id=work_item_id,
                payload={"depends_on_id": depends_on_id, "condition": condition},
            )

    @staticmethod
    def _assert_acyclic_work(db: Any, mission_id: str) -> None:
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
            for dependency in graph[node]:
                visit(dependency)
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
        if not selected_by:
            raise ValueError("selected_by is required")
        with self.store.transaction() as db:
            work = self.store.check_version(
                db,
                table="work_items",
                row_id=work_item_id,
                expected_version=expected_version,
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

    @staticmethod
    def _dependency_satisfied(dep: dict[str, Any]) -> bool:
        condition = json_load(dep["condition_json"], {})
        required = condition.get("required_acceptance", "integrated_accepted")
        actual = dep["acceptance_status"]
        return _ACCEPTANCE_ORDER.get(actual, -1) >= _ACCEPTANCE_ORDER[required]

    def ready_work(self, mission_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        rows = self.store.all(
            """SELECT * FROM work_items
               WHERE mission_id=? AND planning_status='selected'
                 AND execution_status IN ('not_started','queued','abandoned')
               ORDER BY priority DESC, created_at ASC""",
            (mission_id,),
        )
        dependencies = self.store.all(
            """SELECT d.work_item_id,d.depends_on_id,d.condition_json,
                      w.acceptance_status,w.execution_status
               FROM work_dependencies d
               JOIN work_items w ON w.id=d.depends_on_id
               WHERE d.work_item_id IN (
                   SELECT id FROM work_items WHERE mission_id=?
               )""",
            (mission_id,),
        )
        blocked = {
            dep["work_item_id"] for dep in dependencies if not self._dependency_satisfied(dep)
        }

        active_rows = self.store.all(
            """SELECT DISTINCT w.writable_scope_json FROM work_items w
               LEFT JOIN executions e ON e.work_item_id=w.id
               WHERE w.mission_id=? AND (
                   w.execution_status='running'
                   OR e.status IN ('queued','dispatching','leased','running','verifying')
               )""",
            (mission_id,),
        )
        active_scopes = [json_load(row["writable_scope_json"], []) for row in active_rows]
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
