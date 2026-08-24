from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import secrets
import smtplib
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol

from .errors import InvalidTransition, StoreError
from .store import Store
from .util import new_id, utc_now


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _ids(values: Sequence[str] | None) -> list[str]:
    return sorted({str(value) for value in (values or ()) if str(value)})


def _loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


def _parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _markdown(value: Any, *, depth: int = 1) -> str:
    if isinstance(value, Mapping):
        lines: list[str] = []
        for key, item in value.items():
            title = str(key).replace("_", " ").strip().title()
            if isinstance(item, (Mapping, list)):
                lines.append(f"{'#' * min(depth, 6)} {title}\n")
                lines.append(_markdown(item, depth=depth + 1))
            else:
                lines.append(f"- **{title}:** {item}")
        return "\n".join(lines).strip() + "\n"
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (Mapping, list)):
                lines.append(_markdown(item, depth=depth))
            else:
                lines.append(f"- {item}")
        return "\n".join(lines).strip() + "\n"
    return f"{value}\n"


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_text_pdf(path: Path, text: str, *, title: str) -> None:
    """Write a deterministic, dependency-free text PDF with pagination."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        current = raw
        while len(current) > 92:
            lines.append(current[:92])
            current = current[92:]
        lines.append(current)
    per_page = 48
    pages = [lines[index : index + per_page] for index in range(0, len(lines), per_page)] or [[]]
    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 3
    next_id = 4
    content_ids: list[int] = []
    for _ in pages:
        page_ids.append(next_id)
        content_ids.append(next_id + 1)
        next_id += 2
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for _page_id, content_id, page_lines in zip(page_ids, content_ids, pages, strict=True):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        commands = ["BT", "/F1 10 Tf", "48 744 Td", "12 TL"]
        commands.append(f"({_pdf_escape(title)}) Tj")
        commands.append("T*")
        commands.append("T*")
        for line in page_lines:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", "replace")
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    path.write_bytes(output)


class NotificationAdapter(Protocol):
    def send(self, notification: Mapping[str, Any]) -> Mapping[str, Any]: ...


class FileNotificationAdapter:
    def send(self, notification: Mapping[str, Any]) -> Mapping[str, Any]:
        destination = Path(str(notification["destination"])).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "subject": notification["subject"],
            "body": notification["body_text"],
            "attachments": _loads(notification.get("attachment_paths_json"), []),
            "notification_id": notification["id"],
        }
        destination.write_text(_canonical(payload) + "\n", encoding="utf-8")
        return {"provider_message_id": f"file:{destination}", "delivered": True}


class StdoutNotificationAdapter:
    def send(self, notification: Mapping[str, Any]) -> Mapping[str, Any]:
        print(f"{notification['subject']}\n\n{notification['body_text']}")
        return {"provider_message_id": f"stdout:{notification['id']}", "delivered": True}


class WebhookNotificationAdapter:
    def __init__(self, *, timeout_seconds: int = 15):
        self.timeout_seconds = timeout_seconds

    def send(self, notification: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = _canonical(
            {
                "id": notification["id"],
                "subject": notification["subject"],
                "body": notification["body_text"],
                "attachments": _loads(notification.get("attachment_paths_json"), []),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            str(notification["destination"]),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            response_body = response.read(1024 * 1024).decode("utf-8", "replace")
            return {
                "provider_message_id": response.headers.get("X-Request-ID")
                or f"http:{response.status}:{notification['id']}",
                "delivered": 200 <= response.status < 300,
                "status": response.status,
                "body": response_body,
            }


class SMTPNotificationAdapter:
    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        sender: str,
        starttls: bool = True,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self.starttls = starttls

    def send(self, notification: Mapping[str, Any]) -> Mapping[str, Any]:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = str(notification["destination"])
        message["Subject"] = str(notification["subject"])
        message.set_content(str(notification["body_text"]))
        for attachment in _loads(notification.get("attachment_paths_json"), []):
            path = Path(str(attachment)).resolve()
            message.add_attachment(
                path.read_bytes(),
                maintype="application",
                subtype="octet-stream",
                filename=path.name,
            )
        with smtplib.SMTP(self.host, self.port, timeout=30) as client:
            if self.starttls:
                client.starttls()
            if self.username:
                client.login(self.username, self.password or "")
            refused = client.send_message(message)
        return {
            "provider_message_id": message["Message-ID"] or f"smtp:{notification['id']}",
            "delivered": not refused,
            "refused": refused,
        }


class ReportingService:
    def __init__(self, store: Store):
        self.store = store

    def create_schedule(
        self,
        *,
        schedule_type: str,
        specification: Mapping[str, Any],
        action: Mapping[str, Any],
        next_run_at: str | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        if schedule_type not in {"interval", "at", "event"}:
            raise ValueError("unsupported schedule type")
        schedule_id = new_id("schedule")
        now = utc_now()
        if schedule_type == "interval" and not specification.get("seconds"):
            raise ValueError("interval schedule requires seconds")
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO schedules_v2(
                       id,mission_id,schedule_type,specification_json,action_json,
                       next_run_at,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,'active',?,?)""",
                (
                    schedule_id,
                    mission_id,
                    schedule_type,
                    _canonical(dict(specification)),
                    _canonical(dict(action)),
                    next_run_at,
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM schedules_v2 WHERE id=?", (schedule_id,))

    def due_schedules(self, *, now: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        current = now or utc_now()
        return self.store.all(
            """SELECT * FROM schedules_v2
               WHERE status='active' AND next_run_at IS NOT NULL AND next_run_at<=?
               ORDER BY next_run_at,id LIMIT ?""",
            (current, limit),
        )

    def set_schedule_status(
        self,
        schedule_id: str,
        *,
        status: str,
        operator_decision_id: str,
    ) -> dict[str, Any]:
        """Pause or resume a schedule through its authoritative owner."""

        if status not in {"active", "paused"}:
            raise ValueError("operator schedule status must be active or paused")
        with self.store.transaction() as db:
            current = db.execute("SELECT * FROM schedules_v2 WHERE id=?", (schedule_id,)).fetchone()
            if current is None:
                raise StoreError("schedule not found")
            if current["status"] in {"completed", "cancelled"}:
                raise InvalidTransition("terminal schedule cannot be resumed or paused")
            db.execute(
                "UPDATE schedules_v2 SET status=?,updated_at=? WHERE id=?",
                (status, utc_now(), schedule_id),
            )
            self.store.append_event(
                db,
                mission_id=current["mission_id"],
                stream_key="delivery",
                event_type=f"schedule.{status}",
                subject_type="schedule",
                subject_id=schedule_id,
                source_type="operator_decision",
                source_id=operator_decision_id,
                payload={"operator_decision_id": operator_decision_id},
            )
        result = self.store.one("SELECT * FROM schedules_v2 WHERE id=?", (schedule_id,))
        result["operator_decision_id"] = operator_decision_id
        return result

    def mark_schedule_run(
        self,
        schedule_id: str,
        *,
        succeeded: bool,
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        schedule = self.store.one("SELECT * FROM schedules_v2 WHERE id=?", (schedule_id,))
        if schedule["status"] != "active":
            raise InvalidTransition("schedule is not active")
        completed = completed_at or utc_now()
        specification = _loads(schedule["specification_json"], {})
        if not succeeded:
            status = "failed"
            next_run = None
        elif schedule["schedule_type"] == "interval":
            next_run_dt = _parse_time(completed) + dt.timedelta(
                seconds=int(specification["seconds"])
            )
            next_run = next_run_dt.isoformat().replace("+00:00", "Z")
            status = "active"
        else:
            next_run = None
            status = "completed"
        with self.store.transaction() as db:
            db.execute(
                """UPDATE schedules_v2
                   SET last_run_at=?,next_run_at=?,status=?,updated_at=? WHERE id=?""",
                (completed, next_run, status, utc_now(), schedule_id),
            )
        return self.store.one("SELECT * FROM schedules_v2 WHERE id=?", (schedule_id,))

    def generate_report(
        self,
        *,
        report_type: str,
        source_type: str,
        source_id: str,
        content: Mapping[str, Any],
        output_directory: str | Path,
        mission_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        markdown = f"# {title or report_type.replace('_', ' ').title()}\n\n" + _markdown(content)
        content_root = _digest(
            {
                "report_type": report_type,
                "source_type": source_type,
                "source_id": source_id,
                "content": dict(content),
            }
        )
        existing = self.store.one(
            """SELECT * FROM reports_v2
               WHERE report_type=? AND source_type=? AND source_id=? AND content_root=?""",
            (report_type, source_type, source_id, content_root),
            required=False,
        )
        if existing is not None:
            return existing
        report_id = new_id("report")
        output = Path(output_directory).resolve()
        output.mkdir(parents=True, exist_ok=True)
        pdf_path = output / f"{report_id}.pdf"
        write_text_pdf(pdf_path, markdown, title=title or report_type.replace("_", " ").title())
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO reports_v2(
                       id,mission_id,report_type,source_type,source_id,content_root,
                       json_content,markdown_content,pdf_path,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'generated',?,?)""",
                (
                    report_id,
                    mission_id,
                    report_type,
                    source_type,
                    source_id,
                    content_root,
                    _canonical(dict(content)),
                    markdown,
                    str(pdf_path),
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM reports_v2 WHERE id=?", (report_id,))

    def queue_notification(
        self,
        *,
        channel: str,
        destination: str,
        subject: str,
        body_text: str,
        attachment_paths: Sequence[str] | None = None,
        mission_id: str | None = None,
        dedupe_material: Mapping[str, Any] | None = None,
        max_attempts: int = 5,
    ) -> dict[str, Any]:
        if channel not in {"file", "email", "smtp", "webhook", "stdout"}:
            raise ValueError("unsupported notification channel")
        dedupe_key = _digest(
            dict(dedupe_material)
            if dedupe_material is not None
            else {
                "channel": channel,
                "destination": destination,
                "subject": subject,
                "body_text": body_text,
                "attachments": _ids(attachment_paths),
            }
        )
        existing = self.store.one(
            "SELECT * FROM notifications_v2 WHERE dedupe_key=?",
            (dedupe_key,),
            required=False,
        )
        if existing is not None:
            return existing
        notification_id = new_id("notification")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO notifications_v2(
                       id,mission_id,channel,destination,subject,body_text,
                       attachment_paths_json,dedupe_key,status,attempt_count,
                       max_attempts,next_attempt_at,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,'pending',0,?,?,?,?)""",
                (
                    notification_id,
                    mission_id,
                    channel,
                    destination,
                    subject,
                    body_text,
                    _canonical(_ids(attachment_paths)),
                    dedupe_key,
                    max_attempts,
                    now,
                    now,
                    now,
                ),
            )
        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def dispatch_notification(
        self,
        notification_id: str,
        *,
        adapter: NotificationAdapter,
    ) -> dict[str, Any]:
        notification = self.store.one(
            "SELECT * FROM notifications_v2 WHERE id=?", (notification_id,)
        )
        if notification["status"] in {"sent", "delivered", "read"}:
            return notification
        if notification["status"] not in {"pending", "retry", "failed"}:
            raise InvalidTransition("notification is not dispatchable")
        attempt_number = int(notification["attempt_count"]) + 1
        if attempt_number > int(notification["max_attempts"]):
            raise InvalidTransition("notification exhausted its retry budget")
        attempt_id = new_id("notification-attempt")
        request_root = _digest(
            {
                "notification_id": notification_id,
                "attempt_number": attempt_number,
                "destination": notification["destination"],
                "subject": notification["subject"],
                "body": notification["body_text"],
                "attachments": _loads(notification["attachment_paths_json"], []),
            }
        )
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO notification_attempts_v2(
                       id,notification_id,attempt_number,request_root,status,started_at
                   ) VALUES(?,?,?,?, 'sending',?)""",
                (attempt_id, notification_id, attempt_number, request_root, now),
            )
            db.execute(
                """UPDATE notifications_v2
                   SET status='sending',attempt_count=?,updated_at=? WHERE id=?""",
                (attempt_number, now, notification_id),
            )
        try:
            response = dict(adapter.send(notification))
            delivered = bool(response.get("delivered", True))
            status = "delivered" if delivered else "sent"
            attempt_status = "sent"
            next_attempt = None
        except BaseException as exc:
            response = {"error": str(exc)}
            attempt_status = "failed"
            if attempt_number >= int(notification["max_attempts"]):
                status = "failed"
                next_attempt = None
            else:
                status = "retry"
                next_dt = dt.datetime.now(dt.UTC) + dt.timedelta(
                    seconds=min(3600, 2**attempt_number * 15)
                )
                next_attempt = next_dt.isoformat().replace("+00:00", "Z")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE notification_attempts_v2
                   SET status=?,response_json=?,completed_at=? WHERE id=?""",
                (attempt_status, _canonical(response), utc_now(), attempt_id),
            )
            db.execute(
                """UPDATE notifications_v2
                   SET status=?,next_attempt_at=?,provider_message_id=?,updated_at=? WHERE id=?""",
                (
                    status,
                    next_attempt,
                    response.get("provider_message_id"),
                    utc_now(),
                    notification_id,
                ),
            )
        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def record_readback(
        self,
        notification_id: str,
        *,
        readback: Mapping[str, Any],
    ) -> dict[str, Any]:
        notification = self.store.one(
            "SELECT * FROM notifications_v2 WHERE id=?", (notification_id,)
        )
        if notification["status"] not in {"sent", "delivered", "read"}:
            raise InvalidTransition("notification has not been delivered")
        with self.store.transaction() as db:
            db.execute(
                """UPDATE notifications_v2
                   SET status='read',readback_json=?,updated_at=? WHERE id=?""",
                (_canonical(dict(readback)), utc_now(), notification_id),
            )
        return self.store.one("SELECT * FROM notifications_v2 WHERE id=?", (notification_id,))

    def issue_operator_token(
        self,
        *,
        allowed_actions: Sequence[str],
        scope: Mapping[str, Any],
        expires_at: str,
        mission_id: str | None = None,
        max_uses: int = 1,
    ) -> tuple[str, dict[str, Any]]:
        if _parse_time(expires_at) <= dt.datetime.now(dt.UTC):
            raise ValueError("operator token cannot be created expired")
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        token_id = new_id("operator-token")
        now = utc_now()
        with self.store.transaction() as db:
            db.execute(
                """INSERT INTO operator_action_tokens_v2(
                       id,mission_id,token_hash,allowed_actions_json,scope_json,
                       expires_at,max_uses,use_count,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,0,'active',?,?)""",
                (
                    token_id,
                    mission_id,
                    token_hash,
                    _canonical(_ids(allowed_actions)),
                    _canonical(dict(scope)),
                    expires_at,
                    max_uses,
                    now,
                    now,
                ),
            )
        return raw, self.store.one(
            "SELECT * FROM operator_action_tokens_v2 WHERE id=?", (token_id,)
        )

    def accept_operator_action(
        self,
        raw_token: str,
        *,
        action: str,
        target_type: str,
        target_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        candidates = self.store.all("SELECT * FROM operator_action_tokens_v2 WHERE status='active'")
        token = next(
            (row for row in candidates if hmac.compare_digest(str(row["token_hash"]), token_hash)),
            None,
        )
        if token is None:
            raise StoreError("operator token is invalid")
        if _parse_time(token["expires_at"]) <= dt.datetime.now(dt.UTC):
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE operator_action_tokens_v2 SET status='expired',updated_at=? WHERE id=?",
                    (utc_now(), token["id"]),
                )
            raise StoreError("operator token is expired")
        if action not in _loads(token["allowed_actions_json"], []):
            raise StoreError("operator token does not authorize this action")
        scope = _loads(token["scope_json"], {})
        if scope.get("target_type") not in (None, target_type):
            raise StoreError("operator action target type is outside token scope")
        allowed_ids = scope.get("target_ids")
        if isinstance(allowed_ids, list) and target_id not in allowed_ids:
            raise StoreError("operator action target is outside token scope")
        request = {
            "token_id": token["id"],
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "payload": dict(payload or {}),
        }
        request_root = _digest(request)
        existing = self.store.one(
            """SELECT * FROM operator_decisions_v2
               WHERE token_id=? AND request_root=?""",
            (token["id"], request_root),
            required=False,
        )
        if existing is not None:
            return existing
        decision_id = new_id("operator-decision")
        now = utc_now()
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT * FROM operator_action_tokens_v2 WHERE id=?", (token["id"],)
            ).fetchone()
            if current is None or current["status"] != "active":
                raise InvalidTransition("operator token was consumed concurrently")
            if int(current["use_count"]) >= int(current["max_uses"]):
                raise InvalidTransition("operator token has exhausted its uses")
            db.execute(
                """INSERT INTO operator_decisions_v2(
                       id,mission_id,token_id,action,target_type,target_id,payload_json,
                       request_root,status,created_at
                   ) VALUES(?,?,?,?,?,?,?,?,'accepted',?)""",
                (
                    decision_id,
                    token["mission_id"],
                    token["id"],
                    action,
                    target_type,
                    target_id,
                    _canonical(dict(payload or {})),
                    request_root,
                    now,
                ),
            )
            use_count = int(current["use_count"]) + 1
            db.execute(
                """UPDATE operator_action_tokens_v2
                   SET use_count=?,status=?,updated_at=? WHERE id=?""",
                (
                    use_count,
                    "consumed" if use_count >= int(current["max_uses"]) else "active",
                    now,
                    token["id"],
                ),
            )
        return self.store.one("SELECT * FROM operator_decisions_v2 WHERE id=?", (decision_id,))

    def apply_operator_decision(
        self,
        decision_id: str,
        *,
        handler: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> dict[str, Any]:
        try:
            with self.store.transaction() as db:
                row = db.execute(
                    "SELECT * FROM operator_decisions_v2 WHERE id=?", (decision_id,)
                ).fetchone()
                if row is None:
                    raise StoreError("operator decision not found")
                decision = dict(row)
                if decision["status"] == "applied":
                    return decision
                if decision["status"] != "accepted":
                    raise InvalidTransition("operator decision is not applicable")
                result = dict(handler(decision))
                db.execute(
                    """UPDATE operator_decisions_v2
                       SET status='applied',result_json=?,applied_at=? WHERE id=?""",
                    (_canonical(result), utc_now(), decision_id),
                )
        except BaseException as exc:
            result = {"error": str(exc)}
            with self.store.transaction() as db:
                db.execute(
                    """UPDATE operator_decisions_v2
                       SET status='failed',result_json=?,applied_at=?
                       WHERE id=? AND status='accepted'""",
                    (_canonical(result), utc_now(), decision_id),
                )
            if isinstance(exc, (InvalidTransition, StoreError)):
                raise
            raise RuntimeError(str(exc)) from exc
        return self.store.one("SELECT * FROM operator_decisions_v2 WHERE id=?", (decision_id,))

    def terminal_delivery_ready(self, mission_id: str) -> bool:
        terminal = self.store.one(
            """SELECT id,status FROM reports_v2
               WHERE mission_id=? AND report_type='terminal'
               ORDER BY created_at DESC LIMIT 1""",
            (mission_id,),
            required=False,
        )
        if terminal is None or terminal["status"] not in {"delivered", "read"}:
            return False
        pending = self.store.one(
            """SELECT id FROM notifications_v2
               WHERE mission_id=? AND status IN ('pending','sending','retry') LIMIT 1""",
            (mission_id,),
            required=False,
        )
        return pending is None
