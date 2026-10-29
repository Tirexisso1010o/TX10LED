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

## The chain, as stages

An entry point is only one link. Atmosphère needs a chain, and the links are not interchangeable:

| Stage | What it must achieve | Public status on Mariko 23.0.1 |
|---|---|---|
| **0. Trigger** | Obtain the software the entry lives in | Unavailable to this owner: `ns2jb` needs SmileBASIC 4.4.9 |
| **1. Initial code execution** | Arbitrary code in an ordinary userland process | Not publicly demonstrated on Switch 1 23.0.1 |
| **2. Privilege escalation** | A sysmodule with useful permissions, or the kernel | Not publicly demonstrated on Switch 1 23.0.1 |
| **3. Boot-stage execution** | Code at warmboot/package1, before Horizon verifies its modules | **Nothing public** |
| **4. Launch and persistence** | Hand off to a payload or CFW | Solved: Atmosphère 1.12.1, hekate v6.5.4 |

Stage 3 is the one that is usually skipped in discussion, and it is the decisive one. Atmosphère replaces verified system modules, so a kernel exploit that arrives after boot cannot make the boot chain load unsigned code. The historical proof that this is possible on patched hardware is **Caffeine**, a warmboot exploit for patched Erista on 4.0.0–4.1.0, which ran full CFW without Fusée Gelée. No Mariko equivalent is public for modern firmware.

The full stage-by-stage analysis is in [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md).

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
| EP-005 | Local wireless (`ldn`) | Adjacent wireless | Known CVE fixed; room appears; association reached; hostapd/AP path negative before `0x88B7` | **UNKNOWN** | No |
| EP-006 | Bluetooth | Adjacent radio | No public 23.0.1 chain found | **UNKNOWN** | No |
| EP-007 | Game saves and cartridges | Saves / game card | No public code-execution chain found | **UNKNOWN** | No |
| EP-008 | System services and sysmodules | Initial userland primitive | Real primitive, but not target/CFW | **PARTIALLY VERIFIED** | No |
| EP-009 | Kernel / TrustZone | Post-userland | No public 23.0.1 chain found | **UNKNOWN** | No |
| EP-010 | Hardware fault injection / modchip | Microsoldering | Yes — hardware route | **VERIFIED** | Yes, but out of scope |
| EP-011 | GameShare / `splay` receiver | Switch 2 host + local wireless | No public vulnerability found; local `splay` program NCA blocked by key generation `0x17` | **UNKNOWN** | No |

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

The three sharing paths are not the same:

- **Virtual Game Cards** are account-, internet-, proximity-, and license-gated (`E-079`); a PC cannot be a linked console.
- **GameShare / `splay`** requires a real Switch 2 host and ECC-verified host data (`E-038`–`E-044`); a PC cannot produce a valid signed host advertisement.
- **LDN pre-auth** is the only path a PC can reach without a second console or Nintendo signing keys. Retail LDN is AES-encrypted. The owner's local `prod.keys` decrypt the Phase 1 advertisement and confirm security mode 1 (prod), challenge enabled, max 2 participants, app version 26 (`E-081`); the plaintext development-mode path remains a no-key control (`E-078`).

`H-010` is the resulting conditional hypothesis. The passive advertisement capture is complete. One approved prod-mode host run emitted 373 AES-CTR advertisements that decrypted to the captured room, but the console reported no rooms, the host logged no `JOIN`, and the same-phy captures saw no console frames (`E-084`, `E-085`). A second prod-mode run again produced no join and no room, and its pcap capture failed on a wrapper permission error (`E-087`). A third run with the fixed wrapper again produced no join; an independent Location Services-enabled scan saw a hidden ambient BSSID but not the host BSSID (`E-089`). An AP-mode control proved the adapter can transmit at -32 dBm (`E-090`), while a monitor-mode control showed that monitor-mode injection does not transmit (`E-091`). Location Services restored real BSSIDs for the independent scan (`E-092`). A follow-up AP-mode `NL80211_CMD_FRAME` test put a 20-frame test beacon on the air at -28 dBm in all 12 scans (`E-094`), so the AP beacon half of management-frame injection works. A broadcast LDN vendor action frame is still blocked by mac80211's station lookup (`E-093`), but a non-LDN unicast control with a temporary station entry was accepted by the kernel without a netlink error (`E-095`). A real LDN unicast run then sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID; all requests were accepted, but the console was off/away, so reception was not observed (`E-096`). The driver rejects a broadcast-BSSID action frame with `EINVAL`, so only the AP-BSSID variant is available (`E-097`). A supervised rerun on 2026-10-29 made the room `TX10LED` appear on the console, but selecting it produced `2203-0065` immediately; the search screen closed, the console returned to the game normally, and hostapd logged no authentication, association, or station event (`E-098`). The room appearance confirms the advertisement reached the console's scan path. That join failed before association because the hostapd WLAN SSID was `TX10LED-TEST` with open security, not the room's 32-character hexadecimal WLAN SSID and LDN RSN IE. A second supervised run used the corrected WLAN parameters: the console authenticated, associated with AID 1, and was marked authorized, then disassociated with `reason_code=8` about one second later and sent no observed `0x88B7` request (`E-099`). The monitor saw a 28-byte null-data frame, not the authentication request; the AP raw socket saw a 20-byte ethertype `0x0006` frame. The association response included an RSN IE that the `ldn` `MonitorAP` does not send, and the AP control port rejects `0x88B7` with `EINVAL` while the raw authorized-station path transmits it protected with KeyID 0 (`E-100`). A third supervised run omitted the association-response RSN IE, enabled raw-frame diagnostics and a local pcap, and used the raw responder, but the console again authenticated, associated, and was authorized, then disassociated with `reason_code=8` before any `0x88B7` request; the pcap contained no console data payload frame (`E-101`). The current hostapd/AP path is negative for `D9`; the parser hypothesis remains untested. The next step is a materially different AP implementation, a different adapter/driver with working monitor-mode TX, or static analysis of the `ldn` NCA, described in [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md). A local-wireless primitive would still be userland/service-level; a kernel or bootROM stage would be required for Atmosphère.

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

