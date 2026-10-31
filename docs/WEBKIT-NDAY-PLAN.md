# WebKit N-day Assessment Plan

> **Snapshot: 2026-10-31. W1 passed; W2 pending approval.** This plan tests whether the Switch 1 `23.0.1` browser applet is reachable by a public, no-JIT WebKit n-day. It is a stage-1 assessment. A browser compromise would not reach Atmosphère without additional kernel and boot-stage work.

## Purpose and boundary

The browser applet is a genuine attacker-controlled JavaScript surface: the captive-portal flow reaches `WifiWebAuthApplet` without credentials, the applet executes a page served by the local host, and the applet has no URL whitelist. The open question is whether its WebKit build is vulnerable to a public n-day that does not need a JavaScript JIT.

**Authorized by this plan, with separate approval for the console step:**

- local harness validation, loopback self-tests, and read-only source review;
- one bounded reachability page load on the console (W1), with the console's DNS temporarily pointed at the Mac and reverted immediately afterwards — **executed 2026-10-31**;
- one bounded public-PoC page load (W2) only if W1 passes and the owner approves that exact run — **not yet approved**.

**Not authorized by this plan:**

- repeated crash attempts, heap grooming, exploit development, or payload execution;
- any write to the console's storage, firmware, or boot configuration;
- proxying Nintendo services, capturing credentials, or serving account/eShop traffic;
- publishing keys, firmware, decrypted modules, or the owner's local logs;
- claiming a jailbreak from a browser crash or from a public PoC that has not been reproduced on this console.

## What is known

| Fact | Evidence |
|---|---|
| The captive portal reaches `WifiWebAuthApplet` and executes local JavaScript. | `E-058`, `E-060` |
| The User-Agent token is `AppleWebKit/613.0 ... NF/6.0.3.31.11 NintendoBrowser/5.1.0.55481`. The token is frozen and is not a build identifier. | `E-060` |
| Feature detection brackets the engine to the Safari 15.4–15.6 era. | `E-061`, `E-063` |
| The applet has no JIT warm-up, no WebAssembly, no WebGL, no `SharedArrayBuffer`, and no `crypto.subtle`. | `E-061`, `E-062` |
| The applet decodes PNG, JPEG, GIF, BMP, WebP, and SVG; the WebP decoder is non-stock. | `E-065`–`E-069` |
| The applet has no URL whitelist and permits ignoring invalid TLS certificates. | `E-060` |
| W1 passed on 2026-10-31: the applet loaded the local probe page and round-tripped a `Map`/`Date` graph through `postMessage` (`ok=true`, `mapSize=1`, `dateValue=0`). | `E-112`; `2026-10-31-webkit-w1.json` |

The engine bracket and the public PoC are **lineage-adjacent, not an exact build match**. The PoC was written against WebKit-613.1.17.1 (Safari 15.4 / PlayStation lineage); the console's UA token says 613.0 and its feature set brackets the Safari 15.4–15.6 generation. The exact patch level is unknown, and Nintendo may have backported the fix into the 2026 NetFront build. Only a console test can distinguish those cases.

## The stage-1 ceiling

A WebKit memory-corruption bug yields code execution in the browser applet's process. On the Switch that process is sandboxed and has no direct path to the kernel, the boot chain, or Atmosphère. The project's decisive missing stage remains boot-stage execution, as described in [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md). A successful W1/W2 result would be a **stage-1 lead**, not a jailbreak.

## Candidate table

The table separates bugs that are reachable without a JIT from bugs that require one. Most 2023–2025 "WebKit RCE" advisories are JavaScriptCore JIT bugs and are not applicable to an applet with no JIT.

