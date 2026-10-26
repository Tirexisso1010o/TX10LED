"""Minimal read-only PTP client and optional pyusb transport.

Only the documented identity query is implemented.  There is no object
transfer, storage mutation, property write, or payload operation in this
module.
"""

from __future__ import annotations

import errno
import struct
from dataclasses import dataclass
from typing import Any, Protocol

from .errors import (
    DependencyMissing,
    DeviceAccessError,
    DeviceBusyError,
    NoDeviceError,
    OperationTimeout,
    ProbeError,
    PtpProtocolError,
    PtpResponseError,
    PtpSessionRequired,
    UnsupportedModeError,
)
from .log import JsonlLogger
from .redact import redact_serial

PTP_CONTAINER_COMMAND = 1
PTP_CONTAINER_DATA = 2
PTP_CONTAINER_RESPONSE = 3
PTP_CONTAINER_EVENT = 4

PTP_OC_GET_DEVICE_INFO = 0x1001
PTP_OC_OPEN_SESSION = 0x1002
PTP_OC_CLOSE_SESSION = 0x1003

PTP_RC_OK = 0x2001
PTP_RC_SESSION_NOT_OPEN = 0x2003
PTP_RC_SESSION_ALREADY_OPEN = 0x201E

MAX_CONTAINER_SIZE = 16 * 1024 * 1024
MAX_ARRAY_COUNT = 4096
MAX_STRING_CHARS = 4096
MAX_CONTAINERS_PER_COMMAND = 16


@dataclass(frozen=True)
class PtpContainerHeader:
    length: int
    container_type: int
    code: int
    transaction_id: int


def encode_command(
    code: int,
    transaction_id: int,
    params: tuple[int, ...] = (),
) -> bytes:
    length = 12 + 4 * len(params)
    header = struct.pack("<IHHI", length, PTP_CONTAINER_COMMAND, code, transaction_id)
    body = b"".join(struct.pack("<I", param) for param in params)
    return header + body


def encode_data(transaction_id: int, code: int, payload: bytes) -> bytes:
    length = 12 + len(payload)
    return struct.pack("<IHHI", length, PTP_CONTAINER_DATA, code, transaction_id) + payload


def encode_response(code: int, transaction_id: int, params: tuple[int, ...] = ()) -> bytes:
    length = 12 + 4 * len(params)
    header = struct.pack("<IHHI", length, PTP_CONTAINER_RESPONSE, code, transaction_id)
    body = b"".join(struct.pack("<I", param) for param in params)
    return header + body


def parse_container_header(data: bytes) -> PtpContainerHeader:
    if len(data) < 12:
        raise PtpProtocolError(
            f"PTP container header is too short: {len(data)} bytes",
        )
    length, container_type, code, transaction_id = struct.unpack_from("<IHHI", data, 0)
    if length < 12:
        raise PtpProtocolError(f"invalid PTP container length: {length}")
    if length > MAX_CONTAINER_SIZE:
        raise PtpProtocolError(f"PTP container is too large: {length} bytes")
    if container_type not in {
        PTP_CONTAINER_COMMAND,
        PTP_CONTAINER_DATA,
        PTP_CONTAINER_RESPONSE,
        PTP_CONTAINER_EVENT,
    }:
        raise PtpProtocolError(f"unknown PTP container type: {container_type}")
    return PtpContainerHeader(
        length=length,
        container_type=container_type,
        code=code,
        transaction_id=transaction_id,
    )


def _sanitize_text(value: str, *, limit: int = 512) -> str:
    printable = "".join(
        char if (char.isprintable() or char == "\t") else " " for char in value
    )
    return " ".join(printable.split())[:limit]


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    @property
    def remaining(self) -> int:
        return len(self.data) - self.offset

    def take(self, size: int) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise PtpProtocolError(
                f"DeviceInfo is truncated at offset {self.offset} (need {size} bytes)",
            )
        chunk = self.data[self.offset : self.offset + size]
        self.offset += size
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def string(self) -> str:
        length = self.u8()
        if length == 0:
            return ""
        if length > MAX_STRING_CHARS:
            raise PtpProtocolError(f"PTP string is too long: {length} characters")
        raw = self.take(length * 2)
        text = raw.decode("utf-16-le", errors="replace").rstrip("\x00")
        return _sanitize_text(text)

    def array_u16(self) -> tuple[int, ...]:
        count = self.u32()
        if count > MAX_ARRAY_COUNT:
            raise PtpProtocolError(f"PTP array is too long: {count} entries")
        return tuple(self.u16() for _ in range(count))


