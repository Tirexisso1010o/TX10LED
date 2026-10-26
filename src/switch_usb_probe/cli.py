"""Command-line interface for read-only Switch USB inspection.

The commands are intentionally narrow:

* ``doctor`` checks the host and repository.
* ``list`` and ``watch`` enumerate USB devices without opening them.
* ``classify`` explains a VID:PID offline.
* ``compat`` prints the research conclusion.
* ``ptp-info`` is the only command that opens a device, and only after
  ``--confirm``.  It sends the documented PTP identity query.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, TextIO

from . import __version__
from .classify import Classification, classify_device, classify_ids
from .doctor import run_doctor, summarize
from .enumeration import enumerate_usb_devices
from .errors import (
    ExitCode,
    NoDeviceError,
    ProbeError,
    UnsupportedModeError,
    UsageError,
)
from .log import JsonlLogger
from .models import EnumerationResult, UsbDevice
from .ptp import PtpClient, PtpDeviceInfo, UsbPtpTransport
from .sources import ResearchDataError, load_bundle
from .watch import WatchEvent, diff_snapshots, snapshot


class _Parser(argparse.ArgumentParser):
    """Argument parser that reports errors through the project's exit codes."""

    def error(self, message: str) -> None:
        raise UsageError(
            message,
            hint=f"Run `{self.prog} --help` for usage.",
        )


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def _usb_id(value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "must be a decimal or 0x-prefixed hexadecimal USB ID"
        ) from exc
    if not 0 <= parsed <= 0xFFFF:
        raise argparse.ArgumentTypeError("must be between 0x0000 and 0xffff")
    return parsed


def _json_requested(argv: Sequence[str] | None) -> bool:
    arguments = list(sys.argv[1:] if argv is None else argv)
    return "--json" in arguments


@contextlib.contextmanager
def _logger(args: argparse.Namespace) -> Iterator[JsonlLogger]:
    """Create a JSONL logger and close its file, if any."""

    handle: TextIO | None = None
    try:
        if args.log_file is not None:
            path = Path(args.log_file).expanduser()
            try:
                handle = path.open("a", encoding="utf-8")
            except OSError as exc:
                raise UsageError(
                    f"could not open log file {path}: {exc}",
                    hint="Choose a writable path, or omit --log-file.",
                ) from exc
            level = args.log_level or "info"
            yield JsonlLogger(handle, level=level)
        else:
            level = args.log_level or "warning"
            yield JsonlLogger(sys.stderr, level=level)
    finally:
        if handle is not None:
            handle.close()


def _print_error(error: ProbeError, *, json_mode: bool) -> None:
    if json_mode:
        payload = {"ok": False, "error": error.to_dict()}
        print(
            json.dumps(payload, sort_keys=True, ensure_ascii=False),
            file=sys.stderr,
        )
        return
    print(f"error: {error.message}", file=sys.stderr)
    if error.hint:
        print(f"hint: {error.hint}", file=sys.stderr)


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


def _device_row(device: UsbDevice) -> list[str]:
    classification = classify_device(device)
    return [
        device.vid_pid,
        classification.mode.value,
        device.display_name or classification.label,
        device.location_label or "-",
    ]


def _serialize_device(device: UsbDevice) -> dict[str, Any]:
    payload = device.to_dict()
    payload["classification"] = classify_device(device).to_dict()
    return payload


def _serialize_enumeration(result: EnumerationResult) -> dict[str, Any]:
    return {
        "backend": result.backend,
        "count": len(result.devices),
        "devices": [_serialize_device(device) for device in result.devices],
        "warnings": list(result.warnings),
    }


def _warn_warnings(result: EnumerationResult, logger: JsonlLogger) -> None:
    for warning in result.warnings:
        logger.warning("enumeration_warning", warning=warning)
        print(f"warning: {warning}", file=sys.stderr)


