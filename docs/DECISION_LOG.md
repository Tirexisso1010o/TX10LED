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

## 2026-10-26 — Record GameShare as a receiver-side surface, not a method

**Decision:** Add GameShare / the `splay` applet as surface `EP-011` and lead `L-006`, with status `UNKNOWN`. Record the documented data flow, the host and transport prerequisites, the applet's privileges, and the absence of any public vulnerability. Do not present it as an exploit or as a path to Atmosphère.

**Reason:** The user asked whether the GameShare function could be a way in. It is a genuine, documented flow in which a remote device sends data that a system applet on the target parses without the user launching a game — the first such surface in this review. That makes it worth recording. It is also easy to overstate: Nintendo documents that only a Switch 2 can host, Switch 1 receivers are local-wireless only, at least some host data is ECC-verified, and `splay` is an applet with applet-level privileges. No public vulnerability, proof of concept, or exploit exists for it, the protocol, or its NACP/JPEG handling. Recording it as anything stronger would invent a method.

**Alternatives considered:** Fold it into `EP-005` local wireless (rejected: the component, the data flow, and the privileges are distinct); record it as `UNVERIFIED` or `PARTIALLY VERIFIED` (rejected: those imply evidence of a working primitive); omit it until a vulnerability appears (rejected: the surface itself is documented and reachable, and the project exists to track exactly this).

**Consequences:** `research/sources.json` gains 10 sources (40 total), `research/evidence-ledger.json` gains E-038–E-049 (49 total), and `research/entry-points.json` gains `EP-011` and `L-006` (11 surfaces, 6 leads). `research/compatibility-matrix.json` gains `C-019`–`C-022` (22 rows). `docs/ENTRY-POINTS.md`, `docs/COMPATIBILITY.md`, `README.md`, and `research/known-limitations.md` describe the surface, its bounds, and its applet-level ceiling. The validator passes. The entry-point conclusion is unchanged, and no console state was modified.

## 2026-10-26 — Analyse the chain as stages and record the missing boot stage

**Decision:** Add `docs/GAP-ANALYSIS.md`, which decomposes a software-only Atmosphère path into trigger, initial code execution, privilege escalation, boot-stage execution, and launch/persistence. Record boot-stage execution (`C-023`) as `UNKNOWN` and as the decisive missing link for Mariko on 23.0.1.

**Reason:** The owner does not own SmileBASIC 4.4.9, so the only public `ns2jb` trigger is unavailable, and the owner asked to do whatever is needed to progress. Searching harder is not a plan; naming the missing link is. The stage model also corrects a framing error in the earlier documentation: the question is not only "is there a bootROM bug" but "is there any pre-Horizon code execution on 23.0.1". Caffeine proves that a patched console can run full CFW from software alone when warmboot is exploitable, which is why stage 3 rather than the bootROM is the right target. The model also makes clear that a userland chain, including any future Switch 1 `ns2jb` package, would still not produce Atmosphère.

**Alternatives considered:** Keep monitoring and report "nothing new" (rejected: it does not help the owner decide anything); treat a hypothetical kernel exploit as sufficient (rejected: Atmosphère loads at boot and replaces verified modules, so a post-boot kernel primitive is a different artifact); broaden the scope to modchip installation (rejected: out of scope and unsafe).

**Consequences:** `research/sources.json` gains 6 sources (46 total), `research/evidence-ledger.json` gains E-050–E-054 (54 total), and `research/compatibility-matrix.json` gains `C-023` and `C-024` (24 rows). `docs/ENTRY-POINTS.md` gains a stage table, `README.md` links the analysis, and `research/known-limitations.md` and `research/CHECKPOINT.md` are updated. The conclusion is unchanged; the analysis is more precise about what is missing. No console state was modified and no exploit was executed.

## 2026-10-26 — Move from gap analysis to a ranked experiment program

**Decision:** Add `docs/RESEARCH-PLAN.md`, a falsifiable hypothesis register (`research/hypotheses.json`, H-001–H-007), and a gated capmtp boundary harness (`scripts/ptp_boundary.py`) with mocked-pipe tests. Rank the capmtp PTP surface as the first runnable experiment and the Mariko warmboot diff as the highest-value blocked one.

**Reason:** The owner asked for active research rather than documentation. A gap analysis names the missing stage but does not test anything. The PTP surface is the only flow in which the console parses data supplied by a device the owner controls, so it is the only stage-1 hypothesis that can be tested with the materials at hand. It is also narrow, which is why it is scored low on information gain; the point is to falsify it cheaply and record the result instead of leaving it as unexamined suspicion. The warmboot direction remains the only one that can close stage 3, and it is blocked on firmware artifacts rather than on effort.

**Alternatives considered:** Continue monitoring only (rejected: produces no new information); start with browser exploitation (rejected: fingerprinting is the feasible first step, and exploitation is a much larger project); attempt firmware analysis without artifacts (rejected: impossible without package1).

**Consequences:** `research/sources.json` gains the Filesystem services page (47 total), and the validator now checks hypotheses for required fields, stage values, surface references, and evidence/source references. `scripts/ptp_boundary.py` defaults to a dry run, permits only read-only PTP operations, caps reads, and requires `--confirm --active`. `tests/` gains 10 mocked-pipe tests. No device was opened and no console state was modified.

## 2026-10-26 — First capmtp boundary run: one scoped negative, one stall

**Decision:** Record the first hardware boundary run as a scoped negative for the handle-table hypothesis (`H-002`, matrix `C-025`) and as incomplete for the object-read hypothesis (`H-001`). Record the USB-C role workaround and the PTP transaction-ID requirement as environment findings.

