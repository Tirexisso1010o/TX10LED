# Entry Points

> **Research snapshot: 2026-10-26.** No publicly documented, reproducible software-only entry point to Atmosphère was found for an unmodified Switch OLED (Mariko) on firmware 23.0.1. The closest public lead is `ns2jb`, a real software-only userland/sysmodule chain, but it is packaged for Switch 2, is not packaged for Switch 1, and does not provide kernel, bootROM, or CFW access. This is an absence-of-documented-method finding, not proof that no undisclosed method exists.

This document is the readable companion to [`research/entry-points.json`](../research/entry-points.json). The JSON is the source of truth for the surface matrix; this page explains what each surface is, what access it requires, and why it does or does not change the conclusion.

## The question

The research question is narrow:

> Is there a publicly documented, reproducible, **software-only** path to launch **Atmosphère** on an **unmodified Switch OLED (HEG-001)** running **firmware 23.0.1**?

Two axes are deliberately separate:

1. **Firmware compatibility** — can Atmosphère and hekate operate on this system firmware?
2. **Entry-point compatibility** — is there a way to execute unsigned code on this hardware at all?

The answer is **yes** to the first and **no documented software-only method** for the second. Atmosphère 1.12.1 and hekate v6.5.4 support 23.0.1, but support for a firmware's system modules is not a way to run code on a patched bootROM.

## How to read this document

Each surface has one of the five evidence statuses used throughout the repository:

| Status | Meaning |
|---|---|
| **VERIFIED** | Directly supported by an authoritative or primary source, with no reviewed contradiction. |
| **PARTIALLY VERIFIED** | Indirect evidence, or evidence that covers a related but not identical case. |
| **UNVERIFIED** | Plausible or user-reported, but not independently checked. |
| **DISPROVEN** | Contradicted by an authoritative source or direct evidence. |
| **UNKNOWN** | Insufficient evidence; neither supported nor contradicted. |

The status answers a specific claim: **“This surface provides a publicly documented, reproducible software-only path to Atmosphère on the target.”** A surface can have a real public primitive (`PARTIALLY VERIFIED`) without providing a target-specific path. `UNKNOWN` means no qualifying public method was found; it does not mean the surface is safe or unexploitable.

## Summary

| ID | Surface | Access | Public chain on target? | Status | Leads to Atmosphère? |
|---|---|---|---|---|---|
| EP-001 | BootROM / RCM USB recovery | Physical RCM + USB host | No — bootROM patched | **DISPROVEN** | No |
| EP-002 | Recovery / Maintenance mode | Physical buttons | No — update/format only | **DISPROVEN** | No |
| EP-003 | Browser / WebKit applets | Network/applet flow | No public 23.0.1 chain found | **UNKNOWN** | No |
| EP-004 | PTP / MTP USB album mode | USB cable + user mode | No — identity/media only | **DISPROVEN** | No |
| EP-005 | Local wireless (`ldn`) | Adjacent wireless | Known CVE fixed before target | **UNKNOWN** | No |
| EP-006 | Bluetooth | Adjacent radio | No public 23.0.1 chain found | **UNKNOWN** | No |
| EP-007 | Game saves and cartridges | Saves / game card | No public code-execution chain found | **UNKNOWN** | No |
| EP-008 | System services and sysmodules | Initial userland primitive | Real primitive, but not target/CFW | **PARTIALLY VERIFIED** | No |
| EP-009 | Kernel / TrustZone | Post-userland | No public 23.0.1 chain found | **UNKNOWN** | No |
| EP-010 | Hardware fault injection / modchip | Microsoldering | Yes — hardware route | **VERIFIED** | Yes, but out of scope |

Only EP-010 has a documented public chain to Atmosphère on the target, and it is not software-only. The matrix records it for completeness, not as a recommendation.

## EP-001 — BootROM / RCM USB recovery

The Tegra bootROM exposes a USB recovery mode known as RCM (or APX). On vulnerable Erista consoles, **Fusée Gelée** (`CVE-2018-6242`) lets a USB host send an unsigned payload before Horizon OS starts. That is the classic software-only route to a custom bootloader and Atmosphère.

The OLED uses Mariko/Tegra X1+ hardware. Its bootROM is patched against Fusée Gelée. The practical consequences are:

- The console can still be placed into RCM.
- The RCM USB device (`0955:7321`) can enumerate.
- A payload cannot be accepted on patched hardware.
- RCM enumeration is therefore **not** evidence that CFW can be launched.

No other public Mariko bootROM chain was found in the reviewed sources. The surface is marked `DISPROVEN` because the known public method is patched, not because every possible bootROM bug has been ruled out.

**Do not attempt payload injection on the target.**

## EP-002 — Recovery / Maintenance mode

Recovery mode is entered with **Volume Up + Volume Down + Power**. The documented menu supports system update and initialize/format operations. It does not document unsigned-code execution, payload loading, or a shell.

That makes it useful for recovery and maintenance, not for launching Atmosphère. The surface is marked `DISPROVEN` for the entry-point claim. This does not prove the recovery applet has no vulnerabilities; it means no public chain was found in the reviewed documentation.

