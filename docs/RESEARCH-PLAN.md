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
| **D2** | Browser/WebKit n-day assessment (`H-005`) | 1 | **Yes**, with the local captive-portal harness; W2 exploratory run complete | 4 | 4 | 3 | **36** | **W1 passed 2026-10-31 (`E-112`); W2 exploratory run no Stage 1 trigger (`E-113`); candidate deprioritized** |
| **D3** | Mariko warmboot / package1 diff (`H-003`) | 3 | **No** — the 23.0.1 source console is gone; the only modded console is a 22.0.0 unit the owner has chosen to leave untouched | 2 | 5 | 5 | **30** | **Blocked — no 23.0.1 BOOT0/package1 or `0x17` keys; the 22.0.0 console is not being used** |
| **D4** | `fs` path-normalization on Switch 1 (`H-004`) | 2 | No — needs a stage-1 primitive and a binary | 2 | 3 | 2 | **12** | Blocked |
| **D5** | GameShare `splay` parsing (`H-006`) | 1 | No — needs a Switch 2 host; read-only review complete | 1 | 3 | 2 | **6** | **Blocked — no public vulnerability; `splay` program NCA is key generation `0x17`** |
| **D6** | Artemis save chain-load (`H-007`) | 1 | No — no Switch reproduction or save delivery | 2 | 2 | 1 | **4** | Blocked |
| **D7** | Browser non-JS parsers: image decoding (`H-008`) | 1 | **Yes** — the portal serves the assets | 4 | 4 | 3 | **48** | **Closed — inconclusive** |
| **D8** | SD-card FAT32 parser (`H-009`) | 2 | **Yes** — card reader and sacrificial card | 4 | 3 | 4 | **48** | **Closed — negative** |
| **D9** | LDN local-wireless pre-auth parser (`H-010`) | 2 | **Conditional** — association reached; console leaves before the LDN exchange; hostapd/AP path negative | 3 | 4 | 4 | **48** | **Negative for the current hostapd/AP path; parser untested; different AP/adapter or static analysis** |
| **D10** | General Wi-Fi and network-stack parsing (`H-011`, `H-012`) | 2 | **Conditional** — Phase 0/1, Phase 2 Batch 1/2, and Phase 3 complete; Phase 4 control/D-01 complete; remaining blocked by adapter data path | 4 | 3 | 3 | **36** | **Phase 4 control/D-01 complete; remaining cases blocked by adapter** |

`D1`, `D7`, and `D8` are closed. `D2` is reopened for one specific no-JIT candidate after the 2026-10-30 read-only WebKit review; W1 passed on 2026-10-31. The W2 exploratory run on 2026-10-31 loaded the pinned public PoC in four short modes but produced no Stage 1 trigger, alert, crash, reboot, or hang; it deviated from the single-load protocol, so it is not a clean negative. The candidate is deprioritized. `D3` is blocked on 23.0.1 artifact availability: the source console is no longer available, its dump is NCA-only, and the remaining modded console runs 22.0.0 but the owner has chosen to leave it untouched. `D4`–`D6` remain blocked on primitives or hosts. `D5`'s read-only review found no public `splay`/GameShare vulnerability and no post-20.0.0 `splay` security fix; the local `splay` program NCA is key generation `0x17` and cannot be decrypted with the owner's keys, while the only key-generation-`0x15` program is the Mii editor applet `miiEdit` (`E-102`, `E-103`). `D9` is negative for the current hostapd/AP path, and `D10` is the next gated direction: `D9` Phase 1 confirmed the passive advertisement path, the owner's keys decrypt the advertisement and confirm security mode 1, and prod-mode hosts emitted valid AES-CTR advertisements, but the console never joined. An AP-mode control proved the adapter can transmit, and AP-mode `NL80211_CMD_FRAME` beacon injection works, while a monitor-mode control showed that monitor-mode injection does not transmit. The current monitor-mode host path is blocked by `rtw88_8822bu`, and a broadcast vendor action frame is blocked by the station lookup. A unicast control with a temporary station entry and a non-LDN test OUI was accepted by the kernel without a netlink error. A real LDN unicast run then sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID, all accepted by the kernel, but the console was off/away, so reception was not observed. The driver rejects a broadcast-BSSID action frame with `EINVAL`, so only the AP-BSSID variant is available. A supervised rerun on 2026-10-29 made the room `TX10LED` appear, but selecting it produced `2203-0065` immediately and hostapd recorded no authentication or association event (`E-098`). The room appearance confirms the advertisement reaches the console; that join failed because the hostapd WLAN SSID/security did not match the room's 32-character hexadecimal SSID and LDN RSN IE. A second supervised run with the corrected WLAN parameters reached open-system authentication, association with AID 1, and `authorized=1`, but the console disassociated with reason 8 about one second later and sent no observed `0x88B7` request (`E-099`). A third supervised run omitted the association-response RSN IE, captured raw frames on `mon-ldn`, and used the authorized-station raw `0x88B7` response path (`E-100`), but the console again disassociated with reason 8 before `0x88B7` (`E-101`). The current hostapd/AP path is negative for `D9`; the parser hypothesis remains untested. Another active LDN run requires a materially different AP implementation or adapter/driver and new approval. `D3` remains the only direction that can close the decisive stage; its blocker is now 23.0.1 artifact availability, not tooling alone. `D10` Phase 0, Phase 1, Phase 2 Batch 1/2, Phase 3 control E-C, and Phase 3 Batch 1 are complete: an open and a WPA2 AP reached `AP-ENABLED` on channel 1, both SSIDs were visible from the independent macOS scan at -34 dBm, and the host services passed start/stop checks (`E-104`). In Phase 1 the console associated to both test APs, completed the WPA2 pairwise handshake, obtained DHCP lease `192.168.77.94`, and queried `ctest.cdn.nintendo.net`; Test Connection failed at the internet step with `2110-3128` because the AP had no NAT (`E-105`). Phase 2 Batch 1 sent the `W-C` control and `W-01`–`W-08`; there was no crash, reboot, hang, or new error, but `W-06` (DS Parameter IE length 3) showed a shorter association lifetime (7.3 s and 15.4 s) than the 35.4 s control and re-associated immediately (`E-106`). Phase 2 Batch 2 sent the control and `W-09`–`W-14`; there was again no crash, reboot, hang, or new error, but `W-09` (Vendor IE length 0) showed a 14.7 s lifetime versus the 35.6 s control (`E-107`). Those are behavioral leads, not memory-safety findings. Phase 3 control E-C completed the WPA2 pairwise handshake and three group rekeys; Batch 1 sent `E-01`–`E-08` one frame per association through the control port, all accepted, with the station associated at 10 s and lifetimes 35.0–35.4 s (`E-108`). Batch 2 sent `E-09`–`E-14` the same way, all accepted, with lifetimes 35.1–35.5 s (`E-109`). Those are clean negatives for the tested header/descriptor and key-data fields, with a zero/invalid-MIC limitation. Phase 4 control C passed the DHCP/DNS stages and failed at the internet step with `2110-3129`; D-01 (DHCPOFFER option 1 length 0) caused `2110-2963` with no crash and a normal 30.1 s lifetime (`E-110`). The remaining Phase 4 DHCP/DNS cases are blocked by the adapter's intermittent AP data path. A normal AP can expose the `wlan` supplicant and the `bsdsocket`/`ssl` stack through the console's Test Connection flow. Phases 5–6 remain gated by a separate approval.

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

