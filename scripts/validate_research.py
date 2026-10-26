#!/usr/bin/env python3
"""Validate the repository's research data and cross-references.

The validator is intentionally standard-library only. It checks structure,
unique IDs, evidence/source references, status values, summary counts, and a
small set of high-confidence secret patterns. It does not prove that a prose
claim is true.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"

STATUSES = {
    "VERIFIED",
    "PARTIALLY VERIFIED",
    "UNVERIFIED",
    "DISPROVEN",
    "UNKNOWN",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
]

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache"}


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks = 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.error(message)

    def load(self, path: Path) -> dict[str, Any]:
        self.checks += 1
        try:
            with path.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except FileNotFoundError:
            self.error(f"missing file: {path.relative_to(ROOT)}")
            return {}
        except json.JSONDecodeError as exc:
            self.error(
                f"invalid JSON in {path.relative_to(ROOT)}: {exc.msg} "
                f"at line {exc.lineno}"
            )
            return {}
        if not isinstance(document, dict):
            self.error(f"{path.relative_to(ROOT)} must contain a JSON object")
            return {}
        return document

    def unique_ids(self, items: Any, label: str) -> dict[str, dict[str, Any]]:
        self.checks += 1
        if not isinstance(items, list):
            self.error(f"{label} must be a list")
            return {}
        by_id: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                self.error(f"{label}[{index}] must be an object")
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                self.error(f"{label}[{index}] is missing a string id")
                continue
            if item_id in by_id:
                self.error(f"{label} has a duplicate id: {item_id}")
                continue
            by_id[item_id] = item
        return by_id

    def refs(
        self,
        item: dict[str, Any],
        field: str,
        known: dict[str, Any],
        label: str,
    ) -> None:
        values = item.get(field, [])
        if not isinstance(values, list):
            self.error(f"{label}.{field} must be a list")
            return
        for value in values:
            self.checks += 1
            if value not in known:
                self.error(f"{label}.{field} references unknown id: {value}")

    def status(self, item: dict[str, Any], label: str, field: str = "status") -> None:
        value = item.get(field)
        self.checks += 1
        if value not in STATUSES:
            self.error(f"{label} has invalid {field}: {value!r}")

    def scan_secrets(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".pdf",
                ".zip",
                ".pyc",
            }:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                self.error(f"could not read {path.relative_to(ROOT)}: {exc}")
                continue
            for pattern in SECRET_PATTERNS:
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    self.error(
                        f"possible secret in {path.relative_to(ROOT)}:{line}"
                    )

    def run(self) -> int:
        sources_doc = self.load(RESEARCH / "sources.json")
        evidence_doc = self.load(RESEARCH / "evidence-ledger.json")
        matrix_doc = self.load(RESEARCH / "compatibility-matrix.json")
        entry_doc = self.load(RESEARCH / "entry-points.json")
        hypotheses_doc = self.load(RESEARCH / "hypotheses.json")

        sources = self.unique_ids(sources_doc.get("sources"), "sources")
        evidence = self.unique_ids(evidence_doc.get("entries"), "evidence")
        matrix_rows = self.unique_ids(matrix_doc.get("rows"), "matrix.rows")
        usb_modes = self.unique_ids(matrix_doc.get("usb_modes"), "matrix.usb_modes")
        surfaces = self.unique_ids(entry_doc.get("surfaces"), "entry-points.surfaces")
        hypotheses = self.unique_ids(
            hypotheses_doc.get("hypotheses"),
            "hypotheses",
        )
        leads = self.unique_ids(entry_doc.get("leads"), "entry-points.leads")
        flaws = self.unique_ids(
            entry_doc.get("fixed_public_flaws"),
            "entry-points.fixed_public_flaws",
        )

        for source_id, source in sources.items():
            for field in ("title", "publisher", "kind", "url", "retrieved_at"):
                self.check(
                    isinstance(source.get(field), str) and bool(source.get(field)),
                    f"sources[{source_id}] is missing {field}",
                )
            self.check(
                str(source.get("url", "")).startswith(("http://", "https://")),
                f"sources[{source_id}].url is not an HTTP(S) URL",
            )

        for evidence_id, item in evidence.items():
            self.status(item, f"evidence[{evidence_id}]")
            self.check(
                isinstance(item.get("claim"), str) and bool(item.get("claim")),
                f"evidence[{evidence_id}] is missing claim",
            )
            self.refs(item, "sources", sources, f"evidence[{evidence_id}]")

        conclusion = matrix_doc.get("conclusion")
        self.check(isinstance(conclusion, dict), "matrix.conclusion must be an object")
        if isinstance(conclusion, dict):
            self.status(conclusion, "matrix.conclusion", field="claim_status")
            self.refs(conclusion, "evidence", evidence, "matrix.conclusion")

        for row_id, row in matrix_rows.items():
            self.status(row, f"matrix.rows[{row_id}]")
            self.refs(row, "evidence", evidence, f"matrix.rows[{row_id}]")

        for mode_id, mode in usb_modes.items():
            self.status(mode, f"matrix.usb_modes[{mode_id}]")
            self.refs(mode, "evidence", evidence, f"matrix.usb_modes[{mode_id}]")

        entry_analysis = matrix_doc.get("entry_point_analysis")
        self.check(
            isinstance(entry_analysis, dict),
            "matrix.entry_point_analysis must be an object",
        )
        if isinstance(entry_analysis, dict):
            analysis_file = entry_analysis.get("file")
            self.check(
                isinstance(analysis_file, str)
                and (ROOT / analysis_file).is_file(),
                "matrix.entry_point_analysis.file does not exist",
            )
            self.check(
                entry_analysis.get("closest_public_lead") in leads,
                "matrix.entry_point_analysis.closest_public_lead is unknown",
            )

        entry_target = entry_doc.get("target")
        matrix_target = matrix_doc.get("target")
        self.check(isinstance(entry_target, dict), "entry-points.target must be an object")
        self.check(isinstance(matrix_target, dict), "matrix.target must be an object")
        if isinstance(entry_target, dict) and isinstance(matrix_target, dict):
            for field in ("model", "family", "firmware_reported"):
                self.check(
                    entry_target.get(field) == matrix_target.get(field),
                    f"target.{field} differs between entry-points.json and compatibility-matrix.json",
                )

        for surface_id, surface in surfaces.items():
            self.status(surface, f"entry-points.surfaces[{surface_id}]")
            self.check(
                isinstance(surface.get("surface"), str) and bool(surface.get("surface")),
                f"entry-points.surfaces[{surface_id}] is missing surface",
            )
            self.refs(surface, "evidence", evidence, f"entry-points.surfaces[{surface_id}]")
            self.refs(surface, "sources", sources, f"entry-points.surfaces[{surface_id}]")
            if (
                surface.get("status") == "VERIFIED"
                and surface.get("software_only") is True
                and surface.get("leads_to_atmosphere") is True
            ):
                self.error(
                    f"entry-points.surfaces[{surface_id}] is a VERIFIED software-only "
                    "path to Atmosphère; this requires new reviewed evidence and a "
                    "decision-log entry"
                )

        for lead_id, lead in leads.items():
            self.status(lead, f"entry-points.leads[{lead_id}]")
            self.refs(lead, "evidence", evidence, f"entry-points.leads[{lead_id}]")
            self.refs(lead, "sources", sources, f"entry-points.leads[{lead_id}]")
            surface_ref = lead.get("surface")
            if surface_ref is not None:
                self.check(
                    surface_ref in surfaces,
                    f"entry-points.leads[{lead_id}].surface is unknown: {surface_ref}",
                )

        for hypothesis_id, hypothesis in hypotheses.items():
            label = f"hypotheses[{hypothesis_id}]"
            self.status(hypothesis, label)
            for field in (
                "title",
                "component",
                "hypothesis",
                "test_procedure",
                "kill_criteria",
                "last_reviewed",
            ):
                self.check(
                    isinstance(hypothesis.get(field), str)
                    and bool(hypothesis.get(field)),
                    f"{label} is missing {field}",
                )
            self.check(
                hypothesis.get("stage") in {"0", "1", "2", "3", "4"},
                f"{label} has invalid stage: {hypothesis.get('stage')!r}",
            )
            self.check(
                hypothesis.get("resolution")
                in {"open", "closed-negative", "closed-disproven", "blocked"},
                f"{label} has invalid resolution: {hypothesis.get('resolution')!r}",
            )
            self.check(
                hypothesis.get("surface") in surfaces,
                f"{label}.surface is unknown: {hypothesis.get('surface')!r}",
            )
            self.refs(hypothesis, "evidence", evidence, label)
            self.refs(hypothesis, "sources", sources, label)

        for flaw_id, flaw in flaws.items():
            self.refs(
                flaw,
                "evidence",
                evidence,
                f"entry-points.fixed_public_flaws[{flaw_id}]",
            )
            self.check(
                flaw.get("surface") in surfaces,
                f"entry-points.fixed_public_flaws[{flaw_id}].surface is unknown",
            )

        summary = entry_doc.get("summary")
        self.check(isinstance(summary, dict), "entry-points.summary must be an object")
        if isinstance(summary, dict):
            self.check(
                summary.get("closest_public_lead") in leads,
                "entry-points.summary.closest_public_lead is unknown",
            )
            self.status(summary, "entry-points.summary")

        surface_summary = entry_doc.get("surface_summary")
        self.check(
            isinstance(surface_summary, dict),
            "entry-points.surface_summary must be an object",
        )
        if isinstance(surface_summary, dict):
            status_counts = Counter(
                surface.get("status") for surface in surfaces.values()
            )
            expected_counts = {
                status: status_counts.get(status, 0) for status in STATUSES
            }
            self.check(
                surface_summary.get("status_counts") == expected_counts,
                "surface_summary.status_counts does not match the surface statuses",
            )
            self.check(
                surface_summary.get("total_surfaces") == len(surfaces),
                "surface_summary.total_surfaces does not match the surface count",
            )
            software_only = [
                surface_id
                for surface_id, surface in surfaces.items()
                if surface.get("software_only") is True
            ]
            self.check(
                surface_summary.get("software_only_surfaces") == len(software_only),
                "surface_summary.software_only_surfaces does not match",
            )
            public_chain = [
                surface_id
                for surface_id, surface in surfaces.items()
                if surface.get("public_chain_on_target") is True
            ]
            self.check(
                surface_summary.get("surfaces_with_public_chain_on_target")
                == public_chain,
                "surface_summary.surfaces_with_public_chain_on_target does not match",
            )
            software_only_chain = [
                surface_id
                for surface_id in public_chain
                if surfaces[surface_id].get("software_only") is True
                and surfaces[surface_id].get("leads_to_atmosphere") is True
            ]
            self.check(
                surface_summary.get("public_software_only_chain_on_target")
                == bool(software_only_chain),
                "surface_summary.public_software_only_chain_on_target does not match",
            )
            in_scope = [
                surface_id
                for surface_id, surface in surfaces.items()
                if surface.get("in_scope") is True
            ]
            self.check(
                surface_summary.get("in_scope_surfaces") == len(in_scope),
                "surface_summary.in_scope_surfaces does not match",
            )
            out_of_scope = [
                surface_id
                for surface_id, surface in surfaces.items()
                if surface.get("in_scope") is False
            ]
            self.check(
                surface_summary.get("out_of_scope_surfaces") == out_of_scope,
                "surface_summary.out_of_scope_surfaces does not match",
            )

        if isinstance(entry_analysis, dict):
            self.check(
                entry_analysis.get("surfaces_reviewed") == len(surfaces),
                "entry_point_analysis.surfaces_reviewed does not match",
            )
            software_only_count = sum(
                1 for surface in surfaces.values() if surface.get("software_only") is True
            )
            self.check(
                entry_analysis.get("software_only_surfaces") == software_only_count,
                "entry_point_analysis.software_only_surfaces does not match",
            )
            if isinstance(surface_summary, dict):
                self.check(
                    entry_analysis.get("public_software_only_chain_on_target")
                    == surface_summary.get("public_software_only_chain_on_target"),
                    "entry_point_analysis and surface_summary disagree on the software-only chain",
                )

        self.scan_secrets()

        if self.errors:
            print(f"Validation failed with {len(self.errors)} error(s):", file=sys.stderr)
            for message in self.errors:
                print(f"  - {message}", file=sys.stderr)
            return 1

        print(
            "Research data OK: "
            f"{len(sources)} sources, "
            f"{len(evidence)} evidence entries, "
            f"{len(surfaces)} entry-point surfaces, "
            f"{len(leads)} leads, "
            f"{len(hypotheses)} hypotheses, "
            f"{len(matrix_rows)} matrix rows, "
            f"{len(usb_modes)} USB modes."
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(Validator().run())
