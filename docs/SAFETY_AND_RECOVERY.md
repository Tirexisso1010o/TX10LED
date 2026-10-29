# Safety and Recovery

## Scope

This project performs **read-only inspection** of USB devices on macOS, **passive LDN capture** on a Linux host or a Linux VM running on macOS, and **local read-only analysis** of the owner's own firmware dump and keys. The only active wireless actions in scope are explicitly approved LDN host tests and adapter diagnostics described in [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md). The plaintext host test, the 60-second TX check, and three prod-mode host runs were executed. The plaintext host is recorded as inconclusive and the 60-second check as invalid because a wildcard Wi-Fi scan cannot see the null-SSID LDN beacon. The prod-mode hosts emitted valid AES-CTR advertisements but produced no join; the second run's pcap capture failed on a wrapper permission error, and the third run's independent scan did not see the host BSSID. An AP-mode control proved the adapter can transmit at -32 dBm, and a follow-up AP-mode `NL80211_CMD_FRAME` control put a 20-frame test beacon on the air at -28 dBm in all 12 scans. A monitor-mode control showed that monitor-mode injection does not transmit; the current host path is blocked by the driver's monitor-mode TX, not by a console rejection. A unicast control with a temporary station entry and a non-LDN test OUI was accepted by the kernel without a netlink error (`E-095`). A real LDN unicast run then sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID; all requests were accepted, but the console was off/away, so reception was not observed (`E-096`). The driver rejects a broadcast-BSSID action frame with `EINVAL`, so the AP path can only send the AP-BSSID variant (`E-097`). A supervised rerun made the room `TX10LED` appear on the console, but selecting it produced `2203-0065` immediately; the search screen closed, the console returned to the game normally, and hostapd logged no authentication, association, or station event (`E-098`). The room appearance confirms the advertisement reached the scan path; that join failure is consistent with the hostapd WLAN SSID/security not matching the room's 32-character hexadecimal SSID and LDN RSN IE. A second supervised run used the corrected WLAN parameters: the console authenticated, associated with AID 1, and was marked authorized, then disassociated with `reason_code=8` about one second later and sent no observed `0x88B7` request (`E-099`). The owner saw `2203-0066` after a few seconds and a game popup `unable to join the room`; the console returned to the game normally. A local control showed that the AP control port rejects `0x88B7` with `EINVAL`, while the raw authorized-station path transmits it protected with KeyID 0 (`E-100`). A third supervised run omitted the association-response RSN IE and used that raw path, but the console again authenticated, associated, and was authorized, then disassociated with `reason_code=8` before any `0x88B7` request; the pcap contained no console data payload frame (`E-101`). The current hostapd/AP path is negative for `D9`; the parser hypothesis remains untested. The post-run firmware download failure required a USB deauthorize/reauthorize cycle; after that, monitor mode and RX worked again. Location Services restored real BSSIDs for the independent scan. Another active run requires new approval and the console present. The project does not modify the console, its storage, its boot configuration, or its firmware.

The research conclusion is that an unmodified Switch OLED has no publicly documented, reproducible software-only path to Atmosphère. The safe response is not to try increasingly invasive workarounds. It is to stop, document the state, and use a documented route only if you deliberately choose to accept its risks.

## Prohibited actions

Do not use this repository to:

- inject or execute a payload;
- update or downgrade firmware;
- flash, erase, or rewrite NAND or eMMC;
- change partitions or boot configuration;
- install or configure a modchip;
- bypass macOS security controls;
- run privileged drivers or commands;
- kill `ptpcamerad` or another system daemon automatically;
- transmit LDN frames without explicit approval for the specific run;
- use the LDN host to play or share a game, bypass the ticket challenge, or impersonate a GameShare or Virtual Game Card host;
- commit, publish, share, or paste keys, certificates, decrypted system modules, NAND dumps, or proprietary firmware;
- download firmware or keys from a third party;
- use the owner's keys against any console other than the owner's own;
- collect or publish full serial numbers or tokens.

If a procedure requires any of these, it is outside the project's authorization boundary.

## Risk table

| Action | Risk | Authorization |
|---|---|---|
| Enumerate USB devices | Low; reads host device metadata | Allowed |
| Classify a VID:PID offline | None | Allowed |
| Read PTP `GetDeviceInfo` | Low; opens the PTP interface and reads identity data | Requires `--confirm` and a confirmed device identity |
| Enter RCM | Low on its own, but pointless for CFW on patched/Mariko hardware | Not needed for this project |
| Send an RCM payload | High; fails on patched hardware and is outside scope | Prohibited |
| Update firmware | Irreversible eFuse changes; can break CFW compatibility | Prohibited |
| Modchip installation | High; microsoldering, warranty, and bricking risk | Out of scope |
| NAND/eMMC operations | High; data loss and bricking risk | Prohibited |
| Passive LDN capture (monitor mode) | Low; captures frames on the host adapter, transmits nothing | Allowed; keep the pcap and unredacted output local |
| Read-only analysis of the owner's firmware dump and keys | Low; local file parsing, no console interaction | Allowed; artifacts stay local and out of git |
| Transmit LDN frames / host a plaintext or prod-mode LDN network | Medium; can hang or crash the `ldn` sysmodule or Wi-Fi firmware; active frame injection | Explicit approval for the specific run; follow `docs/LDN-TEST-PLAN.md` |
| Install a pairwise CCMP key and answer the LDN `0x88B7` authentication challenge | Medium; the console may reject, hang, or crash the `ldn` sysmodule; the host may transmit malformed authentication data | Separate explicit approval; use the room's real parameters and a bounded challenge response; no application data |

## Before any device interaction

