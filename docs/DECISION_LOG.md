# Decision Log

Decisions are dated and recorded with the reason and the alternatives considered. A decision can be revisited when new evidence appears; the log should then record the change rather than silently rewriting the old entry.

## 2026-10-26 — Keep the existing `TX10LED` repository

**Decision:** Use the existing public repository `Tirexisso1010o/TX10LED` and its `main` branch. The project title in the README is "Switch OLED Atmosphère Research & USB Assistant".

**Reason:** The repository already exists, is public, and its description matches the research mission. Preserving the remote and history avoids a disruptive rename and keeps the existing commit.

**Alternatives considered:** Rename the repository on GitHub; create a separate local repository.

**Consequences:** The URL and repository name remain `TX10LED`. Documentation uses the project title rather than the repository slug. No remote metadata changes were made.

**Superseded in part (2026-10-26):** The repository name and remote decision stand. The README title is now "Switch OLED Potential Jailbreak & USB Tool", after the jailbreak-first refocus and the later potential-jailbreak/USB-tool reframing recorded below.

## 2026-10-26 — Separate firmware compatibility from entry-point compatibility

**Decision:** Treat firmware support and exploit availability as independent axes in the matrix, documentation, and conclusion.

**Reason:** Atmosphère and hekate can support a firmware's system modules without providing a way to run unsigned code on Mariko hardware. Mixing the axes produces a misleading "supported" result.

**Consequences:** The matrix has separate firmware, hardware, entry-point, USB, and target-identity dimensions. The conclusion must state both facts: firmware 23.0.1 is supported; no software-only entry point is documented.

## 2026-10-26 — Use five explicit evidence statuses

