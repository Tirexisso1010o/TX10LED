# Known Limitations

This document records what the research and tooling cannot establish. It is part of the evidence, not a disclaimer appended at the end.

## Scope limitations

- **Public sources only.** The conclusion is based on public releases, documentation, source code, and maintained guides reviewed on 2026-10-26. It is not an audit of private research, unpublished exploits, or every firmware binary.
- **No proof of impossibility.** "No publicly documented software-only path" is not the same as "no software-only path can exist". The ledger labels the existence of an undisclosed exploit `UNKNOWN`.
- **Hardware family, not a laboratory teardown.** The OLED is identified as Mariko/Tegra X1+ from public hardware documentation. This project has not opened the console or inspected its board.
- **Partially observed target identity.** The owner manually confirmed the model `HEG-001`, firmware `23.0.1`, serial prefix `XTJ`, and no-modification history on 2026-10-26. PTP `GetDeviceInfo` on the same date observed firmware `23.0.1` and serial prefix `XTJ***`. The `HEG-001` model number and the no-modification history remain owner-reported; PTP reports a generic `Nintendo Switch` model and cannot detect a modchip.
- **No exploit development.** The project does not attempt to find, develop, or validate a new vulnerability. It records what is publicly documented.

## Firmware and release limitations

- Atmosphère 1.12.1's release notes explicitly add support for firmware **23.0.0** and describe 23.0.0 changes. Firmware **23.0.1** support is established by the maintained NH Switch Guide compatibility checker and community issue discussion. The distinction is recorded in E-001.
- A new Atmosphère or hekate release can change firmware compatibility without changing the entry-point picture.
- A firmware update can burn eFuses and is not a reversible troubleshooting step.
- Open issues and regressions can exist even when a firmware is listed as supported. Firmware support is not a guarantee of bug-free operation.
- Switchbrew's 23.0.1 page has an unfilled `Security flaws fixed` placeholder. The absence of a listed security fix is not proof that 23.0.1 contains none; the official change-log describes a stability update.

## Entry-point limitations

- **`ns2jb` is not a target-specific result.** It is packaged for Switch 2 on 23.0.1. The author says the chain was also tested on Switch 1, but the model and firmware are not stated and the Switch 1 version is not packaged. No OLED/Mariko 23.0.1 test is documented. It does not provide kernel, bootROM, CFW, or persistence.
- **`UNKNOWN` surfaces are not cleared.** Browser/WebKit, local wireless, Bluetooth, game saves/cartridges, GameShare/`splay`, and kernel/TrustZone remain `UNKNOWN` where no public 23.0.1 chain was found. A public flaw list can lag private research.
- **A fixed flaw is not the whole surface.** CVE-2026-82079 is fixed in 23.0.0, but that does not prove the local-wireless stack has no other vulnerabilities. The same applies to the 23.0.0 `bsdsocket` and `audio` fixes.
- **Historical entry points are not current ones.** PegaSwitch targets early firmware and the Fake News entry point; Caffeine targets patched Erista 4.1.0. Neither applies to Mariko/OLED on 23.0.1.
- **Public exploit availability is not established.** CVE-2026-82079's CVE record contains no exploit code, and the linked HackerOne report was not accessible in this review. The ledger labels exploit availability `UNKNOWN`.
- **A userland primitive is not a boot chain.** Even a successful userland/sysmodule compromise would still need a kernel or bootROM stage to launch Atmosphère persistently.
- **Boot-stage execution is the decisive missing link.** Atmosphère replaces verified system modules, so it must run at or before boot. Caffeine shows a warmboot exploit can do this on patched Erista 4.0.0–4.1.0, but no Mariko equivalent is public for modern firmware. Warmboot is package1 section 0, and Mariko package1 is signed and encrypted, so a Mariko path needs a code bug in verified warmboot or TSEC code.
- **The 23.0.1 source console is no longer available.** The existing 23.0.1 NCA dump and keys came from a modded 23.0.1 console the owner no longer has. The remaining modded console runs 22.0.0, so it cannot supply a 23.0.1 BOOT0/package1 image or key generation `0x17` keys. A 22.0.0 dump could support comparative analysis only, and the owner has chosen to leave that console untouched, so no such dump is being pursued.
- **`ns2jb`'s `fs` bug is not an entry point.** It is a privilege-escalation stage reached through an `IFileSystem` handle after the SmileBASIC overflow. A Switch 1 package would still need the SmileBASIC trigger and would still not reach boot stage.
- **The save-based Lua lead is not native code.** Artemis Engine games can chain-load Lua from an edited save, but the public loader is documented for PS4 and Windows; no Switch reproduction is documented, and game-script execution is not native code execution.
- **GameShare is a surface, not a vulnerability.** `splay` is a documented receiver-side parser fed by a remote host, but no public vulnerability, proof of concept, or exploit was found for it, the GameShare protocol, or its NACP/JPEG handling. The claim that it transfers no executable code is an inference from "video streaming is used", not a published protocol guarantee.
- **GameShare reception is proximity-bound and one-directional.** Nintendo documents that only a Switch 2 can host and that Switch 1 receivers use local wireless only. Attacking the target through this surface would therefore require controlling a Switch 2 or spoofing a host, and no public spoofing method exists.
- **`D10` Phases 0–2 Batch 1/2 and Phase 3 are baselines.** Phase 0 verified the APs and host tooling. Phase 1 confirmed association, the WPA2 pairwise handshake, DHCP, and DNS on the console, but the AP had no NAT, so Test Connection failed at the internet step with `2110-3128`; no TLS endpoint was reached. Phase 2 Batch 1 sent the control and `W-01`–`W-08`; there was no crash, reboot, hang, or new error, but `W-06` (DS Parameter IE length 3) showed shorter association lifetimes (7.3 s and 15.4 s versus 35.4 s for the control). Phase 2 Batch 2 sent the control and `W-09`–`W-14`; there was again no crash, reboot, hang, or new error, but `W-09` (Vendor IE length 0) showed a 14.7 s lifetime versus the 35.6 s control. These are behavioral leads, not memory-safety findings. Phase 3 control E-C completed the WPA2 handshake and three group rekeys; Batch 1 sent `E-01`–`E-08` and Batch 2 sent `E-09`–`E-14`, each one frame per association, all accepted, with the station associated at 10 s and lifetimes 35.0–35.5 s; no crash or new error. The hand-built EAPOL frames carried a zero or invalid MIC, so this is a clean negative for the tested fields, not proof that the deeper parser was reached. The same-phy monitor interface on `rtw88_8822bu` did not capture the AP's own frames, so management-frame attribution must use hostapd debug logs and an independent scan. The console may ignore duplicate AP beacons, so the batches do not prove every malformed IE reached the parser.
- **GameShare's authentication coverage is unknown.** ECC signature verification is documented for some host data, including `AdvertiseData`, but public sources do not state how much of the session it covers. Do not assume the stream is authenticated or unauthenticated.
- **`ns2jb`'s Switch 1 test is not a Switch 1 package.** The author says the chain was tested on Switch 1 but has not packaged it. Testing does not establish that the `fs` path-normalization bug is present on Switch 1 23.0.1, and the model and firmware are unstated.
- **SmileBASIC 4 availability is volatile.** The documented `ns2jb` entry point is version-locked to 4.4.9 and was delisted from the eShop in several regions. Store status is region-dependent and changes; a previously purchased copy is not a generally reproducible prerequisite.
- **Gezine's userland claim is unreleased.** A Switch 1/2 non-WebKit, non-save userland exploit was claimed publicly in July 2026, but no code, advisory, technical write-up, or independent reproduction was found. It cannot be treated as a method, and it would not by itself provide kernel, bootROM, or Atmosphère.
- **The entry-point matrix records public documentation, not absolute exploitability.** `DISPROVEN` means the known public method is patched or the documented surface does not execute code; it does not prove that no private method exists.

