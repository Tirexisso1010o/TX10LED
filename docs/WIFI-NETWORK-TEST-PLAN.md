# Wi-Fi and Network Stack Test Plan (D10 / H-011, H-012)

> **Status: Phase 0 complete (host-only; ordinary AP beacons and probe responses only); Phase 1 not started.** This document is an authorization gate, not an approval. Phase 0 established the AP and tooling baseline on 2026-10-29. Phase 1 changes the console's network settings and needs owner approval. Phases 2–6 transmit malformed 802.11 or network data and each need separate explicit approval for the exact case batch. No malformed frame has been sent and the console has not been involved.

## What this tests

This plan covers two related surfaces that a normal Wi-Fi connection exposes:

1. **General 802.11 management and EAPOL parsing** — beacons, probe responses, association responses, and WPA2 EAPOL-Key frames handled by the `wlan` sysmodule and the Wi-Fi firmware.
2. **Network-stack parsing** — DHCP, DNS, IPv6 router advertisements/neighbor discovery, and TLS handshake/certificate data handled by `bsdsocket`, `sfdnsres`, `nifm`/`bsdcfg`, and the `ssl` sysmodule.

It is **not** an LDN test. The LDN pre-auth path (`D9`, `H-010`) is negative for the current hostapd/AP configuration; this plan uses a normal access point and the console's ordinary Wi-Fi client and network-test flows.

No public 23.0.1 vulnerability is claimed. Switchbrew's 23.0.0 changelog records a `bsdsocket` AddrInfo deserialization fix and other network/audio validation fixes, which shows that this stack has recently handled security-relevant input. The target is on 23.0.1, so that specific fix is present; this plan looks for a **different** defect.

## Why this is the next direction

- **The adapter can run an AP.** hostapd 2.11 reaches `AP-ENABLED`, its beacon is visible at -32 dBm, and AP-mode `NL80211_CMD_FRAME` beacon injection is visible at -28 dBm (`E-090`, `E-094`).
- **The console can associate with the adapter's AP.** The LDN AP runs proved authentication, association, and authorization (`E-099`). A normal open/WPA2 AP is the Phase 1 control, not an assumption.
- **The network stack is reachable without a game.** The console's own **Test Connection** flow performs DHCP, DNS, and HTTPS to a connectivity-test endpoint. No game, account, eShop, or paid content is needed.
- **The parser surface is broad but bounded.** One malformed field at a time can be attributed to one parser, and the console's error code and responsiveness give a clear stop signal.

## Scope and non-goals

**In scope**

- The owner's `HEG-001` console on 23.0.1, connected only to a dedicated test SSID that this project creates.
- Normal AP association and the built-in **Test Connection** flow.
- Bounded malformed 802.11 management/EAPOL frames and DHCP/DNS/IPv6/TLS responses, one variable at a time, with explicit approval.

**Out of scope**

- Nintendo Account login, eShop, GameShare, Virtual Game Cards, game sharing, license circumvention, or piracy.
- Capturing or replaying account credentials, tokens, cookies, or any Nintendo service response other than the local connectivity-test endpoint.
- Firmware update or downgrade, NAND/eMMC access, payload injection, modchip work, or save manipulation.
- Exploit development. A fault is a lead, not an exploit.
- Any third-party network or any console other than the owner's.

**Host-spoofing boundary.** DHCP, DNS, and IPv6 responses are part of running a test AP and are in scope. The TLS phase is different: it requires a local DNS sinkhole for the console's connectivity-test hostname so the console connects to a local TLS server. That phase is **optional and separately gated**. It must not proxy account/eShop traffic, capture credentials, or impersonate a Nintendo service beyond returning a local test endpoint. If the owner is not comfortable with that, skip Phase 6.

## Hardware and host

