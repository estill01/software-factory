from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import pytest

from software_factory import (
    CodexAppServerProvider,
    CoreService,
    ExternalAgentProvider,
    ProviderError,
    ProviderObservation,
    ProviderRegistry,
    ProviderRequest,
    Store,
)
from software_factory.provider_provenance import QualifiedClientPin


def request(
    root: Path,
    *,
    prompt: str = "implement bounded work",
    execution_id: str = "exe-provider",
) -> ProviderRequest:
    return ProviderRequest(
        execution_id=execution_id,
        mission_id="mis-provider",
        work_item_id="wrk-provider",
        assignment_id="asn-provider",
        workspace_id="wsp-provider",
        workspace_path=root,
        lease_generation=1,
        role="implementer",
        prompt=prompt,
    )


def test_qualified_client_pin_is_exact_internal_unpublished_identity(tmp_path: Path) -> None:
    pin = QualifiedClientPin.load().record

    assert pin["qualified_producer_revision"] == ("a5659745a7cbcbb002b5f06051f6ed9826f721a7")
    assert pin["qualification_matrix_sha256"] == (
        "0888bed363b63842c37baa8187c9883cdddff73d936596e497e4e013341cd849"
    )
    assert pin["technical_qualification_root_sha256"] == (
        "9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068"
    )
    assert pin["accepted_source_commit"] == "08c416da4202b7036110e33e43d34ea590054e2e"
    assert pin["accepted_source_tree"] == "794650275e9a583c9f47276a271f65cc1020c4e8"
    assert pin["package_tree_object"] == "17772f61da62b41d6d3551deebc474792aafe922"
    assert pin["wheel_sha256"] == (
        "1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9"
    )
    assert pin["resolution"]["registry_allowed"] is False
    assert pin["resolution"]["copied_source_allowed"] is False
    assert pin["release_posture"] == "no-license-selected/unpublished"

    fake = tmp_path / pin["wheel"]
    fake.write_bytes(b"not the accepted wheel")
    with pytest.raises(ProviderError, match="SHA-256"):
        QualifiedClientPin(pin).verify_wheel(fake)


