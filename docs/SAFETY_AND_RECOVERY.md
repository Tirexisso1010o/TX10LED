# Safety and Recovery

## Scope

This project performs **read-only inspection** of USB devices on macOS and **passive LDN capture** on a Linux host. The only active wireless action in scope is a single, explicitly approved plaintext LDN host test described in [`docs/LDN-TEST-PLAN.md`](LDN-TEST-PLAN.md). The project does not modify the console, its storage, its boot configuration, or its firmware.

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
- collect or publish full serial numbers, keys, certificates, tokens, or NAND dumps.

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
| Transmit LDN frames / host a plaintext LDN network | Medium; can hang or crash the `ldn` sysmodule or Wi-Fi firmware; active frame injection | Explicit approval for the specific run; follow `docs/LDN-TEST-PLAN.md` |

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
- Restore the Linux adapter to managed mode and restart NetworkManager.
- Hold the console's power button until it powers off, then boot normally.
- Do not factory-reset or initialize the console as a first response. A wireless hang is not a storage problem.
- Record the exact frame parameters, the host output, and the console's behavior. If the console produced a crash report or error code, preserve it and do not repeat the frame until the report is copied.

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
