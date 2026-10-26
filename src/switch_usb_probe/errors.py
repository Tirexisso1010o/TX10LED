"""Typed errors and the CLI exit-code contract."""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class ExitCode(IntEnum):
    """Stable process exit codes documented in the README."""

    OK = 0
    NO_DEVICE = 2
    ACCESS = 3
    TIMEOUT = 4
    UNSUPPORTED = 5
    CANCELLED = 130


class ProbeError(Exception):
    """Base class for expected, user-facing failures."""

    exit_code: ExitCode = ExitCode.UNSUPPORTED

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": type(self).__name__,
            "message": self.message,
            "exit_code": int(self.exit_code),
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.details:
            payload["details"] = self.details
        return payload


class UsageError(ProbeError):
    """Invalid command-line input."""

    exit_code = ExitCode.UNSUPPORTED


class NoDeviceError(ProbeError):
    """No device matched the request."""

    exit_code = ExitCode.NO_DEVICE


class DeviceAccessError(ProbeError):
    """The device exists but could not be opened or claimed."""

    exit_code = ExitCode.ACCESS


class DeviceBusyError(DeviceAccessError):
    """The device or interface is claimed by another process."""


class OperationTimeout(ProbeError):
    """An enumeration or USB operation exceeded its deadline."""

    exit_code = ExitCode.TIMEOUT


class UnsupportedModeError(ProbeError):
    """The requested mode, device, or operation is not supported."""

    exit_code = ExitCode.UNSUPPORTED


class DependencyMissing(UnsupportedModeError):
    """An optional dependency or native library is unavailable."""


class EnumerationError(UnsupportedModeError):
    """The host enumeration backend failed."""


class PtpProtocolError(UnsupportedModeError):
    """A PTP response was malformed or did not follow the expected flow."""


class PtpResponseError(PtpProtocolError):
    """The device returned a non-success PTP response code."""

    def __init__(self, code: int, *, operation: int | None = None) -> None:
        self.code = code
        self.operation = operation
        name = PTP_RESPONSE_NAMES.get(code, "unknown")
        message = f"PTP response 0x{code:04x} ({name})"
        if operation is not None:
            message = f"{message} for operation 0x{operation:04x}"
        super().__init__(message, details={"response_code": f"0x{code:04x}"})


class PtpSessionRequired(UnsupportedModeError):
    """The device requires OpenSession before GetDeviceInfo."""


class ProbeCancelled(ProbeError):
    """The user cancelled a long-running operation."""

    exit_code = ExitCode.CANCELLED


# Response names used only for diagnostics.  The list is intentionally short;
# unknown codes remain numeric.
PTP_RESPONSE_NAMES: dict[int, str] = {
    0x2000: "Undefined",
    0x2001: "OK",
    0x2002: "GeneralError",
    0x2003: "SessionNotOpen",
    0x2004: "InvalidTransactionID",
    0x2005: "OperationNotSupported",
    0x2006: "ParameterNotSupported",
    0x2007: "IncompleteTransfer",
    0x2008: "InvalidStorageID",
    0x2009: "InvalidObjectHandle",
    0x200A: "DevicePropNotSupported",
    0x200B: "InvalidObjectFormatCode",
    0x200C: "StoreFull",
    0x200D: "ObjectWriteProtected",
    0x200E: "StoreReadOnly",
    0x200F: "AccessDenied",
    0x2010: "NoThumbnailPresent",
    0x2011: "SelfTestFailed",
    0x2012: "PartialDeletion",
    0x2013: "StoreNotAvailable",
    0x2014: "SpecificationByFormatUnsupported",
    0x2015: "NoValidObjectInfo",
    0x2016: "InvalidCodeFormat",
    0x2017: "UnknownVendorCode",
    0x2018: "CaptureAlreadyTerminated",
    0x2019: "DeviceBusy",
    0x201A: "InvalidParentObject",
    0x201B: "InvalidDevicePropFormat",
    0x201C: "InvalidDevicePropValue",
    0x201D: "InvalidParameter",
    0x201E: "SessionAlreadyOpen",
    0x201F: "TransactionCancelled",
    0x2020: "SpecificationOfDestinationUnsupported",
}
