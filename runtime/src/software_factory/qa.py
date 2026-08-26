from __future__ import annotations

from typing import Any

from .errors import EvidenceInvalid, InvalidTransition, RoleConflict, StoreError
from .util import canonical_json, digest_json, json_load, new_id, utc_now


class QAService:
    """Revision-bound QA generation, execution, independent review, and acceptance."""

    def __init__(
        self,
        store: Any,
        workspaces: Any,
        executions: Any,
        *,
        target_profiles: Any | None = None,
    ):
        self.store = store
        self.workspaces = workspaces
        self.executions = executions
        self.target_profiles = target_profiles

    def _candidate_context(
        self, db: Any, work_item_id: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
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
            raise InvalidTransition(
                "only a successful implementation execution can submit a candidate"
            )
        if not execution["workspace_id"]:
            raise InvalidTransition("candidate execution has no workspace")
        frozen = self.workspaces.freeze_workspace(execution["workspace_id"])
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
                        {
                            "type": "independent_review",
                            "required": True,
                            "role": "independent_reviewer",
                        },
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

    def submit_profile_candidate(
        self,
        execution_id: str,
        *,
        profile_key: str,
        target_id: str,
        expected_revision: str,
        expected_currentness_root: str,
        expected_work_version: int,
    ) -> dict[str, Any]:
        """Submit a non-workspace profile result through the canonical QA owner."""

        if self.target_profiles is None:
            raise InvalidTransition("target-profile candidate submission is not configured")
        target_profiles = self.target_profiles
        execution = self.store.one("SELECT * FROM executions WHERE id=?", (execution_id,))
        if execution["status"] != "succeeded" or not execution["work_item_id"]:
            raise InvalidTransition(
                "only a successful bound execution can submit a target-profile candidate"
            )
        if execution["workspace_id"]:
            raise InvalidTransition("workspace candidates must use the software QA submission")
        with (
            target_profiles.currentness_fence(
                profile_key,
                target_id,
                expected_revision=expected_revision,
                expected_currentness_root=expected_currentness_root,
            ) as snapshot,
            self.store.transaction() as db,
        ):
            work = self.store.check_version(
                db,
                table="work_items",
                row_id=execution["work_item_id"],
                expected_version=expected_work_version,
            )
            if work["execution_status"] not in {"submitted", "running"}:
                raise InvalidTransition("work is not ready for target-profile candidate submission")
            expected_effect = json_load(work["expected_effect_json"], {})
            if expected_effect.get("target_profile") != profile_key:
                raise InvalidTransition("work item is bound to another target profile")
            if expected_effect.get("target_id") != target_id:
                raise InvalidTransition("work item is bound to another profile target")
            spec = json_load(work["acceptance_spec_json"], {})
            candidate_root = digest_json(
                {
                    "work_item_id": work["id"],
                    "execution_id": execution_id,
                    "profile_key": profile_key,
                    "target_id": target_id,
                    "revision": snapshot.revision,
                    "currentness_root": snapshot.currentness_root,
                    "attributes": dict(snapshot.attributes),
                    "acceptance_spec": spec,
                    "program_revision_id": work["program_revision_id"],
                }
            )
            if work["candidate_revision"] and work["candidate_revision"] != snapshot.revision:
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
                (work["id"], snapshot.revision),
            ).fetchone()["n"]
            if not existing:
                requirements = spec.get("candidate", []) or [
                    {"type": "profile_currentness", "required": True},
                    {
                        "type": "independent_review",
                        "required": True,
                        "role": "independent_reviewer",
                    },
                ]
                for item in requirements:
                    qa_type = str(item.get("type") or "predicate")
                    predicate = dict(item.get("predicate", {}))
                    if qa_type == "profile_currentness":
                        predicate = {
                            "profile_key": profile_key,
                            "target_id": target_id,
                            "revision": snapshot.revision,
                            "currentness_root": snapshot.currentness_root,
                            "attributes": dict(snapshot.attributes),
                            "execution_id": execution_id,
                        }
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
                            canonical_json(predicate),
                            "pending",
                            snapshot.revision,
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
                (snapshot.revision, new_version, utc_now(), work["id"]),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="qa",
                event_type="profile_candidate.submitted",
                subject_type="work_item",
                subject_id=work["id"],
                prior_version=expected_work_version,
                new_version=new_version,
                payload={
                    "execution_id": execution_id,
                    "profile_key": profile_key,
                    "target_id": target_id,
                    "revision": snapshot.revision,
                    "currentness_root": snapshot.currentness_root,
                    "candidate_root": candidate_root,
                },
            )
        return {
            "work_item_id": execution["work_item_id"],
            "profile_key": profile_key,
            "target_id": target_id,
            "revision": snapshot.revision,
            "currentness_root": snapshot.currentness_root,
            "candidate_root": candidate_root,
            "requirements": self.store.all(
                """SELECT * FROM qa_requirements
                   WHERE work_item_id=? AND phase='candidate' ORDER BY created_at""",
                (execution["work_item_id"],),
            ),
        }

    def record_profile_currentness(self, requirement_id: str) -> dict[str, Any]:
        """Observe and pass one exact non-workspace currentness requirement."""

        requirement = self.store.one("SELECT * FROM qa_requirements WHERE id=?", (requirement_id,))
        if requirement["qa_type"] != "profile_currentness":
            raise InvalidTransition("QA requirement is not a profile-currentness check")
        predicate = json_load(requirement["predicate_json"], {})
        required = {
            "profile_key",
            "target_id",
            "revision",
            "currentness_root",
            "attributes",
            "execution_id",
        }
        if set(predicate) != required:
            raise EvidenceInvalid("profile-currentness requirement has no exact target binding")
        profile_key = str(predicate["profile_key"])
        target_id = str(predicate["target_id"])
        revision = str(predicate["revision"])
        currentness_root = str(predicate["currentness_root"])
        target_profiles = self.target_profiles
        if target_profiles is None:
            raise InvalidTransition("target-profile currentness QA is not configured")
        with target_profiles.currentness_fence(
            profile_key,
            target_id,
            expected_revision=revision,
            expected_currentness_root=currentness_root,
        ) as snapshot:
            if dict(snapshot.attributes) != predicate["attributes"]:
                raise EvidenceInvalid("profile target attributes changed before QA observation")
            work = self.store.one(
                "SELECT * FROM work_items WHERE id=?", (requirement["work_item_id"],)
            )
            result = {
                "profile_key": profile_key,
                "target_id": target_id,
                "revision": snapshot.revision,
                "currentness_root": snapshot.currentness_root,
                "attributes": dict(snapshot.attributes),
                "passed": True,
            }
            evidence_id = self.store.record_evidence(
                mission_id=work["mission_id"],
                evidence_type="profile_currentness",
                subject_type="work_item",
                subject_id=work["id"],
                revision=snapshot.revision,
                execution_id=str(predicate["execution_id"]),
                payload={"requirement_id": requirement_id, **result},
            )
            self._record_qa_result(
                requirement_id=requirement_id,
                execution_id=str(predicate["execution_id"]),
                status="passed",
                revision=snapshot.revision,
                evidence_id=evidence_id,
                result=result,
            )
        return {"evidence_id": evidence_id, **result}

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
        requirement = self.store.one("SELECT * FROM qa_requirements WHERE id=?", (requirement_id,))
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
        verification_workspace = self.workspaces.create_workspace(
            repository_id=implementation_workspace["repository_id"],
            mission_id=work["mission_id"],
            work_item_id=work["id"],
            workspace_type="verification_lane",
            base_revision=requirement["candidate_revision"],
            writable_scope=json_load(work["writable_scope_json"], []),
        )
        execution_id = self.executions.queue_execution(
            mission_id=work["mission_id"],
            execution_type="validation",
            idempotency_key=f"qa:{requirement_id}:{requirement['candidate_revision']}",
            work_item_id=work["id"],
            agent_session_id=agent_session_id,
            workspace_id=verification_workspace,
            input_payload={"qa_requirement_id": requirement_id, "command": command},
            expected_effect={
                "qa_type": requirement["qa_type"],
                "revision": requirement["candidate_revision"],
            },
        )
        generation = self.executions.acquire_leases(
            execution_id,
            [{"kind": "workspace", "key": verification_workspace, "mode": "exclusive"}],
            ttl_seconds=max(timeout_seconds + 30, 60),
        )
        try:
            observed = self.executions.run_command(
                execution_id,
                command,
                generation=generation,
                timeout_seconds=timeout_seconds,
                allowed_exit_codes={0},
            )
        finally:
            self.workspaces.retire_workspace(verification_workspace, force=True)
        passed = observed["status"] == "succeeded"
        if requirement["qa_type"] == "git_clean":
            stdout = self.executions.artifacts.read(observed["stdout_artifact_id"]).decode(
                "utf-8", errors="replace"
            )
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
        return {
            "execution_id": execution_id,
            "passed": passed,
            "evidence_id": evidence_id,
            **observed,
        }

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
        requirement = self.store.one("SELECT * FROM qa_requirements WHERE id=?", (requirement_id,))
        work = self.store.one("SELECT * FROM work_items WHERE id=?", (requirement["work_item_id"],))
        reviewer = self.store.one("SELECT * FROM agent_sessions WHERE id=?", (reviewer_session_id,))
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
        execution_implementers = self.store.all(
            """SELECT DISTINCT agent_session_id FROM executions
               WHERE work_item_id=? AND agent_session_id IS NOT NULL
                 AND execution_type NOT IN (
                   'independent_review','validation','program_review','terminal_verification'
                 )""",
            (work["id"],),
        )
        implementer_ids = {
            row["agent_session_id"] for row in (*implementers, *execution_implementers)
        }
        if reviewer_session_id in implementer_ids:
            raise RoleConflict("implementer cannot review its own candidate")
        result = {
            "work_item_id": work["id"],
            "revision": requirement["candidate_revision"],
            "candidate_root": requirement["acceptance_contract_root"],
            "disposition": disposition,
            "findings": findings or [],
        }
        execution_id = self.executions.queue_execution(
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

    def _complete_profile_candidate_qa(
        self,
        work_item_id: str,
        *,
        profile_key: str,
        target_id: str,
        expected_work_version: int,
    ) -> dict[str, Any]:
        initial = self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,))
        if not initial["candidate_revision"]:
            raise InvalidTransition("work has no submitted profile candidate")
        requirements = self.store.all(
            """SELECT * FROM qa_requirements WHERE work_item_id=? AND phase='candidate'
               AND candidate_revision=? AND status<>'stale' ORDER BY created_at""",
            (work_item_id, initial["candidate_revision"]),
        )
        currentness = [row for row in requirements if row["qa_type"] == "profile_currentness"]
        if len(currentness) != 1:
            raise EvidenceInvalid("profile candidate requires one exact currentness check")
        predicate = json_load(currentness[0]["predicate_json"], {})
        expected_currentness_root = str(predicate.get("currentness_root") or "")
        if (
            predicate.get("profile_key") != profile_key
            or predicate.get("target_id") != target_id
            or predicate.get("revision") != initial["candidate_revision"]
            or not expected_currentness_root
        ):
            raise EvidenceInvalid("profile-currentness requirement is not bound to the candidate")

        target_profiles = self.target_profiles
        if target_profiles is None:
            raise InvalidTransition("target-profile candidate completion is not configured")
        with (
            target_profiles.currentness_fence(
                profile_key,
                target_id,
                expected_revision=initial["candidate_revision"],
                expected_currentness_root=expected_currentness_root,
            ) as snapshot,
            self.store.transaction() as db,
        ):
            work = self.store.check_version(
                db,
                table="work_items",
                row_id=work_item_id,
                expected_version=expected_work_version,
            )
            if work["execution_status"] != "submitted":
                raise InvalidTransition("work has no submitted profile candidate")
            expected_effect = json_load(work["expected_effect_json"], {})
            if (
                expected_effect.get("target_profile") != profile_key
                or expected_effect.get("target_id") != target_id
            ):
                raise InvalidTransition("profile candidate target binding changed")
            if dict(snapshot.attributes) != predicate.get("attributes"):
                raise EvidenceInvalid("profile target attributes changed after QA observation")
            current_requirements = db.execute(
                """SELECT * FROM qa_requirements WHERE work_item_id=? AND phase='candidate'
                   AND candidate_revision=? AND status<>'stale'""",
                (work_item_id, work["candidate_revision"]),
            ).fetchall()
            if not current_requirements:
                raise EvidenceInvalid("profile candidate has no QA requirements")
            missing = [
                row["id"]
                for row in current_requirements
                if row["required"] and row["status"] != "passed"
            ]
            if missing:
                raise EvidenceInvalid(f"profile candidate QA remains incomplete: {missing}")
            reviews = db.execute(
                """SELECT qr.reviewer_session_id FROM qa_results qr
                   JOIN qa_requirements q ON q.id=qr.requirement_id
                   WHERE q.work_item_id=? AND q.phase='candidate'
                     AND q.candidate_revision=? AND q.qa_type IN (
                       'independent_review','review','architecture_review'
                     ) AND qr.status='passed' AND qr.stale_at IS NULL""",
                (work_item_id, work["candidate_revision"]),
            ).fetchall()
            execution = db.execute(
                "SELECT work_item_id,agent_session_id FROM executions WHERE id=?",
                (str(predicate.get("execution_id") or ""),),
            ).fetchone()
            if execution is None or execution["work_item_id"] != work_item_id:
                raise EvidenceInvalid("profile candidate implementation execution is missing")
            implementer_id = execution["agent_session_id"]
            if reviews and any(row["reviewer_session_id"] == implementer_id for row in reviews):
                raise RoleConflict("profile candidate review is not independent")
            new_version = expected_work_version + 1
            db.execute(
                """UPDATE work_items SET qa_status='passed',acceptance_status='pending',
                   state_version=?,updated_at=? WHERE id=?""",
                (new_version, utc_now(), work_item_id),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="qa",
                event_type="profile_candidate.qa_completed",
                subject_type="work_item",
                subject_id=work_item_id,
                prior_version=expected_work_version,
                new_version=new_version,
                payload={
                    "profile_key": profile_key,
                    "target_id": target_id,
                    "candidate_revision": work["candidate_revision"],
                    "currentness_root": snapshot.currentness_root,
                    "qa_requirement_ids": [row["id"] for row in current_requirements],
                    "reviewer_session_ids": [row["reviewer_session_id"] for row in reviews],
                },
            )
        return self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,))

    def complete_candidate_qa(
        self, work_item_id: str, *, expected_work_version: int
    ) -> dict[str, Any]:
        initial = self.store.one("SELECT * FROM work_items WHERE id=?", (work_item_id,))
        expected_effect = json_load(initial["expected_effect_json"], {})
        profile_key = expected_effect.get("target_profile")
        target_id = expected_effect.get("target_id")
        if isinstance(profile_key, str) and isinstance(target_id, str):
            return self._complete_profile_candidate_qa(
                work_item_id,
                profile_key=profile_key,
                target_id=target_id,
                expected_work_version=expected_work_version,
            )
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
            actual_revision = self.workspaces.git_revision(workspace["path"])
            if actual_revision != work["candidate_revision"] or not self.workspaces.git_is_clean(
                workspace["path"]
            ):
                raise EvidenceInvalid("candidate changed after QA freeze")
            requirements = db.execute(
                """SELECT * FROM qa_requirements WHERE work_item_id=? AND phase='candidate'
                   AND candidate_revision=? AND status<>'stale'""",
                (work_item_id, work["candidate_revision"]),
            ).fetchall()
            if not requirements:
                raise EvidenceInvalid("candidate has no QA requirements")
            missing = [
                row["id"] for row in requirements if row["required"] and row["status"] != "passed"
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
                """UPDATE work_items SET qa_status='passed',acceptance_status='pending',
                   state_version=?,updated_at=? WHERE id=?""",
                (new_version, utc_now(), work_item_id),
            )
            self.store.append_event(
                db,
                mission_id=work["mission_id"],
                stream_key="qa",
                event_type="candidate.qa_completed",
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

    def accept_candidate(self, work_item_id: str, *, expected_work_version: int) -> dict[str, Any]:
        del work_item_id, expected_work_version
        raise InvalidTransition(
            "candidate acceptance requires AcceptanceLifecycleService; "
            "complete_candidate_qa records QA without self-promotion"
        )
