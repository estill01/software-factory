from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import AuthorityDenied, InvalidTransition
from ..util import atomic_write, canonical_json, digest_bytes, digest_json
from .contracts import EffectClass, TargetSnapshot

_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_STATE_FILE = "content-target.json"


@dataclass(frozen=True)
class ContentSource:
    """One registered factual source for the maintained neutral content profile."""

    key: str
    title: str
    statement: str

    def __post_init__(self) -> None:
        if not _KEY.fullmatch(self.key):
            raise ValueError("content source key must be a stable lowercase identifier")
        if not self.title.strip() or not self.statement.strip():
            raise ValueError("content source title and statement are required")


@dataclass(frozen=True)
class ContentSection:
    """A registered, source-bound section in the neutral document plan."""

    heading: str
    purpose: str
    source_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.heading.strip() or not self.purpose.strip():
            raise ValueError("content section heading and purpose are required")
        if not self.source_keys or len(set(self.source_keys)) != len(self.source_keys):
            raise ValueError("content section requires unique source keys")


@dataclass(frozen=True)
class _ContentTargetConfig:
    target_id: str
    root: Path
    title: str
    audience: str
    sources: tuple[ContentSource, ...]
    sections: tuple[ContentSection, ...]
    definition_root: str


class ContentTargetProfile:
    """Factory-owned deterministic content-production target profile.

    The profile owns only target inspection and physical content effects. Mission,
    work, QA, supervision, acceptance, and terminal outcome state remain in the
    ordinary Factory services.
    """

    key = "content"
    effect_classes = frozenset(
        {
            EffectClass.WORKSPACE,
            EffectClass.COMMAND,
            EffectClass.TEST,
            EffectClass.BUILD,
            EffectClass.RELEASE,
        }
    )

    def __init__(self) -> None:
        self._targets: dict[str, _ContentTargetConfig] = {}
        self._registry_authority: object | None = None

    def _bind_registry_authority(self, authority: object) -> None:
        if self._registry_authority is not None:
            raise InvalidTransition("content profile is already bound to a registry")
        self._registry_authority = authority

    @staticmethod
    def _definition_material(
        *,
        target_id: str,
        title: str,
        audience: str,
        sources: Sequence[ContentSource],
        sections: Sequence[ContentSection],
    ) -> dict[str, Any]:
        return {
            "schema_version": "software-factory-content-definition/v1",
            "target_id": target_id,
            "title": title,
            "audience": audience,
            "sources": [
                {"key": source.key, "title": source.title, "statement": source.statement}
                for source in sources
            ],
            "sections": [
                {
                    "heading": section.heading,
                    "purpose": section.purpose,
                    "source_keys": list(section.source_keys),
                }
                for section in sections
            ],
        }

    def register_target(
        self,
        target_id: str,
        *,
        root: str | Path,
        title: str,
        audience: str,
        sources: Sequence[ContentSource],
        sections: Sequence[ContentSection],
    ) -> None:
        if not _KEY.fullmatch(target_id):
            raise ValueError("content target ID must be a stable lowercase identifier")
        if target_id in self._targets:
            raise ValueError(f"content target is already registered: {target_id}")
        if not title.strip() or not audience.strip():
            raise ValueError("content target title and audience are required")
        source_values = tuple(sources)
        section_values = tuple(sections)
        if not source_values or not section_values:
            raise ValueError("content target requires sources and sections")
        source_keys = [source.key for source in source_values]
        if len(set(source_keys)) != len(source_keys):
            raise ValueError("content source keys must be unique")
        headings = [section.heading for section in section_values]
        if len(set(headings)) != len(headings):
            raise ValueError("content section headings must be unique")
        unknown = sorted(
            {
                key
                for section in section_values
                for key in section.source_keys
                if key not in source_keys
            }
        )
        if unknown:
            raise ValueError(f"content sections reference unknown sources: {unknown}")
        unused = sorted(
            set(source_keys) - {key for item in section_values for key in item.source_keys}
        )
        if unused:
            raise ValueError(f"content target contains unused sources: {unused}")

        requested_root = Path(root)
        if requested_root.is_symlink():
            raise InvalidTransition("content target root cannot be a symlink")
        target_root = requested_root.resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        if any(target_root.iterdir()):
            raise InvalidTransition("content target root must be empty at registration")
        material = self._definition_material(
            target_id=target_id,
            title=title.strip(),
            audience=audience.strip(),
            sources=source_values,
            sections=section_values,
        )
        definition_root = digest_json(material)
        config = _ContentTargetConfig(
            target_id=target_id,
            root=target_root,
            title=title.strip(),
            audience=audience.strip(),
            sources=source_values,
            sections=section_values,
            definition_root=definition_root,
        )
        self._targets[target_id] = config
        self._write_json(
            target_root / _STATE_FILE,
            {
                "schema_version": "software-factory-content-target/v1",
                "target_id": target_id,
                "definition_root": definition_root,
                "sequence": 0,
                "phase": "registered",
                "reviews": {},
                "outputs": {},
            },
        )

    def _config(self, target_id: str) -> _ContentTargetConfig:
        try:
            return self._targets[target_id]
        except KeyError as exc:
            raise AuthorityDenied(f"content target is not registered: {target_id}") from exc

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        atomic_write(path, (canonical_json(dict(value)) + "\n").encode("utf-8"))

    @staticmethod
    def _write_text(path: Path, value: str) -> None:
        atomic_write(path, value.encode("utf-8"))

    @staticmethod
    def _read_state(config: _ContentTargetConfig) -> dict[str, Any]:
        try:
            state = json.loads((config.root / _STATE_FILE).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise InvalidTransition("content target state is missing or invalid") from exc
        if (
            state.get("schema_version") != "software-factory-content-target/v1"
            or state.get("target_id") != config.target_id
            or state.get("definition_root") != config.definition_root
        ):
            raise InvalidTransition("content target state differs from its registration")
        return state

    @staticmethod
    def _tree(config: _ContentTargetConfig) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        for path in sorted(config.root.rglob("*")):
            if path.is_symlink():
                raise InvalidTransition("content target cannot contain symlinks")
            if path.is_dir():
                continue
            if not path.is_file():
                raise InvalidTransition("content target contains a non-regular member")
            payload = path.read_bytes()
            members.append(
                {
                    "path": path.relative_to(config.root).as_posix(),
                    "sha256": digest_bytes(payload),
                    "size": len(payload),
                }
            )
        return members

    def snapshot(self, target_id: str) -> TargetSnapshot:
        config = self._config(target_id)
        state = self._read_state(config)
        revision = digest_json(
            {
                "profile": self.key,
                "target_id": target_id,
                "definition_root": config.definition_root,
                "sequence": state.get("sequence"),
                "phase": state.get("phase"),
                "reviews": state.get("reviews", {}),
                "outputs": state.get("outputs", {}),
            }
        )
        attributes = {
            "definition_root": config.definition_root,
            "phase": state.get("phase"),
            "sequence": state.get("sequence"),
            "tree": self._tree(config),
        }
        return TargetSnapshot(
            profile_key=self.key,
            target_id=target_id,
            revision=revision,
            currentness_root=digest_json(
                {
                    "profile": self.key,
                    "target_id": target_id,
                    "revision": revision,
                    "attributes": attributes,
                }
            ),
            attributes=attributes,
        )

    def _advance(
        self,
        config: _ContentTargetConfig,
        state: dict[str, Any],
        *,
        phase: str,
        output_key: str | None = None,
        output: Mapping[str, Any] | None = None,
        review_key: str | None = None,
        review: Mapping[str, Any] | None = None,
    ) -> None:
        state["sequence"] = int(state["sequence"]) + 1
        state["phase"] = phase
        if output_key is not None:
            state.setdefault("outputs", {})[output_key] = dict(output or {})
        if review_key is not None:
            state.setdefault("reviews", {})[review_key] = dict(review or {})
        self._write_json(config.root / _STATE_FILE, state)

    @staticmethod
    def _require_phase(state: Mapping[str, Any], allowed: set[str], operation: str) -> None:
        if state.get("phase") not in allowed:
            raise InvalidTransition(
                f"content {operation} is not available from phase {state.get('phase')}"
            )

    @staticmethod
    def _source_records(config: _ContentTargetConfig) -> list[dict[str, str]]:
        return [
            {"key": item.key, "title": item.title, "statement": item.statement}
            for item in config.sources
        ]

    @staticmethod
    def _document_model(config: _ContentTargetConfig) -> dict[str, Any]:
        sources = {source.key: source for source in config.sources}
        return {
            "schema_version": "software-factory-neutral-document/v1",
            "title": config.title,
            "audience": config.audience,
            "sections": [
                {
                    "heading": section.heading,
                    "purpose": section.purpose,
                    "claims": [
                        {
                            "source_key": key,
                            "source_title": sources[key].title,
                            "statement": sources[key].statement,
                        }
                        for key in section.source_keys
                    ],
                }
                for section in config.sections
            ],
        }

    @staticmethod
    def _markdown(model: Mapping[str, Any]) -> str:
        lines = [f"# {model['title']}", "", f"Audience: {model['audience']}", ""]
        for section in model["sections"]:
            lines.extend((f"## {section['heading']}", "", str(section["purpose"]), ""))
            for claim in section["claims"]:
                lines.append(
                    f"- {claim['statement']} [source: {claim['source_key']}; "
                    f"{claim['source_title']}]"
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _html(model: Mapping[str, Any]) -> str:
        sections: list[str] = []
        for section in model["sections"]:
            claims = "".join(
                "<li>"
                + html.escape(str(claim["statement"]))
                + " <cite>["
                + html.escape(str(claim["source_key"]))
                + "] "
                + html.escape(str(claim["source_title"]))
                + "</cite></li>"
                for claim in section["claims"]
            )
            sections.append(
                "<section><h2>"
                + html.escape(str(section["heading"]))
                + "</h2><p>"
                + html.escape(str(section["purpose"]))
                + "</p><ul>"
                + claims
                + "</ul></section>"
            )
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>"
            + html.escape(str(model["title"]))
            + "</title></head><body><main><h1>"
            + html.escape(str(model["title"]))
            + "</h1><p><strong>Audience:</strong> "
            + html.escape(str(model["audience"]))
            + "</p>"
            + "".join(sections)
            + "</main></body></html>\n"
        )

    def _collect_sources(
        self, config: _ContentTargetConfig, state: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_phase(state, {"registered"}, "source collection")
        payload = {
            "schema_version": "software-factory-neutral-sources/v1",
            "sources": self._source_records(config),
        }
        path = config.root / "workspace" / "sources.json"
        self._write_json(path, payload)
        root = digest_json(payload)
        self._advance(
            config,
            state,
            phase="sources_collected",
            output_key="sources",
            output={"path": "workspace/sources.json", "root": root},
        )
        return {"source_count": len(config.sources), "source_root": root}

    def _plan(self, config: _ContentTargetConfig, state: dict[str, Any]) -> dict[str, Any]:
        self._require_phase(state, {"sources_collected"}, "planning")
        payload = {
            "schema_version": "software-factory-neutral-plan/v1",
            "title": config.title,
            "audience": config.audience,
            "sections": [
                {
                    "heading": section.heading,
                    "purpose": section.purpose,
                    "source_keys": list(section.source_keys),
                }
                for section in config.sections
            ],
        }
        path = config.root / "workspace" / "plan.json"
        self._write_json(path, payload)
        root = digest_json(payload)
        self._advance(
            config,
            state,
            phase="planned",
            output_key="plan",
            output={"path": "workspace/plan.json", "root": root},
        )
        return {"section_count": len(config.sections), "plan_root": root}

    def _draft(self, config: _ContentTargetConfig, state: dict[str, Any]) -> dict[str, Any]:
        self._require_phase(state, {"planned"}, "drafting")
        model = self._document_model(config)
        lines = [f"# {config.title}", ""]
        for section in model["sections"]:
            lines.extend((f"## {section['heading']}", str(section["purpose"])))
            lines.extend(str(claim["statement"]) for claim in section["claims"])
            lines.append("")
        draft = "\n".join(lines).rstrip() + "\n"
        path = config.root / "workspace" / "draft.md"
        self._write_text(path, draft)
        root = digest_bytes(draft.encode("utf-8"))
        self._advance(
            config,
            state,
            phase="drafted",
            output_key="draft",
            output={"path": "workspace/draft.md", "root": root},
        )
        return {"draft_root": root}

    def _revise(self, config: _ContentTargetConfig, state: dict[str, Any]) -> dict[str, Any]:
        self._require_phase(state, {"drafted"}, "revision")
        model = self._document_model(config)
        markdown = self._markdown(model)
        self._write_json(config.root / "workspace" / "document.json", model)
        self._write_text(config.root / "workspace" / "document.md", markdown)
        root = digest_json(
            {"model": model, "markdown_sha256": digest_bytes(markdown.encode("utf-8"))}
        )
        self._advance(
            config,
            state,
            phase="revised",
            output_key="document",
            output={
                "model_path": "workspace/document.json",
                "markdown_path": "workspace/document.md",
                "root": root,
            },
        )
        return {"document_root": root}

    def _load_document(self, config: _ContentTargetConfig) -> tuple[dict[str, Any], str]:
        try:
            model = json.loads(
                (config.root / "workspace" / "document.json").read_text(encoding="utf-8")
            )
            markdown = (config.root / "workspace" / "document.md").read_text(encoding="utf-8")
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise InvalidTransition("revised content document is missing or invalid") from exc
        return model, markdown

    def _review(
        self,
        config: _ContentTargetConfig,
        state: dict[str, Any],
        review_key: str,
    ) -> dict[str, Any]:
        self._require_phase(state, {"revised", "reviewing"}, f"{review_key} review")
        model, markdown = self._load_document(config)
        expected = self._document_model(config)
        details: dict[str, Any]
        if review_key == "factual":
            passed = model == expected
            details = {
                "all_claims_source_bound": passed,
                "source_count": len(config.sources),
            }
        elif review_key == "structural":
            expected_headings = [item.heading for item in config.sections]
            actual_headings = [str(item.get("heading")) for item in model.get("sections", [])]
            passed = actual_headings == expected_headings and markdown == self._markdown(expected)
            details = {
                "headings": actual_headings,
                "required_headings": expected_headings,
                "canonical_markdown": markdown == self._markdown(expected),
            }
        elif review_key == "style":
            lowered = markdown.lower()
            prohibited = [token for token in ("todo", "tbd", "placeholder") if token in lowered]
            passed = (
                not prohibited
                and markdown.startswith(f"# {config.title}\n")
                and f"Audience: {config.audience}" in markdown
                and all(section.purpose in markdown for section in config.sections)
            )
            details = {"prohibited_markers": prohibited, "audience_declared": True}
        else:  # pragma: no cover - guarded by the closed dispatch table
            raise AuthorityDenied(f"unknown content review: {review_key}")
        report = {"review": review_key, "passed": passed, "details": details}
        if not passed:
            raise InvalidTransition(f"content {review_key} review failed")
        report_root = digest_json(report)
        self._write_json(config.root / "reviews" / f"{review_key}.json", report)
        self._advance(
            config,
            state,
            phase="reviewing",
            review_key=review_key,
            review={"passed": True, "root": report_root},
        )
        return {"review": review_key, "passed": True, "report_root": report_root}

    def _render(self, config: _ContentTargetConfig, state: dict[str, Any]) -> dict[str, Any]:
        self._require_phase(state, {"reviewing"}, "rendering")
        reviews = state.get("reviews", {})
        missing = [
            key
            for key in ("factual", "structural", "style")
            if not reviews.get(key, {}).get("passed")
        ]
        if missing:
            raise InvalidTransition(f"content rendering requires passed reviews: {missing}")
        model, markdown = self._load_document(config)
        if model != self._document_model(config) or markdown != self._markdown(model):
            raise InvalidTransition("content changed after review")
        rendered = self._html(model)
        path = config.root / "rendered" / "document.html"
        self._write_text(path, rendered)
        artifact_root = digest_bytes(rendered.encode("utf-8"))
        self._advance(
            config,
            state,
            phase="rendered",
            output_key="rendered",
            output={"path": "rendered/document.html", "sha256": artifact_root},
        )
        return {"artifact_path": "rendered/document.html", "artifact_sha256": artifact_root}

    def _deliver(self, config: _ContentTargetConfig, state: dict[str, Any]) -> dict[str, Any]:
        self._require_phase(state, {"rendered"}, "delivery")
        source = config.root / "rendered" / "document.html"
        payload = source.read_bytes()
        artifact_root = digest_bytes(payload)
        if artifact_root != state["outputs"]["rendered"]["sha256"]:
            raise InvalidTransition("rendered artifact changed before delivery")
        delivered = config.root / "delivered" / "document.html"
        atomic_write(delivered, payload)
        receipt = {
            "schema_version": "software-factory-content-delivery/v1",
            "target_id": config.target_id,
            "artifact_path": "delivered/document.html",
            "artifact_sha256": artifact_root,
            "definition_root": config.definition_root,
        }
        self._write_json(config.root / "delivered" / "receipt.json", receipt)
        receipt_root = digest_json(receipt)
        self._advance(
            config,
            state,
            phase="delivered",
            output_key="delivery",
            output={"receipt_root": receipt_root, **receipt},
        )
        return {"artifact_sha256": artifact_root, "receipt_root": receipt_root}

    def _verify_delivery(
        self, config: _ContentTargetConfig, state: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_phase(state, {"delivered"}, "delivery verification")
        try:
            receipt = json.loads(
                (config.root / "delivered" / "receipt.json").read_text(encoding="utf-8")
            )
            payload = (config.root / "delivered" / "document.html").read_bytes()
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise InvalidTransition("delivered content or receipt is missing") from exc
        expected = state["outputs"]["delivery"]
        actual_root = digest_bytes(payload)
        if (
            receipt.get("artifact_sha256") != actual_root
            or receipt.get("definition_root") != config.definition_root
            or expected.get("artifact_sha256") != actual_root
            or expected.get("receipt_root") != digest_json(receipt)
        ):
            raise InvalidTransition("delivered content does not match its exact receipt")
        report = {
            "review": "delivery",
            "passed": True,
            "artifact_sha256": actual_root,
            "receipt_root": digest_json(receipt),
        }
        report_root = digest_json(report)
        self._write_json(config.root / "reviews" / "delivery.json", report)
        self._advance(
            config,
            state,
            phase="delivered_verified",
            review_key="delivery",
            review={"passed": True, "root": report_root},
        )
        return report | {"report_root": report_root}

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
            raise AuthorityDenied("content effects require target-profile registry authority")
        if set(arguments) != {"operation"} or not isinstance(arguments.get("operation"), str):
            raise AuthorityDenied("content effect contains unregistered arguments")
        config = self._config(target_id)
        if self.snapshot(target_id).revision != expected_revision:
            raise InvalidTransition("content target revision changed before authoritative effect")
        state = self._read_state(config)
        operation = str(arguments["operation"])
        dispatch = {
            (EffectClass.WORKSPACE, "collect_sources"): self._collect_sources,
            (EffectClass.COMMAND, "plan"): self._plan,
            (EffectClass.COMMAND, "draft"): self._draft,
            (EffectClass.COMMAND, "revise"): self._revise,
            (EffectClass.TEST, "review_factual"): lambda c, s: self._review(c, s, "factual"),
            (EffectClass.TEST, "review_structural"): lambda c, s: self._review(c, s, "structural"),
            (EffectClass.TEST, "review_style"): lambda c, s: self._review(c, s, "style"),
            (EffectClass.BUILD, "render"): self._render,
            (EffectClass.RELEASE, "deliver"): self._deliver,
            (EffectClass.TEST, "verify_delivery"): self._verify_delivery,
        }
        try:
            handler = dispatch[(effect_class, operation)]
        except KeyError as exc:
            raise AuthorityDenied(
                f"content profile does not register {effect_class.value}/{operation}"
            ) from exc
        return handler(config, state)
