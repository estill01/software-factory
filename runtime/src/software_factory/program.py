from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .store import InvalidTransition, Store, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now

class ProgramService:

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
            with self.store.transaction() as db:
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
                        id,program_id,sequence,source_ref<mapping_json,graph_json,
                        accepted_history_json,resume_frontier_json,status,
                        author_execution_id,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        revision_id,
                        program_id,
                        1,
                        source_ref,
                        "{}",
                        canonical_json(work_graph or {}),
                        "{}",
                        "{}",
                        "accepted",
                        author_execution_id,
                        now,
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
                    },
                )
            return program_id

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
            revision_id = new_id("rev")
            with self.store.transaction() as db:
                program = self.store.check_version(
                    db, table="programs", row_id=program_id, expected_version=expected_version
                )
                prior = db.execute(
                    "SELECT * FROM program_revisions WHERE id=?",
                    (program["current_revision_id"],),
                ).fetchone()
                if prior is None:
                    raise StoreError("current program revision is missing")
                if accepted and not review_execution_id:
                    raise InvalidTransition("accepted consequential revision requires review")
                sequence = prior["sequence"] + 1
                status = "accepted" if accepted else "proposed"
                db.execute(
                    """INSERT INTO program_revisions(
                        id,program_id,sequence,parent_id,source_ref,mapping_json,graph_json,
                        accepted_history_json,resume_frontier_json,status,
                        author_execution_id,review_execution_id,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        revision_id,
                        program_id,
                        sequence,
                        prior["id"],
                        source_ref,
                        canonical_json(mapping),
                        canonical_json(graph),
                        canonical_json(accepted_history),
                        canonical_json(resume_frontier),
                        status,
                        author_execution_id,
                        review_execution_id,
                        utc_now(),
                    ),
                )
                new_version = expected_version + 1
                if accepted:
                    db.execute(
                        """UPDATE programs SET current_revision_id=?,state_version=?,
                           updated_at=? WHERE id=?""",
                        (revision_id, new_version, utc_now(), program_id),
                    )
                self.store.append_event(
                    db,
                    mission_id=program["mission_id"],
                    stream_key="program",
                    event_type="program.revision_accepted" if accepted else "program.revision_proposed",
                    subject_type="program_revision",
                    subject_id=revision_id,
                    prior_version=expected_version,
                    new_version=new_version if accepted else expected_version,
                    payload={
                        "program_id": program_id,
                        "parent_revision_id": prior["id"],
                        "mapping": mapping,
                        "resume_frontier": resume_frontier,
                        "accepted": accepted,
                    },
                )
            return revision_id
