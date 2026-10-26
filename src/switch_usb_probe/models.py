"""Data records shared by enumeration, classification, and the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .redact import redact_serial


@dataclass(frozen=True)
class UsbDevice:
    """A USB device as observed by a host enumeration backend.

    ``raw`` is kept for debugging but is never serialized by default.  It may
    contain host-specific fields, including a full serial number.
    """

    vendor_id: int
    product_id: int
    name: str = ""
    manufacturer: str = ""
    serial_number: str | None = None
    location_id: int | None = None
    bus: int | None = None
    address: int | None = None
    device_class: int | None = None
    source: str = "unknown"
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def vid_pid(self) -> str:
        return format_vid_pid(self.vendor_id, self.product_id)

    @property
    def serial_prefix(self) -> str | None:
        return redact_serial(self.serial_number)

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        if self.manufacturer:
            return f"{self.manufacturer} device"
        return "Unnamed USB device"

    @property
    def location_label(self) -> str | None:
        if self.location_id is not None:
            return f"0x{self.location_id:08x}"
        if self.bus is not None and self.address is not None:
            return f"bus {self.bus} address {self.address}"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize without a full serial number or raw host data."""

        payload: dict[str, Any] = {
            "vid_pid": self.vid_pid,
            "vendor_id": f"0x{self.vendor_id:04x}",
            "product_id": f"0x{self.product_id:04x}",
            "name": self.name,
            "manufacturer": self.manufacturer,
            "serial_prefix": self.serial_prefix,
            "source": self.source,
        }
        if self.location_id is not None:
            payload["location_id"] = f"0x{self.location_id:08x}"
        if self.bus is not None:
            payload["bus"] = self.bus
        if self.address is not None:
            payload["address"] = self.address
        if self.device_class is not None:
            payload["device_class"] = f"0x{self.device_class:02x}"
        return payload


@dataclass(frozen=True)
class EnumerationResult:
    """The result of one host enumeration pass."""

    devices: tuple[UsbDevice, ...] = ()
    backend: str = "unknown"
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "count": len(self.devices),
            "devices": [device.to_dict() for device in self.devices],
            "warnings": list(self.warnings),
        }


def format_vid_pid(vendor_id: int, product_id: int) -> str:
    return f"{vendor_id:04x}:{product_id:04x}"
