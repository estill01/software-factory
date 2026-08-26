from __future__ import annotations

import json
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .engine import ENGINE_CONTRACT_VERSION, MissionSubmission
from .errors import StoreError
from .hosts.embedded import EmbeddedFactoryHost
from .hosts.service import StandaloneFactoryService
from .schema import MIGRATIONS, SCHEMA_VERSION, migration_sql
from .util import digest_bytes, digest_json
from .utility_provenance import QualifiedUtilityPin, load_qualified_utility_modules

_SHA256 = re.compile(r"[0-9a-f]{64}")
_AUTHORITY_FIELDS = {
    "accept",
    "acceptance",
    "accepted",
    "authorization",
    "authorized",
    "authority",
    "permission",
    "release_authority",
}
SERVICE_ENGINE_OPERATIONS = frozenset({"start", "status", "continue", "outcome", "events"})
SERVICE_MAX_REQUEST_BYTES = 1024 * 1024
SERVICE_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SERVICE_MAX_REQUEST_TARGET_BYTES = 4096


@dataclass(frozen=True)
class RuntimeIdentity:
    """Factory-owned identity verified against the currently imported package bytes."""

    component_root: str
    version: str = "2.0.0.dev6"

    def __post_init__(self) -> None:
        if _SHA256.fullmatch(self.component_root) is None:
            raise ValueError("component_root must be an exact lowercase SHA-256")
        if not self.version or len(self.version) > 128:
            raise ValueError("runtime version must be bounded non-empty text")
        self.assert_current()

    def assert_current(self) -> None:
        observed = installed_component_root()
        if not secrets.compare_digest(self.component_root, observed):
            raise ValueError("component_root does not match the installed Factory package bytes")


def installed_component_root() -> str:
    """Hash every authoritative file shipped in the imported Factory package.

    Interpreter caches are excluded because they are derived runtime residue.
    Symlinked package members fail closed so the root always describes the bytes
    actually opened from one regular installed package tree.
    """

    root = Path(__file__).resolve().parent
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc" or not path.is_file():
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise StoreError(f"installed Factory package member is not a regular file: {relative}")
        content = path.read_bytes()
        entries.append(
            {
                "path": relative.as_posix(),
                "size": len(content),
                "sha256": digest_bytes(content),
            }
        )
    if not entries:
        raise StoreError("installed Factory package contains no authoritative files")
    return digest_json({"format": "software-factory-component/1", "files": entries})


def engine_protocol_root() -> str:
    return digest_json(
        {
            "contract": ENGINE_CONTRACT_VERSION,
            "event_sequence_scope": "mission",
            "operations": {
                "cancel": ["mission_id", "reason"],
                "continue": ["mission_id"],
                "events": ["mission_id", "after_sequence", "limit"],
                "outcome": ["mission_id"],
                "start": [
                    "idempotency_key",
                    "title",
                    "objective",
                    "project_id",
                    "autonomy_mode",
                    "resource_limits",
                ],
                "status": ["mission_id"],
            },
        }
    )


def service_api_protocol_root() -> str:
    return digest_json(
        {
            "schema_version": 1,
            "bind_scope": "loopback-only",
            "public_get_routes": ["/", "/health", "/ready"],
            "authenticated_get_routes": [
                "/api/factory-floor",
                "/api/health",
                "/api/missions/{mission_id}",
                "/api/runtime-manifest",
            ],
            "engine_operations": sorted(SERVICE_ENGINE_OPERATIONS),
            "operator_route": "/api/operator-actions",
            "transport_authorization": "bearer-service-token",
            "workflow_currentness_header": "X-Software-Factory-Workflow-Root",
            "operator_authority_header": "X-Software-Factory-Operator-Token",
            "limits": {
                "request_body_bytes": SERVICE_MAX_REQUEST_BYTES,
                "request_target_bytes": SERVICE_MAX_REQUEST_TARGET_BYTES,
                "response_body_bytes": SERVICE_MAX_RESPONSE_BYTES,
            },
        }
    )


def database_schema_root() -> str:
    return digest_json(
        [
            {
                "version": migration.version,
                "name": migration.name,
                "sha256": digest_bytes(migration_sql(migration).encode("utf-8")),
            }
            for migration in MIGRATIONS
        ]
    )