**Final result: no JIT.** A timing probe on 2026-10-26 measured a 400,000-iteration integer loop at 39-40 ms on all twelve runs, and a shape-varying variant at 48-49 ms, with no warm-up. `WebAssembly` was unavailable. The same loop shape under Node collapsed from 6-7 ms to 0-1 ms after warm-up, which is the signature of an optimizing engine. The Switch browser shows no such signature, so it is executing interpreted code. Most public WebKit exploits depend on JIT behaviour. The original review found no public non-JIT exploit for the 15.4-15.6 bracket; a 2026-10-30 follow-up found one (see below).

**Reopened (2026-10-30).** A read-only review identified `CVE-2023-28205` as the only candidate in the reviewed set that combines a public PoC, no JIT requirement, and a reachable structured-clone path. It is a JavaScriptCore `SerializedScriptValue`/`CloneDeserializer` use-after-free: non-GC-scanned `Vector` containers hold `Map`/`Date` objects during deserialization, a GC cycle frees them, and deserialization continues through dangling pointers. The fix commit `c9880de` replaces those containers with `MarkedVector`. The public MIT-licensed PoC targets WebKit-613.1.17.1 and uses `postMessage` with a `Map`/`Date` graph; the applet's UA token is `AppleWebKit/613.0` and its feature set brackets Safari 15.4-15.6, so the lineage is adjacent but not an exact build match. Before the W2 exploratory run on 2026-10-31, the PoC had not been run on the console; Nintendo may have backported the fix. The local runner `scripts/webkit_portal.py`, probe `scripts/webkit_probe.html`, and tests are validated on loopback. **W1 passed on 2026-10-31:** the applet loaded the probe and round-tripped a `Map`/`Date` graph through `postMessage` (`ok=true`, `mapSize=1`, `dateValue=0`), with `postMessage`, `MessageChannel`, `BroadcastChannel`, `Worker`, `structuredClone`, `localStorage`, and ES modules present; no error event occurred and the console behaved normally (`E-112`). The runner now also has a tested `--site` mode and `--entry-query` for the PoC's `?autorun=1`. The W2 exploratory run on 2026-10-31 loaded the pinned PoC in four short modes; the module graph loaded, but the page logged only `Attempt` lines and produced no Stage 1 trigger, alert, crash, reboot, or hang. The run deviated from the single-load protocol, so it is not a clean negative; the candidate is deprioritized and no repeat is planned without a new hypothesis. Even a successful browser compromise is stage 1 only. See [`docs/WEBKIT-NDAY-PLAN.md`](WEBKIT-NDAY-PLAN.md).

**Why it is still blocked.** Feature detection does not reveal the security patch level. Nintendo updates the NetFront shell between firmware versions (20.1.1 used `NF/6.0.3.27.11`; 23.0.1 uses `NF/6.0.3.31.11`) and can backport fixes without adding features. Determining the patch level needs the browser binary or controlled exploit testing. The arXiv analysis also reports no JIT in the Switch browser, which invalidates many public WebKit techniques. Even a full compromise is stage 1 only.

**Risk.** Captive-portal testing changes temporary network settings, which are reversible. It requires the owner to add a network on the console.

## D3 — Mariko warmboot / package1 diff

**Hypothesis:** `H-003`.

**Why it is the important one.** Atmosphère must run at or before boot. Caffeine proved that a warmboot exploit is sufficient on patched Erista; the equivalent on Mariko is the decisive missing stage. Everything else in this plan is a path *to* that stage.