@dataclass(frozen=True)
class PtpDeviceInfo:
    standard_version: int
    vendor_extension_id: int
    vendor_extension_version: int
    vendor_extension_description: str
    functional_mode: int
    operations_supported: tuple[int, ...]
    events_supported: tuple[int, ...]
    device_properties_supported: tuple[int, ...]
    capture_formats: tuple[int, ...]
    image_formats: tuple[int, ...]
    manufacturer: str
    model: str
    device_version: str
    serial_number: str
    trailing_bytes: int = 0

    def to_dict(self, *, prefix_len: int = 3) -> dict[str, Any]:
        return {
            "standard_version": f"0x{self.standard_version:04x}",
            "vendor_extension_id": f"0x{self.vendor_extension_id:08x}",
            "vendor_extension_version": f"0x{self.vendor_extension_version:04x}",
            "vendor_extension_description": self.vendor_extension_description,
            "functional_mode": f"0x{self.functional_mode:04x}",
            "operations_count": len(self.operations_supported),
            "operations_supported": [
                f"0x{code:04x}" for code in self.operations_supported
            ],
            "events_count": len(self.events_supported),
            "device_properties_count": len(self.device_properties_supported),
            "capture_formats_count": len(self.capture_formats),
            "image_formats_count": len(self.image_formats),
            "manufacturer": self.manufacturer,
            "model": self.model,
            "device_version": self.device_version,
            "serial_prefix": redact_serial(self.serial_number, prefix_len=prefix_len),
            "serial_redacted": True,
            "trailing_bytes": self.trailing_bytes,
        }


def parse_device_info(data: bytes) -> PtpDeviceInfo:
    """Parse a PTP DeviceInfo dataset with bounds checks."""

    reader = _Reader(data)
    standard_version = reader.u16()
    vendor_extension_id = reader.u32()
    vendor_extension_version = reader.u16()
    vendor_extension_description = reader.string()
    functional_mode = reader.u16()
    operations_supported = reader.array_u16()
    events_supported = reader.array_u16()
    device_properties_supported = reader.array_u16()
    capture_formats = reader.array_u16()
    image_formats = reader.array_u16()
    manufacturer = reader.string()
    model = reader.string()
    device_version = reader.string()
    serial_number = reader.string()
    return PtpDeviceInfo(
        standard_version=standard_version,
        vendor_extension_id=vendor_extension_id,
        vendor_extension_version=vendor_extension_version,
        vendor_extension_description=vendor_extension_description,
        functional_mode=functional_mode,
        operations_supported=operations_supported,
        events_supported=events_supported,
        device_properties_supported=device_properties_supported,
        capture_formats=capture_formats,
        image_formats=image_formats,
        manufacturer=manufacturer,
        model=model,
        device_version=device_version,
        serial_number=serial_number,
        trailing_bytes=reader.remaining,
    )


class BulkPipe(Protocol):
    def write(self, data: bytes, timeout_ms: int) -> int:
        ...

    def read(self, size: int, timeout_ms: int) -> bytes:
        ...

    def close(self) -> None:
        ...