**Decision:** Use `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `DISPROVEN`, and `UNKNOWN`, with written definitions.

**Reason:** Binary "works / does not work" labels cannot express indirect evidence, user reports, or absence of evidence. The distinction between `DISPROVEN` and `UNKNOWN` is essential to an honest conclusion.

**Consequences:** The validator rejects unknown statuses. The "no publicly documented software-only path" claim is `DISPROVEN` within the reviewed documentation, while the existence of an undisclosed exploit is `UNKNOWN`.

## 2026-10-26 — Inspection-first USB adapter

**Decision:** Build the USB tool around enumeration, classification, watch mode, and an opt-in PTP identity query. Do not include payload injection, flashing, or device-state changes.

**Reason:** The target cannot be safely or usefully exploited through stock USB, and the project's value is reproducible observation. A read-only boundary also makes the tool safe to run on a working console.

**Consequences:** The base tool uses only the Python standard library. Device access is limited to `ptp-info`, which requires `--confirm`.

## 2026-10-26 — Opt in to PTP `GetDeviceInfo`

**Decision:** Support a single PTP operation, `GetDeviceInfo` (`0x1001`). Allow `OpenSession`/`CloseSession` only with `--allow-session` and only for the identity query.

**Reason:** Switchbrew documents that DeviceInfo carries the system display version and serial number. That makes it the least invasive way to observe the console's reported firmware. The stock interface exposes only PTP operations `0x1001`–`0x100A`, so there is no broader control surface to use.

**Alternatives considered:** Passive enumeration only.

**Consequences:** `pyusb` is an optional dependency in a repository-local virtual environment. The default path sends only `GetDeviceInfo`; the session path is explicit. No object transfer or write operation is implemented.

## 2026-10-26 — Never kill `ptpcamerad` automatically

**Decision:** Report a busy interface and let the user decide what to close. Do not kill system daemons, use `sudo`, or install a privileged driver.

**Reason:** Automatically killing a macOS daemon is a system-level side effect that is disproportionate to a read-only identity query. It can also hide a real claim conflict.

**Consequences:** Some PTP reads may fail with exit code `3` until the user closes the conflicting application. The failure is documented and logged.

## 2026-10-26 — Do not add a hardware-modchip guide

**Decision:** Mention the modchip route briefly in the compatibility documentation and link to the maintained guide. Do not add installation instructions, wiring diagrams, firmware, or automation.

**Reason:** The project's mission is software-only. A hardware guide would change the risk profile, require different expertise, and blur the scope. The maintained NH Switch Guide is the appropriate source.

**Alternatives considered:** A separate `docs/HARDWARE_ALTERNATIVES.md`.

**Consequences:** The compatibility matrix marks the modchip route `in_scope: false`. The project does not accept modchip installation contributions.

## 2026-10-26 — MIT license

**Decision:** License the original code and documentation under MIT.

**Reason:** The project is small, permissive, and intended to be easy to reuse. MIT is compatible with the project's scope and avoids a mixed-license documentation setup.

**Consequences:** Third-party sources remain under their own licenses and are cited, not copied. The source register records license notes.

## 2026-10-26 — Standard-library base, optional `pyusb`

**Decision:** Keep enumeration, classification, redaction, logging, and research validation in the standard library. Use `pyusb` only for the opt-in PTP transport.

**Reason:** The base tool should work on a clean macOS Python installation without dependency or driver setup. PTP is the only part that needs a USB backend.

**Consequences:** The base tests do not need third-party packages. The PTP tests use mocked transports, so CI still does not need `pyusb` or hardware.

## 2026-10-26 — Use `unittest` for the test suite

**Decision:** Use the standard-library `unittest` runner and mocked devices.

**Reason:** `pytest` is not installed in the target environment, and the project should be runnable without an extra dependency. `unittest` covers the required test cases.

**Consequences:** The documented test command is `PYTHONPATH=src python3 -m unittest discover -s tests -v`.

**Status (2026-10-26):** The mocked test suite is not implemented yet; this is the intended command once it exists.

## 2026-10-26 — Redact serial numbers by default

**Decision:** Emit only a three-character serial prefix. Do not provide a flag to print the full serial.

**Reason:** A serial is identifying data. The research question only needs the prefix to distinguish model families. A full serial adds privacy risk without adding compatibility value.

**Consequences:** JSON uses `serial_prefix`; logs pass through the same redaction function. Local observation files are ignored by Git.

## 2026-10-26 — OpenCode v2 permissions

**Decision:** Add a project-level `opencode.json` using the v2 ordered `permissions` rules. Use `shell` (not the v1 `bash` action), ask before installs, hardware access, network shell commands, and pushes; deny privileged and destructive commands.

**Reason:** OpenCode v2.1.4 is installed, and its v2 documentation defines the ordered rule model. The project should keep routine research efficient without granting unrestricted host control.

**Consequences:** Routine read-only Git inspection and tests run without prompts. `git push` requires approval; force-push, history rewriting, disk utilities, `sudo`, and process-killing commands are denied.

## 2026-10-26 — No push before explicit confirmation

**Decision:** Make local commits only until the remote, branch, and publication scope are confirmed.

**Reason:** The repository is public. Publication is a separate decision from local authoring.

**Consequences:** The first push is blocked on explicit user confirmation. No force-push, history rewrite, remote deletion, visibility change, or release is authorized.

## 2026-10-26 — Refocus on the jailbreak question; demote the USB assistant

**Decision:** Make the software-only Atmosphère entry-point question the project's headline and primary research track. Keep the read-only USB inspection CLI as an appendix.

**Reason:** The user's goal is a software-only route to Atmosphère, not a USB tool. The USB tool cannot establish exploitability and should not frame the project.

**Alternatives considered:** Keep the combined title and equal billing; remove the USB tool entirely.

**Consequences:** README, compatibility docs, and checkpoint lead with the entry-point conclusion. The CLI remains available for identity observation but is secondary. No code was removed.

**Revised (2026-10-26):** The project is now described as a **potential jailbreak and a USB tool**. The USB tool is no longer called an appendix, and both parts are named in the README title. The entry-point conclusion is unchanged; see the later decision entry.

## 2026-10-26 — Make `entry-points.json` the detailed surface matrix

**Decision:** Record the surface-by-surface analysis in `research/entry-points.json` and keep `research/compatibility-matrix.json` as the higher-level compatibility record. The matrix references the detailed file instead of duplicating its entries.

**Reason:** A single canonical surface matrix avoids drift between a summary and a detailed list. The compatibility matrix remains the quick reference; the entry-point matrix carries access requirements, statuses, leads, and fixed flaws.

**Alternatives considered:** Keep duplicated `entry_points` arrays in both files; put everything in the compatibility matrix.

**Consequences:** `compat` counts the detailed surfaces. `scripts/validate_research.py` checks the cross-references and summary counts. The detailed file uses `EP-###` surface IDs and `L-###` lead IDs.

## 2026-10-26 — Treat `ns2jb` as a lead, not an OLED method

**Decision:** Record `ns2jb` as a real software-only userland/sysmodule chain and the closest public lead, while marking its OLED/Mariko 23.0.1 applicability `UNVERIFIED` and its path to Atmosphère `false`.

**Reason:** The author's write-up and repository establish a real Switch 2 chain on 23.0.1. The author also says the chain was tested on Switch 1, but it is unpackaged, the model/firmware are not stated, and it does not provide kernel, bootROM, CFW, or persistence. Treating the Switch 2 package as an OLED method would overstate the evidence.

**Alternatives considered:** Dismiss `ns2jb` as irrelevant because it is Switch 2-only; claim it works on the OLED because it was "tested on Switch 1".

**Consequences:** The evidence ledger separates the verified primitive (E-021), the unpackaged Switch 1 test (E-022), the capability boundary (E-032), and the unverified target applicability (E-034). The entry-point matrix marks EP-008 `PARTIALLY VERIFIED` and `public_chain_on_target: false`.

