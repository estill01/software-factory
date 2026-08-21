from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test_ids(root: Path) -> set[str]:
    identifiers: set[str] = set()
    for path in sorted(root.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test"
            ):
                identifiers.add(f"{path.name}::{node.name}")
    return identifiers


_DOMAIN_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mission_continuation", ("mission", "range", "terminal", "obligation", "continuation")),
    ("multi_agent_execution", ("agent", "assignment", "lease", "fenc", "workspace", "dispatch")),
    ("qa_acceptance", ("qa", "review", "candidate", "accept", "evidence")),
    ("supervision_adaptation", ("supervis", "incident", "adaptive", "contain", "decision_policy")),
    ("signals_learning", ("signal", "failure_mode", "success_mode", "classifier", "pattern")),
    ("reflection_experiments", ("reflection", "hypothesis", "experiment", "counterexample")),
    ("program_evolution", ("program_evolution", "successor", "portfolio", "tracker_author")),
    ("selection_quality_rsi", ("selection", "selector", "feature_choice", "design_choice")),
    ("release_refresh_rollback", ("release", "refresh", "rollback", "activation")),
    ("systemic_recovery", ("systemic", "recovery", "resume", "factory_defect")),
    ("cleanup_reconciliation", ("cleanup", "reconcile", "preserv", "retire", "worktree")),
    ("reporting_notifications", ("report", "mail", "notification", "roundup", "readback")),
    ("operator_api_ui", ("dashboard", "factory_floor", "api", "server", "operator")),
    ("migration_parity_cutover", ("migration", "parity", "cutover", "legacy")),
)


