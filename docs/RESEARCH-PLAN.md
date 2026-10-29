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
| **D3** | Mariko warmboot / package1 diff (`H-003`) | 3 | **Partial** — NCA-only dump, package1 absent, key coverage incomplete | 2 | 5 | 5 | **30** | Blocked on artifact completeness and key coverage |
| **D4** | `fs` path-normalization on Switch 1 (`H-004`) | 2 | No — needs a stage-1 primitive and a binary | 2 | 3 | 2 | **12** | Blocked |
| **D5** | GameShare `splay` parsing (`H-006`) | 1 | No — needs a Switch 2 host | 1 | 3 | 2 | **6** | Blocked |
| **D6** | Artemis save chain-load (`H-007`) | 1 | No — no Switch reproduction or save delivery | 2 | 2 | 1 | **4** | Blocked |
| **D7** | Browser non-JS parsers: image decoding (`H-008`) | 1 | **Yes** — the portal serves the assets | 4 | 4 | 3 | **48** | **Closed — inconclusive** |
| **D8** | SD-card FAT32 parser (`H-009`) | 2 | **Yes** — card reader and sacrificial card | 4 | 3 | 4 | **48** | **Closed — negative** |
| **D9** | LDN local-wireless pre-auth parser (`H-010`) | 2 | **Conditional** — association reached; console leaves before the LDN exchange; responder next | 3 | 4 | 4 | **48** | **Open — association-RSN/responder test or a different adapter/driver** |

`D1`, `D2`, `D7`, and `D8` are closed. `D3` is blocked on extraction tooling now that the owner has supplied a firmware dump. `D4`–`D6` remain blocked on primitives or hosts. `D9` is the only open runnable direction: Phase 1 confirmed the passive advertisement path, the owner's keys decrypt the advertisement and confirm security mode 1, and prod-mode hosts emitted valid AES-CTR advertisements, but the console never joined. An AP-mode control proved the adapter can transmit, and AP-mode `NL80211_CMD_FRAME` beacon injection works, while a monitor-mode control showed that monitor-mode injection does not transmit. The current monitor-mode host path is blocked by `rtw88_8822bu`, and a broadcast vendor action frame is blocked by the station lookup. A unicast control with a temporary station entry and a non-LDN test OUI was accepted by the kernel without a netlink error. A real LDN unicast run then sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID, all accepted by the kernel, but the console was off/away, so reception was not observed. The driver rejects a broadcast-BSSID action frame with `EINVAL`, so only the AP-BSSID variant is available. A supervised rerun on 2026-10-29 made the room `TX10LED` appear, but selecting it produced `2203-0065` immediately and hostapd recorded no authentication or association event (`E-098`). The room appearance confirms the advertisement reaches the console; that join failed because the hostapd WLAN SSID/security did not match the room's 32-character hexadecimal SSID and LDN RSN IE. A second supervised run with the corrected WLAN parameters reached open-system authentication, association with AID 1, and `authorized=1`, but the console disassociated with reason 8 about one second later and sent no observed `0x88B7` request (`E-099`). The association response included an RSN IE that the `ldn` MonitorAP does not send; the next run omits it, captures raw frames on `mon-ldn`, and uses the authorized-station raw `0x88B7` response path (`E-100`). Another active run requires approval. `D3` remains the only direction that can close the decisive stage; its blocker is now tooling and analysis, not artifact availability.

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

**What blocks it.** Package1 is signed and encrypted on Mariko, and a stock console cannot dump it. The owner has now supplied a **local** 23.0.1 firmware dump and `prod.keys` from their own modded Switch; both are excluded from version control and must never be published. The dump is **NCA-only**: it contains no package1, package2, or KIP files, and package1 lives in BOOT0. The key file also stops at key generation `0x14` (20.0.0), while the 23.0.1 NCAs use up to `0x17` (23.0.0), so the newer NCAs cannot be decrypted. No `hactool` or `nxdump` is installed. A single dump is not enough for a version diff either; a second firmware version would be needed.

**Next task (once tooling exists).** Extract and verify package1 from the owner's dump, then diff section 0 and the TSEC payload across at least two versions, list parsing and bounds logic, and rank candidates by whether they are reachable before Horizon starts. Validate only in an emulator. Keep every extracted artifact local.

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

A local response-path control showed that `NL80211_CMD_CONTROL_PORT_FRAME` rejects ethertype `0x88B7` with `EINVAL`, while EAPOL `0x888E` is accepted. An AF_PACKET raw `0x88B7` frame is transmitted as a protected CCMP data frame with KeyID 0 when the station is authorized and the pairwise key is installed; without authorization the socket accepted the frame but it was not transmitted (`E-100`). The harness now logs the 802.11 subtype and redacted payload hex, writes an optional local pcap on `mon-ldn`, and defaults to omitting the association-response RSN IE (`--include-assoc-rsn` reproduces the earlier behavior). The next run must use those defaults and the raw authorized-station response path.