**What blocks it.** Package1 is signed and encrypted on Mariko, and a stock console cannot dump it. The owner supplied a **local** 23.0.1 firmware dump and `prod.keys` from a modded 23.0.1 Switch that is no longer available; both are excluded from version control and must never be published. A modded 22.0.0 console remains, but the owner has chosen to leave it untouched; its keys do not cover generation `0x17`, and it cannot supply 23.0.1 package1. The dump is **NCA-only**: it contains no package1, package2, or KIP files, and package1 lives in BOOT0. The key file also stops at key generation `0x14` (20.0.0), while the 23.0.1 NCAs use up to `0x17` (23.0.0), so the newer NCAs cannot be decrypted. No `hactool` or `nxdump` is installed. A single dump is not enough for a version diff either; a second firmware version would be needed.

**Next task (once tooling exists).** Extract and verify package1 from the owner's dump, then diff section 0 and the TSEC payload across at least two versions, list parsing and bounds logic, and rank candidates by whether they are reachable before Horizon starts. Validate only in an emulator. Keep every extracted artifact local.

**Kill criterion.** No reachable defect survives review across the diffed versions.

## D4 — `fs` path normalization on Switch 1

**Hypothesis:** `H-004`.

**What is known.** The `ns2jb` write-up describes a fixed `0x301`-byte temporary buffer in `Path::Normalize` reached through `IFileSystem` `GetEntryType` with a `/..\` path. The documented filesystem API is largely unchanged between generations, which makes shared code plausible.

**Why it is not the priority.** It is stage 2. It requires a stage-1 primitive that does not exist publicly on Switch 1 `23.0.1`. Even a confirmed port would not reach Atmosphère.

**Next task.** Only after a stage-1 primitive exists: inspect a Switch 1 `fs` binary for the same normalize-and-copy sequence.

## D5 and D6 — blocked directions

- **D5 (GameShare `splay`)**: requires a Switch 2 host. The 2026-10-29 read-only review found no public `splay`/GameShare vulnerability and no post-20.0.0 `splay` security fix. The local `splay` program NCA is key generation `0x17` and is blocked by the missing `key_area_key_application_16`; its meta CNMT is readable and matches the program NCA. The only program that decrypts with the current keys is the Mii editor applet `miiEdit` at key generation `0x15`, which is not a remote-input surface (`E-102`, `E-103`).
- **D6 (Artemis save chain-load)**: the loader is documented for PS4 and Windows and yields game-level Lua, not native code. There is no documented way to place a crafted save on a stock console.

Both stay in the register as `UNKNOWN` so they are not silently forgotten.

## D7 — Browser non-JS parsers (image decoding)

**Hypothesis:** `H-008`.

**Why this is new.** The no-JIT result closed *JavaScript* exploitation, but the applet still decodes images in-process. Image decoders are a classic JIT-independent target, and the applet has no URL whitelist, so the portal server can serve any file.

**Leading candidate.** `CVE-2023-4863` is a heap buffer overflow in libwebp's Huffman table construction, reachable through a crafted WebP, fixed in libwebp 1.3.2 in September 2023 and exploited in the wild. The target engine is a 2022 WebKit generation, so it would be unpatched unless Nintendo backported the fix.

**First step (safe).** Run `scripts/fingerprint_formats.html` with `scripts/assets/`. It loads a small PNG, JPEG, GIF, BMP, WebP, and SVG and reports which decode. That establishes whether the decoders are reachable at all. It does not test any vulnerability.

**Second step (needs approval).** Only if WebP decodes, test a public crash reproducer and record whether the applet faults. That is exploit testing.

**Result (2026-10-26).** Closed inconclusive.

- All six image formats decode, including lossless WebP, so the Huffman path is reachable.
- The console decoded both public reproducers to 1x1 images. Stock libwebp 1.2.4, 1.3.1, and 1.6.0 reject the same files, so the console's decoder is **non-stock** — consistent with an older or custom implementation that lacks the validation added in 2023.
- Sixty repeated decodes of the stronger file (`nso.webp`, `color_cache_bits=6`) produced no visible fault and the applet stayed responsive.
- The reproducer was validated locally with ASAN against vulnerable commit `7ba44f8`, so the trigger is real; but without ASAN a silent 4-byte-to-430-byte overflow cannot be observed.

**Why it closes.** A no-fault result is unobservable evidence, and repeating it would not add information. Confirming the overflow would need the decoder binary, ASAN, or heap-grooming work that is indistinguishable from exploit development. Even a confirmed trigger would be applet-level and would not provide SD homebrew.

**Kill criterion.** WebP is not decoded, or the decoder rejects crafted input without faulting.

## D8 — SD-card FAT32 parser

**Hypothesis:** `H-009`.

**Result (2026-10-27).** Closed negative on the tested anomalies:

- A control image mounts, and a real console screenshot placed at a crafted `NINTENDO/ALBUM/YYYY/MM/DD` path is listed.
- An out-of-range **file** entry is skipped cleanly; the valid file next to it is listed.
- An out-of-range **directory** entry makes the Album applet hang briefly and report `2802-9999`, a handled failure with no crash report.
- A BPB with zero sectors-per-cluster is rejected at mount with a format prompt.

No memory-safety signal appeared. The tested inputs were either validated at mount, skipped at enumeration, or handled as an applet error. Remaining anomalies (cyclic chains, near-boundary clusters) would test hang behaviour rather than code execution, and the surface is a denial-of-service path at best.

## D9 — LDN local-wireless pre-auth parser

**Hypothesis:** `H-010`.

**Why this is now runnable.** The owner wanted to keep the workflow on macOS. Native macOS cannot inject 802.11 frames, so the radio runs in an OrbStack Ubuntu 26.04 VM with a TP-Link Archer T3U Plus passed through. The adapter uses `rtw88_8822bu`, supports monitor mode, and captured real LDN advertisements. Its AP-mode transmit path is confirmed, but its monitor-mode injection path is not: the driver reports `failed to get tx report from firmware`, and a monitor-mode control did not appear on the Mac, so the plaintext and prod-mode runs are inconclusive. The LDN protocol is publicly documented, and `CVE-2026-82079` — a stack overflow in local wireless fixed in 23.0.0 — shows that this parser has recently handled security-relevant input. The target is on 23.0.1, so that specific bug is patched; this direction looks for a different defect.

**Why the "emulate a Switch 2" version does not work.** There are three different sharing paths, and only one is reachable from a PC:

- **Virtual Game Cards** require a Nintendo Account, an internet connection, local-wireless proximity, and a server-issued license (`E-079`). A PC cannot act as a linked console.
- **GameShare / `splay`** requires a real Switch 2 host. The host's `AdvertiseData` is ECC-verified, the protocol is not publicly specified, and a PC cannot produce a valid signed host advertisement (`E-038`–`E-044`, `L-006`).
- **LDN pre-auth** is the remaining surface: a PC can observe and, with approval, transmit LDN frames without a second console or Nintendo signing keys.

**The key gate — now open, locally.** Retail LDN uses security mode 1 (AES-encrypted). The key derivation needs `prod.keys`. The owner supplied a local dump from their own modded Switch, and it decrypts the Phase 1 advertisement with key-derivation protocol 1 (`E-081`): security mode 1, challenge present, channel 1, max 2 participants, app version 26. The keys must never be committed, published, or shared. Two active paths remain: a PC-hosted **prod-mode** room built from the captured parameters (preferred), and the no-key **security mode 3** plaintext control that the `kinnay/LDN` package supports (`E-078`). Both need a working TX path.

**First step (safe) — completed 2026-10-28.** The console hosted a Dragon Ball FighterZ local-wireless room; the VM captured 64 advertisement frames and parsed the plaintext `NetworkId` header (title `0100a250097f0000`, scene `0`, LDN version `4`, AES-CTR, channel `1`). The full procedure is in [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md), and the sanitized record is [`research/hardware-observations/2026-10-28-ldn-phase1.json`](../research/hardware-observations/2026-10-28-ldn-phase1.json). No keys, no transmission, no console state change.

**Second step — executed once, inconclusive.** The owner approved one run. The console was in join/scan mode and the host advertised a plaintext, no-challenge LDN network with the captured parameters. The host started and stopped cleanly, but the console showed no room, the host logged no `JOIN`, and `dmesg` reported `failed to get tx report from firmware`. Host transmission is unconfirmed, so the result does not show whether the console would accept the network. A follow-up 60-second CoreWLAN scan for the SSID was invalid: the LDN beacon uses a null SSID and the network ID is inside vendor action frames, so a wildcard Wi-Fi scan cannot see it.

**Prod-mode step — executed three times, still inconclusive.** The host was extended to security mode 1 with the owner's keys and the captured title/scene/SSID/channel. It emitted 373 AES-CTR advertisements on channel 1; the first decrypted with the owner's keys, validated its SHA-256, and matched the Phase 1 room fields (title `0100a250097f0000`, scene `0`, LDN version `4`, security mode `1`, challenge present, max `2`, app version `26`, 4 bytes of application data, same SSID). The host logged no `JOIN`, the console reported no rooms after a roughly one-second search, and neither same-phy capture saw a console frame. The captures may be loopback and `dmesg` logged another TX-report failure, so RF transmission is still unconfirmed (`E-084`, `E-085`). The directed CoreWLAN scan used during the run is invalid: a control scan for a random non-existent 16-byte SSID also returned `FOUND` with a nil BSSID (`E-086`).

A second 30-second run triggered the console search after the host was already advertising. The host again logged no `JOIN`, the console again reported no rooms, and `dmesg` TX-report failures rose from 4 to 5. The wrapper's `tcpdump` processes failed with `Permission denied` on the previous run's tcpdump-owned pcaps, so there is no valid run-2 capture. Ten wildcard CoreWLAN scans did not find the host BSSID, but a post-run control scan returned 10 ambient networks with a nil BSSID for every one; the wildcard BSSID comparison was therefore invalid, not negative, for an unpermitted process (`E-087`, `E-088`). Location Services later restored real BSSIDs (`E-092`).

A third run on 2026-10-29 used the fixed wrapper and a Location Services-enabled independent scan. The host again logged no `JOIN`, the console again reported no rooms, and `dmesg` TX-report failures rose from 5 to 6. The independent scan saw a hidden ambient BSSID but not the host BSSID; the captures contained only host frames, and each injected frame appeared as a radiotap pair with `txflags=0x0` (`E-089`). An AP-mode control proved the adapter can transmit at -32 dBm (`E-090`), while a monitor-mode control showed that monitor-mode injection does not transmit (`E-091`). The current host path is therefore blocked by the driver, not by a console rejection. Location Services restored real BSSIDs for the independent scanner (`E-092`).

An approved AP-mode control then tested `NL80211_CMD_FRAME` directly. hostapd 2.11 reached `AP-ENABLED` with `TX10LED-TEST` on channel 1, and 20 `TX10LED-APINJ` beacons submitted through `NL80211_CMD_FRAME` were seen by the Mac at -28 dBm in all 12 scans, alongside the hostapd beacon (`E-094`). The AP-mode beacon half of management-frame injection therefore works on this adapter. A source review of upstream mac80211/nl80211 found that a non-public action frame on an AP interface needs a station entry; a broadcast destination is not a station, so a broadcast LDN vendor action is rejected with `-ENOLINK` even with `NL80211_ATTR_FRAME_NO_STA` (`E-093`). A follow-up approved unicast control added a temporary station entry for the console's MAC and submitted five unicast vendor actions with a non-LDN test OUI; all five were accepted without a netlink error and the station entry was removed (`E-095`). This confirms the kernel-level station-lookup half of the AP path. It does not show that the console received the frame or that its LDN parser reacted, because the test OUI was not LDN and no independent capture was made. The next AP step is a real LDN unicast vendor action through this path, which requires new explicit approval; a different adapter/driver remains the fallback.

On 2026-10-29 the owner approved the real LDN unicast run. The first attempt sent 0 advertisements because `rtw88_8822bu` rejected the broadcast-BSSID action frame with `EINVAL`. A diagnostic showed that both the 1,388-byte LDN frame and a 42-byte control failed with a broadcast BSSID and succeeded with the AP BSSID, while all beacon variants, including the 89-byte null-SSID LDN beacon, were accepted (`E-097`). The rerun used the AP BSSID and sent 568 valid AES-CTR advertisements plus 568 null-SSID beacons at 100 ms intervals; all requests were accepted, the station entry was removed, and monitor mode was restored (`E-096`). The console was off/away during that first run, so the room appearance and parser reaction were not observed; that run is inconclusive. `dmesg` reported a firmware download failure after hostapd stopped, and the adapter required a USB deauthorize/reauthorize cycle before it probed cleanly again. The AP-BSSID variant differs from the original broadcast advertisement, so whether the console accepts it was the main open question. A supervised rerun answered it: the room `TX10LED` appeared, but selecting it produced `2203-0065` immediately and hostapd logged no authentication, association, or station event (`E-098`). The console returned to the game normally. The hostapd WLAN SSID was `TX10LED-TEST` with open security, not the room's 32-character hexadecimal SSID and LDN RSN IE, so the join failed at the WLAN configuration layer before the custom `0x88B7` exchange.

A second supervised run on 2026-10-29 used the room's 32-character hexadecimal WLAN SSID, `ignore_broadcast_ssid=2`, and the LDN RSN IE. The console completed open-system authentication, associated with AID 1, and hostapd marked the station authorized. About one second later the console sent a disassociation with `reason_code=8`; hostapd logged `AP-STA-DISCONNECTED` and later deauthenticated the station due to inactivity. The harness sent 54 advertisements, received 0 `0x88B7` authentication frames, and ended with `joined=False`. The `mon-ldn` monitor saw one 28-byte console data frame (`flags=16`, FCS included), consistent with a null-data frame and not the 946-byte authentication request. The AP raw socket saw one 20-byte frame with ethertype `0x0006`; its payload was not preserved. The owner observed `2203-0066` after a few seconds and the game popup `unable to join the room`; the console returned to the game normally (`E-099`; [`2026-10-29-ap-mode-ldn-join-observed.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-join-observed.json)). The association response included an RSN IE that the `ldn` package's `MonitorAP` does not send; that mismatch is the leading candidate for the disassociation, but it is not proven.

