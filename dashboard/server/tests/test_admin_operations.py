from __future__ import annotations

from dataclasses import replace
import logging
from threading import Barrier, Thread
from typing import Any
import unittest

from software_factory_dashboard.admin_operations import (
    ConfirmationContract,
    DispatchResult,
    OperationCoordinator,
    OperationDefinition,
    OperationError,
    OperationLink,
    OperationOwnerError,
    OperationRegistry,
    OperationTarget,
    PreviewEffect,
    RouteGateRequest,
    RouteGateResult,
    SourceSnapshot,
    VerificationResult,
    fingerprint,
    route_action_fingerprint,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def monotonic(self) -> float:
        return self.value

    def wall(self) -> float:
        return 1_786_320_000.0 + self.value

    def sleep(self, seconds: float) -> None:
        self.value += max(seconds, 0.001)


class SecretStringKey:
    def __str__(self) -> str:
        return "Bearer key-string-secret"


class SecretStringValue:
    def __str__(self) -> str:
        return "Bearer value-string-secret"


class DeterministicOwner:
    def __init__(self) -> None:
        self.value = "initial"
        self.version = 1
        self.dispatches = 0
        self.gates: list[RouteGateRequest] = []
        self.gate_allowed = True
        self.gate_crashes = False
        self.gate_action_hash_override: str | None = None
        self.gate_policy_fingerprint = "b" * 64
        self.gate_recipient_override: str | None = None
        self.source_calls = 0
        self.execute_source_barrier: Barrier | None = None

    def source(self, target: OperationTarget, inputs: dict[str, Any]) -> SourceSnapshot:
        value = self.value
        version = self.version
        self.source_calls += 1
        if self.execute_source_barrier is not None and self.source_calls > 1:
            self.execute_source_barrier.wait(timeout=2)
        return SourceSnapshot(
            fingerprint=fingerprint(
                {"target": target.as_dict(), "value": value, "version": version}
            ),
            evidence={"version": version, "secret_token": "never-render-this"},
        )

    @staticmethod
    def effect(
        target: OperationTarget,
        inputs: dict[str, Any],
        source: SourceSnapshot,
    ) -> PreviewEffect:
        return PreviewEffect(
            summary=f"Set {target.id} to {inputs['value']}",
            risk="Changes only the deterministic in-memory test owner.",
            recipient="test-recipient",
        )

    @staticmethod
    def route_request(
        target: OperationTarget,
        inputs: dict[str, Any],
        source: SourceSnapshot,
    ) -> RouteGateRequest:
        return RouteGateRequest(
            recipient="test-recipient",
            purpose="deterministic-owner-proof",
            source_record=f"TEST-{source.evidence['version']}",
            required_action=f"Set {target.id} to {inputs['value']}",
        )

    def gate(self, request: RouteGateRequest) -> RouteGateResult:
        if self.gate_crashes:
            raise RuntimeError("gate unavailable")
        self.gates.append(request)
        return RouteGateResult(
            allowed=self.gate_allowed,
            action_hash=(
                self.gate_action_hash_override or route_action_fingerprint(request.required_action)
                if self.gate_allowed
                else None
            ),
            recipient=(
                self.gate_recipient_override or request.recipient if self.gate_allowed else None
            ),
            purpose=request.purpose if self.gate_allowed else None,
            source_record=request.source_record if self.gate_allowed else None,
            policy_fingerprint=(self.gate_policy_fingerprint if self.gate_allowed else None),
            reason=None if self.gate_allowed else "Test route denied.",
        )

    def dispatch(
        self,
        target: OperationTarget,
        inputs: dict[str, Any],
        source: SourceSnapshot,
    ) -> DispatchResult:
        self.dispatches += 1
        mode = inputs["mode"]
        if mode == "failed":
            raise OperationOwnerError(
                "test_owner_failed",
                "Bearer owner-secret must never leave the owner boundary.",
            )
        if mode == "owner-crash":
            raise RuntimeError("Bearer log-secret must never be logged")
        if mode == "awaiting-approval":
            return DispatchResult(
                state="awaiting-approval",
                evidence={"request_id": "request-approval"},
            )
        if mode == "awaiting-input":
            return DispatchResult(
                state="awaiting-input",
                evidence={"request_id": "request-input"},
            )
        self.value = inputs["value"]
        self.version += 1
        if mode == "invalid-link":
            return DispatchResult(
                evidence={"request_id": f"request-{self.dispatches}"},
                links=(OperationLink("Unsafe", "https://example.invalid/result"),),
            )
        if mode == "secret-link":
            return DispatchResult(
                evidence={"request_id": f"request-{self.dispatches}"},
                links=(OperationLink("Unsafe", "/admin?token=link-secret#result"),),
            )
        evidence: dict[Any, Any] = {
            "request_id": f"request-{self.dispatches}",
            "access_token": "hidden",
        }
        if mode == "secret-evidence":
            evidence.update(
                {
                    "api_key": "api-secret",
                    "authorization": "Bearer authorization-secret",
                    "credential": "credential-secret",
                    "cookie": "session=secret-cookie",
                    "private_key": "private-secret",
                    "innocent_label": "Bearer value-secret",
                    SecretStringKey(): "safe-key-value",
                    "unsupported_value": SecretStringValue(),
                }
            )
        return DispatchResult(
            evidence=evidence,
            links=(OperationLink("Canonical test source", "/admin"),),
        )

    def verify(
        self,
        target: OperationTarget,
        inputs: dict[str, Any],
        source: SourceSnapshot,
        dispatch: DispatchResult,
    ) -> VerificationResult:
        if inputs["mode"] == "unverified":
            return VerificationResult(
                state="pending",
                evidence={"current_value": self.value},
            )
        if inputs["mode"] == "verification-crash":
            raise RuntimeError("unexpected verification crash")
        if inputs["mode"] == "postcondition-failed":
            return VerificationResult(
                state="failed",
                evidence={"current_value": self.value},
            )
        return VerificationResult(
            state="applied",
            evidence={"current_value": self.value, "version": self.version},
            links=(OperationLink("Verified test source", "/admin"),),
        )


def test_definition(owner: DeterministicOwner, *, timeout: float = 0.1) -> OperationDefinition:
    return OperationDefinition(
        operation_type="test.fixture-set",
        target_kind="test-fixture",
        input_schema={
            "type": "object",
            "properties": {
                "mode": {
                    "enum": [
                        "success",
                        "failed",
                        "owner-crash",
                        "unverified",
                        "verification-crash",
                        "invalid-link",
                        "secret-link",
                        "secret-evidence",
                        "postcondition-failed",
                        "awaiting-approval",
                        "awaiting-input",
                    ]
                },
                "value": {"type": "string", "minLength": 1, "maxLength": 40},
            },
            "required": ["mode", "value"],
            "additionalProperties": False,
        },
        owner="tests/deterministic-owner",
        authority=("Block 10 deterministic test owner",),
        ordinary_consequences=("Changes one in-memory fixture value.",),
        failure_consequences=("The fixture may change before verification completes.",),
        confirmation=ConfirmationContract(
            kind="typed-phrase",
            prompt="Type APPLY TEST FIXTURE",
            expected_value="APPLY TEST FIXTURE",
        ),
        idempotency="One owner request per preview token; never retried automatically.",
        expected_postcondition="The deterministic owner reports the exact requested value.",
        timeout_seconds=timeout,
        limitations=("Test-only owner; no production domain operation is registered.",),
        resolve_source=owner.source,
        describe_effect=owner.effect,
        route_gate_request=owner.route_request,
        route_gate=owner.gate,
        dispatch=owner.dispatch,
        verify=owner.verify,
    )


def preview_payload(mode: str = "success", value: str = "next") -> dict[str, Any]:
    return {
        "operation_type": "test.fixture-set",
        "target": {"kind": "test-fixture", "id": "fixture-1", "project_id": "test"},
        "input": {"mode": mode, "value": value},
    }


def execute_payload(preview: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return {
        **request,
        "preview_token": preview["preview_token"],
        "confirmation": {"class": "typed-phrase", "value": "APPLY TEST FIXTURE"},
    }


class AdministrativeOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.owner = DeterministicOwner()
        self.registry = OperationRegistry((test_definition(self.owner),))
        self.coordinator = OperationCoordinator(
            self.registry,
            preview_ttl_seconds=2,
            monotonic_clock=self.clock.monotonic,
            wall_clock=self.clock.wall,
            sleeper=self.clock.sleep,
        )

    def test_preview_route_gate_execute_and_verify_without_exposing_inputs(self) -> None:
        request = preview_payload()
        preview = self.coordinator.preview(request)
        operation = preview["operation"]

        self.assertEqual(self.owner.value, "initial")
        self.assertEqual(operation["state"], "previewed")
        self.assertEqual(operation["preview"]["route_gate"]["status"], "allowed")
        self.assertRegex(operation["preview"]["route_gate"]["action_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(operation["preview"]["source_evidence"]["secret_token"], "[redacted]")
        self.assertNotIn("input", operation)
        self.assertEqual(len(self.owner.gates), 1)

        executed = self.coordinator.execute(execute_payload(preview, request))["operation"]

        self.assertEqual(executed["state"], "applied")
        self.assertEqual(
            [entry["state"] for entry in executed["history"]],
            ["previewed", "confirmed", "requested", "verifying", "applied"],
        )
        self.assertEqual(executed["request_evidence"]["access_token"], "[redacted]")
        self.assertEqual(executed["verification_evidence"]["current_value"], "next")
        self.assertEqual(len(executed["links"]), 2)
        self.assertEqual(len(self.owner.gates), 2)
        self.assertEqual(self.owner.dispatches, 1)
        with self.assertRaisesRegex(OperationError, "already crossed") as raised:
            self.coordinator.execute(execute_payload(preview, request))
        self.assertEqual(raised.exception.code, "preview_token_replayed")
        self.assertEqual(self.owner.dispatches, 1)

    def test_changed_target_input_confirmation_and_extra_fields_fail_closed(self) -> None:
        request = preview_payload()
        preview = self.coordinator.preview(request)
        changed = execute_payload(preview, request)
        changed["input"] = {"mode": "success", "value": "different"}
        with self.assertRaises(OperationError) as raised:
            self.coordinator.execute(changed)
        self.assertEqual(raised.exception.code, "preview_request_changed")

        wrong_confirmation = execute_payload(preview, request)
        wrong_confirmation["confirmation"] = {"class": "typed-phrase", "value": "yes"}
        with self.assertRaises(OperationError) as raised:
            self.coordinator.execute(wrong_confirmation)
        self.assertEqual(raised.exception.code, "confirmation_mismatch")

        with self.assertRaises(OperationError) as raised:
            self.coordinator.preview({**request, "command": "rm -rf"})
        self.assertEqual(raised.exception.code, "invalid_operation_preview")
        with self.assertRaises(OperationError) as raised:
            self.coordinator.preview(
                {**request, "input": {**request["input"], "path": "/tmp/escape"}}
            )
        self.assertEqual(raised.exception.code, "invalid_operation_input")
        self.assertEqual(self.owner.dispatches, 0)

    def test_duplicate_submit_race_dispatches_the_owner_exactly_once(self) -> None:
        request = preview_payload()
        preview = self.coordinator.preview(request)
        payload = execute_payload(preview, request)
        self.owner.execute_source_barrier = Barrier(2)
        results: list[str] = []

        def execute() -> None:
            try:
                results.append(self.coordinator.execute(payload)["operation"]["state"])
            except OperationError as error:
                results.append(error.code)

        workers = [Thread(target=execute), Thread(target=execute)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=3)

        self.assertFalse(any(worker.is_alive() for worker in workers))
        self.assertCountEqual(results, ["applied", "preview_token_replayed"])
        self.assertEqual(self.owner.dispatches, 1)

    def test_expired_or_stale_preview_never_dispatches(self) -> None:
        request = preview_payload()
        expired = self.coordinator.preview(request)
        self.clock.value += 3
        with self.assertRaises(OperationError) as raised:
            self.coordinator.execute(execute_payload(expired, request))
        self.assertEqual(raised.exception.code, "preview_expired")

        fresh = self.coordinator.preview(request)
        self.owner.version += 1
        with self.assertRaises(OperationError) as raised:
            self.coordinator.execute(execute_payload(fresh, request))
        self.assertEqual(raised.exception.code, "preview_stale")
        self.assertEqual(self.owner.dispatches, 0)

    def test_route_gate_deny_or_failure_prevents_preview_token(self) -> None:
        self.owner.gate_allowed = False
        with self.assertRaises(OperationError) as denied:
            self.coordinator.preview(preview_payload())
        self.assertEqual(denied.exception.code, "route_gate_denied")

        self.owner.gate_allowed = True
        self.owner.gate_crashes = True
        with self.assertRaises(OperationError) as unavailable:
            self.coordinator.preview(preview_payload())
        self.assertEqual(unavailable.exception.code, "route_gate_unavailable")
        self.assertEqual(self.coordinator.framework()["activity"], [])

    def test_route_gate_must_bind_the_exact_action_and_request_identity(self) -> None:
        self.owner.gate_action_hash_override = "0" * 64
        with self.assertRaises(OperationError) as wrong_action:
            self.coordinator.preview(preview_payload())
        self.assertEqual(wrong_action.exception.code, "route_gate_result_invalid")

        self.owner.gate_action_hash_override = None
        self.owner.gate_recipient_override = "unrelated-recipient"
        with self.assertRaises(OperationError) as wrong_identity:
            self.coordinator.preview(preview_payload())
        self.assertEqual(wrong_identity.exception.code, "route_gate_result_invalid")
        self.assertEqual(self.owner.dispatches, 0)
        self.assertEqual(self.coordinator.framework()["activity"], [])

    def test_route_gate_is_rechecked_immediately_before_dispatch(self) -> None:
        request = preview_payload()
        denied_preview = self.coordinator.preview(request)
        self.owner.gate_allowed = False
        with self.assertRaises(OperationError) as denied:
            self.coordinator.execute(execute_payload(denied_preview, request))
        self.assertEqual(denied.exception.code, "route_gate_denied")
        self.assertEqual(self.owner.dispatches, 0)
        self.assertEqual(
            self.coordinator.get(denied_preview["operation"]["id"])["operation"]["state"],
            "cancelled",
        )

        self.owner.gate_allowed = True
        policy_preview = self.coordinator.preview(request)
        self.owner.gate_policy_fingerprint = "c" * 64
        with self.assertRaises(OperationError) as stale:
            self.coordinator.execute(execute_payload(policy_preview, request))
        self.assertEqual(stale.exception.code, "route_gate_stale")
        self.assertEqual(self.owner.dispatches, 0)

    def test_cross_thread_recipient_cannot_bypass_or_disagree_with_route_gate(self) -> None:
        definition = test_definition(self.owner)
        missing_gate = replace(definition, route_gate_request=None, route_gate=None)
        with self.assertRaises(OperationError) as required:
            OperationCoordinator(OperationRegistry((missing_gate,))).preview(preview_payload())
        self.assertEqual(required.exception.code, "route_gate_required")

        mismatch = replace(
            definition,
            route_gate_request=lambda target, inputs, source: RouteGateRequest(
                recipient="different-recipient",
                purpose="deterministic-owner-proof",
                source_record="TEST-1",
                required_action="Exact action",
            ),
        )
        with self.assertRaises(OperationError) as disagreed:
            OperationCoordinator(OperationRegistry((mismatch,))).preview(preview_payload())
        self.assertEqual(disagreed.exception.code, "route_gate_recipient_mismatch")

    def test_public_evidence_failures_links_and_logs_are_secret_safe(self) -> None:
        evidence_request = preview_payload("secret-evidence", "redacted")
        evidence_preview = self.coordinator.preview(evidence_request)
        evidence = self.coordinator.execute(execute_payload(evidence_preview, evidence_request))[
            "operation"
        ]["request_evidence"]
        for key in ("api_key", "authorization", "credential", "cookie", "private_key"):
            self.assertEqual(evidence[key], "[redacted]")
        self.assertEqual(evidence["innocent_label"], "[redacted]")
        self.assertEqual(evidence["[unsupported-key-0]"], "[unsupported]")
        self.assertEqual(evidence["unsupported_value"], "[unsupported]")
        self.assertNotIn("key-string-secret", str(evidence))
        self.assertNotIn("value-string-secret", str(evidence))

        failure_request = preview_payload("failed", "failed")
        failure_preview = self.coordinator.preview(failure_request)
        failure = self.coordinator.execute(execute_payload(failure_preview, failure_request))[
            "operation"
        ]["failure"]
        self.assertEqual(failure["message"], "The registered owner reported a failure.")
        self.assertNotIn("owner-secret", str(failure))

        link_request = preview_payload("secret-link", "link")
        link_preview = self.coordinator.preview(link_request)
        link_result = self.coordinator.execute(execute_payload(link_preview, link_request))[
            "operation"
        ]
        self.assertEqual(link_result["failure"]["code"], "invalid_owner_link")
        self.assertEqual(link_result["links"], [])
        self.assertNotIn("link-secret", str(link_result))

        unsafe_links = (
            OperationLink("Source", "/%2e%2e/admin"),
            OperationLink("Source", "/%2E%2E/admin"),
            OperationLink("Source", "/safe%2f..%2fadmin"),
            OperationLink("Source", "/safe\\..\\admin"),
            OperationLink("Authorization: Bearer label-secret", "/admin"),
        )
        for unsafe_link in unsafe_links:
            with self.subTest(href=unsafe_link.href, label=unsafe_link.label):
                with self.assertRaises(OperationOwnerError) as rejected:
                    OperationCoordinator._validated_links((unsafe_link,))
                self.assertEqual(rejected.exception.code, "invalid_owner_link")
        self.assertEqual(
            OperationCoordinator._validated_links(
                (OperationLink("Canonical source", "/projects/project-1/trackers/abc:def"),)
            ),
            (OperationLink("Canonical source", "/projects/project-1/trackers/abc:def"),),
        )

        crash_request = preview_payload("owner-crash", "crash")
        crash_preview = self.coordinator.preview(crash_request)
        with self.assertLogs(
            "software_factory_dashboard.admin_operations",
            level=logging.ERROR,
        ) as captured:
            crashed = self.coordinator.execute(execute_payload(crash_preview, crash_request))[
                "operation"
            ]
        logs = "\n".join(captured.output)
        self.assertEqual(crashed["failure"]["code"], "owner_failed")
        self.assertIn("exception_type=RuntimeError", logs)
        self.assertNotIn("log-secret", logs)
        self.assertNotIn("Traceback", logs)

    def test_failure_unverified_and_follow_up_states_are_truthful(self) -> None:
        failed_request = preview_payload("failed")
        failed_preview = self.coordinator.preview(failed_request)
        failed = self.coordinator.execute(execute_payload(failed_preview, failed_request))[
            "operation"
        ]
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(failed["failure"]["code"], "test_owner_failed")

        unverified_request = preview_payload("unverified", "changed-but-unverified")
        unverified_preview = self.coordinator.preview(unverified_request)
        unverified = self.coordinator.execute(
            execute_payload(unverified_preview, unverified_request)
        )["operation"]
        self.assertEqual(unverified["state"], "unverified")
        self.assertEqual(unverified["failure"]["code"], "postcondition_timeout")
        self.assertEqual(self.owner.value, "changed-but-unverified")

        for mode, code in (
            ("owner-crash", "owner_failed"),
            ("verification-crash", "postcondition_unavailable"),
            ("invalid-link", "invalid_owner_link"),
        ):
            request = preview_payload(mode, mode)
            preview = self.coordinator.preview(request)
            result = self.coordinator.execute(execute_payload(preview, request))["operation"]
            self.assertIn(result["state"], {"failed", "unverified"})
            self.assertEqual(result["failure"]["code"], code)

        for mode, state in (
            ("awaiting-approval", "awaiting-approval"),
            ("awaiting-input", "awaiting-input"),
        ):
            request = preview_payload(mode, mode)
            preview = self.coordinator.preview(request)
            result = self.coordinator.execute(execute_payload(preview, request))["operation"]
            self.assertEqual(result["state"], state)
            self.assertNotIn("applied", [entry["state"] for entry in result["history"]])

    def test_cancel_only_before_request_and_restart_has_no_parallel_ledger(self) -> None:
        request = preview_payload()
        preview = self.coordinator.preview(request)
        operation_id = preview["operation"]["id"]
        cancelled = self.coordinator.cancel(
            operation_id, {"confirmation": "cancel-before-request"}
        )["operation"]
        self.assertEqual(cancelled["state"], "cancelled")
        self.assertEqual(self.owner.dispatches, 0)

        applied_preview = self.coordinator.preview(request)
        applied = self.coordinator.execute(execute_payload(applied_preview, request))["operation"]
        with self.assertRaises(OperationError) as crossed:
            self.coordinator.cancel(
                applied["id"], {"confirmation": "cancel-before-request"}
            )
        self.assertEqual(crossed.exception.code, "cancel_boundary_crossed")

        restarted = OperationCoordinator(self.registry)
        with self.assertRaises(OperationError) as missing:
            restarted.get(applied["id"])
        self.assertEqual(missing.exception.code, "operation_not_found")
        with self.assertRaises(OperationError) as token_missing:
            restarted.execute(execute_payload(applied_preview, request))
        self.assertEqual(token_missing.exception.code, "invalid_preview_token")


if __name__ == "__main__":
    unittest.main()
