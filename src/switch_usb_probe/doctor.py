"""Environment and repository diagnostics for the CLI."""

from __future__ import annotations

import ctypes.util
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .classify import classify_device
from .errors import ProbeError
from .models import EnumerationResult
from .sources import ResearchDataError, load_bundle, repo_root


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
        if self.remediation:
            payload["remediation"] = self.remediation
        return payload


def _check_macos() -> Check:
    system = platform.system()
    version = platform.mac_ver()[0] or platform.release()
    if system == "Darwin":
        return Check("macOS", "ok", f"{version} ({platform.machine()})")
    return Check(
        "macOS",
        "warn",
        f"host is {system or 'unknown'}; the enumeration backends are macOS-specific",
        "Run the CLI on macOS for hardware inspection.",
    )


def _check_python() -> Check:
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= (3, 11):
        return Check("Python", "ok", f"{version} ({sys.executable})")
    return Check(
        "Python",
        "fail",
        f"{version} is older than the required 3.11",
        "Use Python 3.11 or newer.",
    )


def _check_command(name: str, remediation: str) -> Check:
    path = shutil.which(name)
    if path:
        return Check(name, "ok", path)
    return Check(name, "fail", "not found on PATH", remediation)


def _check_pyusb() -> Check:
    if importlib.util.find_spec("usb") is not None:
        return Check("pyusb", "ok", "installed (optional PTP support available)")
    return Check(
        "pyusb",
        "warn",
        "not installed (optional; only ptp-info needs it)",
        "Create a repository-local .venv and install the ptp extra after approval.",
    )


def _check_libusb() -> Check:
    found = ctypes.util.find_library("usb-1.0")
    if found:
        return Check("libusb", "ok", found)
    for candidate in (
        Path("/opt/homebrew/lib/libusb-1.0.dylib"),
        Path("/usr/local/lib/libusb-1.0.dylib"),
    ):
        if candidate.exists():
            return Check("libusb", "ok", str(candidate))
    return Check(
        "libusb",
        "warn",
        "libusb-1.0 was not found in the usual locations",
        "Only needed for ptp-info. Discuss any installation before changing the system.",
    )


def _check_ptpcamerad() -> Check:
    executable = shutil.which("pgrep")
    if not executable:
        return Check("ptpcamerad", "info", "pgrep not available; cannot check")
    try:
        completed = subprocess.run(
            [executable, "-x", "ptpcamerad"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check("ptpcamerad", "info", f"check failed: {exc}")
    if completed.returncode == 0:
        return Check(
            "ptpcamerad",
            "warn",
            "running; it may claim a PTP interface",
            "Close conflicting apps. Do not kill the daemon or disable SIP automatically.",
        )
    return Check("ptpcamerad", "ok", "not running")


def _check_research(root: Path) -> Check:
    try:
        bundle = load_bundle(root)
    except ResearchDataError as exc:
        return Check(
            "research data",
            "fail",
            str(exc),
            "Restore research/sources.json, evidence-ledger.json, entry-points.json, and compatibility-matrix.json.",
        )
    return Check(
        "research data",
        "ok",
        (
            f"{len(bundle.source_list)} sources, "
            f"{len(bundle.evidence_list)} evidence entries, "
            f"{len(bundle.entry_point_list)} entry-point surfaces, "
            f"target {bundle.matrix.get('target', {}).get('model', 'unknown')}"
        ),
    )


def _check_opencode_config(root: Path) -> Check:
    path = root / "opencode.json"
    if not path.exists():
        return Check(
            "opencode.json",
            "ok",
            "not present (optional)",
            "This file is intentionally untracked; a local permission policy is optional.",
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Check("opencode.json", "fail", f"invalid JSON: {exc}")
    permissions = document.get("permissions")
    if not isinstance(permissions, list):
        return Check(
            "opencode.json",
            "warn",
            "no v2 permissions array found",
            "Use the v2 ordered permissions rules.",
        )
    return Check("opencode.json", "ok", f"{len(permissions)} permission rules")


def _check_usb(
    enumerator: Callable[..., EnumerationResult],
    timeout_s: float,
) -> Check:
    try:
        result = enumerator(source="auto", timeout_s=timeout_s)
    except ProbeError as exc:
        return Check(
            "USB bus",
            "fail",
            exc.message,
            exc.hint,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return Check("USB bus", "fail", f"unexpected enumeration error: {exc}")
    consoles = sum(1 for device in result.devices if classify_device(device).is_console)
    detail = (
        f"{len(result.devices)} device(s) via {result.backend}; "
        f"{consoles} recognized console mode(s)"
    )
    if result.warnings:
        detail = f"{detail}; warnings: {'; '.join(result.warnings)}"
    return Check("USB bus", "ok", detail)


def run_doctor(
    *,
    enumerator: Callable[..., EnumerationResult],
    timeout_s: float = 10.0,
    root: Path | None = None,
) -> list[Check]:
    base = root or repo_root()
    return [
        _check_macos(),
        _check_python(),
        _check_command(
            "system_profiler",
            "This command is part of macOS; check the PATH and OS installation.",
        ),
        _check_command(
            "ioreg",
            "This command is part of macOS; check the PATH and OS installation.",
        ),
        _check_pyusb(),
        _check_libusb(),
        _check_ptpcamerad(),
        _check_research(base),
        _check_opencode_config(base),
        _check_usb(enumerator, timeout_s),
    ]


def summarize(checks: list[Check]) -> dict[str, Any]:
    counts = {"ok": 0, "warn": 0, "fail": 0, "info": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    return {
        "ok": counts["fail"] == 0,
        "counts": counts,
        "checks": [check.to_dict() for check in checks],
    }
