"""Read-only macOS USB inspection and PTP identity probe.

The package is deliberately small and inspection-first.  The only module that
opens a USB device is :mod:`switch_usb_probe.ptp`, and it is used only by the
opt-in ``ptp-info`` command.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
