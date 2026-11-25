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


class AlbumTreeTests(unittest.TestCase):
    def _offsets(self):
        layout = lab.layout_for(64)
        data = layout.data_start * lab.SECTOR
        return data, data + lab.SECTOR, data + 2 * lab.SECTOR

    def test_album_directory_points_out_of_range(self) -> None:
        image = lab.build_image(64, "album_dir_oob")
        root, nintendo, _ = self._offsets()
        self.assertEqual(image[root : root + 11], b"NINTENDO   ")
        self.assertEqual(image[nintendo : nintendo + 11], b"ALBUM      ")
        high = struct.unpack_from("<H", image, nintendo + 20)[0]
        low = struct.unpack_from("<H", image, nintendo + 26)[0]
        self.assertEqual((high << 16) | low, 0x0FFFFFF0)

    def test_long_names_match_the_console_pattern(self) -> None:
        image = lab.build_image(64, "album_date_file_oob")
        layout = lab.layout_for(64)
        day = layout.data_start * lab.SECTOR + 5 * lab.SECTOR

        self.assertEqual(image[day + 11], 0x0F)
        self.assertEqual(image[day] & 0x40, 0x40)  # last LFN chunk stored first
        short1 = b"202610~1JPG"
        self.assertEqual(image[day + 160 : day + 171], short1)
        self.assertEqual(image[day + 160 + 26 : day + 160 + 28], struct.pack("<H", 8))

        short2 = b"202610~2JPG"
        self.assertEqual(image[day + 352 : day + 363], short2)
        high = struct.unpack_from("<H", image, day + 352 + 20)[0]
        low = struct.unpack_from("<H", image, day + 352 + 26)[0]
        self.assertEqual((high << 16) | low, 0x0FFFFFF0)

        checksum = lab._lfn_checksum(short1)
        self.assertEqual(image[day + 13], checksum)

    def test_date_tree_reaches_the_day_directory(self) -> None:
        image = lab.build_image(64, "album_date_file_oob")
        layout = lab.layout_for(64)
        data = layout.data_start * lab.SECTOR

        def at(cluster: int) -> int:
            return data + (cluster - 2) * lab.SECTOR

        chain = [(2, b"NINTENDO   ", 3), (3, b"ALBUM      ", 4), (4, b"2026       ", 5), (5, b"10         ", 6), (6, b"27         ", 7)]
        for cluster, name, target in chain:
            self.assertEqual(image[at(cluster) : at(cluster) + 11], name)
            low = struct.unpack_from("<H", image, at(cluster) + 26)[0]
            self.assertEqual(low, target)
        day = at(7)
        self.assertEqual(image[day + 11], 0x0F)  # first entry is a long-name record

    def test_album_file_points_out_of_range(self) -> None:
        image = lab.build_image(64, "album_file_oob")
        _, _, album = self._offsets()
        self.assertEqual(image[album : album + 11], b"OK      JPG")
        self.assertEqual(image[album + 32 : album + 43], b"TEST    JPG")
        high = struct.unpack_from("<H", image, album + 32 + 20)[0]
        low = struct.unpack_from("<H", image, album + 32 + 26)[0]
        self.assertEqual((high << 16) | low, 0x0FFFFFF0)


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


class LongDayFileTests(unittest.TestCase):
    def _image(self, anomaly: str) -> tuple[bytes, int]:
        image = lab.build_image(64, anomaly)
        layout = lab.layout_for(64)
        return image, layout.data_start * lab.SECTOR

    def test_long_file_path_exceeds_the_fs_buffer(self) -> None:
        for name in (lab.LONG_FILE_PARENT, lab.LONG_FILE_BENIGN):
            self.assertEqual(len(name), 255)
            path = "NINTENDO/ALBUM/2026/10/27/" + name
            self.assertGreater(len(path.encode("utf-8")), 0x301)

    def test_day_directory_spans_two_clusters(self) -> None:
        image, data = self._image("album_date_file_long_parent")
        fat = lab.RESERVED * lab.SECTOR
        fat7 = struct.unpack_from("<I", image, fat + 7 * 4)[0] & 0x0FFFFFFF
        fat8 = struct.unpack_from("<I", image, fat + 8 * 4)[0] & 0x0FFFFFFF
        self.assertEqual(fat7, 8)
        self.assertEqual(fat8, lab.EOC)

        def at(cluster: int) -> int:
            return data + (cluster - 2) * lab.SECTOR

        # The control entry is first (six 32-byte entries for the real name),
        # then the 20 LFN entries and short entry for the crafted name.
        day = image[at(7) : at(7) + 2 * lab.SECTOR]
        self.assertEqual(day[11], 0x0F)
        self.assertEqual(day[0] & 0x40, 0x40)
        crafted = 192
        self.assertEqual(day[crafted + 11], 0x0F)
        self.assertEqual(day[crafted] & 0x40, 0x40)
        short = crafted + 20 * 32
        self.assertEqual(day[short + 11], 0x20)
        low = struct.unpack_from("<H", day, short + 26)[0]
        high = struct.unpack_from("<H", day, short + 20)[0]
        count = (len(lab.JPEG) + lab.SECTOR - 1) // lab.SECTOR
        self.assertEqual((high << 16) | low, 9 + count)

    def test_parent_and_benign_prefixes_differ(self) -> None:
        parent, data = self._image("album_date_file_long_parent")
        benign, _ = self._image("album_date_file_long_benign")

        def first_chars(image: bytes) -> bytes:
            # The crafted LFN entries are stored last-chunk-first, so the
            # sequence-1 entry (the first 13 filename chars) is the 20th
            # LFN entry, immediately before the short entry at offset 832.
            start = data + 5 * lab.SECTOR + 800
            return image[start + 1 : start + 1 + 6]

        parent_prefix = first_chars(parent)
        benign_prefix = first_chars(benign)
        self.assertEqual(parent_prefix, b".\x00.\x00\\\x00")
        self.assertEqual(benign_prefix, b"A\x00A\x00\\\x00")


