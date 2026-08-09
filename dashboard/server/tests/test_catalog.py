from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from software_factory_dashboard.catalog import (
    CatalogError,
    CatalogStore,
    canonical_git_root,
    discover_catalog,
)


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.store = CatalogStore(self.base / "state" / "projects.json")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_repo(self, name: str, *, tracker: bool = False, parent: Path | None = None) -> Path:
        root = (parent or self.base) / name
        root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "catalog@test.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Catalog Test"], check=True)
        (root / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        if tracker:
            (root / "docs").mkdir()
            (root / "docs" / f"{name}-implementation-tracker.md").write_text(
                "# Candidate path only\n",
                encoding="utf-8",
            )
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
        return root

    @staticmethod
    def project(project_id: str, label: str, root: Path, **extra: object) -> dict[str, object]:
        return {
            "id": project_id,
            "label": label,
            "root": str(root),
            "tracker_patterns": [],
            "description": None,
            **extra,
        }

    def test_three_project_lifecycle_is_sorted_replayable_and_catalog_only(self) -> None:
        roots = {
            project_id: self.make_repo(project_id, tracker=True)
            for project_id in ("zeta", "alpha", "middle")
        }
        loaded = self.store.load()
        for project_id in ("zeta", "alpha", "middle"):
            loaded = self.store.register(
                loaded.fingerprint,
                self.project(project_id, project_id.title(), roots[project_id]),
            )

        self.assertEqual([project.id for project in loaded.state.projects], ["alpha", "middle", "zeta"])
        loaded = self.store.update_presentation(
            loaded.fingerprint,
            "middle",
            {"label": "Middle Project", "description": "Presentation metadata only."},
        )
        with self.assertRaisesRegex(CatalogError, "confirmation"):
            self.store.set_archived(loaded.fingerprint, "middle", True, confirmation="middle")
        loaded = self.store.set_archived(
            loaded.fingerprint,
            "middle",
            True,
            confirmation="archive:middle",
        )
        self.assertTrue(next(project for project in loaded.state.projects if project.id == "middle").archived)
        loaded = self.store.set_archived(loaded.fingerprint, "middle", False)

        replayed = CatalogStore(self.store.path).load()
        self.assertEqual(replayed.state, loaded.state)
        middle = next(project for project in replayed.state.projects if project.id == "middle")
        self.assertFalse(middle.archived)
        self.assertEqual(stat.S_IMODE(self.store.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.store.path.parent.stat().st_mode), 0o700)
        self.assertTrue(self.store.previous_path.is_file())
        serialized = json.loads(self.store.path.read_text(encoding="utf-8"))
        self.assertEqual(set(serialized), {"version", "projects"})
        self.assertNotIn("status", json.dumps(serialized))
        self.assertNotIn("run", json.dumps(serialized))

    def test_stale_duplicate_overlap_symlink_traversal_and_operational_fields_are_rejected(self) -> None:
        first = self.make_repo("first")
        second = self.make_repo("second")
        loaded = self.store.load()
        loaded = self.store.register(loaded.fingerprint, self.project("first", "First", first))

        changed_fingerprint = ("0" if loaded.fingerprint[0] != "0" else "1") + loaded.fingerprint[1:]
        with self.assertRaisesRegex(CatalogError, "refresh") as stale:
            self.store.register(changed_fingerprint, self.project("second", "Second", second))
        self.assertEqual(stale.exception.status, 409)
        with self.assertRaisesRegex(CatalogError, "64-character"):
            self.store.register("not-a-fingerprint", self.project("second", "Second", second))
        with self.assertRaisesRegex(CatalogError, "64-character"):
            self.store.register(42, self.project("second", "Second", second))  # type: ignore[arg-type]
        with self.assertRaisesRegex(CatalogError, "already exists"):
            self.store.register(loaded.fingerprint, self.project("first", "Duplicate", second))

        nested = self.make_repo("nested", parent=first)
        with self.assertRaisesRegex(CatalogError, "non-nested"):
            self.store.register(loaded.fingerprint, self.project("nested", "Nested", nested))

        alias = self.base / "second-alias"
        alias.symlink_to(second, target_is_directory=True)
        with self.assertRaisesRegex(CatalogError, "symlinks"):
            canonical_git_root(str(alias))

        non_git = self.base / "not-git"
        non_git.mkdir()
        with self.assertRaises(CatalogError):
            canonical_git_root(str(non_git))

        with self.assertRaisesRegex(CatalogError, "do not traverse"):
            self.store.register(
                loaded.fingerprint,
                self.project(
                    "escape",
                    "Escape",
                    second,
                    tracker_patterns=["../outside.md"],
                ),
            )
        with self.assertRaisesRegex(CatalogError, "cannot store"):
            self.store.register(
                loaded.fingerprint,
                self.project("truth-copy", "Truth copy", second, status="in-progress"),
            )

    def test_prior_file_recovers_invalid_current_but_not_unsafe_permissions(self) -> None:
        root = self.make_repo("recover")
        loaded = self.store.register(
            self.store.load().fingerprint,
            self.project("recover", "Recover", root),
        )
        loaded = self.store.update_presentation(
            loaded.fingerprint,
            "recover",
            {"label": "Updated"},
        )
        self.store.path.write_text("{broken", encoding="utf-8")
        self.store.path.chmod(0o600)

        recovered = CatalogStore(self.store.path).load()
        self.assertTrue(recovered.recovered_from_previous)
        self.assertEqual(recovered.state.projects[0].label, "Recover")
        with self.assertRaisesRegex(CatalogError, "repair it") as read_only:
            self.store.update_presentation(recovered.fingerprint, "recover", {"label": "Unsafe"})
        self.assertEqual(read_only.exception.status, 409)

        self.store.path.chmod(0o644)
        with self.assertRaisesRegex(CatalogError, "group or others"):
            CatalogStore(self.store.path).load()

        unsupported_path = self.base / "unsupported.json"
        unsupported_path.write_text('{"projects":[],"version":99}\n', encoding="utf-8")
        unsupported_path.chmod(0o600)
        with self.assertRaisesRegex(CatalogError, "not supported"):
            CatalogStore(unsupported_path).load()

        oversized_projects = self.base / "oversized-projects.json"
        oversized_projects.write_text(
            json.dumps({"projects": [{}] * 201, "version": 1}),
            encoding="utf-8",
        )
        oversized_projects.chmod(0o600)
        with self.assertRaisesRegex(CatalogError, "200-project"):
            CatalogStore(oversized_projects).load()

        catalog_target = self.base / "catalog-target.json"
        catalog_target.write_text('{"projects":[],"version":1}\n', encoding="utf-8")
        catalog_target.chmod(0o600)
        catalog_alias = self.base / "catalog-alias.json"
        catalog_alias.symlink_to(catalog_target)
        with self.assertRaisesRegex(CatalogError, "non-symlink"):
            CatalogStore(catalog_alias).load()

        dangling_alias = self.base / "dangling-catalog.json"
        dangling_alias.symlink_to(self.base / "missing-catalog.json")
        with self.assertRaisesRegex(CatalogError, "non-symlink"):
            CatalogStore(dangling_alias).load()

    def test_failed_atomic_replacement_preserves_current_catalog(self) -> None:
        root = self.make_repo("atomic")
        loaded = self.store.register(
            self.store.load().fingerprint,
            self.project("atomic", "Atomic", root),
        )
        original_replace = os.replace

        def fail_current(
            source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            target: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        ) -> None:
            if Path(target) == self.store.path:
                raise OSError("simulated atomic replacement failure")
            original_replace(source, target)

        with patch("software_factory_dashboard.catalog.os.replace", side_effect=fail_current):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.store.update_presentation(loaded.fingerprint, "atomic", {"label": "Changed"})

        current = self.store.load()
        self.assertEqual(current.state.projects[0].label, "Atomic")
        self.assertEqual(list(self.store.path.parent.glob(".projects.json.*")), [])

    def test_one_missing_project_does_not_erase_healthy_discovery(self) -> None:
        healthy = self.make_repo("healthy", tracker=True)
        missing = self.make_repo("missing")
        loaded = self.store.load()
        loaded = self.store.register(
            loaded.fingerprint,
            self.project("healthy", "Healthy", healthy),
        )
        loaded = self.store.register(
            loaded.fingerprint,
            self.project("missing", "Missing", missing),
        )
        missing.rename(self.base / "moved-away")

        projects = discover_catalog(self.store.load(), include_archived=True)
        by_id = {project["id"]: project for project in projects}
        self.assertEqual(by_id["healthy"]["discovery"]["status"], "available")
        self.assertEqual(
            by_id["healthy"]["discovery"]["trackers"]["candidates"],
            ["docs/healthy-implementation-tracker.md"],
        )
        self.assertEqual(by_id["missing"]["discovery"]["status"], "unavailable")
        self.assertEqual(by_id["missing"]["discovery"]["errors"][0]["code"], "missing_project_root")


if __name__ == "__main__":
    unittest.main()
