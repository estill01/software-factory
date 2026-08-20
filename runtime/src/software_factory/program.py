from __future__ import annotations

from typing import Any

from .errors import EvidenceInvalid, InvalidTransition, RoleConflict, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now


class ProgramService:
    def __init__(self, store: Any):
        self.store = store

    def create_program(
        self,
        *,
        mission_id: str,
        name: str,
        requested_range: dict[str, Any],
        terminal_criteria: dict[str, Any],
        source_ref: str | None = None,
        work_graph: dict[str, Any] | None = None,
        author_execution_id: str | None = None,
    ) -> str:
        program_id = new_id("pgm")
        revision_id = new_id("rev")
        now = utc_now()
        mapping: dict[str, Any] = {}
        accepted_history: dict[str, Any] = {"accepted": []}
        resume_frontier: dict[str, Any] = {}
        revision_material = {
            "program_id": program_id,
            "sequence": 1,
            "parent_revision_id": None,
            "source_ref": source_ref,
            "mapping": mapping,
            "graph": work_graph or {},
            "accepted_history": accepted_history,
            "resume_frontier": resume_frontier,
            "requested_range": requested_range,
            "terminal_criteria": terminal_criteria,
        }
        revision_root = digest_json(revision_material)
        with self.store.transaction() as db:
            mission = db.execute("SELECT id FROM missions WHERE id=?", (mission_id,)).fetchone()
            if mission is None:
                raise StoreError("mission not found")
            db.execute(
                """INSERT INTO programs(
                    id,mission_id,name,status,current_revision_id,requested_range_json,
                    terminal_criteria_json,state_version,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    program_id,
                    mission_id,
                    name,
                    "active",
                    revision_id,
                    canonical_json(requested_range),
                    canonical_json(terminal_criteria),
                    1,
                    now,
                    now,
                ),
            )
            db.execute(
                """INSERT INTO program_revisions(
                    id,program_id,sequence,source_ref,mapping_json,graph_json,
                    accepted_history_json,resume_frontier_json,status,
                    author_execution_id,created_at,revision_root
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    revision_id,
                    program_id,
                    1,
                    source_ref,
                    canonical_json(mapping),
                    canonical_json(work_graph or {}),
                    canonical_json(accepted_history),
                    canonical_json(resume_frontier),
                    "accepted",
                    author_execution_id,
                    now,
                    revision_root,
                ),
            )
            self.store.append_event(
                db,
                mission_id=mission_id,
                stream_key="program",
                event_type="program.created",
                subject_type="program",
                subject_id=program_id,
                new_version=1,
                payload={
                    "name": name,
                    "revision_id": revision_id,
                    "requested_range": requested_range,
                    "terminal_criteria": terminal_criteria,
                    "revision_root": revision_root,
                },
            )
        return program_id

    def preview_program_revision(
        self,
        program_id: str,
        *,
        mapping: dict[str, Any],
        graph: dict[str, Any],
        accepted_history: dict[str, Any],
        resume_frontier: dict[str, Any],
        source_ref: str,
    ) -> dict[str, Any]:
        program = self.store.one("SELECT * FROM programs WHERE id=?", (program_id,))
        prior = self.store.one(
            "SELECT * FROM program_revisions WHERE id=?",
            (program["current_revision_id"],),
        )
        material = {
            "program_id": program_id,
            "sequence": prior["sequence"] + 1,
            "parent_revision_id": prior["id"],
            "source_ref": source_ref,
            "mapping": mapping,
            "graph": graph,
            "accepted_history": accepted_history,
            "resume_frontier": resume_frontier,
            "requested_range": json_load(program["requested_range_json"], {}),
            "terminal_criteria": json_load(program["terminal_criteria_json"], {}),
        }
        return {"material": material, "revision_root": digest_json(material)}

    @staticmethod
    def _require_review(
        db: Any,
        *,
        program_id: str,
        revision_root: str,
        author_execution_id: str | None,
        review_execution_id: str,
    ) -> str:
        review = db.execute(
            "SELECT * FROM executions WHERE id=?", (review_execution_id,)
        ).fetchone()
        if review is None or review["status"] != "succeeded":
            raise EvidenceInvalid("program review execution is missing or not successful")
        if review["execution_type"] not in {
            "independent_review",
            "tracker_authoring_review",
            "program_review",
        }:
            raise EvidenceInvalid("program revision requires an independent review execution")
        if author_execution_id and review_execution_id == author_execution_id:
            raise RoleConflict("program author cannot review the same revision")
        result = json_load(review["result_json"], {})
        if result.get("program_id") != program_id:
            raise EvidenceInvalid("review is bound to another program")
        if result.get("revision_root") != revision_root:
            raise EvidenceInvalid("review is stale or bound to another revision")
        if result.get("disposition") != "accept":
            raise EvidenceInvalid("review did not accept the revision")
        return digest_json(
            {
                "review_execution_id": review_execution_id,
                "agent_session_id": review["agent_session_id"],
                "revision_root": revision_root,
                "result": result,
            }
        )

    def propose_program_revision(
        self,
        program_id: str,
        *,
        expected_version: int,
        mapping: dict[str, Any],
        graph: dict[str, Any],
        accepted_history: dict[str, Any],
        resume_frontier: dict[str, Any],
        source_ref: str,
        author_execution_id: str | None,
    ) -> str:
        revision_id = new_id("rev")
        preview = self.preview_program_revision(
            program_id,
            mapping=mapping,
            graph=graph,
            accepted_history=accepted_history,
            resume_frontier=resume_frontier,
            source_ref=source_ref,
        )
        material = preview["material"]
        accepted_ids = set(accepted_history.get("accepted", []))
        if not accepted_ids.issubset(set(mapping)):
            raise InvalidTransition("accepted work must have explicit old-to-new mapping")
        with self.store.transaction() as db:
            program = self.store.check_version(
                db,
                table="programs",
                row_id=program_id,
                expected_version=expected_version,
            )
            if program["current_revision_id"] != material["parent_revision_id"]:
                raise InvalidTransition("program current revision changed during proposal")
            db.execute(
                """INSERT INTO program_revisions(
                    id,program_id,sequence,parent_id,source_ref,mapping_json,graph_json,
                    accepted_history_json,resume_frontier_json,status,
                    author_execution_id,created_at,revision_root
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    revision_id,
                    program_id,
                    material["sequence"],
                    material["parent_revision_id"],
                    source_ref,
                    canonical_json(mapping),
                    canonical_json(graph),
                    canonical_json(accepted_history),
                    canonical_json(resume_frontier),
                    "proposed",
                    author_execution_id,
                    utc_now(),
                    preview["revision_root"],
                ),
            )
            self.store.append_event(
                db,
                mission_id=program["mission_id"],
                stream_key="program",
                event_type="program.revision_proposed",
                subject_type="program_revision",
                subject_id=revision_id,
                prior_version=expected_version,
                new_version=expected_version,
                payload={
                    "program_id": program_id,
                    "parent_revision_id": material["parent_revision_id"],
                    "mapping": mapping,
                    "resume_frontier": resume_frontier,
                    "revision_root": preview["revision_root"],
                },
            )
        return revision_id

    def accept_program_revision(
        self,
        revision_id: str,
        *,
        expected_program_version: int,
        review_execution_id: str,
    ) -> str:
        with self.store.transaction() as db:
            revision = db.execute(
                "SELECT * FROM program_revisions WHERE id=?", (revision_id,)
            ).fetchone()
            if revision is None or revision["status"] != "proposed":
                raise InvalidTransition("only a proposed revision can be accepted")
            program = self.store.check_version(
                db,
                table="programs",
                row_id=revision["program_id"],
                expected_version=expected_program_version,
            )
            if program["current_revision_id"] != revision["parent_id"]:
                raise InvalidTransition("revision no longer descends from current program")
            review_root = self._require_review(
                db,
                program_id=revision["program_id"],
                revision_root=revision["revision_root"],
                author_execution_id=revision["author_execution_id"],
                review_execution_id=review_execution_id,
            )
            new_version = expected_program_version + 1
            db.execute(
                """UPDATE program_revisions
                   SET status='accepted',review_execution_id=?,review_root=?
                   WHERE id=?""",
                (review_execution_id, review_root, revision_id),
            )
            db.execute(
                """UPDATE program_revisions SET status='superseded'
                   WHERE id=? AND status='accepted'""",
                (revision["parent_id"],),
            )
            db.execute(
                """UPDATE programs SET current_revision_id=?,state_version=?,updated_at=?
                   WHERE id=?""",
                (revision_id, new_version, utc_now(), revision["program_id"]),
            )
            self.store.append_event(
                db,
                mission_id=program["mission_id"],
                stream_key="program",
                event_type="program.revision_accepted",
                subject_type="program_revision",
                subject_id=revision_id,
                prior_version=expected_program_version,
                new_version=new_version,
                payload={
                    "program_id": revision["program_id"],
                    "parent_revision_id": revision["parent_id"],
                    "revision_root": revision["revision_root"],
                    "review_root": review_root,
                },
            )
        return revision_id

    def revise_program(
        self,
        program_id: str,
        *,
        expected_version: int,
        mapping: dict[str, Any],
        graph: dict[str, Any],
        accepted_history: dict[str, Any],
        resume_frontier: dict[str, Any],
        source_ref: str,
        author_execution_id: str | None,
        review_execution_id: str | None,
        accepted: bool,
    ) -> str:
        revision_id = self.propose_program_revision(
            program_id,
            expected_version=expected_version,
            mapping=mapping,
            graph=graph,
            accepted_history=accepted_history,
            resume_frontier=resume_frontier,
            source_ref=source_ref,
            author_execution_id=author_execution_id,
        )
        if accepted:
            if review_execution_id is None:
                raise InvalidTransition("accepted revision requires review execution")
            self.accept_program_revision(
                revision_id,
                expected_program_version=expected_version,
                review_execution_id=review_execution_id,
            )
        return revision_id