**Reason:** The owner approved active USB probing. The run produced reproducible results: invalid handles and format codes were rejected with `0x2009` and `0x200b`, and a subsequent write timed out. Claiming a vulnerability would be false; discarding the data would waste the run. The transaction-ID finding is a real protocol detail that also fixed a latent bug in the read-only client's session path.

**Alternatives considered:** Treat the whole run as failed because the object family did not finish (rejected: the handle family produced clean data); treat the endpoint stall as a capmtp fault (rejected: it is unexplained and may be a hub artifact).

**Consequences:** `E-056`, `C-025`, and `research/hardware-observations/2026-10-26-ptp-boundary.json` record the result. `H-002` moves to `DISPROVEN` within the tested identifier set; `H-001` stays `UNVERIFIED`. The harness discovery was fixed to use `0xFFFFFFFF` and folder recursion, and both the harness and `PtpClient` send `OpenSession` with transaction ID 0. Tests rose to 20. No exploit was found, no object was modified, and the console was not left in an altered state beyond a stalled endpoint that requires a replug.

## 2026-10-26 — Close the capmtp direction on a reproduced negative

**Decision:** Close direction D1 after the object family returned `0x2006 ParameterNotSupported` for every `GetObject` request. Mark `H-001` as `UNKNOWN` with resolution `closed-negative`, keep `H-002` as `DISPROVEN` within the tested identifier set, and record `C-026`.

**Reason:** The pre-registered kill criterion for `H-001` was "every boundary case returns a documented PTP error or a size-bounded response, and the console stays responsive". That is exactly what happened. Recording the direction as open would invite a repeat that cannot produce new information. Keeping `H-001` as `UNKNOWN` rather than `DISPROVEN` is deliberate: the offset and length validation logic was never reached, so the vulnerability claim itself was not tested, only its reachability.

**Alternatives considered:** Mark `H-001` `DISPROVEN` (rejected: overstates what was tested); keep probing other PTP operations such as `GetThumb` (rejected for now: low expected yield and no pre-registered hypothesis); treat the transient stall as a capmtp fault (rejected: it did not reproduce and cleared after a replug).

**Consequences:** `E-057`, `C-026`, the boundary observation, `docs/RESEARCH-PLAN.md`, and `research/CHECKPOINT.md` record the closure. The next runnable direction is the browser fingerprint (`D2`, `H-005`); the decisive direction (`D3`, `H-003`) remains blocked because the owner cannot provide firmware artifacts. No exploit was found. Tests remain at 20 and the validator passes.

## 2026-10-26 — Add a captive-portal fingerprint harness for the browser direction

**Decision:** Add `scripts/captive_portal.py`, a DNS and HTTP harness that answers A queries with the host's address, redirects unknown paths to a local page, and records request headers plus a JavaScript fingerprint. Add nine loopback tests. Keep the capture file out of version control via `*.local.jsonl`.

**Reason:** The capmtp direction closed negative, and the browser is the only remaining stage-1 surface reachable with the owner's hardware. Fingerprinting is the cheapest way to decide whether a public WebKit n-day could apply: it requires no exploit, changes no console state beyond a temporary DNS entry, and produces one concrete fact (engine vintage) that either closes or opens the direction.

**Alternatives considered:** Guess the engine version from public documentation (rejected: the Switch 1 browser build is not pinned in public sources); skip straight to exploit development (rejected: without a version there is nothing to target).

**Consequences:** The harness is tested on loopback (29 tests total) and verified with `dig` and `curl`. Real use requires binding DNS to 53 and HTTP to 80, which needs elevated privileges, so the run must be started by the owner. The console needs a temporary manual DNS entry pointing at the Mac, which is reversible. No exploit is included and the page only reads browser properties.

## 2026-10-26 — Characterize the browser surface and stop at the patch-level wall

**Decision:** Record the WifiWebAuthApplet as a confirmed stage-1 surface, bracket its engine to Safari 15.4–15.6 (WebKit 615.x, 2022), and mark the direction characterized but blocked. Do not attempt browser exploitation.

**Reason:** The owner approved the captive-portal test, and it produced a clean fingerprint: the applet is reachable without credentials, has no URL whitelist, permits ignoring invalid TLS certificates, and executes page JavaScript. Feature detection narrows the engine to a 2022 WebKit generation, and the applet's NPDM grants a meaningful IPC set. That is enough to call it a real lead. It is not enough to call it a vulnerability: feature detection says nothing about backported security fixes, the NetFront shell changes between firmware versions, and the documented absence of a JIT invalidates many public WebKit techniques. Testing patch-level guesses with public PoCs would be exploit execution on the owner's console, which is outside the authorization boundary. `CVE-2026-2441` was checked and ruled out because it is a Blink bug.

**Alternatives considered:** Try a public WebKit PoC to test the patch level (rejected: exploit execution, crash risk, no consent); keep the direction open as if runnable (rejected: it would invite pointless retries); omit the fingerprint because it did not yield an exploit (rejected: it is a reproducible result that closes a question).

**Consequences:** `E-058` through `E-062`, `C-027` through `C-031`, the browser observation file, the plan, and the checkpoint record the result. `H-005` is `UNKNOWN` with resolution `blocked`. The console's DNS entry was temporary; the owner was advised to revert it. No exploit was attempted and no console state was changed permanently.

## 2026-10-26 — Close the browser direction on a no-JIT measurement

**Decision:** Close direction D2. Record that the target browser shows no JIT warm-up, move `H-005` to `UNKNOWN` with resolution `closed-negative`, and add `C-033`.

**Reason:** The timing probe is unambiguous: a 400,000-iteration integer loop stayed at 39-40 ms across twelve runs, the polymorphic variant at 48-49 ms, and WebAssembly is unavailable. An optimizing engine collapses those numbers; Node does, in the same loop shape. Most public WebKit exploits depend on JIT behaviour, and no public non-JIT exploit exists for the 15.4-15.6 bracket. The direction cannot produce a practical result without original exploit research that would still stop at applet-level userland.

