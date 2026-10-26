#!/usr/bin/env python3
"""Build minimal FAT32 SD-card images with one controlled anomaly each.

The images are for a sacrificial card and a console mount test. They are not
fuzzers: each anomaly targets a specific bounds or consistency check, so a
result is attributable.

This tool only writes files. Writing an image to a physical device is a
separate, destructive step that the owner must run explicitly.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

SECTOR = 512
RESERVED = 32
NUM_FATS = 2
ROOT_CLUSTER = 2
FILE_CLUSTER = 3
FILE_SIZE = 16
EOC = 0x0FFFFFFF

ANOMALIES = {
    "none": "Valid control image with one 16-byte file.",
    "cluster_oob": "FAT chain for the file points far beyond the cluster count.",
    "dir_size_huge": "Directory entry declares a 0xFFFFFFFF byte file size.",
    "dir_cluster_oob": "Directory entry points at an out-of-range first cluster.",
    "fat_loop": "FAT chain for the file loops back to its own cluster.",
    "bpb_spc_zero": "BPB declares zero sectors per cluster.",
    "lfn_bad": "Long-file-name entry has an invalid checksum and length.",
    "two_fats_mismatch": "The two FAT copies disagree about the file chain.",
}


@dataclass(frozen=True)
class Layout:
    total_sectors: int
    fat_sectors: int
    sectors_per_cluster: int
    clusters: int
    data_start: int


def layout_for(size_mb: int, sectors_per_cluster: int = 1) -> Layout:
    total = (size_mb * 1024 * 1024) // SECTOR
    fat = 1
    for _ in range(16):
        data_sectors = total - RESERVED - NUM_FATS * fat
        clusters = data_sectors // sectors_per_cluster
        needed = ((clusters + 2) * 4 + SECTOR - 1) // SECTOR
        if needed <= fat:
            break
        fat = needed
    else:
        raise ValueError("FAT size did not converge")
    data_start = RESERVED + NUM_FATS * fat
    return Layout(total, fat, sectors_per_cluster, clusters, data_start)


def _boot_sector(layout: Layout, volume_id: int, hidden: int = 0) -> bytes:
    bs = bytearray(SECTOR)
    bs[0:3] = b"\xeb\x58\x90"
    bs[3:11] = b"MSWIN4.1"
    struct.pack_into(
        "<HBHBHHBHHHII",
        bs,
        11,
        SECTOR,
        layout.sectors_per_cluster,
        RESERVED,
        NUM_FATS,
        0,
        0,
        0xF8,
        0,
        63,
        255,
        hidden,
        layout.total_sectors,
    )
    struct.pack_into("<IHHIHH", bs, 36, layout.fat_sectors, 0, 0, ROOT_CLUSTER, 1, 6)
    bs[64] = 0x80
    bs[66] = 0x29
    struct.pack_into("<I", bs, 67, volume_id)
    bs[71:82] = b"TX10LAB    "
    bs[82:90] = b"FAT32   "
    bs[510:512] = b"\x55\xaa"
    return bytes(bs)


def _fsinfo() -> bytes:
    sector = bytearray(SECTOR)
    struct.pack_into("<I", sector, 0, 0x41615252)
    struct.pack_into("<I", sector, 484, 0x61417272)
    struct.pack_into("<I", sector, 488, 0xFFFFFFFF)
    struct.pack_into("<I", sector, 492, 0xFFFFFFFF)
    struct.pack_into("<I", sector, 508, 0xAA550000)
    return bytes(sector)


def _fat(layout: Layout, chain: dict[int, int]) -> bytes:
    entries = bytearray((layout.fat_sectors * SECTOR) // 4 * 4)
    table = [0] * (layout.clusters + 2)
    table[0] = 0x0FFFFFF8
    table[1] = 0x0FFFFFFF
    table[ROOT_CLUSTER] = EOC
    table[FILE_CLUSTER] = EOC
    for cluster, value in chain.items():
        table[cluster] = value
    for index, value in enumerate(table):
        struct.pack_into("<I", entries, index * 4, value & 0x0FFFFFFF)
    return bytes(entries[: layout.fat_sectors * SECTOR])


def _directory(layout: Layout, anomaly: str) -> bytes:
    sector = bytearray(SECTOR)
    name = b"TEST    TXT"
    entry = bytearray(32)
    entry[0:11] = name
    entry[11] = 0x20
    high = 0
    cluster = FILE_CLUSTER
    size = FILE_SIZE
    if anomaly in {"cluster_oob", "fat_loop"}:
        size = 1024  # force the driver to follow the FAT chain
    if anomaly == "dir_size_huge":
        size = 0xFFFFFFFF
    if anomaly == "dir_cluster_oob":
        cluster = 0x0FFFFFF0
        high = 0x0FFF
    struct.pack_into("<H", entry, 20, high)
    struct.pack_into("<H", entry, 26, cluster & 0xFFFF)
    struct.pack_into("<I", entry, 28, size)
    offset = 0
    if anomaly == "lfn_bad":
        lfn = bytearray(32)
        lfn[0] = 0x41
        lfn[11] = 0x0F
        lfn[12] = 0x00
        lfn[13] = 0xFF  # invalid checksum
        lfn[26] = 0x00
        lfn[27] = 0x00
        sector[0:32] = lfn
        offset = 32
    sector[offset : offset + 32] = entry
    return bytes(sector)


def _build_fs(
    size_mb: int,
    anomaly: str,
    *,
    volume_id: int,
    hidden: int,
) -> tuple[bytes, Layout]:
    if anomaly not in ANOMALIES:
        raise ValueError(f"unknown anomaly: {anomaly}")
    layout = layout_for(size_mb)
    image = bytearray(layout.total_sectors * SECTOR)
    image[0:SECTOR] = _boot_sector(layout, volume_id, hidden)
    image[SECTOR : 2 * SECTOR] = _fsinfo()
    image[6 * SECTOR : 7 * SECTOR] = _boot_sector(layout, volume_id, hidden)

    chain: dict[int, int] = {}
    if anomaly == "cluster_oob":
        chain[FILE_CLUSTER] = 0x0FFFFFF0
    elif anomaly == "fat_loop":
        chain[FILE_CLUSTER] = FILE_CLUSTER

    first_fat = _fat(layout, chain)
    second_fat = bytearray(first_fat)
    if anomaly == "two_fats_mismatch":
        struct.pack_into("<I", second_fat, FILE_CLUSTER * 4, 0x0FFFFFF0)
    image[RESERVED * SECTOR : (RESERVED + layout.fat_sectors) * SECTOR] = first_fat
    start = (RESERVED + layout.fat_sectors) * SECTOR
    image[start : start + layout.fat_sectors * SECTOR] = bytes(second_fat)
    if anomaly == "bpb_spc_zero":
        image[13] = 0

    data_offset = layout.data_start * SECTOR
    image[data_offset : data_offset + SECTOR] = _directory(layout, anomaly)
    file_offset = data_offset + (FILE_CLUSTER - 2) * SECTOR
    image[file_offset : file_offset + FILE_SIZE] = b"HELLO FROM TX10\n"
    return bytes(image), layout


def build_image(
    size_mb: int,
    anomaly: str,
    *,
    volume_id: int = 0x7A10C0DE,
    mbr: bool = False,
    mbr_start: int = 8192,
) -> bytes:
    hidden = mbr_start if mbr else 0
    fs, layout = _build_fs(
        size_mb, anomaly, volume_id=volume_id, hidden=hidden
    )
    if not mbr:
        return fs
    prefix = bytearray(mbr_start * SECTOR)
    entry = 446
    prefix[entry] = 0x00
    prefix[entry + 1 : entry + 4] = b"\xfe\xff\xff"
    prefix[entry + 4] = 0x0C
    prefix[entry + 5 : entry + 8] = b"\xfe\xff\xff"
    struct.pack_into("<I", prefix, entry + 8, mbr_start)
    struct.pack_into("<I", prefix, entry + 12, len(fs) // SECTOR)
    prefix[510:512] = b"\x55\xaa"
    return bytes(prefix) + fs


def describe(image: bytes) -> dict[str, object]:
    offset = 0
    mbr = image[510:512] == b"\x55\xaa" and image[446 + 4] == 0x0C
    if mbr:
        offset = struct.unpack_from("<I", image, 446 + 8)[0] * SECTOR
    info: dict[str, object] = {
        "mbr": mbr,
        "partition_offset_bytes": offset,
        "bytes_per_sector": struct.unpack_from("<H", image, offset + 11)[0],
        "sectors_per_cluster": image[offset + 13],
        "reserved_sectors": struct.unpack_from("<H", image, offset + 14)[0],
        "num_fats": image[offset + 16],
        "total_sectors": struct.unpack_from("<I", image, offset + 32)[0],
        "fat_sectors": struct.unpack_from("<I", image, offset + 36)[0],
        "root_cluster": struct.unpack_from("<I", image, offset + 44)[0],
        "fs_type": image[offset + 82 : offset + 90].decode("ascii", "replace").strip(),
        "boot_signature": image[offset + 510 : offset + 512].hex(),
    }
    fat_offset = offset + RESERVED * SECTOR + FILE_CLUSTER * 4
    fat = struct.unpack_from("<I", image, fat_offset)[0]
    info["file_chain_entry"] = f"0x{fat:08x}"
    return info


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build FAT32 anomaly images.")
    parser.add_argument("--out", type=Path, help="Output image path.")
    parser.add_argument("--size-mb", type=int, default=64)
    parser.add_argument("--anomaly", choices=sorted(ANOMALIES), default="none")
    parser.add_argument("--mbr", action="store_true", help="Wrap in an MBR partition table.")
    parser.add_argument("--mbr-start", type=int, default=8192)
    parser.add_argument("--list", action="store_true", help="List anomalies.")
    parser.add_argument("--describe", type=Path, help="Describe an image.")
    args = parser.parse_args(argv)

    if args.list:
        for name, note in sorted(ANOMALIES.items()):
            print(f"{name:20} {note}")
        return 0
    if args.describe:
        info = describe(args.describe.read_bytes())
        for key, value in info.items():
            print(f"{key}: {value}")
        return 0
    if not args.out:
        parser.error("--out is required unless --list or --describe is used")

    image = build_image(
        args.size_mb, args.anomaly, mbr=args.mbr, mbr_start=args.mbr_start
    )
    args.out.write_bytes(image)
    print(f"wrote {args.out} ({len(image)} bytes, anomaly={args.anomaly})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
