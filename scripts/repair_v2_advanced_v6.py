#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime" / "src" / "software_factory"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}: found {count}\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_recovery_imports_and_timestamps() -> None:
    path = SOURCE / "recovery.py"
    text = path.read_text(encoding="utf-8")
    if "import json\n" not in text:
        text = text.replace("from __future__ import annotations\n\n", "from __future__ import annotations\n\nimport json\n", 1)
    if "from .util import utc_now\n" not in text:
        text = text.replace("from .store import Store\n", "from .store import Store\nfrom .util import utc_now\n", 1)
    text = text.replace("(plan[\"updated_at\"], plan[\"id\"])", "(utc_now(), plan[\"id\"])")
    text = text.replace(
        "                        plan[\"updated_at\"],\n                        plan[\"id\"],",
        "                        utc_now(),\n                        plan[\"id\"],",
    )
    path.write_text(text, encoding="utf-8")


def make_duplicate_recovery_idempotent() -> None:
    operations = SOURCE / "operations.py"
    text = operations.read_text(encoding="utf-8")
    old = '''        active_statuses = (
            "detected",
            "repairing",
            "qa",
            "releasing",
            "restoring",
            "resuming",
            "verifying",
            "failed",
        )
'''
    new = '''        active_statuses = (
            "detected",
            "repairing",
            "qa",
            "releasing",
            "restoring",
            "resuming",
            "verifying",
            "resolved",
            "failed",
        )
'''
    if new not in text:
        replace_once(operations, old, new)

    recovery = SOURCE / "recovery.py"
    text = recovery.read_text(encoding="utf-8")
    marker = '''        recovery = self.operations.open_recovery(
            target_mission_id=target_mission_id,
            defect_class=defect_class,
            defect_evidence=defect_evidence,
            target_state=target_state,
            requested_range_root=requested_range_root,
            tracker_currentness_root=tracker_currentness_root,
            safe_frontier=safe_frontier,
        )
'''
    addition = marker + '''        if recovery["status"] == "resolved":
            token = self.store.one(
                "SELECT * FROM recovery_resume_tokens_v2 WHERE recovery_id=?",
                (recovery["id"],),
                required=False,
            )
            wake_effect = self.store.one(
                """SELECT * FROM external_effect_intents_v2
                   WHERE idempotency_key=?""",
                (token["resume_key"],) if token else ("",),
                required=False,
            )
            release = self.store.one(
                "SELECT * FROM immutable_releases_v2 WHERE id=?",
                (recovery["release_id"],),
                required=False,
            )
            return {
                "recovery": recovery,
                "release": release,
                "resume_token": token,
                "wake_effect": wake_effect,
                "verification": {"already_resolved": True},
            }
'''
    if "already_resolved" not in text:
        if marker not in text:
            raise RuntimeError("recovery idempotency insertion point is missing")
        recovery.write_text(text.replace(marker, addition, 1), encoding="utf-8")


def main() -> None:
    fix_recovery_imports_and_timestamps()
    make_duplicate_recovery_idempotent()


if __name__ == "__main__":
    main()