| CVE | Component / primitive | JIT needed? | Reachability on this applet | Status |
|---|---|---|---|---|
| **CVE-2023-28205** | JavaScriptCore `SerializedScriptValue` / `CloneDeserializer`; use-after-free during structured-clone deserialization of `Map`/`Date` objects | **No** | `postMessage` and `Map`/`Date` are present; W1 round-tripped a `Map`/`Date` graph successfully. | **Top candidate.** Public MIT-licensed PoC targets WebKit-613.1.17.1; **W1 passed, W2 not run**. Fix commit `c9880de` replaces non-GC-scanned `Vector` containers with `MarkedVector`. |
| CVE-2022-32893 | WebKit out-of-bounds write (WebKit Bugzilla 243557); component not public in the reviewed text | Unknown | Generic web content; no public PoC found | **Secondary.** Fixed in Safari 15.6.1; the target build predates the fix. Requires patch-diff work, not a ready PoC. |
| CVE-2022-32912 | WebGL2 `drawRangeElements` out-of-bounds read | No | **No WebGL** on the console (`E-061`) | Excluded. |
| CVE-2022-42856 | JavaScriptCore type confusion | Yes | No JIT | Excluded. |
| CVE-2023-37450 | JavaScriptCore JIT optimization issue | Yes | No JIT | Excluded. |
| CVE-2023-41993 | JavaScriptCore type confusion / JIT | Yes | No JIT | Excluded. |
| CVE-2024-23222 | JavaScriptCore type confusion / JIT | Yes | No JIT | Excluded. |
| CVE-2024-44308 | JavaScriptCore DFG JIT register allocation | Yes | No JIT | Excluded. |
| CVE-2023-32409 | WebKit GPU-process IPC sandbox escape | No | Not a first-stage primitive; the applet path does not provide the GPU-process bridge | Excluded as a first stage. |
| CVE-2025-24201 | WebKit sandbox escape | No | Not a first-stage primitive | Excluded as a first stage. |
| CVE-2024-44309 | WebKit cookie management / XSS | No | Not memory corruption | Excluded. |
| CVE-2024-27834 | WebKit pointer-authentication bypass | No | Switch 1 has no PAC | Excluded. |
| CVE-2025-31201 | WebKit pointer-authentication bypass | No | Switch 1 has no PAC | Excluded. |
| CVE-2025-31200 | CoreAudio APAC decoder memory corruption | No | Not WebKit; the APAC codec is not expected on the Switch | Excluded. |
| CVE-2023-4863 | libwebp Huffman heap overflow | No | WebP decodes, but the decoder is non-stock and accepted the reproducers without an observable fault | Closed inconclusive in `D7` (`H-008`). |

**Conclusion of the desk review:** only `CVE-2023-28205` combines a public PoC, no JIT requirement, and a reachable structured-clone path. W1 confirmed that the applet can deserialize a `Map`/`Date` graph, so the candidate is reachable; the remaining question is whether this build lacks the `MarkedVector` fix and whether the public PoC produces a controllable fault. W2 is the only way to test that, and it needs separate approval.

## Reachability gates

| Gate | Question | Method | If it fails |
|---|---|---|---|
| **G1** | Does the applet execute a local page? | Captive-portal page load | **Passed** (`E-058`, re-confirmed by `E-112`). |
| **G2** | Does `window.postMessage` round-trip a small `Map`/`Date` object? | `webkit_probe.html` reachability event | **Passed 2026-10-31** (`E-112`): `ok=true`, `mapSize=1`, `dateValue=0`. |
| **G3** | Are ES modules, `Map`, `Date`, `localStorage`, and `window.origin` present? | Probe feature report | **Passed 2026-10-31** (`E-112`): all present, including `moduleScript=true`. |
| **G4** | Does the public PoC's module graph load and run? | W2 page load with `?autorun=1` | Record a load failure as a harness/reachability negative, not a vulnerability negative. |
| **G5** | Does the PoC produce a crash, reboot, or hang? | W2 observation | No signal means the build is not vulnerable to this PoC (or the PoC is incompatible); close the candidate. |
| **G6** | Is the crash a controllable primitive? | Offline triage, repeat only with approval | A NULL dereference or a non-repeatable crash is a DoS signal, not an exploit primitive. |
| **G7** | Can a stage-1 primitive reach kernel/boot? | Separate project direction | Outside this plan; a browser bug alone cannot reach Atmosphère. |

## Phases

### W0 — Local harness and evidence setup (complete 2026-10-30)

Deliverables:

