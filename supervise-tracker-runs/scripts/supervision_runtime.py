#!/usr/bin/env python3
"""Discover the real target owner and bootstrap an isolated native group.

Discovery is read-only. Bootstrap advances one bounded step per invocation;
rerun it until ready. It never retries an ambiguous task-creation request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from gcp_codex_transport import CodexClient
from gcp_supervision import Runtime, locked
from gcp_supervision_roles import role_prompt

ROLES = {
    "reviewer": ("gpt-5.6-sol", "max"),
    "base_reviewer": ("gpt-5.6-sol", "xhigh"),
    "fix_executor": ("gpt-5.6-sol", "xhigh"),
    "watcher": ("gpt-5.6-terra", "max"),
    "liveness": ("gpt-5.6-luna", "low"),
}
INTERVALS = {"liveness": 60, "watcher": 1200, "reviewer": 14400}
INITIALIZE = ("Initialization only. Do not inspect or contact the target, call tools, "
              "log, schedule, implement, or delegate. Reply exactly INITIALIZED and stop.")
NATIVE_ROOT = Path("/srv/patent-studio/private/gcp-supervision")


def save(path, value):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.chmod(0o600)
    temp.replace(path)


def discover(target, *, root=NATIVE_ROOT, socket_path=None, app_tools=False,
             client_factory=CodexClient):
    """Read config files only; do not instantiate Runtime or open writable SQLite."""
    root = Path(root)
    paths = [root / "config.json"]
    # Only this owner's immediate group configs, never task/session histories.
    if (root / "groups").is_dir():
        paths.extend(sorted((root / "groups").glob("*/config.json")))
    matches = []
    for path in paths:
        if not path.exists():
            continue
        config = json.loads(path.read_text())
        if config.get("target_thread_id") == target:
            matches.append((path, config))
    if len(matches) > 1:
        raise ValueError("multiple native owners for exact target; do not create another group")
    if matches:
        path, config = matches[0]
        with client_factory(config["socket_path"], timeout=15) as client:
            observed = client.compact(target)
        if observed.get("id") != target:
            raise ValueError("native owner returned a different target")
        return {"backend": "native", "action": "reuse", "target_thread_id": target,
                "config_path": str(path), "target": observed}
    if app_tools:
        return {"backend": "app", "action": "resolve-existing-app-group-before-boot",
                "target_thread_id": target}
    socket_path = socket_path or str(Path(os.environ.get("CODEX_HOME", str(Path.home()/".codex"))) /
                                     "app-server-control/app-server-control.sock")
    if not Path(socket_path).is_socket():
        return {"backend": None, "action": "owner-access-required", "target_thread_id": target,
                "reason": "No existing native owner, callable app controls, or local Codex socket."}
    with client_factory(socket_path, timeout=15) as client:
        observed = client.compact(target)
    if observed.get("id") != target:
        raise ValueError("local socket does not own the exact target")
    return {"backend": "native", "action": "bootstrap", "target_thread_id": target,
            "socket_path": socket_path, "state_root": str(root/"groups"/target),
            "target": observed}


def new_config(path, *, target, label, socket_path, helper, mission_file, mission_record,
               client_factory=CodexClient):
    """The caller has already verified host storage and direct boot authority."""
    path = Path(path).absolute()
    if path.name != "config.json" or path.parent.name != target or path.parent.parent.name != "groups":
        raise ValueError("native config must be ROOT/groups/EXACT_TARGET/config.json")
    mission_file = Path(mission_file).resolve(strict=True)
    helper = Path(helper).absolute()
    if not helper.is_file():
        raise ValueError("installed helper is unavailable")
    source_hash = hashlib.sha256(mission_file.read_bytes()).hexdigest()
    expected = {"target_thread_id": target, "socket_path": str(socket_path),
                "mission_source_record": mission_record, "mission_source_sha256": source_hash}
    root = path.parents[2]
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with locked(root/"bootstrap-registry.lock"):
        owner = discover(target, root=root, socket_path=socket_path, client_factory=client_factory)
        if owner["action"] == "reuse" and Path(owner["config_path"]).resolve() != path.resolve():
            raise ValueError("target already has a native owner; reuse its exact config")
        if owner["backend"] != "native":
            raise ValueError("native target ownership is not proven")
        if path.exists():
            config = json.loads(path.read_text())
            if any(config.get(k) != v for k, v in expected.items()):
                raise ValueError("existing bootstrap binds another target, socket or mission")
            return config
        validation = subprocess.run([sys.executable, str(helper), "mission-plan",
            "--target-thread", target, "--mission-source-class", "direct-user",
            "--mission-source-record", mission_record, "--mission-source-sha256", source_hash],
            capture_output=True, text=True, timeout=45)
        if validation.returncode:
            raise ValueError("mission-plan rejected bootstrap source: "+
                             (validation.stdout or validation.stderr)[:1000])
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        config = {"schema_version": 1, **expected, "target_label": label,
              "state_root": str(path.parent), "config_path": str(path),
              "helper_path": str(helper), "supervision_root": str(path.parent/"supervision"),
              "native_cli": str(Path(__file__).absolute().with_name("gcp_supervision.py")),
              "mission_file": str(mission_file), "mission_source_class": "direct-user",
              "mission_context": mission_file.read_text(), "roles": {},
              "bootstrap": {"version": 1, "phase": "roles", "pending": None}}
        save(path, config)
        return config


def initialized(turn):
    return (turn.get("status") == "completed" and
            any(item.get("type") == "agentMessage" and item.get("text", "").strip() == "INITIALIZED"
                for item in turn.get("items", [])) and
            all(item.get("type") in ("userMessage", "agentMessage", "reasoning", "plan")
                for item in turn.get("items", [])))


def bootstrap_step(path, *, client_factory=CodexClient):
    path = Path(path).absolute()
    with locked(path.parent/"bootstrap.lock"):
        config = json.loads(path.read_text())
        boot = config["bootstrap"]
        if boot["phase"] == "ready":
            runtime = Runtime(path, client_factory=client_factory)
            try:
                runtime.verify_bindings()
                return {"phase": "ready", "target_thread_id": runtime.target,
                        "config_path": str(path)}
            finally:
                runtime.close()
        with client_factory(config["socket_path"], timeout=20) as client:
            if client.compact(config["target_thread_id"]).get("id") != config["target_thread_id"]:
                raise ValueError("native socket returned a different target")
            pending = boot.get("pending")
            if pending:
                if pending["operation"] == "create":
                    raise ValueError("task creation response uncertain; reconcile native owner before retry")
                name = pending["role"]
                role = config["roles"][name]
                turns = client.turns(role["thread_id"], limit=4).get("data", [])
                turn = next((t for t in turns if t.get("id") == pending.get("turn_id")), None)
                if turn is None:
                    # A lost turn/start response is recoverable only from the exact input marker.
                    turn = next((t for t in turns if pending["marker"] in json.dumps(t.get("items", []))), None)
                if not turn or turn.get("status") == "inProgress":
                    return {"phase": "waiting-initialization", "role": name,
                            "thread_id": role["thread_id"], "operation": pending["operation"]}
                if not initialized(turn):
                    raise ValueError("role initialization did not complete cleanly: "+name)
                role[pending["receipt_key"]] = turn["id"]
                boot["pending"] = None
                save(path, config)
                return {"phase": "initialized", "role": name, "turn_id": turn["id"]}
            for name, (model, reasoning) in ROLES.items():
                if name not in config["roles"]:
                    role_root = path.parent/"roles"/name
                    role_root.mkdir(parents=True, exist_ok=True)
                    boot["pending"] = {"operation": "create", "role": name}
                    save(path, config)  # Fail closed after an ambiguous creation, even after crash.
                    result = client.call("thread/start", {
                        "model": model, "cwd": str(role_root), "approvalPolicy": "never",
                        "sandbox": "danger-full-access", "developerInstructions": INITIALIZE,
                        "config": {"model_reasoning_effort": reasoning}, "ephemeral": False})
                    thread_id = result["thread"]["id"]
                    config["roles"][name] = {"thread_id": thread_id, "model": model,
                                             "reasoning": reasoning, "cwd": str(role_root)}
                    boot["pending"] = None
                    save(path, config)
                    return {"phase": "created", "role": name, "thread_id": thread_id}
                role = config["roles"][name]
                if not role.get("durable_init_turn"):
                    return start_initialization(client, path, config, name, "durable_init_turn")
            for name in ROLES:
                role = config["roles"][name]
                if not role.get("role_init_turn"):
                    instructions = role_prompt(config, name)
                    client.call("thread/resume", {"threadId": role["thread_id"],
                        "model": role["model"], "cwd": role["cwd"], "approvalPolicy": "never",
                        "sandbox": "danger-full-access", "developerInstructions": instructions,
                        "config": {"model_reasoning_effort": role["reasoning"]}})
                    client.call("thread/name/set", {"threadId": role["thread_id"],
                        "name": config["target_label"]+" / supervision / "+name})
                    role["instructions"] = instructions
                    save(path, config)
                    return start_initialization(client, path, config, name, "role_init_turn")
        runtime = Runtime(path, client_factory=client_factory)
        try:
            target_args = ["--target-thread", config["target_thread_id"]]
            source_args = ["--mission-source-class", config["mission_source_class"],
                           "--mission-source-record", config["mission_source_record"],
                           "--mission-source-sha256", config["mission_source_sha256"]]
            runtime.helper(["mission-plan", *target_args, *source_args])
            role_args = [arg for name, role in config["roles"].items()
                         for arg in ("--"+name.replace("_", "-")+"-thread", role["thread_id"])]
            runtime.helper(["init", *target_args, "--target-label", config["target_label"],
                            *role_args, *source_args])
            schedules = {name: runtime.add_schedule(name, seconds,
                         first_due=time.time()+(seconds if name == "reviewer" else 0))
                         for name, seconds in INTERVALS.items()}
            bind_roles = [arg for name, role in config["roles"].items()
                          if name not in ("reviewer", "watcher")
                          for arg in ("--"+name.replace("_", "-")+"-thread", role["thread_id"])]
            runtime.helper(["bind", *target_args, *bind_roles,
                "--liveness-automation", schedules["liveness"],
                "--routine-automation", schedules["watcher"],
                "--meta-automation", schedules["reviewer"]])
            runtime.verify_bindings()
            config = runtime.config
            boot = config["bootstrap"]
            boot["phase"] = "ready"
            save(path, config)
            return {"phase": "ready", "target_thread_id": config["target_thread_id"],
                    "schedules": schedules, "enabled": False}
        finally:
            runtime.close()


def start_initialization(client, path, config, name, receipt_key):
    role = config["roles"][name]
    marker = "[supervision-init:"+name+":"+receipt_key+"]"
    pending = {"operation": "initialize", "role": name, "receipt_key": receipt_key, "marker": marker}
    config["bootstrap"]["pending"] = pending
    save(path, config)
    result = client.call("turn/start", {"threadId": role["thread_id"], "model": role["model"],
        "effort": role["reasoning"], "input": [{"type": "text", "text": INITIALIZE+"\n"+marker,
                                                  "text_elements": []}]})
    pending["turn_id"] = result["turn"]["id"]
    save(path, config)
    return {"phase": "waiting-initialization", "role": name, "turn_id": pending["turn_id"]}


def systemd_unit(config, *, user, group, account_home, codex_home, preflight, temporary_root):
    """Render a reviewable per-group unit; installation is a separate host action."""
    def quote(value):
        if any(c in str(value) for c in "\n\r\x00"):
            raise ValueError("invalid systemd value")
        return '"'+str(value).replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")+'"'
    state = config["state_root"]
    return f'''[Unit]
Description=Codex supervision for {config['target_thread_id']}
After=local-fs.target
RequiresMountsFor={quote(state)}

[Service]
Type=simple
User={user}
Group={group}
WorkingDirectory={state.replace('%', '%%')}
Environment={quote('HOME='+account_home)}
Environment={quote('CODEX_HOME='+codex_home)}
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=PYTHONDONTWRITEBYTECODE=1
Environment={quote('TMPDIR='+temporary_root)}
ExecStartPre={quote(preflight)}
ExecStart=/usr/bin/python3 {quote(config['native_cli'])} --config {quote(config['config_path'])} run
Restart=on-failure
RestartSec=10
TimeoutStopSec=90
UMask=0077
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths={quote(state)}
RestrictAddressFamilies=AF_UNIX

[Install]
WantedBy=multi-user.target
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    detect = sub.add_parser("discover")
    detect.add_argument("--target-thread", required=True)
    detect.add_argument("--native-root", default=str(NATIVE_ROOT))
    detect.add_argument("--socket")
    detect.add_argument("--app-tools-available", action="store_true")
    boot = sub.add_parser("bootstrap")
    boot.add_argument("--config", required=True)
    boot.add_argument("--target-thread", required=True)
    boot.add_argument("--label", required=True)
    boot.add_argument("--socket", required=True)
    boot.add_argument("--helper", required=True)
    boot.add_argument("--mission-file", required=True)
    boot.add_argument("--mission-source-record", required=True)
    args = parser.parse_args()
    if args.command == "discover":
        result = discover(args.target_thread, root=args.native_root, socket_path=args.socket,
                          app_tools=args.app_tools_available)
    else:
        new_config(args.config, target=args.target_thread, label=args.label, socket_path=args.socket,
                   helper=args.helper, mission_file=args.mission_file, mission_record=args.mission_source_record)
        result = bootstrap_step(args.config)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
