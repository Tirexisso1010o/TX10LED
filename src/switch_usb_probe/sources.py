"""Access to the repository's machine-readable research data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ResearchDataError(Exception):
    """The research data is missing, unreadable, or structurally invalid."""


def repo_root() -> Path:
    """Return the repository root, allowing an explicit override for tests."""

    override = os.environ.get("SWITCH_USB_PROBE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError as exc:
        raise ResearchDataError(f"research file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ResearchDataError(
            f"research file is not valid JSON: {path}: {exc.msg} at line {exc.lineno}"
        ) from exc
    except OSError as exc:
        raise ResearchDataError(f"could not read research file {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ResearchDataError(f"research file must contain a JSON object: {path}")
    return document


@dataclass(frozen=True)
class ResearchBundle:
    sources: dict[str, Any]
    evidence: dict[str, Any]
    matrix: dict[str, Any]
    entry_points: dict[str, Any]
    root: Path

    @property
    def source_list(self) -> list[dict[str, Any]]:
        value = self.sources.get("sources", [])
        return value if isinstance(value, list) else []

    @property
    def evidence_list(self) -> list[dict[str, Any]]:
        value = self.evidence.get("entries", [])
        return value if isinstance(value, list) else []

    @property
    def entry_point_list(self) -> list[dict[str, Any]]:
        value = self.entry_points.get("surfaces", [])
        return value if isinstance(value, list) else []

    @property
    def source_by_id(self) -> dict[str, dict[str, Any]]:
        return {
            item["id"]: item
            for item in self.source_list
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    @property
    def evidence_by_id(self) -> dict[str, dict[str, Any]]:
        return {
            item["id"]: item
            for item in self.evidence_list
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    @property
    def reported_firmware(self) -> str | None:
        target = self.matrix.get("target", {})
        if isinstance(target, dict):
            value = target.get("firmware_reported")
            if isinstance(value, str):
                return value
        return None


def load_bundle(root: Path | str | None = None) -> ResearchBundle:
    base = Path(root).expanduser().resolve() if root is not None else repo_root()
    research = base / "research"
    sources = load_json(research / "sources.json")
    evidence = load_json(research / "evidence-ledger.json")
    matrix = load_json(research / "compatibility-matrix.json")
    entry_points = load_json(research / "entry-points.json")
    return ResearchBundle(
        sources=sources,
        evidence=evidence,
        matrix=matrix,
        entry_points=entry_points,
        root=base,
    )
