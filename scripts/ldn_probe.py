#!/usr/bin/env python3
"""Inspect LDN advertisement frames in a pcap or a hex action body.

LDN (local wireless) advertisement frames carry a plaintext ``NetworkId``
header even when the rest of the payload is AES-encrypted.  That means a
passive capture can reveal the title ID, scene ID, SSID, protocol version,
encryption format, and nonce without ``prod.keys``.

This tool is read-only: it parses a capture that was made with tcpdump.  It
does not open a radio, transmit frames, or touch the console.

Capture example (on Linux, with the adapter in monitor mode):

    sudo tcpdump -i wlan0 -y IEEE802_11_RADIO -w ldn.pcap

Analyse:

    python3 scripts/ldn_probe.py --pcap ldn.pcap
    python3 scripts/ldn_probe.py --pcap ldn.pcap --json --redact

The LDN wire format is documented at:
https://github.com/kinnay/NintendoClients/wiki/LDN-Protocol
https://switchbrew.org/wiki/LDN_services
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterator

LDN_CATEGORY = 0x7F
LDN_OUI = b"\x00\x22\xaa"
LDN_PROTOCOL = 4
PACKET_ADVERTISE = 0x0101
PACKET_AUTHENTICATE = 0x0102
PACKET_DISCONNECT = 0x0103

FORMATS = {
    1: "plain",
    2: "aes-ctr",
    3: "aes-gcm",
}

# 802.11 frame control: type 0 (management), subtype 13 (action).
ACTION_FRAME_MASK = 0x00FC
ACTION_FRAME_VALUE = 0x00D0


@dataclass
class Advertisement:
    source: str
    title_id: str
    scene_id: int
    ssid: str
    ldn_version: int
    format: str
    size: int
    nonce: str
    ciphertext_len: int
    payload_len_ok: bool | None
    timestamp: float | None = None

    def public(self) -> dict[str, Any]:
        """Return a dict with identifiers suitable for sharing."""
        data = asdict(self)
        data["source"] = redact_mac(data["source"])
        data["ssid"] = "<redacted>"
        return data


def redact_mac(value: str) -> str:
    parts = value.split(":")
    if len(parts) == 6:
        return "xx:xx:xx:xx:xx:xx"
    return "<redacted>"


def format_mac(raw: bytes) -> str:
    return ":".join(f"{byte:02x}" for byte in raw)


def parse_ldn_action(body: bytes) -> dict[str, Any] | None:
    """Parse an LDN action-frame body.

    ``body`` starts at the 802.11 action category byte (0x7f), not at the
    802.11 header.  Returns ``None`` for frames that are not LDN action
    frames.  Unknown LDN packet types are returned with a small descriptor so
    the caller can report them without interpreting them.
    """
    if len(body) < 8:
        return None
    if body[0] != LDN_CATEGORY:
        return None
    if body[1:4] != LDN_OUI:
        return None
    if body[4] != LDN_PROTOCOL:
        return None
    if body[5] != 0:
        return None

    packet_type = int.from_bytes(body[6:8], "big")

    if packet_type == PACKET_ADVERTISE:
        return parse_advertisement(body)
    if packet_type == PACKET_AUTHENTICATE:
        # Authentication is normally a data frame with ethertype 0x88b7,
        # not an action frame.  Keep this branch descriptive rather than
        # pretending the action body has the data-frame layout.
        return {"packet": "authentication", "raw_len": len(body)}
    if packet_type == PACKET_DISCONNECT:
        return {"packet": "disconnect", "raw_len": len(body)}

    return {"packet": f"unknown(0x{packet_type:04x})", "raw_len": len(body)}


def parse_advertisement(body: bytes) -> dict[str, Any] | None:
    """Parse the plaintext header of an LDN advertisement frame."""
    # category(1) + OUI(3) + protocol(1) + pad(1) + type(2) + pad(4)
    header_len = 0x0C
    network_id_len = 32
    fixed_tail_len = 1 + 1 + 2 + 4  # version, format, size, nonce
    if len(body) < header_len + network_id_len + fixed_tail_len:
        return None

    offset = header_len
    network_id = body[offset : offset + network_id_len]
    offset += network_id_len

    title_id = int.from_bytes(network_id[0:8], "big")
    scene_id = int.from_bytes(network_id[10:12], "big")
    ssid = network_id[16:32]

    version = body[offset]
    offset += 1
    frame_format = body[offset]
    offset += 1
    size = int.from_bytes(body[offset : offset + 2], "big")
    offset += 2
    nonce = body[offset : offset + 4]
    offset += 4

    ciphertext_len = len(body) - offset
    if frame_format in (1, 2):
        expected = 32 + size
    elif frame_format == 3:
        expected = 16 + size
    else:
        expected = None

    return {
        "packet": "advertisement",
        "title_id": f"{title_id:016x}",
        "scene_id": scene_id,
        "ssid": ssid.hex(),
        "ldn_version": version,
        "format": FORMATS.get(frame_format, f"unknown({frame_format})"),
        "size": size,
        "nonce": nonce.hex(),
        "ciphertext_len": ciphertext_len,
        "payload_len_ok": expected == ciphertext_len if expected is not None else None,
    }


def parse_authentication(body: bytes) -> dict[str, Any] | None:
    """Parse the plaintext header of an LDN authentication frame.

    Authentication frames are data frames, not action frames, so this helper
    is used only when the caller has already identified the LDN data payload.
    The body starts with the OUI (no action category).
    """
    if len(body) < 6 + 0x48:
        return None
    if body[0:3] != LDN_OUI:
        return None
    if int.from_bytes(body[3:5], "big") != PACKET_AUTHENTICATE:
        return None
    if body[5] != 0:
        return None

    auth = body[6:]
    version = auth[0]
    size_lo = auth[1]
    status = auth[2]
    is_response = auth[3]
    size_hi = auth[4]
    frame_format = auth[5]

    network_id = auth[8:40]
    server_random = auth[40:56]
    client_random = auth[56:72]
    payload_size = (size_hi << 8) | size_lo
    payload = auth[72 : 72 + payload_size]

    return {
        "packet": "authentication",
        "version": version,
        "status": status,
        "is_response": bool(is_response),
        "format": "aes-gcm" if frame_format == 1 else "plain",
        "title_id": f"{int.from_bytes(network_id[0:8], 'little'):016x}",
        "scene_id": int.from_bytes(network_id[10:12], "little"),
        "server_random": server_random.hex(),
        "client_random": client_random.hex(),
        "payload_size": payload_size,
        "payload_len_ok": len(payload) == payload_size,
    }


def pcap_packets(path: Path) -> Iterator[tuple[float, int, bytes]]:
    """Yield (timestamp, linktype, packet) from a classic pcap file."""
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError("pcap is shorter than the global header")

    magic = data[0:4]
    # The magic is written in the capture host's byte order.  On a
    # little-endian host, 0xa1b2c3d4 appears as d4 c3 b2 a1.
    if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        endian = "<"
    elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
        endian = ">"
    else:
        raise ValueError("unsupported pcap magic")

    linktype = struct.unpack_from(endian + "I", data, 20)[0]
    offset = 24
    while offset + 16 <= len(data):
        ts_sec, ts_frac, incl_len, _orig_len = struct.unpack_from(
            endian + "IIII", data, offset
        )
        offset += 16
        if offset + incl_len > len(data):
            break
        packet = data[offset : offset + incl_len]
        offset += incl_len
        yield ts_sec + ts_frac / 1_000_000, linktype, packet


def ieee80211_body(packet: bytes, linktype: int) -> bytes | None:
    """Return the 802.11 payload after the MAC header, or None."""
    if linktype == 127:  # IEEE802_11_RADIO (radiotap)
        if len(packet) < 4:
            return None
        radiotap_len = struct.unpack_from("<H", packet, 2)[0]
        frame = packet[radiotap_len:]
    elif linktype == 105:  # IEEE802_11
        frame = packet
    else:
        return None

    if len(frame) < 24:
        return None
    frame_control = struct.unpack_from("<H", frame, 0)[0]
    if (frame_control & ACTION_FRAME_MASK) != ACTION_FRAME_VALUE:
        return None
    return frame[24:]


def extract_advertisements(path: Path) -> list[Advertisement]:
    found: list[Advertisement] = []
    for timestamp, linktype, packet in pcap_packets(path):
        body = ieee80211_body(packet, linktype)
        if body is None:
            continue
        parsed = parse_ldn_action(body)
        if not parsed or parsed.get("packet") != "advertisement":
            continue
        # A truncated or FCS-padded frame is still useful for the header, but
        # ``payload_len_ok`` records that it was not a complete payload.
        source = format_mac(packet[10:16]) if linktype == 105 else format_mac(
            packet[struct.unpack_from("<H", packet, 2)[0] + 10 :][:6]
        )
        found.append(
            Advertisement(
                source=source,
                title_id=parsed["title_id"],
                scene_id=parsed["scene_id"],
                ssid=parsed["ssid"],
                ldn_version=parsed["ldn_version"],
                format=parsed["format"],
                size=parsed["size"],
                nonce=parsed["nonce"],
                ciphertext_len=parsed["ciphertext_len"],
                payload_len_ok=parsed["payload_len_ok"],
                timestamp=timestamp,
            )
        )
    return found


def unique_advertisements(found: list[Advertisement]) -> list[Advertisement]:
    seen: set[tuple[str, str, int, str]] = set()
    unique: list[Advertisement] = []
    for item in found:
        key = (item.source, item.title_id, item.scene_id, item.ssid)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pcap", type=Path, help="pcap captured with tcpdump")
    source.add_argument("--hex", help="hex action body starting with 7f 00 22 aa")
    parser.add_argument("--json", action="store_true", help="print JSON lines")
    parser.add_argument("--redact", action="store_true", help="redact MAC and SSID")
    parser.add_argument("--max", type=int, default=20, help="max networks to print")
    args = parser.parse_args(argv)

    if args.hex:
        try:
            body = bytes.fromhex("".join(args.hex.split()))
        except ValueError as exc:
            parser.error(f"invalid hex: {exc}")
        parsed = parse_ldn_action(body)
        if parsed is None:
            print("not an LDN action frame", file=sys.stderr)
            return 1
        print(json.dumps(parsed, indent=2))
        return 0

    try:
        frames = extract_advertisements(args.pcap)
    except (OSError, ValueError) as exc:
        print(f"could not read pcap: {exc}", file=sys.stderr)
        return 1

    if not frames:
        print(
            "No LDN advertisement frames found. Check that the adapter is in "
            "monitor mode, that the capture is on the console's channel "
            "(1/6/11 or 36/40/44/48), and that the console is hosting a "
            "local-wireless room.",
            file=sys.stderr,
        )
        return 1

    unique = unique_advertisements(frames)
    counts = Counter((item.title_id, item.scene_id) for item in frames)

    if args.json:
        for item in unique[: args.max]:
            data = item.public() if args.redact else asdict(item)
            print(json.dumps(data, sort_keys=True))
    else:
        print(
            f"{len(frames)} advertisement frame(s), "
            f"{len(unique)} unique network(s)"
        )
        for item in unique[: args.max]:
            shown = item.public() if args.redact else asdict(item)
            print()
            for key, value in shown.items():
                print(f"  {key}: {value}")
        if len(unique) > args.max:
            print(f"\n... {len(unique) - args.max} more network(s) not shown")

    print()
    print("Frames by title/scene:")
    for (title_id, scene_id), count in counts.most_common():
        print(f"  {title_id} scene {scene_id}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