**Third step — read-only, in progress.** The owner's keys decrypt the Phase 1 advertisement and confirm the room is prod mode with the challenge enabled (`E-081`). The next no-radio step is to extract the `ldn` sysmodule from the owner's firmware dump and compare its parser against the 23.0.0 fix for `CVE-2026-82079`. No extraction tool is installed yet; if none can be obtained without downloading firmware or keys, record the tooling gap. The supplied key file stops at generation `0x14`, while the `ldn` NCA uses `0x17`, so the content is currently undecryptable (`E-083`).

**Next active step — requires new approval.** The real LDN unicast run was executed (`E-096`), a supervised rerun made the room appear but failed the join with `2203-0065` (`E-098`), and a second supervised run with the corrected WLAN parameters reached authentication and association (AID 1) before the console disassociated with reason 8 and sent no observed `0x88B7` request (`E-099`). The driver rejects a broadcast-BSSID action frame (`E-097`), so the AP path can only send the AP-BSSID variant; the room appearance shows that this is sufficient for the scan path. The next step is to rerun with the association-response RSN IE omitted to match the `ldn` `MonitorAP`, with the local `mon-ldn` pcap and raw-frame diagnostics enabled, and with the authorized-station raw `0x88B7` response path (`E-100`). The responder derives the WLAN key from the same `server_random` and the game's passphrase, installs the pairwise CCMP key, and answers the console's `0x88B7` authentication challenge. Use the console's station address recovered locally from the Phase 1 capture. Record whether the console reaches the `0x88B7` exchange, whether the 28-byte null-data frame recurs, and what the 20-byte ethertype `0x0006` frame contains. Confirm RF with the Mac's Location Services-enabled BSSID scan (`E-092`). Do **not** use a directed scan for the 16-byte SSID (`E-086`). If the console still leaves before `0x88B7`, record `D9` as negative rather than repeating the same host configuration. If no path is viable, try a different adapter/driver with working monitor-mode TX (`mt7921e` per the `kinnay/LDN` README) or record D9 as blocked on tooling/adapter.

**Kill criterion.** After host transmission is independently confirmed, the console rejects the prod-mode network **and** every plaintext/no-key variant; or the adapter cannot capture/transmit LDN action frames and no known-good adapter or second host is available; or the firmware cannot be parsed with the available tools. If the console joins but every malformed authentication response is rejected cleanly, record as negative.

**Risk.** A malformed frame could hang or crash the `ldn` sysmodule or Wi-Fi firmware. Recovery is to stop the host, power-cycle the console, and restart the adapter. No storage is written. Active frame injection requires explicit approval for the specific run.

**Capability ceiling.** A pre-auth bug in `ldn` would be stage 2 at best. It would not by itself reach boot-stage execution, and a full chain would still need a kernel or warmboot stage.

## Task queue

| # | Task | Depends on | Status |
|---|---|---|---|
| T1 | Implement `capmtp` boundary harness with tests | — | **Done** (`scripts/ptp_boundary.py`, 20 tests) |
| T2 | Run handle family on the target | Owner approval + console connected | **Done — negative** |
| T3 | Run object family on the target | T2 + one screenshot | **Done — closed negative** |
| T4 | Record the results | T2, T3 | **Done** (`E-056`, `E-057`, `C-025`, `C-026`) |
| T5 | Browser fingerprint via captive portal | Owner approval + network setup | **Done** — engine bracketed to WebKit 615.x |
| T6 | Determine browser security patch level | Browser binary or controlled exploit testing | **Closed — moot (no JIT)** |
| T7 | Package1 extraction, verify, and warmboot checklist | A BOOT0/package1 image + matching keys + a second firmware version | Blocked on artifact completeness and key coverage |
| T8 | Switch 1 `fs` comparison | Stage-1 primitive | Blocked |
| T9 | WebP reproducer on the console | Owner approval | **Done — no fault, inconclusive** |
| T10 | SD FAT32 anomaly matrix | Card reader + sacrificial card | **Done — handled rejects, no memory signal** |
| T11 | LDN passive capture, plaintext-host, then prod-mode host | macOS + OrbStack VM + compatible adapter + owner approval | **Phase 1 done; room appears; association reached; console leaves before `0x88B7`; corrected AP/responder next** |
| T12 | Malformed LDN authentication responses | T11 join + separate approval | Not started |
| T13 | Extract and analyze the `ldn` sysmodule from the owner's firmware | `key_area_key_application_16` + extraction tooling | Blocked on key coverage; `ldn` NCA identified |

## Program status

Every direction that could be executed with the owner's hardware has now been either falsified or characterized:

- **D1 capmtp**: closed negative (`E-056`, `E-057`).
- **D2 browser**: closed negative, no JIT (`E-058` to `E-064`).
- **D3 warmboot**: blocked on artifact completeness and key coverage. The owner's local 23.0.1 dump is NCA-only, and the key file stops at generation `0x14`.
- **D4 `fs`**: blocked on a stage-1 primitive.
- **D5 GameShare**: blocked on a Switch 2 host.
- **D6 Artemis**: blocked on save delivery and native escape.
- **D7 browser image parsers**: closed inconclusive (non-stock decoder accepted the reproducer; no observable fault).
- **D8 SD-card FAT32 parser**: closed negative on tested anomalies (mount rejection, entry skip, handled applet error; no crash report).
- **D9 LDN pre-auth parser**: open but blocked on the host TX path. Passive capture succeeded. The owner's local keys decrypt the advertisement and confirm security mode 1 (prod), challenge enabled, max 2 participants, app version 26 (`E-081`). One approved plaintext-host run produced no join, but the adapter's transmit path is unconfirmed (`failed to get tx report from firmware`). The 60-second CoreWLAN TX check was invalid because the LDN beacon uses a null SSID. A later prod-mode host emitted 373 AES-CTR advertisements that decrypted to the same room, but the console still reported no rooms, the host logged no `JOIN`, and the same-phy captures saw no console frames (`E-084`, `E-085`). The directed CoreWLAN scan is invalid because it returns false positives for non-existent 16-byte SSIDs (`E-086`). A second prod-mode run again produced no join and no room; its pcap capture failed on a wrapper permission error, and the wildcard BSSID scan is invalid because macOS returned a nil BSSID for every network (`E-087`, `E-088`). On 2026-10-29 run 3 again produced no join and no room; the independent Location Services-enabled scan saw a hidden ambient BSSID but not the host BSSID (`E-089`). An AP-mode control proved the adapter can transmit at -32 dBm (`E-090`), while a monitor-mode control showed that monitor-mode injection does not transmit (`E-091`). Location Services restored real BSSIDs for the independent scanner (`E-092`). A follow-up AP-mode `NL80211_CMD_FRAME` test put a 20-frame test beacon on the air at -28 dBm in all 12 scans (`E-094`), so the beacon half of the AP path works. The vendor-action half is still blocked for broadcast: a non-public action frame on an AP interface needs a station entry and is rejected with `-ENOLINK` (`E-093`). A unicast control with a temporary station entry and a non-LDN test OUI was accepted by the kernel without a netlink error (`E-095`). A real LDN unicast run then sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID; all requests were accepted, but the console was off/away, so reception was not observed (`E-096`). The driver rejects a broadcast-BSSID action frame with `EINVAL`, so only the AP-BSSID variant is available (`E-097`). A supervised rerun made the room `TX10LED` appear, but selecting it produced `2203-0065` immediately and hostapd saw no authentication or association (`E-098`). The room appearance confirms the scan path; that join failure is consistent with the hostapd WLAN SSID/security not matching the room. A second supervised run with the room's 32-character hexadecimal WLAN SSID and the LDN RSN IE reached authentication, association (AID 1), and `authorized=1`, then the console disassociated with reason 8 about one second later; no `0x88B7` request was observed (`E-099`). The association response included an RSN IE that the `ldn` MonitorAP does not send, and the AP control port rejects `0x88B7` with `EINVAL` while the raw authorized-station path transmits it protected with KeyID 0 (`E-100`). The next step is the association-RSN omission plus raw-frame diagnostics and the raw responder; a different adapter/driver is the fallback. The key gate is no longer the blocker.

D9 is the only remaining runnable direction. It is conditional, not promised: the real LDN unicast run was executed, a supervised rerun made the room appear but failed the join with `2203-0065` before hostapd saw an association, and a second supervised run reached authentication and association before the console left with reason 8 without an observed `0x88B7` request. The next diagnostic must omit the association-response RSN IE, capture raw frames on `mon-ldn`, and answer through the raw authorized-station `0x88B7` path before the join result can be interpreted. A directed scan for the 16-byte SSID is invalid (`E-086`); a wildcard CoreWLAN BSSID comparison is valid only with Location Services (`E-092`), and the monitor-mode path on `rtw88_8822bu` does not transmit (`E-091`). The preferred active test is a **prod-mode** host built from the captured parameters and the owner's local keys, with the plaintext mode-3 room as a no-key control. A pre-auth `ldn` bug would be stage 2 at best, not a path to Atmosphère on its own. Further progress also requires static analysis of the owner's firmware dump or new public research. That is a statement about available inputs, not proof of impossibility.

## How results are recorded

A run is recorded as one of:

- **Reproduced finding** — an observation that matches the expected signal and survives a repeat.
- **Negative result** — the kill criterion was met; the direction closes with the exact procedure and outcome.
- **Inconclusive** — the run could not be completed; the blocker is recorded.

Nothing is recorded as an exploit until it has been reproduced on hardware and shown to produce the claimed capability.

## Related records

- [`research/hypotheses.json`](../research/hypotheses.json) — the falsifiable register.
- [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md) — the passive capture and approved plaintext-host procedure.
- [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md) — the stage model.
- [`docs/ENTRY-POINTS.md`](ENTRY-POINTS.md) — surfaces and leads.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — boundaries and recovery.
