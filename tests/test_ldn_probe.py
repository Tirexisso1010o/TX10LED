"""Tests for the read-only LDN advertisement parser."""

from __future__ import annotations

import struct
import unittest
from pathlib import Path

from scripts.ldn_probe import (
    Advertisement,
    extract_advertisements,
    parse_authentication,
    parse_ldn_action,
    unique_advertisements,
)


TITLE_ID = 0x0100000000001000
SCENE_ID = 1
SSID = bytes.fromhex("00112233445566778899aabbccddeeff")


def advertisement_body(
    *,
    title_id: int = TITLE_ID,
    scene_id: int = SCENE_ID,
    ssid: bytes = SSID,
    version: int = 4,
    frame_format: int = 2,
    size: int = 0x500,
    nonce: bytes = b"\x01\x02\x03\x04",
) -> bytes:
    network_id = (
        title_id.to_bytes(8, "big")
        + b"\x00\x00"
        + scene_id.to_bytes(2, "big")
        + b"\x00" * 4
        + ssid
    )
    if frame_format in (1, 2):
        payload = b"\x00" * 32 + b"\x00" * size
    else:
        payload = b"\x00" * 16 + b"\x00" * size
    body = (
        b"\x7f"
        + b"\x00\x22\xaa"
        + b"\x04"
        + b"\x00"
        + b"\x01\x01"
        + b"\x00" * 4
        + network_id
        + bytes([version, frame_format])
        + size.to_bytes(2, "big")
        + nonce
        + payload
    )
    return body


def pcap_with_action(body: bytes, source: bytes = b"\x02\x00\x00\x00\x00\x01") -> bytes:
    radiotap = bytes([0, 0, 8, 0, 0, 0, 0, 0])
    frame_control = struct.pack("<H", 0x00D0)
    duration = b"\x00\x00"
    addr1 = b"\xff" * 6
    addr3 = source
    sequence = b"\x00\x00"
    frame = frame_control + duration + addr1 + source + addr3 + sequence + body

    packet = radiotap + frame
    global_header = struct.pack(
        "<IHHIIII",
        0xA1B2C3D4,
        2,
        4,
        0,
        0,
        65535,
        127,
    )
    record = struct.pack("<IIII", 1, 0, len(packet), len(packet)) + packet
    return global_header + record


class AdvertisementParseTests(unittest.TestCase):
    def test_aes_ctr_header(self) -> None:
        parsed = parse_ldn_action(advertisement_body(frame_format=2))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["packet"], "advertisement")
        self.assertEqual(parsed["title_id"], "0100000000001000")
        self.assertEqual(parsed["scene_id"], SCENE_ID)
        self.assertEqual(parsed["ssid"], SSID.hex())
        self.assertEqual(parsed["ldn_version"], 4)
        self.assertEqual(parsed["format"], "aes-ctr")
        self.assertEqual(parsed["size"], 0x500)
        self.assertEqual(parsed["nonce"], "01020304")
        self.assertTrue(parsed["payload_len_ok"])

    def test_plain_header(self) -> None:
        parsed = parse_ldn_action(advertisement_body(frame_format=1))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["format"], "plain")
        self.assertTrue(parsed["payload_len_ok"])

    def test_aes_gcm_header(self) -> None:
        parsed = parse_ldn_action(advertisement_body(frame_format=3))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["format"], "aes-gcm")
        self.assertTrue(parsed["payload_len_ok"])

    def test_truncated_payload_is_marked(self) -> None:
        body = advertisement_body(frame_format=2, size=0x100)
        parsed = parse_ldn_action(body[:-8])
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertFalse(parsed["payload_len_ok"])

    def test_wrong_oui(self) -> None:
        body = bytearray(advertisement_body())
        body[1:4] = b"\x00\x22\xab"
        self.assertIsNone(parse_ldn_action(bytes(body)))

    def test_wrong_protocol(self) -> None:
        body = bytearray(advertisement_body())
        body[4] = 5
        self.assertIsNone(parse_ldn_action(bytes(body)))

    def test_short_body(self) -> None:
        self.assertIsNone(parse_ldn_action(b"\x7f\x00\x22\xaa"))

    def test_unknown_packet_type_is_reported(self) -> None:
        body = bytearray(advertisement_body())
        body[6:8] = (0x0199).to_bytes(2, "big")
        parsed = parse_ldn_action(bytes(body))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["packet"], "unknown(0x0199)")

    def test_authentication_header(self) -> None:
        payload = b"\x00" * 0x40
        network_id = (
            TITLE_ID.to_bytes(8, "little")
            + b"\x00\x00"
            + SCENE_ID.to_bytes(2, "little")
            + b"\x00" * 4
            + SSID
        )
        auth = (
            bytes([4, len(payload) & 0xFF, 0, 0, len(payload) >> 8, 0])
            + b"\x00\x00"
            + network_id
            + b"\x11" * 16
            + b"\x22" * 16
            + payload
        )
        body = b"\x00\x22\xaa" + b"\x01\x02" + b"\x00" + auth
        parsed = parse_authentication(body)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["packet"], "authentication")
        self.assertEqual(parsed["title_id"], "0100000000001000")
        self.assertEqual(parsed["scene_id"], SCENE_ID)
        self.assertEqual(parsed["payload_size"], len(payload))
        self.assertTrue(parsed["payload_len_ok"])


class PcapTests(unittest.TestCase):
    def test_extract_action_frame(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.pcap"
            path.write_bytes(pcap_with_action(advertisement_body()))
            found = extract_advertisements(path)
        self.assertEqual(len(found), 1)
        item = found[0]
        self.assertIsInstance(item, Advertisement)
        self.assertEqual(item.title_id, "0100000000001000")
        self.assertEqual(item.source, "02:00:00:00:00:01")

    def test_unique_advertisements(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.pcap"
            first = pcap_with_action(advertisement_body())
            # Build a second identical packet by duplicating the record.
            record = first[24:]
            second_record = record
            path.write_bytes(first + second_record)
            found = extract_advertisements(path)
        self.assertEqual(len(found), 2)
        self.assertEqual(len(unique_advertisements(found)), 1)

    def test_non_action_frame_is_ignored(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.pcap"
            data = bytearray(pcap_with_action(advertisement_body()))
            # Assertion: the frame control starts after the 24-byte pcap
            # header, 16-byte record header, and 8-byte radiotap header.
            offset = 24 + 16 + 8
            data[offset : offset + 2] = struct.pack("<H", 0x0080)
            path.write_bytes(bytes(data))
            found = extract_advertisements(path)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
