from __future__ import annotations

from collections import defaultdict
from typing import Any

from .errors import EvidenceInvalid, InvalidTransition
from .util import canonical_json, new_id, utc_now


class CapabilityService:
    def __init__(self, store: Any):
        self.store = store

    def add_capability(
        self,
        *,
        mission_id: str,
        name: str,
        description: str,
        required: bool = True,
        protected: bool = False,
        acceptance_spec: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> str:
        capability_id = new_id("cap")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO capabilities(
                    id,mission_id,parent_id,name,description,required,protected,status,
                    acceptance_spec_json,state_version,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    capability_id,
                    mission_id,
                    parent_id,
                    name,
                    description,
                    int(required),
                    int(protected),
                    "absent",
                    canonical_json(acceptance_spec or {}),
                    1,
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="capability",
                event_type="capability.created",
                subject_type="capability",
                subject_id=capability_id,
                new_version=1,
                payload={
                    "name": name,
                    "required": required,
                    "protected": protected,
                    "acceptance_spec": acceptance_spec or {},
                },
            )
        return capability_id

    def set_capability_status(
        self,
        capability_id: str,
        *,
        expected_version: int,
        status: str,
        evidence_id: str,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        allowed = {
            "absent": {"partial", "locally_verified", "regressed"},
            "partial": {"locally_verified", "regressed"},
            "locally_verified": {"integrated", "regressed"},
            "integrated": {"end_to_end_verified", "regressed"},
            "end_to_end_verified": {"regressed"},
            "regressed": {
                "partial",
                "locally_verified",
                "integrated",
                "end_to_end_verified",
            },
        }
        with self.store.transaction() as db:
            current = self.store.check_version(
                db,
                table="capabilities",
                row_id=capability_id,
                expected_version=expected_version,
            )
            if status not in allowed[current["status"]]:
                raise InvalidTransition(
                    f"capability {current['status']} -> {status} is not allowed"
                )
            evidence = self.store.require_evidence(
                db,
                [evidence_id],
                mission_id=current["mission_id"],
                subject_type="capability",
                subject_id=capability_id,
            )[0]
            payload = self.store.one(
                "SELECT payload_json FROM evidence_records WHERE id=?",
                (evidence_id,),
                db=db,
            )
            if status == "end_to_end_verified" and evidence["evidence_type"] not in {
                "end_to_end_probe",
                "terminal_probe",
                "installed_probe",
            }:
                raise EvidenceInvalid(
                    "end-to-end capability status requires an end-to-end/terminal probe"
                )
            new_version = expected_version + 1
            db.execute(
                """UPDATE capabilities SET status=?,current_evidence_id=?,
                   state_version=?,updated_at=? WHERE id=?""",
                (status, evidence_id, new_version, utc_now(), capability_id),
            )
            self.store.append_event(
                db,
                mission_id=current["mission_id"],
                stream_key="capability",
                event_type="capability.status_changed",
                subject_type="capability",
                subject_id=capability_id,
                source_type="actor",
                source_id=actor_id,
                prior_version=expected_version,
                new_version=new_version,
                payload={
                    "from": current["status"],
                    "to": status,
                    "evidence_id": evidence_id,
                    "evidence_payload": payload,
                },
            )
        return self.store.one("SELECT * FROM capabilities WHERE id=?", (capability_id,))

    def add_obligation(
        self,
        *,
        mission_id: str,
        obligation_type: str,
        description: str,
        capability_id: str | None = None,
        parent_id: str | None = None,
        priority: int = 0,
        status: str = "open",
    ) -> str:
        obligation_id = new_id("obl")
        now = utc_now()
        with self.store.transaction() as db:
            if capability_id:
                capability = db.execute(
                    "SELECT mission_id FROM capabilities WHERE id=?", (capability_id,)
                ).fetchone()
                if capability is None or capability["mission_id"] != mission_id:
                    raise InvalidTransition("capability does not belong to mission")
            db.execute(
                """INSERT INTO obligations(
                    id,mission_id,capability_id,parent_id,obligation_type,description,
                    status,priority,resolution_json,state_version,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    obligation_id,
                    mission_id,
                    capability_id,
                    parent_id,
                    obligation_type,
                    description,
                    status,
                    priority,
                    "{}",
                    1,
                    now,
                    now,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="work",
                event_type="obligation.created",
                subject_type="obligation",
                subject_id=obligation_id,
                new_version=1,
                payload={
                    "type": obligation_type,
                    "description": description,
                    "capability_id": capability_id,
                    "priority": priority,
                },
            )
        return obligation_id

    def add_obligation_dependency(
        self,
        obligation_id: str,
        depends_on_id: str,
        condition: dict[str, Any] | None = None,
    ) -> None:
        if obligation_id == depends_on_id:
            raise ValueError("obligation cannot depend on itself")
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT id,mission_id FROM obligations WHERE id IN (?,?)",
                (obligation_id, depends_on_id),
            ).fetchall()
            if len(rows) != 2 or len({row["mission_id"] for row in rows}) != 1:
                raise InvalidTransition("obligation dependency must remain in one mission")
            db.execute(
                """INSERT INTO obligation_dependencies
                   (obligation_id,depends_on_id,condition_json) VALUES(?,?,?)""",
                (obligation_id, depends_on_id, canonical_json(condition or {})),
            )
            mission_id = rows[0]["mission_id"]
            self._assert_acyclic_obligations(db, mission_id)
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="work",
                event_type="obligation.dependency_added",
                subject_type="obligation",
                subject_id=obligation_id,
                payload={"depends_on_id": depends_on_id, "condition": condition or {}},
            )

    @staticmethod
    def _assert_acyclic_obligations(db: Any, mission_id: str) -> None:
        rows = db.execute(
            """SELECT d.obligation_id,d.depends_on_id
               FROM obligation_dependencies d
               JOIN obligations o ON o.id=d.obligation_id
               WHERE o.mission_id=?""",
            (mission_id,),
        ).fetchall()
        graph: dict[str, set[str]] = defaultdict(set)
        nodes: set[str] = set()
        for row in rows:
            graph[row["obligation_id"]].add(row["depends_on_id"])
            nodes.update((row["obligation_id"], row["depends_on_id"]))
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise InvalidTransition("obligation dependency graph contains a cycle")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in nodes:
            visit(node)
