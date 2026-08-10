from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


MAX_FLOOR_ROWS = 80
MAX_TASK_ONLY_ROWS = 32
MAX_ATTENTION = 80
MAX_CONCLUSIONS = 24
MAX_OUTCOMES = 24
RECENT_TASK_SECONDS = 24 * 60 * 60


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _newest_timestamp(*values: Any) -> str | None:
    candidates = [(parsed, value) for value in values if (parsed := _timestamp(value))]
    return max(candidates, default=(None, None), key=lambda item: item[0])[1]


def _record_ref(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, Mapping):
        return None
    return {
        "record_id": record.get("record_id"),
        "kind": record.get("kind"),
        "status": record.get("status"),
        "severity": record.get("severity"),
        "category": record.get("category"),
        "summary": record.get("summary"),
        "action": record.get("action"),
        "resolution": record.get("resolution"),
        "observed_at": record.get("timestamp"),
        "source": record.get("source"),
    }


def _task_posture(task: Mapping[str, Any] | None) -> tuple[str, str]:
    if task is None:
        return "unavailable", "Task state unavailable"
    status = task.get("status")
    value = status.get("type") if isinstance(status, Mapping) else None
    if value == "active":
        return "active", "Active"
    if value == "idle":
        return "idle", "Idle"
    if value == "systemError":
        return "terminal", "System error"
    if value == "notLoaded":
        return "unavailable", "Not loaded"
    return "unknown", "Unknown"


def _supervision_posture(run: Mapping[str, Any] | None) -> tuple[str, str]:
    if run is None:
        return "unmonitored", "Unmonitored"
    if run.get("status") != "available":
        return "unavailable", "Source unavailable"
    lifecycle = run.get("lifecycle")
    value = lifecycle.get("status") if isinstance(lifecycle, Mapping) else None
    if value in {"paused", "completed", "stopped", "failed", "blocked"}:
        return str(value), str(value).replace("-", " ").title()
    return "active", "Supervising"


def _task_is_recent(task: Mapping[str, Any], observed_at: str) -> bool:
    status, _ = _task_posture(task)
    if status == "active":
        return True
    observed = _timestamp(observed_at)
    recency = _timestamp(task.get("recency_at") or task.get("updated_at"))
    return bool(observed and recency and (observed - recency).total_seconds() <= RECENT_TASK_SECONDS)


def _project_binding(
    run: Mapping[str, Any] | None,
    task: Mapping[str, Any] | None,
    project_labels: Mapping[str, str],
) -> tuple[dict[str, Any], list[str]]:
    run_binding = run.get("project_binding") if isinstance(run, Mapping) else None
    task_binding = task.get("project_binding") if isinstance(task, Mapping) else None
    run_id = (
        run_binding.get("project_id")
        if isinstance(run_binding, Mapping) and run_binding.get("status") == "bound"
        else None
    )
    task_id = (
        task_binding.get("project_id")
        if isinstance(task_binding, Mapping) and task_binding.get("status") == "bound"
        else None
    )
    disagreements: list[str] = []
    run_status = run_binding.get("status") if isinstance(run_binding, Mapping) else None
    task_status = task_binding.get("status") if isinstance(task_binding, Mapping) else None
    if run_id and task_id and run_id != task_id:
        disagreements.append(
            f"Supervision binds project {run_id}; task cwd binds project {task_id}."
        )
        return (
            {
                "status": "ambiguous",
                "project_id": None,
                "label": "Project disagreement",
                "reason": disagreements[0],
            },
            disagreements,
        )
    project_id = run_id or task_id
    if run_id and task_id:
        status = "bound"
        reason = "Supervision and task cwd agree."
    elif run_id:
        status = "run-only"
        reason = "Only the supervision owner supplies a project binding."
        if task_status and task_status != "bound":
            disagreements.append(
                f"Task project binding is {task_status}; supervision binds project {run_id}."
            )
    elif task_id:
        status = "task-only"
        reason = "Only canonical task cwd supplies a project binding."
        if run_status and run_status != "bound":
            disagreements.append(
                f"Supervision project binding is {run_status}; task cwd binds project {task_id}."
            )
    else:
        return (
            {
                "status": "unassigned",
                "project_id": None,
                "label": "Unassigned",
                "reason": "No current source binds this work to a registered project.",
            },
            disagreements,
        )
    return (
        {
            "status": status,
            "project_id": project_id,
            "label": project_labels.get(str(project_id), str(project_id)),
            "reason": reason,
        },
        disagreements,
    )