class LegacyParityService:
    """Exact retained-case discovery, mapping, execution, and parity evidence."""

    def discover(
        self,
        repository_root: str | Path,
        *,
        test_roots: Sequence[str | Path],
    ) -> list[dict[str, Any]]:
        repository = Path(repository_root).resolve()
        cases: list[dict[str, Any]] = []
        seen: set[str] = set()
        for configured_root in test_roots:
            root = (repository / configured_root).resolve()
            try:
                root.relative_to(repository)
            except ValueError as exc:
                raise ValueError("legacy test root escapes repository") from exc
            if not root.exists():
                continue
            paths = [root] if root.is_file() else sorted(root.rglob("*"))
            for path in paths:
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(repository).as_posix()
                suffix = path.suffix.lower()
                if suffix == ".py" and (
                    path.name.startswith("test_") or path.name.endswith("_test.py")
                ):
                    try:
                        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                    except (OSError, SyntaxError):
                        identifiers = [path.stem]
                    else:
                        identifiers = [
                            node.name
                            for node in ast.walk(tree)
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and node.name.startswith("test")
                        ] or [path.stem]
                elif suffix in {".js", ".jsx", ".ts", ".tsx"} and (
                    ".test." in path.name or ".spec." in path.name
                ):
                    identifiers = [path.name]
                else:
                    continue
                for identifier in identifiers:
                    case_id = f"{relative}::{identifier}"
                    if case_id in seen:
                        continue
                    seen.add(case_id)
                    cases.append(
                        {
                            "legacy_case_id": case_id,
                            "relative_path": relative,
                            "case_key": identifier,
                            "file_sha256": _file_digest(path),
                            "bytes": path.stat().st_size,
                        }
                    )
        return sorted(cases, key=lambda case: case["legacy_case_id"])

    def propose_mapping(
        self,
        cases: Sequence[Mapping[str, Any]],
        *,
        acceptance_matrix_path: str | Path,
        overrides: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        matrix = json.loads(Path(acceptance_matrix_path).read_text(encoding="utf-8"))
        domains = matrix["domains"]
        explicit = dict(overrides or {})
        mappings: list[dict[str, Any]] = []
        for case in cases:
            case_id = str(case["legacy_case_id"])
            override = explicit.get(case_id)
            if override is not None:
                domain = str(override["domain"])
                native_ids = [str(value) for value in override["native_test_ids"]]
                disposition = str(override.get("disposition", "equivalent"))
                rationale = dict(override.get("rationale", {}))
            else:
                normalized = case_id.lower()
                domain = next(
                    (
                        candidate_domain
                        for candidate_domain, keywords in _DOMAIN_RULES
                        if any(keyword in normalized for keyword in keywords)
                    ),
                    "",
                )
                native_ids = (
                    [str(value) for value in domains[domain]["required"]]
                    if domain in domains
                    else []
                )
                disposition = "stronger_replacement" if native_ids else "unmapped"
                rationale = {
                    "mapping_source": "explicit-domain-rule" if native_ids else "none",
                    "legacy_file_sha256": case["file_sha256"],
                    "domain": domain or None,
                }
            mappings.append(
                dict(case)
                | {
                    "domain": domain or "unmapped",
                    "native_test_ids": native_ids,
                    "disposition": disposition,
                    "rationale": rationale,
                }
            )
        material = {
            "schema_version": 1,
            "acceptance_matrix_sha256": _file_digest(Path(acceptance_matrix_path)),
            "cases": mappings,
        }
        return material | {"manifest_root": _digest(material)}

    def verify_mapping(
        self,
        manifest: Mapping[str, Any],
        *,
        native_test_root: str | Path,
        acceptance_matrix_path: str | Path,
    ) -> dict[str, Any]:
        native_root = Path(native_test_root)
        native_ids = _test_ids(native_root)
        matrix = json.loads(Path(acceptance_matrix_path).read_text(encoding="utf-8"))
        known_domains = set(matrix["domains"])
        failures: list[str] = []
        legacy_ids: set[str] = set()
        for case in manifest.get("cases", []):
            case_id = str(case.get("legacy_case_id", ""))
            if not case_id or case_id in legacy_ids:
                failures.append(f"duplicate or missing legacy case id: {case_id}")
                continue
            legacy_ids.add(case_id)
            if case.get("disposition") not in {"equivalent", "stronger_replacement"}:
                failures.append(f"unaccepted parity disposition: {case_id}")
            if case.get("domain") not in known_domains:
                failures.append(f"unknown parity domain: {case_id}")
            mapped = [str(value) for value in case.get("native_test_ids", [])]
            if not mapped:
                failures.append(f"legacy case has no native executable mapping: {case_id}")
            for native_id in mapped:
                if native_id in native_ids:
                    continue
                module = native_id.split("::", 1)[0]
                if not any(identifier.startswith(f"{module}::") for identifier in native_ids):
                    failures.append(f"mapped native test is absent: {case_id} -> {native_id}")
            if not case.get("file_sha256") or not case.get("rationale"):
                failures.append(f"legacy case lacks provenance or rationale: {case_id}")
        if failures:
            raise RuntimeError("; ".join(failures))
        return {
            "status": "verified",
            "legacy_case_count": len(legacy_ids),
            "native_test_count": len(native_ids),
            "manifest_root": manifest["manifest_root"],
        }

    def execute(
        self,
        *,
        repository_root: str | Path,
        legacy_commands: Sequence[Sequence[str]],
        native_command: Sequence[str],
    ) -> dict[str, Any]:
        root = Path(repository_root).resolve()
        legacy_results: list[dict[str, Any]] = []
        for command in legacy_commands:
            result = subprocess.run(
                [str(value) for value in command],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            legacy_results.append(
                {
                    "command": list(command),
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        native = subprocess.run(
            [str(value) for value in native_command],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        evidence = {
            "legacy_results": legacy_results,
            "native_result": {
                "command": list(native_command),
                "exit_code": native.returncode,
                "stdout": native.stdout,
                "stderr": native.stderr,
            },
        }
        evidence["status"] = (
            "passed"
            if all(result["exit_code"] == 0 for result in legacy_results)
            and native.returncode == 0
            else "failed"
        )
        evidence["evidence_root"] = _digest(evidence)
        if evidence["status"] != "passed":
            raise RuntimeError("legacy/native parity execution failed")
        return evidence

    def write_manifest(self, path: str | Path, manifest: Mapping[str, Any]) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        encoded = _canonical(dict(manifest)) + "\n"
        if output.exists() and output.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("existing parity manifest differs")
        output.write_text(encoded, encoding="utf-8")
        return output
