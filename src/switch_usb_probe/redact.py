"""Serial-number and log-field redaction.

The research only needs a short prefix to distinguish model families.  Keeping
the full serial adds privacy risk without adding compatibility value, so every
device-derived string passes through this module before it is printed or
logged.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "serial",
        "serial_number",
        "serial_num",
        "serialnumber",
        "serial_no",
        "serialno",
        "device_serial",
        "usb_serial_number",
        "usb_serial",
        "sn",
    }
)

# Nintendo serials observed in the wild are commonly 14-16 characters and start
# with a three-letter model/region prefix such as XAW, XKW, XTW, XTJ, or HAE.
# This is intentionally conservative: it should catch a real serial in prose or
# JSON without treating ordinary identifiers as secrets.
SERIAL_RE = re.compile(r"\b(?:X[A-Z]{2}|H[A-Z]{2})[0-9A-Z]{8,14}\b")

REDACTED = "***"


def redact_serial(value: str | None, *, prefix_len: int = 3) -> str | None:
    """Return a short prefix plus a fixed redaction marker.

    ``None`` and empty values stay ``None``.  Very short values are fully
    redacted so the function never accidentally returns a complete serial.
    """

    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if prefix_len <= 0 or len(cleaned) <= prefix_len:
        return REDACTED
    return f"{cleaned[:prefix_len]}{REDACTED}"


def redact_text(text: str) -> str:
    """Redact anything that looks like a Nintendo serial number in free text."""

    return SERIAL_RE.sub(lambda match: f"{match.group(0)[:3]}{REDACTED}", text)


def contains_probable_serial(text: str) -> bool:
    """Return whether *text* contains a plausible full serial number."""

    return SERIAL_RE.search(text) is not None


def redact_mapping(value: Any) -> Any:
    """Recursively redact sensitive keys and serial-shaped strings.

    Dict keys are matched case-insensitively.  A value under a sensitive key is
    replaced with a redacted form even if it does not match the serial regex,
    because the key itself is a strong signal.
    """

    if isinstance(value, Mapping):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in SENSITIVE_KEYS:
                if isinstance(item, str):
                    result[key] = redact_serial(item)
                elif item is None:
                    result[key] = None
                else:
                    result[key] = REDACTED
            else:
                result[key] = redact_mapping(item)
        return result
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_mapping(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
