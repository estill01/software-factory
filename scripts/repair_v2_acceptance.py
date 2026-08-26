from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runtime" / "src" / "software_factory"
TESTS = ROOT / "runtime" / "tests"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        return
    if count != 1:
        raise RuntimeError(f"expected at most one match in {path}: {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def align_schema_version() -> None:
    for path in [SOURCE / "schema.py", *sorted(TESTS.glob("test_*.py"))]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(SCHEMA_VERSION\s*=\s*)18\b", r"\g<1>19", text)
        text = re.sub(r"(\[\"schema_version\"\]\s*==\s*)18\b", r"\g<1>19", text)
        text = re.sub(r"(schema_version\s*==\s*)18\b", r"\g<1>19", text)
        path.write_text(text, encoding="utf-8")


def harden_acceptance_types() -> None:
    path = SOURCE / "acceptance.py"
    replace_once(
        path,
        """            try:\n                process = subprocess.run(\n""",
        """            exit_code: int | None\n            result: dict[str, Any]\n            try:\n                process = subprocess.run(\n""",
    )
    replace_once(
        path,
        """                result = {\n                    \"command\": command,\n                    \"exit_code\": process.returncode,\n""",
        """                exit_code = process.returncode\n                result = {\n                    \"command\": command,\n                    \"exit_code\": exit_code,\n""",
    )
    replace_once(
        path,
        """                process = None\n            duration_ms = max(0, int((time.monotonic() - start) * 1000))\n""",
        """                exit_code = None\n            duration_ms = max(0, int((time.monotonic() - start) * 1000))\n""",
    )
    replace_once(
        path,
        """                        process.returncode if process is not None else None,\n""",
        """                        exit_code,\n""",
    )


def main() -> None:
    align_schema_version()
    harden_acceptance_types()


if __name__ == "__main__":
    main()
