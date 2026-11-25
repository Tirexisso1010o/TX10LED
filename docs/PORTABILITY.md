# Portability Assessment: Switch 2 Progressions on Mariko 23.0.1

> **Snapshot: 2026-11-25.** This is a read-only assessment. It asks whether any public Switch 2 progression could be modified into a method for the target: a Switch OLED (`HEG-001`, Mariko) on firmware `23.0.1`, serial prefix `XTJ`, no modification history reported. It does not authorize running an exploit, changing console state, or weakening the Mac. The November 2026 `fs` packages are Switch 2-only, and `23.5.0` closes the `fs` bug on both families.

## Verdict

Among the Switch 2 progressions, only `ns2jb` has a technically credible port path, and it is not buildable from the public package or the current local artifacts. A separate Switch 1 artifact, CivSwitch, now supplies a public stage-1 primitive, but it is not fs-level and is untested on Switch 1 23.0.1.

| Progression | Modifiable for the OLED? | Bottom line |
|---|---|---|
| **`ns2jb` core chain** | **In principle, yes; in practice, blocked** | The author developed the SmileBASIC trigger and ROP stage on a Switch 1 and says the exploit was tested there. But no Switch 1 bootstrap, offsets, hashes, payload, or package is public, and the entry point is not owned. |
| **`mac2jb`** | **Host-side only** | Its USB typing and RPC wrapper could in principle drive a Switch 1 chain, but it supplies no target-side chain. It also requires SIP disabled and an unsigned kernel extension, which this project does not authorize. |
| **WebKit port** | **No code to modify** | Unpublished, Switch 2-specific, and the Switch 1 browser is a different, older build. The *approach* is a research idea, not a port. |
| **MintBrew / HBLauncher / GPUBrewLauncher / OunceCake / ftpd-sb / Stremio** | **Downstream** | They need a working `ns2jb` session first. They add no independent entry point. |
| **Gezine universal userland** | **Nothing to modify** | Unreleased and unverified as of 2026-11-01: no public repo, write-up, CVE, or reproduction. The `20.0.0+` floor is a Switch 2 requirement for Switch 1 compatibility mode, not a Switch 1 floor. If it ships as claimed it is the best future stage-1 lead, but it is userland only and reaching `fs` would still need a second-stage fs bug. |
| **Atmosphère 1.12.2 / hekate 6.5.5** | **Not an entry point** | Firmware-compatible with 23.0.1 and 23.5.0, but on an OLED they still require a modchip. |

## CivSwitch: a Switch 1 stage-1 artifact (2026-11-03)

CivSwitch is not a Switch 2 progression, so it is not a port candidate in the table above. It matters because it is the first public **Switch 1** stage-1 primitive found in this project that does not need SmileBASIC or a modchip.

| Property | Finding |
|---|---|
| Trigger | Civilization VII 1.0.0 **physical cartridge**; chat XSS typed by a Pico RP2040/RP2350 USB HID. |
| Primitive | JavaScript in the game's embedded V8; `addrof`/`fakeobj`; arbitrary read/write; native ROP in the game process. |
| Loader | TCP JavaScript loader on port 9026. |
| Firmware | README claims Switch 1/2 20.x.x–23.0.1; Switch 1 22.5.0 and Switch 2 20.4.0/23.0.1 are tested. Switch 1 23.0.1 is claimed but untested. |
| Stage ceiling | Game process only. The public `core.js` has no `fs` IPC, fs sysmodule payload, or privilege escalation. |
| Extra requirements | Paid 1.0.0 cartridge, Pico USB HID, English(US) system and USB-keyboard settings, local-wireless lobby. |
| Destructive option | `installer-creator` writes `XSTRIG.Civ7Save` and wipes `save:/saves/Single/`; not needed for a session-only loader test. |

For the fs-level goal, CivSwitch changes the stage-1 picture but not the stage-2 blocker. It supplies a userland process with native code and arbitrary read/write in principle, but it is tied to the Civ VII 1.0.0 game build, the public code has no fs escalation, and the exact Switch 1 23.0.1 `fs` binary is still missing. A CivSwitch-to-`fs` chain would be original work: derive the fs anchors, confirm the `Path::Normalize` bug on Switch 1 23.0.1, and build an IPC trigger from the game process.

**Status:** recorded as `L-008`, `EP-012`, `C-038`, `E-127`, `E-128`. The owner kept the free-only rule on 2026-11-03 and declined the paid cartridge, the Pico, and the console test.

## What the author actually demonstrated on Switch 1

The public write-up contains two relevant statements:

1. “This was a Switch 1 game, so the SmileBASIC agent could work on the exploit on my Switch 1, while the WebKit agent worked on the Switch 2. After some time, it got ROP.”
2. “The exploit has also been tested on the Switch 1, but I haven’t gotten around to packaging it yet. It wouldn’t provide the capabilities of a modchip, but it wouldn’t require any external hardware.”

The first statement confirms the **SmileBASIC trigger and ROP stage on a Switch 1**. The second claims **the exploit** was tested there, but it does not state the model, firmware, or how far the chain went. Neither statement claims 23.0.1, and no Switch 1 bootstrap, offsets, hashes, payload, or package is published (`E-117`).

That is enough to say a port is technically credible. It is not enough to say a Switch 1 port exists, is public, or works on `23.0.1`.

## The port in four stages

| Stage | Public material | What a Switch 1 port needs | Status |
|---|---|---|---|
| **0. Entry point** | SmileBASIC 4.4.9 | A copy the owner owns | **Blocked**: paid, delisted, not owned; the demo was removed |
| **1. Trigger** | SmileBASIC integer overflow | The same app binary; the author got ROP on a Switch 1 | **Credible**, but gated by stage 0 |
| **2. `fs` escalation** | Switch 2 `fs` offsets and hashes | A Switch 1 `fs` binary for `23.0.1`, and re-derived anchors | **Unavailable**: no `fs` NCA in the dump; keys stop at `0x14` |
| **3. Loader and payload** | Switch 2 `ro`/`ldr` behavior | A Switch 1 payload and loader-compatible behavior | **Unpublished** |
| **4. Boot stage** | None | A warmboot/package1 primitive | **Missing**; none of these supplies it |

### Why stage 2 is not a constant swap

The public `bootstrap.bas` hardcodes Switch 2 `fs` values:

- **13 distinct `CALL#` targets**, from `0x140B90` through `0x5872F0`, used for fs-side operations;
- **20 `PUT` writes** into fixed offsets of the fake filesystem and IPC structures;
- **11 content-hash gates** over fs code or data, for example `HASH#(W$(D#,128)) != 1437608693`;
- **62 `FAIL` gates** in total, including address, size, and CRC checks.

Those values are Switch 2. A Switch 1 port needs the Switch 1 `fs` binary to find the equivalent anchors and recompute the hashes. Without the binary, changing constants would fail validation or crash. The author notes that the Switch 1 root of trust is owned, so its code can be decrypted and read; that access is not available for the target `23.0.1` build with the current keys.

## Local artifact check

I parsed all 238 NCA headers in `Firmware/Firmware.23.0.1` read-only on 2026-10-31:

- **No NCA has title ID `0100000000000000` (`fs`).**
- The system program NCAs that are present in the `01000000000000xx` range, including `ldn` at `0100000000000018`, are all **key generation `0x17`**.
- The key file stops at `key_area_key_application_14` (20.0.0), so generation `0x17` content cannot be decrypted.
- Therefore the exact Switch 1 `23.0.1` `fs` binary needed for stage 2 is neither present nor decryptable with the current artifacts (`E-118`).

The modded 22.0.0 console could theoretically supply an older `fs` binary, but the owner has chosen to leave it untouched, and `22.0.0` is not `23.0.1`. A 22.0.0 binary would support a diff only if a 23.0.1 binary were also available, which it is not.

## The November 2026 Switch 2 fs chains

Between 2026-11-13 and 2026-11-24 the public `fs` exploitation scene moved from a demo to a set of Switch 2 packages. None is a Switch 1 port.

| Project | Trigger | Target | What it provides | Switch 1 status |
|---|---|---|---|---|
| **KaiHEN** (`ouncebrew/kaihen`) | Switch 2 acquisition tools, including SmileBASIC and Seedsow | Switch 2 only | Homebrew environment and minimal CFW; full system/NAND access; `ro/`, `hen/`, `bootstrap/`, `libkaihen/` | None. The README describes a Switch 2 homebrew environment; no Switch 1 build. |
| **Seedsow FS** (`Malev0/seedsow-fs-kaihen`) | Seedsow Lullaby demo/full save | Switch 2 `23.0.1` | PC-driven and console-only `fs` exploit that starts kaiHEN; warns of brick risk | None. Switch 2 only; the Switch 1 Seedsow route remains game-level Lua. |
| **CivSwitchFS** (`ItsNerisma/CivSwitchFS`) | Civilization VII 1.0.0 physical cartridge + CivSwitch loader | Switch 2 `23.0.1` | Full `fsp-srv` handle exposed as `globalThis.fspSrv`; semi-untethered; brick warnings | None. Requires Switch 2 and the paid cartridge. |
| **civ7-fs-kaihen** (`s8n/civ7-fs-kaihen`) | Civilization VII + CivSwitch | Switch 2 `<= 23.0.1` | CivSwitch + `civ7-fs` + kaiHEN; wired network; several-minute race | None. The README recommends CivSwitchFS-kaiHEN instead. |