def _command_doctor(args: argparse.Namespace, logger: JsonlLogger) -> int:
    checks = run_doctor(
        enumerator=enumerate_usb_devices,
        timeout_s=args.timeout,
    )
    report = summarize(checks)
    if args.json:
        _print_json(report)
    else:
        _print_table(
            ["CHECK", "STATUS", "DETAIL"],
            [[check.name, check.status.upper(), check.detail] for check in checks],
        )
        for check in checks:
            if check.status == "fail" and check.remediation:
                print(f"\n{check.name}: {check.remediation}", file=sys.stderr)
        print(
            "\nNo USB device was opened. Optional PTP support is only used by "
            "`ptp-info --confirm`.",
            file=sys.stderr,
        )
    logger.info("doctor_complete", ok=report["ok"], counts=report["counts"])
    return int(ExitCode.OK) if report["ok"] else int(ExitCode.UNSUPPORTED)


def _command_list(args: argparse.Namespace, logger: JsonlLogger) -> int:
    result = enumerate_usb_devices(source=args.source, timeout_s=args.timeout)
    _warn_warnings(result, logger)
    devices = list(result.devices)
    if args.switch_only:
        devices = [device for device in devices if classify_device(device).is_console]

    if args.json:
        payload = {
            "backend": result.backend,
            "count": len(devices),
            "devices": [_serialize_device(device) for device in devices],
            "warnings": list(result.warnings),
            "filtered": "switch_only" if args.switch_only else None,
        }
        _print_json(payload)
    else:
        if not devices:
            print("No matching USB devices found." if args.switch_only else "No USB devices found.")
        else:
            _print_table(
                ["VID:PID", "MODE", "NAME", "LOCATION"],
                [_device_row(device) for device in devices],
            )
            console_notes: dict[str, tuple[str, ...]] = {}
            for device in devices:
                classification = classify_device(device)
                if classification.is_console:
                    console_notes.setdefault(classification.mode.value, classification.notes)
            if console_notes:
                print("\nNotes:")
                for mode, notes in console_notes.items():
                    for note in notes:
                        print(f"  {mode}: {note}")

    logger.info(
        "list_complete",
        backend=result.backend,
        total=len(result.devices),
        matched=len(devices),
        switch_only=args.switch_only,
    )
    if args.switch_only and not devices:
        return int(ExitCode.NO_DEVICE)
    return int(ExitCode.OK)


def _print_watch_event(event: WatchEvent, *, json_mode: bool) -> None:
    classification = classify_device(event.device)
    if json_mode:
        payload = event.to_dict()
        payload["device"]["classification"] = classification.to_dict()
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False), flush=True)
        return
    direction = "+" if event.kind == "connected" else "-"
    print(
        f"{direction} {event.device.vid_pid}  {classification.mode.value:<24} "
        f"{event.device.display_name or classification.label}",
        flush=True,
    )
    if classification.is_console and event.kind == "connected":
        for note in classification.notes:
            print(f"  {note}", flush=True)


def _command_watch(args: argparse.Namespace, logger: JsonlLogger) -> int:
    def enumerate_once() -> list[UsbDevice]:
        result = enumerate_usb_devices(source=args.source, timeout_s=args.timeout)
        _warn_warnings(result, logger)
        return list(result.devices)

    previous = snapshot(enumerate_once())
    logger.info("watch_started", baseline=len(previous), interval=args.interval)
    if not args.json:
        print(
            f"Watching for USB changes every {args.interval:g}s. Press Ctrl-C to stop.",
            file=sys.stderr,
        )

    events = 0
    failures = 0
    while True:
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("watch_cancelled", events=events)
            raise
        try:
            current = snapshot(enumerate_once())
            failures = 0
        except ProbeError as exc:
            failures += 1
            logger.warning(
                "watch_enumeration_failed",
                error=str(exc),
                consecutive_failures=failures,
            )
            if failures >= 3:
                raise
            continue

        connected, disconnected = diff_snapshots(previous, current)
        previous = current
        for device in connected:
            classification = classify_device(device)
            if args.switch_only and not classification.is_console:
                continue
            _print_watch_event(
                WatchEvent("connected", device),
                json_mode=args.json,
            )
            events += 1
            if args.count and events >= args.count:
                logger.info("watch_count_reached", events=events)
                return int(ExitCode.OK)
        for device in disconnected:
            classification = classify_device(device)
            if args.switch_only and not classification.is_console:
                continue
            _print_watch_event(
                WatchEvent("disconnected", device),
                json_mode=args.json,
            )
            events += 1
            if args.count and events >= args.count:
                logger.info("watch_count_reached", events=events)
                return int(ExitCode.OK)


