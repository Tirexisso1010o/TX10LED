"""Connect/disconnect diffing for the polling watch command."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Hashable

from .models import UsbDevice

DeviceKey = tuple[Any, ...]


def device_key(device: UsbDevice) -> DeviceKey:
    """Stable key for a physical device across enumeration passes."""

    if device.location_id is not None:
        return ("location", device.vendor_id, device.product_id, device.location_id)
    if device.bus is not None and device.address is not None:
        return (
            "bus",
            device.vendor_id,
            device.product_id,
            device.bus,
            device.address,
        )
    return (
        "identity",
        device.vendor_id,
        device.product_id,
        device.name,
        device.manufacturer,
    )


def snapshot(devices: Iterable[UsbDevice]) -> dict[DeviceKey, UsbDevice]:
    result: dict[DeviceKey, UsbDevice] = {}
    for device in devices:
        result[device_key(device)] = device
    return result


def diff_snapshots(
    previous: Mapping[DeviceKey, UsbDevice],
    current: Mapping[DeviceKey, UsbDevice],
) -> tuple[list[UsbDevice], list[UsbDevice]]:
    """Return ``(connected, disconnected)`` in deterministic order."""

    connected_keys = sorted(current.keys() - previous.keys(), key=str)
    disconnected_keys = sorted(previous.keys() - current.keys(), key=str)
    return (
        [current[key] for key in connected_keys],
        [previous[key] for key in disconnected_keys],
    )


@dataclass(frozen=True)
class WatchEvent:
    kind: str
    device: UsbDevice

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.kind,
            "device": self.device.to_dict(),
        }