- macOS 26.3 on Apple silicon.
- OrbStack Ubuntu 26.04 arm64 VM with USB passthrough.
- TP-Link Archer T3U Plus (`2357:0138`, `rtw88_8822bu`), used in **AP mode**.
- hostapd 2.11, dnsmasq, radvd, Python 3.12 with Scapy, tcpdump, and OpenSSL.
- The Mac's built-in Wi-Fi, with Location Services enabled, for independent control scans (`E-092`).
- The VM's virtual Ethernet for upstream access. The USB adapter must not be the only network path.

### Adapter limits carried over from D9

- **Monitor-mode injection does not transmit** on `rtw88_8822bu` (`E-091`). Do not build this plan on monitor-mode TX.
- **AP-mode beacon injection works** (`E-094`), and a unicast vendor action with a temporary station entry is accepted by the kernel (`E-095`).
- **AP + monitor concurrency was tested in Phase 0.** A same-phy monitor interface can be created while hostapd runs, but it does not capture the AP's own frames on `rtw88_8822bu`. Use the hostapd `-dd` log for management-frame attribution and the Mac's independent scan for the on-air control. Do not rely on the same-phy monitor for injected-frame evidence.
- **The driver can wedge after hostapd stops.** Recovery is in [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md).

### Host packages

```bash
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq radvd tcpdump iw ethtool usbutils \
  python3 python3-venv python3-pip openssl
python3 -m venv ~/wifi-venv
~/wifi-venv/bin/pip install scapy
```

Do not install or run a custom kernel driver. Use the in-kernel `rtw88_8822bu` driver.

## Console test network

Create **new** networks on the console; do not edit or delete the owner's existing networks.

| SSID | Security | Purpose |
|---|---|---|
| `TX10LED-NET` | Open | Phase 1 baseline, beacon/probe/association IE fuzzing |
| `TX10LED-WPA2` | WPA2-PSK, AES/CCMP | Phase 1 WPA2 control and Phase 3 EAPOL |

- Use a random, local-only WPA2 passphrase. Do not commit it.
- Keep the console on AC power for active phases.
- Use **Settings → Internet → Internet Settings → Test Connection** for DHCP/DNS/TLS. This does not write save data or launch a game.
- For scan/association phases, use the **Internet Settings** network list. Do not open eShop, a Nintendo Account flow, or a game.
- After the tests, delete the two test networks. If the console's network settings misbehave, delete only the test network; do **not** initialize the console.

## Phase 0 — host-only setup (no console interaction)

**Result (2026-10-29): complete.** hostapd 2.11 reached `AP-ENABLED` for both `TX10LED-NET` and `TX10LED-WPA2` on channel 1. The independent macOS CoreWLAN scan saw both SSIDs at -34 dBm on channel 1. dnsmasq 2.92, radvd 2.20, OpenSSL 3.5.5, Scapy 2.8.0, and tcpdump 4.99.6 passed start/stop checks. A same-phy monitor interface was created while the AP ran, but it captured zero frames from the AP's BSSID, so management-frame attribution will use hostapd `-dd` logs and the independent scan. The console was not involved. See `research/hardware-observations/2026-10-29-wifi-phase0.json` and `E-104`.

1. Verify the adapter and driver:

   ```bash
   ip -br link
   iw dev
   ethtool -i <interface>
   iw list | sed -n '/Supported interface modes/,/Band 1/p'
   ```

2. Start an open test AP:

   ```ini
   interface=<interface>
   driver=nl80211
   ssid=TX10LED-NET
   hw_mode=g
   channel=1
   beacon_int=100
   auth_algs=1
   wpa=0
   ignore_broadcast_ssid=0
   ```

   ```bash
   sudo hostapd -dd /etc/hostapd/tx10led-open.conf
   ```

3. From the Mac, run a Location Services-enabled wildcard scan and confirm `TX10LED-NET` is visible with the adapter's BSSID. This is the independent AP control.

4. Start a WPA2 test AP with `wpa=2`, `wpa_key_mgmt=WPA-PSK`, `rsn_pairwise=CCMP`, and a local-only passphrase. Confirm the SSID is visible. Do not connect the console yet.

