from __future__ import annotations

from typing import Any

from .errors import EvidenceInvalid, InvalidTransition, RoleConflict, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now


class QAService:
    """Revision-bound QA generation, execution, independent review, and acceptance."""

    def _candidate_context(self, db: Any, work_item_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        work_row = db.execute("SELECT * FROM work_items WHERE id=?", (work_item_id,)).fetchone()
        if work_row is None:
            raise StoreError("work item not found")
        work = dict(work_row)
        assignment_row = db.execute(
            """SELECT a.*,w.path,w.current_revision,w.status AS workspace_status
               FROM work_assignments a JOIN workspaces w ON w.id=a.workspace_id
               WHERE a.work_item_id=? AND a.role='implementer'
                 AND a.status IN ('accepted','active','completed')
               ORDER BY a.created_at DESC LIMIT 1""",
            (work_item_id,),
        ).fetchone()
        if assignment_row is None:
            raise InvalidTransition("candidate has no implementation assignment/workspace")
        return work, dict(assignment_row)

    def submit_candidate(
        self,
        execution_id: str,
        *,
        expected_work_version: int,
    ) -> dict[str, Any]:
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        if execution["status"] != "succeeded" or not execution["work_item_id"]:
            raise InvalidTransition("only a successful implementation execution can submit a candidate")
        if not execution["workspace_id"]:
            raise InvalidTransition("candidate execution has no workspace")
        frozen = self.freeze_workspace(execution["workspace_id"])
        with self.store.transaction() as db:
            work = self.store.check_version(
                db,
                table="work_items",
                row_id=execution["work_item_id"],
                expected_version=expected_work_version,
            )
            if work["execution_status"] not in {"submitted", "running"}:
                raise InvalidTransition("work is not ready for candidate submission")
            spec = json_load(work["acceptance_spec_json"], {})
            candidate_root = digest_json(
                {
                    "work_item_id": work["id"],
                    "workspace_id": execution["workspace_id"],
                    "revision": frozen["revision"],
                    "tree": frozen["tree"],
                    "changed_files": frozen["changed_files"],
                    "acceptance_spec": spec,
                    "program_revision_id": work["program_revision_id"],
                }
            )
            if work["candidate_revision"] and work["candidate_revision"] != frozen["revision"]:
                db.execute(
                    """UPDATE qa_requirements SET status='stale',updated_at=?
                       WHERE work_item_id=? AND status IN ('pending','running','passed','failed')""",
                    (utc_now(), work["id"]),
                )
                db.execute(
                    """UPDATE qa_results SET stale_at=? WHERE requirement_id IN (
                         SELECT id FROM qa_requirements WHERE work_item_id=?
                       ) AND stale_at IS NULL""",
                    (utc_now(), work["id"]),
                )
                db.execute(
                    """UPDATE evidence_records SET status='stale',invalidated_at=?
                       WHERE subject_type='work_item' AND subject_id=? AND status='current'""",
                    (utc_now(), work["id"]),
                )
            existing = db.execute(
                """SELECT COUNT(*) AS n FROM qa_requirements
                   WHERE work_item_id=? AND phase='candidate' AND status<>'stale'
                     AND candidate_revision=?""",
                (work["id"], frozen["revision"]),
            ).fetchone()["n"]
            if not existing:
                requirements = spec.get("candidate", [])
                if not requirements:
                    requirements = [
                        {"type": "git_clean", "required": True},
                        {"type": "independent_review", "required": True, "role": "independent_reviewer"},
                    ]
                for item in requirements:
                    qa_type = str(item.get("type") or "predicate")
                    db.execute(
                        """INSERT INTO qa_requirements(
                            id,work_item_id,phase,qa_type,required,independence_role,
                            command_json,predicate_json,status,candidate_revision,created_at,
                            updated_at,acceptance_contract_root,state_version
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            new_id("qar"),
                            work["id"],
                            "candidate",
                            qa_type,
                            int(item.get("required", True)),
                            item.get("role"),
                            canonical_json({"argv": item.get("command", [])}),
                            canonical_json(item.get("predicate", {})),
                            "pending",
                            frozen["revision"],
                            utc_now(),
                            utc_now(),
                            candidate_root,
                            1,
                        ),
                    )
            new_version = expected_work_version + 1
            db.execute(
                """UPDATE work_items SET candidate_revision=?,execution_status='submitted',
                   qa_status='pending',acceptance_status='pending',state_version=?,updated_at=?
                   WHERE id=?""",
                (frozen["revision"], new_version, utc_now(), work["id"]),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="qa",
                event_type="candidate.submitted",
                subject_type="work_item",
                subject_id=work["id"],
                prior_version=expected_work_version,
                new_version=new_version,
                payload={**frozen, "candidate_root": candidate_root, "execution_id": execution_id},
            )
        return {
            "work_item_id": execution["work_item_id"],
            **frozen,
            "candidate_root": candidate_root,
            "requirements": self.store.all(
                "SELECT * FROM qa_requirements WHERE work_item_id=? AND phase='candidate' ORDER BY created_at",
                (execution["work_item_id"],),
            ),
        }

    def _record_qa_result(
        self,
        *,
        requirement_id: str,
        execution_id: str | None,
        status: str,
        revision: str,
        evidence_id: str,
        result: dict[str, Any],
        reviewer_session_id: str | None = None,
        reviewer_assignment_id: str | None = None,
    ) -> str:
        result_id = new_id("qrs")
        with self.store.transaction() as db:
            requirement = db.execute(
                "SELECT * FROM qa_requirements WHERE id=?", (requirement_id,)
            ).fetchone()
            if requirement is None or requirement["status"] == "stale":
                raise InvalidTransition("QA requirement is missing or stale")
            if requirement["candidate_revision"] != revision:
                raise EvidenceInvalid("QA result revision does not match requirement")
            db.execute(
                """INSERT INTO qa_results(
                    id,requirement_id,execution_id,status,revision,evidence_id,result_json,
                    reviewer_session_id,observed_at,candidate_root,reviewer_assignment_id
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result_id,
                    requirement_id,
                    execution_id,
                    status,
                    revision,
                    evidence_id,
                    canonical_json(result),
                    reviewer_session_id,
                    utc_now(),
                    requirement["acceptance_contract_root"],
                    reviewer_assignment_id,
                ),
            )
            db.execute(
                """UPDATE qa_requirements SET status=?,updated_at=?,state_version=state_version+1
                   WHERE id=?""",
                ("passed" if status == "passed" else "failed", utc_now(), requirement_id),
            )
        return result_id

    def run_qa_command(
        self,
        requirement_id: str,
        *,
        agent_session_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        requirement = self.store.one(
            "SELECT * FROM qa_requirements WHERE id=?", (requirement_id,)
        )
        connection = self.store.connect()
        try:
            work, implementation = self._candidate_context(connection, requirement["work_item_id"])
        finally:
            connection.close()
        implementation_workspace = self.store.one(
            "SELECT * FROM workspaces WHERE id=?", (implementation["workspace_id"],)
        )
        command = json_load(requirement["command_json"], {}).get("argv", [])
        if requirement["qa_type"] == "git_clean":
            command = ["git", "status", "--porcelain=v1"]
        if not command:
            raise InvalidTransition("QA command requirement has no command")
        verification_workspace = self.create_workspace(
            repository_id=implementation_workspace["repository_id"],
            mission_id=work["mission_id"],
            work_item_id=work["id"],
            workspace_type="verification_lane",
            base_revision=requirement["candidate_revision"],
            writable_scope=json_load(work["writable_scope_json"], []),
        )
        execution_id = self.queue_execution(
            mission_id=work["mission_id"],
            execution_type="validation",
            idempotency_key=f"qa:{requirement_id}:{requirement['candidate_revision']}",
            work_item_id=work["id"],
            agent_session_id=agent_session_id,
            workspace_id=verification_workspace,
            input_payload={"qa_requirement_id": requirement_id, "command": command},
            expected_effect={"qa_type": requirement["qa_type"], "revision": requirement["candidate_revision"]},
        )
        generation = self.acquire_leases(
            execution_id,
            [{"kind": "workspace", "key": verification_workspace, "mode": "exclusive"}],
            ttl_seconds=max(timeout_seconds + 30, 60),
        )
        try:
            observed = self.run_command(
                execution_id,
                command,
                generation=generation,
                timeout_seconds=timeout_seconds,
                allowed_exit_codes={0},
            )
        finally:
            self.retire_workspace(verification_workspace, force=True)
        passed = observed["status"] == "succeeded"
        if requirement["qa_type"] == "git_clean":
            stdout = self.artifacts.read(observed["stdout_artifact_id"]).decode("utf-8", errors="replace")
            passed = passed and not stdout.strip()
        evidence_id = self.store.record_evidence(
            mission_id=work["mission_id"],
            evidence_type="qa_command",
            subject_type="work_item",
            subject_id=work["id"],
            revision=requirement["candidate_revision"],
            execution_id=execution_id,
            producer_session_id=agent_session_id,
            payload={"requirement_id": requirement_id, "observed": observed, "passed": passed},
        )
        self._record_qa_result(
            requirement_id=requirement_id,
            execution_id=execution_id,
            status="passed" if passed else "failed",
            revision=requirement["candidate_revision"],
            evidence_id=evidence_id,
            result=observed,
            reviewer_session_id=agent_session_id,
        )
        return {"execution_id": execution_id, "passed": passed, "evidence_id": evidence_id, **observed}

    def record_independent_review(
        self,
        requirement_id: str,
        *,
        reviewer_session_id: str,
        disposition: str,
        findings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if disposition not in {"accept", "changes_requested", "reject"}:
            raise ValueError("unsupported review disposition")
        requirement = self.store.one(
            "SELECT * FROM qa_requirements WHERE id=?", (requirement_id,)
        )
        work = self.store.one(
            "SELECT * FROM work_items WHERE id=?", (requirement["work_item_id"],)
        )
        reviewer = self.store.one(
            "SELECT * FROM agent_sessions WHERE id=?", (reviewer_session_id,)
        )
        if reviewer["mission_id"] != work["mission_id"] or reviewer["role"] not in {
            "independent_reviewer",
            "reviewer",
            "evaluator",
            "terminal_reviewer",
        }:
            raise RoleConflict("reviewer does not hold an independent review role")
        implementers = self.store.all(
            """SELECT agent_session_id FROM work_assignments
               WHERE work_item_id=? AND role='implementer'
                 AND status IN ('accepted','active','completed','released')""",
            (work["id"],),
        )
        if reviewer_session_id in {row["agent_session_id"] for row in implementers}:
            raise RoleConflict("implementer cannot review its own candidate")
        result = {
            "work_item_id": work["id"],
            "revision": requirement["candidate_revision"],
            "candidate_root": requirement["acceptance_contract_root"],
            "disposition": disposition,
            "findings": findings or [],
        }
        execution_id = self.queue_execution(
            mission_id=work["mission_id"],
            execution_type="independent_review",
            idempotency_key=f"review:{requirement_id}:{reviewer_session_id}:{digest_json(result)}",
            work_item_id=work["id"],
            agent_session_id=reviewer_session_id,
            input_payload=result,
        )
        with self.store.transaction() as db:
            db.execute(
                """UPDATE executions SET status='succeeded',result_json=?,started_at=?,finished_at=?,
                   state_version=state_version+1 WHERE id=?""",
                (canonical_json(result), utc_now(), utc_now(), execution_id),
            )
        evidence_id = self.store.record_evidence(
            mission_id=work["mission_id"],
            evidence_type="independent_review",
            subject_type="work_item",
            subject_id=work["id"],
            revision=requirement["candidate_revision"],
            execution_id=execution_id,
            producer_session_id=reviewer_session_id,
            payload=result,
        )
        self._record_qa_result(
            requirement_id=requirement_id,
            execution_id=execution_id,
            status="passed" if disposition == "accept" else "failed",
            revision=requirement["candidate_revision"],
            evidence_id=evidence_id,
            result=result,
            reviewer_session_id=reviewer_session_id,
        )
        if disposition != "accept":
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE work_items SET qa_status='changes_requested',updated_at=?
                       WHERE id=?""",
                    (utc_now(), work["id"]),
                )
                if findings:
                    for finding in findings:
                        db.execute(
                            """INSERT INTO obligations(
                                id,mission_id,capability_id,parent_id,obligation_type,description,
                                status,priority,resolution_json,state_version,created_at,updated_at
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                new_id("obl"),
                                work["mission_id"],
                                None,
                                work["obligation_id"],
                                "remediate",
                                str(finding.get("statement") or "Resolve review finding"),
                                "open",
                                int(finding.get("priority", work["priority"])),
                                "{}",
                                1,
                                utc_now(),
                                utc_now(),
                            ),
                        )
        return {"execution_id": execution_id, "evidence_id": evidence_id, **result}

    def accept_candidate(self, work_item_id: str, *, expected_work_version: int) -> dict[str, Any]:
        with self.store.transaction() as db:
            work = self.store.check_version(
                db,
                table="work_items",
                row_id=work_item_id,
                expected_version=expected_work_version,
            )
            if not work["candidate_revision"] or work["execution_status"] != "submitted":
                raise InvalidTransition("work has no submitted candidate")
            _, implementation = self._candidate_context(db, work_item_id)
            workspace = db.execute(
                "SELECT * FROM workspaces WHERE id=?", (implementation["workspace_id"],)
            ).fetchone()
            actual_revision = self.git_revision(workspace["path"])
            if actual_revision != work["candidate_revision"] or not self.git_is_clean(workspace["path"]):
                raise EvidenceInvalid("candidate changed after QA freeze")
            requirements = db.execute(
                """SELECT * FROM qa_requirements WHERE work_item_id=? AND phase='candidate'
                   AND candidate_revision=? AND status<>'stale'""",
                (work_item_id, work["candidate_revision"]),
            ).fetchall()
            if not requirements:
                raise EvidenceInvalid("candidate has no QA requirements")
            missing = [
                row["id"]
                for row in requirements
                if row["required"] and row["status"] != "passed"
            ]
            if missing:
                raise EvidenceInvalid(f"candidate QA remains incomplete: {missing}")
            reviews = db.execute(
                """SELECT qr.reviewer_session_id FROM qa_results qr
                   JOIN qa_requirements q ON q.id=qr.requirement_id
                   WHERE q.work_item_id=? AND q.phase='candidate' AND q.qa_type IN (
                     'independent_review','review','architecture_review'
                   ) AND qr.status='passed' AND qr.stale_at IS NULL""",
                (work_item_id,),
            ).fetchall()
            implementer_id = implementation["agent_session_id"]
            if reviews and any(row["reviewer_session_id"] == implementer_id for row in reviews):
                raise RoleConflict("candidate review is not independent")
            new_version = expected_work_version + 1
            db.execute(
                """UPDATE work_items SET qa_status='passed',acceptance_status='candidate_accepted',
                   state_version=?,updated_at=? WHERE id=?""",
                (new_version, utc_now(), work_item_id),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="qa",
                event_type="candidate.accepted",
                subject_type="work_item",
                subject_id=work_item_id,
                prior_version=expected_work_version,
                new_version=new_version,
                payload={
                    "candidate_revision": work["candidate_revision"],
                    "qa_requirement_ids": [row["id"] for row in requirements],
                    "reviewer_session_ids": [row["reviewer_session_id"] for row in reviews],
                },
            )
        return self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,))