def _tracker_binding(
    run: Mapping[str, Any] | None,
    project_id: str | None,
    trackers_by_project: Mapping[str, list[Mapping[str, Any]]],
) -> tuple[dict[str, Any], list[str]]:
    topology = run.get("topology") if isinstance(run, Mapping) else None
    canonical = topology.get("tracker_binding") if isinstance(topology, Mapping) else None
    if isinstance(canonical, Mapping) and canonical.get("status") == "bound":
        path = canonical.get("tracker_path")
        candidates = [
            tracker
            for tracker in trackers_by_project.get(project_id or "", [])
            if tracker.get("relative_path") == path
        ]
        if len(candidates) == 1:
            tracker = candidates[0]
            return (
                {
                    "status": "exact",
                    "id": tracker.get("id"),
                    "title": tracker.get("title"),
                    "relative_path": tracker.get("relative_path"),
                    "candidates": [],
                },
                [],
            )
    candidates = trackers_by_project.get(project_id or "", [])
    available = [tracker for tracker in candidates if tracker.get("status") == "available"]
    if len(available) == 1:
        tracker = available[0]
        return (
            {
                "status": "candidate",
                "id": tracker.get("id"),
                "title": tracker.get("title"),
                "relative_path": tracker.get("relative_path"),
                "candidates": [tracker.get("id")],
            },
            ["Tracker association is a project-local candidate, not a canonical run binding."],
        )
    if len(available) > 1:
        return (
            {
                "status": "ambiguous",
                "id": None,
                "title": None,
                "relative_path": None,
                "candidates": [tracker.get("id") for tracker in available],
            },
            [f"{len(available)} project trackers are candidates; none is selected."],
        )
    return (
        {
            "status": "unavailable",
            "id": None,
            "title": None,
            "relative_path": None,
            "candidates": [],
        },
        ["No canonical tracker association is available."],
    )


