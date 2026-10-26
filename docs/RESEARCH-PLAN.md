# Research Plan

> **Snapshot: 2026-10-26.** This plan replaces "look for an existing exploit" with a ranked set of falsifiable experiments. It is a research agenda, not an authorization. Each experiment states its risk and its kill criterion.

## Objective and rules of engagement

**Objective:** determine whether a new software-only chain can reach Atmosphère on a Switch OLED (`HEG-001`, Mariko) running `23.0.1`.

**Rules:**

1. A hypothesis is only interesting if it names an observation that would kill it.
2. A negative result is recorded and the direction is closed, not retried.
3. Results from Erista or Switch 2 do not transfer to Mariko without an argument for why the code is shared.
4. Nothing is claimed to work on hardware until it has been reproduced there.
5. No exploit execution, payload injection, firmware change, save injection, host spoofing, or console opening without explicit approval.

## How directions are ranked

Each direction is scored 1–5 on three axes:

- **Feasibility** — can it be executed with the materials at hand?
- **Information gain** — how much does the result change what we know?
- **Relevance** — how directly does it touch the missing stages?

The score is a planning aid, not evidence. A blocked direction can still be the most valuable one; it is marked as blocked rather than dropped.

## Ranked directions

| ID | Direction | Stage | Feasible now? | F | I | R | Score | Status |
|---|---|---|---|---|---|---|---|---|
| **D1** | capmtp PTP boundary validation (`H-001`, `H-002`) | 1 | **Yes** — console + USB host | 5 | 2 | 3 | **30** | **Closed — negative** |
| **D2** | Browser/WebKit fingerprint (`H-005`) | 1 | **Yes**, with a captive-portal setup | 3 | 3 | 3 | **27** | **Closed — negative (no JIT)** |
| **D3** | Mariko warmboot / package1 diff (`H-003`) | 3 | No — needs artifacts | 1 | 5 | 5 | **25** | Blocked |
| **D4** | `fs` path-normalization on Switch 1 (`H-004`) | 2 | No — needs a stage-1 primitive and a binary | 2 | 3 | 2 | **12** | Blocked |
| **D5** | GameShare `splay` parsing (`H-006`) | 1 | No — needs a Switch 2 host | 1 | 3 | 2 | **6** | Blocked |
| **D6** | Artemis save chain-load (`H-007`) | 1 | No — no Switch reproduction or save delivery | 2 | 2 | 1 | **4** | Blocked |

`D1` is now closed: the capmtp surface was tested on hardware and produced only documented errors. `D2` is the next runnable direction. `D3` remains the only direction that can close the decisive stage, and it is blocked because the owner cannot provide firmware artifacts.

## D1 — capmtp PTP boundary validation

**Hypotheses:** `H-001` (object-read offset/length), `H-002` (handle-table identifiers).

**What is known.** `capmtp` implements PTP over USB and exposes only operations `0x1001`–`0x100A`. The request parameters are fixed-width u32 handles, format codes, offsets, and lengths; no request carries a string or a caller-supplied buffer (`E-055`). This is a *narrow* parser surface, which is why the information gain is scored low: a negative result is the most likely outcome.

**Result (2026-10-26).** Run against the target, and **closed negative**:

- Handle-table identifiers were validated. Invalid storage, invalid format, and handles `0`, `1`, `0x7FFFFFFF`, `0x80000000`, `0xFFFFFFFF` all returned documented errors (`0x2009`, `0x200b`). The `0xFFFFFFFF` storage/parent pair returned 14 associations, which is documented "all" semantics. `H-002` is `DISPROVEN` within the tested set.
- `GetObject` (0x1009) returned **`0x2006 ParameterNotSupported`** for all ten parameter sets, including a valid handle at offset 0. Object data could not be read, so offset and length validation was never exercised. `H-001` is `UNKNOWN` with resolution `closed-negative`, because the operation is not a reachable primitive.
- A transient bulk-endpoint stall occurred during the first enumeration and cleared after a replug. It did not reproduce and is not attributed to capmtp.

Two protocol findings came out of the run: `OpenSession` must carry transaction ID 0 (`0x2004` otherwise), and the console rejects a parent handle of 0, using `0xFFFFFFFF` for "all". Both are fixed in the harness and covered by tests.

