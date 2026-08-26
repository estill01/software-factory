from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from software_factory import AuthorityDenied, EffectClass, InvalidTransition, TargetSnapshot


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _root(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


class ObservationCardExtensionProfile:
    """Consumer-owned example profile kept wholly outside the Factory package."""

    key = "observation-card"
    effect_classes = frozenset(
        {EffectClass.WORKSPACE, EffectClass.BUILD, EffectClass.TEST, EffectClass.RELEASE}
    )

    def __init__(self, root: Path, records: Sequence[Mapping[str, Any]]) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True)
        self.records = tuple(dict(record) for record in records)
        self.authority: object | None = None
        self._write("state.json", {"sequence": 0, "phase": "registered"})

    def _write(self, relative: str, value: Mapping[str, Any]) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_canonical(value) + "\n", encoding="utf-8")

    def _state(self) -> dict[str, Any]:
        return json.loads((self.root / "state.json").read_text(encoding="utf-8"))

    def _advance(self, phase: str) -> None:
        state = self._state()
        state["sequence"] += 1
        state["phase"] = phase
        self._write("state.json", state)

    def _bind_registry_authority(self, authority: object) -> None:
        if self.authority is not None:
            raise InvalidTransition("external extension is already registered")
        self.authority = authority

    def snapshot(self, target_id: str) -> TargetSnapshot:
        if target_id != "field-summary":
            raise AuthorityDenied("external observation target is not registered")
        state = self._state()
        members = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                payload = path.read_bytes()
                members.append(
                    {
                        "path": path.relative_to(self.root).as_posix(),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                )
        revision = _root({"state": state, "records": self.records})
        attributes = {"phase": state["phase"], "members": members}
        return TargetSnapshot(
            profile_key=self.key,
            target_id=target_id,
            revision=revision,
            currentness_root=_root({"revision": revision, "attributes": attributes}),
            attributes=attributes,
        )

    def _execute_effect(
        self,
        authority: object,
        effect_class: EffectClass,
        target_id: str,
        *,
        expected_revision: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if authority is not self.authority:
            raise AuthorityDenied("external effects require registry authority")
        if target_id != "field-summary" or set(arguments) != {"operation"}:
            raise AuthorityDenied("external effect contract is closed")
        if self.snapshot(target_id).revision != expected_revision:
            raise InvalidTransition("external extension revision changed")
        operation = arguments["operation"]
        state = self._state()
        if (effect_class, operation) == (EffectClass.WORKSPACE, "collect"):
            if state["phase"] != "registered":
                raise InvalidTransition("external collection is out of order")
            self._write("workspace/records.json", {"records": list(self.records)})
            self._advance("collected")
            return {"record_count": len(self.records)}
        if (effect_class, operation) == (EffectClass.BUILD, "render"):
            if state["phase"] != "collected":
                raise InvalidTransition("external render is out of order")
            values = [int(record["value"]) for record in self.records]
            summary = {"count": len(values), "minimum": min(values), "maximum": max(values)}
            self._write("rendered/summary.json", summary)
            self._advance("rendered")
            return summary
        if (effect_class, operation) == (EffectClass.RELEASE, "deliver"):
            if state["phase"] != "rendered":
                raise InvalidTransition("external delivery is out of order")
            summary = json.loads(
                (self.root / "rendered" / "summary.json").read_text(encoding="utf-8")
            )
            self._write("delivered/summary.json", summary)
            self._write("delivered/receipt.json", {"summary_root": _root(summary)})
            self._advance("delivered")
            return {"summary_root": _root(summary)}
        if (effect_class, operation) == (EffectClass.TEST, "verify"):
            if state["phase"] != "delivered":
                raise InvalidTransition("external verification is out of order")
            summary = json.loads(
                (self.root / "delivered" / "summary.json").read_text(encoding="utf-8")
            )
            receipt = json.loads(
                (self.root / "delivered" / "receipt.json").read_text(encoding="utf-8")
            )
            if receipt != {"summary_root": _root(summary)}:
                raise InvalidTransition("external delivery receipt differs")
            self._advance("delivered_verified")
            return {"passed": True, **receipt}
        raise AuthorityDenied(f"external extension does not register {effect_class}/{operation}")