- `scripts/webkit_portal.py` — local DNS/HTTP runner with preflight, timestamped logging, a bounded duration, a loopback self-test, a printed console runbook, and an optional `--site <dir>` static-site mode for W2.
- `scripts/webkit_probe.html` — engine/build probe with JS/CSS/media feature checks, a `postMessage` round-trip check, a module-script check, heartbeat, and `onerror`/`unhandledrejection` reporting to `/fp`.
- `tests/test_webkit_portal.py` — loopback tests for interface parsing, port checks, preflight, runbook text, site-mode traversal/MIME handling, and the self-test.

Validation performed:

```sh
python3 scripts/webkit_portal.py --local-test
python3 -m unittest discover -s tests
python3 scripts/validate_research.py
python3 scripts/webkit_portal.py --dry-run
```

The self-test uses loopback high ports and needs no root. The dry run resolves the Mac's default-route LAN address (`192.168.178.167`), binds that address, and reports the low-port `sudo` requirement as a note. The runner deliberately does **not** bind `0.0.0.0:53`: Cloudflare WARP holds `127.0.2.2:53` and `127.0.2.3:53` on this Mac, so a wildcard UDP bind fails with `EADDRINUSE`. Binding the LAN address avoids the conflict and exposes the responder only on the Wi-Fi interface.

**Gate W0:** self-test PASS, the full test suite passes, the validator passes, and the dry run prints the correct LAN address and a reversible console runbook. No console contact.

### W1 — Reachability probe (one console page load; separate approval)

**Purpose:** prove that the applet can deserialize a structured-clone graph through `postMessage`, without serving the PoC.

Procedure:

1. Start the runner with the default page and a 300-second bound:

   ```sh
   sudo python3 scripts/webkit_portal.py --duration 300
   ```

   The runner prints the Mac LAN address, DNS/HTTP endpoints, page, log path, and the console steps. It binds the LAN address, not the wildcard address.

2. On the console: **Settings → Internet → Internet Settings → [active network] → Change Settings → DNS Settings → Manual**, set the primary DNS to the printed Mac address, save, and run **Test Connection**.

3. The console resolves `ctest.cdn.nintendo.net` to the Mac, receives the redirect, loads `/portal`, and the page posts `probe`, `reachability`, heartbeat, and error events to `/fp`.

4. Revert **DNS Settings** to **Automatic** immediately after the page reports `probe sent` or after 30 seconds. Stop the runner with Ctrl-C; the timer also stops it after 300 seconds.

5. Preserve the log at `research/hardware-observations/webkit-portal-<UTC>.local.jsonl` (ignored by git). Write a tracked, sanitized summary observation after the run.

**Pass criteria:** the log contains a `reachability` event with `result.ok: true`, a `mapSize` of 1, and a `dateValue` of 0; the `features` report shows `postMessage`, `MessageChannel` (or a documented absence), `structuredClone`, `Map`, `Date`, `localStorage`, and `moduleScript: true`.

**Fail criteria:** no page load, no `postMessage` round-trip, or no `Map`/`Date` clone. Record the failure and close the structured-clone candidate; do not serve the PoC.

**Stop conditions:** the console hangs, reboots, or shows a crash report; DNS cannot be reverted; the applet cannot be closed. Stop, record, and do not repeat the load.

**Result (2026-10-31): PASS.** The console at `192.168.178.136` loaded the probe from the Mac, made 30 DNS queries for `ctest.cdn.nintendo.net`, and fetched `/portal` at 17:12:35 local. The reachability event at 16:12:38.516Z reported `ok=true`, `marker=4660`, `mapSize=1`, and `dateValue=0`. The feature report showed `postMessage`, `MessageChannel`, `MessagePort`, `BroadcastChannel`, `Worker`, `structuredClone`, `origin=http://192.168.178.167`, `moduleScript=true`, `Map`, `Date`, `localStorage`, `sessionStorage`, and `indexedDB`; `WebAssembly`, `SharedArrayBuffer`, `Atomics`, WebGL, `Intl`, and `crypto.subtle` were absent. The page sent 20 heartbeats and a `done` event; there were no `error` or `unhandledrejection` events. The owner reported normal console behavior and reverted DNS to Automatic. The sanitized record is [`research/hardware-observations/2026-10-31-webkit-w1.json`](../research/hardware-observations/2026-10-31-webkit-w1.json) and `E-112`; the full JSONL log is local-only. This passes G1–G3, not the vulnerability test.

