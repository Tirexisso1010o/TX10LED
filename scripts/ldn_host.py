#!/usr/bin/env python3
"""Host a plaintext LDN network for a single, approved pre-auth test.

This is a research tool, not a game-sharing tool.  It creates a
security-mode-3 (system-debug) LDN network.  In that mode the advertisement
and data frames are plaintext, so the host does not need ``prod.keys``.  The
retail console may reject the network; that is one of the results the test is
designed to observe.

The tool is Linux-only because the LDN package uses nl80211 monitor mode.  It
defaults to a dry run; transmitting requires both ``--host`` and ``--confirm``.

Prerequisites on the Linux host:

    sudo pacman -S --needed python python-pip iw tcpdump ethtool
    python3 -m venv .venv
    .venv/bin/pip install ldn
    sudo systemctl stop NetworkManager
    sudo -E .venv/bin/python scripts/ldn_host.py ... --dry-run
    sudo -E .venv/bin/python scripts/ldn_host.py ... --host --confirm

The interface must support monitor mode and action-frame transmission.  The
LDN package's README reports MediaTek and Realtek drivers as the most
reliable, with ``mt7921e`` confirmed.

This script never writes to the console, never sends application data, and
never asks for or uses real keys.  It uses a dummy key dictionary only to
satisfy the package's parameter check; security mode 3 does not derive a WLAN
key.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

# Non-secret placeholders.  In security mode 3 the package does not call the
# key-derivation path, so these values are never used to encrypt anything.
DUMMY_KEYS = {
    "master_key_00": bytes(16),
    "aes_kek_generation_source": bytes(16),
    "aes_key_generation_source": bytes(16),
}


def parse_ssid(value: str) -> bytes:
    raw = bytes.fromhex(value.replace(":", "").replace(" ", ""))
    if len(raw) != 16:
        raise argparse.ArgumentTypeError("SSID must be exactly 16 bytes (32 hex chars)")
    return raw


def parse_title_id(value: str) -> int:
    cleaned = value.lower().removeprefix("0x")
    if len(cleaned) != 16:
        raise argparse.ArgumentTypeError("title ID must be 16 hex chars")
    try:
        return int(cleaned, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title-id", type=parse_title_id, required=True)
    parser.add_argument("--scene-id", type=int, required=True)
    parser.add_argument("--ssid", type=parse_ssid, required=True)
    parser.add_argument("--channel", type=int, default=6, choices=[1, 6, 11, 36, 40, 44, 48])
    parser.add_argument("--name", default="TX10LED")
    parser.add_argument("--app-version", type=int, default=0)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--ifname", default="ldn")
    parser.add_argument("--phyname", default="phy0")
    parser.add_argument(
        "--host",
        action="store_true",
        help="actually create the network (default: dry run)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirm active frame transmission; required with --host",
    )
    return parser


def make_param(args: argparse.Namespace) -> Any:
    import ldn

    param = ldn.CreateNetworkParam()
    param.ifname = args.ifname
    param.phyname = args.phyname
    param.local_communication_id = args.title_id
    param.scene_id = args.scene_id
    param.max_participants = 8
    param.security_mode = ldn.SECURITY_MODE_SYSTEM_DEBUG
    param.enable_challenge = False
    param.ssid = args.ssid
    param.channel = args.channel
    param.name = args.name.encode()
    param.app_version = args.app_version
    param.platform = ldn.PLATFORM_NX
    param.protocol = 1
    param.version = 4
    param.keys = dict(DUMMY_KEYS)
    param.password = b""
    param.check()
    return param


def dry_run(args: argparse.Namespace) -> int:
    import ldn

    param = make_param(args)

    key_derivation = ldn.KeyDerivation(param.keys, param.protocol)
    network = ldn.NetworkInfo(param.protocol)
    network.address = ldn.MACAddress(bytes.fromhex("020000000001"))
    network.channel = param.channel
    network.band = ldn.ChannelBands[param.channel]
    network.local_communication_id = param.local_communication_id
    network.scene_id = param.scene_id
    network.ssid = param.ssid
    network.version = param.version
    network.server_random = bytes(range(16))
    network.security_mode = param.security_mode
    network.accept_policy = param.accept_policy
    network.max_participants = param.max_participants
    network.num_participants = 1
    network.application_data = param.application_data
    network.app_version = param.app_version
    network.challenge = 0
    network.nonce = b"\x00\x00\x00\x01"

    participant = ldn.ParticipantInfo()
    participant.ip_address = "169.254.1.1"
    participant.mac_address = network.address
    participant.connected = True
    participant.name = param.name
    participant.app_version = param.app_version
    participant.platform = param.platform
    network.participants = [participant] + [ldn.ParticipantInfo() for _ in range(7)]

    frame = network.build_advertisement(key_derivation)
    encoded = frame.encode()

    print("Dry run only; no radio access.")
    print(f"  title ID:     {param.local_communication_id:016x}")
    print(f"  scene ID:     {param.scene_id}")
    print(f"  SSID:         {param.ssid.hex()}")
    print(f"  channel:      {param.channel}")
    print(f"  security:     {param.security_mode} (system debug / plaintext)")
    print("  challenge:    disabled")
    print(f"  frame length: {len(encoded)} bytes")
    print(f"  frame hex:    {encoded.hex()}")
    print()
    print("A retail console may reject security mode 3.  If it does, the")
    print("no-key path is closed and the retail path requires prod.keys.")
    return 0


async def host(args: argparse.Namespace) -> int:
    import ldn
    import trio

    param = make_param(args)
    print("Creating plaintext LDN network.  Press Ctrl-C to stop.")
    print(f"  title ID {param.local_communication_id:016x}, scene {param.scene_id}, "
          f"channel {param.channel}, SSID {param.ssid.hex()}")
    print("  Waiting for the console to join.  No application data is sent.")

    async with ldn.create_network(param) as network:
        with trio.move_on_after(args.duration):
            while True:
                event = await network.next_event()
                if isinstance(event, ldn.JoinEvent):
                    participant = event.participant
                    print(
                        f"JOIN index={event.index} mac={participant.mac_address} "
                        f"ip={participant.ip_address} "
                        f"name={participant.name.decode(errors='replace')} "
                        f"platform={participant.platform}"
                    )
                elif isinstance(event, ldn.LeaveEvent):
                    print(f"LEAVE index={event.index} mac={event.participant.mac_address}")
                elif isinstance(event, ldn.DisconnectEvent):
                    print(f"DISCONNECT reason={event.reason}")
                    break
    print("Host stopped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if sys.platform != "linux":
        print(
            "This script requires Linux with nl80211 monitor mode. "
            "The passive parser (scripts/ldn_probe.py) is portable.",
            file=sys.stderr,
        )
        return 2

    try:
        import ldn  # noqa: F401
    except Exception as exc:  # pragma: no cover - host-side dependency
        print(
            f"Could not import the LDN package: {exc}\n"
            "Install it with: .venv/bin/pip install ldn",
            file=sys.stderr,
        )
        return 2

    if not args.host:
        return dry_run(args)

    if not args.confirm:
        print(
            "--host transmits LDN frames. Re-run with --confirm after "
            "reviewing the test plan and obtaining approval.",
            file=sys.stderr,
        )
        return 2

    import trio

    try:
        return trio.run(host, args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