1. Confirm the model under the stand. The OLED model is `HEG-001`.
2. Confirm the firmware in **System Settings → System → System Update**. Do not press Update.
3. Confirm whether the console has ever been opened or modchipped.
4. Use a data-capable USB-C cable in the **bottom** port, not the dock.
5. For PTP, open **Settings → Data Management → Manage Screenshots and Videos → Copy to PC via USB** and leave the screen open.
6. Run `ptp-info --dry-run` first. Read the selected device and the planned operations.
7. Use `--confirm` only after the device identity is confirmed.

The tool never requires RCM for identity inspection.

## Recovery scenarios

### The console is in RCM unexpectedly

- Do not send a payload.
- Disconnect the USB cable.
- Hold the power button until the console powers off, then boot normally.
- On patched/Mariko hardware, RCM cannot accept a payload. Attempting one is not a recovery step.

### The PTP screen is stuck or the console is unresponsive

- Disconnect the USB cable.
- Exit the **Copy to PC via USB** screen with the home button.
- If the console is still unresponsive, hold the power button until it powers off, then boot normally.
- Do not perform a factory reset or initialize the console as a first response. That can destroy data and does not address a host-side USB problem.

### The console is unresponsive after an LDN frame test

- Stop the LDN host and the channel-hop loop first.
- Restore the Linux adapter to managed mode and restart NetworkManager if it is installed.
- Hold the console's power button until it powers off, then boot normally.
- Do not factory-reset or initialize the console as a first response. A wireless hang is not a storage problem.
- Record the exact frame parameters, the host output, and the console's behavior. If the console produced a crash report or error code, preserve it and do not repeat the frame until the report is copied.
- If the console shows `2203-0065` or `2203-0066` and returns to the game normally, do not power-cycle it. Record the error, the room name, whether the search screen closed, and whether hostapd logged authentication or association. That combination is a join failure, not evidence of a parser fault (`E-098`, `E-099`). For `2203-0066`, also record whether the console associated and how long it stayed connected before disassociating; the second and third runs associated with AID 1 and left with reason 8 about one to 1.4 seconds later, without an observed `0x88B7` request (`E-099`, `E-101`).

### The Wi-Fi adapter fails to probe after an LDN host run

- Stop `hostapd` and any `tcpdump` process first.
- Check `dmesg` for `error beacon valid`, `failed to download rsvd page`, `failed to download firmware`, or `probe with driver rtw88_8822bu failed with error -16`.
- If those appear, the driver is wedged; a module reload alone may not recover it.
- Detach and reattach the adapter with OrbStack, then deauthorize/reauthorize the USB device (`echo 0 > /sys/bus/usb/devices/<bus-port>/authorized`, then `echo 1 > ...`) and reload `rtw88_8822bu`.
- Verify with a passive 5-second `tcpdump` on a channel known to have ambient traffic (for example channel 6 or 11). Zero packets on every channel means the radio is not receiving.
- Do not run another LDN test until the adapter receives again.

### The Mac reports the device as busy

- Close applications that may be using the camera/PTP device.
- Disconnect and reconnect the cable.
- Run `doctor` and check whether `ptpcamerad` is running.
- Do not kill the daemon, disable SIP, or install a privileged driver as a first response.
- If the interface remains busy, stop and record the error. A host-side claim conflict is not a reason to escalate privileges.

### A USB operation times out

- Disconnect the cable, reconnect it, and retry the read-only command once.
- If it times out again, stop. Repeated retries can leave a session or interface in a bad state.
- Record the command, exit code, and sanitized log.

### The console was updated unintentionally

- Do not attempt a downgrade. Firmware downgrades can burn or mismatch eFuses and can leave the console unable to boot.
- Record the new firmware version.
- Re-check Atmosphère and hekate compatibility.
- Re-check whether the entry-point conclusion changes. A firmware update does not create an entry point on Mariko.

### A modchip was installed

- This project does not provide modchip recovery or installation guidance.
- Use the installer's or maintained guide's recovery procedure.
- Do not mix instructions from unrelated tools.
- Record the modification in the hardware observation, because it changes the meaning of "unmodified console".

## Local keys and firmware

- The owner's `Firmware/prod.keys.txt` and `Firmware/Firmware.23.0.1` are local-only artifacts from the owner's own modded Switch.
- `.gitignore` excludes `Firmware/`, `Firmware.*/`, and `prod.keys*`. Run `git check-ignore -v Firmware/prod.keys.txt Firmware/Firmware.23.0.1` before any commit that touches the tree.
- Do not copy them into `research/`, `docs/`, `scripts/`, or any path that is not ignored.
- Do not paste key names with values, key material, decrypted NCAs, or decrypted KIPs into chat, issues, commits, or logs. Record only derived, non-secret fields such as the security mode, channel, and participant limits.
- Extracted firmware artifacts inherit the same rule: local only, never committed.

## Privacy

- Report only a serial **prefix** (three characters) when discussing model families.
- Do not paste a full serial into an issue, chat, or commit.
- Review JSONL logs before sharing. The tool redacts serials, but logs may contain device names and paths.
- Do not commit local observation files. Use `*.local.json`; the repository ignores those names.
- Do not upload NAND dumps, keys, certificates, or proprietary firmware.

## Incident response

If something unexpected happens:

1. Stop the operation.
2. Disconnect the console.
3. Do not run additional state-changing commands.
4. Record what happened, the exact command, the exit code, and the sanitized output.
5. Preserve the console state; do not initialize or reformat it.
6. Open a private security report if the issue involves a tool safety boundary.

## Legal and warranty note

Console modification can affect warranty coverage and may violate Nintendo's service terms or local law. This document is not legal advice. Decide deliberately whether to accept those risks; do not treat a research conclusion as authorization. In particular, this project does not authorize bypassing Nintendo's license checks or using LDN research to share games without a valid license.