def _command_classify(args: argparse.Namespace, logger: JsonlLogger) -> int:
    classification = classify_ids(args.vid, args.pid)
    if args.json:
        _print_json(
            {
                "vid_pid": f"{args.vid:04x}:{args.pid:04x}",
                **classification.to_dict(),
            }
        )
    else:
        print(f"VID:PID: {args.vid:04x}:{args.pid:04x}")
        print(f"Mode: {classification.mode.value}")
        print(f"Label: {classification.label}")
        print(f"Recognized: {'yes' if classification.recognized else 'no'}")
        print(f"Console: {'yes' if classification.is_console else 'no'}")
        print(f"PTP: {'yes' if classification.is_ptp else 'no'}")
        print(f"RCM: {'yes' if classification.is_rcm else 'no'}")
        print(f"Target PTP candidate: {'yes' if classification.is_target_ptp_candidate else 'no'}")
        print(f"Safety: {classification.safety}")
        if classification.notes:
            print("Notes:")
            for note in classification.notes:
                print(f"  - {note}")
    logger.info(
        "classify_complete",
        vid=f"0x{args.vid:04x}",
        pid=f"0x{args.pid:04x}",
        mode=classification.mode.value,
    )
    return int(ExitCode.OK)


def _command_compat(args: argparse.Namespace, logger: JsonlLogger) -> int:
    try:
        bundle = load_bundle()
    except ResearchDataError as exc:
        raise UnsupportedModeError(
            str(exc),
            hint="Run from the repository root or set SWITCH_USB_PROBE_ROOT.",
        ) from exc
    matrix = bundle.matrix
    target = matrix.get("target", {})
    conclusion = matrix.get("conclusion", {})
    rows = matrix.get("rows", [])
    entry_points = bundle.entry_point_list
    usb_modes = matrix.get("usb_modes", [])

    if args.json:
        _print_json(
            {
                "last_reviewed": matrix.get("last_reviewed"),
                "target": target,
                "conclusion": conclusion,
                "counts": {
                    "rows": len(rows) if isinstance(rows, list) else 0,
                    "entry_points": len(entry_points) if isinstance(entry_points, list) else 0,
                    "usb_modes": len(usb_modes) if isinstance(usb_modes, list) else 0,
                },
            }
        )
    else:
        if not isinstance(target, dict) or not isinstance(conclusion, dict):
            raise UnsupportedModeError("compatibility matrix is missing target or conclusion data")
        print("Switch OLED Atmosphère compatibility")
        print(f"Last reviewed: {matrix.get('last_reviewed', 'unknown')}")
        print()
        print(f"Target model: {target.get('model', 'unknown')}")
        print(f"Target family: {target.get('family', 'unknown')}")
        print(f"Firmware reported: {target.get('firmware_reported', 'unknown')}")
        print(f"Firmware verified: {'yes' if target.get('firmware_verified') else 'no'}")
        print()
        print(f"Claim: {conclusion.get('claim', 'unknown')}")
        print(f"Status: {conclusion.get('claim_status', 'unknown')}")
        print(
            "Software-only path documented: "
            f"{'yes' if conclusion.get('software_only_path_documented') else 'no'}"
        )
        print(f"Scope: {conclusion.get('scope', 'unknown')}")
        print(f"Entry-point surfaces reviewed: {len(entry_points)}")
        print()
        print(str(conclusion.get("summary", "")).strip())
        evidence = conclusion.get("evidence", [])
        if isinstance(evidence, list) and evidence:
            print(f"\nEvidence: {', '.join(str(item) for item in evidence)}")
        print(
            "\nThis is an absence-of-documented-method finding, not proof that "
            "no undisclosed exploit exists."
        )
    logger.info("compat_read", target=bundle.matrix.get("target", {}).get("model"))
    return int(ExitCode.OK)


