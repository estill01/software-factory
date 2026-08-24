from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from ..errors import AuthorityDenied, InvalidTransition


class EffectClass(StrEnum):
    """Fixed target-effect classes owned by profiles, never by providers."""

    WORKSPACE = "workspace"
    COMMAND = "command"
    TEST = "test"
    BUILD = "build"
    INTEGRATION = "integration"
    RELEASE = "release"
    CLEANUP = "cleanup"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class TargetSnapshot:
    profile_key: str
    target_id: str
    revision: str
    currentness_root: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileEffectResult:
    profile_key: str
    effect_class: EffectClass
    target_id: str
    before: TargetSnapshot
    after: TargetSnapshot
    result: Mapping[str, Any]


class TargetProfile(Protocol):
    key: str
    effect_classes: frozenset[EffectClass]

    def snapshot(self, target_id: str) -> TargetSnapshot: ...

    def _execute_effect(
        self,
        effect_class: EffectClass,
        target_id: str,
        *,
        expected_revision: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class TargetProfileRegistry:
    """Composition-owned profile registry and exact-currentness effect fence."""

    def __init__(self) -> None:
        self._profiles: dict[str, TargetProfile] = {}

    def register(self, profile: TargetProfile) -> None:
        key = profile.key.strip()
        if not key:
            raise ValueError("target profile key is required")
        if key in self._profiles:
            raise ValueError(f"target profile is already registered: {key}")
        if not profile.effect_classes:
            raise ValueError("target profile must own at least one fixed effect class")
        if any(not isinstance(effect, EffectClass) for effect in profile.effect_classes):
            raise ValueError("target profile effect classes must be fixed EffectClass values")
        self._profiles[key] = profile

    def get(self, profile_key: str) -> TargetProfile:
        try:
            return self._profiles[profile_key]
        except KeyError as exc:
            raise AuthorityDenied(f"target profile is not registered: {profile_key}") from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._profiles))

    def snapshot(self, profile_key: str, target_id: str) -> TargetSnapshot:
        return self.get(profile_key).snapshot(target_id)

    def execute(
        self,
        profile_key: str,
        effect_class: EffectClass,
        target_id: str,
        *,
        expected_revision: str,
        expected_currentness_root: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> ProfileEffectResult:
        if not isinstance(effect_class, EffectClass):
            raise AuthorityDenied("target effect must use a registered fixed effect class")
        profile = self.get(profile_key)
        if effect_class not in profile.effect_classes:
            raise AuthorityDenied(
                f"target profile {profile_key} does not own effect {effect_class.value}"
            )
        before = profile.snapshot(target_id)
        if before.revision != expected_revision:
            raise InvalidTransition("target revision changed before authoritative effect")
        if before.currentness_root != expected_currentness_root:
            raise InvalidTransition("target currentness changed before authoritative effect")
        result = profile._execute_effect(
            effect_class,
            target_id,
            expected_revision=expected_revision,
            arguments=dict(arguments or {}),
        )
        after = profile.snapshot(target_id)
        return ProfileEffectResult(
            profile_key=profile_key,
            effect_class=effect_class,
            target_id=target_id,
            before=before,
            after=after,
            result=dict(result),
        )
