# Checkpoint

Last updated: 2026-10-26

## Current state

- Research snapshot: **2026-10-26**.
- Repository: `Tirexisso1010o/TX10LED`, branch `main`, pre-existing commit `8e828a8`.
- Target: Nintendo Switch OLED, owner-confirmed `HEG-001`, firmware `23.0.1`, serial prefix `XTJ`, no modification history reported.
- Console state: unchanged by this project.
- Hardware validation: **PTP identity observation recorded** on 2026-10-26. The console enumerated as `057e:201d` and answered `GetDeviceInfo` without a session.
- Target identity: **PARTIALLY VERIFIED**. Firmware 23.0.1 and serial prefix XTJ are PTP-observed; the HEG-001 model number and no-modification history are owner-reported.
- Publication: pushed to `origin/main` at `d047ad3`. The GameShare research pass is committed separately; see `git log` for the latest commit.
- Focus: potential software-only jailbreak research, the GameShare receiver surface, and the read-only USB tool.

## Verified conclusions

1. Atmosphère 1.12.1 and hekate v6.5.4 support firmware 23.0.1. This is firmware compatibility.
2. The OLED uses Mariko/Tegra X1+ hardware. Fusée Gelée (`CVE-2018-6242`) is disproven for this hardware.
3. Patched/Mariko consoles can enter RCM but cannot receive a payload.
4. No publicly documented, reproducible software-only path to Atmosphère was found for an unmodified OLED on 23.0.1. This is an absence-of-documented-method finding, not proof of impossibility.
5. The documented route is a hardware modchip, which is out of scope.
6. `ns2jb` is a real software-only userland/sysmodule chain on Switch 2 23.0.1. It combines a 32-bit integer overflow in the SmileBASIC interpreter with a path-normalization buffer overflow in the `fs` sysmodule. The author says it was **tested on Switch 1 but not packaged**, and it does not provide kernel, bootROM, CFW, or persistence.
7. The packaged `ns2jb` demo requires SmileBASIC 4.4.9, system software 23.0.1, a Node.js 22+ host on the same network, and more than 20 MiB free in the SmileBASIC save. It is tethered and installs no CFW or persistence.
8. SmileBASIC 4 was delisted from the eShop in several regions after the `ns2jb` release, so the documented entry point is only available to people who already own it.
9. GameShare is handled on the receiving system by the **`splay` system applet**, added in 20.0.0. It uses `ldn` local wireless with `SetProtocol` value 3, receives a video stream, and accepts the game NACP and JPEG images during setup. At least some host data, including `AdvertiseData`, is ECC-verified.
10. Only a Switch 2 can host GameShare. A Switch 1/OLED can only receive, and only over local wireless. Nintendo states the feature cannot be used between two Switch 1/OLED/Lite systems.
11. `splay` holds `StreamPlaySaveData` (`FsAccessFlag` bit 47) and, on Switch 1 with 23.0.0+, access to `news:c` and `stpl:sys`. These are applet-level privileges.
12. **No public vulnerability, proof of concept, or exploit** was found for `splay`, the GameShare protocol, or its NACP/JPEG handling. The surface is `UNKNOWN`.
13. A full `splay` compromise would yield applet-level userland code execution, not kernel, bootROM, or Atmosphère.
14. Gezine claims a Switch 1/2 userland exploit that is not WebKit- or save-based and works offline across firmware versions. It is unreleased, has no public technical details, and is `UNVERIFIED`. Gezine also says SmileBASIC 4 is not strictly required, naming Artemis Engine and an undisclosed physical cartridge.
15. CVE-2026-82079 is a local-wireless stack overflow fixed in 23.0.0; the target is reported on 23.0.1. No public exploit code was found.
16. PegaSwitch (early browser) and Caffeine (patched Erista 4.1.0) are historical and do not apply to the target.
17. Switchbrew's 23.0.0 page documents fixes for `bsdsocket`, `audio`, and `ldn`; 23.0.1 lists a stability fix and an `sdb`/SystemVersion update, with an unfilled security-flaw placeholder.
18. Atmosphère is a boot-time CFW, so a software-only path needs **boot-stage execution** (stage 3), not only a userland or kernel primitive. Caffeine proves the category works on patched hardware: a warmboot exploit ran full CFW on patched Erista 4.0.0–4.1.0 without Fusée Gelée.
19. No public Mariko warmboot or pre-Horizon chain exists for modern firmware. Warmboot is package1 section 0, and Mariko package1 is signed and encrypted, so an equivalent would need a code bug in verified warmboot or TSEC code.
20. The `ns2jb` `fs` bug is a privilege-escalation stage, not an entry point: it is reached through an `IFileSystem` handle after the SmileBASIC overflow. Without stage 1 there is nothing to escalate from.
21. SmileBASIC 4 is download-only, so there is no physical cartridge route; the owner does not have it, and the delisting removes the purchase route in several regions.
22. Artemis Engine games can chain-load Lua from an edited save, but the public loader is documented for PS4 and Windows and yields game-script level, not native code. No Switch reproduction is documented.