**Why it was worth running.** It was the only reachable flow in which the console parses data supplied by a device the owner controls. It is now falsified, not merely suspected, and the harness is reusable for any future USB surface.

**Next task.** With the console connected in **Copy to PC via USB** mode and at least one screenshot present:

```bash
.venv/bin/python scripts/ptp_boundary.py --family handles --dry-run
.venv/bin/python scripts/ptp_boundary.py --family handles --confirm --active
.venv/bin/python scripts/ptp_boundary.py --family objects --dry-run
.venv/bin/python scripts/ptp_boundary.py --family objects --confirm --active
```

The harness discovers the first storage and object handle, then sends boundary offsets and identifiers. It refuses non-read operations, caps reads at 2 MiB, and stops on the first timeout.

**Expected signal.** A returned length larger than the object's declared size, data inconsistent with that size, or a success response for an identifier that was never advertised.

**Kill criterion.** Every case returns a documented PTP error or a size-bounded response, and the console stays responsive. Record the run as negative and stop probing this operation.

**Risk.** A boundary request could hang or crash `capmtp`. Recovery is to disconnect the cable and reboot the console. No object is modified.

## D2 — Browser/WebKit fingerprint

**Hypothesis:** `H-005`.

**What is known.** The Switch 1 browser is NetFront-based and reachable through captive-portal and account-login applets. The `ns2jb` author cites ARM pointer authentication as a reason to avoid WebKit on Switch 2; Switch 1 does not have PAC. That makes the browser comparatively more attractive on this console.

**Next task.** Serve a controlled page through a captive portal and record the user agent, JS feature detection, and engine quirks. Map the result to public WebKit advisories. This step is fingerprinting only; it does not attempt exploitation.

**Result (2026-10-26).** The applet was reached and fingerprinted. It is a genuine stage-1 surface, and it is now characterized:

- The captive-portal DNS redirect works; the console queried `ctest.cdn.nintendo.net`, followed a 302, and executed the page's JavaScript.
- `WifiWebAuthApplet` has **no URL whitelist** and permits ignoring invalid TLS certificates.
- The User-Agent is a frozen token and identifies nothing. Feature detection brackets the engine to **Safari 15.4–15.6 (WebKit 615.x, 2022)**: `at`, `findLast`, `structuredClone`, `Error.cause`, and RegExp match indices are present; `toSorted`, `toReversed`, lookbehind, and `ArrayBuffer.transfer` are absent.
- `Intl` is entirely absent, and `WebAssembly`, `Atomics`, `SharedArrayBuffer`, `serviceWorker`, and `crypto.subtle` are unavailable.
- Web-applet NPDM grants `fsp-srv`, `nvdrv:a`, `hid:sys`, `ssl`, `bsd:a`, and `SystemSaveData`, so a compromise would be a real userland foothold, not an empty sandbox.
- `CVE-2026-2441` was ruled out: it is a Blink/Chromium CSS bug, not WebKit.

**Final result: no JIT.** A timing probe on 2026-10-26 measured a 400,000-iteration integer loop at 39-40 ms on all twelve runs, and a shape-varying variant at 48-49 ms, with no warm-up. `WebAssembly` was unavailable. The same loop shape under Node collapsed from 6-7 ms to 0-1 ms after warm-up, which is the signature of an optimizing engine. The Switch browser shows no such signature, so it is executing interpreted code. Most public WebKit exploits depend on JIT behaviour, and no public non-JIT exploit was found for the 15.4-15.6 bracket.

**Why it is still blocked.** Feature detection does not reveal the security patch level. Nintendo updates the NetFront shell between firmware versions (20.1.1 used `NF/6.0.3.27.11`; 23.0.1 uses `NF/6.0.3.31.11`) and can backport fixes without adding features. Determining the patch level needs the browser binary or controlled exploit testing. The arXiv analysis also reports no JIT in the Switch browser, which invalidates many public WebKit techniques. Even a full compromise is stage 1 only.

**Risk.** Captive-portal testing changes temporary network settings, which are reversible. It requires the owner to add a network on the console.