5. Verify AP + capture. If a same-phy monitor interface cannot capture while hostapd runs, record that and use `tcpdump -i <ap-interface>` plus hostapd logs.

6. Verify dnsmasq, radvd, Scapy, and OpenSSL start and stop cleanly. No console is involved in this phase.

**Exit criteria:** the AP is visible, hostapd reaches `AP-ENABLED`, the independent scan sees the test SSID, and the capture path is known. If not, stop and record the host blocker.

## Phase 1 — baseline association and passive capture (approval required)

**This phase changes the console's network settings. It transmits no malformed frames.**

### State A — open network

1. On the console, add `TX10LED-NET` and connect.
2. Leave the console on **Internet Settings** or the Home screen.
3. Run **Test Connection** once.
4. Capture on the AP interface or monitor interface for the whole sequence.
5. Record: association result, DHCP lease, DNS queries, TLS endpoint, console error code (if any), and whether the console stays associated.

### State B — WPA2 network

1. Add `TX10LED-WPA2` and connect with the local passphrase.
2. Capture the 4-way handshake.
3. Run **Test Connection** once.
4. Record the same fields, plus whether the handshake completes and whether the console stays associated.

**This is the control.** A malformed test is only interpretable if the matching control associates and reaches the intended parser. If the console refuses the open or WPA2 test AP, record the phase as blocked and do not proceed to the dependent active phase.

**No injection in Phase 1.** Do not send beacons, EAPOL, DHCP, DNS, RA, or TLS data beyond what hostapd/dnsmasq/radvd normally send.

## Phase 2 — 802.11 management IE fuzzing (active, approval required)

**This phase transmits malformed 802.11 management frames. Do not run it without explicit approval for the exact batch.**

### Common procedure

- Console state: associated to `TX10LED-NET`, on **Internet Settings** or Home.
- Keep hostapd running with `beacon_int=1000` so the valid beacon is sparse.
- Inject one malformed beacon at 200 ms intervals for 5 seconds (25 frames). Copy every field from the control beacon except the one malformed IE.
- Capture on the AP/monitor interface and record whether the console disconnects, shows an error, hangs, or reboots.
- Wait 10 seconds after the batch. If the console disconnected, reconnect before the next case.
- Run the control first: 25 well-formed beacons with the same length and rate.

### 2A — Beacon IE matrix

| ID | Frame | Malformed field | Frames | Batch |
|---|---|---|---|---|
| W-01 | Beacon | SSID IE length 33 with 33 bytes | 25 | 1 |
| W-02 | Beacon | SSID IE length 0 | 25 | 1 |
| W-03 | Beacon | Supported Rates IE length 0 | 25 | 1 |
| W-04 | Beacon | Supported Rates IE length 9 | 25 | 1 |
| W-05 | Beacon | DS Parameter IE length 0 | 25 | 1 |
| W-06 | Beacon | DS Parameter IE length 3 | 25 | 1 |
| W-07 | Beacon | RSN IE length 1 with 1 byte | 25 | 1 |
| W-08 | Beacon | RSN IE length 255, all `0xff` | 25 | 1 |
| W-09 | Beacon | Vendor IE (221) length 0 | 25 | 2 |
| W-10 | Beacon | Vendor IE length 255, OUI `00:22:aa`, type `0x04` | 25 | 2 |
| W-11 | Beacon | Extended Capabilities IE length 0 | 25 | 2 |
| W-12 | Beacon | HT Capabilities IE length 1 | 25 | 2 |
| W-13 | Beacon | VHT Capabilities IE length 1 | 25 | 2 |
| W-14 | Beacon | Country IE length 1 | 25 | 2 |

**Batch 1:** W-01 through W-08 plus control W-C. **Batch 2:** W-09 through W-14 plus control W-C. Do not combine batches.

### 2B — Probe response and association response (conditional)