class FactoryLifecycleAdapter:
    """Factory-owned mapping to the neutral structural lifecycle protocol."""

    def __init__(
        self,
        host: EmbeddedFactoryHost | StandaloneFactoryService,
        embedded_contract: ModuleType,
        *,
        mode: str,
    ):
        if mode not in {"embedded", "service"}:
            raise ValueError("lifecycle adapter mode must be embedded or service")
        self._host = host
        self._contract_module = embedded_contract
        shape = (
            embedded_contract.HostShape.EMBEDDED
            if mode == "embedded"
            else embedded_contract.HostShape.SERVICE
        )
        self.contract = embedded_contract.HostContract(
            shape=shape,
            process_owner_count=0 if mode == "embedded" else 1,
        )

    def _unknown(self, operation) -> Any:
        try:
            return operation()
        except (LookupError, StoreError) as exc:
            raise self._contract_module.UnknownRunError("unknown Factory mission") from exc

    def start(self, request: MissionSubmission) -> Any:
        if type(request) is not MissionSubmission:
            raise TypeError("Factory lifecycle start requires MissionSubmission")
        ref = self._host.start(request)
        return self._contract_module.RunRef(ref.mission_id)

    def _outcome(self, ref) -> Any:
        outcome = self._unknown(lambda: self._host.outcome(ref.value))
        if not outcome.terminal:
            return None
        if outcome.disposition == "succeeded":
            return self._contract_module.Succeeded(ref, outcome)
        if outcome.disposition == "cancelled":
            return self._contract_module.Cancelled(ref)
        return self._contract_module.Failed(ref, outcome)

    def status(self, ref) -> Any:
        if type(ref) is not self._contract_module.RunRef:
            raise TypeError("status requires the exact shared RunRef")
        snapshot = self._unknown(lambda: self._host.status(ref.value))
        outcome = self._outcome(ref)
        if outcome is None:
            state = self._contract_module.RunState.RUNNING
        elif type(outcome) is self._contract_module.Succeeded:
            state = self._contract_module.RunState.SUCCEEDED
        elif type(outcome) is self._contract_module.Cancelled:
            state = self._contract_module.RunState.CANCELLED
        else:
            state = self._contract_module.RunState.FAILED
        return self._contract_module.RunStatus(ref, state, snapshot.last_event_sequence)

    def events(self, ref, *, after_sequence: int = 0) -> tuple[Any, ...]:
        if type(ref) is not self._contract_module.RunRef:
            raise TypeError("events requires the exact shared RunRef")
        if type(after_sequence) is not int or after_sequence < 0:
            raise self._contract_module.InvalidCursorError("event cursor must be non-negative")
        events = self._unknown(
            lambda: self._host.events(ref.value, after_sequence=after_sequence, limit=1000)
        )
        return tuple(
            self._contract_module.EventRecord(ref, event.sequence, event) for event in events
        )

    def cancel(self, ref) -> Any:
        if type(ref) is not self._contract_module.RunRef:
            raise TypeError("cancel requires the exact shared RunRef")
        before = self._outcome(ref)
        if before is not None:
            return self._contract_module.CancelResult(ref, self.status(ref).state, False)
        self._unknown(lambda: self._host.cancel(ref.value, reason="structural cancellation"))
        state = self.status(ref).state
        return self._contract_module.CancelResult(ref, state, True)

    def outcome(self, ref) -> Any:
        if type(ref) is not self._contract_module.RunRef:
            raise TypeError("outcome requires the exact shared RunRef")
        return self._outcome(ref)


@dataclass(frozen=True)
class QualifiedUtilityRuntime:
    embedded_contract: ModuleType
    runtime_manifest: ModuleType
    pin: QualifiedUtilityPin

    @classmethod
    def from_wheels(
        cls,
        *,
        embedded_contract_wheel: str | Path,
        runtime_manifest_wheel: str | Path,
    ) -> QualifiedUtilityRuntime:
        embedded, manifest, pin = load_qualified_utility_modules(
            embedded_contract_wheel=embedded_contract_wheel,
            runtime_manifest_wheel=runtime_manifest_wheel,
        )
        return cls(embedded_contract=embedded, runtime_manifest=manifest, pin=pin)

    def lifecycle_adapter(
        self,
        host: EmbeddedFactoryHost | StandaloneFactoryService,
        *,
        mode: str,
    ) -> FactoryLifecycleAdapter:
        return FactoryLifecycleAdapter(host, self.embedded_contract, mode=mode)

    def manifest_document(self, identity: RuntimeIdentity) -> str:
        identity.assert_current()
        module = self.runtime_manifest
        packages = self.pin.record["packages"]
        manifest = module.RuntimeManifest(
            component=module.Component(
                "software-factory",
                identity.version,
                module.Sha256Root(identity.component_root),
            ),
            protocols=(
                module.Protocol(
                    "software-factory-database",
                    str(SCHEMA_VERSION),
                    module.Sha256Root(database_schema_root()),
                    ("single-writer", "transactional-migrations"),
                ),
                module.Protocol(
                    "software-factory-engine",
                    ENGINE_CONTRACT_VERSION,
                    module.Sha256Root(engine_protocol_root()),
                    ("bounded-events", "idempotent-submission", "typed-operations"),
                ),
                module.Protocol(
                    "software-factory-loopback-service",
                    "1",
                    module.Sha256Root(service_api_protocol_root()),
                    (
                        "content-minimized-views",
                        "current-workflow-root",
                        "one-time-operator-authority",
                        "transport-authentication",
                    ),
                ),
            ),
            capabilities=(
                module.Capability("embedded-host", "1"),
                module.Capability("loopback-service", "1"),
                module.Capability("operator-view", "1"),
            ),
            dependencies=tuple(
                module.Component(
                    name,
                    package["version"],
                    module.Sha256Root(package["wheel_content_root_sha256"]),
                )
                for name, package in sorted(packages.items())
            ),
        )
        document = module.canonical_json(manifest)
        self._reject_authority_fields(json.loads(document))
        return document

    @classmethod
    def _reject_authority_fields(cls, value: Any) -> None:
        if isinstance(value, dict):
            if _AUTHORITY_FIELDS.intersection(value):
                raise StoreError("runtime manifest cannot carry Factory authority")
            for item in value.values():
                cls._reject_authority_fields(item)
        elif isinstance(value, list):
            for item in value:
                cls._reject_authority_fields(item)