A third supervised run on 2026-10-29 omitted the association-response RSN IE to match the `ldn` `MonitorAP`, enabled raw-frame diagnostics and a local `mon-ldn` pcap, and used the authorized-station raw `0x88B7` response path. The console again authenticated, associated with AID 1, and was marked authorized, then sent one 28-byte null-data frame and disassociated with `reason_code=8` about 1.4 seconds after association. The pcap contains no console data payload frame and no `0x88B7` request; the owner saw `2203-0066` again and the game popup `unable to join the room` (`E-101`; [`2026-10-29-ap-mode-ldn-join-third.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-join-third.json)). Omitting the association-response RSN IE did not change the outcome. The pcap shows that the console's probe request and the hostapd probe response both carried the real 32-byte SSID, but hostapd beacons carry a zero-length SSID while the `ldn` `MonitorAP` sends 32 zero bytes. That beacon-SSID difference is the leading remaining host-side candidate; capability information, the extended-capabilities IE, and hostapd's state machine versus the reference `MonitorAP` are also untested. The current hostapd/AP path is negative for `D9`.

A local response-path control showed that `NL80211_CMD_CONTROL_PORT_FRAME` rejects ethertype `0x88B7` with `EINVAL`, while EAPOL `0x888E` is accepted. An AF_PACKET raw `0x88B7` frame is transmitted as a protected CCMP data frame with KeyID 0 when the station is authorized and the pairwise key is installed; without authorization the socket accepted the frame but it was not transmitted (`E-100`). The harness now logs the 802.11 subtype and redacted payload hex, writes an optional local pcap on `mon-ldn`, and defaults to omitting the association-response RSN IE (`--include-assoc-rsn` reproduces the earlier behavior). The next run must use those defaults and the raw authorized-station response path.

**Third step — read-only, in progress.** The owner's keys decrypt the Phase 1 advertisement and confirm the room is prod mode with the challenge enabled (`E-081`). The next no-radio step is to extract the `ldn` sysmodule from the owner's firmware dump and compare its parser against the 23.0.0 fix for `CVE-2026-82079`. No extraction tool is installed yet; if none can be obtained without downloading firmware or keys, record the tooling gap. The supplied key file stops at generation `0x14`, while the `ldn` NCA uses `0x17`, so the content is currently undecryptable (`E-083`).

**Next active step — no further same-config run.** The real LDN unicast run was executed (`E-096`), a supervised rerun made the room appear but failed the join with `2203-0065` (`E-098`), a second supervised run with the corrected WLAN parameters reached authentication and association before the console left with reason 8 (`E-099`), and a third supervised run omitted the association-response RSN IE and used the raw authorized-station response path, but the console again left before `0x88B7` (`E-101`). The current hostapd/AP path is negative for `D9`. Do not repeat the same hostapd configuration. A further active LDN test would need a materially different AP implementation that sends a 32-zero-byte beacon and reproduces the `ldn` `MonitorAP` association behavior, or a different adapter/driver with working monitor-mode TX; both require new explicit approval. Otherwise, the next LDN step is read-only: decrypt the `ldn` NCA with a key set that covers key generation `0x17`, extract the NSO, and compare the parser against the 23.0.0 fix for CVE-2026-82079. The key file currently stops at `_14`, so this is blocked on key coverage. If neither path is available, record `D9` as blocked on tooling and move to a different surface.

**Kill criterion.** After host transmission is independently confirmed, the console rejects the prod-mode network **and** every plaintext/no-key variant; or the adapter cannot capture/transmit LDN action frames and no known-good adapter or second host is available; or the firmware cannot be parsed with the available tools. If the console joins but every malformed authentication response is rejected cleanly, record as negative.

**Risk.** A malformed frame could hang or crash the `ldn` sysmodule or Wi-Fi firmware. Recovery is to stop the host, power-cycle the console, and restart the adapter. No storage is written. Active frame injection requires explicit approval for the specific run.

**Capability ceiling.** A pre-auth bug in `ldn` would be stage 2 at best. It would not by itself reach boot-stage execution, and a full chain would still need a kernel or warmboot stage.

## D10 — General Wi-Fi and network-stack parsing

**Hypotheses:** `H-011` (802.11 management/EAPOL), `H-012` (DHCP/DNS/IPv6/TLS).

**Why this is next.** `D9`'s hostapd/AP path is negative, but it proved the adapter can run an AP and inject beacons. A normal AP keeps the console associated and exposes the `wlan` supplicant and the `bsdsocket`/`ssl` stack through the built-in **Test Connection** flow. Switchbrew's 23.0.0 changelog records a `bsdsocket` AddrInfo deserialization fix; the target has that fix, so this direction looks for a different defect. No public 23.0.1 vulnerability is known or claimed.

**What is reachable.** Phase 1 must establish a normal open and WPA2 association; the LDN AP association is evidence, not a substitute. Phase 2 uses AP-mode `NL80211_CMD_FRAME` beacon injection (confirmed in `E-094`) for one malformed IE at a time, and hostapd `vendor_elements`/`assocresp_elements` for vendor IEs. Phase 3 sends EAPOL-Key frames through `NL80211_CMD_CONTROL_PORT_FRAME` only after a clean rekey control (`E-100`). Phases 4–6 use the console's Test Connection for DHCP/DNS, IPv6 RA/ND only if the console uses IPv6, and TLS only through an approved local sinkhole for the connectivity-test hostname.

**What is not reachable with stock hostapd.** Arbitrary non-vendor association-response IEs and arbitrary EAPOL pre-handshake timing require a patched hostapd or a userspace AP. Those cases are marked deferred; they are not silently attempted with a different frame.

**Kill criteria.** A phase is negative if the control is clean and every approved case produces no crash, reboot, hang, or new error and the console remains responsive. A phase is blocked if the console cannot associate or the host cannot transmit the required frame. A reproducible crash tied to one input is a lead, not an exploit. `D10` is negative if every reachable phase is negative.

**Risk.** A malformed frame or response could hang or crash a network sysmodule or the Wi-Fi firmware. Recovery is to stop the host, restore the adapter, delete the test SSID, and power-cycle the console. No internal storage is written. Active frames need explicit approval for the exact batch. Phase 6 must not capture credentials or proxy account/eShop traffic.

**Capability ceiling.** `wlan`, `bsdsocket`, `sfdnsres`, `nifm`/`bsdcfg`, and `ssl` are system services or sysmodules. A fault is stage 1–2 at best. A Wi-Fi firmware fault is below Horizon but not boot-stage. Atmosphère still needs warmboot/package1 execution, which remains blocked.

The full matrix, controls, approval record, stop conditions, and recovery steps are in [`docs/WIFI-NETWORK-TEST-PLAN.md`](WIFI-NETWORK-TEST-PLAN.md).

## Task queue

| # | Task | Depends on | Status |
|---|---|---|---|
| T1 | Implement `capmtp` boundary harness with tests | — | **Done** (`scripts/ptp_boundary.py`, 20 tests) |
| T2 | Run handle family on the target | Owner approval + console connected | **Done — negative** |
| T3 | Run object family on the target | T2 + one screenshot | **Done — closed negative** |
| T4 | Record the results | T2, T3 | **Done** (`E-056`, `E-057`, `C-025`, `C-026`) |
| T5 | Browser fingerprint via captive portal | Owner approval + network setup | **Done** — engine bracketed to WebKit 615.x |
| T6 | Determine browser security patch level | Browser binary or controlled exploit testing | **Closed — moot (no JIT)** |
| T7 | Package1 extraction, verify, and warmboot checklist | A 23.0.1 BOOT0/package1 image + matching keys + a second firmware version | Blocked — the 23.0.1 source console is gone; the only modded console is a 22.0.0 unit the owner has chosen to leave untouched |
| T8 | Switch 1 `fs` comparison | Stage-1 primitive | Blocked |
| T9 | WebP reproducer on the console | Owner approval | **Done — no fault, inconclusive** |
| T10 | SD FAT32 anomaly matrix | Card reader + sacrificial card | **Done — handled rejects, no memory signal** |
| T11 | LDN passive capture, plaintext-host, then prod-mode host | macOS + OrbStack VM + compatible adapter + owner approval | **Phase 1 done; room appears; association reached; console leaves before `0x88B7`; hostapd/AP path negative** |
| T12 | Malformed LDN authentication responses | T11 join + separate approval | Not started |
| T13 | Extract and analyze the `ldn` sysmodule from the owner's firmware | `key_area_key_application_16` + extraction tooling | Blocked on key coverage; `ldn` NCA identified |
| T14 | Draft and wire the general Wi-Fi/network test plan (`D10`) | `E-090`, `E-094`, `E-095`, `E-100` | **Done — plan drafted; Phase 0 complete (`E-104`)** |
| T15 | Establish the open/WPA2 baseline and capture the Test Connection flow | T14 + owner approval for Phase 1 + console present | **Done — baseline complete (`E-105`); internet step failed as expected (no NAT)** |
| T16 | Run approved 802.11/EAPOL and DHCP/DNS/IPv6/TLS batches | T15 + separate approval per batch | **Phase 4 control/D-01 complete; remaining blocked by adapter data path; W-06/W-09 leads remain** |

## Program status

Every direction that has been executed with the owner's hardware has been either falsified or characterized. `D10` Phase 0, Phase 1, Phase 2 Batch 1/2, Phase 3 control E-C, and Phase 3 Batch 1 are complete; Phase 2 sent the approved malformed beacons with `W-06`/`W-09` behavioral leads, and Phase 3 Batch 1 was a clean negative:

- **D1 capmtp**: closed negative (`E-056`, `E-057`).
- **D2 browser**: W1 reachability passed on 2026-10-31 (`E-112`); the W2 exploratory run loaded the pinned `CVE-2023-28205` PoC but produced no Stage 1 trigger (`E-113`); not a clean negative; deprioritized.
- **D3 warmboot**: blocked on 23.0.1 artifact availability and key coverage. The owner's local 23.0.1 dump is NCA-only, the key file stops at generation `0x14`, and the modded 23.0.1 source console is no longer available. The remaining modded console runs 22.0.0 and will be left untouched, so it cannot support either a 23.0.1 boot-chain diff or a comparative dump.
- **D4 `fs`**: blocked on a stage-1 primitive.
- **D5 GameShare**: blocked on a Switch 2 host.
- **D6 Artemis**: blocked on save delivery and native escape.
- **D7 browser image parsers**: closed inconclusive (non-stock decoder accepted the reproducer; no observable fault).
- **D8 SD-card FAT32 parser**: closed negative on tested anomalies (mount rejection, entry skip, handled applet error; no crash report).
- **D9 LDN pre-auth parser**: negative for the current hostapd/AP path; the parser hypothesis remains untested. Passive capture succeeded. The owner's local keys decrypt the advertisement and confirm security mode 1 (prod), challenge enabled, max 2 participants, app version 26 (`E-081`). One approved plaintext-host run produced no join, but the adapter's transmit path is unconfirmed (`failed to get tx report from firmware`). The 60-second CoreWLAN TX check was invalid because the LDN beacon uses a null SSID. A later prod-mode host emitted 373 AES-CTR advertisements that decrypted to the same room, but the console still reported no rooms, the host logged no `JOIN`, and the same-phy captures saw no console frames (`E-084`, `E-085`). The directed CoreWLAN scan is invalid because it returns false positives for non-existent 16-byte SSIDs (`E-086`). A second prod-mode run again produced no join and no room; its pcap capture failed on a wrapper permission error, and the wildcard BSSID scan is invalid because macOS returned a nil BSSID for every network (`E-087`, `E-088`). On 2026-10-29 run 3 again produced no join and no room; the independent Location Services-enabled scan saw a hidden ambient BSSID but not the host BSSID (`E-089`). An AP-mode control proved the adapter can transmit at -32 dBm (`E-090`), while a monitor-mode control showed that monitor-mode injection does not transmit (`E-091`). Location Services restored real BSSIDs for the independent scanner (`E-092`). A follow-up AP-mode `NL80211_CMD_FRAME` test put a 20-frame test beacon on the air at -28 dBm in all 12 scans (`E-094`), so the beacon half of the AP path works. The vendor-action half is still blocked for broadcast: a non-public action frame on an AP interface needs a station entry and is rejected with `-ENOLINK` (`E-093`). A unicast control with a temporary station entry and a non-LDN test OUI was accepted by the kernel without a netlink error (`E-095`). A real LDN unicast run then sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID; all requests were accepted, but the console was off/away, so reception was not observed (`E-096`). The driver rejects a broadcast-BSSID action frame with `EINVAL`, so only the AP-BSSID variant is available (`E-097`). A supervised rerun made the room `TX10LED` appear, but selecting it produced `2203-0065` immediately and hostapd saw no authentication or association (`E-098`). The room appearance confirms the scan path; that join failure is consistent with the hostapd WLAN SSID/security not matching the room. A second supervised run with the room's 32-character hexadecimal WLAN SSID and the LDN RSN IE reached authentication, association (AID 1), and `authorized=1`, then the console disassociated with reason 8 about one second later; no `0x88B7` request was observed (`E-099`). The third supervised run omitted the association-response RSN IE and used the raw authorized-station response path, but the console again disassociated with reason 8 before `0x88B7` (`E-101`). The AP control port rejects `0x88B7` with `EINVAL` while the raw authorized-station path transmits it protected with KeyID 0 (`E-100`). The current hostapd/AP path is negative for `D9`; the leading remaining host-side difference is the beacon SSID encoding (hostapd zero-length versus the `ldn` MonitorAP's 32 zero bytes). A materially different AP implementation, a different adapter/driver, or static analysis of the `ldn` NCA is the next step. The key gate is no longer the blocker for the advertisement, but the NCA key generation is still missing.
- **D10 general Wi-Fi and network stack**: Phase 0, Phase 1, Phase 2 Batch 1/2, and Phase 3 complete. The adapter's AP mode is verified, and a normal AP can expose the `wlan` supplicant and the `bsdsocket`/`ssl` stack through the console's built-in **Test Connection** flow. Phase 1 added the two test networks; Phases 2–6 transmit malformed 802.11 management/EAPOL frames or DHCP/DNS/IPv6/TLS responses. Phase 0 brought up the open and WPA2 test APs and verified the tooling; the independent scan saw both SSIDs at -34 dBm on channel 1 (`E-104`). Phase 1 associated the console to both APs, completed the WPA2 pairwise handshake, obtained DHCP lease `192.168.77.94`, and queried `ctest.cdn.nintendo.net`; Test Connection failed at the internet step with `2110-3128` because the AP had no NAT (`E-105`). Phase 2 Batch 1 sent the control and `W-01`–`W-08`; there was no crash, reboot, hang, or new error, but `W-06` showed 7.3 s and 15.4 s association lifetimes versus the 35.4 s control, then re-associated (`E-106`). Phase 2 Batch 2 sent the control and `W-09`–`W-14`; there was again no crash, reboot, hang, or new error, but `W-09` showed a 14.7 s lifetime versus the 35.6 s control (`E-107`). Those are behavioral leads, not memory-safety findings. Phase 3 control E-C completed the WPA2 pairwise handshake and three group rekeys; Batch 1 sent `E-01`–`E-08` one frame per association, all accepted, with the station associated at 10 s and lifetimes 35.0–35.4 s (`E-108`). Batch 2 sent `E-09`–`E-14` the same way, with lifetimes 35.1–35.5 s (`E-109`). Those are clean negatives for the tested header/descriptor and key-data cases, with a zero/invalid-MIC limitation. Phase 4 control C passed the DHCP/DNS stages and failed at the internet step with `2110-3129`; D-01 (DHCPOFFER option 1 length 0) caused `2110-2963` with no crash and a normal 30.1 s lifetime (`E-110`). The remaining Phase 4 DHCP/DNS cases are blocked by the adapter's intermittent AP data path. Phases 5–6 need separate explicit approval, and Phase 6 needs an additional decision on the local DNS sinkhole. The full gated matrix is in [`docs/WIFI-NETWORK-TEST-PLAN.md`](WIFI-NETWORK-TEST-PLAN.md).

`D9` is negative for the current hostapd/AP path; its parser hypothesis remains untested. It is conditional, not promised: the real LDN unicast run was executed, a supervised rerun made the room appear but failed the join with `2203-0065` before hostapd saw an association, and a second supervised run reached authentication and association before the console left with reason 8 without an observed `0x88B7` request. The third run omitted the association-response RSN IE, captured raw frames on `mon-ldn`, and used the raw authorized-station `0x88B7` path, but the console still left before the LDN exchange. The current hostapd/AP path is therefore negative for `D9`; the parser hypothesis remains untested. A materially different AP implementation, a different adapter/driver, or static analysis of the `ldn` NCA is the next step. A directed scan for the 16-byte SSID is invalid (`E-086`); a wildcard CoreWLAN BSSID comparison is valid only with Location Services (`E-092`), and the monitor-mode path on `rtw88_8822bu` does not transmit (`E-091`). The prod-mode host has already been run with the captured parameters and the owner's local keys; it emitted valid advertisements but the console did not join, and the monitor-mode TX path is blocked. The next active option is a materially different AP implementation or adapter/driver, with new approval. A pre-auth `ldn` bug would be stage 2 at best, not a path to Atmosphère on its own. Further progress also requires static analysis of the owner's firmware dump or new public research. That is a statement about available inputs, not proof of impossibility. `D10` is the next direction, but it is gated: Phase 0, Phase 1, Phase 2 Batch 1/2, Phase 3, and Phase 4 control/D-01 are complete; the remaining Phase 4 cases are blocked by the adapter data path, and each later active batch needs its own approval. A D10 fault would be stage 1–2 at best and would not reach Atmosphère without boot-stage execution.

## How results are recorded

A run is recorded as one of:

- **Reproduced finding** — an observation that matches the expected signal and survives a repeat.
- **Negative result** — the kill criterion was met; the direction closes with the exact procedure and outcome.
- **Inconclusive** — the run could not be completed; the blocker is recorded.

Nothing is recorded as an exploit until it has been reproduced on hardware and shown to produce the claimed capability.

## Related records

- [`research/hypotheses.json`](../research/hypotheses.json) — the falsifiable register.
- [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md) — the passive capture and approved plaintext-host procedure.
- [`docs/WIFI-NETWORK-TEST-PLAN.md`](WIFI-NETWORK-TEST-PLAN.md) — the gated `D10` matrix, controls, and approval record.
- [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md) — the stage model.
- [`docs/ENTRY-POINTS.md`](ENTRY-POINTS.md) — surfaces and leads.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — boundaries and recovery.
