"""Read-only USB enumeration backends for macOS.

The primary backend is ``system_profiler``.  ``ioreg`` is a fallback when the
primary command fails.  Neither backend opens a USB device or claims an
interface.
"""

from __future__ import annotations

import json
import plistlib
import re
import subprocess
from collections.abc import Callable, Iterable
from typing import Any

from .errors import EnumerationError, OperationTimeout, UnsupportedModeError
from .models import EnumerationResult, UsbDevice
from .redact import redact_text

Runner = Callable[[list[str], float], str]

_SYSTEM_PROFILER_ARGS = ["system_profiler", "SPUSBDataType", "-json"]
_IOREG_ARGS = ["ioreg", "-a", "-p", "IOUSB", "-l", "-w", "0"]

_VALID_SOURCES = {"auto", "system_profiler", "ioreg"}


def run_command(args: list[str], timeout_s: float) -> str:
    """Run a read-only host command and return stdout.

    A non-zero exit status, a missing command, or a timeout becomes a typed
    error.  The command itself is never constructed from device-controlled
    input.
    """

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OperationTimeout(
            f"command timed out after {timeout_s:g}s: {' '.join(args)}",
            hint="Disconnect and reconnect the USB device, then retry once.",
        ) from exc
    except FileNotFoundError as exc:
        raise EnumerationError(
            f"required host command not found: {args[0]}",
            hint="This backend is macOS-specific. Use --source with an available backend.",
        ) from exc
    except OSError as exc:
        raise EnumerationError(
            f"could not run {args[0]}: {exc}",
        ) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        detail = redact_text(detail[:300])
        message = f"{args[0]} exited with status {completed.returncode}"
        if detail:
            message = f"{message}: {detail}"
        raise EnumerationError(message)

    return completed.stdout


