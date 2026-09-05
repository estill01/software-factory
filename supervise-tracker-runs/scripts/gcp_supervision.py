#!/usr/bin/env python3
"""GCP-owned schedules and delivery for one existing supervision group.

Codex owns tasks; supervision_log.py owns semantic policy/evidence; this service
owns only recurring wake state and transport receipts. It uses no desktop RPC.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import uuid

from gcp_codex_transport import CodexClient, RpcError, TransportError

DEFAULT_CONFIG = "/srv/patent-studio/private/gcp-supervision/config.json"
TERMINAL_DELIVERY = {"started", "acknowledged"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@contextlib.contextmanager
def locked(path):
    with open(path, "a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


class Runtime:
    def __init__(self, config_path=DEFAULT_CONFIG, *, client_factory=CodexClient):
        self.config_path = Path(config_path)
        self.config = json.loads(self.config_path.read_text())
        if self.config.get("schema_version") != 1:
            raise ValueError("unsupported runtime configuration")
        self.target = self.config["target_thread_id"]
        self.root = Path(self.config["state_root"])
        self.client_factory = client_factory
        if not self.root.is_absolute() or not self.root.is_dir():
            raise ValueError("existing absolute state root required")
        role_ids = [role["thread_id"] for role in self.config["roles"].values()]
        if len(set(role_ids + [self.target])) != len(role_ids) + 1:
            raise ValueError("roles and target must be distinct")
        self.db = sqlite3.connect(self.root / "runtime.sqlite3", timeout=5,
                                  isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS schedules (
          id TEXT PRIMARY KEY, role TEXT NOT NULL UNIQUE,
          interval_seconds INTEGER NOT NULL CHECK(interval_seconds > 0),
          enabled INTEGER NOT NULL, next_due REAL NOT NULL,
          created_at REAL NOT NULL, updated_at REAL NOT NULL,
          last_delivery TEXT, last_started_at REAL);
        CREATE TABLE IF NOT EXISTS deliveries (
          id TEXT PRIMARY KEY, recipient TEXT NOT NULL, message TEXT NOT NULL,
          message_sha256 TEXT NOT NULL, source TEXT NOT NULL, purpose TEXT NOT NULL,
          schedule_id TEXT, scheduled_for REAL,
          state TEXT NOT NULL, queue_id TEXT, turn_id TEXT,
          created_at REAL NOT NULL, updated_at REAL NOT NULL, error TEXT);
        CREATE TABLE IF NOT EXISTS health (
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT NULL);
        """)

    def close(self):
        self.db.close()

    def client(self):
        return self.client_factory(self.config["socket_path"], timeout=20)

    def helper(self, arguments):
        command = [sys.executable, self.config["helper_path"], "--root",
                   self.config["supervision_root"], *arguments]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=45)
        if proc.returncode:
            raise RuntimeError(f"supervision helper rejected {arguments[0]}: {(proc.stdout or proc.stderr)[:1000]}")
        if "--help" in arguments:
            return {"help": proc.stdout}
        return json.loads(proc.stdout)

    def add_schedule(self, role, interval, *, first_due=None):
        if role not in ("liveness", "watcher", "reviewer"):
            raise ValueError("only maintained scheduled roles are eligible")
        schedule_id = "gcp-" + str(uuid.uuid5(uuid.NAMESPACE_URL, self.target+":"+role))
        now = time.time()
        self.db.execute("""INSERT OR IGNORE INTO schedules
          (id,role,interval_seconds,enabled,next_due,created_at,updated_at)
          VALUES (?,?,?,0,?,?,?)""",
          (schedule_id, role, interval, first_due if first_due is not None else now, now, now))
        row = self.db.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
        if row["interval_seconds"] != interval or row["role"] != role:
            raise ValueError("existing schedule conflicts with requested binding")
        return schedule_id

    def schedule_state(self, enabled):
        if enabled and self.config.get("bootstrap"):
            if self.config["bootstrap"].get("phase") != "ready":
                raise ValueError("bootstrap must be ready before schedule activation")
            self.verify_bindings()
        self.db.execute("UPDATE schedules SET enabled=?, updated_at=?", (int(enabled), time.time()))

    def verify_bindings(self):
        """Verify semantic owner bindings against the actual isolated schedule owner."""
        from supervision_runtime import ROLES, INTERVALS, initialized
        if set(self.config["roles"]) != set(ROLES):
            raise ValueError("exactly five maintained native roles required")
        policy = self.helper(["status", "--target-thread", self.target])["policy"]
        if policy["target_thread_id"] != self.target:
            raise ValueError("semantic owner target mismatch")
        binding = policy["runtime"]
        for name, (model, effort) in ROLES.items():
            role = self.config["roles"][name]
            if (binding.get(name+"_thread_id") != role["thread_id"] or
                    (role["model"], role["reasoning"]) != (model, effort) or
                    not role.get("durable_init_turn") or not role.get("role_init_turn")):
                raise ValueError("missing initialization or divergent role binding: "+name)
        schedules = {row["role"]: row for row in self.db.execute("SELECT * FROM schedules")}
        if set(schedules) != set(INTERVALS):
            raise ValueError("exactly three maintained native schedules required")
        keys = {"liveness": "liveness", "watcher": "routine", "reviewer": "meta"}
        for name, interval in INTERVALS.items():
            row = schedules[name]
            if row["interval_seconds"] != interval or binding.get(keys[name]+"_automation_id") != row["id"]:
                raise ValueError("schedule and policy binding disagree: "+name)
        mission = policy["mission_binding"]
        expected = self.helper(["mission-plan", "--target-thread", self.target,
            "--mission-source-class", self.config["mission_source_class"],
            "--mission-source-record", self.config["mission_source_record"],
            "--mission-source-sha256", self.config["mission_source_sha256"]])["mission_binding"]
        if (mission.get("mission_root") != expected["mission_root"] or
                mission.get("mission_source_record") != expected["mission_source_record"] or
                mission.get("mission_derivation") != expected["mission_derivation"]):
            raise ValueError("mission source binding changed; reconcile before activating")
        if not self.config["bootstrap"].get("initialization_verified_at"):
            with self.client() as client:
                for name, role in self.config["roles"].items():
                    turns = client.turns(role["thread_id"], limit=4).get("data", [])
                    for key in ("durable_init_turn", "role_init_turn"):
                        if not any(t["id"] == role[key] and initialized(t) for t in turns):
                            raise ValueError("native initialization proof unavailable: "+name)
            # This receipt is transport evidence, not semantic acceptance.
            from supervision_runtime import save
            self.config["bootstrap"]["initialization_verified_at"] = time.time()
            save(self.config_path, self.config)
        return {"verified": True, "target_thread_id": self.target}

    def compact(self, thread_id):
        self.require_recipient(thread_id)
        with self.client() as client:
            return client.compact(thread_id)

    def direct_turns(self, thread_id, limit):
        self.require_recipient(thread_id)
        with self.client() as client:
            return client.turns(thread_id, limit=limit)

    def require_recipient(self, thread_id):
        allowed = {self.target} | {r["thread_id"] for r in self.config["roles"].values()}
        if thread_id not in allowed:
            raise ValueError("task is outside this exact supervision group")

    def prepare(self, key, recipient, message, source, purpose,
                *, schedule_id=None, scheduled_for=None):
        self.require_recipient(recipient)
        if not message.strip() or len(message.encode()) > 16000:
            raise ValueError("empty or oversized delivery")
        delivery_id = str(uuid.uuid5(uuid.NAMESPACE_URL, self.target+":"+key))
        now = time.time()
        self.db.execute("""INSERT OR IGNORE INTO deliveries
          (id,recipient,message,message_sha256,source,purpose,schedule_id,scheduled_for,
           state,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?, 'prepared',?,?)""",
          (delivery_id, recipient, message, digest(message), source, purpose,
           schedule_id, scheduled_for, now, now))
        row = self.db.execute("SELECT * FROM deliveries WHERE id=?", (delivery_id,)).fetchone()
        if (row["recipient"], row["message_sha256"], row["source"], row["purpose"]) != (
                recipient, digest(message), source, purpose):
            raise ValueError("delivery identity already binds different content")
        return delivery_id

    def update_delivery(self, identity, state, **values):
        if set(values) - {"queue_id", "turn_id", "error"}:
            raise ValueError("unsupported delivery field")
        values |= {"state": state, "updated_at": time.time()}
        sql = ",".join(key+"=?" for key in values)
        self.db.execute("UPDATE deliveries SET "+sql+" WHERE id=?", (*values.values(), identity))

    @staticmethod
    def marker(identity):
        return f"[gcp-supervision-delivery:{identity}]"

    def reconcile(self, client, row):
        """Resolve uncertainty from native owner data; absence is never a retry grant."""
        queued = client.call("thread/queue/list", {"threadId": row["recipient"]})
        for item in queued.get("data", []):
            if item.get("clientUserMessageId") == row["id"] or self.marker(row["id"]) in canonical(item):
                queue_id = item.get("id")
                if not queue_id:
                    raise TransportError("native queued submission has no identity")
                self.update_delivery(row["id"], "queued", queue_id=queue_id, error=None)
                return "queued", queue_id
        for turn in client.turns(row["recipient"], limit=4).get("data", []):
            if any(item.get("type") == "userMessage" and self.marker(row["id"]) in canonical(item)
                   for item in turn.get("items", [])):
                self.update_delivery(row["id"], "acknowledged", turn_id=turn["id"], error=None)
                return "acknowledged", None
        return "uncertain", None

    def deliver(self, identity):
        with locked(self.root / "delivery.lock"):
            row = self.db.execute("SELECT * FROM deliveries WHERE id=?", (identity,)).fetchone()
            if row is None:
                raise ValueError("unknown delivery")
            if row["state"] in TERMINAL_DELIVERY:
                return row["state"]
            if row["state"] == "failed":
                return "failed"
            effect_possible = row["state"] != "prepared"
            try:
                with self.client() as client:
                    compact = client.compact(row["recipient"])
                    status = compact["status"]["type"]
                    if status == "notLoaded":
                        client.call("thread/resume", {"threadId": row["recipient"]})
                        status = client.compact(row["recipient"])["status"]["type"]
                    state, queue_id = row["state"], row["queue_id"]
                    if state in ("sending", "starting", "uncertain", "queued"):
                        state, queue_id = self.reconcile(client, row)
                        if state == "acknowledged":
                            return state
                        if state == "uncertain":
                            self.update_delivery(identity, "uncertain", error="native receipt not yet found; retry withheld")
                            return state
                    message = self.marker(identity)+"\n"+row["message"]
                    inputs = [{"type": "text", "text": message, "text_elements": []}]
                    if state == "prepared":
                        self.update_delivery(identity, "sending")
                        effect_possible = True
                        if status == "active" and row["recipient"] == self.target:
                            turns = client.turns(self.target, limit=1)["data"]
                            if not turns or turns[0]["status"] != "inProgress":
                                raise TransportError("target active turn changed before steer")
                            client.call("turn/steer", {"threadId": self.target,
                                "expectedTurnId": turns[0]["id"], "input": inputs,
                                "clientUserMessageId": identity})
                            self.update_delivery(identity, "started", turn_id=turns[0]["id"], error=None)
                            return "started"
                        result = client.call("thread/queue/add", {
                            "threadId": row["recipient"], "clientUserMessageId": identity, "input": inputs})
                        queue_id = result["queuedSubmission"]["id"]
                        self.update_delivery(identity, "queued", queue_id=queue_id, error=None)
                        # Current Codex automatically drains an idle task's queue.
                        # Observe its owner before attempting an explicit start.
                        state, queue_id = self.reconcile(client, row)
                        if state == "acknowledged":
                            return state
                        if state == "uncertain":
                            self.update_delivery(identity, "uncertain", error="accepted add awaiting native start receipt")
                            return state
                        status = client.compact(row["recipient"])["status"]["type"]
                    if status == "active":
                        return "queued"
                    self.update_delivery(identity, "starting")
                    result = client.call("thread/queue/start", {
                        "threadId": row["recipient"], "queuedSubmissionId": queue_id})
                    self.update_delivery(identity, "started", turn_id=result["turn"]["id"], error=None)
                    return "started"
            except RpcError as exc:
                # An explicit RPC rejection is visible and is never retried as a
                # new delivery. Earlier queue effects remain recoverable by ID.
                state = "uncertain" if effect_possible else "failed"
                self.update_delivery(identity, state, error=str(exc)[:700])
                return state
            except (OSError, TransportError, TimeoutError, KeyError) as exc:
                state = "uncertain" if effect_possible else "prepared"
                self.update_delivery(identity, state, error=type(exc).__name__)
                return state

    def gated_send(self, recipient, purpose, source, message, extra=(), *, action=None):
        sender = os.environ.get("CODEX_THREAD_ID")
        if sender not in {r["thread_id"] for r in self.config["roles"].values()}:
            raise ValueError("gated role sending requires a bound runtime role")
        if purpose == "status-broadcast" and action is not None and action != message:
            raise ValueError("status-broadcast action must remain the exact message payload")
        args = ["thread-route-gate", "--target-thread", self.target,
                "--recipient-thread", recipient, "--purpose", purpose,
                "--source-record", source, "--action", message if action is None else action, *extra]
        gate = self.helper(args)
        if gate.get("send_allowed") is not True:
            return {"delivered": False, "gate": gate}
        key = "route:"+digest(canonical([sender, recipient, purpose, source, message]))
        identity = self.prepare(key, recipient, message, source, purpose)
        return {"delivery_id": identity, "state": self.deliver(identity), "gate": gate}

    def heartbeat(self, role):
        if role == "liveness":
            return "Run your ordinary one-minute compact liveness check using the current helper and native transport. Stop quietly when no route is required."
        if role == "watcher":
            return "Run one ordinary bounded watcher check under your role and current policy. Use native direct task evidence and the current helper. Keep unchanged/non-actionable results quiet."
        return "Run the bounded supervisor-effectiveness review under your role. First use the current helper status. Stop quietly if no new review evidence exists; otherwise review only the bounded delta and exact original target evidence."

    def repair_unstarted_reviewer(self):
        """Repair only the observed bootstrap loss through the existing policy writer.

        The original no-rollout task and old policy version remain retained.
        This is not a general rebind API for operating supervision groups.
        """
        if os.environ.get("CODEX_THREAD_ID") != self.target:
            raise ValueError("bootstrap repair belongs to the direct implementation task")
        pending = self.config["pending_reviewer_replacement"]
        old, new = pending["old_thread_id"], pending["new_thread_id"]
        if self.db.execute("SELECT count(*) FROM deliveries").fetchone()[0]:
            raise ValueError("bootstrap repair is closed after first runtime delivery")
        if self.db.execute("SELECT count(*) FROM schedules WHERE enabled=1").fetchone()[0]:
            raise ValueError("bootstrap repair requires inactive schedules")
        with self.client() as client:
            if client.compact(old)["status"]["type"] != "notLoaded":
                raise ValueError("old reviewer is still available")
            try:
                client.turns(old, limit=1)
            except RpcError as exc:
                if not any(text in str(exc).lower() for text in ("no rollout", "missing source rollout")):
                    raise
            else:
                raise ValueError("old reviewer has resumable history")
            history = client.turns(new, limit=1).get("data", [])
            if (len(history) != 1 or history[0].get("status") != "completed"
                    or not any(item.get("type") == "agentMessage"
                               and item.get("text", "").strip() == "INITIALIZED"
                               for item in history[0].get("items", []))):
                raise ValueError("replacement initialization is not independently observable")
        spec = importlib.util.spec_from_file_location("gcp_policy_owner", self.config["helper_path"])
        owner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = owner
        spec.loader.exec_module(owner)
        args = argparse.Namespace(root=self.config["supervision_root"], target_thread=self.target)
        directory, policy, _, events, _, _ = owner.load_control_snapshot(args)
        if any(event.get("kind") != "policy-change" for event in events):
            raise ValueError("bootstrap repair cannot replace a reviewer after monitoring evidence")
        current = policy["runtime"]["reviewer_thread_id"]
        if current not in (old, new):
            raise ValueError("reviewer binding changed concurrently")
        if current == old:
            policy["runtime"]["reviewer_thread_id"] = new
            owner.write_policy_version(directory, policy,
                kind="runtime-bootstrap-repair",
                reason="Replace an unused reviewer with no rollout after verified durable initialization.",
                evidence_values=[old, new, history[0]["id"], self.target])
        self.config["roles"]["reviewer"]["thread_id"] = new
        self.config["reviewer_bootstrap_repair"] = pending
        self.config.pop("pending_reviewer_replacement")
        temporary = self.config_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.config, indent=2)+"\n")
        temporary.chmod(0o600)
        temporary.replace(self.config_path)
        return {"repaired": True, "old_thread_id": old, "new_thread_id": new,
                "policy_version": policy["policy_version"]}

    def tick(self):
        now = time.time()
        self.db.execute("INSERT OR REPLACE INTO health VALUES ('service_heartbeat',?,?)", (str(os.getpid()), now))
        # Finish already-owned dispatches first; uncertainty never creates a new
        # message identity or advances a schedule as if delivery succeeded.
        pending = self.db.execute("""SELECT id FROM deliveries
          WHERE state IN ('prepared','sending','starting','queued')
             OR (state='uncertain' AND updated_at<=?)
          ORDER BY created_at LIMIT 12""", (now-30,)).fetchall()
        for row in pending:
            if self.deliver(row["id"]) in TERMINAL_DELIVERY:
                self.finish_scheduled_delivery(row["id"], now)
        results = []
        for schedule in self.db.execute("SELECT * FROM schedules WHERE enabled=1 AND next_due<=? ORDER BY next_due", (now,)).fetchall():
            role = self.config["roles"][schedule["role"]]
            existing = self.db.execute("SELECT id FROM deliveries WHERE schedule_id=? AND scheduled_for=? AND state IN ('started','acknowledged')",
                                       (schedule["id"], schedule["next_due"])).fetchone()
            if existing:
                self.finish_scheduled_delivery(existing["id"], now)
                continue
            outstanding = self.db.execute("SELECT id,state FROM deliveries WHERE schedule_id=? AND state NOT IN ('started','acknowledged') ORDER BY created_at DESC LIMIT 1", (schedule["id"],)).fetchone()
            if outstanding:
                results.append({"schedule_id": schedule["id"], "state": outstanding["state"]})
                continue
            status = self.compact(role["thread_id"])["status"]["type"]
            if status == "active":
                continue
            due = schedule["next_due"]
            identity = self.prepare(f"wake:{schedule['id']}:{due}", role["thread_id"],
                                    self.heartbeat(schedule["role"]), schedule["id"], "heartbeat",
                                    schedule_id=schedule["id"], scheduled_for=due)
            state = self.deliver(identity)
            results.append({"schedule_id": schedule["id"], "delivery_id": identity, "state": state})
            if state in TERMINAL_DELIVERY:
                self.finish_scheduled_delivery(identity, now)
        return results

    def finish_scheduled_delivery(self, identity, now):
        delivery = self.db.execute("SELECT * FROM deliveries WHERE id=?", (identity,)).fetchone()
        if not delivery or not delivery["schedule_id"] or delivery["state"] not in TERMINAL_DELIVERY:
            return
        schedule = self.db.execute("SELECT * FROM schedules WHERE id=?", (delivery["schedule_id"],)).fetchone()
        due = delivery["scheduled_for"]
        if schedule["next_due"] != due:
            return
        next_due = due + (int(max(0, now-due) // schedule["interval_seconds"])+1)*schedule["interval_seconds"]
        self.db.execute("UPDATE schedules SET next_due=?, last_delivery=?, last_started_at=?, updated_at=? WHERE id=? AND next_due=?",
                        (next_due, identity, now, now, schedule["id"], due))

    def status(self):
        schedules = [dict(row) for row in self.db.execute("SELECT * FROM schedules ORDER BY role")]
        for row in schedules:
            row["thread_id"] = self.config["roles"][row["role"]]["thread_id"]
        deliveries = [dict(row) for row in self.db.execute("SELECT id,recipient,source,purpose,schedule_id,state,queue_id,turn_id,created_at,updated_at,error FROM deliveries ORDER BY created_at DESC LIMIT 20")]
        return {"target_thread_id": self.target, "backend": "gcp-local-codex", "schedules": schedules,
                "roles": {name: {k:v for k,v in value.items() if k != "instructions"}
                          for name,value in self.config["roles"].items()},
                "deliveries": deliveries,
                "health": [dict(row) for row in self.db.execute("SELECT * FROM health")]}

    def run(self):
        if self.config.get("bootstrap"):
            self.verify_bindings()
        stop = False
        def stopping(*_):
            nonlocal stop
            stop = True
        signal.signal(signal.SIGTERM, stopping)
        signal.signal(signal.SIGINT, stopping)
        with open(self.root / "service.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            previous_error = None
            while not stop:
                try:
                    results = self.tick()
                    for result in results:
                        if result.get("delivery_id"):
                            print(canonical(result), flush=True)
                    previous_error = None
                except Exception as exc:
                    error = type(exc).__name__+": "+str(exc)[:400]
                    if error != previous_error:
                        print(canonical({"service_error": error}), flush=True)
                    previous_error = error
                    self.db.execute("INSERT OR REPLACE INTO health VALUES ('last_error',?,?)", (error, time.time()))
                for _ in range(5):
                    if stop:
                        break
                    time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "tick", "status", "pause", "resume", "repair-unstarted-reviewer"):
        sub.add_parser(command)
    compact = sub.add_parser("read")
    compact.add_argument("--thread", required=True)
    turns = sub.add_parser("turns")
    turns.add_argument("--thread", required=True)
    turns.add_argument("--limit", type=int, default=1)
    helper = sub.add_parser("helper")
    helper.add_argument("arguments", nargs=argparse.REMAINDER)
    send = sub.add_parser("send")
    send.add_argument("--recipient", required=True)
    send.add_argument("--purpose", required=True)
    send.add_argument("--source-record", required=True)
    send.add_argument("--message", required=True)
    send.add_argument("--action", help="Concise exact action for the semantic gate; full evidence stays in --message.")
    send.add_argument("gate_arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    runtime = Runtime(args.config)
    try:
        if args.command == "run":
            runtime.run()
            return
        if args.command == "tick":
            result = runtime.tick()
        elif args.command == "status":
            result = runtime.status()
        elif args.command == "repair-unstarted-reviewer":
            result = runtime.repair_unstarted_reviewer()
        elif args.command in ("pause", "resume"):
            runtime.schedule_state(args.command == "resume")
            result = runtime.status()
        elif args.command == "read":
            result = runtime.compact(args.thread)
        elif args.command == "turns":
            result = runtime.direct_turns(args.thread, args.limit)
        elif args.command == "helper":
            arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            result = runtime.helper(arguments)
        else:
            extra = args.gate_arguments[1:] if args.gate_arguments[:1] == ["--"] else args.gate_arguments
            result = runtime.gated_send(args.recipient, args.purpose, args.source_record,
                                        args.message, extra, action=args.action)
        print(canonical(result))
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