def test_external_agent_provider_is_bounded_and_keeps_callbacks_in_factory() -> None:
    seen: list[ProviderRequest] = []

    provider = ExternalAgentProvider(
        dispatch=lambda value: (
            seen.append(value)
            or ProviderObservation(
                status="running",
                external_thread_id="external-thread",
                handle={"execution_id": value.execution_id},
            )
        ),
        poll=lambda handle: ProviderObservation(status="succeeded", handle=handle),
        cancel=lambda handle: ProviderObservation(status="cancelled", handle=handle),
        max_prompt_bytes=8,
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        provider.dispatch(request(root, prompt="bounded"))
        assert len(seen) == 1
        assert not hasattr(seen[0], "callback_token")
        with pytest.raises(ValueError, match="prompt exceeds"):
            provider.dispatch(request(root, prompt="too many bytes"))
        assert provider.poll({"execution_id": "exe"}).status == "succeeded"
        assert provider.cancel({"execution_id": "exe"}).status == "cancelled"


def test_registry_rejects_duplicate_process_owner_and_closes_replacement() -> None:
    class Owned:
        process_owner_key = "shared-process-owner"

        def __init__(self) -> None:
            self.closed = 0

        def dispatch(self, _: ProviderRequest) -> ProviderObservation:
            return ProviderObservation(status="running")

        def poll(self, _: dict[str, Any]) -> ProviderObservation:
            return ProviderObservation(status="running")

        def cancel(self, _: dict[str, Any]) -> ProviderObservation:
            return ProviderObservation(status="cancelled")

        def close(self) -> None:
            self.closed += 1

    registry = ProviderRegistry()
    first = Owned()
    second = Owned()
    registry.register("owned", first)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("duplicate", second)

    registry.replace("owned", second)
    assert first.closed == 1
    registry.close()
    assert second.closed == 1
    assert registry.keys() == ()
    registry.close()
    assert second.closed == 1


def _fake_codex(path: Path, *, approval_callback: bool = False) -> Path:
    script = path / "codex-fixture"
    script.write_text(
        textwrap.dedent(
            r"""#!/usr/bin/env python3
import json
import sys

if sys.argv[1:] == ["--version"]:
    print("codex-cli 0.147.0")
    raise SystemExit(0)

thread_id = "thread-factory"
turn_id = "turn-factory"
approval_callback = __APPROVAL_CALLBACK__
approval_answered = not approval_callback

def thread(turns):
    return {
        "cliVersion": "0.147.0",
        "createdAt": 0,
        "cwd": "/tmp/factory",
        "ephemeral": False,
        "id": thread_id,
        "modelProvider": "fixture",
        "preview": "factory fixture",
        "sessionId": "session-factory",
        "source": "cli",
        "status": {"type": "idle"},
        "turns": turns,
        "updatedAt": 0,
    }

completed_turn = {"id": turn_id, "items": [], "status": "completed"}

for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        continue
    if method is None:
        if request_id == "factory-approval":
            approval_answered = message.get("result", {}).get("decision") == "decline"
        continue
    if method == "initialize":
        result = {
            "codexHome": "/tmp/codex-home",
            "platformFamily": "unix",
            "platformOs": "macos",
            "userAgent": "software-factory-fixture",
        }
    elif method == "thread/start":
        result = {
            "approvalPolicy": "never",
            "approvalsReviewer": "user",
            "cwd": "/tmp/factory",
            "model": "fixture",
            "modelProvider": "fixture",
            "sandbox": {"type": "dangerFullAccess"},
            "thread": thread([]),
        }
    elif method == "thread/resume":
        result = {
            "approvalPolicy": "never",
            "approvalsReviewer": "user",
            "cwd": "/tmp/factory",
            "model": "fixture",
            "modelProvider": "fixture",
            "sandbox": {"type": "dangerFullAccess"},
            "thread": thread([completed_turn]),
        }
    elif method == "turn/start":
        result = {"turn": {"id": turn_id, "items": [], "status": "inProgress"}}
    elif method == "thread/list":
        result = {"data": [thread([])]}
    elif method == "thread/read":
        observed_turn = completed_turn if approval_answered else {
            "id": turn_id,
            "items": [],
            "status": "inProgress",
        }
        result = {"thread": thread([observed_turn])}
    elif method == "turn/interrupt":
        result = {}
    else:
        result = {}
    print(json.dumps({"id": request_id, "result": result}, separators=(",", ":")), flush=True)
    if method == "turn/start" and approval_callback:
        callback = {
            "id": "factory-approval",
            "method": "item/commandExecution/requestApproval",
            "params": {
                "itemId": "item-factory",
                "startedAtMs": 0,
                "threadId": thread_id,
                "turnId": turn_id,
            },
        }
        print(json.dumps(callback, separators=(",", ":")), flush=True)
"""
        ).replace("__APPROVAL_CALLBACK__", repr(approval_callback)),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def _qualified_wheel() -> Path:
    value = os.environ.get("SFV2_CODEX_CLIENT_WHEEL")
    if not value:
        pytest.skip("exact qualified client wheel was not supplied")
    return Path(value)


def test_exact_shared_client_provider_dispatch_restart_reattach_and_submit(
    tmp_path: Path,
) -> None:
    wheel = _qualified_wheel()
    executable = _fake_codex(tmp_path)
    provider = CodexAppServerProvider(
        wheel_path=wheel,
        codex_executable=executable,
        owner_key="fixture",
        operation_timeout_seconds=15,
    )
    registry = ProviderRegistry()
    registry.register("codex-app-server", provider)
    diagnostic = provider.diagnose()
    assert diagnostic["operation"] == "thread/list"
    assert diagnostic["generative_turn_started"] is False
    assert diagnostic["observed_thread_count"] == 1
    assert diagnostic["wheel_sha256"] == (
        "1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9"
    )
    store = Store(tmp_path / "factory.sqlite3")
    core = CoreService(
        store,
        providers=registry,
        default_provider="codex-app-server",
    )
    project = core.create_project("provider fixture")
    mission = core.create_mission(
        project_id=project,
        title="provider lifecycle",
        objective="submit attributable provider evidence",
    )
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "fixture"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"],
        cwd=repository,
        check=True,
    )
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repository, check=True)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    repository_id = core.register_repository(
        repository,
        project_id=project,
        default_branch="main",
        current_revision=revision,
        workspace_policy={"workspace_root": str(tmp_path / "worktrees")},
    )
    obligation = core.add_obligation(
        mission_id=mission,
        obligation_type="implement",
        description="run provider",
    )
    work = core.create_work_item(
        mission_id=mission,
        obligation_id=obligation,
        repository_id=repository_id,
        work_type="implementation",
        title="provider work",
        description="produce provider evidence",
        writable_scope=["src"],
        provider_key="codex-app-server",
    )
    core.select_work(work, expected_version=1, selected_by="selector", basis={"required": True})

    dispatch = core.dispatch_work(work)
    assert dispatch["provider_status"] == "running"
    execution = store.one("SELECT * FROM executions WHERE id=?", (dispatch["execution_id"],))
    handle = json.loads(execution["provider_handle_json"])
    assert handle["producer_revision"] == "a5659745a7cbcbb002b5f06051f6ed9826f721a7"
    assert handle["thread_id"] == "thread-factory"
    assert handle["turn_id"] == "turn-factory"
    assert "callback_token" not in json.dumps(handle)
    stale_handle = dict(handle)
    stale_handle["wheel_sha256"] = "0" * 64
    with pytest.raises(ProviderError, match="stale producer material"):
        provider.poll(stale_handle)

    replacement = CodexAppServerProvider(
        wheel_path=wheel,
        codex_executable=executable,
        owner_key="fixture",
        operation_timeout_seconds=15,
    )
    registry.replace("codex-app-server", replacement)
    updates = core.poll_provider_executions(mission)
    assert updates == [{"execution_id": dispatch["execution_id"], "status": "succeeded"}]
    execution = store.one("SELECT * FROM executions WHERE id=?", (dispatch["execution_id"],))
    assert execution["status"] == "succeeded"
    assert json.loads(execution["result_json"])["provider_success_only"] is True
    assert (
        store.one("SELECT acceptance_status FROM work_items WHERE id=?", (work,))[
            "acceptance_status"
        ]
        == "pending"
    )
    core.close()