def _select_ptp_candidate(result: EnumerationResult) -> tuple[UsbDevice, Classification]:
    candidates: list[tuple[UsbDevice, Classification]] = []
    for device in result.devices:
        classification = classify_device(device)
        if classification.is_ptp:
            candidates.append((device, classification))
    if not candidates:
        raise NoDeviceError(
            "no PTP-capable Switch device found",
            hint=(
                "Connect the console with a data-capable cable in the bottom port, "
                "then open Settings > Data Management > Manage Screenshots and "
                "Videos > Copy to PC via USB."
            ),
        )
    if len(candidates) > 1:
        listed = ", ".join(device.vid_pid for device, _ in candidates)
        raise UnsupportedModeError(
            f"multiple PTP candidates found ({listed}); refusing to guess",
            hint="Disconnect all but the target console, then retry.",
        )
    return candidates[0]


def _ptp_plan(device: UsbDevice, classification: Classification) -> dict[str, Any]:
    return {
        "opened": False,
        "dry_run": True,
        "device": device.to_dict(),
        "classification": classification.to_dict(),
        "planned_operations": [
            {
                "name": "GetDeviceInfo",
                "code": "0x1001",
                "direction": "read-only",
                "sends_data": False,
            }
        ],
        "session": {
            "default": "GetDeviceInfo only",
            "allow_session": "OpenSession 0x1002, GetDeviceInfo 0x1001, CloseSession 0x1003",
        },
        "notes": [
            "No device was opened and no USB request was sent.",
            "The default probe does not write data, transfer files, or send a payload.",
            "macOS ptpcamerad may hold the interface; this tool will not kill it.",
        ],
    }


