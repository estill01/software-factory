#!/usr/bin/env python3
"""Read-only structural verifier for Markdown implementation trackers."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path


BLOCK_HEADING = re.compile(
    r"^(?P<marks>#{2,4})\s+Block\s+(?P<number>\d+)\s*(?:[—:-]\s*(?P<title>.*))?$"
)
SECTION_HEADING = re.compile(r"^#{2,6}\s+(?P<title>.+?)\s*$")
STATUS_LINE = re.compile(r"^\s*(?:\*\*)?Status(?:\*\*)?\s*:\s*`?(?P<status>[a-z][a-z0-9-]*)`?\s*$", re.I)
LABELED_BULLET = re.compile(
    r"^\s*-\s*(?:\*\*)?(?P<label>[^:*]+?)(?:\*\*)?\s*:\s*(?P<value>.*?)\s*$"
)

CORE_SECTIONS = (
    ("objective",),
    ("required work",),
    ("acceptance",),
    ("stop",),
)
FULL_SECTIONS = CORE_SECTIONS + (
    ("inputs and dependencies", "inputs/dependencies"),
    ("scope and non-goals", "scope/non-goals", "boundary and non-goals"),
    ("deliverables and recorded state", "deliverables and persistent capability state", "deliverables"),
    ("resource and economy contract", "resource/economy contract", "resource contract"),
    ("qa and independent review", "qa/independent review", "qa"),
    ("negative tests",),
    ("completion evidence",),
)

CAPABILITY_FRAME_HEADING = "target-product capability frame"
CAPABILITY_FRAME_FIELDS = (
    "applicability",
    "applicability rationale",
    "direct product sources",
    "product thesis and intended effect",
    "protected capabilities",
    "architecture strategy",
    "requested capability",
    "proportionality",
    "tradeoffs",
    "uncertainty",
)
CAPABILITY_APPLICABILITY = {"consequential", "routine", "not-applicable"}
CAPABILITY_DELTA_HEADING = "target-product capability delta"
CAPABILITY_DELTA_FIELDS = (
    "intended capability gain",
    "potential capability loss or regression",
    "protected-capability effect",
    "architecture and operating-model effect",
    "tradeoff and source evidence",
)
CAPABILITY_POSTURES = {"consequential", "routine", "not-applicable"}


@dataclass(frozen=True)
class Block:
    number: int
    title: str
    line: int
    level: int
    body: tuple[str, ...]


def normalize_heading(value: str) -> str:
    value = value.strip().lower().rstrip(":")
    return re.sub(r"\s+", " ", value)


def iter_unfenced_lines(lines: Sequence[str]) -> Iterator[tuple[int, str]]:
    """Yield physical line indexes outside matching backtick or tilde fences."""
    fence_character: str | None = None
    fence_length = 0
    for index, line in enumerate(lines):
        if fence_character is not None:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
                line,
            )
            if closing:
                fence_character = None
                fence_length = 0
            continue

        opening = re.match(r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$", line)
        if opening:
            marker = opening.group("marker")
            if marker[0] == "`" and "`" in opening.group("info"):
                yield index, line
                continue
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        if line.startswith("    ") or line.startswith("\t"):
            continue
        yield index, line


def parse_blocks(lines: list[str]) -> list[Block]:
    starts: list[tuple[int, re.Match[str]]] = []
    for index, line in iter_unfenced_lines(lines):
        match = BLOCK_HEADING.match(line.rstrip())
        if match:
            starts.append((index, match))

    blocks: list[Block] = []
    for position, (start, match) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        block_level = len(match.group("marks"))
        for relative_index, line in iter_unfenced_lines(lines[start + 1 : end]):
            heading = SECTION_HEADING.match(line.rstrip())
            current_level = len(line) - len(line.lstrip("#"))
            if heading and current_level <= block_level:
                end = start + 1 + relative_index
                break
        blocks.append(
            Block(
                number=int(match.group("number")),
                title=(match.group("title") or "").strip(),
                line=start + 1,
                level=block_level,
                body=tuple(lines[start + 1 : end]),
            )
        )
    return blocks


def parse_status(block: Block) -> tuple[str | None, int | None]:
    for offset, line in iter_unfenced_lines(block.body):
        match = STATUS_LINE.match(line)
        if match:
            return match.group("status").lower(), block.line + offset + 1
    return None, None


def parse_sections(block: Block) -> set[str]:
    sections: set[str] = set()
    for _, line in iter_unfenced_lines(block.body):
        match = SECTION_HEADING.match(line.rstrip())
        level = len(line) - len(line.lstrip("#"))
        if match and level > block.level:
            sections.add(normalize_heading(match.group("title")))
    return sections


def extract_section(
    lines: Sequence[str],
    title: str,
    *,
    expected_level: int | None = None,
) -> list[str] | None:
    """Return one unfenced Markdown section body, bounded by heading level."""
    wanted = normalize_heading(title)
    start: int | None = None
    level: int | None = None
    for index, line in iter_unfenced_lines(lines):
        match = SECTION_HEADING.match(line.rstrip())
        if not match:
            continue
        current_level = len(line) - len(line.lstrip("#"))
        if start is None:
            if (
                normalize_heading(match.group("title")) == wanted
                and (expected_level is None or current_level == expected_level)
            ):
                start = index + 1
                level = current_level
            continue
        if current_level <= level:
            return list(lines[start:index])
    return list(lines[start:]) if start is not None else None


def count_section_headings(
    lines: Sequence[str],
    title: str,
    *,
    expected_level: int | None = None,
) -> int:
    wanted = normalize_heading(title)
    count = 0
    for _, line in iter_unfenced_lines(lines):
        match = SECTION_HEADING.match(line.rstrip())
        current_level = len(line) - len(line.lstrip("#"))
        if (
            match
            and normalize_heading(match.group("title")) == wanted
            and (expected_level is None or current_level == expected_level)
        ):
            count += 1
    return count


def parse_labeled_bullets(lines: list[str]) -> tuple[dict[str, str], set[str]]:
    fields: dict[str, str] = {}
    duplicates: set[str] = set()
    for _, line in iter_unfenced_lines(lines):
        match = LABELED_BULLET.match(line)
        if not match:
            continue
        label = normalize_heading(match.group("label"))
        if label in fields:
            duplicates.add(label)
        else:
            fields[label] = match.group("value").strip()
    return fields, duplicates


def normalized_value(value: str) -> str:
    return value.strip().strip("`\".' ").lower()


def is_meaningful(value: str) -> bool:
    normalized = normalized_value(value)
    placeholder_prefix = re.match(r"^(?:tbd|todo|pending|evidence pending)(?:\b|\s|:)", normalized)
    return bool(normalized) and normalized not in {"n/a", "none", "not applicable"} and not (
        placeholder_prefix or "{{" in value or "}}" in value
    )


def is_concrete_evidence(value: str) -> bool:
    normalized = normalized_value(value)
    deferred = re.search(
        r"\b(?:will be|to be)\s+(?:added|collected|determined|provided|supplied)\b"
        r"|\bevidence\s+(?:after|following)\s+implementation\b"
        r"|^(?:deferred|forthcoming|not yet|to follow)\b"
        r"|\b(?:evidence|sources?)\b.{0,80}\b(?:deferred|forthcoming|pending|not yet|will follow|to follow)\b"
        r"|\b(?:deferred|forthcoming|pending|not yet|will follow|to follow)\b.{0,80}\b(?:evidence|sources?)\b",
        normalized,
    )
    return is_meaningful(value) and deferred is None


def is_not_applicable(value: str) -> bool:
    normalized = normalized_value(value)
    return normalized == "n/a" or normalized.startswith("not applicable") or normalized.startswith("none")


def verify_capability_frame(lines: list[str], first_block_line: int) -> tuple[list[str], str | None]:
    errors: list[str] = []
    preamble = lines[: first_block_line - 1]
    count = count_section_headings(preamble, CAPABILITY_FRAME_HEADING)
    if count > 1:
        errors.append(f"tracker has {count} sections named '{CAPABILITY_FRAME_HEADING}'; expected one")
    section = extract_section(preamble, CAPABILITY_FRAME_HEADING)
    if section is None:
        return [f"before line {first_block_line}: missing section '{CAPABILITY_FRAME_HEADING}'"], None
    fields, duplicates = parse_labeled_bullets(section)
    for label in sorted(duplicates):
        errors.append(f"target-product capability frame has duplicate field '{label}'")
    for label in CAPABILITY_FRAME_FIELDS:
        value = fields.get(label)
        if value is None:
            errors.append(f"target-product capability frame is missing field '{label}'")
        elif not is_meaningful(value):
            errors.append(f"target-product capability frame field '{label}' is empty or a placeholder")

    applicability = normalized_value(fields.get("applicability", ""))
    if applicability not in CAPABILITY_APPLICABILITY:
        errors.append(
            "target-product capability frame field 'applicability' must be one of: "
            + ", ".join(sorted(CAPABILITY_APPLICABILITY))
        )
    if applicability == "consequential" and is_not_applicable(fields.get("direct product sources", "")):
        errors.append("consequential target-product capability frame requires direct product sources")
    if applicability == "consequential" and not is_concrete_evidence(fields.get("direct product sources", "")):
        errors.append("consequential target-product capability frame requires current direct product sources")
    return errors, applicability if applicability in CAPABILITY_APPLICABILITY else None


def verify_capability_delta(block: Block) -> tuple[list[str], str | None]:
    errors: list[str] = []
    expected_level = block.level + 1
    count = count_section_headings(
        block.body,
        CAPABILITY_DELTA_HEADING,
        expected_level=expected_level,
    )
    if count > 1:
        errors.append(
            f"line {block.line}: Block {block.number} has {count} sections named "
            f"'{CAPABILITY_DELTA_HEADING}'; expected one"
        )
    section = extract_section(
        block.body,
        CAPABILITY_DELTA_HEADING,
        expected_level=expected_level,
    )
    if section is None:
        return [
            f"line {block.line}: Block {block.number} is missing section "
            f"'{CAPABILITY_DELTA_HEADING}'"
        ], None
    fields, duplicates = parse_labeled_bullets(section)
    for label in sorted(duplicates):
        errors.append(
            f"line {block.line}: Block {block.number} capability delta has duplicate field '{label}'"
        )
    posture = normalized_value(fields.get("posture", ""))
    if posture not in CAPABILITY_POSTURES:
        errors.append(
            f"line {block.line}: Block {block.number} capability delta field 'posture' "
            "must be one of: consequential, not-applicable, routine"
        )
        return errors, None
    if posture == "consequential":
        for label in CAPABILITY_DELTA_FIELDS:
            value = fields.get(label)
            if value is None:
                errors.append(
                    f"line {block.line}: Block {block.number} consequential capability delta "
                    f"is missing field '{label}'"
                )
            elif not is_meaningful(value) or is_not_applicable(value):
                errors.append(
                    f"line {block.line}: Block {block.number} consequential capability delta "
                    f"field '{label}' needs a concrete value"
                )
            elif label == "tradeoff and source evidence" and not is_concrete_evidence(value):
                errors.append(
                    f"line {block.line}: Block {block.number} consequential capability delta "
                    "field 'tradeoff and source evidence' cannot defer its evidence"
                )
    else:
        justification = fields.get("routine or not-applicable justification")
        if justification is None or not is_meaningful(justification):
            errors.append(
                f"line {block.line}: Block {block.number} {posture} capability delta requires "
                "field 'routine or not-applicable justification'"
            )
    return errors, posture


def duplicate_numbers(numbers: Iterable[int]) -> list[int]:
    return [number for number, count in Counter(numbers).items() if count > 1]


def parse_status_table(lines: list[str]) -> tuple[dict[int, tuple[str, str, int]], list[str]]:
    rows: dict[int, tuple[str, str, int]] = {}
    errors: list[str] = []
    visible = list(iter_unfenced_lines(lines))
    header_position: int | None = None
    for position, (_, line) in enumerate(visible):
        if re.match(r"^\|\s*Block\s*\|", line, re.I):
            header_position = position
            break
    if header_position is None:
        return rows, errors

    for position in range(header_position + 2, len(visible)):
        index, line = visible[position]
        if index != visible[position - 1][0] + 1:
            break
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not re.fullmatch(r"\d+", cells[0]):
            continue
        if len(cells) < 4:
            errors.append(f"line {index + 1}: malformed status-table row")
            continue
        number = int(cells[0])
        if number in rows:
            errors.append(f"line {index + 1}: duplicate status-table row for Block {number}")
            continue
        status = cells[-1].strip("`").lower()
        dependencies = cells[-2]
        rows[number] = (status, dependencies, index + 1)
    return rows, errors


def sequence_metadata(lines: list[str]) -> tuple[int | None, int | None]:
    pattern = re.compile(r"^\s*-?\s*Tracker sequence\s*:\s*Blocks\s+0[–-](\d+)\s*$", re.I)
    for index, line in iter_unfenced_lines(lines):
        match = pattern.match(line)
        if match:
            return int(match.group(1)), index + 1
    return None, None


def verify(path: Path, profile: str) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks = parse_blocks(lines)
    errors: list[str] = []
    warnings: list[str] = []

    if not blocks:
        errors.append("no Block headings found")
        return {"path": str(path), "profile": profile, "blocks": [], "errors": errors, "warnings": warnings}

    numbers = [block.number for block in blocks]
    duplicates = duplicate_numbers(numbers)
    if duplicates:
        errors.append(f"duplicate Block headings: {', '.join(map(str, duplicates))}")
    expected = list(range(len(numbers)))
    expected_set = set(expected)
    if numbers != expected:
        errors.append(f"Block headings are not continuous and ordered: found {numbers}, expected {expected}")

    required_sections = FULL_SECTIONS if profile == "full" else CORE_SECTIONS
    tracker_capability_posture: str | None = None
    if profile == "full":
        frame_count = count_section_headings(lines, CAPABILITY_FRAME_HEADING)
        if frame_count != 1:
            errors.append(
                f"tracker has {frame_count} total sections named '{CAPABILITY_FRAME_HEADING}'; expected one"
            )
        delta_count = count_section_headings(lines, CAPABILITY_DELTA_HEADING)
        if delta_count != len(blocks):
            errors.append(
                f"tracker has {delta_count} total sections named '{CAPABILITY_DELTA_HEADING}'; "
                f"expected {len(blocks)}"
            )
        frame_errors, tracker_capability_posture = verify_capability_frame(lines, blocks[0].line)
        errors.extend(frame_errors)
    block_statuses: dict[int, str] = {}
    block_capability_postures: list[str] = []
    for block in blocks:
        status, _ = parse_status(block)
        if status is None:
            errors.append(f"line {block.line}: Block {block.number} has no Status line")
        else:
            block_statuses[block.number] = status
        sections = parse_sections(block)
        for aliases in required_sections:
            if not any(alias in sections for alias in aliases):
                errors.append(
                    f"line {block.line}: Block {block.number} is missing section "
                    f"'{aliases[0]}'"
                )
        if profile == "full":
            delta_errors, block_capability_posture = verify_capability_delta(block)
            errors.extend(delta_errors)
            if block_capability_posture is not None:
                block_capability_postures.append(block_capability_posture)
            if (
                tracker_capability_posture in {"routine", "not-applicable"}
                and block_capability_posture == "consequential"
            ):
                errors.append(
                    f"line {block.line}: Block {block.number} capability posture 'consequential' "
                    f"contradicts tracker applicability '{tracker_capability_posture}'"
                )

    if (
        profile == "full"
        and tracker_capability_posture == "consequential"
        and "consequential" not in block_capability_postures
    ):
        errors.append("consequential tracker requires at least one consequential Block capability delta")

    table, table_errors = parse_status_table(lines)
    errors.extend(table_errors)
    if not table:
        message = "no status/order table with a '| Block |' header found"
        (errors if profile == "full" else warnings).append(message)
    else:
        table_numbers = list(table)
        if table_numbers != expected:
            errors.append(f"status-table Blocks do not match headings: found {table_numbers}, expected {expected}")
        for number, (table_status, dependencies, line) in table.items():
            if number in block_statuses and table_status != block_statuses[number]:
                errors.append(
                    f"line {line}: Block {number} table status '{table_status}' "
                    f"does not match block status '{block_statuses[number]}'"
                )
            dependency_numbers = [int(value) for value in re.findall(r"\d+", dependencies)]
            for dependency in dependency_numbers:
                if dependency not in expected_set:
                    errors.append(f"line {line}: Block {number} depends on unknown Block {dependency}")
                elif dependency >= number:
                    errors.append(
                        f"line {line}: Block {number} has non-preceding dependency Block {dependency}"
                    )

    declared_terminal, metadata_line = sequence_metadata(lines)
    if declared_terminal is not None and declared_terminal != max(numbers):
        errors.append(
            f"line {metadata_line}: tracker sequence ends at Block {declared_terminal}, "
            f"but headings end at Block {max(numbers)}"
        )
    elif declared_terminal is None:
        warnings.append("no explicit 'Tracker sequence: Blocks 0–N' metadata found")

    return {
        "path": str(path),
        "profile": profile,
        "blocks": numbers,
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tracker", type=Path, help="Markdown tracker to verify")
    parser.add_argument(
        "--profile",
        choices=("core", "full"),
        default="full",
        help=(
            "full requires the current capability frame, deltas, and implementation-ready block sections; "
            "core is the compatibility profile for inherited trackers"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable diagnostics")
    parser.add_argument(
        "--revision-packet",
        type=Path,
        help="also verify one exact active-program structural revision packet",
    )
    parser.add_argument(
        "--previous-tracker",
        type=Path,
        help="exact predecessor tracker required with --revision-packet",
    )
    args = parser.parse_args(argv)

    if bool(args.revision_packet) != bool(args.previous_tracker):
        parser.error("--revision-packet and --previous-tracker must be supplied together")

    if not args.tracker.is_file():
        print(f"error: tracker does not exist: {args.tracker}", file=sys.stderr)
        return 2

    try:
        result = verify(args.tracker, args.profile)
    except (OSError, UnicodeError) as exc:
        print(f"error: cannot read tracker: {exc}", file=sys.stderr)
        return 2

    if args.revision_packet is not None:
        module_path = Path(__file__).with_name("program_revision.py")
        spec = importlib.util.spec_from_file_location(
            "verify_tracker_program_revision", module_path
        )
        if spec is None or spec.loader is None:
            result["errors"].append("program revision verifier is unavailable")
        else:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                packet = module.validate_revision_packet(
                    module.load_json(args.revision_packet),
                    previous_tracker=args.previous_tracker,
                    proposed_tracker=args.tracker,
                )
                result["program_revision"] = {
                    "revision_id": packet["revision_id"],
                    "packet_root": packet["packet_root"],
                    "resume_block": packet["resume_block"],
                }
            except module.ProgramRevisionError as exc:
                result["errors"].append(f"program revision: {exc}")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"tracker: {result['path']}\n"
            f"profile: {result['profile']}\n"
            f"blocks: {len(result['blocks'])}"
        )
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")
        print("result: PASS" if not result["errors"] else "result: FAIL")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