Stock hostapd can add raw **vendor** IEs to probe responses and association responses with `vendor_elements` and `assocresp_elements`. Arbitrary non-vendor IE replacement requires a patched hostapd or a userspace AP; that is not part of the first batch.

| ID | Frame | Malformed field | Count | Batch |
|---|---|---|---|---|
| P-01 | Probe response | Vendor IE length 0 | 1 per probe request, max 5 | 1 |
| P-02 | Probe response | Vendor IE length 255, OUI `00:22:aa`, type `0x04` | 1 per probe request, max 5 | 1 |
| A-01 | Association response | Vendor IE length 0 | 1 per association attempt, max 3 | 1 |
| A-02 | Association response | Vendor IE length 255, OUI `00:22:aa`, type `0x04` | 1 per association attempt, max 3 | 1 |
| P-03 | Probe response | RSN IE length 1 or 255 | 1 per probe request, max 5 | Deferred |
| A-03 | Association response | RSN IE length 1 or 255 | 1 per attempt, max 3 | Deferred |
| A-04 | Association response | Extended Capabilities IE length 0 | 1 per attempt, max 3 | Deferred |

**Procedure:** put the console on the network-selection screen so it scans and probes. For P-01/P-02, answer one probe request with one malformed probe response; do not answer every request. For A-01/A-02, use a fresh association attempt per case. If the kernel rejects the unicast probe/association response or hostapd does not emit the malformed vendor IE, record the case as blocked; do not fall back to a different frame type without approval.

**Controls:** P-C and A-C use the same vendor IE with a well-formed length and payload.

## Phase 3 — EAPOL fuzzing (active, approval required; conditional)

**This phase transmits EAPOL-Key frames to an associated console. Do not run it without separate approval.**

### Preconditions

- Console is associated to `TX10LED-WPA2` and the normal 4-way handshake completes.
- The host can send EAPOL with `NL80211_CMD_CONTROL_PORT_FRAME` (ethertype `0x888E`), which the AP control port accepts (`E-100`). If it cannot, record the phase as blocked.
- **Control E-C:** after the normal handshake, send one well-formed EAPOL-Key rekey frame. If the console ignores it, disconnects, or the host cannot send it, stop; do not send malformed EAPOL.

### EAPOL-Key matrix

| ID | Field | Malformed value | Frames | Batch |
|---|---|---|---|---|
| E-01 | EAPOL version | 0 | 1 | 1 |
| E-02 | EAPOL version | 255 | 1 | 1 |
| E-03 | Descriptor type | 0 | 1 | 1 |
| E-04 | Descriptor type | 255 | 1 | 1 |
| E-05 | Key info | `0x0000` | 1 | 1 |
| E-06 | Key info | `0xffff` | 1 | 1 |
| E-07 | Key length | 0 | 1 | 1 |
| E-08 | Key length | `0xffff` | 1 | 1 |
| E-09 | Key data length | `0xffff` with only 2 bytes present | 1 | 2 |
| E-10 | Key data RSN IE | Length 0 | 1 | 2 |
| E-11 | Key data RSN IE | Length 255, truncated | 1 | 2 |
| E-12 | Replay counter | All `0xff` | 1 | 2 |
| E-13 | Nonce | All zero | 1 | 2 |
| E-14 | MIC | All zero | 1 | 2 |

**Batch 1:** E-01 through E-08 plus control E-C. One malformed frame per association; reconnect between cases. **Batch 2:** E-09 through E-14, same procedure.

Stop on the first disconnect that does not recover, error code, hang, reboot, or crash report. A clean deauthentication/reconnect is not a fault; record it and continue only if the control still works.

## Phase 4 — DHCP and DNS fuzzing (active, approval required)

**This phase sends crafted DHCP/DNS responses. Do not run it without explicit approval.**

### Baseline

Run dnsmasq as the DHCP/DNS server and complete one **Test Connection**. Record the normal lease, DNS query names, response times, and console error (none expected). The malformed server must reproduce the same lease and query flow with exactly one changed field.

### DHCP matrix

