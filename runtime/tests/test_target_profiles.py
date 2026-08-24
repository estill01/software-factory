from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from software_factory import (
    AuthorityDenied,
    CoreService,
    EffectClass,
    InvalidTransition,
    RegisteredSoftwareCommand,
    Store,
    TargetProfileRegistry,
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def initialize_repository(root: Path) -> str:
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Target Profile Test")
    git(root, "config", "user.email", "target-profile@example.invalid")
    (root / "src").mkdir()
    (root / "src" / "base.py").write_text("BASE = True\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    return git(root, "rev-parse", "HEAD")


def target_runtime(tmp_path: Path) -> tuple[CoreService, str, Path]:
    repository = tmp_path / "target"
    revision = initialize_repository(repository)
    core = CoreService(Store(tmp_path / "factory.sqlite3"))
    repository_id = core.register_repository(
        repository,
        default_branch="main",
        current_revision=revision,
        workspace_policy={"workspace_root": str(tmp_path / "workspaces")},
    )
    core.software_profile.register_target(
        repository_id,
        commands=[
            RegisteredSoftwareCommand(
                key="implement",
                effect_class=EffectClass.COMMAND,
                argv=(
                    "bash",
                    "-lc",
                    "printf 'RESULT = 1\\n' > src/result.py && git add src/result.py && git commit -m result",
                ),
            ),
            RegisteredSoftwareCommand(
                key="focused-test",
                effect_class=EffectClass.TEST,
                argv=(
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert Path('src').is_dir()",
                ),
            ),
            RegisteredSoftwareCommand(
                key="build",
                effect_class=EffectClass.BUILD,
                argv=(
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert Path('src').is_dir()",
                ),
            ),
        ],
        integration_root=tmp_path / "integration",
        release_root=tmp_path / "releases",
        preservation_root=tmp_path / "preservation",
    )
    return core, repository_id, repository


def execute(
    core: CoreService,
    repository_id: str,
    effect_class: EffectClass,
    arguments: dict,
):
    snapshot = core.target_profiles.snapshot("software", repository_id)
    return core.target_profiles.execute(
        "software",
        effect_class,
        repository_id,
        expected_revision=snapshot.revision,
        expected_currentness_root=snapshot.currentness_root,
        arguments=arguments,
    )


def create_candidate_workspace(
    core: CoreService, repository_id: str, *, mission_id: str
) -> tuple[str, str]:
    snapshot = core.target_profiles.snapshot("software", repository_id)
    created = core.target_profiles.execute(
        "software",
        EffectClass.WORKSPACE,
        repository_id,
        expected_revision=snapshot.revision,
        expected_currentness_root=snapshot.currentness_root,
        arguments={
            "operation": "create",
            "mission_id": mission_id,
            "workspace_type": "candidate_lane",
            "writable_scope": ["src"],
        },
    )
    return str(created.result["workspace_id"]), snapshot.revision


def test_registry_rejects_unowned_effects_self_acceptance_and_worktree_authority(
    tmp_path: Path,
) -> None:
    core, repository_id, repository = target_runtime(tmp_path)
    snapshot = core.target_profiles.snapshot("software", repository_id)
    assert core.target_profiles.keys() == ("software",)
    assert snapshot.revision == git(repository, "rev-parse", "refs/heads/main")
    assert not hasattr(core.software_profile, "accept")
    assert not hasattr(core.software_profile, "execute_effect")
    with pytest.raises(AttributeError):
        core.__getattr__("execute_effect")

    with pytest.raises(AuthorityDenied, match="fixed effect class"):
        core.target_profiles.execute(  # type: ignore[arg-type]
            "software",
            "accept",
            repository_id,
            expected_revision=snapshot.revision,
            expected_currentness_root=snapshot.currentness_root,
        )
    with pytest.raises(AuthorityDenied, match="not registered"):
        core.target_profiles.snapshot("unknown", repository_id)

    linked = tmp_path / "linked"
    git(repository, "worktree", "add", "-b", "linked-target", str(linked), "main")
    linked_id = core.register_repository(
        linked,
        default_branch="linked-target",
        current_revision=git(linked, "rev-parse", "HEAD"),
    )
    with pytest.raises(InvalidTransition, match="linked worktree"):
        core.software_profile.register_target(linked_id, commands=[])

    class CommandOnly:
        key = "command-only"
        effect_classes = frozenset({EffectClass.COMMAND})

        def snapshot(self, target_id: str):
            return snapshot

        def _execute_effect(self, *args, **kwargs):
            raise AssertionError("unowned effect reached profile")

    partial = TargetProfileRegistry()
    partial.register(CommandOnly())
    with pytest.raises(AuthorityDenied, match="does not own"):
        partial.execute(
            "command-only",
            EffectClass.BUILD,
            repository_id,
            expected_revision=snapshot.revision,
            expected_currentness_root=snapshot.currentness_root,
        )


def test_workspace_and_registered_command_effects_are_exact_currentness_fenced(
    tmp_path: Path,
) -> None:
    core, repository_id, repository = target_runtime(tmp_path)
    mission = core.create_mission(title="Profile mission", objective="Run a fixed command")
    initial = core.target_profiles.snapshot("software", repository_id)
    with pytest.raises(AuthorityDenied, match="unregistered arguments"):
        core.target_profiles.execute(
            "software",
            EffectClass.WORKSPACE,
            repository_id,
            expected_revision=initial.revision,
            expected_currentness_root=initial.currentness_root,
            arguments={
                "operation": "create",
                "mission_id": mission,
                "workspace_type": "candidate_lane",
                "workspace_root": str(tmp_path / "injected"),
            },
        )

    workspace_id, base_revision = create_candidate_workspace(
        core, repository_id, mission_id=mission
    )
    execution_id = core.executions.queue_execution(
        mission_id=mission,
        execution_type="profile_command",
        idempotency_key="profile-command",
        workspace_id=workspace_id,
    )
    generation = core.executions.acquire_leases(
        execution_id,
        [{"kind": "workspace", "key": workspace_id, "mode": "exclusive"}],
    )
    command = execute(
        core,
        repository_id,
        EffectClass.COMMAND,
        {
            "execution_id": execution_id,
            "generation": generation,
            "command_key": "implement",
        },
    )
    assert command.result["status"] == "succeeded"
    assert command.result["source_revision_before"] == base_revision
    for effect_class, command_key in (
        (EffectClass.TEST, "focused-test"),
        (EffectClass.BUILD, "build"),
    ):
        validation_execution = core.executions.queue_execution(
            mission_id=mission,
            execution_type=f"profile_{effect_class.value}",
            idempotency_key=f"profile-{effect_class.value}",
            workspace_id=workspace_id,
        )
        validation_generation = core.executions.acquire_leases(
            validation_execution,
            [{"kind": "workspace", "key": workspace_id, "mode": "exclusive"}],
        )
        validation = execute(
            core,
            repository_id,
            effect_class,
            {
                "execution_id": validation_execution,
                "generation": validation_generation,
                "command_key": command_key,
            },
        )
        assert validation.result["status"] == "succeeded"
    with pytest.raises(AuthorityDenied, match="not registered"):
        execute(
            core,
            repository_id,
            EffectClass.COMMAND,
            {
                "execution_id": execution_id,
                "generation": generation,
                "command_key": "bash -lc injected",
            },
        )

    stale = core.target_profiles.snapshot("software", repository_id)
    (repository / "src" / "main.py").write_text("MAIN = 2\n", encoding="utf-8")
    git(repository, "add", "src/main.py")
    git(repository, "commit", "-m", "advance target")
    with pytest.raises(InvalidTransition, match="revision changed"):
        core.target_profiles.execute(
            "software",
            EffectClass.WORKSPACE,
            repository_id,
            expected_revision=stale.revision,
            expected_currentness_root=stale.currentness_root,
            arguments={
                "operation": "create",
                "mission_id": mission,
                "workspace_type": "candidate_lane",
            },
        )


def test_integration_uses_registered_validation_and_branch_currentness(tmp_path: Path) -> None:
    core, repository_id, repository = target_runtime(tmp_path)
    git(repository, "switch", "-c", "candidate")
    (repository / "src" / "candidate.py").write_text("CANDIDATE = True\n", encoding="utf-8")
    git(repository, "add", "src/candidate.py")
    git(repository, "commit", "-m", "candidate")
    git(repository, "switch", "main")
    inventory = core.operations.inventory_repository(repository_root=repository)
    bundle = core.operations.preserve_repository(
        inventory["id"], output_directory=tmp_path / "integration-preservation"
    )
    item = core.operations.plan_cleanup_item(
        inventory["id"],
        item_type="branch",
        item_key="candidate",
        classification="accepted",
        disposition="integrate",
        evidence={"review": "independent"},
    )

    prepared = execute(
        core,
        repository_id,
        EffectClass.INTEGRATION,
        {
            "operation": "prepare",
            "cleanup_item_id": item["id"],
            "preservation_bundle_id": bundle["id"],
            "validation_key": "focused-test",
        },
    )
    assert prepared.result["status"] == "accepted"
    published = execute(
        core,
        repository_id,
        EffectClass.INTEGRATION,
        {"operation": "publish", "candidate_id": prepared.result["id"]},
    )
    assert published.result["status"] == "published"
    assert published.after.revision == prepared.result["candidate_head"]
    assert (repository / "src" / "candidate.py").is_file()


def test_release_cleanup_and_rollback_remain_external_acceptance_gated(tmp_path: Path) -> None:
    core, repository_id, _ = target_runtime(tmp_path)
    mission = core.create_mission(title="Release mission", objective="Stage and roll back")
    workspace_id, _ = create_candidate_workspace(core, repository_id, mission_id=mission)
    execution_id = core.executions.queue_execution(
        mission_id=mission,
        execution_type="release_candidate",
        idempotency_key="release-candidate",
        workspace_id=workspace_id,
    )
    generation = core.executions.acquire_leases(
        execution_id,
        [{"kind": "workspace", "key": workspace_id, "mode": "exclusive"}],
    )
    execute(
        core,
        repository_id,
        EffectClass.COMMAND,
        {
            "execution_id": execution_id,
            "generation": generation,
            "command_key": "implement",
        },
    )
    frozen = execute(
        core,
        repository_id,
        EffectClass.WORKSPACE,
        {"operation": "freeze", "workspace_id": workspace_id},
    )
    assert frozen.result["revision"] != frozen.before.revision
    workspace_path = core.workspace_owner.workspace_path(workspace_id)
    dirty_after_freeze = workspace_path / "dirty-after-freeze"
    dirty_after_freeze.write_text("not staged\n", encoding="utf-8")
    with pytest.raises(InvalidTransition, match="changed after candidate freeze"):
        execute(
            core,
            repository_id,
            EffectClass.RELEASE,
            {"operation": "stage", "workspace_id": workspace_id, "mission_id": mission},
        )
    dirty_after_freeze.unlink()
    staged = execute(
        core,
        repository_id,
        EffectClass.RELEASE,
        {"operation": "stage", "workspace_id": workspace_id, "mission_id": mission},
    )
    other_repository = tmp_path / "other-target"
    other_revision = initialize_repository(other_repository)
    other_id = core.register_repository(
        other_repository,
        default_branch="main",
        current_revision=other_revision,
        workspace_policy={"workspace_root": str(tmp_path / "other-workspaces")},
    )
    core.software_profile.register_target(
        other_id,
        commands=[],
        integration_root=tmp_path / "other-integration",
        release_root=tmp_path / "other-releases",
        preservation_root=tmp_path / "other-preservation",
    )
    with pytest.raises(AuthorityDenied, match="another software target root"):
        execute(
            core,
            other_id,
            EffectClass.RELEASE,
            {"operation": "activate", "release_id": staged.result["id"]},
        )
    with pytest.raises(InvalidTransition, match="independent review"):
        execute(
            core,
            repository_id,
            EffectClass.RELEASE,
            {"operation": "activate", "release_id": staged.result["id"]},
        )

    core.operations.review_release(
        staged.result["id"],
        reviewer_session_id="independent-reviewer",
        disposition="accepted",
        findings={"currentness": "exact"},
        evidence_ids=["review-evidence"],
    )
    activated = execute(
        core,
        repository_id,
        EffectClass.RELEASE,
        {"operation": "activate", "release_id": staged.result["id"]},
    )
    assert activated.result["status"] == "active"
    rolled_back = execute(
        core,
        repository_id,
        EffectClass.ROLLBACK,
        {"release_id": staged.result["id"], "evidence_ids": ["rollback-evidence"]},
    )
    assert rolled_back.result["status"] == "rolled_back"

    reconciled = execute(
        core,
        repository_id,
        EffectClass.CLEANUP,
        {"operation": "reconcile", "active_writers": [], "classifications": []},
    )
    assert reconciled.result["preservation_bundle"]["verified"] == 1
    with pytest.raises(AuthorityDenied, match="unregistered arguments"):
        execute(
            core,
            repository_id,
            EffectClass.CLEANUP,
            {
                "operation": "reconcile",
                "active_writers": [],
                "classifications": [],
                "preservation_directory": str(tmp_path / "injected"),
            },
        )
