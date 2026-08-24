from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import AuthorityDenied, InvalidTransition
from ..util import digest_json
from .contracts import EffectClass, TargetSnapshot


@dataclass(frozen=True)
class RegisteredSoftwareCommand:
    key: str
    effect_class: EffectClass
    argv: tuple[str, ...]
    timeout_seconds: int = 300
    allowed_exit_codes: frozenset[int] = frozenset({0})

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("registered command key is required")
        if self.effect_class not in {EffectClass.COMMAND, EffectClass.TEST, EffectClass.BUILD}:
            raise ValueError("registered command must be command, test, or build")
        if not self.argv or any(not isinstance(part, str) or not part for part in self.argv):
            raise ValueError("registered command requires a fixed nonempty argument vector")
        if self.timeout_seconds <= 0:
            raise ValueError("registered command timeout must be positive")
        if not self.allowed_exit_codes:
            raise ValueError("registered command requires at least one allowed exit code")


@dataclass(frozen=True)
class _SoftwareTargetConfig:
    repository_id: str
    repository_root: Path
    target_branch: str
    commands: Mapping[str, RegisteredSoftwareCommand]
    integration_root: Path | None
    release_root: Path | None
    preservation_root: Path | None


class SoftwareTargetProfile:
    """Factory-owned Git/software effects behind one fixed target-profile contract."""

    key = "software"
    effect_classes = frozenset(EffectClass)
    _workspace_types = frozenset({"candidate_lane", "verification_lane", "experiment_lane"})

    def __init__(
        self,
        store: Any,
        *,
        workspaces: Any,
        executions: Any,
        operations: Any,
        reconciliation: Any,
        releases: Any,
    ) -> None:
        self.store = store
        self._workspaces = workspaces
        self._executions = executions
        self._operations = operations
        self._reconciliation = reconciliation
        self._releases = releases
        self._targets: dict[str, _SoftwareTargetConfig] = {}
        self._registry_authority: object | None = None

    def workspace_path(self, workspace_id: str) -> Path:
        return self._workspaces.workspace_path(workspace_id)

    def repository_path(self, repository_id: str | None) -> Path:
        return self._workspaces.repository_path(repository_id)

    def git_revision(self, path: str | Path) -> str:
        return self._workspaces.git_revision(path)

    def git_tree(self, path: str | Path, revision: str = "HEAD") -> str:
        return self._workspaces.git_tree(path, revision)

    def git_is_clean(self, path: str | Path) -> bool:
        return self._workspaces.git_is_clean(path)

    def create_workspace(
        self,
        *,
        repository_id: str,
        mission_id: str,
        work_item_id: str | None,
        workspace_type: str,
        base_revision: str | None = None,
        writable_scope: list[str] | None = None,
        exclusions: list[str] | None = None,
        created_by_execution_id: str | None = None,
    ) -> str:
        """Restricted compatibility surface for controller and QA composition.

        Path roots and branch names remain repository policy. A non-target base
        is accepted only when it is an existing frozen candidate for this work.
        """

        repository, root, branch = self._validated_repository(repository_id)
        target_revision = self._git(root, "rev-parse", f"refs/heads/{branch}^{{commit}}")
        base = base_revision or target_revision
        if base != target_revision:
            if work_item_id is None:
                raise InvalidTransition("non-target workspace base requires bound work")
            candidate = self.store.one(
                """SELECT id FROM workspaces
                   WHERE repository_id=? AND work_item_id=? AND current_revision=?
                     AND status IN ('frozen','retained')
                   ORDER BY created_at DESC LIMIT 1""",
                (repository_id, work_item_id, base),
                required=False,
            )
            if candidate is None:
                raise InvalidTransition("workspace base is not a frozen target candidate")
        if repository["current_revision"] not in {None, target_revision}:
            raise InvalidTransition("repository current revision differs from target branch")
        return self._workspaces.create_workspace(
            repository_id=repository_id,
            mission_id=mission_id,
            work_item_id=work_item_id,
            workspace_type=workspace_type,
            base_revision=base,
            writable_scope=writable_scope,
            exclusions=exclusions,
            created_by_execution_id=created_by_execution_id,
        )

    def freeze_workspace(self, workspace_id: str, *, require_clean: bool = True) -> dict[str, Any]:
        return self._workspaces.freeze_workspace(workspace_id, require_clean=require_clean)

    def retire_workspace(self, workspace_id: str, *, force: bool = False) -> None:
        self._workspaces.retire_workspace(workspace_id, force=force)

    @staticmethod
    def _git(root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    @staticmethod
    def _resolved_git_path(root: Path, value: str) -> Path:
        path = Path(value)
        return (root / path).resolve() if not path.is_absolute() else path.resolve()

    def _validated_repository(self, repository_id: str) -> tuple[dict[str, Any], Path, str]:
        repository = self.store.one("SELECT * FROM repositories WHERE id=?", (repository_id,))
        root = Path(repository["path"]).resolve()
        top = Path(self._git(root, "rev-parse", "--show-toplevel")).resolve()
        if top != root:
            raise InvalidTransition("software target must be its registered Git top level")
        if self._git(root, "rev-parse", "--is-bare-repository") != "false":
            raise InvalidTransition("software target must be a non-bare primary checkout")
        git_dir = self._resolved_git_path(root, self._git(root, "rev-parse", "--git-dir"))
        common_dir = self._resolved_git_path(root, self._git(root, "rev-parse", "--git-common-dir"))
        if git_dir != common_dir:
            raise InvalidTransition("linked worktree cannot be software target authority")
        branch = str(repository["default_branch"])
        subprocess.run(
            ["git", "check-ref-format", f"refs/heads/{branch}"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        self._git(root, "rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}")
        return repository, root, branch

    def _bind_registry_authority(self, authority: object) -> None:
        if self._registry_authority is not None:
            raise InvalidTransition("software profile is already bound to a registry")
        self._registry_authority = authority

    def register_target(
        self,
        repository_id: str,
        *,
        commands: Sequence[RegisteredSoftwareCommand],
        integration_root: str | Path | None = None,
        release_root: str | Path | None = None,
        preservation_root: str | Path | None = None,
    ) -> None:
        _, root, branch = self._validated_repository(repository_id)
        if repository_id in self._targets:
            raise ValueError(f"software target is already registered: {repository_id}")
        command_map: dict[str, RegisteredSoftwareCommand] = {}
        for command in commands:
            if command.key in command_map:
                raise ValueError(f"software command is already registered: {command.key}")
            command_map[command.key] = command
        self._targets[repository_id] = _SoftwareTargetConfig(
            repository_id=repository_id,
            repository_root=root,
            target_branch=branch,
            commands=command_map,
            integration_root=Path(integration_root).resolve() if integration_root else None,
            release_root=Path(release_root).resolve() if release_root else None,
            preservation_root=Path(preservation_root).resolve() if preservation_root else None,
        )

    def _config(self, target_id: str) -> _SoftwareTargetConfig:
        try:
            return self._targets[target_id]
        except KeyError as exc:
            raise AuthorityDenied(f"software target is not registered: {target_id}") from exc

    def snapshot(self, target_id: str) -> TargetSnapshot:
        config = self._config(target_id)
        repository, root, branch = self._validated_repository(target_id)
        if root != config.repository_root or branch != config.target_branch:
            raise InvalidTransition("software target registration changed")
        revision = self._git(root, "rev-parse", f"refs/heads/{branch}^{{commit}}")
        tree = self._git(root, "rev-parse", f"{revision}^{{tree}}")
        checked_out_branch = self._git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
        if checked_out_branch != branch:
            raise InvalidTransition("software target branch is not checked out at its primary root")
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--binary",
                "--no-color",
                "--no-ext-diff",
                "--full-index",
                revision,
                "--",
            ],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout.split(b"\0")
        untracked_entries: list[dict[str, Any]] = []
        for encoded in sorted(value for value in untracked if value):
            relative = encoded.decode("utf-8", errors="surrogateescape")
            path = root / relative
            if path.is_symlink():
                payload = path.readlink().as_posix().encode("utf-8", errors="surrogateescape")
                kind = "symlink"
            elif path.is_file():
                payload = path.read_bytes()
                kind = "file"
            else:
                payload = b""
                kind = "other"
            untracked_entries.append(
                {
                    "path": relative,
                    "kind": kind,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        attributes = {
            "repository_root": str(root),
            "target_branch": branch,
            "checked_out_branch": checked_out_branch,
            "tree": tree,
            "working_tree_status_root": hashlib.sha256(status).hexdigest(),
            "working_tree_content_root": digest_json(
                {
                    "diff_sha256": hashlib.sha256(diff).hexdigest(),
                    "untracked": untracked_entries,
                }
            ),
            "repository_state_version": int(repository["state_version"]),
        }
        currentness_root = digest_json(
            {
                "profile": self.key,
                "target_id": target_id,
                "revision": revision,
                "attributes": attributes,
            }
        )
        return TargetSnapshot(
            profile_key=self.key,
            target_id=target_id,
            revision=revision,
            currentness_root=currentness_root,
            attributes=attributes,
        )

    @staticmethod
    def _arguments(
        arguments: Mapping[str, Any],
        *,
        required: set[str],
        optional: set[str] | None = None,
    ) -> None:
        keys = set(arguments)
        missing = required - keys
        extra = keys - required - (optional or set())
        if missing:
            raise ValueError(f"target effect is missing arguments: {sorted(missing)}")
        if extra:
            raise AuthorityDenied(f"target effect has unregistered arguments: {sorted(extra)}")

    @staticmethod
    def _string_list(value: Any, *, name: str) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise ValueError(f"{name} must be a sequence of strings")
        result = [str(item) for item in value]
        if any(not item for item in result):
            raise ValueError(f"{name} cannot contain empty values")
        return result

    def _workspace_effect(
        self, config: _SoftwareTargetConfig, expected_revision: str, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        operation = str(arguments.get("operation") or "")
        if operation == "create":
            self._arguments(
                arguments,
                required={"operation", "mission_id", "workspace_type"},
                optional={"work_item_id", "writable_scope", "exclusions"},
            )
            workspace_type = str(arguments["workspace_type"])
            if workspace_type not in self._workspace_types:
                raise AuthorityDenied("workspace type is not registered by the software profile")
            workspace_id = self._workspaces.create_workspace(
                repository_id=config.repository_id,
                mission_id=str(arguments["mission_id"]),
                work_item_id=(
                    str(arguments["work_item_id"]) if arguments.get("work_item_id") else None
                ),
                workspace_type=workspace_type,
                base_revision=expected_revision,
                writable_scope=self._string_list(
                    arguments.get("writable_scope"), name="writable_scope"
                ),
                exclusions=self._string_list(arguments.get("exclusions"), name="exclusions"),
            )
            workspace = self.store.one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
            return {
                "workspace_id": workspace_id,
                "base_revision": workspace["base_revision"],
                "current_revision": workspace["current_revision"],
                "status": workspace["status"],
            }
        if operation == "freeze":
            self._arguments(arguments, required={"operation", "workspace_id"})
            workspace = self._workspace_for_target(config, str(arguments["workspace_id"]))
            if workspace["base_revision"] != expected_revision:
                raise InvalidTransition("candidate workspace has a stale target base")
            return self._workspaces.freeze_workspace(str(arguments["workspace_id"]))
        raise AuthorityDenied("workspace operation is not registered")

    def _registered_command(
        self, config: _SoftwareTargetConfig, key: Any, effect_class: EffectClass
    ) -> RegisteredSoftwareCommand:
        command = config.commands.get(str(key))
        if command is None or command.effect_class is not effect_class:
            raise AuthorityDenied(f"software {effect_class.value} command is not registered: {key}")
        return command

    def _command_effect(
        self,
        config: _SoftwareTargetConfig,
        effect_class: EffectClass,
        expected_revision: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self._arguments(arguments, required={"execution_id", "generation", "command_key"})
        command = self._registered_command(config, arguments["command_key"], effect_class)
        execution = self.store.one(
            """SELECT e.*,w.repository_id,w.base_revision FROM executions e
               JOIN workspaces w ON w.id=e.workspace_id WHERE e.id=?""",
            (str(arguments["execution_id"]),),
        )
        if execution["repository_id"] != config.repository_id:
            raise AuthorityDenied("command execution workspace belongs to another target")
        if execution["base_revision"] != expected_revision:
            raise InvalidTransition("command execution workspace has a stale target base")
        return self._executions.run_command(
            str(arguments["execution_id"]),
            command.argv,
            generation=int(arguments["generation"]),
            timeout_seconds=command.timeout_seconds,
            allowed_exit_codes=set(command.allowed_exit_codes),
        )

    def _assert_inventory_target(
        self, config: _SoftwareTargetConfig, cleanup_item_id: str
    ) -> dict[str, Any]:
        inventory = self.store.one(
            """SELECT i.* FROM cleanup_items_v2 c
               JOIN repository_inventories_v2 i ON i.id=c.inventory_id WHERE c.id=?""",
            (cleanup_item_id,),
        )
        if Path(inventory["repository_root"]).resolve() != config.repository_root:
            raise AuthorityDenied("cleanup or integration item belongs to another target")
        return inventory

    def _integration_effect(
        self, config: _SoftwareTargetConfig, expected_revision: str, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        operation = str(arguments.get("operation") or "")
        if operation == "prepare":
            self._arguments(
                arguments,
                required={
                    "operation",
                    "cleanup_item_id",
                    "preservation_bundle_id",
                    "validation_key",
                },
            )
            if config.integration_root is None:
                raise AuthorityDenied("software target has no registered integration root")
            self._assert_inventory_target(config, str(arguments["cleanup_item_id"]))
            command = config.commands.get(str(arguments["validation_key"]))
            if command is None or command.effect_class not in {EffectClass.TEST, EffectClass.BUILD}:
                raise AuthorityDenied("integration validation command is not registered")
            return self._reconciliation.prepare_integration(
                str(arguments["cleanup_item_id"]),
                preservation_bundle_id=str(arguments["preservation_bundle_id"]),
                target_branch=config.target_branch,
                worktree_root=config.integration_root,
                validation_command=command.argv,
            )
        if operation == "publish":
            self._arguments(
                arguments,
                required={"operation", "candidate_id"},
                optional={"post_publish_validation_key"},
            )
            candidate = self.store.one(
                "SELECT * FROM integration_candidates_v2 WHERE id=?",
                (str(arguments["candidate_id"]),),
            )
            if (
                Path(candidate["repository_root"]).resolve() != config.repository_root
                or candidate["target_branch"] != config.target_branch
            ):
                raise AuthorityDenied("integration candidate belongs to another target")
            if candidate["target_head_before"] != expected_revision:
                raise InvalidTransition("integration candidate was prepared for a stale target")
            validation_key = arguments.get("post_publish_validation_key")
            command = (
                self._registered_command(config, validation_key, EffectClass.TEST)
                if validation_key
                else None
            )
            return self._reconciliation.publish_integration(
                str(arguments["candidate_id"]),
                post_publish_validation=command.argv if command else None,
            )
        raise AuthorityDenied("integration operation is not registered")

    def _workspace_for_target(
        self, config: _SoftwareTargetConfig, workspace_id: str
    ) -> dict[str, Any]:
        workspace = self.store.one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
        if workspace["repository_id"] != config.repository_id:
            raise AuthorityDenied("workspace belongs to another software target")
        return workspace

    def _release_effect(
        self, config: _SoftwareTargetConfig, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        if config.release_root is None:
            raise AuthorityDenied("software target has no registered release root")
        operation = str(arguments.get("operation") or "")
        if operation == "stage":
            self._arguments(
                arguments,
                required={
                    "operation",
                    "workspace_id",
                    "mission_id",
                    "implementer_session_id",
                },
            )
            workspace = self._workspace_for_target(config, str(arguments["workspace_id"]))
            if workspace["status"] != "frozen" or not workspace["current_revision"]:
                raise InvalidTransition(
                    "release source workspace must be an exact frozen candidate"
                )
            actual_revision = self._workspaces.git_revision(workspace["path"])
            if actual_revision != workspace[
                "current_revision"
            ] or not self._workspaces.git_is_clean(workspace["path"]):
                raise InvalidTransition("release source workspace changed after candidate freeze")
            release = self._releases.stage(
                source_root=workspace["path"],
                release_root=config.release_root,
                source_revision=actual_revision,
                source_tree_root=self._workspaces.git_tree(workspace["path"], actual_revision),
                mission_id=str(arguments["mission_id"]),
                implementer_session_id=str(arguments["implementer_session_id"]),
                required_probes=(
                    {"key": "candidate-behavior", "type": "test"},
                    {"key": "protected-capabilities", "type": "protected_capability"},
                ),
                protected_capabilities=("target-currentness", "release-isolation"),
            )
            self._assert_release_target(config, str(release["id"]))
            return release
        if operation == "activate":
            self._arguments(arguments, required={"operation", "release_id"})
            self._assert_release_target(config, str(arguments["release_id"]))
            return self._releases.activate(
                str(arguments["release_id"]), release_root=config.release_root
            )
        raise AuthorityDenied("release operation is not registered")

    def _assert_release_target(
        self, config: _SoftwareTargetConfig, release_id: str
    ) -> dict[str, Any]:
        release = self.store.one("SELECT * FROM immutable_releases_v2 WHERE id=?", (release_id,))
        if config.release_root is None:
            raise AuthorityDenied("software target has no registered release root")
        if Path(release["release_path"]).resolve().parent != config.release_root:
            raise AuthorityDenied("release belongs to another software target root")
        workspace = self.store.one(
            """SELECT id FROM workspaces WHERE repository_id=? AND current_revision=?
               ORDER BY created_at LIMIT 1""",
            (config.repository_id, release["source_revision"]),
            required=False,
        )
        if workspace is None:
            raise AuthorityDenied("release source is not a candidate of this software target")
        return release

    def _cleanup_effect(
        self, config: _SoftwareTargetConfig, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        operation = str(arguments.get("operation") or "")
        if operation == "reconcile":
            self._arguments(
                arguments,
                required={"operation", "active_writers", "classifications"},
                optional={"mission_id"},
            )
            if config.preservation_root is None:
                raise AuthorityDenied("software target has no registered preservation root")
            active_writers = arguments["active_writers"]
            classifications = arguments["classifications"]
            if isinstance(active_writers, (str, bytes)) or not isinstance(active_writers, Sequence):
                raise ValueError("active_writers must be a sequence")
            if isinstance(classifications, (str, bytes)) or not isinstance(
                classifications, Sequence
            ):
                raise ValueError("classifications must be a sequence")
            return self._reconciliation.reconcile(
                repository_root=config.repository_root,
                mission_id=str(arguments["mission_id"]) if arguments.get("mission_id") else None,
                active_writers=[dict(value) for value in active_writers],
                classifications=[dict(value) for value in classifications],
                preservation_directory=config.preservation_root,
            )
        if operation == "retire_workspace":
            self._arguments(arguments, required={"operation", "workspace_id"})
            self._workspace_for_target(config, str(arguments["workspace_id"]))
            self._workspaces.retire_workspace(str(arguments["workspace_id"]), force=False)
            return {"workspace_id": str(arguments["workspace_id"]), "status": "retired"}
        if operation == "execute_retirement":
            self._arguments(
                arguments,
                required={"operation", "cleanup_item_id", "preservation_bundle_id"},
            )
            self._assert_inventory_target(config, str(arguments["cleanup_item_id"]))
            return self._operations.execute_retirement(
                str(arguments["cleanup_item_id"]),
                preservation_bundle_id=str(arguments["preservation_bundle_id"]),
            )
        raise AuthorityDenied("cleanup operation is not registered")

    def _rollback_effect(
        self, config: _SoftwareTargetConfig, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        self._arguments(arguments, required={"release_id", "evidence_ids"})
        if config.release_root is None:
            raise AuthorityDenied("software target has no registered release root")
        self._assert_release_target(config, str(arguments["release_id"]))
        evidence_ids = self._string_list(arguments["evidence_ids"], name="evidence_ids")
        if not evidence_ids:
            raise ValueError("release rollback requires evidence")
        return self._operations.rollback_release(
            str(arguments["release_id"]),
            release_root=config.release_root,
            evidence_ids=evidence_ids,
        )

    def _execute_effect(
        self,
        authority: object,
        effect_class: EffectClass,
        target_id: str,
        *,
        expected_revision: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if authority is not self._registry_authority:
            raise AuthorityDenied("software target effects require registry authority")
        config = self._config(target_id)
        if effect_class is EffectClass.WORKSPACE:
            return self._workspace_effect(config, expected_revision, arguments)
        if effect_class in {EffectClass.COMMAND, EffectClass.TEST, EffectClass.BUILD}:
            return self._command_effect(config, effect_class, expected_revision, arguments)
        if effect_class is EffectClass.INTEGRATION:
            return self._integration_effect(config, expected_revision, arguments)
        if effect_class is EffectClass.RELEASE:
            return self._release_effect(config, arguments)
        if effect_class is EffectClass.CLEANUP:
            return self._cleanup_effect(config, arguments)
        if effect_class is EffectClass.ROLLBACK:
            return self._rollback_effect(config, arguments)
        raise AuthorityDenied(f"software profile does not own effect: {effect_class.value}")
