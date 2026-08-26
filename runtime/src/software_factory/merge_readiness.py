from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReadinessFinding:
    check: str
    severity: str
    message: str
    evidence: Mapping[str, Any]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class MergeReadinessService:
    """Fail-closed merge-readiness audit for the exact repository tree.

    This is deliberately independent of PR prose and agent assertions. It binds
    acceptance coverage, migration ordering, source hygiene, and optional
    mechanical gates into one content-addressed report.
    """

    _MIGRATION = re.compile(r"^(?P<version>\d{4})_[A-Za-z0-9_.-]+\.sql$")

    def __init__(self, repository_root: str | Path):
        self.root = Path(repository_root).resolve()
        if not self.root.is_dir():
            raise ValueError("repository root does not exist")

    @staticmethod
    def _test_ids(test_root: Path) -> set[str]:
        identifiers: set[str] = set()
        for path in sorted(test_root.rglob("test_*.py")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(test_root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError):
                continue
            for node in tree.body:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and node.name.startswith("test"):
                    identifiers.add(f"{relative}::{node.name}")
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    for member in node.body:
                        if isinstance(
                            member, (ast.FunctionDef, ast.AsyncFunctionDef)
                        ) and member.name.startswith("test"):
                            identifiers.add(f"{relative}::{node.name}::{member.name}")
        return identifiers

    def _acceptance_findings(self) -> tuple[list[ReadinessFinding], dict[str, Any]]:
        matrix_path = self.root / "runtime" / "acceptance-matrix.json"
        test_root = self.root / "runtime" / "tests"
        findings: list[ReadinessFinding] = []
        if not matrix_path.is_file():
            findings.append(
                ReadinessFinding(
                    "acceptance-matrix",
                    "blocker",
                    "runtime/acceptance-matrix.json is missing",
                    {},
                )
            )
            return findings, {"required": 0, "observed": 0, "missing": []}
        try:
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(
                ReadinessFinding(
                    "acceptance-matrix",
                    "blocker",
                    "acceptance matrix is unreadable",
                    {"error": str(exc)},
                )
            )
            return findings, {"required": 0, "observed": 0, "missing": []}

        domains = matrix.get("domains")
        if not isinstance(domains, Mapping) or not domains:
            findings.append(
                ReadinessFinding(
                    "acceptance-matrix",
                    "blocker",
                    "acceptance matrix has no domains",
                    {},
                )
            )
            return findings, {"required": 0, "observed": 0, "missing": []}

        required: set[str] = set()
        malformed: list[str] = []
        for domain, record in domains.items():
            if not isinstance(record, Mapping):
                malformed.append(str(domain))
                continue
            values = record.get("required", ())
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                malformed.append(str(domain))
                continue
            required.update(values)
        if malformed:
            findings.append(
                ReadinessFinding(
                    "acceptance-matrix",
                    "blocker",
                    "acceptance matrix contains malformed domains",
                    {"domains": sorted(malformed)},
                )
            )

        observed = self._test_ids(test_root)
        missing = sorted(
            identifier
            for identifier in required
            if identifier not in observed
            and not any(
                candidate.endswith(f"::{identifier}") or candidate == identifier
                for candidate in observed
            )
        )
        if missing:
            findings.append(
                ReadinessFinding(
                    "acceptance-matrix",
                    "blocker",
                    "required behavioral cases are not implemented",
                    {"missing": missing},
                )
            )
        return findings, {
            "matrix_sha256": hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
            "required": len(required),
            "observed": len(observed),
            "missing": missing,
        }

    def _migration_findings(self) -> tuple[list[ReadinessFinding], dict[str, Any]]:
        migration_root = self.root / "runtime" / "src" / "software_factory" / "migrations"
        findings: list[ReadinessFinding] = []
        versions: dict[int, list[str]] = {}
        invalid: list[str] = []
        for path in sorted(migration_root.glob("*.sql")):
            match = self._MIGRATION.match(path.name)
            if match is None:
                invalid.append(path.name)
                continue
            versions.setdefault(int(match.group("version")), []).append(path.name)
        duplicates = {str(version): names for version, names in versions.items() if len(names) > 1}
        if invalid:
            findings.append(
                ReadinessFinding(
                    "migrations",
                    "blocker",
                    "migration filenames are not canonically versioned",
                    {"files": invalid},
                )
            )
        if duplicates:
            findings.append(
                ReadinessFinding(
                    "migrations",
                    "blocker",
                    "multiple migrations claim the same version",
                    {"duplicates": duplicates},
                )
            )
        ordered = sorted(versions)
        gaps: list[int] = []
        if ordered:
            expected = set(range(ordered[0], ordered[-1] + 1))
            gaps = sorted(expected - set(ordered))
        if gaps:
            findings.append(
                ReadinessFinding(
                    "migrations",
                    "blocker",
                    "migration sequence contains gaps",
                    {"versions": gaps},
                )
            )
        return findings, {
            "versions": ordered,
            "duplicates": duplicates,
            "invalid": invalid,
            "gaps": gaps,
        }

    def _hygiene_findings(self) -> tuple[list[ReadinessFinding], dict[str, Any]]:
        findings: list[ReadinessFinding] = []
        pending = sorted(
            path.relative_to(self.root).as_posix()
            for path in self.root.glob(".v2-*-pending")
            if path.is_file()
        )
        uploads = (
            sorted(
                path.relative_to(self.root).as_posix()
                for path in (self.root / ".sf-upload").rglob("*")
                if path.is_file()
            )
            if (self.root / ".sf-upload").exists()
            else []
        )
        if pending:
            findings.append(
                ReadinessFinding(
                    "source-hygiene",
                    "blocker",
                    "pending integration markers remain",
                    {"paths": pending},
                )
            )
        if uploads:
            findings.append(
                ReadinessFinding(
                    "source-hygiene",
                    "blocker",
                    "encoded or staged source transport remains",
                    {"paths": uploads},
                )
            )
        return findings, {"pending": pending, "uploads": uploads}

    def _run_commands(
        self, commands: Sequence[Sequence[str]]
    ) -> tuple[list[ReadinessFinding], list[dict[str, Any]]]:
        findings: list[ReadinessFinding] = []
        results: list[dict[str, Any]] = []
        for command in commands:
            normalized = [str(part) for part in command]
            process = subprocess.run(
                normalized,
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
            record = {
                "command": normalized,
                "exit_code": process.returncode,
                "stdout_sha256": hashlib.sha256(process.stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
            }
            results.append(record)
            if process.returncode != 0:
                findings.append(
                    ReadinessFinding(
                        "mechanical-gate",
                        "blocker",
                        "merge gate command failed",
                        record,
                    )
                )
        return findings, results

    def audit(
        self,
        *,
        commands: Sequence[Sequence[str]] = (),
        expected_head: str | None = None,
    ) -> dict[str, Any]:
        findings: list[ReadinessFinding] = []
        acceptance_findings, acceptance = self._acceptance_findings()
        migration_findings, migrations = self._migration_findings()
        hygiene_findings, hygiene = self._hygiene_findings()
        command_findings, command_results = self._run_commands(commands)
        findings.extend(acceptance_findings)
        findings.extend(migration_findings)
        findings.extend(hygiene_findings)
        findings.extend(command_findings)

        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if expected_head is not None and head != expected_head:
            findings.append(
                ReadinessFinding(
                    "currentness",
                    "blocker",
                    "repository head differs from the audited revision",
                    {"expected": expected_head, "observed": head},
                )
            )

        report: dict[str, Any] = {
            "schema_version": 1,
            "status": "ready" if not findings else "blocked",
            "head": head,
            "acceptance": acceptance,
            "migrations": migrations,
            "hygiene": hygiene,
            "commands": command_results,
            "findings": [asdict(finding) for finding in findings],
        }
        report["evidence_root"] = _digest(report)
        return report

    @staticmethod
    def write_report(path: str | Path, report: Mapping[str, Any]) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            json.dumps(
                dict(report),
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        output.write_text(payload, encoding="utf-8")
        return output