class UnicodePathTests(unittest.TestCase):
    def test_path_exceeds_the_fs_buffer(self) -> None:
        path = (
            "/NINTENDO/ALBUM/"
            + lab.UNICODE_DIR_1
            + "/"
            + lab.UNICODE_DIR_2
            + "/"
            + lab.UNICODE_FILE
        )
        self.assertGreater(len(path.encode("utf-8")), 0x301)
        self.assertTrue(lab.UNICODE_DIR_1.startswith("..\\"))

    def test_benign_path_has_same_length_without_parent(self) -> None:
        crafted = (
            "/NINTENDO/ALBUM/"
            + lab.UNICODE_DIR_1
            + "/"
            + lab.UNICODE_DIR_2
            + "/"
            + lab.UNICODE_FILE
        )
        benign = (
            "/NINTENDO/ALBUM/"
            + lab.UNICODE_BENIGN_DIR_1
            + "/"
            + lab.UNICODE_DIR_2
            + "/"
            + lab.UNICODE_FILE
        )
        self.assertEqual(len(crafted.encode("utf-8")), len(benign.encode("utf-8")))
        self.assertTrue(crafted.split("/")[3].startswith("..\\"))
        self.assertFalse(benign.split("/")[3].startswith("..\\"))

    def test_benign_image_builds(self) -> None:
        image = lab.build_image(64, "album_unicode_benign_path")
        layout = lab.layout_for(64)
        data = layout.data_start * lab.SECTOR
        short1 = data + 2 * lab.SECTOR + 32 + 14 * 32
        self.assertEqual(image[short1 + 11], 0x10)
        self.assertEqual(struct.unpack_from("<H", image, short1 + 26)[0], 5)

    def test_tree_points_at_the_crafted_entries(self) -> None:
        image = lab.build_image(64, "album_unicode_parent_backslash")
        layout = lab.layout_for(64)
        data = layout.data_start * lab.SECTOR

        def at(cluster: int) -> int:
            return data + (cluster - 2) * lab.SECTOR

        # NINTENDO/ALBUM at cluster 3 points to the contents at cluster 4.
        self.assertEqual(image[at(3) : at(3) + 11], b"ALBUM      ")
        self.assertEqual(image[at(3) + 11], 0x10)
        self.assertEqual(struct.unpack_from("<H", image, at(3) + 26)[0], 4)

        # Contents cluster 4: control year at 0, crafted LFN at 32, short at 480.
        self.assertEqual(image[at(4) : at(4) + 11], b"2026       ")
        self.assertEqual(image[at(4) + 11], 0x10)
        self.assertEqual(struct.unpack_from("<H", image, at(4) + 26)[0], 18)
        self.assertEqual(image[at(4) + 32 + 11], 0x0F)
        short1 = at(4) + 32 + 14 * 32
        self.assertEqual(image[short1 + 11], 0x10)
        self.assertEqual(struct.unpack_from("<H", image, short1 + 26)[0], 5)

        # First crafted directory at cluster 5 points to cluster 6.
        short2 = at(5) + 14 * 32
        self.assertEqual(image[short2 + 11], 0x10)
        self.assertEqual(struct.unpack_from("<H", image, short2 + 26)[0], 6)

        # Second crafted directory at cluster 6 holds the JPEG entry.
        short3 = at(6) + 14 * 32
        self.assertEqual(image[short3 + 11], 0x20)
        self.assertEqual(struct.unpack_from("<H", image, short3 + 26)[0], 7)
        self.assertEqual(struct.unpack_from("<I", image, short3 + 28)[0], len(lab.JPEG))

        # Control file at cluster 20: five LFN chunks, then the short entry.
        short4 = at(20) + 5 * 32
        self.assertEqual(image[short4 + 11], 0x20)
        self.assertEqual(struct.unpack_from("<H", image, short4 + 26)[0], 21)

        # FAT chains: crafted data 7..17, control data 21..31.
        self.assertEqual(struct.unpack_from("<I", image, FAT_OFFSET + 7 * 4)[0], 8)
        self.assertEqual(struct.unpack_from("<I", image, FAT_OFFSET + 17 * 4)[0], lab.EOC)
        self.assertEqual(struct.unpack_from("<I", image, FAT_OFFSET + 21 * 4)[0], 22)
        self.assertEqual(struct.unpack_from("<I", image, FAT_OFFSET + 31 * 4)[0], lab.EOC)


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