def _roles(
    run: Mapping[str, Any] | None,
    tasks_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    topology = run.get("topology") if isinstance(run, Mapping) else None
    raw_roles = topology.get("roles") if isinstance(topology, Mapping) else None
    projected: list[dict[str, Any]] = []
    for role in raw_roles if isinstance(raw_roles, list) else []:
        if not isinstance(role, Mapping):
            continue
        thread_id = role.get("thread_id")
        task = tasks_by_id.get(str(thread_id)) if thread_id else None
        task_status, _ = _task_posture(task)
        automation = role.get("automation")
        projected.append(
            {
                "role": role.get("role"),
                "label": role.get("label"),
                "thread_id": thread_id,
                "binding_status": role.get("binding_status"),
                "task_status": task_status,
                "automation_status": (
                    automation.get("owner_status")
                    if isinstance(automation, Mapping)
                    else "unavailable"
                ),
            }
        )
    return projected


def _light(
    run: Mapping[str, Any] | None,
    task: Mapping[str, Any] | None,
    tracker: Mapping[str, Any],
    disagreements: Sequence[str],
    observed_at: str,
) -> dict[str, Any]:
    task_status, _ = _task_posture(task)
    if run is None:
        return {
            "posture": "neutral",
            "label": "Unmonitored",
            "reason": "No supervision group is bound to this implementation task.",
            "observed_at": task.get("updated_at") if task else observed_at,
            "source_identity": "codex-app-server/task-state",
            "completion_claim": False,
        }
    raw = run.get("light")
    posture = raw.get("posture") if isinstance(raw, Mapping) else "neutral"
    label = raw.get("label") if isinstance(raw, Mapping) else "Unknown"
    facts = raw.get("facts") if isinstance(raw, Mapping) else []
    first = facts[0] if isinstance(facts, list) and facts else None
    reason = (
        first.get("detail")
        if isinstance(first, Mapping)
        else "No current operating-light reason is available."
    )
    source_identity = (
        first.get("source_identity")
        if isinstance(first, Mapping)
        else "supervision/derived-light"
    )
    light_time = (
        first.get("observed_at")
        if isinstance(first, Mapping)
        else run.get("observed_at") or observed_at
    )
    supervision_status, _ = _supervision_posture(run)
    if supervision_status in {"paused", "completed", "stopped"}:
        return {
            "posture": "neutral",
            "label": supervision_status.title(),
            "reason": f"The recorded supervision lifecycle is {supervision_status}.",
            "observed_at": light_time,
            "source_identity": "supervision/lifecycle",
            "completion_claim": False,
        }
    if posture == "green" and (
        task_status in {"unavailable", "unknown"}
        or tracker.get("status") in {"candidate", "ambiguous", "unavailable"}
        or disagreements
    ):
        return {
            "posture": "amber",
            "label": "Coverage incomplete",
            "reason": disagreements[0] if disagreements else "A required row source is unavailable.",
            "observed_at": light_time,
            "source_identity": "factory-floor/source-reconciliation",
            "completion_claim": False,
        }
    return {
        "posture": posture if posture in {"red", "amber", "green", "neutral"} else "neutral",
        "label": label or "Unknown",
        "reason": reason,
        "observed_at": light_time,
        "source_identity": source_identity,
        "completion_claim": False,
    }


def _row(
    *,
    run: Mapping[str, Any] | None,
    task: Mapping[str, Any] | None,
    project_labels: Mapping[str, str],
    trackers_by_project: Mapping[str, list[Mapping[str, Any]]],
    tasks_by_id: Mapping[str, Mapping[str, Any]],
    observed_at: str,
) -> dict[str, Any]:
    target_id = str(run.get("target_thread_id")) if run else str(task.get("id"))
    project, disagreements = _project_binding(run, task, project_labels)
    tracker, tracker_disagreements = _tracker_binding(
        run,
        project.get("project_id"),
        trackers_by_project,
    )
    disagreements.extend(tracker_disagreements)
    task_status, task_label = _task_posture(task)
    supervision_status, supervision_label = _supervision_posture(run)
    roles = _roles(run, tasks_by_id)
    topology = run.get("topology") if run else None
    activities = run.get("activities") if run else None
    activity = activities[-1] if isinstance(activities, list) and activities else None
    conclusions = run.get("conclusions") if run else None
    conclusion = conclusions[-1] if isinstance(conclusions, list) and conclusions else None
    counts = run.get("counts") if run else None
    issue_counts = {
        "incidents": int(counts.get("open_incidents", 0)) if isinstance(counts, Mapping) else 0,
        "decisions": int(counts.get("open_decisions", 0)) if isinstance(counts, Mapping) else 0,
        "transitions": int(counts.get("open_successor_transitions", 0))
        if isinstance(counts, Mapping)
        else 0,
    }
    issue_counts["total"] = sum(issue_counts.values())
    last_check = _record_ref(run.get("last_check")) if run else None
    observed = _newest_timestamp(
        task.get("updated_at") if task else None,
        run.get("observed_at") if run else None,
        last_check.get("observed_at") if last_check else None,
    ) or observed_at
    source_refs = []
    if run:
        source_refs.append(
            {
                "kind": "supervision-run",
                "identity": target_id,
                "record_id": None,
                "path": run.get("source", {}).get("root")
                if isinstance(run.get("source"), Mapping)
                else None,
                "line": None,
                "revision": run.get("fingerprint"),
                "route": f"/?inspect=run:{target_id}",
            }
        )
    if task:
        source_refs.append(
            {
                "kind": "codex-task",
                "identity": target_id,
                "record_id": target_id,
                "path": None,
                "line": None,
                "revision": None,
                "route": f"/?inspect=task:{target_id}",
            }
        )
    if tracker.get("id"):
        source_refs.append(
            {
                "kind": "tracker",
                "identity": tracker.get("id"),
                "record_id": None,
                "path": tracker.get("relative_path"),
                "line": None,
                "revision": None,
                "route": f"/?inspect=tracker:{tracker.get('id')}",
            }
        )
    return {
        "id": f"run:{target_id}" if run else f"task:{target_id}",
        "project": project,
        "implementation": {
            "task_id": task.get("id") if task else target_id,
            "name": task.get("name") if task else run.get("target_label") if run else None,
            "status": task_status,
            "status_label": task_label,
            "updated_at": task.get("updated_at") if task else None,
            "source_status": "available" if task else "unavailable",
        },
        "supervision": {
            "run_id": target_id if run else None,
            "group_id": topology.get("supervisor_group_id")
            if isinstance(topology, Mapping)
            else None,
            "target_thread_id": target_id,
            "status": supervision_status,
            "status_label": supervision_label,
            "binding_integrity": topology.get("binding_integrity")
            if isinstance(topology, Mapping)
            else "unavailable",
            "roles": roles,
            "role_count": len(roles),
            "last_check": last_check,
            "next_check": {
                "status": "unavailable",
                "at": None,
                "reason": "The automation owner exposes cadence but no canonical next occurrence.",
            },
        },
        "work": {
            "active_block": (
                str(activity.get("active_block"))
                if isinstance(activity, Mapping) and activity.get("active_block") is not None
                else None
            ),
            "checkpoint": activity.get("checkpoint")
            if isinstance(activity, Mapping)
            else None,
            "mission_root": run.get("current_mission", {}).get("root")
            if run and isinstance(run.get("current_mission"), Mapping)
            else None,
            "last_action": activity.get("action")
            if isinstance(activity, Mapping)
            else None,
            "tracker": tracker,
        },
        "issues": issue_counts,
        "conclusion": _record_ref(conclusion),
        "light": _light(run, task, tracker, disagreements, observed_at),
        "freshness": {
            "status": "current" if observed else "unavailable",
            "observed_at": observed,
            "reason": "Newest exact task, run, or check observation for this row.",
        },
        "disagreements": disagreements,
        "detail": {
            "kind": "run" if run else "task",
            "id": target_id,
            "route": f"/?inspect={'run' if run else 'task'}:{target_id}",
            "source_refs": source_refs,
        },
    }


def _attention(
    operations: Mapping[str, Any] | None,
    task_only_rows: Sequence[Mapping[str, Any]],
    source_health: Sequence[Mapping[str, Any]],
    observed_at: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if operations:
        records_by_target: dict[str, dict[str, Mapping[str, Any]]] = {}
        for run in operations.get("runs", []):
            if not isinstance(run, Mapping):
                continue
            records: dict[str, Mapping[str, Any]] = {}
            for family in ("incidents", "decisions", "successor_transitions"):
                for record in run.get(family, []):
                    if not isinstance(record, Mapping):
                        continue
                    head = record.get("head")
                    record_id = head.get("record_id") if isinstance(head, Mapping) else None
                    if record_id:
                        records[str(record_id)] = record
            records_by_target[str(run.get("target_thread_id"))] = records
        for raw in operations.get("attention", []):
            if not isinstance(raw, Mapping):
                continue
            owner_record = records_by_target.get(
                str(raw.get("target_thread_id")), {}
            ).get(str(raw.get("source_record_id")))
            items.append(
                {
                    "id": f"attention:{raw.get('target_thread_id')}:{raw.get('rule')}:{raw.get('source_record_id')}",
                    "rank": int(raw.get("rank", len(items) + 1)),
                    "rule": raw.get("rule"),
                    "severity": raw.get("severity")
                    if raw.get("severity") in {"red", "amber", "neutral"}
                    else "neutral",
                    "target_thread_id": raw.get("target_thread_id"),
                    "project_id": None,
                    "reason": raw.get("detail"),
                    "owner": raw.get("source_identity"),
                    "safe_frontier": (
                        owner_record.get("safe_frontier")
                        if isinstance(owner_record, Mapping)
                        else None
                    ),
                    "observed_at": raw.get("observed_at"),
                    "source": {
                        "identity": raw.get("source_identity"),
                        "record_id": raw.get("source_record_id"),
                        "path": raw.get("source_path"),
                        "line": raw.get("source_line"),
                        "route": f"/?inspect=attention:{raw.get('target_thread_id')}:{raw.get('source_record_id')}",
                    },
                }
            )
        next_rank = max((int(item["rank"]) for item in items), default=0) + 1
        for raw in operations.get("orphan_automations", []):
            if not isinstance(raw, Mapping):
                continue
            automation_id = raw.get("id") or raw.get("automation_id") or "unknown"
            items.append(
                {
                    "id": f"attention:orphan-automation:{automation_id}",
                    "rank": next_rank,
                    "rule": "orphan-supervisor-automation",
                    "severity": "amber",
                    "target_thread_id": raw.get("target_thread_id"),
                    "project_id": None,
                    "reason": "A supervisor automation is not referenced by a current role binding.",
                    "owner": "codex-automation/manifest",
                    "safe_frontier": "Inspect the manifest and current role bindings before acting.",
                    "observed_at": raw.get("observed_at") or observed_at,
                    "source": {
                        "identity": "codex-automation/manifest",
                        "record_id": automation_id,
                        "path": raw.get("path"),
                        "line": None,
                        "route": f"/?inspect=automation:{automation_id}",
                    },
                }
            )
            next_rank += 1
        for raw in operations.get("unmonitored_projects", []):
            if not isinstance(raw, Mapping):
                continue
            project_id = raw.get("project_id")
            items.append(
                {
                    "id": f"attention:unmonitored-project:{project_id}",
                    "rank": next_rank,
                    "rule": "unmonitored-project",
                    "severity": "neutral",
                    "target_thread_id": None,
                    "project_id": project_id,
                    "reason": raw.get("reason"),
                    "owner": "supervise-tracker-runs/project-binding",
                    "safe_frontier": None,
                    "observed_at": observed_at,
                    "source": {
                        "identity": "supervise-tracker-runs/project-binding",
                        "record_id": project_id,
                        "path": None,
                        "line": None,
                        "route": f"/?inspect=project:{project_id}",
                    },
                }
            )
            next_rank += 1
    next_rank = max((int(item["rank"]) for item in items), default=0) + 1
    for row in task_only_rows:
        items.append(
            {
                "id": f"attention:unmonitored:{row['implementation']['task_id']}",
                "rank": next_rank,
                "rule": "unmonitored-implementation",
                "severity": "neutral",
                "target_thread_id": row["implementation"]["task_id"],
                "project_id": row["project"]["project_id"],
                "reason": "A current or recently active task has no exact supervision run.",
                "owner": "codex-app-server/task-state",
                "safe_frontier": None,
                "observed_at": row["freshness"]["observed_at"],
                "source": {
                    "identity": "codex-app-server/task-state",
                    "record_id": row["implementation"]["task_id"],
                    "path": None,
                    "line": None,
                    "route": row["detail"]["route"],
                },
            }
        )
        next_rank += 1
    for source in source_health:
        if source.get("status") == "available":
            continue
        items.append(
            {
                "id": f"attention:source:{source.get('family')}",
                "rank": next_rank,
                "rule": "source-partial-or-unavailable",
                "severity": "neutral",
                "target_thread_id": None,
                "project_id": None,
                "reason": source.get("reason"),
                "owner": source.get("identity"),
                "safe_frontier": None,
                "observed_at": source.get("observed_at") or observed_at,
                "source": {
                    "identity": source.get("identity"),
                    "record_id": None,
                    "path": None,
                    "line": None,
                    "route": f"/?inspect=source:{source.get('family')}",
                },
            }
        )
        next_rank += 1
    return sorted(items, key=lambda item: (int(item["rank"]), str(item["id"])))[:MAX_ATTENTION]


def _conclusions(operations: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for run in operations.get("runs", []) if operations else []:
        if not isinstance(run, Mapping):
            continue
        for record in run.get("conclusions", []):
            if not isinstance(record, Mapping):
                continue
            source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
            items.append(
                {
                    "id": f"conclusion:{run.get('target_thread_id')}:{record.get('record_id')}",
                    "target_thread_id": run.get("target_thread_id"),
                    "target_label": run.get("target_label"),
                    "author": None,
                    "author_status": "unavailable",
                    "disposition": record.get("status") or record.get("phase"),
                    "summary": record.get("summary"),
                    "next_action": record.get("action"),
                    "current": True,
                    "superseded": False,
                    "observed_at": record.get("timestamp"),
                    "source": {
                        "identity": "supervise-tracker-runs/events.jsonl",
                        "record_id": record.get("record_id"),
                        "path": source.get("path"),
                        "line": source.get("line"),
                        "revision": record.get("record_sha256"),
                        "route": f"/?inspect=conclusion:{run.get('target_thread_id')}:{record.get('record_id')}",
                    },
                    "retained_open_work": sum(
                        int(run.get("counts", {}).get(key, 0))
                        for key in (
                            "open_incidents",
                            "open_decisions",
                            "open_successor_transitions",
                        )
                    )
                    if isinstance(run.get("counts"), Mapping)
                    else None,
                }
            )
    items.sort(key=lambda item: _timestamp(item.get("observed_at")) or datetime.min.replace(tzinfo=UTC), reverse=True)
    return items[:MAX_CONCLUSIONS]


def _outcomes(trackers: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for tracker in trackers:
        if tracker.get("status") != "available":
            continue
        blocks = tracker.get("blocks")
        for block in blocks if isinstance(blocks, list) else []:
            if not isinstance(block, Mapping) or block.get("status") != "accepted":
                continue
            completion = block.get("completion_evidence")
            git = tracker.get("git") if isinstance(tracker.get("git"), Mapping) else {}
            counts = tracker.get("counts") if isinstance(tracker.get("counts"), Mapping) else {}
            items.append(
                {
                    "id": f"outcome:{tracker.get('id')}:{block.get('number')}",
                    "project_id": tracker.get("project_id"),
                    "tracker_id": tracker.get("id"),
                    "tracker_title": tracker.get("title"),
                    "block": block.get("number"),
                    "title": block.get("title"),
                    "status": "accepted",
                    "evidence_revision": tracker.get("fingerprint"),
                    "accepted_at": None,
                    "observed_at": tracker.get("observed_at"),
                    "currentness": (
                        "current"
                        if git.get("status") == "available"
                        and git.get("content_matches_head") is True
                        and not git.get("worktree_changed")
                        else "stale-or-dirty"
                    ),
                    "retained_open_work": counts.get("open"),
                    "source": {
                        "identity": tracker.get("source", {}).get("identity")
                        if isinstance(tracker.get("source"), Mapping)
                        else tracker.get("id"),
                        "record_id": None,
                        "path": tracker.get("raw_file", {}).get("path")
                        if isinstance(tracker.get("raw_file"), Mapping)
                        else tracker.get("relative_path"),
                        "line": completion.get("line")
                        if isinstance(completion, Mapping)
                        else block.get("line"),
                        "revision": tracker.get("fingerprint"),
                        "route": f"/?inspect=outcome:{tracker.get('id')}:{block.get('number')}",
                    },
                }
            )
    items.sort(
        key=lambda item: (
            _timestamp(item.get("observed_at")) or datetime.min.replace(tzinfo=UTC),
            int(item.get("block") or -1),
        ),
        reverse=True,
    )
    return items[:MAX_OUTCOMES]


def _metric(
    key: str,
    label: str,
    value: int | float | None,
    *,
    unit: str,
    period: str,
    coverage: str,
    source: str,
    estimate: bool = False,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": value,
        "unit": unit,
        "period": period,
        "coverage": coverage,
        "source_identity": source,
        "estimate": estimate,
        "available": value is not None,
    }


def compose_factory_floor(
    *,
    projects: Sequence[Mapping[str, Any]],
    operations: Mapping[str, Any] | None,
    trackers: Sequence[Mapping[str, Any]],
    task_data: Mapping[str, Any] | None,
    source_health: Sequence[Mapping[str, Any]],
    observed_at: str,
) -> dict[str, Any]:
    project_labels = {str(project["id"]): str(project["label"]) for project in projects}
    tasks = [
        task
        for task in (task_data.get("tasks", []) if task_data else [])
        if isinstance(task, Mapping)
    ]
    tasks_by_id = {str(task["id"]): task for task in tasks}
    trackers_by_project: dict[str, list[Mapping[str, Any]]] = {}
    for tracker in trackers:
        project_id = tracker.get("project_id")
        if project_id:
            trackers_by_project.setdefault(str(project_id), []).append(tracker)
    rows: list[dict[str, Any]] = []
    matched_tasks: set[str] = set()
    for run in operations.get("runs", []) if operations else []:
        if not isinstance(run, Mapping):
            continue
        target_id = str(run.get("target_thread_id"))
        task = tasks_by_id.get(target_id)
        if task:
            matched_tasks.add(target_id)
        rows.append(
            _row(
                run=run,
                task=task,
                project_labels=project_labels,
                trackers_by_project=trackers_by_project,
                tasks_by_id=tasks_by_id,
                observed_at=observed_at,
            )
        )
    task_only: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task.get("id"))
        if task_id in matched_tasks or not _task_is_recent(task, observed_at):
            continue
        binding = task.get("project_binding")
        if not isinstance(binding, Mapping) or binding.get("status") != "bound":
            continue
        task_only.append(
            _row(
                run=None,
                task=task,
                project_labels=project_labels,
                trackers_by_project=trackers_by_project,
                tasks_by_id=tasks_by_id,
                observed_at=observed_at,
            )
        )
    task_only.sort(
        key=lambda row: _timestamp(row["freshness"]["observed_at"])
        or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    rows.extend(task_only[:MAX_TASK_ONLY_ROWS])
    posture_order = {"red": 0, "amber": 1, "green": 2, "neutral": 3}
    rows.sort(
        key=lambda row: (
            posture_order.get(row["light"]["posture"], 4),
            str(row["project"]["label"]),
            str(row["id"]),
        )
    )
    row_count = len(rows)
    rows = rows[:MAX_FLOOR_ROWS]
    posture_counts = Counter(row["light"]["posture"] for row in rows)
    conclusions = _conclusions(operations)
    outcomes = _outcomes(trackers)
    attention = _attention(operations, task_only[:MAX_TASK_ONLY_ROWS], source_health, observed_at)
    run_count = len(operations.get("runs", [])) if operations else None
    active_tasks = sum(1 for row in rows if row["implementation"]["status"] == "active")
    active_implementations = sum(
        1
        for row in rows
        if row["implementation"]["status"] == "active"
        or row["supervision"]["status"] == "active"
    )
    active_projects = len(
        {
            row["project"]["project_id"]
            for row in rows
            if row["project"]["project_id"]
            and (
                row["implementation"]["status"] in {"active", "idle"}
                or row["supervision"]["status"] == "active"
            )
        }
    )
    degraded_groups = sum(
        1
        for row in rows
        if row["supervision"]["run_id"]
        and row["supervision"]["binding_integrity"] != "valid"
    )
    open_issues = sum(int(row["issues"]["total"]) for row in rows)
    accepted_blocks = sum(
        int(tracker.get("counts", {}).get("accepted", 0))
        for tracker in trackers
        if isinstance(tracker.get("counts"), Mapping)
    )
    tracker_status_counts = Counter(
        block.get("status")
        for tracker in trackers
        if tracker.get("status") == "available"
        for block in (
            tracker.get("blocks") if isinstance(tracker.get("blocks"), list) else []
        )
        if isinstance(block, Mapping) and isinstance(block.get("status"), str)
    )
    orphaned_supervisors = (
        len(operations.get("orphan_automations", [])) if operations else None
    )
    unmonitored_implementations = sum(
        1 for row in rows if row["supervision"]["status"] == "unmonitored"
    )
    incident_count = sum(int(row["issues"]["incidents"]) for row in rows)
    decision_count = sum(int(row["issues"]["decisions"]) for row in rows)
    transition_count = sum(int(row["issues"]["transitions"]) for row in rows)
    aggregate = operations.get("metrics", {}).get("aggregate") if operations else None
    aggregate = aggregate if isinstance(aggregate, Mapping) else {}
    per_run = operations.get("metrics", {}).get("per_run") if operations else None
    checks = 0
    checks_available = False
    for item in per_run if isinstance(per_run, list) else []:
        metrics = item.get("metrics") if isinstance(item, Mapping) else None
        counts = metrics.get("counts") if isinstance(metrics, Mapping) else None
        by_kind = counts.get("by_kind") if isinstance(counts, Mapping) else None
        if isinstance(by_kind, Mapping):
            checks += int(by_kind.get("check", 0))
            checks_available = True
    estimate = aggregate.get("api_equivalent_estimate")
    totals = estimate.get("totals") if isinstance(estimate, Mapping) else None
    cost = totals.get("projected_cost_usd_base") if isinstance(totals, Mapping) else None
    metrics = [
        _metric(
            "active-projects",
            "Active projects",
            active_projects,
            unit="count",
            period="Current task/run page",
            coverage=f"{len(projects)} registered projects",
            source="factory-floor/exact-bindings",
        ),
        _metric(
            "unmonitored-implementations",
            "Unmonitored implementations",
            unmonitored_implementations if task_data else None,
            unit="count",
            period="Current task/run page",
            coverage="Recent registered-project tasks without an exact run",
            source="factory-floor/task-run-join",
        ),
        _metric(
            "active-tasks",
            "Active tasks",
            active_tasks if task_data else None,
            unit="count",
            period="Current App Server page",
            coverage=f"{len(tasks)} bounded tasks" if task_data else "Task source unavailable",
            source="codex-app-server/task-list",
        ),
        _metric(
            "active-implementations",
            "Active implementations",
            active_implementations if operations or task_data else None,
            unit="count",
            period="Current task/run page",
            coverage="Active task rows or current active supervision targets",
            source="factory-floor/task-run-join",
        ),
        _metric(
            "orphaned-supervisors",
            "Orphaned supervisors",
            orphaned_supervisors,
            unit="count",
            period="Current automation inventory",
            coverage="Unreferenced maintained automation manifests",
            source="supervise-tracker-runs/automation-inventory",
        ),
        _metric(
            "supervision-runs",
            "Supervision runs",
            run_count,
            unit="count",
            period="Current missions",
            coverage=f"{run_count} projected runs" if run_count is not None else "Run source unavailable",
            source="supervise-tracker-runs",
        ),
        _metric(
            "blocks-in-progress",
            "Blocks in progress",
            int(tracker_status_counts.get("in-progress", 0)) if trackers else None,
            unit="count",
            period="Current tracker sources",
            coverage=f"{len(trackers)} projected trackers",
            source="tracker-markdown/status",
        ),
        _metric(
            "blocks-not-started",
            "Blocks not started",
            int(tracker_status_counts.get("not-started", 0)) if trackers else None,
            unit="count",
            period="Current tracker sources",
            coverage=f"{len(trackers)} projected trackers",
            source="tracker-markdown/status",
        ),
        _metric(
            "degraded-groups",
            "Degraded groups",
            degraded_groups if operations else None,
            unit="count",
            period="Current missions",
            coverage="Exact role/task/automation bindings",
            source="supervise-tracker-runs/topology",
        ),
        _metric(
            "open-incidents",
            "Open incidents",
            incident_count if operations else None,
            unit="count",
            period="Current missions",
            coverage="Current mission incident heads",
            source="supervise-tracker-runs/incidents",
        ),
        _metric(
            "open-decisions",
            "Open decisions",
            decision_count if operations else None,
            unit="count",
            period="Current missions",
            coverage="Current mission decision heads",
            source="supervise-tracker-runs/decisions",
        ),
        _metric(
            "open-transitions",
            "Open transitions",
            transition_count if operations else None,
            unit="count",
            period="Current missions",
            coverage="Current mission successor-transition heads",
            source="supervise-tracker-runs/successor-transitions",
        ),
        _metric(
            "semantic-conclusions",
            "Current conclusions",
            len(conclusions) if operations else None,
            unit="count",
            period="Current missions, bounded",
            coverage=f"Newest {MAX_CONCLUSIONS} semantic owner records",
            source="supervise-tracker-runs/conclusion-classifier",
        ),
        _metric(
            "accepted-blocks",
            "Accepted Blocks",
            accepted_blocks if trackers else None,
            unit="count",
            period="Current tracker sources",
            coverage=f"{len(trackers)} projected trackers",
            source="tracker-markdown/status",
        ),
        _metric(
            "open-items",
            "Open issues",
            open_issues if operations else None,
            unit="count",
            period="Current missions",
            coverage="Incidents, decisions, transitions",
            source="supervise-tracker-runs/heads",
        ),
        _metric(
            "supervisor-checks",
            "Supervisor checks",
            checks if checks_available else None,
            unit="count",
            period="Active mission report periods",
            coverage=f"{aggregate.get('available_run_count', 0)} runs with metrics",
            source="weekly-report/metrics",
        ),
        _metric(
            "api-equivalent",
            "API-equivalent estimate",
            round(float(cost), 2) if isinstance(cost, (int, float)) else None,
            unit="USD estimate",
            period="Active mission report periods",
            coverage=(
                f"{estimate.get('coverage_run_count', 0)} runs"
                if isinstance(estimate, Mapping)
                else "Cost projection unavailable"
            ),
            source="weekly-report/api-equivalent-estimate",
            estimate=True,
        ),
    ]
    return {
        "summary": {
            "registered_projects": len(projects),
            "active_implementations": (
                active_implementations if operations or task_data else None
            ),
            "supervisor_groups": run_count,
            "action_required": sum(
                1 for item in attention if item["severity"] in {"red", "amber"}
            ),
            "postures": {
                posture: int(posture_counts.get(posture, 0))
                for posture in ("red", "amber", "green", "neutral")
            },
        },
        "projects": [
            {"id": project.get("id"), "label": project.get("label")}
            for project in projects
        ],
        "rows": rows,
        "rows_truncated": row_count > MAX_FLOOR_ROWS,
        "attention": attention,
        "conclusions": conclusions,
        "accepted_outcomes": outcomes,
        "metrics": metrics,
        "source_health": list(source_health),
        "fingerprint": _digest(
            {
                "projects": [project.get("id") for project in projects],
                "operations": operations.get("fingerprint") if operations else None,
                "trackers": [tracker.get("fingerprint") for tracker in trackers],
                "tasks": [task.get("id") for task in tasks],
                "sources": source_health,
            }
        ),
    }
