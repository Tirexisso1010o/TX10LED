#!/usr/bin/env python3
"""Boundary-parameter experiment harness for the capmtp PTP surface.

This is a research tool, not part of the read-only `switch-usb-probe` CLI. It
sends only PTP read operations, but it deliberately sends boundary values that a
normal client would not, so it is gated twice:

* the default is a dry run that opens no device;
* sending requires both ``--confirm`` and ``--active``.

Hypotheses H-001 and H-002 in ``research/hypotheses.json`` describe what this
harness is trying to falsify. A run that produces only documented errors is a
negative result and must be recorded as such.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switch_usb_probe.classify import classify_device  # noqa: E402
from switch_usb_probe.enumeration import enumerate_usb_devices  # noqa: E402
from switch_usb_probe.errors import (  # noqa: E402
    OperationTimeout,
    ProbeError,
    PtpProtocolError,
    PtpResponseError,
)
from switch_usb_probe.ptp import (  # noqa: E402
    PTP_CONTAINER_DATA,
    PTP_CONTAINER_EVENT,
    PTP_CONTAINER_RESPONSE,
    PTP_RC_OK,
    PTP_RC_SESSION_ALREADY_OPEN,
    MAX_CONTAINER_SIZE,
    encode_command,
    parse_container_header,
    UsbPtpTransport,
)

PTP_OC_GET_STORAGE_IDS = 0x1004
PTP_OC_GET_STORAGE_INFO = 0x1005
PTP_OC_GET_OBJECT_HANDLES = 0x1007
PTP_OC_GET_OBJECT_INFO = 0x1008
PTP_OC_GET_OBJECT = 0x1009
PTP_OC_OPEN_SESSION = 0x1002
PTP_OC_CLOSE_SESSION = 0x1003

# Read-only operations this harness is permitted to emit.
READ_ONLY_OPS = frozenset(
    {
        PTP_OC_GET_STORAGE_IDS,
        PTP_OC_GET_STORAGE_INFO,
        PTP_OC_GET_OBJECT_HANDLES,
        PTP_OC_GET_OBJECT_INFO,
        PTP_OC_GET_OBJECT,
        PTP_OC_OPEN_SESSION,
        PTP_OC_CLOSE_SESSION,
    }
)

MAX_DATA_BYTES = 2 * 1024 * 1024
MAX_READ_BYTES = 0x00100000


@dataclass(frozen=True)
class Case:
    """One planned PTP transaction."""

    name: str
    code: int
    params: tuple[int, ...]
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "code": f"0x{self.code:04x}",
            "params": [f"0x{value:08x}" for value in self.params],
            "rationale": self.rationale,
        }


@dataclass
class Observation:
    """Outcome of one transaction, including failures."""

    name: str
    code: int
    response_code: int | None = None
    response_params: tuple[int, ...] = ()
    data_len: int = 0
    elapsed_ms: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.response_code == PTP_RC_OK

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "code": f"0x{self.code:04x}",
            "response_code": (
                None if self.response_code is None else f"0x{self.response_code:04x}"
            ),
            "response_params": [f"0x{value:08x}" for value in self.response_params],
            "data_len": self.data_len,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
        }


class BoundaryClient:
    """Minimal PTP transaction client that refuses non-read operations."""

    def __init__(self, pipe: object, *, timeout_ms: int = 2000) -> None:
        self.pipe = pipe
        self.timeout_ms = timeout_ms
        self._transaction_id = 1
        self.session_opened = False

    def _next_transaction_id(self) -> int:
        current = self._transaction_id
        self._transaction_id = (self._transaction_id % 0xFFFFFFFF) + 1
        return current

    def _read_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.pipe.read(size - len(chunks), self.timeout_ms)  # type: ignore[attr-defined]
            if not chunk:
                raise OperationTimeout(
                    "PTP read returned no data",
                    hint="The console may have stopped responding. Stop the run.",
                )
            chunks.extend(chunk)
        return bytes(chunks)

    def command(
        self, code: int, params: Sequence[int] = ()
    ) -> tuple[int, tuple[int, ...], bytes]:
        if code not in READ_ONLY_OPS:
            raise PtpProtocolError(
                f"refusing to send non-read-only PTP operation 0x{code:04x}"
            )
        transaction_id = self._next_transaction_id()
        self.pipe.write(  # type: ignore[attr-defined]
            encode_command(code, transaction_id, tuple(params)),
            self.timeout_ms,
        )
        payload = bytearray()
        response_params: tuple[int, ...] = ()
        for _ in range(16):
            header, body = self._read_container()
            if header.container_type == PTP_CONTAINER_EVENT:
                continue
            if header.transaction_id != transaction_id:
                raise PtpProtocolError(
                    "PTP transaction ID mismatch: "
                    f"expected {transaction_id}, got {header.transaction_id}"
                )
            if header.container_type == PTP_CONTAINER_DATA:
                payload.extend(body)
                if len(payload) > MAX_DATA_BYTES:
                    raise PtpProtocolError("PTP data phase exceeded the safety cap")
                continue
            if header.container_type == PTP_CONTAINER_RESPONSE:
                response_params = struct.unpack_from(
                    f"<{len(body) // 4}I", body, 0
                ) if len(body) >= 4 else ()
                if header.code != PTP_RC_OK:
                    raise PtpResponseError(header.code, operation=code)
                return header.code, response_params, bytes(payload)
            raise PtpProtocolError(
                f"unexpected PTP container type: {header.container_type}"
            )
        raise PtpProtocolError("too many PTP containers without a response")

    def _read_container(self) -> tuple[object, bytes]:
        header_bytes = self._read_exact(12)
        header = parse_container_header(header_bytes)
        if header.length > MAX_CONTAINER_SIZE:
            raise PtpProtocolError("PTP container exceeded the safety cap")
        body = self._read_exact(header.length - 12)
        return header, body

    def open_session(self) -> None:
        try:
            self.command(PTP_OC_OPEN_SESSION, (1,))
        except PtpResponseError as exc:
            if exc.code == PTP_RC_SESSION_ALREADY_OPEN:
                self.session_opened = False
                return
            raise
        self.session_opened = True

    def close(self) -> None:
        if not self.session_opened:
            return
        try:
            self.command(PTP_OC_CLOSE_SESSION)
        finally:
            self.session_opened = False


def object_info_size(payload: bytes) -> int | None:
    """Return ObjectCompressedSize from a PTP ObjectInfo dataset."""

    if len(payload) < 12:
        return None
    return struct.unpack_from("<I", payload, 8)[0]


def build_handles_plan() -> list[Case]:
    """Boundary identifiers for handle-table lookups (H-002)."""

    return [
        Case(
            "storage_ids",
            PTP_OC_GET_STORAGE_IDS,
            (),
            "Baseline: enumerate logical storages before touching handles.",
        ),
        Case(
            "handles_invalid_storage",
            PTP_OC_GET_OBJECT_HANDLES,
            (0xFFFFFFFF, 0, 0),
            "Invalid storage ID; checks whether the ID is validated.",
        ),
        Case(
            "handles_invalid_format",
            PTP_OC_GET_OBJECT_HANDLES,
            (0xFFFFFFFF, 0xFFFFFFFF, 0),
            "Invalid object format filter.",
        ),
        Case(
            "handles_invalid_parent",
            PTP_OC_GET_OBJECT_HANDLES,
            (0xFFFFFFFF, 0, 0xFFFFFFFF),
            "Invalid parent handle.",
        ),
        Case(
            "info_zero",
            PTP_OC_GET_OBJECT_INFO,
            (0,),
            "Handle 0 is normally reserved; checks for off-by-one indexing.",
        ),
        Case(
            "info_one",
            PTP_OC_GET_OBJECT_INFO,
            (1,),
            "Small handle that may or may not correspond to an object.",
        ),
        Case(
            "info_int_max",
            PTP_OC_GET_OBJECT_INFO,
            (0x7FFFFFFF,),
            "Largest signed handle.",
        ),
        Case(
            "info_sign_bit",
            PTP_OC_GET_OBJECT_INFO,
            (0x80000000,),
            "Sets the sign bit; catches signed/unsigned confusion.",
        ),
        Case(
            "info_uint_max",
            PTP_OC_GET_OBJECT_INFO,
            (0xFFFFFFFF,),
            "Largest unsigned handle.",
        ),
    ]


def build_object_plan(handle: int, size: int | None) -> list[Case]:
    """Boundary offsets and lengths for object reads (H-001)."""

    cases = [
        Case(
            "info_baseline",
            PTP_OC_GET_OBJECT_INFO,
            (handle,),
            "Baseline metadata for the selected object.",
        ),
        Case(
            "read_zero_length",
            PTP_OC_GET_OBJECT,
            (handle, 0, 0),
            "Zero-length read; checks the empty-read path.",
        ),
        Case(
            "read_head",
            PTP_OC_GET_OBJECT,
            (handle, 0, 0x1000),
            "Baseline read of the first 4 KiB.",
        ),
    ]
    if size is not None and size > 0:
        cases.extend(
            [
                Case(
                    "read_last_byte",
                    PTP_OC_GET_OBJECT,
                    (handle, size - 1, 0x1000),
                    "Offset at the last valid byte.",
                ),
                Case(
                    "read_at_size",
                    PTP_OC_GET_OBJECT,
                    (handle, size, 0x1000),
                    "Offset exactly at the end; should yield zero bytes or an error.",
                ),
                Case(
                    "read_past_size",
                    PTP_OC_GET_OBJECT,
                    (handle, size + 1, 0x1000),
                    "One byte past the end; checks bounds enforcement.",
                ),
            ]
        )
    cases.extend(
        [
            Case(
                "read_offset_int_max",
                PTP_OC_GET_OBJECT,
                (handle, 0x7FFFFFFF, 0x1000),
                "Largest signed offset.",
            ),
            Case(
                "read_offset_sign_bit",
                PTP_OC_GET_OBJECT,
                (handle, 0x80000000, 0x1000),
                "Sign-bit offset; catches signed/unsigned confusion.",
            ),
            Case(
                "read_offset_uint_max",
                PTP_OC_GET_OBJECT,
                (handle, 0xFFFFFFFF, 0x1000),
                "Largest unsigned offset.",
            ),
            Case(
                "read_length_large",
                PTP_OC_GET_OBJECT,
                (handle, 0, MAX_READ_BYTES),
                "Large length request. A true 0xFFFFFFFF length is not sent "
                "because it risks an unbounded transfer.",
            ),
        ]
    )
    return cases


def _u32_array(payload: bytes) -> tuple[int, ...]:
    if len(payload) < 4:
        return ()
    count = struct.unpack_from("<I", payload, 0)[0]
    available = (len(payload) - 4) // 4
    count = min(count, available)
    return struct.unpack_from(f"<{count}I", payload, 4) if count else ()


def discover_target(client: "BoundaryClient") -> tuple[int, int | None]:
    """Pick the first storage and object handle, and read its size.

    Returns ``(handle, size)``. Raises if the console advertises no objects.
    """

    _, _, storage_payload = client.command(PTP_OC_GET_STORAGE_IDS)
    storage_ids = _u32_array(storage_payload)
    if not storage_ids:
        raise ProbeError("the console advertised no PTP storages")
    storage = storage_ids[0]

    _, _, handles_payload = client.command(
        PTP_OC_GET_OBJECT_HANDLES, (storage, 0, 0)
    )
    handles = _u32_array(handles_payload)
    if not handles:
        raise ProbeError(
            "the storage advertised no objects",
            hint="Add at least one screenshot or video, then retry.",
        )
    handle = handles[0]

    size: int | None = None
    try:
        _, _, info_payload = client.command(PTP_OC_GET_OBJECT_INFO, (handle,))
        size = object_info_size(info_payload)
    except ProbeError:
        size = None
    return handle, size


def plan_to_dict(cases: Iterable[Case]) -> list[dict[str, object]]:
    return [case.to_dict() for case in cases]


def _select_device(source: str, timeout_s: float):
    result = enumerate_usb_devices(source=source, timeout_s=timeout_s)
    candidates = []
    for device in result.devices:
        classification = classify_device(device)
        if classification.mode.value in {"switch_ptp", "switch2_ptp"}:
            candidates.append((device, classification.mode.value))
    if not candidates:
        raise ProbeError(
            "no PTP-capable Switch device found",
            hint=(
                "Connect the console, open Settings > Data Management > "
                "Manage Screenshots and Videos > Copy to PC via USB, then retry."
            ),
        )
    preferred = [item for item in candidates if item[1] == "switch_ptp"]
    chosen = preferred or candidates
    if len(chosen) > 1:
        listed = ", ".join(device.vid_pid for device, _ in chosen)
        raise ProbeError(
            f"multiple PTP candidates found ({listed}); refusing to guess"
        )
    device, mode = chosen[0]
    if mode == "switch2_ptp":
        print(
            "warning: the selected device is a Switch 2, not the OLED target.",
            file=sys.stderr,
        )
    return device


def run_cases(client: BoundaryClient, cases: Sequence[Case]) -> list[Observation]:
    observations: list[Observation] = []
    for case in cases:
        started = time.monotonic()
        observation = Observation(name=case.name, code=case.code)
        try:
            code, params, payload = client.command(case.code, case.params)
            observation.response_code = code
            observation.response_params = params
            observation.data_len = len(payload)
        except OperationTimeout as exc:
            observation.error = f"timeout: {exc}"
        except PtpResponseError as exc:
            observation.response_code = exc.code
            observation.error = f"ptp error: {exc}"
        except ProbeError as exc:
            observation.error = f"transport error: {exc}"
        observation.elapsed_ms = int((time.monotonic() - started) * 1000)
        observations.append(observation)
        if observation.error and observation.error.startswith("timeout"):
            break
    return observations


def _print_plan(cases: Sequence[Case]) -> None:
    print("capmtp boundary plan (dry run)")
    print(f"Planned read-only transactions: {len(cases)}")
    for case in cases:
        params = ", ".join(f"0x{value:08x}" for value in case.params)
        print(f"  {case.name:22} op=0x{case.code:04x} params=[{params}]")
    print("\nNo device was opened and no USB request was sent.")
    print("On a real run the first storage and object handle are discovered first.")
    print("Sending requires --confirm --active, and an approved console state.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Boundary-parameter harness for the capmtp PTP surface.",
    )
    parser.add_argument(
        "--family",
        choices=("objects", "handles"),
        default="objects",
        help="Which hypothesis family to plan.",
    )
    parser.add_argument("--handle", type=lambda value: int(value, 0), default=None)
    parser.add_argument("--size", type=lambda value: int(value, 0), default=None)
    parser.add_argument(
        "--source", choices=("auto", "ioreg", "system_profiler"), default="auto"
    )
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--active", action="store_true")
    args = parser.parse_args(argv)

    if args.family == "handles":
        cases = build_handles_plan()
    else:
        cases = build_object_plan(args.handle or 0, args.size)

    if not (args.confirm and args.active):
        if args.json:
            print(json.dumps({"dry_run": True, "cases": plan_to_dict(cases)}, indent=2))
        else:
            _print_plan(cases)
        return 0

    device = _select_device(args.source, max(0.5, args.timeout))
    timeout_ms = max(100, int(args.timeout * 1000))
    transport = UsbPtpTransport.open(
        device.vendor_id, device.product_id, timeout_ms=timeout_ms
    )
    client = BoundaryClient(transport, timeout_ms=timeout_ms)
    try:
        client.open_session()
        if args.family == "objects" and args.handle is None:
            handle, size = discover_target(client)
            cases = build_object_plan(handle, size)
        observations = run_cases(client, cases)
    finally:
        try:
            client.close()
        finally:
            transport.close()

    payload = {
        "dry_run": False,
        "family": args.family,
        "cases": [observation.to_dict() for observation in observations],
        "limitations": [
            "Only read-only PTP operations were sent.",
            "A reachable timeout may indicate a capmtp crash or hang, not a vulnerability.",
            "No result here establishes code execution or exploitability.",
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for observation in observations:
            status = "OK" if observation.ok else (observation.error or "error")
            print(
                f"{observation.name:22} rc="
                f"{'-' if observation.response_code is None else f'0x{observation.response_code:04x}'}"
                f" data={observation.data_len}B {observation.elapsed_ms}ms {status}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