def _command_ptp_info(args: argparse.Namespace, logger: JsonlLogger) -> int:
    result = enumerate_usb_devices(source=args.source, timeout_s=args.timeout)
    _warn_warnings(result, logger)
    device, classification = _select_ptp_candidate(result)

    if classification.mode.value == "switch2_ptp":
        print(
            "warning: the selected device is a Switch 2, not the OLED target.",
            file=sys.stderr,
        )

    plan = _ptp_plan(device, classification)
    if args.dry_run or not args.confirm:
        if args.json:
            _print_json(plan)
        else:
            print("PTP identity probe plan (dry run)")
            print(f"Device: {device.vid_pid}  {device.display_name or classification.label}")
            print(f"Mode: {classification.mode.value}")
            print("Planned operation: GetDeviceInfo (0x1001), read-only")
            print("Session: not opened unless --allow-session is required and approved")
            print("\nNo device was opened and no USB request was sent.")
            print("Re-run with --confirm after confirming the device identity.")
        logger.info(
            "ptp_dry_run",
            vid_pid=device.vid_pid,
            mode=classification.mode.value,
        )
        return int(ExitCode.OK)

    timeout_ms = max(100, int(args.timeout * 1000))
    info: PtpDeviceInfo | None = None
    session_opened = False
    transport: UsbPtpTransport | None = None
    client: PtpClient | None = None
    logger.info(
        "ptp_open",
        vid_pid=device.vid_pid,
        mode=classification.mode.value,
        allow_session=args.allow_session,
        timeout_ms=timeout_ms,
    )
    try:
        transport = UsbPtpTransport.open(
            device.vendor_id,
            device.product_id,
            timeout_ms=timeout_ms,
        )
        logger.info("ptp_interface_claimed", **transport.describe())
        client = PtpClient(
            transport,
            timeout_ms=timeout_ms,
            allow_session=args.allow_session,
            logger=logger,
        )
        info = client.get_device_info()
        session_opened = client.session_opened
        logger.info(
            "ptp_device_info",
            model=info.model,
            device_version=info.device_version,
            operations_count=len(info.operations_supported),
            session_opened=session_opened,
        )
    finally:
        if client is not None:
            client.close()
        if transport is not None:
            transport.close()

    if info is None:  # pragma: no cover - defensive
        raise UnsupportedModeError("the PTP probe produced no DeviceInfo")

    payload = {
        "opened": True,
        "dry_run": False,
        "device": device.to_dict(),
        "classification": classification.to_dict(),
        "session_opened": session_opened,
        "ptp": info.to_dict(),
        "limitations": [
            "PTP DeviceInfo is a read-only identity observation.",
            "It does not prove exploitability, boot state, CFW access, or console integrity.",
            "A modified firmware can spoof the response.",
        ],
    }
    if args.json:
        _print_json(payload)
    else:
        print("PTP DeviceInfo (read-only)")
        print(f"Manufacturer: {info.manufacturer or '-'}")
        print(f"Model: {info.model or '-'}")
        print(f"Device version: {info.device_version or '-'}")
        print(f"Serial prefix: {info.to_dict().get('serial_prefix') or '-'}")
        print(f"Operations supported: {len(info.operations_supported)}")
        print(f"Session opened: {'yes' if session_opened else 'no'}")
        print(
            "\nThis is an identity observation, not proof of exploitability or "
            "console integrity."
        )
    return int(ExitCode.OK)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="switch-usb-probe",
        description=(
            "Read-only macOS USB inspection and PTP identity probe for "
            "Nintendo Switch research."
        ),
        epilog=(
            "No command sends a payload, writes to a device, or changes console "
            "state. Only `ptp-info --confirm` opens a device."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON on stdout",
    )
    common.add_argument(
        "--log-file",
        type=Path,
        help="append JSONL structured logs to this file (serials are redacted)",
    )
    common.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        help="log level (default: warning to stderr, info when --log-file is used)",
    )

    usb_common = argparse.ArgumentParser(add_help=False)
    usb_common.add_argument(
        "--source",
        choices=["auto", "system_profiler", "ioreg"],
        default="auto",
        help="enumeration backend (default: auto)",
    )
    usb_common.add_argument(
        "--timeout",
        type=_positive_float,
        default=10.0,
        help="enumeration and USB timeout in seconds (default: 10)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor",
        parents=[common, usb_common],
        help="check the host, optional dependencies, research data, and USB bus",
    )
    doctor.set_defaults(func=_command_doctor)

    list_parser = subparsers.add_parser(
        "list",
        parents=[common, usb_common],
        help="enumerate USB devices without opening them",
    )
    list_parser.add_argument(
        "--switch-only",
        action="store_true",
        help="only show recognized console modes",
    )
    list_parser.set_defaults(func=_command_list)

    watch = subparsers.add_parser(
        "watch",
        parents=[common, usb_common],
        help="poll for USB connect and disconnect events",
    )
    watch.add_argument(
        "--interval",
        type=_positive_float,
        default=1.0,
        help="polling interval in seconds (default: 1)",
    )
    watch.add_argument(
        "--count",
        type=_non_negative_int,
        default=0,
        help="exit after this many events; 0 means run until cancelled",
    )
    watch.add_argument(
        "--switch-only",
        action="store_true",
        help="only report recognized console modes",
    )
    watch.set_defaults(func=_command_watch)

    classify = subparsers.add_parser(
        "classify",
        parents=[common],
        help="explain a USB VID:PID offline",
    )
    classify.add_argument("--vid", type=_usb_id, required=True, help="USB vendor ID")
    classify.add_argument("--pid", type=_usb_id, required=True, help="USB product ID")
    classify.set_defaults(func=_command_classify)

    compat = subparsers.add_parser(
        "compat",
        parents=[common],
        help="print the current compatibility conclusion",
    )
    compat.set_defaults(func=_command_compat)

    ptp = subparsers.add_parser(
        "ptp-info",
        parents=[common, usb_common],
        help="read PTP DeviceInfo after an explicit confirmation gate",
    )
    gate = ptp.add_mutually_exclusive_group()
    gate.add_argument(
        "--dry-run",
        action="store_true",
        help="show the plan without importing pyusb or opening the device",
    )
    gate.add_argument(
        "--confirm",
        action="store_true",
        help="open the selected device and send only the read-only identity query",
    )
    ptp.add_argument(
        "--allow-session",
        action="store_true",
        help=(
            "if the device requires it, send OpenSession and CloseSession around "
            "GetDeviceInfo; no other operation is sent"
        ),
    )
    ptp.set_defaults(func=_command_ptp_info)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    json_mode = _json_requested(argv)
    try:
        args = parser.parse_args(argv)
        json_mode = bool(args.json)
        with _logger(args) as logger:
            return int(args.func(args, logger))
    except ProbeError as exc:
        _print_error(exc, json_mode=json_mode)
        return int(exc.exit_code)
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return int(ExitCode.CANCELLED)
    except BrokenPipeError:
        return int(ExitCode.OK)
