"""Tests for the FAT32 anomaly generator and the write safety gate."""

from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lab = load("sdcard_lab", ROOT / "scripts" / "sdcard_lab.py")
writer = load("sdcard_write", ROOT / "scripts" / "sdcard_write.py")

FAT_OFFSET = lab.RESERVED * lab.SECTOR
FILE_FAT_ENTRY = FAT_OFFSET + lab.FILE_CLUSTER * 4
DIR_OFFSET = (lab.RESERVED + 2 * lab.layout_for(64).fat_sectors) * lab.SECTOR


class LayoutTests(unittest.TestCase):
    def test_layout_is_self_consistent(self) -> None:
        layout = lab.layout_for(64)
        self.assertGreaterEqual(layout.fat_sectors, 1)
        self.assertGreater(layout.clusters, 0)
        self.assertEqual(
            layout.data_start,
            lab.RESERVED + lab.NUM_FATS * layout.fat_sectors,
        )

    def test_control_image_is_valid(self) -> None:
        image = lab.build_image(64, "none")
        info = lab.describe(image)
        self.assertEqual(info["fs_type"], "FAT32")
        self.assertEqual(info["boot_signature"], "55aa")
        self.assertEqual(info["sectors_per_cluster"], 1)
        self.assertEqual(info["file_chain_entry"], "0x0fffffff")
        self.assertEqual(image[510:512], b"\x55\xaa")


class MbrTests(unittest.TestCase):
    def test_mbr_layout_matches_the_card(self) -> None:
        fs = lab.build_image(64, "none")
        image = lab.build_image(64, "none", mbr=True)
        self.assertEqual(len(image), 8192 * lab.SECTOR + len(fs))
        self.assertEqual(image[510:512], b"\x55\xaa")
        self.assertEqual(image[446 + 4], 0x0C)
        self.assertEqual(struct.unpack_from("<I", image, 446 + 8)[0], 8192)
        self.assertEqual(
            struct.unpack_from("<I", image, 446 + 12)[0], len(fs) // lab.SECTOR
        )
        offset = 8192 * lab.SECTOR
        self.assertEqual(image[offset + 510 : offset + 512], b"\x55\xaa")
        self.assertEqual(image[offset + 82 : offset + 90], b"FAT32   ")
        self.assertEqual(struct.unpack_from("<I", image, offset + 28)[0], 8192)

    def test_describe_finds_the_partition(self) -> None:
        info = lab.describe(lab.build_image(64, "none", mbr=True))
        self.assertTrue(info["mbr"])
        self.assertEqual(info["partition_offset_bytes"], 4194304)
        self.assertEqual(info["fs_type"], "FAT32")


class AnomalyTests(unittest.TestCase):
    def test_cluster_oob_points_beyond_the_volume(self) -> None:
        image = lab.build_image(64, "cluster_oob")
        self.assertEqual(struct.unpack_from("<I", image, FILE_FAT_ENTRY)[0], 0x0FFFFFF0)

    def test_fat_loop_points_at_itself(self) -> None:
        image = lab.build_image(64, "fat_loop")
        self.assertEqual(
            struct.unpack_from("<I", image, FILE_FAT_ENTRY)[0], lab.FILE_CLUSTER
        )

    def test_dir_size_huge(self) -> None:
        image = lab.build_image(64, "dir_size_huge")
        self.assertEqual(struct.unpack_from("<I", image, DIR_OFFSET + 28)[0], 0xFFFFFFFF)

    def test_dir_cluster_oob(self) -> None:
        image = lab.build_image(64, "dir_cluster_oob")
        high = struct.unpack_from("<H", image, DIR_OFFSET + 20)[0]
        low = struct.unpack_from("<H", image, DIR_OFFSET + 26)[0]
        self.assertEqual((high << 16) | low, 0x0FFFFFF0)

    def test_bpb_spc_zero(self) -> None:
        image = lab.build_image(64, "bpb_spc_zero")
        self.assertEqual(image[13], 0)

    def test_lfn_bad_marker(self) -> None:
        image = lab.build_image(64, "lfn_bad")
        self.assertEqual(image[DIR_OFFSET + 11], 0x0F)
        self.assertEqual(image[DIR_OFFSET + 13], 0xFF)

    def test_two_fats_mismatch(self) -> None:
        layout = lab.layout_for(64)
        image = lab.build_image(64, "two_fats_mismatch")
        second = FAT_OFFSET + layout.fat_sectors * lab.SECTOR + lab.FILE_CLUSTER * 4
        self.assertEqual(struct.unpack_from("<I", image, FILE_FAT_ENTRY)[0], 0x0FFFFFFF)
        self.assertEqual(struct.unpack_from("<I", image, second)[0], 0x0FFFFFF0)


class WriteGateTests(unittest.TestCase):
    def test_refuses_disk0(self) -> None:
        with self.assertRaises(writer.UnsafeTarget):
            writer.validate("/dev/disk0", 1, {"Internal": False, "Whole": True})

    def test_refuses_internal_disk(self) -> None:
        with self.assertRaises(writer.UnsafeTarget):
            writer.validate("/dev/disk4", 1, {"Internal": True, "Whole": True})

    def test_refuses_partition(self) -> None:
        with self.assertRaises(writer.UnsafeTarget):
            writer.validate("/dev/disk4", 1, {"Internal": False, "Whole": False})

    def test_refuses_small_disk(self) -> None:
        with self.assertRaises(writer.UnsafeTarget):
            writer.validate(
                "/dev/disk4", 100, {"Internal": False, "Whole": True, "TotalSize": 50}
            )

    def test_accepts_removable_whole_disk(self) -> None:
        writer.validate(
            "/dev/disk4",
            100,
            {"Internal": False, "Whole": True, "TotalSize": 1000},
        )


if __name__ == "__main__":
    unittest.main()
