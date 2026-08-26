from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
from typing import Any

from ...errors import StoreError


@dataclass(frozen=True, slots=True)
class LibRSIPin:
    distribution: str
    import_name: str
    version: str
    producer_acceptance_revision: str
    source_commit: str
    repository_tree: str
    package_tree: str
    package_content_root: str
    package_content_root_algorithm: str
    wheel_sha256: str
    sdist_sha256: str
    semantic_record_schema_version: int
    outcome_projection_schema_version: int
    event_projection_schema_version: int
    adapter_contract: str
    source_url: str
    artifact_boundary: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> LibRSIPin:
        return cls(**value)

    @property
    def dependency_spec(self) -> str:
        return f"{self.distribution} @ git+{self.source_url}@{self.source_commit}"


def _load_pin() -> LibRSIPin:
    payload = files("software_factory.semantic_pins").joinpath("librsi.json").read_text()
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError("libRSI pin must be a JSON object")
    return LibRSIPin.from_dict(value)


LIBRSI_PIN = _load_pin()


def verify_installed_librsi() -> dict[str, Any]:
    """Fail closed unless the loaded package matches the immutable accepted pin.

    This runtime admits the pinned VCS installation only when PEP 610 proves the
    exact source URL and commit. A wheel without that metadata is not silently
    admitted; a future artifact-hash installer requires a separate explicit owner.
    """

    import librsi

    if librsi.__version__ != LIBRSI_PIN.version:
        raise StoreError(
            f"libRSI version mismatch: {librsi.__version__!r} != {LIBRSI_PIN.version!r}"
        )
    distribution = metadata.distribution(LIBRSI_PIN.distribution)
    installed_version = distribution.version
    if installed_version != LIBRSI_PIN.version:
        raise StoreError("installed libRSI distribution version does not match its import")

    direct_url_text = distribution.read_text("direct_url.json")
    direct_url: dict[str, Any] | None = None
    if not direct_url_text:
        raise StoreError("installed libRSI lacks exact PEP 610 VCS provenance")
    loaded = json.loads(direct_url_text)
    if not isinstance(loaded, dict):
        raise StoreError("libRSI direct_url.json is invalid")
    direct_url = loaded
    vcs = loaded.get("vcs_info")
    if loaded.get("url") != LIBRSI_PIN.source_url:
        raise StoreError("VCS-installed libRSI source URL does not match the accepted producer")
    if (
        not isinstance(vcs, dict)
        or vcs.get("vcs") != "git"
        or vcs.get("commit_id") != LIBRSI_PIN.source_commit
        or vcs.get("requested_revision") != LIBRSI_PIN.source_commit
    ):
        raise StoreError("VCS-installed libRSI is not bound to the accepted source commit")

    return {
        "adapter_contract": LIBRSI_PIN.adapter_contract,
        "distribution": LIBRSI_PIN.distribution,
        "version": installed_version,
        "source_commit": LIBRSI_PIN.source_commit,
        "package_content_root": LIBRSI_PIN.package_content_root,
        "direct_url": direct_url,
    }