## Completed work

- Source register (46 sources), evidence ledger (E-001–E-054), and compatibility matrix (24 rows).
- Detailed entry-point matrix (`research/entry-points.json`) covering 11 surfaces and 6 public leads, including `EP-011` GameShare/`splay` and `L-006`.
- Readable entry-point analysis (`docs/ENTRY-POINTS.md`) with a stage model, a GameShare section, bounds, and capability ceiling.
- Stage-by-stage gap analysis (`docs/GAP-ANALYSIS.md`) identifying boot-stage execution as the decisive missing link.
- README framing the project as a potential-jailbreak investigation plus a read-only USB tool, with GameShare in the short-version table and the surface table.
- Compatibility narrative with the `ns2jb` distinction and the GameShare receiver section.
- Known-limitations update covering GameShare, `ns2jb`'s unpackaged Switch 1 test, SmileBASIC delisting, Gezine's unreleased claim, `UNKNOWN` surfaces, the 23.0.1 placeholder, and the userland-to-boot gap.
- Decision-log entry recording GameShare as a surface, not a method.
- Standard-library research validator (`scripts/validate_research.py`).
- PTP response-code correction (`0x2001`) in `docs/USB_INTEGRATION.md`.
- Removed the dead `render_research.py` permission rule from `opencode.json`; deny rules remain last in the ordered list.
- Read-only USB inspection package and CLI.
- Manual target observation (`research/hardware-observations/2026-10-26-manual.json`): HEG-001, firmware 23.0.1, serial prefix XTJ, no modification history reported.
- PTP target observation (`research/hardware-observations/2026-10-26-ptp.json`): `057e:201d`, firmware 23.0.1, serial prefix XTJ, 10 operations, no session.
- Enumeration fallback fix: `system_profiler` returned no devices on macOS 26.3 while `ioreg` saw the console; `auto` now falls back on an empty result.
- Repository-local `.venv` with `pyusb` 1.3.1 installed via `pip install -e '.[ptp]'`.
- `ptp-info --dry-run` verified: it exits with code `2` and opens nothing when no PTP device is connected.

## Validation run

```bash
python3 scripts/validate_research.py
.venv/bin/python -m switch_usb_probe doctor
```

Current result:

```text
Research data OK: 46 sources, 54 evidence entries, 11 entry-point surfaces, 6 leads, 24 matrix rows, 5 USB modes.
```

PTP observation:

```text
Manufacturer: Nintendo
Model: Nintendo Switch
Device version: 23.0.1
Serial prefix: XTJ***
Operations supported: 10
Session opened: no
```

`doctor` reports `pyusb OK`, `libusb OK`, `ptpcamerad not running`, and 1 device via `ioreg` with a `system_profiler` empty-result warning.

## Pending approvals

- Any console state change, firmware update, RCM entry, payload attempt, GameShare host spoofing, or crafted-data send requires explicit approval and is currently not authorized.

## Pending work

- USB test suite and fixtures, including a regression test for the empty-`system_profiler` fallback.
- Generated Markdown renderer and CI workflow.
- PTP media transfer and file operations are out of scope; the identity probe is complete.

## Unresolved questions

- Does `DeviceInfo` ever distinguish OLED from LCD hardware, or is the model string always generic?
- What Switch 1 model and firmware did the `ns2jb` author test, and is a Switch 1 package planned?
- Is there an independent OLED/Mariko 23.0.1 reproduction of any userland/sysmodule chain?
- What does the GameShare ECC signature actually cover: only `AdvertiseData`, or setup metadata and stream data as well?
- Is the `splay` NACP and JPEG handling reachable before any user confirmation on the receiver, or only after an explicit join?
- Did 23.0.1 change `splay` beyond the 23.0.0 NPDM additions, and are there unpublished splay fixes?

## Next safe action

The PTP identity observation is complete and recorded. The console is unchanged. GameShare is documented as a surface with no public vulnerability. Continue monitoring public sources for:

1. a packaged Switch 1 version of the `ns2jb` chain with a stated model and firmware;
2. a public chain connecting a userland/sysmodule primitive to kernel or bootROM access on Mariko;
3. a public 23.0.1-specific browser, local-wireless, or Bluetooth chain;
4. public GameShare/`splay` protocol research or a `jpegdec`/NACP parsing advisory;
5. any public Mariko warmboot, package1, or pre-Horizon code-execution research for modern firmware, which is the decisive missing stage.

Do not update firmware, enter RCM, inject a payload, spoof a GameShare host, send crafted data to the console, or change console state.