## 2026-10-26 — Add a standard-library research validator

**Decision:** Add `scripts/validate_research.py` to check JSON structure, unique IDs, source/evidence cross-references, status values, summary counts, and high-confidence secret patterns.

**Reason:** The research data now spans four JSON files and multiple cross-references. A reproducible check is cheaper and safer than ad hoc inspection, and it does not require a third-party dependency.

**Alternatives considered:** Rely on manual checks; add a pytest/CI-only validator.

**Consequences:** The validator is part of the documented workflow. It checks structure and references, not the truth of prose claims. The renderer and USB test suite remain pending.

## 2026-10-26 — Describe the project as a potential jailbreak and a USB tool

**Decision:** Name the project "Switch OLED Potential Jailbreak & USB Tool" and describe it as a source-backed investigation into a potential software-only Atmosphère jailbreak plus a read-only USB inspection tool. Both parts are part of the project identity; the USB tool is no longer called an appendix.

**Reason:** The user asked for the documentation to say what the project actually is: a potential jailbreak and a USB tool. "Potential" is load-bearing. The research has not produced a working jailbreak, and the documentation must not imply that it has.

**Alternatives considered:** Keep the research-only title and describe the USB tool as an appendix; claim the project is a jailbreak (rejected as false); remove the USB tool.

**Consequences:** README, `pyproject.toml`, `SECURITY.md`, `docs/USB_INTEGRATION.md`, and `research/CHECKPOINT.md` use the new framing. The entry-point conclusion is unchanged: no publicly documented, reproducible software-only path to Atmosphère was found. The README keeps an explicit "not a working jailbreak" boundary and the five evidence statuses.

## 2026-10-26 — Treat owner manual confirmation as `PARTIALLY VERIFIED`

**Decision:** Record the owner's manual confirmation of the model, firmware, serial prefix, and no-modification history as `PARTIALLY VERIFIED`, not `VERIFIED`. Keep `firmware_verified: false` until a PTP `GetDeviceInfo` observation or another independent check is recorded.

**Reason:** The owner read the values from the console's System Settings, which is direct testimony and stronger than the initial report. It is still owner-reported and not independently observed or tool-attested. The project's `VERIFIED` label is reserved for authoritative or primary sources with no reviewed contradiction, so manual testimony does not meet that bar by itself.

**Alternatives considered:** Leave the identity `UNVERIFIED` until PTP; mark it `VERIFIED` because the owner read it from the console.

**Consequences:** `E-009`, matrix row `C-011`, `docs/COMPATIBILITY.md`, the README summary, and `research/known-limitations.md` now say `PARTIALLY VERIFIED` with the limitation stated. The observation is recorded in `research/hardware-observations/2026-10-26-manual.json`. A PTP observation is still pending and would strengthen, but not prove, exploitability or integrity.

## 2026-10-26 — Record the PTP identity observation and the empty-`system_profiler` fallback

**Decision:** Record the read-only PTP `GetDeviceInfo` observation as evidence (E-037) and mark the target's PTP enumeration and identity query `VERIFIED`. Keep the overall target identity `PARTIALLY VERIFIED`, because `DeviceInfo` reports the generic model `Nintendo Switch` and cannot establish `HEG-001`, OLED-versus-LCD hardware, or the absence of a modchip. Change `auto` enumeration to fall back to `ioreg` when `system_profiler` succeeds but returns no devices.

**Reason:** The console enumerated as `057e:201d` and answered `GetDeviceInfo` without opening a session, reporting firmware `23.0.1`, serial prefix `XTJ***`, and 10 operations. That is direct tool observation of the firmware and serial prefix, so the earlier `firmware_verified: false` gate is satisfied for those fields. It is still not a model or integrity attestation. On the same host, `system_profiler SPUSBDataType` returned an empty list while `ioreg` saw the console, so treating an empty result as a valid empty bus made the tool miss a connected device.

**Alternatives considered:** Mark the whole target `VERIFIED` (rejected: the model and modchip history remain owner-reported); keep `firmware_verified: false` (rejected: contradicts the observation); leave the enumeration behavior unchanged (rejected: it hides a real device on this macOS version).

**Consequences:** `E-009`, `E-010`, `E-012`, `E-037`, matrix rows `C-008`, `C-011`, `U-001`, the target record, `docs/COMPATIBILITY.md`, `docs/USB_INTEGRATION.md`, the README, `research/known-limitations.md`, and `research/CHECKPOINT.md` are updated. The observation is recorded in `research/hardware-observations/2026-10-26-ptp.json` with the serial truncated to a three-character prefix. The entry-point conclusion is unchanged, and no console state was modified.