| ID | Message | Malformed field | Responses | Batch |
|---|---|---|---|---|
| D-01 | DHCPOFFER | Option 1 (subnet mask) length 0 | 1 | 1 |
| D-02 | DHCPOFFER | Option 1 length 3 | 1 | 1 |
| D-03 | DHCPOFFER | Option 3 (router) length 0 | 1 | 1 |
| D-04 | DHCPOFFER | Option 3 length 5 | 1 | 1 |
| D-05 | DHCPOFFER | Option 6 (DNS) length 0 | 1 | 1 |
| D-06 | DHCPOFFER | Option 6 length 5 | 1 | 1 |
| D-07 | DHCPOFFER | Option 51 (lease time) length 3 | 1 | 1 |
| D-08 | DHCPOFFER | Option 54 (server identifier) length 0 | 1 | 1 |
| D-09 | DHCPOFFER | Option 15 (domain name) length 0 | 1 | 2 |
| D-10 | DHCPOFFER | Option 119 (domain search) compression-pointer loop | 1 | 2 |
| D-11 | DHCPACK | `yiaddr` `0.0.0.0` | 1 | 2 |
| D-12 | DHCPACK | `chaddr` mismatch | 1 | 2 |

**Batch 1:** D-01 through D-08 plus control D-C. **Batch 2:** D-09 through D-12. One malformed OFFER/ACK per **Test Connection** attempt; wait 10 seconds and reconnect the test network between cases. Maximum 3 retries per case.

### DNS matrix

| ID | Message | Malformed field | Responses | Batch |
|---|---|---|---|---|
| N-01 | DNS response | `QDCOUNT=2` with one question | 1 | 1 |
| N-02 | DNS response | `ANCOUNT=1` with no answer | 1 | 1 |
| N-03 | DNS response | Answer name pointer to itself | 1 | 1 |
| N-04 | DNS response | Compression pointer beyond packet | 1 | 1 |
| N-05 | DNS response | Label length 64 | 1 | 1 |
| N-06 | DNS response | Name length greater than 255 | 1 | 1 |
| N-07 | DNS response | `RDLENGTH` greater than remaining data | 1 | 1 |
| N-08 | DNS response | CNAME loop | 1 | 1 |
| N-09 | DNS response | EDNS0 OPT `RDLEN=0xffff` truncated | 1 | 2 |
| N-10 | DNS response | Multiple CNAME/A records with inconsistent counts | 1 | 2 |

**Batch 1:** N-01 through N-08 plus control N-C. **Batch 2:** N-09 and N-10. Answer one query per **Test Connection** attempt; do not answer every query in the flow.

**Stop conditions:** any console hang, reboot, crash report, new error code, or loss of Wi-Fi that does not recover in 30 seconds.

## Phase 5 — IPv6 router advertisement / neighbor discovery (active, approval required; conditional)

**This phase sends crafted ICMPv6 messages. Do not run it without explicit approval.**

### Preconditions

- radvd baseline sends a normal RA.
- The console acquires an IPv6 address, or the host observes the console's Router Solicitation / Neighbor Solicitation. Verify with `tcpdump -i <interface> icmp6` and `ip -6 neigh`.
- If the console never uses IPv6, record the phase as **not reachable**; do not force it with malformed RAs.

### IPv6 matrix

| ID | Message | Malformed field | Rate | Batch |
|---|---|---|---|---|
| I-01 | RA | Option length 0 | 1/s for 10 s | 1 |
| I-02 | RA | Source link-layer address option length 2 | 1/s for 10 s | 1 |
| I-03 | RA | MTU option length 0 | 1/s for 10 s | 1 |
| I-04 | RA | Prefix Information option length 0 | 1/s for 10 s | 1 |
| I-05 | RA | Prefix Information option length 5 | 1/s for 10 s | 1 |
| I-06 | RA | RDNSS option length 0 | 1/s for 10 s | 1 |
| I-07 | RA | DNSSL option length 255, truncated | 1/s for 10 s | 2 |
| I-08 | RA | ICMPv6 payload length 15 | 1/s for 10 s | 2 |
| I-09 | RA | Hop limit 0 | 1/s for 10 s | 2 |
| I-10 | RA | Unknown option length 0 | 1/s for 10 s | 2 |