class PtpClient:
    """Transaction-level PTP client for read-only identity queries."""

    def __init__(
        self,
        pipe: BulkPipe,
        *,
        timeout_ms: int = 2000,
        allow_session: bool = False,
        logger: JsonlLogger | None = None,
        transaction_id_start: int = 1,
    ) -> None:
        if timeout_ms <= 0:
            raise UnsupportedModeError("PTP timeout must be greater than zero")
        self.pipe = pipe
        self.timeout_ms = timeout_ms
        self.allow_session = allow_session
        self.logger = logger
        self._transaction_id = transaction_id_start
        self.session_opened = False

    def _next_transaction_id(self) -> int:
        current = self._transaction_id
        self._transaction_id = (self._transaction_id % 0xFFFFFFFF) + 1
        return current

    def _read_exact(self, size: int) -> bytes:
        if size == 0:
            return b""
        chunks = bytearray()
        attempts = 0
        while len(chunks) < size:
            attempts += 1
            if attempts > 1024:
                raise PtpProtocolError("PTP read made no progress")
            chunk = self.pipe.read(size - len(chunks), self.timeout_ms)
            if not chunk:
                raise OperationTimeout(
                    "PTP read returned no data",
                    hint="The device may have stopped responding. Disconnect and retry once.",
                )
            chunks.extend(chunk)
        return bytes(chunks)

    def _read_container(self) -> tuple[PtpContainerHeader, bytes]:
        header_bytes = self._read_exact(12)
        header = parse_container_header(header_bytes)
        body = self._read_exact(header.length - 12)
        return header, body

    def _command(self, code: int, params: tuple[int, ...] = ()) -> bytes:
        transaction_id = self._next_transaction_id()
        command = encode_command(code, transaction_id, params)
        self.pipe.write(command, self.timeout_ms)
        payload = bytearray()
        for _ in range(MAX_CONTAINERS_PER_COMMAND):
            header, body = self._read_container()
            if header.container_type == PTP_CONTAINER_EVENT:
                # Events are not part of the read-only identity flow.  They can
                # carry their own transaction ID; ignore them.
                continue
            if header.transaction_id != transaction_id:
                raise PtpProtocolError(
                    "PTP transaction ID mismatch: "
                    f"expected {transaction_id}, got {header.transaction_id}"
                )
            if header.container_type == PTP_CONTAINER_DATA:
                payload.extend(body)
                if len(payload) > MAX_CONTAINER_SIZE:
                    raise PtpProtocolError("PTP data phase is too large")
                continue
            if header.container_type == PTP_CONTAINER_RESPONSE:
                if header.code != PTP_RC_OK:
                    raise PtpResponseError(header.code, operation=code)
                return bytes(payload)
            raise PtpProtocolError(
                f"unexpected PTP container type during command: {header.container_type}"
            )
        raise PtpProtocolError("too many PTP containers without a response")

    def _open_session(self) -> None:
        try:
            self._command(PTP_OC_OPEN_SESSION, (1,))
        except PtpResponseError as exc:
            if exc.code == PTP_RC_SESSION_ALREADY_OPEN:
                # Another client owns the session.  Do not close it on the way
                # out, because this client did not open it.
                if self.logger:
                    self.logger.warning("ptp_session_already_open")
                self.session_opened = False
                return
            raise
        self.session_opened = True

    def get_device_info(self) -> PtpDeviceInfo:
        try:
            payload = self._command(PTP_OC_GET_DEVICE_INFO)
        except PtpResponseError as exc:
            if exc.code != PTP_RC_SESSION_NOT_OPEN:
                raise
            if not self.allow_session:
                raise PtpSessionRequired(
                    "the device requires OpenSession before GetDeviceInfo",
                    hint=(
                        "Re-run with --allow-session to send OpenSession, "
                        "GetDeviceInfo, and CloseSession only."
                    ),
                ) from exc
            self._open_session()
            payload = self._command(PTP_OC_GET_DEVICE_INFO)
        return parse_device_info(payload)

    def close(self) -> None:
        if not self.session_opened:
            return
        try:
            self._command(PTP_OC_CLOSE_SESSION)
        except ProbeError as exc:
            if self.logger:
                self.logger.warning("ptp_close_session_failed", error=str(exc))
        finally:
            self.session_opened = False


def _import_usb() -> Any:
    try:
        import usb.core  # type: ignore[import-not-found]
        import usb.util  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DependencyMissing(
            "pyusb is not installed",
            hint=(
                "Create a repository-local virtual environment and install the "
                "optional dependency: python3 -m venv .venv && "
                ".venv/bin/python -m pip install -e '.[ptp]'"
            ),
        ) from exc
    return usb


def map_usb_error(exc: BaseException, *, usb_module: Any | None = None) -> ProbeError:
    """Translate a pyusb/libusb exception into a typed project error."""

    if isinstance(exc, ProbeError):
        return exc
    name = type(exc).__name__.lower()
    text = str(exc)
    lowered = text.lower()
    code = getattr(exc, "errno", None)
    if code is None and exc.args and isinstance(exc.args[0], int):
        code = exc.args[0]

    if "timeout" in name or code == errno.ETIMEDOUT or "timed out" in lowered:
        return OperationTimeout(
            f"USB operation timed out: {text}",
            hint="Disconnect and reconnect the device, then retry once.",
        )
    if "nobackend" in name or "no backend" in lowered:
        return DependencyMissing(
            "no libusb backend is available",
            hint=(
                "Install libusb in a way appropriate for this Mac and retry. "
                "Do not use sudo or install a privileged driver without approval."
            ),
        )
    if (
        code in {errno.EBUSY, errno.EAGAIN}
        or "busy" in lowered
        or "exclusive" in lowered
    ):
        return DeviceBusyError(
            f"USB device or interface is busy: {text}",
            hint=(
                "Close applications that may be using the PTP device. macOS "
                "ptpcamerad may hold the interface; this tool will not kill it. "
                "Do not disable SIP or use sudo as a workaround."
            ),
        )
    if (
        code in {errno.EACCES, errno.EPERM}
        or "access denied" in lowered
        or "permission" in lowered
        or "not permitted" in lowered
    ):
        return DeviceAccessError(
            f"USB access was denied: {text}",
            hint="Check the device claim and macOS permissions. Do not use sudo.",
        )
    if (
        code == errno.ENODEV
        or "no such device" in lowered
        or "device disconnected" in lowered
        or "not found" in lowered
    ):
        return NoDeviceError(f"USB device is no longer present: {text}")
    return DeviceAccessError(f"USB operation failed: {text}")