## EP-003 — Browser / WebKit applets

The Switch uses NetFront NX, a WebKit-based browser, in several applets. The captive-portal `WifiWebAuthApplet` and the account-login browser are the best-known network-facing surfaces. Early Switch exploits, including **PegaSwitch**, used browser applets and DNS/captive-portal redirection.

PegaSwitch is archived and its documented launch paths target firmware **1.0.0** and the **Fake News** entry point. It does not document 23.0.1 support. No public 23.0.1 browser chain was found in the reviewed flaw list or browser documentation.

The surface is `UNKNOWN`, not `DISPROVEN`: browser applets remain a live attack surface, and public flaw lists can lag private research. A browser primitive would still be userland-only; a kernel or bootROM stage would be required for Atmosphère.

## EP-004 — PTP / MTP USB album mode

The stock **Copy to PC via USB** mode exposes standard PTP operations for identity and media transfer. Switchbrew documents that Capmtp exposes only PTP operations `0x1001`–`0x100A`. `GetDeviceInfo` (`0x1001`) reports the model, system display version, and serial number; it is read-only identity data.

There is no documented shell, ADB, firmware-query service, or general-purpose remote-control interface in this mode. The surface is `DISPROVEN` as an entry point. It is still useful for **verifying the target's reported identity** without changing console state.

A PTP response can be spoofed by modified firmware. It is an observation, not an integrity attestation, and it cannot establish exploitability, boot state, CFW access, or NAND contents.

## EP-005 — Local wireless (`ldn`)

Local wireless is used for nearby multiplayer and local communication. **CVE-2026-82079** is a stack-based buffer overflow in this area. The CVE record says it affects system versions **before 23.0.0** and is fixed in **23.0.0**; the target is reported on 23.0.1.

No public exploit code for the CVE was found in the reviewed sources. Even if one existed, the target is outside the affected range. The surface is `UNKNOWN` for any *other* public 23.0.1 chain, not because CVE-2026-82079 is still open.

A local-wireless primitive would still be userland/service-level; a kernel or bootROM stage would be required for Atmosphère.

## EP-006 — Bluetooth

The Bluetooth stack handles controllers and wireless peripherals. Switchbrew lists Bluetooth stack overflows fixed in **15.0.0**, **16.0.0**, **21.0.0**, and **22.0.0**. No public 23.0.1 chain was found.

The surface is `UNKNOWN`. The flaw list is a public record, not a complete audit, and absence of a listed chain is not proof that the stack is unexploitable.

## EP-007 — Game saves and cartridges

Save data, game cards, and game-level parsers are a large, game-dependent attack surface. The reviewed flaw list's Games section documents game-level infoleaks and anti-cheat issues, not a public save-data or cartridge code-execution chain on 23.0.1.

Save editing and cartridge data manipulation are **not** code execution. The surface is `UNKNOWN`; no qualifying public chain was found. A game-context primitive would still need a kernel or bootROM stage for Atmosphère.

## EP-008 — System services and sysmodules: the `ns2jb` lead

Horizon OS runs many system services and sysmodules, including filesystem (`fs`), `bsdsocket`, `audio`, and other IPC services. A userland or sysmodule compromise can run native code with service privileges. This is the closest public lead to a software-only path.

### What `ns2jb` is

`ns2jb` is a **software-only, tethered userland/sysmodule jailbreak for the Nintendo Switch 2** on system software **23.0.1**. It runs native code as ordinary sysmodules and as the built-in `fs` sysmodule. It requires **SmileBASIC 4.4.9**, a host on the same network, and a one-time program load.

The author's write-up says the exploit chain was **also tested on Switch 1**, but:

- it has **not been packaged** for Switch 1;
- the Switch 1 model and firmware are **not stated**;
- the author says it **would not provide the capabilities of a modchip**;
- the published repository is **Switch 2 only**.

### What it proves — and what it does not

| Question | Answer |
|---|---|
| Is it a real software-only chain? | **Yes**, on Switch 2 system software 23.0.1. |
| Does it run native code? | **Yes**, as ordinary sysmodules and `fs`. |
| Does it provide kernel access? | **No.** |
| Does it provide bootROM access? | **No.** |
| Does it install CFW or persistence? | **No.** |
| Is it packaged for Switch 1? | **No.** |
| Is it confirmed on OLED/Mariko 23.0.1? | **No.** The author does not state the Switch 1 model or firmware. |
| Is it a path to Atmosphère by itself? | **No.** It is a userland/sysmodule primitive, not a boot chain. |

The surface is `PARTIALLY VERIFIED`: the primitive is real, but it does not meet the target or CFW criteria. The Switch 1 test is a lead worth following, not a method to run. Do not treat the Switch 2 package as an OLED method.

### Related 23.0.0 service fixes

Switchbrew's 23.0.0 page documents fixes for:

- `bsdsocket` AddrInfo deserialization;
- multiple `audio` RequestUpdate validation issues;
- `ldn` CVE-2026-82079.

These are public fixes, not a public exploit chain. They show that system-service surfaces are actively maintained and patched.

## EP-009 — Kernel / TrustZone