**Batch 1:** I-01 through I-06 plus control I-C (normal RA). **Batch 2:** I-07 through I-10. One RA per second for 10 seconds; stop immediately if the console loses IPv6 or Wi-Fi.

## Phase 6 — TLS handshake and certificate parsing (active, approval required; optional)

**This phase requires a local DNS sinkhole for the console's connectivity-test hostname and a local TLS server. Do not run it without separate approval and an explicit decision that this is within scope.**

### Preconditions

- The console's **Test Connection** reaches a local TLS listener on port 443 after DNS resolution of the connectivity-test hostname to the VM.
- A control with a valid self-signed certificate completes a TCP/TLS handshake and is rejected by the console's certificate validation with a normal error. The rejection is expected; a crash is not.
- No Nintendo Account, eShop, or game traffic is proxied. No credentials, cookies, or tokens are captured. If any appear, stop and delete the capture.

### TLS matrix

| ID | Message | Malformed field | Connections | Batch |
|---|---|---|---|---|
| T-01 | TLS record | Record length 0 | 1 | 1 |
| T-02 | TLS record | Record length larger than data | 1 | 1 |
| T-03 | TLS handshake | Handshake length larger than record | 1 | 1 |
| T-04 | TLS certificate | Certificate length larger than handshake | 1 | 1 |
| T-05 | TLS certificate | DER length `0xffffffff` | 1 | 1 |
| T-06 | TLS certificate | DER indefinite length | 1 | 1 |
| T-07 | TLS certificate | Chain of 1,000 certificates | 1 | 2 |
| T-08 | TLS certificate | Duplicate SAN extension | 1 | 2 |
| T-09 | TLS certificate | SAN GeneralName length overflow | 1 | 2 |
| T-10 | TLS certificate | Invalid validity time | 1 | 2 |

**Batch 1:** T-01 through T-06 plus control T-C. **Batch 2:** T-07 through T-10. One connection per **Test Connection** attempt. If the console does not connect to the local listener, record the phase as blocked; do not spoof a different hostname.

## Approval record

Every active batch needs a filled copy of this table before it runs.

| Field | Value |
|---|---|
| Phase / batch | |
| Case IDs | |
| Maximum frames or responses | |
| Console state | |
| Test SSID | |
| Host state | |
| Approved by | |
| Date and time | |
| Stop conditions acknowledged | |

**No approval, no transmission.** A general statement such as "continue the research" is not approval for a specific batch.

## Stop conditions

Stop the run immediately and preserve the logs if any of these occur:

- The console hangs, reboots, shows a black screen, or does not respond for 30 seconds.
- The console shows an error code that did not appear in the Phase 1 control.
- Wi-Fi disconnects and does not recover within 30 seconds.
- The console shows a crash report, a system-memory error, or an update prompt.
- hostapd, dnsmasq, radvd, or the capture process crashes.
- The adapter stops receiving or `dmesg` shows a firmware download/probe failure.
- The console starts an account login, eShop, GameShare, Virtual Game Card, or game flow.
- A credential, token, cookie, or Nintendo service response appears in the capture.
- The control case fails, or the malformed frame/packet cannot be attributed to one field.

After the first anomaly, do **not** send another case. Copy the logs, record the exact case ID and frame/packet bytes, and review before any repeat.

## Recovery

### Console unresponsive after a Wi-Fi/network test

1. Stop hostapd, dnsmasq, radvd, and tcpdump.
2. Restore the adapter to managed mode and restart NetworkManager if installed.
3. Hold the console's power button until it powers off, then boot normally.
4. Do not factory-reset or initialize the console. A wireless or network-stack hang is not a storage problem.
5. If the console shows an error code and remains responsive, record it and do not power-cycle.
6. If a crash report appears, copy it before rebooting and do not repeat the input.

