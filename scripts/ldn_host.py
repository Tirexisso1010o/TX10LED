#!/usr/bin/env python3
"""Host an LDN network for a single, approved pre-auth test.

This is a research tool, not a game-sharing tool.  It can create either a
security-mode-3 (system-debug) network, whose advertisement and data frames are
plaintext, or a security-mode-1 (prod) network, whose advertisement is
encrypted with the local ``prod.keys``.  The retail console may reject either
network; that is one of the results the test is designed to observe.

The tool is Linux-only because the LDN package uses nl80211 monitor mode.  It
defaults to a dry run; transmitting requires both ``--host`` and ``--confirm``.

Prerequisites on the Linux host or Linux VM:

    sudo apt-get install -y iw tcpdump ethtool python3 python3-venv
    python3 -m venv ~/ldn-venv
    ~/ldn-venv/bin/pip install ldn
    sudo systemctl stop NetworkManager 2>/dev/null || true
    sudo -E ~/ldn-venv/bin/python scripts/ldn_host.py ... --dry-run
    sudo -E ~/ldn-venv/bin/python scripts/ldn_host.py ... --host --confirm

The interface must support monitor mode and action-frame transmission.  The
LDN package's README reports MediaTek and Realtek drivers as the most
reliable, with ``mt7921e`` confirmed.  The TP-Link Archer T3U Plus
(2357:0138) using ``rtw88_8822bu`` in an OrbStack Ubuntu VM is validated for
passive capture, but its transmit path is unconfirmed; ``dmesg`` reports
``failed to get tx report from firmware``.  Use ``--compat-no-active-ack``
with this driver because it rejects ``NL80211_MNTR_FLAG_ACTIVE``.

This script never writes to the console, never sends application data, and
never prints key material, the SSID, or a complete frame.  In security mode 3
it uses dummy key placeholders only to satisfy the package's parameter check;
that mode does not derive a WLAN key.  In security mode 1 it reads keys from a
local file that must remain outside version control.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

# Non-secret placeholders.  In security mode 3 the package does not call the
# key-derivation path, so these values are never used to encrypt anything.
DUMMY_KEYS = {
    "master_key_00": bytes(16),
    "aes_kek_generation_source": bytes(16),
    "aes_key_generation_source": bytes(16),
}

REQUIRED_KEYS = (
    "master_key_00",
    "aes_kek_generation_source",
    "aes_key_generation_source",
)

VALID_CHANNELS = (1, 6, 11, 36, 40, 44, 48)
SECURITY_MODE_NAMES = {
    1: "prod / encrypted",
    2: "debug / advertisement encrypted",
    3: "system debug / plaintext",
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


def parse_hex_bytes(value: str) -> bytes:
    cleaned = value.replace(":", "").replace(" ", "")
    if len(cleaned) % 2:
        raise argparse.ArgumentTypeError("hex value must have an even number of digits")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def load_room_file(path: Path) -> dict[str, Any]:
    """Load local-only captured room parameters.

    The file is expected to stay under the git-ignored ``Firmware/`` directory
    (or another local-only location).  It may contain the SSID, so it must
    never be committed or pasted into documentation.
    """
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("room file must contain a JSON object")

    room: dict[str, Any] = {}

    if "title_id" in raw:
        try:
            room["title_id"] = parse_title_id(str(raw["title_id"]))
        except argparse.ArgumentTypeError as exc:
            raise ValueError(f"room file title_id: {exc}") from exc

    for key in (
        "scene_id",
        "channel",
        "app_version",
        "max_participants",
        "ldn_version",
        "protocol",
        "security_mode",
        "num_participants",
    ):
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"room file {key} must be an integer")
        room[key] = value

    if "ssid" in raw:
        try:
            room["ssid"] = parse_ssid(str(raw["ssid"]))
        except argparse.ArgumentTypeError as exc:
            raise ValueError(f"room file ssid: {exc}") from exc

    if "application_data" in raw:
        try:
            room["application_data"] = parse_hex_bytes(str(raw["application_data"]))
        except argparse.ArgumentTypeError as exc:
            raise ValueError(f"room file application_data: {exc}") from exc

    if "challenge" in raw:
        if not isinstance(raw["challenge"], bool):
            raise ValueError("room file challenge must be true or false")
        room["challenge"] = raw["challenge"]

    return room


def load_keys_file(path: Path) -> dict[str, bytes]:
    """Load a local prod.keys file without ever printing its contents."""
    import ldn

    keys = ldn.load_keys(str(path))
    missing = [name for name in REQUIRED_KEYS if name not in keys]
    if missing:
        raise ValueError(
            "keys file is missing required key(s): " + ", ".join(missing)
        )
    return keys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--room-file",
        type=Path,
        help=(
            "local-only JSON with captured room parameters; CLI values override "
            "the file. Keep this file outside version control."
        ),
    )
    parser.add_argument("--title-id", type=parse_title_id, default=None)
    parser.add_argument("--scene-id", type=int, default=None)
    parser.add_argument("--ssid", type=parse_ssid, default=None)
    parser.add_argument(
        "--channel", type=int, default=None, choices=list(VALID_CHANNELS)
    )
    parser.add_argument("--name", default="TX10LED")
    parser.add_argument("--app-version", type=int, default=None)
    parser.add_argument("--max-participants", type=int, default=None)
    parser.add_argument("--ldn-version", type=int, default=None, choices=[2, 3, 4])
    parser.add_argument("--protocol", type=int, default=None, choices=[1, 3])
    parser.add_argument(
        "--security-mode",
        type=int,
        default=None,
        choices=[1, 2, 3],
        help="1 = prod (encrypted), 2 = debug, 3 = system debug (plaintext)",
    )
    parser.add_argument(
        "--application-data",
        type=parse_hex_bytes,
        default=None,
        help="application data hex (at most 0x180 bytes)",
    )
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=None,
        help="local prod.keys file; required for security modes 1 and 2",
    )
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--ifname", default="ldn")
    parser.add_argument("--phyname", default="phy0")
    challenge = parser.add_mutually_exclusive_group()
    challenge.add_argument(
        "--challenge", dest="challenge", action="store_true", default=None
    )
    challenge.add_argument(
        "--no-challenge", dest="challenge", action="store_false"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="build and validate the frame without touching the radio (default)",
    )
    mode.add_argument(
        "--host",
        action="store_true",
        help="actually create the network",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirm active frame transmission; required with --host",
    )
    parser.add_argument(
        "--compat-no-active-ack",
        action="store_true",
        help=(
            "create the LDN ACK monitor without NL80211_MNTR_FLAG_ACTIVE; "
            "needed for rtw88_8822bu, which rejects the active flag"
        ),
    )
    return parser


def resolve_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> argparse.Namespace:
    """Merge the room file and CLI values, then validate the result."""
    room: dict[str, Any] = {}
    if args.room_file is not None:
        try:
            room = load_room_file(args.room_file)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(f"could not load room file: {exc}")

    def pick(name: str, default: Any) -> Any:
        value = getattr(args, name)
        if value is not None:
            return value
        if name in room:
            return room[name]
        return default

    args.title_id = pick("title_id", None)
    args.scene_id = pick("scene_id", None)
    args.ssid = pick("ssid", None)
    args.channel = pick("channel", 6)
    args.app_version = pick("app_version", 0)
    args.max_participants = pick("max_participants", 8)
    args.ldn_version = pick("ldn_version", 4)
    args.protocol = pick("protocol", 1)
    args.security_mode = pick("security_mode", 3)
    args.application_data = pick("application_data", b"")
    args.challenge = pick("challenge", args.security_mode != 3)

    if args.title_id is None:
        parser.error("--title-id or --room-file with title_id is required")
    if args.scene_id is None:
        parser.error("--scene-id or --room-file with scene_id is required")
    if args.ssid is None:
        parser.error("--ssid or --room-file with ssid is required")

    if not 0 <= args.scene_id <= 0xFFFF:
        parser.error("--scene-id must fit in 16 bits")
    if not 0 <= args.max_participants <= 8:
        parser.error("--max-participants must be between 0 and 8")
    if len(args.application_data) > 0x180:
        parser.error("--application-data must be at most 0x180 bytes")
    if args.channel not in VALID_CHANNELS:
        parser.error(f"--channel must be one of {VALID_CHANNELS}")

    if args.security_mode in (1, 2):
        if args.keys_file is None:
            parser.error(
                "--keys-file is required for security modes 1 and 2"
            )
        try:
            args.keys = load_keys_file(args.keys_file)
        except (OSError, ValueError) as exc:
            parser.error(f"could not load keys file: {exc}")
        args.key_count = len(args.keys)
    else:
        args.keys = dict(DUMMY_KEYS)
        args.key_count = 0

    return args


def make_param(args: argparse.Namespace) -> Any:
    import ldn

    param = ldn.CreateNetworkParam()
    param.ifname = args.ifname
    param.phyname = args.phyname
    param.local_communication_id = args.title_id
    param.scene_id = args.scene_id
    param.max_participants = args.max_participants
    param.application_data = args.application_data
    param.security_mode = args.security_mode
    param.enable_challenge = args.challenge
    param.ssid = args.ssid
    param.channel = args.channel
    param.name = args.name.encode()
    param.app_version = args.app_version
    param.platform = ldn.PLATFORM_NX
    param.protocol = args.protocol
    param.version = args.ldn_version
    param.keys = dict(args.keys)
    param.password = b""
    param.check()
    return param


def expected_format(ldn: Any, security_mode: int, protocol: int) -> int:
    if security_mode == ldn.SECURITY_MODE_SYSTEM_DEBUG:
        return ldn.ADVERTISE_FORMAT_PLAIN
    if protocol == 1:
        return ldn.ADVERTISE_FORMAT_AES_CTR
    return ldn.ADVERTISE_FORMAT_AES_GCM


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
    network.challenge = 0x1122334455667788 if param.enable_challenge else 0
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

    # Decode the frame with the same key derivation.  This validates the
    # ciphertext, the SHA-256 trailer, and every field that the host will send
    # without printing the frame or the SSID.
    check = ldn.AdvertisementFrame(key_derivation, param.protocol)
    check.decode(encoded)
    decoded = ldn.NetworkInfo(param.protocol)
    decoded.parse_advertisement(check)

    checks = {
        "title_id": decoded.local_communication_id
        == network.local_communication_id,
        "scene_id": decoded.scene_id == network.scene_id,
        "ssid": decoded.ssid == network.ssid,
        "ldn_version": decoded.version == network.version,
        "security_mode": decoded.security_mode == network.security_mode,
        "app_version": decoded.app_version == network.app_version,
        "max_participants": decoded.max_participants
        == network.max_participants,
        "application_data": decoded.application_data == network.application_data,
        "challenge": decoded.challenge == network.challenge,
        "nonce": decoded.nonce == network.nonce,
        "participants": len(decoded.participants) == len(network.participants),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        print(
            "Round-trip decode failed for: " + ", ".join(failed),
            file=sys.stderr,
        )
        return 1

    wanted_format = expected_format(ldn, param.security_mode, param.protocol)
    if frame.format != wanted_format:
        print(
            f"Unexpected frame format {frame.format}; expected {wanted_format}",
            file=sys.stderr,
        )
        return 1

    format_names = {
        ldn.ADVERTISE_FORMAT_PLAIN: "plain",
        ldn.ADVERTISE_FORMAT_AES_CTR: "aes-ctr",
        ldn.ADVERTISE_FORMAT_AES_GCM: "aes-gcm",
    }

    print("Dry run only; no radio access.")
    if args.room_file is not None:
        print(f"  room file:      {args.room_file} (local-only)")
    print(f"  title ID:       {param.local_communication_id:016x}")
    print(f"  scene ID:       {param.scene_id}")
    print("  SSID:           <redacted; 16 bytes>")
    print(f"  channel:        {param.channel}")
    print(
        f"  security mode:  {param.security_mode} "
        f"({SECURITY_MODE_NAMES.get(param.security_mode, 'unknown')})"
    )
    print(f"  challenge:      {'enabled' if param.enable_challenge else 'disabled'}")
    print(f"  max participants: {param.max_participants}")
    print(f"  app version:    {param.app_version}")
    print(f"  LDN version:    {param.version}")
    print(f"  protocol:       {param.protocol}")
    print(f"  application data: {len(param.application_data)} bytes")
    if param.security_mode == 3:
        print("  keys:           dummy placeholders (not used in system-debug mode)")
    else:
        print(f"  keys file:      {args.keys_file} (local-only)")
        print(f"  keys loaded:    {args.key_count} (required keys present)")
    print(f"  frame format:   {format_names[frame.format]}")
    print(f"  frame length:   {len(encoded)} bytes")
    print(f"  round-trip:     OK ({len(checks)} fields match)")
    print()
    if param.security_mode == 3:
        print("A retail console may reject security mode 3.  If it does, the")
        print("no-key path is closed and the retail path requires prod.keys.")
    else:
        print("The frame is encrypted with the local keys.  Do not paste the")
        print("frame, the keys, or the SSID into a commit or a report.")
    return 0


def install_no_active_ack_compat() -> None:
    """Create the LDN ACK monitor without the unsupported ACTIVE flag.

    ``kinnay/LDN`` creates a second monitor interface with
    ``NL80211_MNTR_FLAG_ACTIVE`` so the driver can ACK incoming unicast frames.
    The in-kernel ``rtw88_8822bu`` driver rejects that flag with
    ``EOPNOTSUPP``.  The second interface is not referenced by ``MonitorAP``;
    creating it without the flag lets the host start, at the cost of relying on
    the hardware/driver for ACK handling.
    """
    from ldn import wlan

    @contextlib.asynccontextmanager
    async def create_monitor_ap(
        self: Any,
        phyname: str,
        ifname: str,
        ifname_active: str,
        ssid: str,
        channel: int,
        key: bytes | None,
        max_stations: int,
    ):
        async with self.create_monitor(phyname, ifname, channel) as monitor:
            async with self.create_monitor(
                phyname, ifname_active, active=False
            ):
                access_point = wlan.MonitorAP(
                    monitor, ssid, channel, key, max_stations
                )
                async with access_point.start():
                    yield access_point

    wlan.Factory.create_monitor_ap = create_monitor_ap


async def host(args: argparse.Namespace) -> int:
    import ldn
    import trio

    if args.compat_no_active_ack:
        install_no_active_ack_compat()

    param = make_param(args)
    print("Creating LDN network.  Press Ctrl-C to stop.")
    print(f"  title ID {param.local_communication_id:016x}, "
          f"scene {param.scene_id}, channel {param.channel}")
    print(
        f"  security mode {param.security_mode} "
        f"({SECURITY_MODE_NAMES.get(param.security_mode, 'unknown')}), "
        f"challenge {'enabled' if param.enable_challenge else 'disabled'}"
    )
    print("  SSID: <redacted; 16 bytes>")
    print("  Waiting for the console to join.  No application data is sent.")

    joined = 0
    async with ldn.create_network(param) as network:
        print("Advertising now.")
        with trio.move_on_after(args.duration):
            while True:
                event = await network.next_event()
                if isinstance(event, ldn.JoinEvent):
                    joined += 1
                    participant = event.participant
                    print(
                        f"JOIN index={event.index} mac={participant.mac_address} "
                        f"ip={participant.ip_address} "
                        f"name={participant.name.decode(errors='replace')} "
                        f"platform={participant.platform}"
                    )
                elif isinstance(event, ldn.LeaveEvent):
                    print(f"LEAVE index={event.index} "
                          f"mac={event.participant.mac_address}")
                elif isinstance(event, ldn.DisconnectEvent):
                    print(f"DISCONNECT reason={event.reason}")
                    break
    print(f"Host stopped.  Join events observed: {joined}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if sys.platform != "linux":
        print(
            "This script requires Linux with nl80211 monitor mode. "
            "The passive parser (scripts/ldn_probe.py) is portable.",
            file=sys.stderr,
        )
        return 2

    args = resolve_args(args, parser)

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