### W2 — Public PoC crash check (one console page load; separate approval)

**Only if W1 passes.** This is exploit testing, not fingerprinting, and needs its own approval naming the exact PoC revision, page, duration, and console state.

The public PoC is MIT-licensed (`Copyright (c) 2024 Nathan Fargo`) and uses ES modules and relative imports (`poc.js`, `module/...`). Pin the fetch to commit `57126d03eeceb2e46b39adbe1fad2abf08ed33e3` (2026-01-04): `index.html` SHA-256 `3d9074f1c72bbff804ab84218124193b71a95c0666a9fbe0f2742c78028cc4a4`, `poc.js` SHA-256 `873fe43af25961b312ff3d24c20c15a5475a51ac359cdb572dcb150f11137be4`, and `LICENSE` SHA-256 `f35dc89ed271b7cf6b599a6d1bd43269f2306c8e1669035f97db48f98184875a`. The runner now has a tested `--site <dir>` static-site mode with path-traversal and dotfile protection and explicit `text/javascript` MIME mapping for `.js`/`.mjs`. It serves `index.html` at `/portal` and every other file at the URL root, so the PoC's relative imports resolve without rewriting its logic.

Do not vendor the PoC into git. Fetch it into `scripts/assets.local/uaf-2023-28205/` (ignored), keep its `LICENSE`, and serve it locally only after approval. A read-only source inspection has been done, but the PoC has **not** been served to the console or executed, and it is not in the repository.

**Persistent write:** the PoC writes a run log and a run counter to the applet's `localStorage` (`uaf-2023-28205.logs`, capped at 2000 entries). This is applet-local storage, not the console filesystem, but it is a persistent write. W2 therefore needs either explicit approval for that write or an in-memory shim installed before `poc.js` is imported. A local WebKit test confirmed that `Object.defineProperty(window, 'localStorage', {value: shim})` works. A shim wrapper can also stop the PoC's infinite loop after 120 seconds by navigating to `about:blank`; without it, the 300-second runner bound stops DNS/HTTP but does **not** stop the page, so the owner must close the applet manually.

**Observable signal:** in crash mode, if the UAF triggers without crashing, the PoC calls `alert('triggered, try crash')`. Dismiss it and record the index it displays. If neither a crash nor the alert appears within 120 seconds, close the applet and record a negative result.

Procedure (after approval):

1. Start the runner with the PoC site, the auto-run entry query, and a 300-second bound:

   ```sh
   sudo python3 scripts/webkit_portal.py \
     --site scripts/assets.local/uaf-2023-28205 \
     --entry-query autorun=1 \
     --duration 300
   ```

   The `/` request redirects to `/portal?autorun=1`; the PoC's `index.html` calls `main()` when the `autorun` parameter is present. The runner serves `poc.js` and `module/*.mjs` from the same root with `text/javascript`. The runner bound covers DNS/HTTP; the page's JavaScript continues until it crashes, navigates away, or is closed.

2. Point the console's DNS at the Mac as in W1, run **Test Connection** once, and observe the applet.
3. Revert DNS immediately. Do not reload the page, click retry, or run a second attempt.
4. Record whether the applet crashed, the console rebooted, the page hung, the PoC alert appeared, or the page completed without a fault. Preserve the log and any crash report the console displays. If neither a crash nor the alert appears within 120 seconds, close the applet and record a negative result.

**Signal:** a crash, reboot, or hang that occurs on the PoC page and not on the W1 page. A crash is **not** proof of exploitability; it is a reason to triage offline.

**No signal:** the build is not vulnerable to this PoC, the PoC is incompatible with the applet, or the module graph did not load. Distinguish those cases from the log; close the candidate if the module graph loaded and the page completed.

**Stop conditions:** any crash/reboot/hang; the console becomes unresponsive; the DNS revert fails. Do not repeat the PoC without a new approval and a new hypothesis.

### W3 — Crash triage and primitive assessment (offline/read-only; separate approval)

If W2 produces a crash:

