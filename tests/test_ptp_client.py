"""Tests for the documented PTP client's session handling.

PTP requires OpenSession to carry transaction ID 0. The device rejects other
values with 0x2004 (InvalidTransactionID), which is what the target console
returned during the first boundary run.
"""

from __future__ import annotations

import struct
import unittest

from switch_usb_probe.ptp import (
    PTP_OC_OPEN_SESSION,
    PTP_RC_OK,
    PtpClient,
    encode_response,
)


class MockPipe:
    def __init__(self, stream: bytes) -> None:
        self.stream = stream
        self.offset = 0
        self.writes: list[bytes] = []

    def write(self, data: bytes, timeout_ms: int) -> int:
        self.writes.append(data)
        return len(data)

    def read(self, size: int, timeout_ms: int) -> bytes:
        chunk = self.stream[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        return None


def command_fields(data: bytes) -> tuple[int, int, int]:
    _, container_type, code, transaction_id = struct.unpack_from("<IHHI", data, 0)
    assert container_type == 1
    return code, transaction_id, len(data)


class SessionTests(unittest.TestCase):
    def test_open_session_uses_transaction_id_zero(self) -> None:
        pipe = MockPipe(encode_response(PTP_RC_OK, 0))
        client = PtpClient(pipe, timeout_ms=50)
        client._open_session()

        code, transaction_id, length = command_fields(pipe.writes[0])
        self.assertEqual(code, PTP_OC_OPEN_SESSION)
        self.assertEqual(transaction_id, 0)
        self.assertEqual(length, 16)  # header plus the session parameter
        self.assertTrue(client.session_opened)

    def test_session_counter_restarts_after_open(self) -> None:
        pipe = MockPipe(encode_response(PTP_RC_OK, 0))
        client = PtpClient(pipe, timeout_ms=50, transaction_id_start=9)
        client._open_session()
        self.assertEqual(client._transaction_id, 1)

    def test_close_uses_the_next_transaction_id(self) -> None:
        pipe = MockPipe(encode_response(PTP_RC_OK, 0) + encode_response(0x2001, 1))
        client = PtpClient(pipe, timeout_ms=50)
        client._open_session()
        client.close()
        code, transaction_id, _ = command_fields(pipe.writes[1])
        self.assertEqual(transaction_id, 1)
        self.assertFalse(client.session_opened)


if __name__ == "__main__":
    unittest.main()