### Network settings are wrong or the test SSID is stuck

- Delete only `TX10LED-NET` and `TX10LED-WPA2` in **Internet Settings**.
- Do not delete the owner's existing networks.
- Do not initialize the console.

### Adapter is wedged

- Stop hostapd and tcpdump.
- Check `dmesg` for `failed to get tx report from firmware`, `failed to download firmware`, or `probe with driver rtw88_8822bu failed`.
- Deauthorize/reauthorize the USB device in OrbStack, reload `rtw88_8822bu`, and verify RX with a 5-second passive capture on a channel with ambient traffic.
- Do not run another test until RX works.

### Console was updated unintentionally

- Do not attempt a downgrade.
- Record the new firmware version and re-check the entry-point conclusion.
- A firmware update does not create a Mariko entry point.

## Evidence and privacy

- Keep pcaps, hostapd/dnsmasq/radvd logs, Scapy scripts, and the WPA2 passphrase **local only**. Do not commit them.
- Write one sanitized JSON record per case under `research/hardware-observations/` with:
  - case ID, phase, date/time;
  - frame or packet type and length;
  - the one malformed field and value;
  - frame/packet count;
  - console state and exact error code;
  - host result and control result;
  - whether the console stayed associated/responsive.
- Redact MAC addresses and any local identifiers. The test SSID may be recorded; the WPA2 passphrase may not.
- Add evidence-ledger entries only after a run. An observation is `VERIFIED`; a hypothesis stays `UNKNOWN` until a reproducible fault is demonstrated.
- Never record a crash as an exploit. A crash is a lead that needs a second reproduction, minimization, and parser attribution.

## Kill criteria

**A phase is negative** if the control is clean, every case in the approved batch produces no crash, reboot, hang, or new error, and the console remains responsive. Record the exact matrix and close that phase.

**A phase is blocked** if the console cannot associate, the host cannot transmit the required frame/packet, the adapter cannot capture, or the console never reaches the parser (for example, no IPv6 address or no TLS connection). Record the blocker; do not reinterpret it as a console rejection.

**D10 is negative** if every reachable phase is negative. Close the direction and do not repeat the same matrix without a materially different input or a new public lead.

**A single reproducible crash/reboot tied to one input is a lead, not an exploit.** Stop, reproduce once with the control, minimize the input, identify the parser, and review before any capability claim.

## Capability ceiling

- `wlan`, `bsdsocket`, `sfdnsres`, `nifm`/`bsdcfg`, and `ssl` are system services or sysmodules. A fault in them is **stage 1–2 at best**.
- A Wi-Fi firmware fault is below Horizon but still **not boot-stage execution**.
- Atmosphère needs boot-stage execution (warmboot/package1). That stage remains blocked: the 23.0.1 BOOT0/package1 image and generation `0x17` keys are unavailable, and the modded 22.0.0 console is off-limits.
- A successful D10 result would be a primitive or a denial-of-service finding, not a software-only jailbreak.

## Related records

- [`docs/RESEARCH-PLAN.md`](RESEARCH-PLAN.md) — D10 and the ranked directions.
- [`research/hypotheses.json`](../research/hypotheses.json) — H-011 and H-012.
- [`docs/ENTRY-POINTS.md`](ENTRY-POINTS.md) — EP-008 system services/sysmodules and EP-005 LDN.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — authorization, recovery, and privacy.
- [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md) — the AP-mode controls reused here.
- [`research/evidence-ledger.json`](../research/evidence-ledger.json) — `E-024`, `E-090`, `E-094`, `E-095`, `E-100`.
- [`research/sources.json`](../research/sources.json) — `switchbrew-wlan`, `switchbrew-sockets`, `switchbrew-ssl`, `switchbrew-23.0.0`, `switchbrew-system-flaws`.
