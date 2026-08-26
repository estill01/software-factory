from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from typing import Any

from .errors import EvidenceInvalid, InvalidTransition
from .util import digest_json, json_load


def terminal_profile_bindings(db: Any, mission_id: str) -> list[dict[str, str]]:
    """Return the exact selected, non-cancelled profile set eligible for terminal use."""

    bindings: list[dict[str, str]] = []
    rows = db.execute(
        """SELECT id,expected_effect_json,candidate_revision,acceptance_status
           FROM work_items
           WHERE mission_id=? AND planning_status='selected'
             AND execution_status<>'cancelled' ORDER BY id""",
        (mission_id,),
    ).fetchall()
    for row in rows:
        expected_effect = json_load(row["expected_effect_json"], {})
        profile_key = expected_effect.get("target_profile")
        target_id = expected_effect.get("target_id")
        if not isinstance(profile_key, str) or not isinstance(target_id, str):
            continue
        if row["acceptance_status"] != "installed_accepted":
            raise InvalidTransition("terminal profile set contains work below installed acceptance")
        revision = str(row["candidate_revision"] or "")
        requirements = db.execute(
            """SELECT qa_type,status,acceptance_contract_root,predicate_json
               FROM qa_requirements
               WHERE work_item_id=? AND phase='candidate' AND candidate_revision=?
                 AND status<>'stale'""",
            (row["id"], revision),
        ).fetchall()
        roots = {
            str(requirement["acceptance_contract_root"])
            for requirement in requirements
            if requirement["acceptance_contract_root"]
        }
        currentness = [
            requirement
            for requirement in requirements
            if requirement["qa_type"] == "profile_currentness" and requirement["status"] == "passed"
        ]
        if not revision or len(roots) != 1 or len(currentness) != 1:
            raise EvidenceInvalid(
                "installed profile work lacks one active passed candidate/currentness root"
            )
        predicate = json_load(currentness[0]["predicate_json"], {})
        if (
            predicate.get("profile_key") != profile_key
            or predicate.get("target_id") != target_id
            or predicate.get("revision") != revision
            or not isinstance(predicate.get("currentness_root"), str)
        ):
            raise EvidenceInvalid("installed profile currentness binding is incomplete")
        bindings.append(
            {
                "work_item_id": str(row["id"]),
                "profile_key": profile_key,
                "target_id": target_id,
                "candidate_root": next(iter(roots)),
                "revision": revision,
                "currentness_root": str(predicate["currentness_root"]),
            }
        )
    return sorted(
        bindings,
        key=lambda item: (item["profile_key"], item["target_id"], item["work_item_id"]),
    )


def terminal_profile_scope(mission_id: str, bindings: Sequence[dict[str, str]]) -> str:
    root = digest_json({"mission_id": mission_id, "profile_bindings": list(bindings)})
    return f"mission:{mission_id}:profiles:{root}"


@contextmanager
def terminal_profile_fences(
    target_profiles: Any,
    bindings: Sequence[dict[str, str]],
) -> Iterator[None]:
    """Acquire every physical profile fence in the binding's deterministic order."""

    if bindings and target_profiles is None:
        raise InvalidTransition("terminal profile currentness is not configured")
    with ExitStack() as stack:
        for binding in bindings:
            stack.enter_context(
                target_profiles.currentness_fence(
                    binding["profile_key"],
                    binding["target_id"],
                    expected_revision=binding["revision"],
                    expected_currentness_root=binding["currentness_root"],
                )
            )
        yield