### Planned `D10` network-service test

`D10` targets the same class of service surfaces from the network side: the `wlan` supplicant (802.11 management/EAPOL) and the `bsdsocket`/`sfdnsres`/`nifm`/`ssl` stack (DHCP/DNS/IPv6/TLS), through a dedicated test AP and the console's built-in **Test Connection**. Phase 0 and Phase 1 baselines are complete; Phase 2 and later are gated and not started. See [`docs/WIFI-NETWORK-TEST-PLAN.md`](WIFI-NETWORK-TEST-PLAN.md). A fault there would be stage 1–2 at best and would not reach Atmosphère without boot-stage execution.

## EP-009 — Kernel / TrustZone

Kernel code execution is typically needed for full system control. A bootROM or secure-monitor compromise is needed for pre-boot CFW that survives reboot. The reviewed public flaw list contains no unpatched Mariko software-only boot chain and no public 23.0.1 kernel/TrustZone chain.

The 23.0.0 update fixed `bsdsocket`, `audio`, and `ldn` issues; 23.0.1 lists only a stability fix and an `sdb`/SystemVersion update. The surface is `UNKNOWN`.

A kernel exploit alone is not Atmosphère. Atmosphère needs a boot path; kernel code execution may not survive reboot or provide a way to launch the CFW.

## EP-010 — Hardware fault injection / modchip (out of scope)

The maintained NH Switch Guide documents a hardware modchip as the route for patched and Mariko consoles. A modchip performs CPU voltage glitching to bypass bootROM verification and launch a payload from the SD card. Installation requires microsoldering and carries warranty, safety, and bricking risks.

This is a real documented route to Atmosphère on the target, but it is **not software-only** and is **out of scope** for this project. This repository provides no installation instructions, wiring diagrams, firmware, or automation. Use the maintained guide and a reputable installer if you choose that route.

## EP-011 — GameShare / `splay` applet (receiver-side remote input)

GameShare lets a **Nintendo Switch 2** host share compatible software with nearby systems, including a Switch 1 or OLED system. On the receiving system the session is handled by the **`splay` system applet**, which was introduced in system update **20.0.0** and is launched by `qlaunch`.

It is a documented flow in which a nearby device sends data that a system applet on the target parses **without the user launching a game**. That is why it is recorded as its own surface rather than folded into local wireless.

### What is documented

| Property | Finding |
|---|---|
| Receiver component | `splay` applet, added in 20.0.0; launched by `qlaunch`. |
| Transport | `ldn` local wireless, with `SetProtocol` value 3. |
| Payload | A **video stream**, plus setup metadata: the game's NACP and JPEG images. |
| Authentication | ECC signature verification is used for some data, including the `AdvertiseData` returned by `Scan`. |
| Receiver privileges | `StreamPlaySaveData` (`FsAccessFlag` bit 47); on Switch 1 with 23.0.0+, `news:c` and `stpl:sys`. |
| Who can host | Only a Switch 2. Nintendo states the feature cannot be used between two Switch 1/OLED/Lite systems. |
| How a Switch 1 can receive | Local wireless only. Online GameShare via GameChat is documented for Switch 2 systems. |

### Read-only review (2026-10-29)

The public record was reviewed again on **2026-10-29**, and the owner's local dump was inspected without decrypting the `splay` program content:

- **No public vulnerability or exploit was found.** Switchbrew's Splay Applet and Switch System Flaws pages, the 20.0.0/23.0.0/23.0.1 changelogs, and Nintendo's GameShare FAQ contain no `splay`/GameShare advisory, proof of concept, or exploit (`E-102`).
- **No post-20.0.0 `splay` security fix is documented.** 23.0.0 updated `splay`'s NPDM (`FsAccessFlag` bit 47, `news:c`, `stpl:sys`, KernelVersion 27.1) and RomFS (`lyt`, `message`, `sound`), but the changelog records no security fix. 23.0.1 updated only `sdb`; `splay` was not updated (`E-102`).
- **The `splay` program NCA is not decryptable locally.** It uses key generation `0x17`, which needs `key_area_key_application_16`; the owner's key file stops at `_14`. Its meta NCA uses key generation `0x00`, and the CNMT reports title `0100000000001048`, version `0x5c0004b0`, one Program content entry, and a SHA-256 that matches the local program NCA (`E-103`).
- **The only key-generation-`0x15` program is `miiEdit`.** Title `0100000000001009` decrypted with `key_area_key_application_14` and verified its section-0 master hash, which confirms the local NCA decryption path. It is a Mii editor applet, not a remote-input surface (`E-103`).

