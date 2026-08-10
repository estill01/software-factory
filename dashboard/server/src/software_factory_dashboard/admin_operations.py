from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
import json
import logging
import re
import secrets
from threading import RLock
from time import monotonic, sleep
from typing import Any, Callable, Mapping

from jsonschema import Draft202012Validator


LOGGER = logging.getLogger(__name__)

OPERATION_STATES = {
    "previewed",
    "confirmed",
    "requested",
    "awaiting-approval",
    "awaiting-input",
    "verifying",
    "applied",
    "failed",
    "unverified",
    "cancelled",
}
TERMINAL_STATES = {"applied", "failed", "unverified", "cancelled"}
OPERATION_TYPE_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*\Z")
IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
INTERNAL_LINK_PATTERN = re.compile(
    r"/(?:[A-Za-z0-9._~:@-]+(?:/[A-Za-z0-9._~:@-]+)*)?\Z"
)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|authorization|body|content|cookie|credential|password|"
    r"private[_-]?key|prompt|secret|session|token)",
    re.I,
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?:\bBearer\s+\S+|(?:api[_-]?key|authorization|cookie|credential|password|"
    r"private[_-]?key|secret|token)\s*[:=]\s*\S+)",
    re.I,
)
MAX_ACTIVITY_RECORDS = 200


