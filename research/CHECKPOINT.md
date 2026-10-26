# Checkpoint

Last updated: 2026-10-26

## Current state

- Research snapshot: **2026-10-26**.
- Repository: `Tirexisso1010o/TX10LED`, branch `main`, pre-existing commit `8e828a8`.
- Target: Nintendo Switch OLED, user-reported `HEG-001`, firmware `23.0.1`.
- Console state: unchanged by this project.
- Hardware validation: **pending**. No USB observation has been recorded.
- Publication: **not pushed**. Local changes only until the remote, branch, and publication scope are confirmed.
- Focus: potential software-only jailbreak research and the read-only USB tool.

## Verified conclusions

1. Atmosphère 1.12.1 and hekate v6.5.4 support firmware 23.0.1. This is firmware compatibility.
2. The OLED uses Mariko/Tegra X1+ hardware. Fusée Gelée (`CVE-2018-6242`) is disproven for this hardware.
3. Patched/Mariko consoles can enter RCM but cannot receive a payload.
4. No publicly documented, reproducible software-only path to Atmosphère was found for an unmodified OLED on 23.0.1. This is an absence-of-documented-method finding, not proof of impossibility.
5. The documented route is a hardware modchip, which is out of scope.
6. `ns2jb` is a real software-only userland/sysmodule chain on Switch 2 23.0.1. The author says it was also tested on Switch 1, but it is not packaged for Switch 1, the model/firmware are not stated, and it does not provide kernel, bootROM, CFW, or persistence. It is the closest public lead, not a path to Atmosphère.
7. CVE-2026-82079 is a local-wireless stack overflow fixed in 23.0.0; the target is reported on 23.0.1. No public exploit code was found.
8. PegaSwitch (early browser) and Caffeine (patched Erista 4.1.0) are historical and do not apply to the target.
9. Switchbrew's 23.0.0 page documents fixes for `bsdsocket`, `audio`, and `ldn`; 23.0.1 lists a stability fix and an `sdb`/SystemVersion update, with an unfilled security-flaw placeholder.

## Completed work

- Source register (30 sources), evidence ledger (E-001–E-036), and compatibility matrix.
- Detailed entry-point matrix (`research/entry-points.json`) covering 10 surfaces and 5 public leads.
- Readable entry-point analysis (`docs/ENTRY-POINTS.md`).
- README framing the project as a potential-jailbreak investigation plus a read-only USB tool.
- Compatibility narrative with the `ns2jb` distinction.
- Known-limitations update covering `UNKNOWN` surfaces, the 23.0.1 placeholder, and the userland-to-boot gap.
- Standard-library research validator (`scripts/validate_research.py`).
- PTP response-code correction (`0x2001`) in `docs/USB_INTEGRATION.md`.
- Removed the dead `render_research.py` permission rule from `opencode.json`; deny rules remain last in the ordered list.
- Read-only USB inspection package and CLI.
- Repository-local `.venv` with `pyusb` 1.3.1 installed via `pip install -e '.[ptp]'`.
- `ptp-info --dry-run` verified: it exits with code `2` and opens nothing when no PTP device is connected.

## Validation run

```bash
python3 scripts/validate_research.py
.venv/bin/python -m switch_usb_probe doctor
```

Current result:

```text
Research data OK: 30 sources, 36 evidence entries, 10 entry-point surfaces, 5 leads, 18 matrix rows, 5 USB modes.
```

`doctor` reports `pyusb OK`, `libusb OK`, `ptpcamerad not running`, and 0 connected USB devices.

## Pending approvals

- Connect the console in PTP mode and confirm its identity before opening it.
- Confirm the remote, branch, and publication scope before the first push.
- Any console state change, firmware update, RCM entry, or payload attempt requires explicit approval and is currently not authorized.

## Pending work

- USB test suite and fixtures.
- Generated Markdown renderer and CI workflow.
- PTP hardware validation once the console is connected and its identity is confirmed.

## Unresolved questions

- Does the target console report `HEG-001` and firmware `23.0.1` in Settings?
- What is the serial prefix (three characters only)?
- Has the console ever been opened or modchipped?
- Does the OLED enumerate as `057e:201d` in Copy to PC via USB mode?
- Does the OLED answer PTP `GetDeviceInfo` without `OpenSession`, or does it require `--allow-session`?
- What Switch 1 model and firmware did the `ns2jb` author test, and is a Switch 1 package planned?
- Is there an independent OLED/Mariko 23.0.1 reproduction of any userland/sysmodule chain?

## Next safe action

Run the research validator and the local CLI checks. Then ask the user for:

1. the manual console details (model, firmware confirmation without updating, serial prefix only, and whether it has ever been opened or modchipped);
2. confirmation of the remote, branch, and publication scope before the first push.

The `.venv` and `pyusb` install was approved and completed. Do not update firmware, enter RCM, inject a payload, or change console state.