The important point for this project is not that these packages exist; it is that **the public `fs` payloads are build- and platform-specific**. They rely on Switch 2 `fs` addresses, NCA hashes, and process behavior, and the Switch 1 `23.0.1` `fs` binary is still missing. A Switch 1 port would be original work, not a configuration change.

Two further boundaries:

- **23.5.0 closed the vulnerability.** Switchbrew records the `fs` `PathNormalizer::Normalize` overflow as fixed in `23.5.0`; the temporary buffer is now sized to the source path up to `0x600` bytes (`E-129`, `E-130`). `23.5.0` also updates the anti-downgrade fuse list. The target must stay on `23.0.1`.
- **The Switch 2 packages carry brick warnings.** CivSwitchFS warns that the race can corrupt the save, cache, or worse; Seedsow FS warns of brick risk. They are not safe substitutes for a Switch 1 test, and they are prohibited on the OLED.

### The BigInt WebKit candidate belongs to this Switch 2 group

`jamesrover45/switch2-webkit-exploit` is another Switch 2-only chain: BigInt structured-clone desync in the Switch 2 `WifiWebAuthApplet`, tested on `20.4.0`, about 5% reliable, and kernel-panic-capable on failure (`E-133`). It does not supply a Switch 1 browser primitive. Upstream WebKit `safari-613-branch` handles `BigIntTag` in the deserializer, so even the premise needs a Switch 1 build-specific check (`E-134`). It is not a shortcut around the missing Switch 1 `fs` binary or the supernag.

## What would change the verdict

1. The author publishes a Switch 1 package, or a Switch 1 bootstrap/offsets/payload.
2. The owner owns SmileBASIC 4.4.9, or a free Switch 1 entry point appears.
3. A Switch 1 `23.0.1` `fs` binary becomes available from an owner-controlled source.
4. Gezine releases the claimed universal userland exploit, with code or a write-up identifying the target process and primitives. (As of 2026-11-01 there is no public release; `E-126`.)
5. CivSwitch is reproduced on Switch 1 23.0.1 and a Switch 1 `fs` payload or the missing `fs` binary appears (`E-127`, `E-128`).
6. A Switch 1 `fs` package, or a Switch 1 Seedsow/KaiHEN port with a save-delivery route, is published. The November 2026 packages are Switch 2-only (`E-131`).
7. A stock-safe way to clear the supernag appears, or a new no-save Switch 1 entry point on `23.0.1` is found. The current target's browser is gated by a persistent local flag (`E-136`, `E-138`).

Even then, the result is stage 1–2: native code as `fs`, not kernel, bootROM, CFW, or persistence. Stage 3 remains the decisive missing link.

## What not to do

- Do not run the Switch 2 package, `mac2jb`, or a fork on the OLED.
- Do not run KaiHEN, Seedsow FS, CivSwitchFS, civ7-fs-kaihen, or the BigInt WebKit page on the OLED.
- Do not disable SIP or load the unsigned kernel extension.
- Do not download firmware, keys, or SmileBASIC.
- Do not dump or update the 22.0.0 console without explicit approval.
- Do not update the OLED to `23.5.0` or accept a supernag; the update fixes the `fs` bug and burns the anti-downgrade fuses.
- Do not attempt a stock supernag clearance; maintenance mode and console initialization do not clear it.

## References

- `E-021`, `E-022`, `E-045`, `E-046` — the `ns2jb` chain, requirements, and release status.
- `E-114`, `E-115`, `E-116` — the public package, macOS wrapper, forks, and WebKit claim.
- `E-117` — the author’s Switch 1 development and test statements.
- `E-118` — the local NCA dump check.
- `E-127`, `E-128` — the CivSwitch stage-1 primitive and its requirements.
- `E-129`, `E-130` — the 23.5.0 fs fix, the anti-downgrade fuses, and the `PathNormalizer::Normalize` details.
- `E-131` — the November 2026 Switch 2-only fs chains.
- `E-133`, `E-134` — the BigInt WebKit candidate and the upstream 613 caveat.
- `E-136`, `E-138` — the supernag mechanism and the absence of a stock clearance.
- `L-001`, `L-008`, `EP-008`, `EP-012`, `H-004` — the machine-readable lead, surface, and hypothesis records.
