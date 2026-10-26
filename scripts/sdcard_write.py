#!/usr/bin/env python3
"""Validate and write a lab image to a sacrificial SD card.

Writing a raw image destroys the target device's contents. This script refuses
internal disks and disks smaller than the image, prints the exact commands, and
only writes when ``--write`` is passed. Run it without ``--write`` first.
"""

from __future__ import annotations

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


class UnsafeTarget(Exception):
    pass


def disk_info(device: str) -> dict[str, Any]:
    result = subprocess.run(
        ["diskutil", "info", "-plist", device],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise UnsafeTarget(f"diskutil could not read {device}")
    return plistlib.loads(result.stdout)


def validate(device: str, image_size: int, info: dict[str, Any]) -> None:
    if not device.startswith("/dev/disk"):
        raise UnsafeTarget("device must be a /dev/diskN path")
    if device in {"/dev/disk0", "/dev/rdisk0"}:
        raise UnsafeTarget("refusing disk0")
    if info.get("Internal"):
        raise UnsafeTarget("refusing an internal disk")
    if info.get("Whole") is False:
        raise UnsafeTarget("target must be the whole disk, not a partition")
    total = int(info.get("TotalSize") or 0)
    if total < image_size:
        raise UnsafeTarget(
            f"target is {total} bytes, smaller than the image ({image_size})"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a lab image to an SD card.")
    parser.add_argument("--device", required=True, help="Whole disk, e.g. /dev/disk4")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--write", action="store_true", help="Actually write.")
    args = parser.parse_args(argv)

    image = args.image.read_bytes()
    try:
        info = disk_info(args.device)
        validate(args.device, len(image), info)
    except UnsafeTarget as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    name = info.get("MediaName") or info.get("DeviceIdentifier") or "?"
    total = int(info.get("TotalSize") or 0)
    print(f"target : {args.device}  {name}  {total} bytes")
    print(f"image  : {args.image}  {len(image)} bytes")
    print("This erases the target disk.")

    raw = args.device.replace("/dev/disk", "/dev/rdisk")
    print("\nCommands:")
    print(f"  diskutil unmountDisk {args.device}")
    print(f"  sudo dd if={args.image} of={raw} bs=1m")
    print("  sync")

    if not args.write:
        print("\nDry run. Re-run with --write to execute.")
        return 0

    subprocess.run(["diskutil", "unmountDisk", args.device], check=False)
    result = subprocess.run(
        ["sudo", "dd", f"if={args.image}", f"of={raw}", "bs=1m"],
    )
    subprocess.run(["sync"], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
