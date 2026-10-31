# H-013 — SD-card free-trigger test plan

> **Status: prepared, not run.** No card has been written and the console has not been touched. This plan needs explicit approval for the card write and the console run.

## Purpose

`H-013` asks whether a free system applet can pass a user-controlled path containing a `..\` component to `fs` `GetEntryType`, triggering the same `Path::Normalize` overflow described in `ns2jb` **without SmileBASIC**. A positive result would confirm the bug is reachable on the target `23.0.1` build; it would still be a crash until the Switch 1 `fs` binary and heap-grooming exploit are available.

The narrowed goal is fs-level native code execution, so a confirmed free trigger is worth knowing even though it is not code execution by itself.

## Why the image is built this way

The album's normal path is too short: `NINTENDO/ALBUM/YYYY/MM/DD/<file>` plus a 255-character filename is below the `0x301`-byte `Path::Normalize` buffer. The test image therefore uses a deep Unicode tree:

```
NINTENDO/ALBUM/<..\ + 167 CJK>/<170 CJK>/<170 CJK>.jpg
```

- The first component starts with `..\`, the parent-directory-plus-backslash pattern from the write-up.
- The full path is **532 characters / 1546 UTF-8 bytes**, well above `0x301` (769 bytes).
- The image also contains the owner's **real Exif screenshot** at `NINTENDO/ALBUM/2026/10/27` as the control, so the album can show a known-good file and prove the card mounted. A synthetic JPEG without Exif was ignored by the Album (`E-075`, `E-076`), so the control must be the real screenshot.
- A **benign control image** has the same tree and path length, but the first component starts with `AA\` instead of `..\`. If the crafted image crashes and the benign one does not, the `..\` component is implicated.

The paths are encoded as FAT32 long file names; the FS path is assumed to be UTF-8. If the console rejects the Unicode names or does not traverse the crafted directory, the test is negative for this surface, not evidence that the bug is absent.

## Images

Generate both images with MBR wrapping (the D8 card used an MBR at LBA 8192), using the owner's real screenshot as the control:

```sh
python3 scripts/sdcard_lab.py --mbr --stamp 0045 \
  --jpeg scripts/assets.local/real.jpg \
  --valid-name '2026102700452400-57B4628D2267231D57E0FC1078C0596D.jpg' \
  --anomaly album_unicode_parent_backslash --out h013-crafted.img
python3 scripts/sdcard_lab.py --mbr --stamp 0045 \
  --jpeg scripts/assets.local/real.jpg \
  --valid-name '2026102700452400-57B4628D2267231D57E0FC1078C0596D.jpg' \
  --anomaly album_unicode_benign_path --out h013-benign.img
```

Prepared dry-run images (not committed; regenerate with the commands above):

| Image | Anomaly | Size | SHA-256 |
|---|---|---|---|
| `h013-crafted.img` | `album_unicode_parent_backslash` | 71,303,168 bytes | `388a9549157a4cd92f28e7b3633a9ce247013cd2e9ba4d84873ad3f855520377` |
| `h013-benign.img` | `album_unicode_benign_path` | 71,303,168 bytes | `818fee2774c009822c4972fcd649c0293f4cff0636d5b72c73e661678b6de4f0` |

> **Revision note.** The first prepared benign image was missing the `NINTENDO/ALBUM` level; the second used a synthetic control that the Album ignored because it lacks Exif. Neither produced a console result. The SHA-256 values above use the corrected tree and the owner's real Exif screenshot (`MD5 ffa6936426b64d3c1689a3352915d80d`) as the control. Verify the images by mounting them read-only before writing.

Verify either image read-only before writing:

```sh
python3 scripts/sdcard_lab.py --describe h013-crafted.img
```

## Card write

The write is destructive and must be run by the owner, against the sacrificial card only. Run the **benign** image first; only after a clean benign run should you write the crafted image:

```sh
python3 scripts/sdcard_write.py --device /dev/diskN --image h013-benign.img
# inspect the printed plan, then re-run with --write
python3 scripts/sdcard_write.py --device /dev/diskN --image h013-benign.img --write

# only after the benign run is clean:
python3 scripts/sdcard_write.py --device /dev/diskN --image h013-crafted.img
python3 scripts/sdcard_write.py --device /dev/diskN --image h013-crafted.img --write
```

The writer refuses `disk0`, internal disks, partitions, and cards smaller than the image. Do not use the console's primary card.

## Console run

### 1. Benign control first

1. Write `h013-benign.img` to the sacrificial card and insert it.
2. Open **Album** and confirm the control image under `2026/10/27` appears. If it does not, the card or album setup failed; abort.
3. Wait 60 seconds without touching the console. If the album displays the long `AA\<CJK>` folder, open it once; otherwise leave the album on the control image.
4. Record any error code, black screen, hang, reboot, or crash report.
5. Reboot, remove the card, and restore the original card.

If the benign image crashes or hangs, **stop**. The long Unicode path itself is implicated; do not run the crafted image, and record the result as a long-path/parser issue rather than a `..\` trigger.

### 2. Crafted image

Only if the benign run is clean:

1. Write `h013-crafted.img` to the sacrificial card and insert it.
2. Open **Album** and confirm the same control image appears.
3. Wait 60 seconds without touching the console. If the album displays the crafted `..\<CJK>` folder, open it once; otherwise leave the album on the control image.
4. Record any error code, black screen, hang, reboot, or crash report.
5. Reboot, remove the card, and restore the original card.

## Abort and recovery

Abort immediately if the console hangs for more than 60 seconds, shows a black screen or an error screen, reboots repeatedly, or the card becomes hot.

Recovery: power off, remove the card, wait 10 seconds, power on. Do not factory-reset or initialize the console. The card is sacrificial; console data is not written by this test.

## Interpretation

| Result | Meaning |
|---|---|
| Control visible; crafted clean; benign clean | The album did not traverse the crafted path, rejected it, or the path did not reach `GetEntryType`. Negative for this surface; H-013 remains open for the browser/download route. |
| Crafted crashes/hangs; benign clean | Possible `..\` trigger. Record the behavior and do not repeat without a new hypothesis. The next requirement is the Switch 1 `fs` binary and the heap-grooming exploit. |
| Crafted and benign both crash | Likely a long-path/Unicode issue, not a `..\`-specific trigger. Record as a length/parser result, not a confirmed trigger. |
| Control not visible | Card or album setup failure. Abort; no conclusion. |

A crash is **not** fs-level code execution. It would confirm reachability only.

## Safety and authorization

- No firmware, keys, or SmileBASIC are used.
- No malformed `fs` commands are sent; the test only places a crafted filename/path on a sacrificial FAT32 card.
- The console is not modified; the risk is an applet or `fs` hang, recoverable by a reboot.
- The card write is destructive to the sacrificial card and requires owner approval.
- **No run is authorized by this document.** The test needs a separate explicit approval naming the image SHA-256 and the console session.

## References

- `H-013`, `H-004` — hypotheses.
- `E-045` — the `ns2jb` `Path::Normalize` description.
- `E-114`, `E-118` — the Switch 2-only package and the local `fs` artifact gap.
- `docs/PORTABILITY.md` — why the `fs` binary remains the gate.
