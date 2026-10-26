# Gap Analysis: What a Software-Only Path Would Require

> **Research snapshot: 2026-10-26.** This is read-only analysis. It describes which pieces are missing and why. It does not authorize executing an exploit, injecting a payload, changing firmware, spoofing a GameShare host, or writing save data to the console.

## Why this document exists

Most discussion of a "jailbreak" collapses into "find a bug". Atmosphère is not a bug; it is a chain of stages, and each stage has a different job. Writing the chain out as stages makes the missing pieces explicit and prevents a common category error: treating a userland bug as if it were a CFW path.

The conclusion of this analysis is not "keep looking harder". It is that **one specific stage has no public artifact for Mariko on any modern firmware**, and no amount of searching can substitute for research that has not been published.

## The stages

| Stage | What it must achieve | Why it is needed |
|---|---|---|
| **0. Trigger** | Obtain the software or surface the entry point lives in | An entry point is only reachable through a specific title, applet, or protocol |
| **1. Initial code execution** | Arbitrary code in an ordinary userland process | The first foothold; usually a memory-corruption bug in a parser |
| **2. Privilege escalation** | Move to a sysmodule with useful permissions, or to the kernel | A game process can do almost nothing; system services hold the permissions |
| **3. Boot-stage execution** | Run code at warmboot/package1, or otherwise before Horizon verifies its own modules | Atmosphère replaces or patches system modules; Horizon will not load unsigned ones |
| **4. Launch and persistence** | Hand off to a payload or CFW, ideally surviving reboot | This is what makes the result Atmosphère rather than a session |

Atmosphère is a **boot-time** CFW. A runtime kernel exploit can patch a running system, but that is not the same artifact, does not survive a reboot, and is not what the maintained guide installs.

## Where the target stands

| Stage | Public status on Mariko 23.0.1 | Closest public artifact |
|---|---|---|
| 0. Trigger | **Unavailable to this owner** | `ns2jb` needs SmileBASIC 4.4.9; it is delisted and not owned |
| 1. Initial execution | **Not publicly demonstrated on Switch 1 23.0.1** | `ns2jb`'s SmileBASIC integer overflow, packaged for Switch 2 |
| 2. Privilege escalation | **Not publicly demonstrated on Switch 1 23.0.1** | `ns2jb`'s `fs` `Path::Normalize` overflow, packaged for Switch 2 |
| 3. Boot stage | **Nothing public** | Caffeine, a warmboot exploit for **Erista 4.0.0–4.1.0 only** |
| 4. Launch | Packages exist, launch path missing | Atmosphère 1.12.1 and hekate v6.5.4 support 23.0.1 |

Stage 4 is the only stage with maintained software behind it — Atmosphère and hekate exist and support 23.0.1 — but it has nothing to hand off to without stage 3. Stage 3 is empty.

## Stage 3 is the one people forget

It is tempting to think that a kernel exploit would be enough. It is not. Atmosphère has to run **before or during boot**, because its job is to replace verified system modules with patched ones. A kernel exploit that arrives after Horizon has booted cannot retroactively convince the boot chain to load unsigned modules.

### The Caffeine precedent

Caffeine is the counter-example that proves this is not impossible in principle. It is an implementation of a **warmboot exploit** for system software **4.1.0 and below** (excluding 1.0.0), and the maintained hacks guide notes that patched Erista models can use it on **4.0.0–4.1.0**.

That matters because patched Erista consoles cannot use Fusée Gelée. Caffeine did not need the bootROM. It attacked warmboot instead, which was enough to launch a payload and run full CFW. In other words:

> A patched console can run CFW from software alone **if the boot stage itself is exploitable**.

Warmboot is not a minor detail: it is package1 **section 0**, and on Mariko package1 is distributed in a signed and encrypted format. A Mariko equivalent would therefore need a memory-corruption bug in the verified warmboot or TSEC code — not a re-signed package. No such bug is public for modern firmware, and the Caffeine family was fixed years ago.

### Why the modchip works

The modchip performs stage 3 **physically**. It glitches the CPU during boot so verification is bypassed and a payload loads from SD. That is exactly the stage that software-only research is missing on Mariko. It is also why the maintained guide routes Mariko consoles to hardware and not to software.

## Why `ns2jb` does not close stages 1–2

`ns2jb` is the strongest public lead, and it is easy to over-read:

- Its **entry** is SmileBASIC 4.4.9. That is stage 0, and this owner does not have it. The title is delisted, version-locked, and there is no published Switch 1 package.
- Its **`fs` path-normalization bug is stage 2**. Stage 2 without stage 1 is unreachable: you need code execution in a process that can send the IPC command in the first place.
- The author says the chain was **tested on Switch 1 but not packaged**. Testing is not a distribution, and the model and firmware are unstated.
- Even the packaged demo is **tethered** and installs no CFW or persistence. It closes stage 2 on Switch 2 and does nothing for stage 3 anywhere.

So `ns2jb` is genuinely valuable research, and it still leaves this console with no stage 1 and every Mariko console with no stage 3.

## What "userland homebrew" would actually require

"Homebrew" covers two different goals, and they need different amounts of access:

| Goal | What it needs | Is applet-level userland enough? |
|---|---|---|
| Run custom code inside an existing process (a browser payload, a game script) | Code execution in that process | **In principle yes**, given a vulnerability |
| Run separate homebrew apps (NRO files) from the SD card | SD filesystem access, a loader that accepts unsigned code, and usually kernel patches | **No** |

The captive-portal applet illustrates the gap:

- Its filesystem permission is **SystemSaveData**, not the SD card, so it cannot browse or read `sd:/`.
- It has **`ldr:ro`** (read-only loader) and **`ns:web`**, not `ldr:s` or `pm`, so it cannot start a new process.
- It has no kernel access, so it cannot patch the loader or the filesystem checks.

That is why `ns2jb` can run homebrew on Switch 2: it reaches **sysmodule** code execution, including the `fs` sysmodule, and can launch a custom process with an ordinary sysmodule's NPDM. A browser bug alone does not reach that. Reaching NRO homebrew from a browser compromise would need a second, separate sysmodule or kernel exploit.

So "userland is fine" is true only for the first meaning. For the second meaning, the browser is step 1 of 3, and steps 2 and 3 have no public implementation on Mariko 23.0.1.

## Other candidate triggers examined

| Candidate | What it actually gives | Why it does not close stage 1 |
|---|---|---|
| Artemis Engine save loading | Lua script execution inside a game, chain-loaded from a save file | Documented for PS4 and Windows; requires placing a crafted save on the console; yields game-script level, not native code; no Switch reproduction |
| GameShare / `splay` | A Switch 2 host feeds a system applet data to parse | No public vulnerability; needs a Switch 2 host; applet-level even if broken |
| Browser / WebKit applets | A userland primitive in an applet | No public 23.0.1 chain; a browser bug would still only be stage 1 |
| Save and cartridge exploits | Game-context execution | No public native-code chain on 23.0.1 |
| Bluetooth / local wireless | Service-level parsing | Public flaws are fixed before 23.0.1; still only stage 1 or 2 |

None of these is dismissed as impossible. Each is recorded as a surface with no qualifying public chain.

## What would actually move this forward

1. **A Switch 1 package of `ns2jb`.** This would close stage 0 and possibly stages 1–2 for a console that owns SmileBASIC. It would still not be Atmosphère, because stage 3 remains.
2. **A public Mariko warmboot or pre-Horizon bug on modern firmware.** This is the decisive missing piece. It is also the piece no public source currently hints at.
3. **A public kernel exploit for 23.x plus a launch method.** A kernel exploit alone is not enough, and none is public for this firmware.

Order matters. Stage 3 is worth more than stages 0–2 combined: a boot-stage bug on 23.0.1 Mariko would be useful even without a game exploit, while another game exploit without stage 3 only produces homebrew-level access at best.

## What this does not authorize

This document is analysis, not a procedure. It does not authorize:

- executing an exploit or injecting a payload;
- updating or downgrading firmware;
- writing crafted save data to the console;
- spoofing a GameShare host or sending crafted network data;
- opening the console or installing a modchip.

Those steps are outside the project's authorization boundary, and several of them carry bricking risk. See [`SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md).

## Related records

- [`docs/ENTRY-POINTS.md`](ENTRY-POINTS.md) — surface-by-surface analysis.
- [`research/evidence-ledger.json`](../research/evidence-ledger.json) — E-050 to E-053 record the warmboot and save-based leads.
- [`research/compatibility-matrix.json`](../research/compatibility-matrix.json) — `C-023` and `C-024`.
- [`research/known-limitations.md`](../research/known-limitations.md) — what the research cannot establish.