## USB limitations

- The target OLED's enumeration as `057e:201d` and its `GetDeviceInfo` response were observed on 2026-10-26. That is one console and one observation, not a general OLED compatibility proof. `system_profiler` returned no devices on that host; the tool fell back to `ioreg`.
- PTP behavior is documented by reverse engineering and can vary by firmware revision.
- The PTP interface may be claimed by `ptpcamerad` or another macOS process. The tool reports a busy device rather than killing the process.
- A PTP `DeviceInfo` response can be spoofed by modified firmware. It is an observation, not an integrity attestation.
- Stock USB does not expose a shell, ADB, firmware-query service, or general-purpose remote-control interface.
- USB enumeration cannot establish exploitability, boot state, CFW access, or NAND contents.
- `system_profiler` and `ioreg` output formats are macOS implementation details and may change across releases.
- The tool does not support Windows or Linux enumeration backends. The research data is platform-independent, but the CLI's enumeration path is macOS-first.

## Research-process limitations

- Search results can be incomplete. A source that was not indexed, not public, or not in the reviewed languages could change a conclusion.
- The source register records snapshots, not byte-for-byte archives. Links can rot or change after the retrieval date.
- Community guides are maintained by volunteers. They are high-quality secondary sources, not Nintendo statements.
- The validator checks schema, cross-references, summary counts, and high-confidence secret patterns. It cannot prove that a prose claim is true.
- The test suite uses mocked devices. It verifies parsing and safety behavior, not real USB firmware behavior.

## Safety and legal limitations

- Modchip installation is out of scope and carries warranty, safety, and bricking risks.
- Console modification may affect warranty coverage and may violate service terms or local law.
- This repository does not provide legal advice.
- The project does not authorize firmware changes, NAND operations, or payload injection.

## What would improve confidence

- A maintained source that documents an OLED-specific PTP product ID or behavior, or a way for `DeviceInfo` to distinguish OLED from LCD.
- Independent reproduction of the PTP observation on a second OLED, or a maintained note that the `DeviceInfo` model string is always generic.
- Independent reproduction of the compatibility conclusion on another OLED.
- A packaged, reproducible Switch 1 version of the `ns2jb` chain, with the model and firmware identified.
- An independent OLED/Mariko 23.0.1 test of a userland/sysmodule chain.
- A public chain connecting a userland/sysmodule primitive to kernel or bootROM access on Mariko.
- A public 23.0.1-specific browser, local-wireless, or Bluetooth chain.
- A public technical description of the GameShare/splay protocol, including what its ECC signatures cover and how NACP and JPEG data are validated.
- A public vulnerability or proof of concept in `splay` or a service it drives, combined with a Mariko kernel or bootROM stage.
- A public, reproducible entry point that changes the software-only conclusion. If one appears, the matrix and evidence ledger must be updated rather than patched with an unsupported claim.