## D3 — Mariko warmboot / package1 diff

**Hypothesis:** `H-003`.

**Why it is the important one.** Atmosphère must run at or before boot. Caffeine proved that a warmboot exploit is sufficient on patched Erista; the equivalent on Mariko is the decisive missing stage. Everything else in this plan is a path *to* that stage.

**What blocks it.** Package1 is signed and encrypted on Mariko, and a stock console cannot dump it. This project does not accept proprietary firmware or keys. Without at least two package1 images, there is nothing to diff and no way to form a technical hypothesis about warmboot.

**Next task (once artifacts exist).** Diff package1 section 0 and the TSEC payload across versions, list parsing and bounds logic, and rank candidates by whether they are reachable before Horizon starts. Validate only in an emulator.

**Kill criterion.** No reachable defect survives review across the diffed versions.

## D4 — `fs` path normalization on Switch 1

**Hypothesis:** `H-004`.

**What is known.** The `ns2jb` write-up describes a fixed `0x301`-byte temporary buffer in `Path::Normalize` reached through `IFileSystem` `GetEntryType` with a `/..\` path. The documented filesystem API is largely unchanged between generations, which makes shared code plausible.

**Why it is not the priority.** It is stage 2. It requires a stage-1 primitive that does not exist publicly on Switch 1 `23.0.1`. Even a confirmed port would not reach Atmosphère.

**Next task.** Only after a stage-1 primitive exists: inspect a Switch 1 `fs` binary for the same normalize-and-copy sequence.

## D5 and D6 — blocked directions

- **D5 (GameShare `splay`)**: requires a Switch 2 host. The surface is documented, but there is no public protocol specification and no vulnerability.
- **D6 (Artemis save chain-load)**: the loader is documented for PS4 and Windows and yields game-level Lua, not native code. There is no documented way to place a crafted save on a stock console.

Both stay in the register as `UNKNOWN` so they are not silently forgotten.

## Task queue

| # | Task | Depends on | Status |
|---|---|---|---|
| T1 | Implement `capmtp` boundary harness with tests | — | **Done** (`scripts/ptp_boundary.py`, 20 tests) |
| T2 | Run handle family on the target | Owner approval + console connected | **Done — negative** |
| T3 | Run object family on the target | T2 + one screenshot | **Done — closed negative** |
| T4 | Record the results | T2, T3 | **Done** (`E-056`, `E-057`, `C-025`, `C-026`) |
| T5 | Browser fingerprint via captive portal | Owner approval + network setup | **Done** — engine bracketed to WebKit 615.x |
| T6 | Determine browser security patch level | Browser binary or controlled exploit testing | **Closed — moot (no JIT)** |
| T7 | Package1 differ and warmboot checklist | Legal firmware artifacts | Blocked (owner cannot provide) |
| T8 | Switch 1 `fs` comparison | Stage-1 primitive | Blocked |

## Program status

Every direction that could be executed with the owner's hardware has now been either falsified or characterized:

- **D1 capmtp**: closed negative (`E-056`, `E-057`).
- **D2 browser**: closed negative, no JIT (`E-058` to `E-064`).
- **D3 warmboot**: blocked on firmware artifacts the owner cannot provide.
- **D4 `fs`**: blocked on a stage-1 primitive.
- **D5 GameShare**: blocked on a Switch 2 host.
- **D6 Artemis**: blocked on save delivery and native escape.

No runnable software-only direction remains with the current materials. Further progress requires new public research or a lawful firmware source. That is a statement about available inputs, not proof of impossibility.

## How results are recorded

A run is recorded as one of:

- **Reproduced finding** — an observation that matches the expected signal and survives a repeat.
- **Negative result** — the kill criterion was met; the direction closes with the exact procedure and outcome.
- **Inconclusive** — the run could not be completed; the blocker is recorded.

Nothing is recorded as an exploit until it has been reproduced on hardware and shown to produce the claimed capability.

## Related records

- [`research/hypotheses.json`](../research/hypotheses.json) — the falsifiable register.
- [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md) — the stage model.
- [`docs/ENTRY-POINTS.md`](ENTRY-POINTS.md) — surfaces and leads.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — boundaries and recovery.