- determine whether the fault matches the expected `CloneDeserializer` UAF (fault address, stack shape, repeatability);
- determine whether the build lacks the `MarkedVector` fix, using read-only analysis of the owner's own browser NCA if the available keys decrypt it;
- decide whether the crash is a controllable primitive or only a denial of service.

Do not publish decrypted modules, keys, or raw crash memory. A NULL dereference, a non-repeatable crash, or a crash in an unrelated parser is a negative for exploitation even if it is a real bug.

**Gate W3:** a repeatable, controllable primitive is required before any exploitation work. Without it, close the candidate.

### W4 — Stage-1 to userland (not authorized now)

Only if W3 yields a controllable primitive. This requires a full exploit chain, a sandbox escape, and a kernel or boot-stage path. The project has no such chain, and the browser alone cannot provide one. Each step needs separate approval; the stage-1 ceiling remains.

### W5 — Close-out and monitoring

- Record the W1/W2 result in the evidence ledger and the browser hypothesis.
- If negative, close the candidate and do not fuzz the applet blindly.
- Continue read-only monitoring for a packaged Switch 1 `ns2jb`, a new `23.0.1` Mariko chain, or a new no-JIT browser candidate.

## Runbook summary

```sh
# Local validation, no root, no console
python3 scripts/webkit_portal.py --local-test
python3 -m unittest discover -s tests
python3 scripts/validate_research.py

# Dry run: prints the LAN address and reversible console steps
python3 scripts/webkit_portal.py --dry-run

# W1: one bounded console page load; needs root for DNS 53 / HTTP 80
sudo python3 scripts/webkit_portal.py --duration 300

# W2 (only after separate approval): one bounded PoC page load
sudo python3 scripts/webkit_portal.py \
  --site scripts/assets.local/uaf-2023-28205 \
  --entry-query autorun=1 \
  --duration 300
```

Console steps:

1. **Settings → Internet → Internet Settings → [active network] → Change Settings.**
2. **DNS Settings → Manual.** Primary DNS: the Mac's LAN address printed by the runner. Secondary DNS: the router address, or automatic if allowed.
3. Save, then **Test Connection**.
4. Wait for `probe sent` (or up to 30 seconds), then revert **DNS Settings** to **Automatic**.
5. Stop the runner with Ctrl-C.

The responder answers DNS locally and serves one page. It does not forward packets, proxy Nintendo services, or capture credentials.

## Evidence to record

- The runner's JSONL log, kept local (`.local.jsonl` is ignored).
- A tracked observation JSON with the console model/firmware, the page hash, the event counts, the reachability result, and the console's visible behavior. No full serial numbers, tokens, or credentials. W1 is recorded in [`research/hardware-observations/2026-10-31-webkit-w1.json`](../research/hardware-observations/2026-10-31-webkit-w1.json).
- An evidence-ledger entry for W1 (and W2 if run), with the exact command, duration, page hash, and limitations. W1 is `E-112`.
- A hypothesis update for `H-005` (browser WebKit n-day applicability), including the new candidate and the console result.

## Stop conditions and recovery

- **Applet hang or crash:** stop the runner, revert DNS, close the applet, and power-cycle only if the console is unresponsive. Record the page and the last log event; do not repeat the load.
- **Console reboot:** do not re-enter the applet. Record the time, the page, and any error code; preserve the log.
- **DNS revert fails:** restore the network settings manually before doing anything else. Do not leave the console pointed at the Mac.
- **Runner cannot bind 53:** confirm it is binding the LAN address, not `0.0.0.0`; Cloudflare WARP holds `127.0.2.2/3:53`. Do not kill WARP or other system services.
- **Page does not load:** check the DNS and HTTP log for the console's address; do not toggle the console's network settings repeatedly.

## Sources

- `nvd-cve-2023-28205`, `apple-security-ios-16.4.1`, `webkit-commit-c9880de`, `github-uaf-2023-28205`
- `nvd-cve-2022-32893`, `webkit-bugzilla-243557`, `webkitgtk-wsa-2022-0009`, `nvd-cve-2025-31200`
- `switchbrew-internet-browser`, `nvd-cve-2023-4863`

The candidate table is a desk review, not a claim that any CVE is exploitable on this console. The only way to resolve the question is the bounded W1/W2 procedure above.