def parse_usb_id(value: Any) -> int | None:
    """Parse a USB ID from system_profiler or ioreg output."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"0x[0-9a-fA-F]+", text)
    if match:
        return int(match.group(0), 16)
    if re.fullmatch(r"[0-9a-fA-F]{4}", text):
        return int(text, 16)
    if re.fullmatch(r"\d+", text):
        return int(text, 10)
    return None


def _parse_location(value: Any) -> int | None:
    return parse_usb_id(value)


def _dedupe(devices: Iterable[UsbDevice]) -> tuple[UsbDevice, ...]:
    seen: set[tuple[Any, ...]] = set()
    result: list[UsbDevice] = []
    for device in devices:
        key = (
            device.vendor_id,
            device.product_id,
            device.location_id,
            device.name if device.location_id is None else None,
            device.manufacturer if device.location_id is None else None,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(device)

    def sort_key(device: UsbDevice) -> tuple[int, int, int, str]:
        location = device.location_id if device.location_id is not None else 1 << 62
        return (location, device.vendor_id, device.product_id, device.name)

    return tuple(sorted(result, key=sort_key))


def _walk_system_profiler(items: Any, *, depth: int = 0) -> list[UsbDevice]:
    if depth > 16 or not isinstance(items, list):
        return []
    found: list[UsbDevice] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        vendor_id = parse_usb_id(item.get("vendor_id"))
        product_id = parse_usb_id(item.get("product_id"))
        if vendor_id is not None and product_id is not None:
            found.append(
                UsbDevice(
                    vendor_id=vendor_id,
                    product_id=product_id,
                    name=str(item.get("_name") or item.get("USB Product Name") or ""),
                    manufacturer=str(
                        item.get("manufacturer") or item.get("USB Vendor Name") or ""
                    ),
                    serial_number=item.get("serial_num")
                    or item.get("USB Serial Number"),
                    location_id=_parse_location(item.get("location_id")),
                    device_class=parse_usb_id(item.get("bDeviceClass")),
                    source="system_profiler",
                    raw=dict(item),
                )
            )
        found.extend(
            _walk_system_profiler(item.get("_items"), depth=depth + 1)
        )
    return found


def parse_system_profiler_json(raw: str | bytes | dict[str, Any]) -> tuple[UsbDevice, ...]:
    """Parse ``system_profiler SPUSBDataType -json`` output."""

    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", errors="replace")
        except Exception as exc:  # pragma: no cover - defensive
            raise EnumerationError("could not decode system_profiler output") from exc
    if isinstance(raw, str):
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EnumerationError(
                f"system_profiler returned invalid JSON: {exc.msg}",
            ) from exc
    elif isinstance(raw, dict):
        document = raw
    else:
        raise EnumerationError("system_profiler output must be a JSON object")

    if not document:
        return ()
    items = document.get("SPUSBDataType")
    if items is None:
        raise EnumerationError("system_profiler JSON is missing SPUSBDataType")
    if not isinstance(items, list):
        raise EnumerationError("SPUSBDataType must be a list")
    return _dedupe(_walk_system_profiler(items))


def _walk_ioreg(value: Any, *, depth: int = 0) -> list[UsbDevice]:
    if depth > 32:
        return []
    found: list[UsbDevice] = []
    if isinstance(value, dict):
        vendor_id = parse_usb_id(value.get("idVendor"))
        product_id = parse_usb_id(value.get("idProduct"))
        if vendor_id is not None and product_id is not None:
            name = (
                value.get("USB Product Name")
                or value.get("IORegistryEntryName")
                or ""
            )
            found.append(
                UsbDevice(
                    vendor_id=vendor_id,
                    product_id=product_id,
                    name=str(name),
                    manufacturer=str(value.get("USB Vendor Name") or ""),
                    serial_number=value.get("USB Serial Number"),
                    location_id=_parse_location(value.get("locationID")),
                    device_class=parse_usb_id(value.get("bDeviceClass")),
                    source="ioreg",
                    raw=dict(value),
                )
            )
        for child in value.values():
            found.extend(_walk_ioreg(child, depth=depth + 1))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_ioreg(child, depth=depth + 1))
    return found


def parse_ioreg_plist(raw: str | bytes | dict[str, Any]) -> tuple[UsbDevice, ...]:
    """Parse ``ioreg -a -p IOUSB -l -w 0`` property-list output."""

    if isinstance(raw, str):
        raw_bytes = raw.encode("utf-8", errors="replace")
    elif isinstance(raw, bytes):
        raw_bytes = raw
    elif isinstance(raw, dict):
        return _dedupe(_walk_ioreg(raw))
    else:
        raise EnumerationError("ioreg output must be a property list or object")

    try:
        document = plistlib.loads(raw_bytes)
    except (plistlib.InvalidFileException, ValueError, TypeError) as exc:
        raise EnumerationError(f"ioreg returned an invalid property list: {exc}") from exc
    return _dedupe(_walk_ioreg(document))


def enumerate_usb_devices(
    *,
    source: str = "auto",
    timeout_s: float = 10.0,
    runner: Runner | None = None,
) -> EnumerationResult:
    """Enumerate USB devices without opening them."""

    if source not in _VALID_SOURCES:
        raise UnsupportedModeError(
            f"unsupported enumeration source: {source}",
            hint="Use auto, system_profiler, or ioreg.",
        )
    if timeout_s <= 0:
        raise UnsupportedModeError("timeout must be greater than zero")

    command_runner = runner or run_command
    warnings: list[str] = []

    if source in {"auto", "system_profiler"}:
        try:
            raw = command_runner(_SYSTEM_PROFILER_ARGS, timeout_s)
            devices = parse_system_profiler_json(raw)
            return EnumerationResult(
                devices=devices,
                backend="system_profiler",
                warnings=tuple(warnings),
            )
        except (OperationTimeout, EnumerationError) as exc:
            if source == "system_profiler":
                raise
            warnings.append(
                f"system_profiler unavailable ({exc}); falling back to ioreg"
            )

    raw = command_runner(_IOREG_ARGS, timeout_s)
    devices = parse_ioreg_plist(raw)
    return EnumerationResult(
        devices=devices,
        backend="ioreg",
        warnings=tuple(warnings),
    )