This review does not change the status: the surface remains `UNKNOWN`. It narrows the next step to a Switch 2 host for a supervised receiver test or a key set covering key generation `0x17` for static analysis. Neither is available.

### What it proves — and what it does not

| Question | Answer |
|---|---|
| Is the surface reachable on the target? | **Yes.** A 23.0.1 Switch 1 can act as a GameShare receiver. |
| Is there a public vulnerability or exploit? | **No.** None was found for `splay`, the protocol, or its NACP/JPEG handling, and no post-20.0.0 `splay` security fix is documented. |
| Is the receiver code analyzable locally? | **Not yet.** The `splay` program NCA uses key generation `0x17`; `key_area_key_application_16` is missing. Only its meta CNMT is readable. |
| Would a compromise give kernel access? | **No.** `splay` is an applet; its documented privileges are applet-level. |
| Would it give bootROM access or Atmosphère? | **No.** A separate kernel or bootROM stage would still be required. |
| Can the target host a session itself? | **No.** Hosting requires a Switch 2, so the target cannot be the sender. |

The surface is `UNKNOWN`: it is real and user-reachable, but no qualifying public chain exists. The result is recorded as lead `L-006`.

### Why it is interesting, and why it is bounded

It is interesting because a remote peer supplies a system applet with parsing work — NACP metadata, JPEGs, and stream data — and that applet holds a filesystem permission that ordinary software does not. Historically, parsers fed by a remote peer have been productive targets.

It is bounded by four things:

- **Host requirement.** Nintendo documents that only a Switch 2 can host. Attacking the target through this surface would require controlling a Switch 2 or successfully spoofing a host.
- **Transport.** Switch 1 receivers are local-wireless only, so this is a proximity surface, not an internet-facing one.
- **Authentication.** At least some host data is ECC-verified. Public documentation does not say how much of the session that covers, which is itself an open question.
- **Capability ceiling.** Even a full `splay` compromise is applet-level userland. It is not a boot chain.

**This is a surface, not an exploit.** No proof of concept exists publicly, and the project does not have one.

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

As of **2026-10-29**, the reviewed public documentation supports this conclusion:

> Firmware 23.0.1 is compatible with Atmosphère 1.12.1 and hekate v6.5.4, but an unmodified Switch OLED has no publicly documented, reproducible software-only path to launch Atmosphère. The documented route requires a hardware modchip, which is outside this project's scope.

The closest public lead is `ns2jb`. It is a genuine software-only userland/sysmodule chain, but it is packaged for Switch 2, is not packaged for Switch 1, and does not provide kernel, bootROM, or CFW access. It does not change the conclusion for the OLED.

GameShare (`EP-011`) was reviewed as a receiver-side remote-input surface and recorded as `UNKNOWN`. It is reachable on the target, but no public vulnerability exists, hosting requires a Switch 2, and any compromise would stop at applet privileges. A second read-only review on 2026-10-29 found no public `splay`/GameShare vulnerability and no post-20.0.0 `splay` security fix; the local `splay` program NCA is blocked by key generation `0x17`, while its meta CNMT is readable (`E-102`, `E-103`). It does not change the conclusion either.

## What would change this conclusion

The conclusion would need to be revisited if any of the following became available:

- A public, independently reproduced Mariko bootROM or pre-boot software vulnerability that works on 23.0.1.
- A packaged, reproducible Switch 1 version of the `ns2jb` chain, with the model and firmware identified.
- A public chain that connects a userland/sysmodule primitive to kernel or bootROM access on Mariko, with reproducible steps and hardware evidence.
- A public vulnerability in `splay` or the GameShare protocol, combined with a Mariko kernel or bootROM stage.
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
- **A remote-input surface is not a remote exploit.** GameShare gives a host a documented way to send data that the `splay` applet parses. No public vulnerability exists, and the applet is not a boot path.

## Related records

- [`research/entry-points.json`](../research/entry-points.json) — machine-readable surface matrix.
- [`research/evidence-ledger.json`](../research/evidence-ledger.json) — claims, statuses, confidence, and limitations.
- [`research/compatibility-matrix.json`](../research/compatibility-matrix.json) — high-level compatibility record.
- [`docs/COMPATIBILITY.md`](COMPATIBILITY.md) — compatibility narrative.
- [`research/known-limitations.md`](../research/known-limitations.md) — what the research cannot establish.
- [`docs/RESEARCH_METHODOLOGY.md`](RESEARCH_METHODOLOGY.md) — source rules and status definitions.
