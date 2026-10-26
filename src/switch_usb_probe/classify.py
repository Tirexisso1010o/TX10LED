"""Known Nintendo Switch USB modes and safety-oriented classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import UsbDevice, format_vid_pid

NINTENDO_VENDOR_ID = 0x057E
NVIDIA_VENDOR_ID = 0x0955


class UsbMode(str, Enum):
    SWITCH_NORMAL = "switch_normal"
    SWITCH_PTP = "switch_ptp"
    SWITCH2_PTP = "switch2_ptp"
    SWITCH_RCM = "switch_rcm"
    SWITCH_PRO_CONTROLLER = "switch_pro_controller"
    JOYCON_LEFT = "joycon_left"
    JOYCON_RIGHT = "joycon_right"
    JOYCON_GRIP = "joycon_grip"
    NINTENDO_UNKNOWN = "nintendo_unknown"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class KnownDevice:
    mode: UsbMode
    label: str
    recognized: bool
    is_console: bool
    is_ptp: bool
    is_rcm: bool
    is_target_ptp_candidate: bool
    notes: tuple[str, ...] = field(default_factory=tuple)
    safety: str = "Inspection only."


KNOWN_DEVICES: dict[tuple[int, int], KnownDevice] = {
    (NINTENDO_VENDOR_ID, 0x2000): KnownDevice(
        mode=UsbMode.SWITCH_NORMAL,
        label="Nintendo Switch (normal USB mode)",
        recognized=True,
        is_console=True,
        is_ptp=False,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=(
            "Normal operation does not expose a documented shell, ADB, or firmware-query interface.",
            "Identification only; the tool does not claim control capability.",
        ),
        safety="Inspection only. No device interface is opened.",
    ),
    (NINTENDO_VENDOR_ID, 0x201D): KnownDevice(
        mode=UsbMode.SWITCH_PTP,
        label="Nintendo Switch / Switch Lite (PTP album mode)",
        recognized=True,
        is_console=True,
        is_ptp=True,
        is_rcm=False,
        is_target_ptp_candidate=True,
        notes=(
            "Copy to PC via USB mode. Only PTP operations 0x1001-0x100A are documented.",
            "GetDeviceInfo can report model, system display version, and serial prefix.",
            "OLED enumeration is partially verified until a hardware observation is recorded.",
        ),
        safety="Read-only GetDeviceInfo is supported. No writes, object transfer, or payloads.",
    ),
    (NINTENDO_VENDOR_ID, 0x2061): KnownDevice(
        mode=UsbMode.SWITCH2_PTP,
        label="Nintendo Switch 2 (PTP album mode)",
        recognized=True,
        is_console=True,
        is_ptp=True,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=(
            "Switch 2 product ID; this is not the OLED target.",
            "The same PTP identity query may work, but the research target is the original Switch OLED.",
        ),
        safety="Read-only GetDeviceInfo is supported. Do not confuse this with the OLED target.",
    ),
    (NVIDIA_VENDOR_ID, 0x7321): KnownDevice(
        mode=UsbMode.SWITCH_RCM,
        label="NVIDIA Tegra APX / Switch RCM",
        recognized=True,
        is_console=True,
        is_ptp=False,
        is_rcm=True,
        is_target_ptp_candidate=False,
        notes=(
            "RCM is reachable on patched consoles, but a payload cannot be accepted on Mariko/OLED.",
            "This project does not send payloads or exploit RCM.",
        ),
        safety="Do not send a payload. RCM presence is not evidence that injection works.",
    ),
    (NINTENDO_VENDOR_ID, 0x2009): KnownDevice(
        mode=UsbMode.SWITCH_PRO_CONTROLLER,
        label="Nintendo Switch Pro Controller",
        recognized=True,
        is_console=False,
        is_ptp=False,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=("Controller only; not a console.",),
        safety="Inspection only.",
    ),
    (NINTENDO_VENDOR_ID, 0x2006): KnownDevice(
        mode=UsbMode.JOYCON_LEFT,
        label="Nintendo Switch Joy-Con (L)",
        recognized=True,
        is_console=False,
        is_ptp=False,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=("Controller only; not a console.",),
        safety="Inspection only.",
    ),
    (NINTENDO_VENDOR_ID, 0x2007): KnownDevice(
        mode=UsbMode.JOYCON_RIGHT,
        label="Nintendo Switch Joy-Con (R)",
        recognized=True,
        is_console=False,
        is_ptp=False,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=("Controller only; not a console.",),
        safety="Inspection only.",
    ),
    (NINTENDO_VENDOR_ID, 0x200E): KnownDevice(
        mode=UsbMode.JOYCON_GRIP,
        label="Nintendo Switch Joy-Con charging grip",
        recognized=True,
        is_console=False,
        is_ptp=False,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=("Accessory only; not a console.",),
        safety="Inspection only.",
    ),
}


@dataclass(frozen=True)
class Classification:
    mode: UsbMode
    label: str
    recognized: bool
    is_console: bool
    is_ptp: bool
    is_rcm: bool
    is_target_ptp_candidate: bool
    notes: tuple[str, ...]
    safety: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "label": self.label,
            "recognized": self.recognized,
            "is_console": self.is_console,
            "is_ptp": self.is_ptp,
            "is_rcm": self.is_rcm,
            "is_target_ptp_candidate": self.is_target_ptp_candidate,
            "notes": list(self.notes),
            "safety": self.safety,
        }


def classify_device(device: UsbDevice) -> Classification:
    """Classify a device without opening it."""

    known = KNOWN_DEVICES.get((device.vendor_id, device.product_id))
    if known is not None:
        return Classification(
            mode=known.mode,
            label=known.label,
            recognized=known.recognized,
            is_console=known.is_console,
            is_ptp=known.is_ptp,
            is_rcm=known.is_rcm,
            is_target_ptp_candidate=known.is_target_ptp_candidate,
            notes=known.notes,
            safety=known.safety,
        )

    if device.vendor_id == NINTENDO_VENDOR_ID:
        return Classification(
            mode=UsbMode.NINTENDO_UNKNOWN,
            label="Nintendo device (unrecognized product ID)",
            recognized=True,
            is_console=False,
            is_ptp=False,
            is_rcm=False,
            is_target_ptp_candidate=False,
            notes=(
                f"Vendor 0x{NINTENDO_VENDOR_ID:04x} is Nintendo, but product "
                f"0x{device.product_id:04x} is not in the local table.",
                "No control capability is claimed for an unrecognized product ID.",
            ),
            safety="Inspection only. Do not assume a protocol from the vendor ID alone.",
        )

    return Classification(
        mode=UsbMode.UNKNOWN,
        label="Unrecognized USB device",
        recognized=False,
        is_console=False,
        is_ptp=False,
        is_rcm=False,
        is_target_ptp_candidate=False,
        notes=(
            f"VID:PID {format_vid_pid(device.vendor_id, device.product_id)} is not in the local table.",
            "The tool does not open or control unrecognized devices.",
        ),
        safety="Inspection only.",
    )


def classify_ids(vendor_id: int, product_id: int) -> Classification:
    return classify_device(UsbDevice(vendor_id=vendor_id, product_id=product_id))