class OperationError(RuntimeError):
    """A bounded operation-framework rejection safe to return to the client."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable


class OperationOwnerError(RuntimeError):
    """An owner-reported failure after the operation request boundary."""

    def __init__(self, code: str, message: str, *, state: str = "failed") -> None:
        if state not in {"failed", "unverified"}:
            raise ValueError("Owner errors may end only as failed or unverified")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", code):
            raise ValueError("Owner error code is invalid")
        super().__init__(message)
        self.code = code
        self.state = state


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def fingerprint(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def route_action_fingerprint(action: str) -> str:
    """Match the maintained thread-route-gate action_sha256 contract."""

    return sha256(
        json.dumps(
            action,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _timestamp(value: float | None = None) -> str:
    observed = datetime.fromtimestamp(value, UTC) if value is not None else datetime.now(UTC)
    return observed.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _redact(value: Any, *, key: str = "") -> Any:
    if SENSITIVE_KEY_PATTERN.search(key):
        return "[redacted]"
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        string_keys = {item_key for item_key in value if isinstance(item_key, str)}
        unsupported_key_index = 0
        for item_key, item_value in value.items():
            if isinstance(item_key, str):
                public_key = item_key
                redacted[public_key] = _redact(item_value, key=public_key)
            else:
                while True:
                    public_key = f"[unsupported-key-{unsupported_key_index}]"
                    unsupported_key_index += 1
                    if public_key not in redacted and public_key not in string_keys:
                        break
                redacted[public_key] = "[unsupported]"
        return redacted
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value[:100]]
    if isinstance(value, str):
        if SENSITIVE_VALUE_PATTERN.search(value):
            return "[redacted]"
        return value if len(value) <= 500 else f"{value[:497]}..."
    if value is None or isinstance(value, bool | int | float):
        return value
    return "[unsupported]"


def _owner_failure_message(state: str) -> str:
    if state == "unverified":
        return "The registered owner reported that its canonical postcondition is unverified."
    return "The registered owner reported a failure."


@dataclass(frozen=True)
class OperationTarget:
    kind: str
    id: str
    project_id: str | None

    @classmethod
    def parse(cls, value: Any) -> "OperationTarget":
        if not isinstance(value, dict) or set(value) != {"kind", "id", "project_id"}:
            raise OperationError(
                "invalid_operation_target",
                "Operation target requires exactly kind, id, and project_id.",
            )
        kind = value["kind"]
        target_id = value["id"]
        project_id = value["project_id"]
        if not isinstance(kind, str) or not IDENTITY_PATTERN.fullmatch(kind):
            raise OperationError("invalid_operation_target", "Target kind is invalid.")
        if not isinstance(target_id, str) or not IDENTITY_PATTERN.fullmatch(target_id):
            raise OperationError("invalid_operation_target", "Target ID is invalid.")
        if project_id is not None and (
            not isinstance(project_id, str) or not IDENTITY_PATTERN.fullmatch(project_id)
        ):
            raise OperationError("invalid_operation_target", "Target project ID is invalid.")
        return cls(kind=kind, id=target_id, project_id=project_id)

    def as_dict(self) -> dict[str, str | None]:
        return {"kind": self.kind, "id": self.id, "project_id": self.project_id}


@dataclass(frozen=True)
class SourceSnapshot:
    fingerprint: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not SHA256_PATTERN.fullmatch(self.fingerprint):
            raise ValueError("Source fingerprint must be a lowercase SHA-256")


@dataclass(frozen=True)
class RouteGateRequest:
    recipient: str
    purpose: str
    source_record: str
    required_action: str
    target_thread: str | None = None

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value.strip() and len(value) <= 240
            for value in (
                self.recipient,
                self.purpose,
                self.source_record,
                self.required_action,
            )
        ):
            raise ValueError("Route-gate fields must be nonempty and bounded")
        if self.target_thread is not None and (
            not isinstance(self.target_thread, str)
            or not self.target_thread.strip()
            or len(self.target_thread) > 240
        ):
            raise ValueError("Route-gate target must be nonempty and bounded")


@dataclass(frozen=True)
class RouteGateResult:
    allowed: bool
    action_hash: str | None
    recipient: str | None = None
    purpose: str | None = None
    source_record: str | None = None
    policy_fingerprint: str | None = None
    reason: str | None = None
    target_thread: str | None = None

    def __post_init__(self) -> None:
        if self.allowed:
            if not (
                isinstance(self.action_hash, str)
                and SHA256_PATTERN.fullmatch(self.action_hash)
                and isinstance(self.policy_fingerprint, str)
                and SHA256_PATTERN.fullmatch(self.policy_fingerprint)
            ):
                raise ValueError("Allowed route gates require exact action and policy fingerprints")
            if not all(
                isinstance(value, str) and value.strip()
                for value in (self.recipient, self.purpose, self.source_record)
            ):
                raise ValueError("Allowed route gates must echo their exact request identity")
            if self.target_thread is not None and (
                not isinstance(self.target_thread, str) or not self.target_thread.strip()
            ):
                raise ValueError("Allowed route-gate target is invalid")


@dataclass(frozen=True)
class PreviewEffect:
    summary: str
    risk: str
    recipient: str | None = None

    def __post_init__(self) -> None:
        if not self.summary.strip() or not self.risk.strip():
            raise ValueError("Preview effect and risk are required")
        if len(self.summary) > 500 or len(self.risk) > 1_000:
            raise ValueError("Preview effect and risk must be bounded")
        if self.recipient is not None and not self.recipient.strip():
            raise ValueError("Preview recipient cannot be empty")


@dataclass(frozen=True)
class ConfirmationContract:
    kind: str
    prompt: str
    expected_value: str

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.prompt.strip() or not self.expected_value:
            raise ValueError("Confirmation contract is incomplete")
        if max(len(self.kind), len(self.prompt), len(self.expected_value)) > 200:
            raise ValueError("Confirmation contract must be bounded")


@dataclass(frozen=True)
class OperationLink:
    label: str
    href: str

    def __post_init__(self) -> None:
        if len(self.label) > 120 or len(self.href) > 2_000:
            raise ValueError("Operation links must be bounded")


@dataclass(frozen=True)
class DispatchResult:
    state: str = "requested"
    evidence: Mapping[str, Any] = field(default_factory=dict)
    links: tuple[OperationLink, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in {"requested", "awaiting-approval", "awaiting-input"}:
            raise ValueError("Dispatch state is invalid")


@dataclass(frozen=True)
class VerificationResult:
    state: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    links: tuple[OperationLink, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in {"applied", "pending", "failed", "unverified"}:
            raise ValueError("Verification state is invalid")


SourceResolver = Callable[[OperationTarget, Mapping[str, Any]], SourceSnapshot]
EffectResolver = Callable[[OperationTarget, Mapping[str, Any], SourceSnapshot], PreviewEffect]
RouteRequestResolver = Callable[
    [OperationTarget, Mapping[str, Any], SourceSnapshot], RouteGateRequest | None
]
RouteGate = Callable[[RouteGateRequest], RouteGateResult]
OwnerDispatcher = Callable[
    [OperationTarget, Mapping[str, Any], SourceSnapshot], DispatchResult
]
PostconditionVerifier = Callable[
    [OperationTarget, Mapping[str, Any], SourceSnapshot, DispatchResult], VerificationResult
]


@dataclass(frozen=True)
class OperationDefinition:
    operation_type: str
    target_kind: str
    input_schema: Mapping[str, Any]
    owner: str
    authority: tuple[str, ...]
    ordinary_consequences: tuple[str, ...]
    failure_consequences: tuple[str, ...]
    confirmation: ConfirmationContract
    idempotency: str
    expected_postcondition: str
    timeout_seconds: float
    limitations: tuple[str, ...]
    resolve_source: SourceResolver
    describe_effect: EffectResolver
    dispatch: OwnerDispatcher
    verify: PostconditionVerifier
    route_gate_request: RouteRequestResolver | None = None
    route_gate: RouteGate | None = None
    supported: bool = True
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if not OPERATION_TYPE_PATTERN.fullmatch(self.operation_type):
            raise ValueError("Operation type is invalid")
        if not IDENTITY_PATTERN.fullmatch(self.target_kind):
            raise ValueError("Target kind is invalid")
        if not self.owner.strip() or not self.authority:
            raise ValueError("Operation owner and authority are required")
        if self.input_schema.get("type") != "object" or self.input_schema.get(
            "additionalProperties"
        ) is not False:
            raise ValueError("Operation input schema must be a closed object")
        Draft202012Validator.check_schema(dict(self.input_schema))
        if self.timeout_seconds < 0:
            raise ValueError("Operation timeout cannot be negative")
        if self.route_gate_request is not None and self.route_gate is None:
            raise ValueError("Cross-thread operation requires a route-gate owner")
        if not self.supported and not self.unavailable_reason:
            raise ValueError("Unavailable operations require a reason")

    def descriptor(self) -> dict[str, Any]:
        return {
            "type": self.operation_type,
            "target_kind": self.target_kind,
            "input_schema": dict(self.input_schema),
            "owner": self.owner,
            "authority": list(self.authority),
            "consequences": {
                "ordinary": list(self.ordinary_consequences),
                "failure": list(self.failure_consequences),
            },
            "confirmation_class": self.confirmation.kind,
            "idempotency": self.idempotency,
            "expected_postcondition": self.expected_postcondition,
            "timeout_seconds": self.timeout_seconds,
            "limitations": list(self.limitations),
            "status": "supported" if self.supported else "unavailable",
            "reason": self.unavailable_reason,
        }


class OperationRegistry:
    """Closed operation definitions; definitions dispatch only to their named owner."""

    def __init__(self, definitions: tuple[OperationDefinition, ...] = ()) -> None:
        self._definitions: dict[str, OperationDefinition] = {}
        for definition in definitions:
            if definition.operation_type in self._definitions:
                raise ValueError(f"Duplicate operation type: {definition.operation_type}")
            self._definitions[definition.operation_type] = definition

    def get(self, operation_type: str) -> OperationDefinition:
        definition = self._definitions.get(operation_type)
        if definition is None:
            raise OperationError(
                "unknown_operation",
                "Operation type is not registered.",
                status=404,
            )
        if not definition.supported:
            raise OperationError(
                "operation_unavailable",
                definition.unavailable_reason or "Operation is unavailable.",
                status=409,
            )
        return definition

    def descriptors(self) -> list[dict[str, Any]]:
        return [
            definition.descriptor()
            for definition in sorted(
                self._definitions.values(), key=lambda item: item.operation_type
            )
        ]


@dataclass
class _OperationRecord:
    operation_id: str
    definition: OperationDefinition
    target: OperationTarget
    inputs: dict[str, Any]
    request_fingerprint: str
    source: SourceSnapshot
    effect: PreviewEffect
    route_request: RouteGateRequest | None
    route_result: RouteGateResult | None
    preview_token: str
    expires_monotonic: float
    expires_at: str
    state: str
    history: list[dict[str, Any]]
    consumed: bool = False
    request_evidence: Mapping[str, Any] | None = None
    verification_evidence: Mapping[str, Any] | None = None
    links: tuple[OperationLink, ...] = ()
    failure: dict[str, Any] | None = None


class OperationCoordinator:
    """Ephemeral preview, dispatch, and canonical-postcondition coordinator."""

    def __init__(
        self,
        registry: OperationRegistry | None = None,
        *,
        preview_ttl_seconds: float = 120.0,
        monotonic_clock: Callable[[], float] = monotonic,
        wall_clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if preview_ttl_seconds <= 0:
            raise ValueError("Preview TTL must be positive")
        self.registry = registry or OperationRegistry()
        self.preview_ttl_seconds = preview_ttl_seconds
        self._monotonic = monotonic_clock
        self._wall = wall_clock or (lambda: datetime.now(UTC).timestamp())
        self._sleep = sleeper
        self._lock = RLock()
        self._records: dict[str, _OperationRecord] = {}
        self._token_index: dict[str, str] = {}

    def framework(self) -> dict[str, Any]:
        with self._lock:
            activity = [self._public(record) for record in reversed(self._records.values())]
        return {
            "ephemeral": True,
            "registered_operations": self.registry.descriptors(),
            "activity": activity,
            "restart_posture": (
                "Operation correlation is process-local. After restart, prior operation state "
                "must be reconstructed from its canonical owner or shown as unavailable."
            ),
        }

    def preview(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if set(payload) != {"operation_type", "target", "input"}:
            raise OperationError(
                "invalid_operation_preview",
                "Preview requires exactly operation_type, target, and input.",
            )
        operation_type = payload["operation_type"]
        if not isinstance(operation_type, str):
            raise OperationError("unknown_operation", "Operation type is not registered.", status=404)
        definition = self.registry.get(operation_type)
        target = OperationTarget.parse(payload["target"])
        if target.kind != definition.target_kind:
            raise OperationError(
                "operation_target_mismatch",
                "Operation target kind does not match its registry definition.",
                status=409,
            )
        inputs = payload["input"]
        if not isinstance(inputs, dict):
            raise OperationError("invalid_operation_input", "Operation input must be an object.")
        validation_errors = sorted(
            Draft202012Validator(definition.input_schema).iter_errors(inputs),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if validation_errors:
            field = ".".join(str(part) for part in validation_errors[0].absolute_path)
            location = f" at {field}" if field else ""
            raise OperationError(
                "invalid_operation_input",
                f"Operation input did not match its closed schema{location}.",
            )

        try:
            source = definition.resolve_source(target, inputs)
            effect = definition.describe_effect(target, inputs, source)
            route_request = (
                definition.route_gate_request(target, inputs, source)
                if definition.route_gate_request is not None
                else None
            )
        except OperationError:
            raise
        except Exception as error:
            LOGGER.warning("preview owner unavailable for operation type=%s", operation_type)
            raise OperationError(
                "operation_preview_unavailable",
                "The registered owner could not resolve a current bounded preview.",
                status=503,
                retryable=True,
            ) from error
        if effect.recipient is not None and route_request is None:
            raise OperationError(
                "route_gate_required",
                "An operation with a cross-thread recipient requires a registered route gate.",
                status=503,
            )
        if route_request is not None and effect.recipient != route_request.recipient:
            raise OperationError(
                "route_gate_recipient_mismatch",
                "Preview recipient did not match the exact route-gate recipient.",
                status=503,
            )
        route_result: RouteGateResult | None = None
        if route_request is not None:
            try:
                route_result = (
                    definition.route_gate(route_request) if definition.route_gate else None
                )
            except Exception as error:  # owner boundary; body is intentionally not logged
                LOGGER.warning("route gate unavailable for operation type=%s", operation_type)
                raise OperationError(
                    "route_gate_unavailable",
                    "The required cross-thread route gate is unavailable.",
                    status=503,
                    retryable=True,
                ) from error
            if route_result is None:
                raise OperationError(
                    "route_gate_unavailable",
                    "The required cross-thread route gate returned no result.",
                    status=503,
                    retryable=True,
                )
            if not isinstance(route_result, RouteGateResult):
                raise OperationError(
                    "route_gate_result_invalid",
                    "Route gate returned an invalid result contract.",
                    status=503,
                )
            if not route_result.allowed:
                raise OperationError(
                    "route_gate_denied",
                    "Route gate denied the exact action.",
                    status=409,
                )
            self._validate_route_result(route_request, route_result)

        now_monotonic = self._monotonic()
        expires_monotonic = now_monotonic + self.preview_ttl_seconds
        expires_at = _timestamp(self._wall() + self.preview_ttl_seconds)
        operation_id = f"op_{secrets.token_urlsafe(12)}"
        preview_token = secrets.token_urlsafe(32)
        request_material = {
            "operation_type": operation_type,
            "target": target.as_dict(),
            "input": inputs,
        }
        history = [{"state": "previewed", "observed_at": _timestamp(self._wall())}]
        record = _OperationRecord(
            operation_id=operation_id,
            definition=definition,
            target=target,
            inputs=dict(inputs),
            request_fingerprint=fingerprint(request_material),
            source=source,
            effect=effect,
            route_request=route_request,
            route_result=route_result,
            preview_token=preview_token,
            expires_monotonic=expires_monotonic,
            expires_at=expires_at,
            state="previewed",
            history=history,
        )
        with self._lock:
            self._make_capacity()
            self._records[operation_id] = record
            self._token_index[preview_token] = operation_id
        LOGGER.info("operation previewed type=%s id=%s", operation_type, operation_id)
        return {"operation": self._public(record), "preview_token": preview_token}

    def execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if set(payload) != {
            "operation_type",
            "target",
            "input",
            "preview_token",
            "confirmation",
        }:
            raise OperationError(
                "invalid_operation_execute",
                "Execute requires exactly operation_type, target, input, preview_token, and confirmation.",
            )
        preview_token = payload["preview_token"]
        if not isinstance(preview_token, str):
            raise OperationError("invalid_preview_token", "Preview token is invalid.")
        with self._lock:
            operation_id = self._token_index.get(preview_token)
            record = self._records.get(operation_id) if operation_id else None
            if record is None or not secrets.compare_digest(record.preview_token, preview_token):
                raise OperationError(
                    "invalid_preview_token",
                    "Preview token is invalid or unavailable after restart.",
                    status=404,
                )
            if record.consumed or record.state not in {"previewed", "confirmed"}:
                raise OperationError(
                    "preview_token_replayed",
                    "Preview token has already crossed its request boundary.",
                    status=409,
                )
            if self._monotonic() > record.expires_monotonic:
                self._transition(record, "cancelled")
                record.failure = {
                    "code": "preview_expired",
                    "message": "Preview expired before execution.",
                }
                raise OperationError(
                    "preview_expired",
                    "Preview expired; resolve current sources and preview again.",
                    status=409,
                )

            request_material = {
                "operation_type": payload["operation_type"],
                "target": payload["target"],
                "input": payload["input"],
            }
            if not secrets.compare_digest(record.request_fingerprint, fingerprint(request_material)):
                raise OperationError(
                    "preview_request_changed",
                    "Operation type, target, project, recipient-bearing input, or other input changed after preview.",
                    status=409,
                )
            confirmation = payload["confirmation"]
            expected_confirmation = {
                "class": record.definition.confirmation.kind,
                "value": record.definition.confirmation.expected_value,
            }
            if not isinstance(confirmation, dict) or confirmation != expected_confirmation:
                raise OperationError(
                    "confirmation_mismatch",
                    "Execution requires the exact typed confirmation from the preview.",
                    status=409,
                )
            self._transition(record, "confirmed")

        try:
            current_source = record.definition.resolve_source(record.target, record.inputs)
        except OperationError:
            raise
        except Exception as error:
            LOGGER.warning(
                "execution source unavailable type=%s id=%s",
                record.definition.operation_type,
                record.operation_id,
            )
            raise OperationError(
                "operation_source_unavailable",
                "Authoritative source currentness is unavailable; execution did not reach the owner.",
                status=503,
                retryable=True,
            ) from error
        if not secrets.compare_digest(current_source.fingerprint, record.source.fingerprint):
            with self._lock:
                self._transition(record, "cancelled")
                record.failure = {
                    "code": "preview_stale",
                    "message": "Authoritative source changed after preview.",
                }
            raise OperationError(
                "preview_stale",
                "Authoritative source changed; preview the operation again.",
                status=409,
            )

        self._recheck_route_gate(record, current_source)

        with self._lock:
            if record.state == "cancelled":
                raise OperationError(
                    "operation_cancelled",
                    "Operation was cancelled before the owner request.",
                    status=409,
                )
            if record.consumed or record.state != "confirmed":
                raise OperationError(
                    "preview_token_replayed",
                    "Preview token has already crossed its request boundary.",
                    status=409,
                )
            record.consumed = True
            self._transition(record, "requested")

        try:
            dispatch = record.definition.dispatch(record.target, record.inputs, current_source)
        except OperationOwnerError as error:
            with self._lock:
                self._transition(record, error.state)
                record.failure = {
                    "code": error.code,
                    "message": _owner_failure_message(error.state),
                }
            LOGGER.warning(
                "operation owner ended type=%s id=%s state=%s code=%s",
                record.definition.operation_type,
                record.operation_id,
                error.state,
                error.code,
            )
            return {"operation": self._public(record)}
        except Exception as error:
            with self._lock:
                self._transition(record, "failed")
                record.failure = {
                    "code": "owner_failed",
                    "message": "The registered owner failed before returning request evidence.",
                }
            LOGGER.error(
                "operation owner crashed type=%s id=%s exception_type=%s",
                record.definition.operation_type,
                record.operation_id,
                type(error).__name__,
            )
            return {"operation": self._public(record)}

        try:
            validated_dispatch_links = self._validated_links(dispatch.links)
        except OperationOwnerError as error:
            with self._lock:
                self._transition(record, error.state)
                record.failure = {
                    "code": error.code,
                    "message": _owner_failure_message(error.state),
                }
            return {"operation": self._public(record)}
        with self._lock:
            record.request_evidence = dispatch.evidence
            record.links = validated_dispatch_links
            if dispatch.state in {"awaiting-approval", "awaiting-input"}:
                self._transition(record, dispatch.state)
                return {"operation": self._public(record)}
            self._transition(record, "verifying")

        deadline = self._monotonic() + record.definition.timeout_seconds
        while True:
            try:
                verification = record.definition.verify(
                    record.target,
                    record.inputs,
                    current_source,
                    dispatch,
                )
            except OperationOwnerError as error:
                with self._lock:
                    self._transition(record, error.state)
                    record.failure = {
                        "code": error.code,
                        "message": _owner_failure_message(error.state),
                    }
                return {"operation": self._public(record)}
            except Exception as error:
                with self._lock:
                    self._transition(record, "unverified")
                    record.failure = {
                        "code": "postcondition_unavailable",
                        "message": "Canonical postcondition verification is unavailable.",
                    }
                LOGGER.error(
                    "operation verification crashed type=%s id=%s exception_type=%s",
                    record.definition.operation_type,
                    record.operation_id,
                    type(error).__name__,
                )
                return {"operation": self._public(record)}

            if verification.state != "pending":
                try:
                    validated_links = self._validated_links(record.links + verification.links)
                except OperationOwnerError as error:
                    with self._lock:
                        self._transition(record, error.state)
                        record.failure = {
                            "code": error.code,
                            "message": _owner_failure_message(error.state),
                        }
                    return {"operation": self._public(record)}
                with self._lock:
                    final_state = verification.state
                    self._transition(record, final_state)
                    record.verification_evidence = verification.evidence
                    record.links = validated_links
                    if final_state in {"failed", "unverified"}:
                        record.failure = {
                            "code": f"postcondition_{final_state}",
                            "message": (
                                "Canonical postcondition failed."
                                if final_state == "failed"
                                else "Owner request was accepted but the canonical postcondition was not verified."
                            ),
                        }
                return {"operation": self._public(record)}
            if self._monotonic() >= deadline:
                with self._lock:
                    self._transition(record, "unverified")
                    record.verification_evidence = verification.evidence
                    record.failure = {
                        "code": "postcondition_timeout",
                        "message": "Owner request was accepted but the canonical postcondition timed out.",
                    }
                return {"operation": self._public(record)}
            self._sleep(min(0.05, max(0.0, deadline - self._monotonic())))

    def cancel(self, operation_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if payload != {"confirmation": "cancel-before-request"}:
            raise OperationError(
                "cancel_confirmation_required",
                "Cancellation requires the exact pre-request confirmation.",
            )
        with self._lock:
            record = self._record(operation_id)
            if record.state not in {"previewed", "confirmed"} or record.consumed:
                raise OperationError(
                    "cancel_boundary_crossed",
                    "The owner request boundary was crossed; cancellation cannot claim to undo it.",
                    status=409,
                )
            self._transition(record, "cancelled")
            record.failure = {
                "code": "cancelled_before_request",
                "message": "Operation was cancelled before the owner was requested.",
            }
            return {"operation": self._public(record)}

    def get(self, operation_id: str) -> dict[str, Any]:
        with self._lock:
            return {"operation": self._public(self._record(operation_id))}

    def _record(self, operation_id: str) -> _OperationRecord:
        if not isinstance(operation_id, str) or not operation_id.startswith("op_"):
            raise OperationError("invalid_operation_id", "Operation ID is invalid.")
        record = self._records.get(operation_id)
        if record is None:
            raise OperationError(
                "operation_not_found",
                "Operation is unavailable in this server session; inspect its canonical owner.",
                status=404,
            )
        return record

    @staticmethod
    def _validate_route_result(
        request: RouteGateRequest,
        result: RouteGateResult,
    ) -> None:
        expected_action_hash = route_action_fingerprint(request.required_action)
        if (
            result.recipient != request.recipient
            or result.purpose != request.purpose
            or result.source_record != request.source_record
            or (
                request.target_thread is not None
                and result.target_thread != request.target_thread
            )
            or result.action_hash is None
            or not secrets.compare_digest(result.action_hash, expected_action_hash)
            or result.policy_fingerprint is None
        ):
            raise OperationError(
                "route_gate_result_invalid",
                "Allowed route-gate result did not bind the exact recipient, purpose, source, action, and policy.",
                status=503,
            )

    @staticmethod
    def _route_binding(result: RouteGateResult) -> dict[str, Any]:
        return {
            "allowed": result.allowed,
            "target_thread": result.target_thread,
            "recipient": result.recipient,
            "purpose": result.purpose,
            "source_record": result.source_record,
            "action_hash": result.action_hash,
            "policy_fingerprint": result.policy_fingerprint,
        }

    def _invalidate_preview(
        self,
        record: _OperationRecord,
        *,
        code: str,
        message: str,
    ) -> None:
        with self._lock:
            if not record.consumed and record.state in {"previewed", "confirmed"}:
                self._transition(record, "cancelled")
                record.failure = {"code": code, "message": message}

    def _recheck_route_gate(
        self,
        record: _OperationRecord,
        current_source: SourceSnapshot,
    ) -> None:
        definition = record.definition
        if definition.route_gate_request is None:
            return
        try:
            current_request = definition.route_gate_request(
                record.target,
                record.inputs,
                current_source,
            )
        except Exception as error:
            self._invalidate_preview(
                record,
                code="route_gate_unavailable",
                message="Route gate could not be re-resolved before owner dispatch.",
            )
            LOGGER.warning(
                "route request unavailable before dispatch type=%s id=%s exception_type=%s",
                definition.operation_type,
                record.operation_id,
                type(error).__name__,
            )
            raise OperationError(
                "route_gate_unavailable",
                "The required cross-thread route gate is unavailable; preview again.",
                status=503,
                retryable=True,
            ) from error
        if current_request != record.route_request or current_request is None:
            self._invalidate_preview(
                record,
                code="route_gate_stale",
                message="Exact route-gate request changed after preview.",
            )
            raise OperationError(
                "route_gate_stale",
                "Route recipient, purpose, source, or action changed; preview again.",
                status=409,
            )
        try:
            current_result = (
                definition.route_gate(current_request) if definition.route_gate else None
            )
        except Exception as error:
            self._invalidate_preview(
                record,
                code="route_gate_unavailable",
                message="Route gate could not be rechecked before owner dispatch.",
            )
            LOGGER.warning(
                "route gate unavailable before dispatch type=%s id=%s exception_type=%s",
                definition.operation_type,
                record.operation_id,
                type(error).__name__,
            )
            raise OperationError(
                "route_gate_unavailable",
                "The required cross-thread route gate is unavailable; preview again.",
                status=503,
                retryable=True,
            ) from error
        if not isinstance(current_result, RouteGateResult):
            self._invalidate_preview(
                record,
                code="route_gate_result_invalid",
                message="Route gate returned an invalid current result.",
            )
            raise OperationError(
                "route_gate_result_invalid",
                "Route gate returned an invalid current result; preview again.",
                status=503,
            )
        if not current_result.allowed:
            self._invalidate_preview(
                record,
                code="route_gate_denied",
                message="Current route gate denied the exact action.",
            )
            raise OperationError(
                "route_gate_denied",
                "Current route gate denied the exact action; preview again.",
                status=409,
            )
        try:
            self._validate_route_result(current_request, current_result)
        except OperationError:
            self._invalidate_preview(
                record,
                code="route_gate_result_invalid",
                message="Current route-gate result did not bind the exact action.",
            )
            raise
        if self._route_binding(current_result) != self._route_binding(record.route_result):
            self._invalidate_preview(
                record,
                code="route_gate_stale",
                message="Route-gate action or policy changed after preview.",
            )
            raise OperationError(
                "route_gate_stale",
                "Route-gate action or policy changed; preview again.",
                status=409,
            )

    def _transition(self, record: _OperationRecord, state: str) -> None:
        if state not in OPERATION_STATES:
            raise ValueError(f"Invalid operation state: {state}")
        record.state = state
        record.history.append({"state": state, "observed_at": _timestamp(self._wall())})
        LOGGER.info(
            "operation transition type=%s id=%s state=%s",
            record.definition.operation_type,
            record.operation_id,
            state,
        )

    def _make_capacity(self) -> None:
        if len(self._records) < MAX_ACTIVITY_RECORDS:
            return
        terminal_id = next(
            (
                operation_id
                for operation_id, record in self._records.items()
                if record.state in TERMINAL_STATES
            ),
            None,
        )
        if terminal_id is None:
            raise OperationError(
                "operation_capacity_reached",
                "Operation activity capacity is full with nonterminal requests.",
                status=503,
                retryable=True,
            )
        removed = self._records.pop(terminal_id)
        self._token_index.pop(removed.preview_token, None)

    @staticmethod
    def _validated_links(links: tuple[OperationLink, ...]) -> tuple[OperationLink, ...]:
        unique: list[OperationLink] = []
        seen: set[tuple[str, str]] = set()
        for link in links:
            if (
                not link.label.strip()
                or not link.href.startswith("/")
                or link.href.startswith("//")
                or "?" in link.href
                or "#" in link.href
                or not INTERNAL_LINK_PATTERN.fullmatch(link.href)
                or any(segment in {".", ".."} for segment in link.href.split("/"))
                or _redact(link.label) != link.label
            ):
                raise OperationOwnerError(
                    "invalid_owner_link",
                    "Owner returned an invalid result link.",
                    state="unverified",
                )
            identity = (link.label, link.href)
            if identity not in seen:
                seen.add(identity)
                unique.append(link)
        return tuple(unique)

    @staticmethod
    def _public(record: _OperationRecord) -> dict[str, Any]:
        route_gate = {
            "status": "not-required",
            "target_thread": None,
            "recipient": None,
            "purpose": None,
            "source_record": None,
            "required_action": None,
            "action_hash": None,
            "policy_fingerprint": None,
            "binding_fingerprint": None,
        }
        if record.route_request is not None:
            route_binding = (
                OperationCoordinator._route_binding(record.route_result)
                if record.route_result is not None
                else None
            )
            route_gate = {
                "status": "allowed" if record.route_result and record.route_result.allowed else "unavailable",
                "target_thread": record.route_request.target_thread,
                "recipient": record.route_request.recipient,
                "purpose": record.route_request.purpose,
                "source_record": record.route_request.source_record,
                "required_action": _redact(record.route_request.required_action),
                "action_hash": record.route_result.action_hash if record.route_result else None,
                "policy_fingerprint": (
                    record.route_result.policy_fingerprint if record.route_result else None
                ),
                "binding_fingerprint": fingerprint(route_binding) if route_binding else None,
            }
        return {
            "id": record.operation_id,
            "type": record.definition.operation_type,
            "target": record.target.as_dict(),
            "state": record.state,
            "owner": record.definition.owner,
            "authority": _redact(list(record.definition.authority)),
            "preview": {
                "effect": _redact(record.effect.summary),
                "risk": _redact(record.effect.risk),
                "recipient": record.effect.recipient,
                "source_fingerprint": record.source.fingerprint,
                "source_evidence": _redact(record.source.evidence),
                "route_gate": route_gate,
                "consequences": {
                    "ordinary": _redact(list(record.definition.ordinary_consequences)),
                    "failure": _redact(list(record.definition.failure_consequences)),
                },
                "confirmation": {
                    "class": record.definition.confirmation.kind,
                    "prompt": record.definition.confirmation.prompt,
                    "expected_value": record.definition.confirmation.expected_value,
                },
                "expected_postcondition": record.definition.expected_postcondition,
                "idempotency": record.definition.idempotency,
                "limitations": _redact(list(record.definition.limitations)),
                "expires_at": record.expires_at,
            },
            "history": list(record.history),
            "request_evidence": _redact(record.request_evidence),
            "verification_evidence": _redact(record.verification_evidence),
            "links": [{"label": link.label, "href": link.href} for link in record.links],
            "failure": _redact(record.failure),
        }