class UsbPtpTransport:
    """pyusb-backed bulk transport for a PTP interface."""

    def __init__(
        self,
        device: Any,
        *,
        timeout_ms: int = 2000,
        usb_module: Any | None = None,
    ) -> None:
        self.usb = usb_module or _import_usb()
        self.device = device
        self.timeout_ms = timeout_ms
        self.interface_number: int | None = None
        self.ep_in: Any = None
        self.ep_out: Any = None
        self._claimed = False

    @classmethod
    def open(
        cls,
        vendor_id: int,
        product_id: int,
        *,
        bus: int | None = None,
        address: int | None = None,
        timeout_ms: int = 2000,
        usb_module: Any | None = None,
    ) -> "UsbPtpTransport":
        usb = usb_module or _import_usb()
        search: dict[str, int] = {
            "idVendor": vendor_id,
            "idProduct": product_id,
        }
        if bus is not None:
            search["bus"] = bus
        if address is not None:
            search["address"] = address
        try:
            device = usb.core.find(**search)
        except Exception as exc:
            raise map_usb_error(exc, usb_module=usb) from exc
        if device is None:
            raise NoDeviceError(
                f"no USB device found for {vendor_id:04x}:{product_id:04x}",
                hint="Check the cable, the console screen, and the selected USB mode.",
            )
        transport = cls(device, timeout_ms=timeout_ms, usb_module=usb)
        transport._configure_and_claim()
        return transport

    def _get_configuration(self) -> Any:
        usb = self.usb
        try:
            return self.device.get_active_configuration()
        except Exception as first_exc:
            try:
                self.device.set_configuration()
                return self.device.get_active_configuration()
            except Exception as exc:
                raise map_usb_error(exc, usb_module=usb) from first_exc

    def _configure_and_claim(self) -> None:
        usb = self.usb
        configuration = self._get_configuration()
        interface = None
        for candidate in configuration:
            if (
                candidate.bInterfaceClass == 0x06
                and candidate.bInterfaceSubClass == 0x01
                and candidate.bInterfaceProtocol == 0x01
            ):
                interface = candidate
                break
        if interface is None:
            raise UnsupportedModeError(
                "the device has no PTP still-image interface (class 06/01/01)",
                hint="The device may be in a different USB mode; use `list` to classify it.",
            )

        ep_in = usb.util.find_descriptor(
            interface,
            custom_match=lambda endpoint: (
                usb.util.endpoint_direction(endpoint.bEndpointAddress)
                == usb.util.ENDPOINT_IN
                and usb.util.endpoint_type(endpoint.bmAttributes)
                == usb.util.ENDPOINT_TYPE_BULK
            ),
        )
        ep_out = usb.util.find_descriptor(
            interface,
            custom_match=lambda endpoint: (
                usb.util.endpoint_direction(endpoint.bEndpointAddress)
                == usb.util.ENDPOINT_OUT
                and usb.util.endpoint_type(endpoint.bmAttributes)
                == usb.util.ENDPOINT_TYPE_BULK
            ),
        )
        if ep_in is None or ep_out is None:
            raise UnsupportedModeError(
                "the PTP interface is missing a bulk IN or bulk OUT endpoint",
            )

        try:
            usb.util.claim_interface(self.device, interface.bInterfaceNumber)
        except Exception as exc:
            raise map_usb_error(exc, usb_module=usb) from exc

        self.interface_number = interface.bInterfaceNumber
        self.ep_in = ep_in
        self.ep_out = ep_out
        self._claimed = True

    def write(self, data: bytes, timeout_ms: int) -> int:
        try:
            written = self.ep_out.write(data, timeout=timeout_ms)
        except Exception as exc:
            raise map_usb_error(exc, usb_module=self.usb) from exc
        if written != len(data):
            raise PtpProtocolError(
                f"short USB write: {written} of {len(data)} bytes",
            )
        return int(written)

    def read(self, size: int, timeout_ms: int) -> bytes:
        try:
            data = self.ep_in.read(size, timeout=timeout_ms)
        except Exception as exc:
            raise map_usb_error(exc, usb_module=self.usb) from exc
        return bytes(data)

    def describe(self) -> dict[str, Any]:
        return {
            "interface_number": self.interface_number,
            "in_endpoint": (
                f"0x{self.ep_in.bEndpointAddress:02x}" if self.ep_in else None
            ),
            "out_endpoint": (
                f"0x{self.ep_out.bEndpointAddress:02x}" if self.ep_out else None
            ),
            "claimed": self._claimed,
        }

    def close(self) -> None:
        usb = self.usb
        if self._claimed and self.interface_number is not None:
            try:
                usb.util.release_interface(self.device, self.interface_number)
            except Exception:
                pass
            self._claimed = False
        try:
            usb.util.dispose_resources(self.device)
        except Exception:
            pass

    def __enter__(self) -> "UsbPtpTransport":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