Kernel code execution is typically needed for full system control. A bootROM or secure-monitor compromise is needed for pre-boot CFW that survives reboot. The reviewed public flaw list contains no unpatched Mariko software-only boot chain and no public 23.0.1 kernel/TrustZone chain.

The 23.0.0 update fixed `bsdsocket`, `audio`, and `ldn` issues; 23.0.1 lists only a stability fix and an `sdb`/SystemVersion update. The surface is `UNKNOWN`.

A kernel exploit alone is not Atmosphère. Atmosphère needs a boot path; kernel code execution may not survive reboot or provide a way to launch the CFW.

## EP-010 — Hardware fault injection / modchip (out of scope)

The maintained NH Switch Guide documents a hardware modchip as the route for patched and Mariko consoles. A modchip performs CPU voltage glitching to bypass bootROM verification and launch a payload from the SD card. Installation requires microsoldering and carries warranty, safety, and bricking risks.

This is a real documented route to Atmosphère on the target, but it is **not software-only** and is **out of scope** for this project. This repository provides no installation instructions, wiring diagrams, firmware, or automation. Use the maintained guide and a reputable installer if you choose that route.

## Historical leads

| Lead | Era | Why it does not apply |
|---|---|---|
| PegaSwitch | Early Switch browser, firmware 1.0.0 / Fake News | Archived; its documented launch paths target early firmware, not 23.0.1. |
| Caffeine | Patched Erista, firmware 4.1.0 | Different hardware and firmware; the OLED is Mariko, not Erista. |

Both are recorded in the JSON as `L-002` and `L-003`. They are useful for understanding how earlier entry points worked, not as current methods.

## Fixed public flaws

| Flaw | Surface | Fixed in | Target affected? |
|---|---|---|---|
| Fusée Gelée (`CVE-2018-6242`) | EP-001 BootROM/RCM | Mariko bootROM | No |
| Local-wireless stack overflow (`CVE-2026-82079`) | EP-005 `ldn` | 23.0.0 | No |
| `bsdsocket` AddrInfo deserialization | EP-008 system services | 23.0.0 | No |
| `audio` RequestUpdate validation | EP-008 system services | 23.0.0 | No |
| Bluetooth stack overflows | EP-006 Bluetooth | 15.0.0, 16.0.0, 21.0.0, 22.0.0 | No |

“Fixed” means the reviewed public source says the flaw is fixed in that version or hardware revision. It does not mean every related code path has been audited.

## What this means

As of **2026-10-26**, the reviewed public documentation supports this conclusion:

> Firmware 23.0.1 is compatible with Atmosphère 1.12.1 and hekate v6.5.4, but an unmodified Switch OLED has no publicly documented, reproducible software-only path to launch Atmosphère. The documented route requires a hardware modchip, which is outside this project's scope.

The closest public lead is `ns2jb`. It is a genuine software-only userland/sysmodule chain, but it is packaged for Switch 2, is not packaged for Switch 1, and does not provide kernel, bootROM, or CFW access. It does not change the conclusion for the OLED.

## What would change this conclusion

The conclusion would need to be revisited if any of the following became available:

- A public, independently reproduced Mariko bootROM or pre-boot software vulnerability that works on 23.0.1.
- A packaged, reproducible Switch 1 version of the `ns2jb` chain, with the model and firmware identified.
- A public chain that connects a userland/sysmodule primitive to kernel or bootROM access on Mariko, with reproducible steps and hardware evidence.
- A documented software-only entry point from a maintained project that explicitly supports the OLED on 23.0.1.
- A correction showing that the target is not Mariko/OLED hardware.

A firmware update alone would not create an entry point. A new Atmosphère release alone would not create one either. The missing component is a way to execute unsigned code before Horizon OS starts, or a complete userland-to-boot chain that reaches that point.

## What not to infer

- **“No public method” is not “no method.”** The existence of an undisclosed exploit is `UNKNOWN`, not `DISPROVEN`.
- **Firmware support is not entry-point support.** Atmosphère supporting 23.0.1 does not mean an unmodified OLED can launch it.
- **RCM enumeration is not exploitability.** A patched console can enter RCM and enumerate; it still cannot receive a payload.
- **PTP identity is not integrity.** `GetDeviceInfo` reports what the console says, not whether it is unmodified or exploitable.
- **A userland primitive is not CFW.** `ns2jb` demonstrates code execution as sysmodules and `fs`, not a boot chain.
- **A historical exploit is not a current one.** PegaSwitch and Caffeine are recorded to prevent category errors, not as 23.0.1 methods.

## Related records

- [`research/entry-points.json`](../research/entry-points.json) — machine-readable surface matrix.
- [`research/evidence-ledger.json`](../research/evidence-ledger.json) — claims, statuses, confidence, and limitations.
- [`research/compatibility-matrix.json`](../research/compatibility-matrix.json) — high-level compatibility record.
- [`docs/COMPATIBILITY.md`](COMPATIBILITY.md) — compatibility narrative.
- [`research/known-limitations.md`](../research/known-limitations.md) — what the research cannot establish.
- [`docs/RESEARCH_METHODOLOGY.md`](RESEARCH_METHODOLOGY.md) — source rules and status definitions.
