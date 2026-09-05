import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gcp_supervision import Runtime
from gcp_supervision_roles import role_prompt
from supervision_runtime import (ROLES, bootstrap_step, discover, new_config,
                                 systemd_unit)


class NativeOwner:
    def __init__(self):
        self.histories = {}
        self.creates = 0
        self.starts = 0
        self.lose_create = False
        self.lose_turn = False
        self.instructions = {}

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def compact(self, target):
        return {"id": target, "status": {"type": "idle"}, "updatedAt": 1}

    def turns(self, identity, limit=4):
        return {"data": self.histories.get(identity, [])[:limit]}

    def call(self, method, params):
        if method == "thread/start":
            self.creates += 1
            identity = "role-"+str(self.creates)
            self.histories[identity] = []
            if self.lose_create:
                raise TimeoutError("accepted create response lost")
            return {"thread": {"id": identity}}
        if method == "turn/start":
            self.starts += 1
            turn = {"id": "turn-"+str(self.starts), "status": "completed",
                    "items": [{"type": "userMessage", "content": params["input"]},
                              {"type": "agentMessage", "text": "INITIALIZED"}]}
            self.histories[params["threadId"]].insert(0, turn)
            if self.lose_turn:
                self.lose_turn = False
                raise TimeoutError("accepted turn response lost")
            return {"turn": turn}
        if method == "thread/resume":
            if not self.histories[params["threadId"]]:
                raise AssertionError("resume before durable initialization")
            self.instructions[params["threadId"]] = params["developerInstructions"]
            return {}
        if method == "thread/name/set":
            return {}
        raise AssertionError(method)


class PortableRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root/"groups"/"target"/"config.json"
        self.mission = self.root/"mission.md"
        self.mission.write_text("Direct user authority: portable supervision only.")
        self.helper = Path(__file__).with_name("supervision_log.py")
        self.owner = NativeOwner()

    def tearDown(self):
        self.temp.cleanup()

    def configure(self, path=None, target="target"):
        with patch.object(Path, "is_socket", return_value=True):
            return new_config(path or self.path, target=target, label="Example",
                          socket_path="/unused", helper=self.helper,
                          mission_file=self.mission, mission_record="direct-user:example",
                          client_factory=self.owner)

    def ready(self, path=None):
        path = path or self.path
        self.configure(path, "target" if path == self.path else "second")
        for _ in range(30):
            result = bootstrap_step(path, client_factory=self.owner)
            if result["phase"] == "ready":
                return result
        self.fail("bootstrap did not terminate")

    def test_app_selection_does_not_create_state(self):
        result = discover("target", root=self.root/"missing", app_tools=True)
        self.assertEqual(result["backend"], "app")
        self.assertFalse((self.root/"missing").exists())

    def test_missing_controls_returns_capability_gap(self):
        result = discover("target", root=self.root/"missing", socket_path=str(self.root/"absent"))
        self.assertEqual(result["action"], "owner-access-required")

    def test_native_socket_fallback_checks_target_without_database(self):
        with patch.object(Path, "is_socket", return_value=True):
            result = discover("target", root=self.root, socket_path="/unused", client_factory=self.owner)
        self.assertEqual(result["action"], "bootstrap")
        self.assertFalse(list(self.root.rglob("runtime.sqlite3")))

    def test_existing_owner_wins_over_available_app_and_is_read_only(self):
        self.configure()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = discover("target", root=self.root, app_tools=True, client_factory=self.owner)
        self.assertEqual(result["config_path"], str(self.path))
        self.assertEqual(result["action"], "reuse")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_duplicate_owner_refuses_fallback(self):
        config = self.configure()
        (self.root/"config.json").write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "multiple native owners"):
            discover("target", root=self.root, app_tools=True)

    def test_config_replay_rejects_another_mission_or_target(self):
        self.configure()
        with self.assertRaises(ValueError):
            self.configure(target="different")
        self.mission.write_text("Different mission")
        with self.assertRaises(ValueError):
            self.configure()

    def test_lost_create_response_never_creates_a_second_role(self):
        self.configure()
        self.owner.lose_create = True
        with self.assertRaises(TimeoutError):
            bootstrap_step(self.path, client_factory=self.owner)
        with self.assertRaisesRegex(ValueError, "creation response uncertain"):
            bootstrap_step(self.path, client_factory=self.owner)
        self.assertEqual(self.owner.creates, 1)

    def test_invalid_mission_is_rejected_before_config_and_role_creation(self):
        with patch.object(Path, "is_socket", return_value=True):
            with self.assertRaisesRegex(ValueError, "mission-plan rejected"):
                new_config(self.path, target="target", label="Example", socket_path="/unused",
                           helper=self.helper, mission_file=self.mission,
                           mission_record="invalid record with spaces", client_factory=self.owner)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.owner.creates, 0)

    def test_lost_initialization_response_reconciles_direct_native_turn(self):
        self.configure()
        bootstrap_step(self.path, client_factory=self.owner)
        self.owner.lose_turn = True
        with self.assertRaises(TimeoutError):
            bootstrap_step(self.path, client_factory=self.owner)
        result = bootstrap_step(self.path, client_factory=self.owner)
        self.assertEqual(result["phase"], "initialized")
        self.assertEqual(self.owner.starts, 1)

    def test_complete_bootstrap_replay_reuses_five_roles_and_three_paused_schedules(self):
        self.ready()
        self.assertEqual((self.owner.creates, self.owner.starts), (5, 10))
        self.assertEqual(bootstrap_step(self.path, client_factory=self.owner)["phase"], "ready")
        runtime = Runtime(self.path, client_factory=self.owner)
        try:
            self.assertEqual(len(runtime.status()["schedules"]), 3)
            self.assertTrue(all(not s["enabled"] for s in runtime.status()["schedules"]))
            runtime.schedule_state(True)
            self.assertTrue(all(s["enabled"] for s in runtime.status()["schedules"]))
        finally:
            runtime.close()
        self.assertEqual((self.owner.creates, self.owner.starts), (5, 10))

    def test_second_group_does_not_change_first_group(self):
        self.ready()
        before = {p: p.read_bytes() for p in self.path.parent.rglob("*") if p.is_file()}
        second = self.root/"groups"/"second"/"config.json"
        self.ready(second)
        self.assertEqual(before, {p: p.read_bytes() for p in self.path.parent.rglob("*") if p.is_file()})
        self.assertEqual(self.owner.creates, 10)

    def test_activation_refuses_schedule_binding_mismatch(self):
        self.ready()
        runtime = Runtime(self.path, client_factory=self.owner)
        try:
            runtime.db.execute("UPDATE schedules SET interval_seconds=3 WHERE role='watcher'")
            with self.assertRaisesRegex(ValueError, "schedule and policy"):
                runtime.schedule_state(True)
            self.assertFalse(any(s["enabled"] for s in runtime.status()["schedules"]))
        finally:
            runtime.close()

    def test_activation_refuses_missing_initialization(self):
        self.ready()
        config = json.loads(self.path.read_text())
        config["roles"]["watcher"].pop("role_init_turn")
        self.path.write_text(json.dumps(config))
        runtime = Runtime(self.path, client_factory=self.owner)
        try:
            with self.assertRaisesRegex(ValueError, "missing initialization"):
                runtime.schedule_state(True)
        finally:
            runtime.close()

    def test_activation_refuses_same_record_with_different_mission_hash(self):
        self.ready()
        config = json.loads(self.path.read_text())
        config["mission_source_sha256"] = "0"*64
        self.path.write_text(json.dumps(config))
        runtime = Runtime(self.path, client_factory=self.owner)
        try:
            with self.assertRaisesRegex(ValueError, "mission source binding changed"):
                runtime.schedule_state(True)
        finally:
            runtime.close()

    def test_commands_bind_explicit_config_and_quote_spaces(self):
        config = self.configure()
        config["config_path"] = "/state with spaces/target/config.json"
        config["roles"] = {name: {"thread_id": name} for name in ROLES}
        prompt = role_prompt(config, "watcher")
        self.assertIn("--config '/state with spaces/target/config.json'", prompt)
        self.assertNotIn("python3 /srv/patent-studio/private/gcp-supervision", prompt)
        self.assertIn("portable supervision only", prompt)
        self.assertNotIn("monitored patent implementation", prompt)

    def test_luna_helper_command_has_one_interpreter(self):
        import shlex
        import sys
        config = self.configure()
        config["roles"] = {name: {"thread_id": name} for name in ROLES}
        prompt = role_prompt(config, "liveness")
        command = next(line for line in prompt.replace("\\\n", " ").splitlines()
                       if "liveness-gate" in line and " helper -- " in line)
        argv = shlex.split(command)
        self.assertEqual(argv[:2], [sys.executable, config["native_cli"]])
        self.assertEqual(argv[2:7], ["--config", str(self.path), "helper", "--", "liveness-gate"])

    def test_bootstrap_refuses_legacy_owner_before_creating_roles(self):
        config = self.configure()
        # An already registered legacy group for another target must be reused.
        config["target_thread_id"] = "legacy"
        (self.root/"config.json").write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "already has a native owner"):
            self.configure(self.root/"groups"/"legacy"/"config.json", "legacy")
        self.assertEqual(self.owner.creates, 0)
        self.assertFalse((self.root/"groups"/"legacy").exists())

    def test_bootstrap_rejects_sibling_config_in_shared_state(self):
        self.configure()
        with self.assertRaisesRegex(ValueError, "ROOT/groups/EXACT_TARGET"):
            self.configure(self.path.with_name("second.json"), "second")
        self.assertEqual(self.owner.creates, 0)

    def test_service_quotes_exact_group_and_preserves_codex_home(self):
        config = self.configure()
        unit = systemd_unit(config, user="owner", group="owner", account_home="/home/owner",
                            codex_home="/home/owner/.codex-alt", preflight="/host/preflight",
                            temporary_root="/data/tmp")
        self.assertIn('--config "'+str(self.path)+'" run', unit)
        self.assertIn('"CODEX_HOME=/home/owner/.codex-alt"', unit)
        self.assertIn('ReadWritePaths="'+str(self.path.parent)+'"', unit)
        self.assertIn('WorkingDirectory='+str(self.path.parent)+'\n', unit)

    def test_unit_passes_native_systemd_parser(self):
        import shutil
        import subprocess
        if not shutil.which("systemd-analyze"):
            self.skipTest("systemd parser unavailable on this host")
        config = self.configure()
        unit = systemd_unit(config, user="root", group="root", account_home="/root",
                            codex_home="/root/.codex", preflight="/usr/bin/true",
                            temporary_root=str(self.root))
        path = self.root/"test-supervision.service"
        path.write_text(unit)
        proc = subprocess.run(["systemd-analyze", "verify", str(path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
