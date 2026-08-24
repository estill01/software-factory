from __future__ import annotations

from collections.abc import Mapping
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
            terminal_stage = db.execute(
                """SELECT id FROM acceptance_stage_records_v2
                   WHERE mission_id=? AND stage='terminal' AND status='accepted'
                   LIMIT 1""",
                (mission_id,),
            ).fetchone()
            if terminal_stage is not None:
                raise InvalidTransition(
                    "a new active program requires the accepted terminal stage to be reopened"
                )
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

    @staticmethod
    def _frontier_has_remaining(value: Any) -> bool:
        if value in (None, False, "", 0):
            return False
        if isinstance(value, Mapping):
            return any(ProgramService._frontier_has_remaining(item) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(ProgramService._frontier_has_remaining(item) for item in value)
        return True

    def complete_program(
        self,
        program_id: str,
        *,
        expected_version: int,
        reviewer_session_id: str,
        evidence_ids: list[str],
    ) -> dict[str, Any]:
        """Close a reviewed program range before terminal mission acceptance."""

        if not evidence_ids:
            raise EvidenceInvalid("program completion requires current outcome evidence")
        with self.store.transaction() as db:
            program = self.store.check_version(
                db,
                table="programs",
                row_id=program_id,
                expected_version=expected_version,
            )
            if program["status"] != "active":
                raise InvalidTransition("only an active program can complete")
            revision = db.execute(
                "SELECT * FROM program_revisions WHERE id=?",
                (program["current_revision_id"],),
            ).fetchone()
            if revision is None or revision["status"] != "accepted":
                raise InvalidTransition("program completion requires its accepted current revision")
            accepted_history = json_load(revision["accepted_history_json"], {})
            if accepted_history.get("range_complete") is not True:
                raise InvalidTransition(
                    "accepted program revision has not reconciled the full requested range"
                )
            frontier = json_load(revision["resume_frontier_json"], {})
            if self._frontier_has_remaining(frontier):
                raise InvalidTransition("program resume frontier still contains remaining work")
            unfinished = db.execute(
                """SELECT id FROM work_items
                   WHERE program_id=? AND planning_status='selected'
                     AND execution_status<>'cancelled'
                     AND acceptance_status<>'installed_accepted' LIMIT 1""",
                (program_id,),
            ).fetchone()
            if unfinished is not None:
                raise InvalidTransition(
                    "program still has selected work below installed acceptance"
                )
            reviewer = db.execute(
                "SELECT mission_id,role FROM agent_sessions WHERE id=?",
                (reviewer_session_id,),
            ).fetchone()
            if (
                reviewer is None
                or reviewer["mission_id"] != program["mission_id"]
                or reviewer["role"]
                not in {"independent_reviewer", "evaluator", "terminal_reviewer"}
            ):
                raise RoleConflict("program completion requires an independent reviewer")
            self.store.require_evidence(
                db,
                evidence_ids,
                mission_id=program["mission_id"],
                subject_type="program",
                subject_id=program_id,
                revision=revision["revision_root"],
            )
            new_version = expected_version + 1
            db.execute(
                """UPDATE programs SET status='completed',state_version=?,updated_at=?
                   WHERE id=?""",
                (new_version, utc_now(), program_id),
            )
            self.store.append_event(
                db,
                mission_id=program["mission_id"],
                stream_key="program",
                event_type="program.completed",
                subject_type="program",
                subject_id=program_id,
                source_type="session",
                source_id=reviewer_session_id,
                prior_version=expected_version,
                new_version=new_version,
                payload={
                    "program_revision_id": revision["id"],
                    "revision_root": revision["revision_root"],
                    "evidence_ids": evidence_ids,
                },
            )
        return self.store.one("SELECT * FROM programs WHERE id=?", (program_id,))

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
        accepted_values = accepted_history.get("accepted", [])
        if not isinstance(accepted_values, list) or any(
            not isinstance(value, str) or not value for value in accepted_values
        ):
            raise InvalidTransition("accepted history must contain nonempty work identifiers")
        accepted_ids = set(accepted_values)
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
            prior_revision = db.execute(
                "SELECT accepted_history_json FROM program_revisions WHERE id=?",
                (material["parent_revision_id"],),
            ).fetchone()
            if prior_revision is None:
                raise InvalidTransition("program parent revision is missing")
            prior_history = json_load(prior_revision["accepted_history_json"], {})
            prior_values = prior_history.get("accepted", [])
            if not isinstance(prior_values, list) or any(
                not isinstance(value, str) or not value for value in prior_values
            ):
                raise InvalidTransition("stored accepted history is invalid")
            if not set(prior_values).issubset(accepted_ids):
                raise InvalidTransition("program revision cannot omit accepted work history")
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