**Alternatives considered:** Keep the direction open pending patch-level information (rejected: without a JIT the patch level is secondary, and obtaining it needs the binary or exploit testing); attempt a public JIT-based PoC (rejected: would not apply and would be exploit execution); try a non-JIT fuzzing campaign (rejected: out of scope, and it would require crash testing on the owner's console).

**Consequences:** `E-064`, `C-033`, the plan, and the checkpoint record the closure. The program now has no runnable software-only direction with the current materials. The console is unchanged; the DNS entry was temporary and should be reverted. No exploit was attempted.

## 2026-10-26 — Close the WebP decoder lead as inconclusive

**Decision:** Close `H-008` and `D7`. Record that the console's WebP decoder is non-stock — it accepts both CVE-2023-4863 reproducers that stock libwebp 1.2.4, 1.3.1, and 1.6.0 reject — but that sixty repeated decodes produced no visible fault, so vulnerability is unconfirmed.

**Reason:** The reproducer was validated locally with ASAN against vulnerable commit `7ba44f8`, so the trigger is genuine. The console decoded it anyway, which is consistent with an older or custom decoder lacking the 2023 validation, but a silent overflow cannot be observed without ASAN. The pre-registered kill criterion for this direction was a clean run with no fault; that is what happened. Continuing would mean heap-grooming work aimed at forcing a crash, which is indistinguishable from exploit development and would still stop at applet-level userland.

**Alternatives considered:** Repeat the stress longer (rejected: same unobservable outcome); generate a stronger trigger with `craft.c` (rejected: moves into exploit development with no path to homebrew); treat acceptance as proof of vulnerability (rejected: it is not).

**Consequences:** `E-067`, `E-068`, `C-034`, the plan, and the checkpoint record the closure. The console is unchanged and stayed responsive. The local reproducer files are not committed. No software-only direction with an observable signal remains with the current materials.

## 2026-10-27 — Close the SD-card filesystem surface on handled rejects

**Decision:** Close `H-009` and `D8`. Record that the tested FAT32 anomalies were rejected at mount, skipped at enumeration, or handled as an applet error, with no crash report and no memory-safety signal.

**Reason:** The control image mounts and a real console screenshot placed at a crafted `NINTENDO/ALBUM/YYYY/MM/DD` path is listed, so the parser is genuinely reachable. But an out-of-range file entry is skipped while a valid neighbour is listed, zero sectors-per-cluster is refused at mount, and an out-of-range directory produces `2802-9999` with the console healthy. Those are validation paths. The remaining anomalies would test hang behaviour, not code execution, and this surface is a denial-of-service path at best.

**Alternatives considered:** Continue with cyclic chains and near-boundary clusters (rejected: they would produce hangs or reads of unallocated card data, not a memory-safety primitive); treat the `2802-9999` as a crash (rejected: no crash report and the console stayed responsive).

**Consequences:** `E-070` through `E-077`, `C-035`, `C-036`, the plan, and the checkpoint record the result. The sacrificial card can be reformatted. The console is unchanged. No software-only direction with an observable signal remains with the available materials.

## 2026-10-27 — Open the LDN pre-auth direction (D9 / H-010), conditionally

**Decision:** Open `D9` and `H-010` for the local-wireless pre-auth parser. Start with a passive LDN advertisement capture. Do not transmit frames until the owner approves the specific plaintext-host test.

**Reason:** The owner now has a CachyOS PC and a Wi-Fi adapter that can use monitor mode, which makes the LDN surface testable for the first time. The protocol is publicly documented, and `CVE-2026-82079` — a local-wireless stack overflow fixed in 23.0.0 — shows that the parser has recently handled security-relevant input. The target is on 23.0.1, so that specific bug is patched; the direction looks for a different defect, not a re-test of the CVE.

**The key constraint:** Retail LDN uses AES-encrypted security mode 1 and needs `prod.keys`, which the owner does not have. The only no-key path is the plaintext security-mode-3 network supported by `kinnay/LDN`. Retail may reject it. If it does, the direction closes as blocked on keys; the project will not download or use keys.

**Alternatives considered:** Emulating a Switch 2 to spoof GameShare (rejected: requires a real Switch 2 host, the host `AdvertiseData` is ECC-verified, and the protocol is not public); spoofing a Virtual Game Card console (rejected: Nintendo Account, internet, local-wireless proximity, and a server-issued license gate a PC out of the flow); downloading `prod.keys` (rejected: prohibited and untrustworthy).

**Consequences:** `E-078` and `E-079`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `scripts/ldn_probe.py`, and `scripts/ldn_host.py` record the direction. `D9` is conditional: the passive capture is safe and ready; the active plaintext-host test needs approval; a pre-auth `ldn` bug would be stage 2 at best. If the plaintext path is rejected, the program returns to monitoring with no runnable direction.

**Superseded in part (2026-10-28):** the passive capture succeeded, and one Phase 2 plaintext-host run was approved and executed. It is recorded as inconclusive because the adapter's transmit path is unconfirmed. See the Phase 2 entry below.

## 2026-10-28 — Keep the LDN radio path on macOS with an OrbStack VM

**Decision:** Run the LDN radio tooling in an OrbStack Ubuntu 26.04 arm64 VM on the Mac, with the TP-Link Archer T3U Plus passed through by USB. Do not reboot into CachyOS for the passive capture. Do not attempt native macOS frame injection.

**Reason:** The owner asked to keep the workflow on macOS. Native macOS does not expose raw 802.11 frame injection, and `kinnay/LDN` is Linux-only. The Archer T3U Plus is an RTL8822BU adapter supported by the in-kernel `rtw88_8822bu` driver, which advertises monitor mode. OrbStack 2.2.5 passed the adapter through, the driver loaded firmware 30.20.0, and a 20-frame passive capture succeeded. The adapter re-enumerated once after firmware load; attaching the new USB ID fixed it.

**Alternatives considered:** Native macOS monitor mode (rejected: no injection, and macOS 26.3 has reports of zero-packet monitor captures); UTM (rejected: USB passthrough is unreliable for Wi-Fi adapters); CachyOS PC (rejected for this run: it would require rebooting away from macOS); a MediaTek MT7921U adapter (kept as fallback if the Realtek path failed).

**Consequences:** The validated path is documented in `docs/LDN-TEST-PLAN.md`. The Mac stays the host, the built-in Wi-Fi stays connected, and the VM owns only the USB adapter. Phase 1 captured 64 Dragon Ball FighterZ advertisement frames and parsed the plaintext `NetworkId` header without keys; the sanitized observation is `research/hardware-observations/2026-10-28-ldn-phase1.json`. The pcap and unredacted JSON stay local. Phase 2 remained active frame injection and required explicit approval; it was later approved and executed once, and is recorded as inconclusive in the next entry. No console state changed.

## 2026-10-28 — Record the Phase 2 plaintext-host run as inconclusive, not a rejection

**Decision:** Do not close `D9` as blocked on keys yet. Record the one approved Phase 2 run as **inconclusive** because the host's transmission is unconfirmed. Do not repeat the active join attempt until the transmit path is verified.

**Reason:** The host started with `--compat-no-active-ack`, advertised for 30 seconds on channel 1, and stopped cleanly. The console showed no room, the host log contained no `JOIN`, and no authentication request was observed. `dmesg` reported `failed to get tx report from firmware` after the 2-second and 30-second runs. The in-kernel `rtw88_8822bu` driver is reported to fail beacon transmission in AP mode with this firmware error, and no independent receiver was used. The result therefore cannot distinguish a console rejection of security mode 3 from a host that never transmitted.

**Alternatives considered:** Close `D9` as blocked on keys (rejected: transmission is not confirmed, so the no-room result is not a clean rejection); repeat the join attempt with the same adapter (rejected: it would reproduce the same unverified condition); treat the free game as a workaround (rejected: the game does not control the LDN security mode; a free game is only a second scan target).

**Consequences:** `E-080`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-28-ldn-phase2.json` record the result. The next diagnostic is to confirm the host's frames are on air with a monitor-mode capture on the host interface or a second monitor-mode receiver. If transmission is confirmed and the console still ignores the room, close `D9` as blocked on `prod.keys`. If the `rtw88_8822bu` path cannot transmit, try a known-good adapter (`mt7921e` is confirmed by the `kinnay/LDN` README) or the CachyOS PC. Another active run requires new explicit approval. No console state changed.

## 2026-10-28 — Reject the CoreWLAN TX check as invalid; require a monitor-mode capture

**Decision:** Do not treat the 60-second CoreWLAN scan as evidence that the host did not transmit. Keep `D9` inconclusive and require a directed scan for the known SSID, a monitor-mode capture on the host interface, or a second receiver before another join attempt.

**Reason:** The host advertised for 60 seconds and three scans from the Mac's built-in Wi-Fi did not show the 32-character SSID. But the LDN host beacon uses `SSIDElement("\x00" * 32)`, and the real network ID is carried in vendor action frames. A wildcard Wi-Fi scan does not report either, so the scan cannot distinguish a silent host from a transmitting host. `dmesg` logged a third `failed to get tx report from firmware` message, which keeps the adapter's TX path suspect but does not prove it failed.

**Alternatives considered:** Treat the missing SSID as a negative TX result (rejected: the check cannot see the frame format); repeat the scan with a phone (rejected: same limitation); run another blind join attempt (rejected: it would reproduce the unverified condition).

**Consequences:** `research/hardware-observations/2026-10-28-ldn-phase2.json`, `research/CHECKPOINT.md`, and `docs/LDN-TEST-PLAN.md` record the invalid check. The next diagnostic is a short host run with a directed scan for the known SSID (a positive result confirms TX) plus `tcpdump` on `ldn` or a second monitor-mode adapter/PC; it requires new explicit approval because it transmits LDN frames. No console state changed.

**Superseded in part (2026-10-29):** the directed scan was later proven invalid — it returned `FOUND` for a random non-existent 16-byte SSID with a nil BSSID. The next diagnostic is now a **wildcard** scan for the host BSSID or a second receiver; see the prod-mode entry below.

## 2026-10-28 — Accept the owner's local keys and firmware for read-only analysis, not for publication

**Decision:** Use the owner-provided `Firmware/prod.keys.txt` and `Firmware/Firmware.23.0.1` locally for read-only interoperability and firmware analysis. Treat the keys as owner-supplied artifacts from their own modded Switch, exclude them from version control, and never commit, publish, share, or paste them. Do not download firmware or keys from any other source.

**Reason:** The keys decrypt the Phase 1 Dragon Ball FighterZ advertisement with key-derivation protocol 1, and the advertisement SHA-256 validates. The decrypted fields confirm the room is security mode 1 (prod/encrypted), challenge enabled, channel 1, max 2 participants, app version 26. That answers the earlier open question and makes a PC-hosted prod-mode room possible without guessing. The firmware dump gives the first local opportunity to inspect the `ldn` sysmodule and package1 rather than relying only on public documentation.

**Alternatives considered:** Continue with only the plaintext mode-3 path (rejected: retail may reject it, and the prod-mode room is the closer reproduction); download a matching key set or firmware from the internet (rejected: prohibited and untrustworthy); commit the keys or firmware to the repository (rejected: proprietary material and a security risk); publish decrypted modules (rejected: same reason).

**Consequences:** `.gitignore` excludes `Firmware/`, `Firmware.*/`, and `prod.keys*`; `git check-ignore` confirms both artifacts are ignored. `E-081`, the Phase 1 observation, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, and `research/CHECKPOINT.md` record the decryption. A PC-hosted prod-mode room and a PC join of the Switch-hosted room are now possible but still require new explicit approval. Firmware extraction is blocked on tooling: no `hactool` or `nxdump` is installed. The target console remains unmodified and no console state changed. *(Refined 2026-10-29: the dump is NCA-only and the key file stops at key generation 0x14, so the 23.0.1 NCAs cannot be decrypted; see the next entry and `E-083`.)*

## 2026-10-29 — Record the NCA inventory and the key-coverage gap

**Decision:** Treat the owner's firmware dump as an **NCA-only** set and record that the supplied keys do not cover the 23.0.1 program-NCA key generation. Keep the `ldn` **program content** encrypted and do not attempt decryption with a mismatched key. Decrypting the `ldn` **meta** NCA is allowed because it uses a key generation the owner's file covers; it is metadata, not the parser. Do not brute-force, derive, or download keys.

**Reason:** All 238 NCA headers decrypt as valid NCA3 with the owner's `header_key`. The `ldn` sysmodule is title `0100000000000018`, version `0x5c0004b0` (1543505072), NCA `755bcf33085ed666cbbcf34de83d1cb0.nca`, a 556,544-byte program NCA with key generation `0x17` (23.0.0) and a 556,032-byte AES-CTR PartitionFS section 0. The `ldn` meta NCA decrypts with `key_area_key_application_00`; its CNMT reports the title version and the program NCA's SHA-256, which matches the local file exactly. Key generation `0x17` needs `key_area_key_application_16`; the key file stops at `key_area_key_application_14` (20.0.0). The dump contains no package1, package2, KIP, or other non-NCA file, and package1 is stored in BOOT0. The LDN advertisement decryption still succeeds because it uses `master_key_00` with key-derivation protocol 1; that does not imply full 23.0.1 key coverage.

**Alternatives considered:** Try the older `key_area_key_application_14` (rejected: wrong generation, and a failure would not be informative); derive the missing keys from `master_key_source` (rejected: the master keys are not derivable from the sources in this file); download a newer key set or firmware (rejected: prohibited and untrustworthy); treat the header identification as sufficient for parser analysis (rejected: the parser is inside the encrypted NSO).

**Consequences:** `E-083`, `H-003`, `H-010`, `docs/FIRMWARE_ANALYSIS.md`, `docs/RESEARCH-PLAN.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-firmware-inventory.json` record the result. Static analysis of `ldn` is blocked until a key set covers generation `0x15`/`0x16`; warmboot analysis is blocked until a BOOT0/package1 image is available. The target console remains unmodified and no console state changed.

## 2026-10-29 — Run the prod-mode host once; reject the directed scan as a TX check

**Decision:** Execute one approved 30-second prod-mode host run with the owner's local keys and the captured Dragon Ball FighterZ parameters. Record the run as **inconclusive**, not a rejection, because RF transmission is still not independently confirmed. Reject the macOS directed CoreWLAN scan as a transmission check and use a **wildcard** scan for the host adapter's BSSID, or a second monitor-mode receiver, for the next attempt.

**Reason:** The prod-mode host is the closest reproduction of a real room and the key gate is open. The run emitted 373 AES-CTR advertisements on channel 1; the first decrypted with `KeyDerivation(protocol=1)`, validated its SHA-256, and matched the Phase 1 room's title, scene, LDN version, security mode, challenge state, participant limit, app version, application-data length, and SSID. The host logged no `JOIN`, the owner reports that the game searches for about one second and then says it found no rooms, and neither same-phy capture saw a console frame. The captures may be loopback, and `dmesg` logged one more `failed to get tx report from firmware` (3 to 4). The directed CoreWLAN scan used during the run returned `FOUND` at -90 dBm on channel 6 and -94 dBm on channel 13 with a nil BSSID, while the host was on channel 1. A control scan for a random non-existent 16-byte SSID also returned `FOUND` at -81 dBm on channel 1 with a nil BSSID. That makes the directed result a false positive, not evidence of TX.

**Alternatives considered:** Treat the no-room result as a clean rejection of the prod-mode room (rejected: RF transmission is unconfirmed and the console search may not have overlapped the advertisement window); repeat the run immediately with the same directed scan (rejected: the scan cannot distinguish a real host from noise); close D9 as blocked on the adapter (rejected: a wildcard BSSID check and a second receiver have not been tried); use a wildcard scan for the LDN SSID (rejected: the beacon has a null SSID and the network ID is in vendor action frames).

**Consequences:** `E-084`, `E-085`, `E-086`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ldn-prod-host.json` record the run and the invalid scan. The next active test is one repeat 30-second prod-mode run on channel 1, with the console search triggered inside the advertisement window and a wildcard CoreWLAN scan for the host BSSID. If the BSSID appears, RF TX is confirmed; if the console still ignores the room, record the discovery result and consider channel 6/11 or a scan-filter explanation. If the BSSID does not appear, try the CachyOS PC/`mt7921e` adapter or another independent receiver before interpreting the console result. Another active run requires new explicit approval. No console state changed.

**Superseded in part (2026-10-29):** the repeat run was executed, but the wildcard CoreWLAN BSSID check is also invalid because macOS returned a nil BSSID for every network. See the next entry.

## 2026-10-29 — Record the repeat prod-mode run and reject the macOS BSSID check

**Decision:** Record the second approved prod-mode run as **inconclusive**. Do not use the macOS wildcard `CWNetwork.bssid` comparison as an independent transmission check; require a second monitor-mode receiver, a phone Wi-Fi analyzer that shows hidden BSSIDs, or the CachyOS PC/`mt7921e` path.

**Reason:** The repeat host started and advertised with the console search triggered inside the window, but the host again logged `Join events observed: 0`, the console again reported no rooms, and `dmesg` TX-report failures rose from 4 to 5. The wrapper's `tcpdump` processes failed with `Permission denied` on the previous run's tcpdump-owned pcaps, so the run has no valid capture; its summary is from run 1. Ten wildcard scans during the run each reported `BSSID not found in 8 scan result(s)`, but a post-run control scan returned 10 ambient networks and `CWNetwork.bssid` was `nil` for every one. That is a platform redaction limitation, not evidence that the host was absent. The repeat run therefore cannot distinguish a silent host from a transmitting host, and the BSSID check cannot do so either.

**Alternatives considered:** Treat the missing BSSID as a negative TX result (rejected: the control scan shows the API never returns a BSSID on this Mac); repeat the run with the same Mac scan (rejected: same limitation); use Location Services permission to expose BSSIDs (not attempted: a system privacy change, and a second receiver is more direct); close D9 as blocked on the adapter (rejected: a second receiver has not been tried); ignore the failed capture and reuse run 1's frame counts (rejected: those counts are from a different run).

**Consequences:** `E-087`, `E-088`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ldn-prod-host-run2.json` record the repeat run, the capture failure, and the invalid BSSID check. The local wrapper needs a unique pcap path and `sudo rm -f` for old tcpdump-owned files before the next run. The next active test requires a second receiver and new explicit approval. No console state changed.

## 2026-10-29 — Run 3, restore the BSSID check with Location Services, and isolate the monitor-mode TX blocker

**Decision:** Execute one more approved prod-mode run with the fixed wrapper and a Location Services-enabled independent scan. Record the run as inconclusive about the console's response, because the host path does not transmit in monitor mode. Add AP-mode and monitor-mode controls, and move the next host path to AP-mode management-frame injection or a different adapter/driver.

**Reason:** Run 3 again logged no `JOIN` and no room; the independent scan did not see the host BSSID, although it saw a hidden ambient BSSID on channel 1. The AP-mode control transmitted at -32 dBm, while the monitor-mode control did not appear on the Mac. That isolates the failure to monitor-mode injection on `rtw88_8822bu`, not to the adapter's RF path or the console. Location Services restored real BSSIDs, so the earlier nil-BSSID limitation is a permission issue, not an API dead end.

**Alternatives considered:** Treat run 3 as a console rejection (rejected: the host path is not on air); continue with monitor mode and a second receiver (rejected: the control shows the frames do not leave the adapter); use hostapd vendor elements without testing whether the advertisement can be carried in a beacon/probe response (deferred: test AP-mode `NL80211_CMD_FRAME` first); build the out-of-tree `rtl88x2bu` driver (blocked: OrbStack kernel headers are missing); use a different adapter/PC (not available).

**Consequences:** `E-089`, `E-090`, `E-091`, `E-092`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `research/CHECKPOINT.md`, and the three new observation files record the result. The current monitor-mode host path is blocked. The next active step is a harmless AP-mode `NL80211_CMD_FRAME` diagnostic, then adapting the LDN host if the driver supports it; a different adapter/driver is the fallback. Another active run requires new explicit approval. No console state changed.

## 2026-10-29 — AP-mode management-frame injection works for beacons; broadcast vendor actions are blocked by the station lookup

**Decision:** Record the approved AP-mode `NL80211_CMD_FRAME` control as a success for **beacon** transmission and keep the LDN vendor-action path open only for a **unicast** action to a station entry. Do not treat the AP beacon result as proof that an LDN room can be advertised. The next active test is a harmless unicast vendor action to the console's station MAC and requires new explicit approval.

**Reason:** hostapd 2.11 reached `AP-ENABLED` with `TX10LED-TEST` on channel 1. Twenty `TX10LED-APINJ` beacons submitted through `NL80211_CMD_FRAME` at 100 ms intervals were seen by the Mac at -28 dBm in all 12 scans with the adapter BSSID, while ambient networks remained visible. That resolves the beacon half of the AP path. A source review found that `cfg80211_mgmt_tx_check` and `ieee80211_mgmt_tx` require a station entry for a non-public action frame on an AP interface; a broadcast destination is not a station, and `NL80211_ATTR_FRAME_NO_STA` does not bypass the check. The LDN advertisement is a vendor action frame, so a broadcast LDN action frame would be rejected with `-ENOLINK` before it reaches the driver.

**Alternatives considered:** Treat the AP beacon success as proof that the LDN host will work (rejected: the LDN advertisement is an action frame, not a beacon); send a broadcast LDN action frame anyway (rejected: the source check predicts `-ENOLINK`, and the test would not distinguish a kernel rejection from a console rejection); use hostapd vendor elements without testing the action path (deferred: the LDN advertisement is a vendor action frame, and the console may not read it from a beacon/probe response); build an out-of-tree `rtl88x2bu` driver (blocked: OrbStack kernel headers are missing); use a different adapter/PC (not available).

**Consequences:** `E-093` and `E-094`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `docs/SAFETY_AND_RECOVERY.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ap-mode-frame-injection.json` record the result. The AP-mode beacon half is verified; the vendor-action half needs a unicast station entry or a different adapter/driver. The next active test requires new explicit approval. No console state changed.

## 2026-10-29 — The unicast vendor-action path is accepted by the kernel

**Decision:** Record the approved 5-frame unicast vendor-action control as a **kernel-level success** for the station-lookup path and keep the console parser question open. Do not treat the result as proof that the console received the frame or that its LDN parser reacted. The next active test is a **real LDN** unicast vendor action through the AP interface and requires new explicit approval.

**Reason:** hostapd 2.11 reached `AP-ENABLED` with `TX10LED-TEST` on channel 1. `Firmware/ap_unicast_test.py` added a temporary station entry for the console's MAC, which was recovered locally from the Phase 1 pcap, and submitted five unicast vendor action frames with the non-LDN test OUI `00:11:22` and payload `TX10LED-UNICAST` through `NL80211_CMD_FRAME`. `NL80211_CMD_NEW_STATION` succeeded, all five `NL80211_CMD_FRAME` requests returned without a netlink error, the station entry was removed, and the adapter was restored to monitor mode (`E-095`). This confirms the kernel-level half of the AP path that `E-093` predicted. It does not show RF reception or a console reaction: the test used a non-LDN OUI, no independent capture was made, and the console was not instrumented. `dmesg` again reported `failed to get tx report from firmware`.

**Alternatives considered:** Treat the accepted unicast frame as proof that the console will see an LDN room (rejected: the frame was not an LDN vendor action and was not independently captured); send the real LDN vendor action immediately under the same approval (rejected: the approval covered a harmless non-LDN test, and a real LDN frame is a separate active test); skip the unicast control and go straight to a different adapter/driver (deferred: the station-lookup path had not been tested on the running kernel); keep the temporary station entry after the test (rejected: cleanup is required).

**Consequences:** `E-095`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `docs/SAFETY_AND_RECOVERY.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ap-mode-unicast-vendor.json` record the result. The AP-mode beacon half and the unicast station-lookup half are verified. The next active test is a real LDN unicast vendor action through the AP interface, with the console observed, and it requires new explicit approval. No console state changed.

## 2026-10-29 — The real LDN unicast run is inconclusive because the console was absent; broadcast-BSSID action frames are rejected

**Decision:** Record the approved real LDN unicast run as a **kernel-level success** for the AP-BSSID path and **inconclusive** for the console's LDN parser. Do not treat the 568 accepted frames as proof that the console received them. Do not close `D9`. Require a supervised rerun with the console in the search screen, or a different adapter/driver.

**Reason:** The first 60-second attempt sent 0 advertisements because `rtw88_8822bu` rejected the broadcast-BSSID action frame with `[Errno 22] Invalid argument`. `Firmware/ap_action_variants.py` isolated the rejection: the 1,388-byte LDN advertisement and a 42-byte control both failed with a broadcast BSSID and succeeded with the AP BSSID; all beacon variants, including the 89-byte null-SSID LDN beacon, were accepted (`E-097`). The rerun used `--variant ap` and sent 568 valid AES-CTR advertisements plus 568 null-SSID beacons at 100 ms intervals; all requests returned without a netlink error, the station entry was removed, and hostapd reached `AP-DISABLED` (`E-096`). The console was off/away during the window, so no room appearance or parser reaction was observed. `dmesg` reported `failed to get tx report from firmware` and, after hostapd stopped, a firmware download failure; the adapter required a USB deauthorize/reauthorize cycle before it probed cleanly again.

**Alternatives considered:** Treat the run as a console rejection (rejected: the console was off/away); treat the 568 accepted requests as proof of RF transmission (rejected: no independent receiver captured the frames, and the driver reported TX-report failures); keep the broadcast BSSID (rejected: the driver returns `EINVAL`); switch to a different adapter immediately (deferred: the AP-BSSID variant has not been observed by the console); close `D9` as blocked on tooling (rejected: the host path now sends real LDN frames; the missing piece is a supervised observation).

**Consequences:** `E-096`, `E-097`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `docs/SAFETY_AND_RECOVERY.md`, `docs/ENTRY-POINTS.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ap-mode-ldn-unicast.json` record the result. The AP-BSSID unicast path is verified at the kernel level; the broadcast variant is unavailable on this driver; the next active run requires new explicit approval and the console present. No console state changed.

## 2026-10-29 — The supervised rerun reaches the scan path but fails the join at the WLAN layer

**Decision:** Record the supervised AP-mode rerun as a **real advertisement-delivery success** and a **join failure before association**, not as a parser fault or a vulnerability. Treat the immediate `2203-0065` error as consistent with a host WLAN configuration mismatch: hostapd advertised `TX10LED-TEST` with open security, while the LDN client joins the room's 32-character hexadecimal WLAN SSID and expects the LDN RSN IE. Do not repeat the same hostapd configuration. The next active test must correct the WLAN SSID/RSN and add a userspace responder for the custom `0x88B7` authentication exchange; it requires new explicit approval.

**Reason:** The console displayed the room `TX10LED`, so the AP-BSSID unicast advertisement reached the console's scan path. Selecting the room produced `2203-0065` immediately; the search screen closed and the console returned to the game normally. The hostapd log contains only `AP-ENABLED` and `AP-DISABLED`, with no `IEEE 802.11: authenticated`, `AP-STA-CONNECTED`, or other station event. That means the console did not complete association with the hostapd AP, so it never reached the custom LDN authentication exchange. The LDN protocol documentation and the `kinnay/LDN` client confirm that the WLAN SSID is `network.ssid.hex()` (32 characters), the beacon zeroes the SSID, and the join is open-system authentication followed by an encrypted `0x88B7` request/response. The hostapd test SSID and open security did not match those parameters. The console remained responsive, so there is no evidence of a memory-safety fault.

**Alternatives considered:** Treat `2203-0065` as a clean rejection of the PC-hosted room (rejected: the AP's SSID/security did not match the room, and the console never associated); treat the room appearance as proof that the full join path works (rejected: hostapd saw no association); send malformed authentication frames next (rejected: the console has not reached the authentication exchange, and Phase 3 requires a separate approval); keep using `TX10LED-TEST` (rejected: it cannot match the LDN client's expected SSID); use `ssid2=<16 raw bytes>` (rejected: the client passes the 32-character hex string, not the raw bytes).

**Consequences:** `E-098`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `docs/SAFETY_AND_RECOVERY.md`, `docs/ENTRY-POINTS.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ap-mode-ldn-unicast-observed.json` record the result. The next test must use hostapd `ssid=<32-character hex string>`, `ignore_broadcast_ssid=2`, and the LDN RSN IE (`30140100000fac040100000fac040100000fac020c00`), install the pairwise CCMP key derived from the same `server_random` and the game passphrase, and answer the `0x88B7` challenge. The exact hostapd/RSN mechanics still need a local prototype because `own_ie_override` only applies with the WPA state machine and `wpa=0` does not set the privacy bit. No console state changed beyond the observed error and return to the game.

## 2026-10-29 — The corrected AP reaches association; the console leaves before the LDN exchange

**Decision:** Record the second supervised AP-mode run as a **WLAN-layer success** (authentication, association, authorization) and a **join failure before the custom `0x88B7` exchange**. Do not treat it as a parser fault or a vulnerability. The leading host-side mismatch is the RSN IE in the association response, which the `ldn` package's `MonitorAP` does not send. The next active test omits that element, enables raw-frame diagnostics and a local pcap on `mon-ldn`, and uses the authorized-station raw `0x88B7` response path; it requires new explicit approval.

**Reason:** The console completed open-system authentication, associated with AID 1, and hostapd marked the station `authorized=1`. About one second later hostapd received a disassociation from the console with `reason_code=8` (`sending STA is leaving BSS`), logged `AP-STA-DISCONNECTED`, and later deauthenticated the station due to inactivity. The harness sent 54 advertisements, received 0 `0x88B7` authentication frames, and ended with `joined=False`. The `mon-ldn` monitor saw one 28-byte console data frame (`flags=16`, FCS included), consistent with a 24-byte null-data header and no payload, not the 946-byte LDN authentication request. The AP raw socket saw one 20-byte frame with ethertype `0x0006`; its payload was not preserved. The owner observed `2203-0066` after a few seconds and the game popup `unable to join the room`; the console returned to the game normally. The association response included the LDN RSN IE, while the reference `MonitorAP` association response carries only supported rates. That difference is a candidate explanation for the disassociation, not a proven cause. The console remained responsive, so there is no evidence of a memory-safety fault.

**Alternatives considered:** Treat `2203-0066` as a clean rejection of the PC-hosted room (rejected: the console authenticated and associated, so the failure is after the WLAN layer); treat association as proof that the full join path works (rejected: no `0x88B7` request was observed and the console left); repeat the same hostapd configuration (rejected: the association-response RSN mismatch is untested and the null-data/0x0006 frames are unidentified); send malformed authentication frames next (rejected: the console has not reached the authentication exchange, and Phase 3 requires separate approval); add a second adapter or a different PC (not available).

**Consequences:** `E-099`, `H-010`, `C-037`, `EP-005`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `docs/SAFETY_AND_RECOVERY.md`, `docs/ENTRY-POINTS.md`, `research/CHECKPOINT.md`, and `research/hardware-observations/2026-10-29-ap-mode-ldn-join-observed.json` record the result. The hostapd config generator now omits `assocresp_elements` by default (`--include-assoc-rsn` restores the earlier behavior), the harness logs 802.11 subtypes and redacted payload hex and can write `/tmp/ap-ldn-monitor.pcap`, and the wrapper defaults to `HOSTAPD_ASSOC_RSN=0`. No console state changed beyond the observed error and return to the game.

## 2026-10-29 — The AP control port rejects `0x88B7`; the raw authorized-station path works

**Decision:** Use an AF_PACKET raw send on the AP interface as the `0x88B7` response path after the station is authorized and the pairwise CCMP key is installed. Keep the control-port attempt only as a fallback for drivers that accept a non-EAPOL ethertype. Do not treat the control-port `EINVAL` as a harness failure.

**Reason:** On the AP interface, `NL80211_CMD_CONTROL_PORT_FRAME` with ethertype `0x88B7` returned `[Errno 22] Invalid argument`, while the same command with EAPOL `0x888E` was accepted and captured as a protected data frame with KeyID 0. A raw AF_PACKET `0x88B7` frame was accepted by the socket but not transmitted when the fake station was unauthorized. After authorizing the station with `NL80211_CMD_SET_STATION` (`NL80211_ATTR_STA_FLAGS2` mask/set `0x2` and the nested `NL80211_STA_FLAG_AUTHORIZED` flag) and installing the pairwise key, the monitor captured two protected data frames to the fake station with IV 1 and IV 2 and KeyID 0; the `0x88B7` frame was the second (`E-100`). This matches the real association state, where hostapd sets `authorized=1` at association.

**Alternatives considered:** Treat the control-port rejection as a blocker (rejected: the raw path transmits the same ethertype when the station is authorized); send the response before authorization (rejected: the frame is accepted by the socket but not transmitted); patch hostapd or the driver (deferred: the raw path works without a kernel change); use EAPOL as a substitute (rejected: the LDN exchange uses `0x88B7`, not EAPOL).

**Consequences:** `E-100`, `H-010`, `C-037`, `EP-005`, `Firmware/ap_ldn_join_test.py`, `docs/LDN-TEST-PLAN.md`, `docs/RESEARCH-PLAN.md`, `docs/SAFETY_AND_RECOVERY.md`, and `research/CHECKPOINT.md` record the result. The harness logs the control-port rejection once and falls back to the raw socket. The station must be authorized and the pairwise key installed before the send. No console was involved in this control.
