"""Tests for the capmtp boundary harness.

These tests use a mock bulk pipe. They verify framing, safety gating, and plan
construction. They do not test a real console and cannot prove anything about
capmtp's robustness.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ptp_boundary", ROOT / "scripts" / "ptp_boundary.py"
)
assert SPEC and SPEC.loader
ptp_boundary = importlib.util.module_from_spec(SPEC)
sys.modules["ptp_boundary"] = ptp_boundary
SPEC.loader.exec_module(ptp_boundary)

from switch_usb_probe.ptp import (  # noqa: E402
    PTP_RC_OK,
    encode_data,
    encode_response,
)


class MockPipe:
    """A bulk pipe that replays a fixed byte stream."""

    def __init__(self, stream: bytes) -> None:
        self.stream = stream
        self.offset = 0
        self.writes: list[bytes] = []

    def write(self, data: bytes, timeout_ms: int) -> int:
        self.writes.append(data)
        return len(data)

    def read(self, size: int, timeout_ms: int) -> bytes:
        if self.offset >= len(self.stream):
            return b""
        chunk = self.stream[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        return None


def response_stream(
    transaction_id: int,
    payload: bytes = b"",
    *,
    code: int = PTP_RC_OK,
    params: tuple[int, ...] = (),
) -> bytes:
    data = encode_data(transaction_id, 0x1009, payload) if payload else b""
    return data + encode_response(code, transaction_id, params)


class PlanTests(unittest.TestCase):
    def test_object_plan_covers_boundaries(self) -> None:
        cases = ptp_boundary.build_object_plan(handle=7, size=100)
        names = {case.name for case in cases}
        self.assertIn("read_last_byte", names)
        self.assertIn("read_at_size", names)
        self.assertIn("read_past_size", names)
        offsets = {
            case.params[1]
            for case in cases
            if case.name.startswith("read_") and len(case.params) == 3
        }
        self.assertIn(99, offsets)
        self.assertIn(100, offsets)
        self.assertIn(101, offsets)
        self.assertIn(0x80000000, offsets)
        self.assertIn(0xFFFFFFFF, offsets)

    def test_object_plan_without_size_skips_size_cases(self) -> None:
        cases = ptp_boundary.build_object_plan(handle=7, size=None)
        names = {case.name for case in cases}
        self.assertNotIn("read_at_size", names)
        self.assertIn("read_offset_uint_max", names)

    def test_handles_plan_covers_invalid_ids(self) -> None:
        cases = ptp_boundary.build_handles_plan()
        handles = {
            case.params[0]
            for case in cases
            if case.code == ptp_boundary.PTP_OC_GET_OBJECT_INFO
        }
        self.assertIn(0, handles)
        self.assertIn(0x7FFFFFFF, handles)
        self.assertIn(0x80000000, handles)
        self.assertIn(0xFFFFFFFF, handles)

    def test_every_planned_operation_is_read_only(self) -> None:
        cases = ptp_boundary.build_object_plan(1, 10) + ptp_boundary.build_handles_plan()
        for case in cases:
            self.assertIn(case.code, ptp_boundary.READ_ONLY_OPS, case.name)


class ClientTests(unittest.TestCase):
    def test_refuses_non_read_operation(self) -> None:
        client = ptp_boundary.BoundaryClient(MockPipe(b""), timeout_ms=50)
        with self.assertRaises(Exception):
            client.command(0x100B)  # DeleteObject

    def test_parses_data_and_response(self) -> None:
        pipe = MockPipe(response_stream(1, b"abcd", params=(0x1234,)))
        client = ptp_boundary.BoundaryClient(pipe, timeout_ms=50)
        code, params, payload = client.command(0x1009, (7, 0, 16))
        self.assertEqual(code, PTP_RC_OK)
        self.assertEqual(params, (0x1234,))
        self.assertEqual(payload, b"abcd")
        self.assertEqual(len(pipe.writes), 1)

    def test_empty_read_is_a_timeout(self) -> None:
        client = ptp_boundary.BoundaryClient(MockPipe(b""), timeout_ms=50)
        with self.assertRaises(ptp_boundary.OperationTimeout):
            client.command(0x1008, (1,))

    def test_run_stops_after_timeout(self) -> None:
        cases = [
            ptp_boundary.Case("first", 0x1008, (1,), "times out"),
            ptp_boundary.Case("second", 0x1008, (2,), "must not run"),
        ]
        client = ptp_boundary.BoundaryClient(MockPipe(b""), timeout_ms=50)
        observations = ptp_boundary.run_cases(client, cases)
        self.assertEqual(len(observations), 1)
        self.assertTrue(observations[0].error.startswith("timeout"))

    def test_object_info_size(self) -> None:
        dataset = bytes(8) + (0xDEADBEEF).to_bytes(4, "little") + bytes(4)
        self.assertEqual(ptp_boundary.object_info_size(dataset), 0xDEADBEEF)
        self.assertIsNone(ptp_boundary.object_info_size(b"short"))


class SelectionTests(unittest.TestCase):
    """The active path must classify raw UsbDevice records, not tuples."""

    def _with_devices(self, devices):
        from switch_usb_probe.models import EnumerationResult

        original = ptp_boundary.enumerate_usb_devices
        ptp_boundary.enumerate_usb_devices = (
            lambda **kwargs: EnumerationResult(devices=tuple(devices))
        )
        return original

    def test_selects_a_ptp_console(self) -> None:
        from switch_usb_probe.models import UsbDevice

        original = self._with_devices(
            [UsbDevice(vendor_id=0x057E, product_id=0x201D, name="Nintendo Switch")]
        )
        try:
            device = ptp_boundary._select_device("auto", 0.5)
        finally:
            ptp_boundary.enumerate_usb_devices = original
        self.assertEqual(device.vid_pid, "057e:201d")

    def test_rejects_when_no_ptp_device_exists(self) -> None:
        original = self._with_devices([])
        try:
            with self.assertRaises(ptp_boundary.ProbeError):
                ptp_boundary._select_device("auto", 0.5)
        finally:
            ptp_boundary.enumerate_usb_devices = original

    def test_prefers_the_oled_over_a_switch2(self) -> None:
        from switch_usb_probe.models import UsbDevice

        original = self._with_devices(
            [
                UsbDevice(vendor_id=0x057E, product_id=0x2061),
                UsbDevice(vendor_id=0x057E, product_id=0x201D),
            ]
        )
        try:
            device = ptp_boundary._select_device("auto", 0.5)
        finally:
            ptp_boundary.enumerate_usb_devices = original
        self.assertEqual(device.vid_pid, "057e:201d")

    def test_refuses_to_guess_between_two_consoles(self) -> None:
        from switch_usb_probe.models import UsbDevice

        original = self._with_devices(
            [
                UsbDevice(vendor_id=0x057E, product_id=0x201D),
                UsbDevice(vendor_id=0x057E, product_id=0x201D),
            ]
        )
        try:
            with self.assertRaises(ptp_boundary.ProbeError):
                ptp_boundary._select_device("auto", 0.5)
        finally:
            ptp_boundary.enumerate_usb_devices = original


class DryRunTests(unittest.TestCase):
    def test_dry_run_does_not_touch_the_device(self) -> None:
        original = ptp_boundary._select_device

        def explode(*args, **kwargs):
            raise AssertionError("dry run must not enumerate devices")

        ptp_boundary._select_device = explode
        try:
            self.assertEqual(ptp_boundary.main(["--family", "handles"]), 0)
        finally:
            ptp_boundary._select_device = original


if __name__ == "__main__":
    unittest.main()


class FakeClient:
    """Minimal command router for discovery tests."""

    def __init__(self, routes):
        self.routes = routes

    def command(self, code, params=(), *, transaction_id=None):
        key = (code, tuple(params))
        if key not in self.routes:
            raise AssertionError(f"unexpected command {key}")
        return self.routes[key]


def u32_array(*values: int) -> bytes:
    return len(values).to_bytes(4, "little") + b"".join(
        v.to_bytes(4, "little") for v in values
    )


def object_info(size: int) -> bytes:
    return bytes(8) + size.to_bytes(4, "little") + bytes(76)


class DiscoveryTests(unittest.TestCase):
    def test_discovers_a_non_empty_child(self) -> None:
        routes = {
            (0x1004, ()): (0x2001, (), u32_array(0x60001)),
            (0x1007, (0x60001, 0, 0xFFFFFFFF)): (0x2001, (), u32_array(0x2AE, 0x2B0)),
            (0x1007, (0x60001, 0, 0x2AE)): (0x2001, (), u32_array(0x2AF)),
            (0x1008, (0x2AF,)): (0x2001, (), object_info(1234)),
        }
        handle, size = ptp_boundary.discover_target(FakeClient(routes))
        self.assertEqual(handle, 0x2AF)
        self.assertEqual(size, 1234)

    def test_skips_empty_objects_and_folder_failures(self) -> None:
        routes = {
            (0x1004, ()): (0x2001, (), u32_array(0x60001)),
            (0x1007, (0x60001, 0, 0xFFFFFFFF)): (0x2001, (), u32_array(0x2AE, 0x2B0)),
            (0x1007, (0x60001, 0, 0x2AE)): (0x2001, (), u32_array(0x2AF)),
            (0x1008, (0x2AF,)): (0x2001, (), object_info(0)),
            (0x1007, (0x60001, 0, 0x2B0)): (0x2001, (), u32_array(0x2B1)),
            (0x1008, (0x2B1,)): (0x2001, (), object_info(200377)),
        }
        handle, size = ptp_boundary.discover_target(FakeClient(routes))
        self.assertEqual(handle, 0x2B1)
        self.assertEqual(size, 200377)

    def test_raises_when_the_album_is_empty(self) -> None:
        routes = {
            (0x1004, ()): (0x2001, (), u32_array(0x60001)),
            (0x1007, (0x60001, 0, 0xFFFFFFFF)): (0x2001, (), u32_array()),
        }
        with self.assertRaises(ptp_boundary.ProbeError):
            ptp_boundary.discover_target(FakeClient(routes))