def test_shared_client_provider_declines_unrouted_approval_and_cancels_exact_turn(
    tmp_path: Path,
) -> None:
    wheel = _qualified_wheel()
    executable = _fake_codex(tmp_path, approval_callback=True)
    provider = CodexAppServerProvider(
        wheel_path=wheel,
        codex_executable=executable,
        owner_key="approval-fixture",
        operation_timeout_seconds=15,
    )

    handle = dict(provider.dispatch(request(tmp_path)).handle)
    observation = provider.poll(handle)
    for _ in range(4):
        if observation.status != "running":
            break
        observation = provider.poll(handle)
    assert observation.status == "succeeded"
    assert observation.result["rejected_callback_count"] == 1
    provider.close()

    cancellation = CodexAppServerProvider(
        wheel_path=wheel,
        codex_executable=executable,
        owner_key="cancellation-fixture",
        operation_timeout_seconds=15,
    )
    cancel_handle = dict(cancellation.dispatch(request(tmp_path, execution_id="exe-cancel")).handle)
    cancelled = cancellation.cancel(cancel_handle)
    assert cancelled.status == "cancelled"
    assert cancelled.external_thread_id == cancel_handle["thread_id"]
    assert cancelled.external_task_id == cancel_handle["turn_id"]
    cancellation.close()
