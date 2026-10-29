# LDN Pre-Auth Test Plan (D9 / H-010)

> **Status: Phase 0, Phase 1, one Phase 2 plaintext run, three prod-mode runs, adapter TX diagnostics, and two supervised AP-mode reruns executed.** The adapter and passive capture were verified against the target. Phase 2 was approved once and executed, but it is **inconclusive**: the host started and stopped cleanly, yet no room appeared. A follow-up 60-second TX check was **invalid** because a wildcard Wi-Fi scan cannot see the null-SSID LDN beacon, and the directed CoreWLAN scan is also **invalid** because it returns false positives for non-existent 16-byte SSIDs. The first prod-mode host using the owner's local `prod.keys` emitted 373 AES-CTR advertisements that decrypted to the captured room, but the console still reported no rooms, the host logged no `JOIN`, and the same-phy captures saw no console frames. A second prod-mode run with the search triggered inside the advertisement window again logged no `JOIN` and no room; its pcap capture failed on a wrapper permission error. A third run with the fixed wrapper again produced no join and no room; an independent Location Services-enabled scan saw a hidden ambient BSSID but not the host BSSID. An AP-mode control proved the adapter can transmit at -32 dBm, and a follow-up AP-mode `NL80211_CMD_FRAME` test put a 20-frame test beacon on the air at -28 dBm in all 12 scans. A monitor-mode control showed that monitor-mode injection does not transmit. The current `rtw88_8822bu` monitor-mode host path is therefore **blocked**. The AP beacon half works, and a non-LDN unicast vendor action with a temporary station entry was accepted by the kernel; a broadcast LDN vendor action frame remains blocked by mac80211's station lookup. The next AP test is a real LDN vendor action through the unicast path, with new approval, or a different adapter/driver. A real LDN unicast run on 2026-10-29 sent 568 valid advertisements and 568 null-SSID beacons with the AP BSSID, all accepted by the kernel, but the console was off/away, so reception was not observed; that run is inconclusive. A supervised rerun then made the room `TX10LED` appear on the console, but selecting it produced `2203-0065` immediately, the search screen closed, and the console returned to the game normally. hostapd logged only `AP-ENABLED` and `AP-DISABLED`, with no authentication, association, or station event (`E-098`). The room appearance confirms that the AP-BSSID advertisement reaches the console's scan path; that join failed before hostapd saw an association because the hostapd test SSID was `TX10LED-TEST` with open security, not the room's 32-character hexadecimal WLAN SSID and LDN RSN IE. A second supervised run used the corrected WLAN parameters: the console authenticated, associated with AID 1, and was marked authorized, then disassociated with `reason_code=8` about one second later and sent no observed `0x88B7` request (`E-099`). The monitor saw a 28-byte null-data frame, not the authentication request; the AP raw socket saw a 20-byte ethertype `0x0006` frame. The association response included an RSN IE that the `ldn` `MonitorAP` does not send, so the next test omits it, captures raw frames and a local pcap on `mon-ldn`, and uses the authorized-station raw `0x88B7` response path (`E-100`). The driver rejects a broadcast-BSSID action frame with `EINVAL`, so the AP path can only send the AP-BSSID variant. The key file does not cover the 23.0.1 NCA key generation, so the `ldn` sysmodule content has not been decrypted. Another active run requires new explicit owner approval. Nothing in this document authorizes game sharing, host spoofing, key publication, or console modification.

## What this tests

This is a narrow question about the console's **local-wireless (LDN) parser**, not about Virtual Game Cards and not about GameShare.

- **Virtual Game Cards** are gated by a Nintendo Account, an internet connection, local-wireless proximity, and a server-issued license. A PC cannot act as a linked console; emulating a Switch 2 does not change that.
- **GameShare / `splay`** requires a real Switch 2 host. The host's `AdvertiseData` is ECC-verified, the protocol is not publicly specified, and a PC cannot produce a valid signed host advertisement. A PC can receive LDN frames, but it cannot be a valid GameShare host.
- **LDN pre-auth** is the remaining surface that a PC can reach without a second console and without Nintendo's signing keys. The protocol is documented, the frames are observable, and the parser runs before a station is authenticated.

The known public LDN bug, `CVE-2026-82079`, is a stack overflow fixed in **23.0.0**. The target is on **23.0.1**, so that specific bug is not available. This test is looking for a *different* parser defect. No such defect is known or claimed.

## The key gate

Retail LDN uses security mode 1: advertisement and data frames are AES-encrypted. The key derivation needs `aes_kek_generation_source`, `aes_key_generation_source`, and a master key from `prod.keys`.

**Status (2026-10-28):** the owner supplied `Firmware/prod.keys.txt` and a `Firmware/Firmware.23.0.1` dump from their **own modded Switch**. Both are local-only and excluded from version control. Using `KeyDerivation(protocol=1)` and the Phase 1 pcap, the advertisement decrypted and its SHA-256 validated: **security mode 1 (prod)**, challenge present, channel 1, 2.4 GHz, max 2 participants, app version 26. The keys therefore match the target firmware's **LDN key derivation**. They do not cover the 23.0.1 NCA key generation: the key file stops at generation `0x14`, while the `ldn` NCA uses `0x17`, so the sysmodule content has not been decrypted (`E-083`). The `ldn` **meta** NCA is readable, however; its CNMT reports title version `0x5c0004b0` and a program-NCA SHA-256 that matches the local file. This project still does not download keys, and the keys must never be committed, published, or shared.

Two active paths are now available:

1. **PC hosts, Switch joins, prod mode (preferred).** The host uses security mode 1 with the owner's keys and the captured title/scene parameters. This is the closest reproduction of a real room. It still needs a working TX path and explicit approval.
2. **PC hosts, Switch joins, plaintext mode 3 (no-key control).** The `kinnay/LDN` package supports security mode 3, and `create_network` does not derive a WLAN data key in that mode. Retail consoles may reject this development-only mode. The one approved run is inconclusive because TX is unconfirmed.

A third active path, **Switch hosts and PC joins**, is supported by the library but needs the same keys *and* the same TX path. It validates the key exchange but does not exercise the station-side parser that the host direction reaches.

The central falsifiable questions are:

> Does the retail 23.0.1 console accept a PC-hosted prod-mode LDN network built from its own advertised parameters?

> If not, does it accept the plaintext security-mode-3 network?

A `JOIN` on either path means the station-side authentication parser is reachable. A clean rejection with confirmed transmission closes that path. Neither result is a vulnerability.

## Hardware and host requirements

- A Linux host. On macOS, the validated path is an **OrbStack Ubuntu 26.04 arm64 VM** with USB passthrough. Native macOS cannot inject 802.11 frames. A separate CachyOS/Arch PC also works.
- A Wi-Fi adapter that can receive **and transmit** action frames in monitor mode. The **TP-Link Archer T3U Plus** (`2357:0138`, `rtw88_8822bu`) is validated for passive capture, but its transmit path is not yet confirmed; `dmesg` reports `failed to get tx report from firmware`. The `kinnay/LDN` README reports MediaTek and Realtek drivers as the most reliable; `mt7921e` is confirmed. Treat the Archer as a capture adapter until a transmission diagnostic succeeds.
- Python 3.12 or later.
- `CAP_NET_ADMIN` and `CAP_NET_RAW` (run as root).
- NetworkManager stopped while the dedicated adapter is in monitor mode. The OrbStack VM does not run NetworkManager, so this only applies to a full Linux host.
- A wired connection or a second adapter if the host needs internet access during the test. The OrbStack VM keeps its virtual Ethernet connection while the USB adapter is in monitor mode.

The adapter must not be the only network path if you need to download packages. Install dependencies first, then stop NetworkManager.

### Validated passive-capture path on macOS

The 2026-10-28 run used:

```text
macOS 26.3 (arm64)
  └── OrbStack 2.2.5
      └── Ubuntu 26.04.1 LTS, kernel 7.2.12-orbstack
          └── TP-Link Archer T3U Plus, 2357:0138
              driver: rtw88_8822bu, firmware 30.20.0
```

Attach the adapter to the VM:

```bash
orb usb list
orb usb attach <id> -m ldn
```

Then verify it inside the VM:

```bash
orb -m ldn bash -lc 'lsusb; iw dev; ethtool -i <interface>'
```

The adapter may re-enumerate once after firmware load. If it disappears, run `orb usb list` again and attach the new ID.

## Phase 0 — verify the adapter

On the Linux host or VM, with the adapter attached:

```bash
ip -br link
for i in /sys/class/net/*; do
  name=$(basename "$i")
  [ -e "$i/phy80211" ] || continue
  echo "== $name =="
  ethtool -i "$name" | grep -E 'driver|version|firmware'
done
iw list | sed -n '/Supported interface modes/,/Band 1/p'
python3 --version
```

Record the interface name, driver, and whether `monitor` appears under supported interface modes. A driver that cannot transmit action frames, or drops them after association, will not work.

Install the user-space tools and the LDN package on Ubuntu/OrbStack:

```bash
sudo apt-get update
sudo apt-get install -y iw tcpdump ethtool usbutils python3 python3-venv python3-pip linux-firmware
python3 -m venv ~/ldn-venv
~/ldn-venv/bin/pip install ldn
```

On Arch/CachyOS, the equivalent package step is:

```bash
sudo pacman -S --needed python python-pip iw tcpdump ethtool linux-firmware
```

The `rtw88_8822bu` driver needs `rtw88/rtw8822b_fw.bin`. On Ubuntu 26.04 the firmware package installs it compressed as `.zst`; the kernel used in this run loaded it successfully. If the driver reports a missing firmware file, decompress it:

```bash
sudo apt-get install -y zstd
sudo zstd -d -f /lib/firmware/rtw88/rtw8822b_fw.bin.zst -o /lib/firmware/rtw88/rtw8822b_fw.bin
```

Do not run the host yet. Phase 0 is read-only host configuration.

## Phase 1 — passive capture (safe)

### Console state

Open a local-wireless screen and **host** a room. The exact route depends on what is installed:

- a game with local wireless: for example, Mario Kart 8 Deluxe → Local Wireless → Create Room;
- the Virtual Game Cards link flow, if it offers a host/link screen;
- another title with a local-wireless lobby.

The console must be actively advertising an LDN network. A game's local-wireless lobby is the most reliable trigger because it does not require a Nintendo Account. The LDN challenge is enabled for games, but Phase 1 does not authenticate; it only captures the advertisement header.

### Capture

Put the adapter in monitor mode. Replace `wlan0` with the interface from Phase 0:

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
```

Capture on one channel first (1, 6, or 11 for 2.4 GHz; 36, 40, 44, or 48 for 5 GHz):

```bash
sudo iw dev wlan0 set channel 6
sudo tcpdump -i wlan0 -y IEEE802_11_RADIO -w ldn-ch6.pcap
```

If nothing appears, capture across the three 2.4 GHz channels with a hop loop in a second terminal:

```bash
while true; do
  for ch in 1 6 11; do
    sudo iw dev wlan0 set channel "$ch"
    sleep 0.2
  done
done
```

Let the capture run for 10–20 seconds while the console is on the hosting screen, then stop `tcpdump` with Ctrl-C and stop the hop loop.

The 2026-10-28 run used a 15-round hop over channels 1, 6, and 11 with 0.5 s dwell per channel. It captured 269 frames, including 64 LDN advertisements. Most advertisements were on channel 1.

Restore the adapter:

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type managed
sudo ip link set wlan0 up
sudo systemctl start NetworkManager 2>/dev/null || true
```

### Analyse

Run the parser on the VM, or copy the pcap to macOS first:

```bash
~/ldn-venv/bin/python scripts/ldn_probe.py --pcap ldn-ch6.pcap
~/ldn-venv/bin/python scripts/ldn_probe.py --pcap ldn-ch6.pcap --json --redact
```

The parser prints the plaintext `NetworkId` header:

- `title_id` — the local communication ID (usually the title ID);
- `scene_id` — the game mode;
- `ssid` — the 16-byte network identifier;
- `ldn_version`, `format` (`plain`, `aes-ctr`, or `aes-gcm`), `size`, `nonce`;
- the source MAC and the ciphertext length.

A passive capture does not use keys, does not transmit, and does not touch the console. Keep the pcap and the unredacted JSON local; they contain MAC addresses. Record only the sanitized header fields in the research record.

### Phase 1 outcomes

| Observation | Meaning | Next |
|---|---|---|
| Advertisement frames with `format: aes-ctr` | The console is hosting a retail LDN network. The header is readable. | Phase 2 |
| Advertisement frames with `format: aes-gcm` | The console is using the newer LDN protocol (Switch 2 style). The header is still readable. | Phase 2, but expect protocol differences |
| No frames | Wrong channel, adapter not in monitor mode, driver dropping action frames, or console not hosting. | Recheck Phase 0 and the console screen; do not transmit yet |
| Frames from other devices only | The console is not the host, or it is scanning. | Use a hosting screen or have the console create a room |

**Observed on 2026-10-28:** the target hosted a Dragon Ball FighterZ local-wireless room. The capture contained 64 advertisement frames for one network: title `0100a250097f0000`, scene `0`, LDN version `4`, format `aes-ctr`, size `1280`, nonce `39030b16`, and a valid 1312-byte ciphertext after removing the 4-byte FCS. The dominant channel was 1. The sanitized record is [`research/hardware-observations/2026-10-28-ldn-phase1.json`](../research/hardware-observations/2026-10-28-ldn-phase1.json). The pcap and unredacted JSON are local-only.

## Phase 2 — plaintext host (active, approval required)

**This phase transmits LDN frames. Do not run it until the owner has explicitly approved this specific test.**

### Console state

Put the console in the **join/scan** role, not the hosting role. For a game, open Local Wireless → Join Room and leave it scanning. For the Virtual Game Cards flow, use the screen that searches for the other console. The console must be actively looking for a network.

A free-to-start game with local wireless is sufficient. **Super Kirby Clash** supports local wireless Party Quest and is free to download. A free game does not change the LDN security mode: the `ldn` sysmodule handles the network, and the game's scan UI may filter or display the result. Use a free game as a second scan target, not as a way around the mode-3 gate.

### Host

Use the `title_id`, `scene_id`, `ssid`, and `channel` from the Phase 1 capture. The values in the commands below are placeholders; replace them with the captured header fields. Stop NetworkManager if it is running, so it does not fight the monitor interface:

```bash
sudo systemctl stop NetworkManager 2>/dev/null || true

# Build the frame without touching the radio.
sudo -E ~/ldn-venv/bin/python scripts/ldn_host.py \
  --title-id 0100000000001000 \
  --scene-id 1 \
  --ssid 00112233445566778899aabbccddeeff \
  --channel 6 \
  --ifname ldn \
  --phyname phy1 \
  --name TX10LED \
  --dry-run
```

Check the dry-run output: security mode 3, challenge disabled, a valid frame length. Then transmit:

```bash
sudo -E ~/ldn-venv/bin/python scripts/ldn_host.py \
  --title-id 0100000000001000 \
  --scene-id 1 \
  --ssid 00112233445566778899aabbccddeeff \
  --channel 6 \
  --ifname ldn \
  --phyname phy1 \
  --name TX10LED \
  --duration 30 \
  --host --confirm \
  --compat-no-active-ack
```

`--ifname` is the **new** monitor interface that the LDN package creates; it must not already exist. `--phyname` is the existing PHY from `iw dev`. In the OrbStack VM the PHY was `phy1`; do not assume `phy0`.

`--compat-no-active-ack` is required for the `rtw88_8822bu` driver. The stock package creates a second monitor interface with `NL80211_MNTR_FLAG_ACTIVE`, which this driver rejects with `EOPNOTSUPP`. The flag creates the same interface without the active flag. The second interface is not referenced by the package's `MonitorAP`; the host uses the first monitor for send and receive.

For the 2026-10-28 capture, the title ID is `0100a250097f0000`, the scene ID is `0`, and the dominant channel is `1`. Read the SSID from the local unredacted JSON; do not commit it.

The script hosts a plaintext LDN network and sends no application data. It prints `JOIN` if the console authenticates and registers, `LEAVE` if it disconnects, and `DISCONNECT` if the host tears the network down.

Restore the host afterward:

```bash
sudo systemctl start NetworkManager 2>/dev/null || true
```

### Phase 2 result (2026-10-28)

The owner approved one active run. The first attempt failed before transmission because the package creates a second monitor interface with `NL80211_MNTR_FLAG_ACTIVE`, which `rtw88_8822bu` rejects with `EOPNOTSUPP`. The `--compat-no-active-ack` path creates the same interface without the flag.

A 2-second diagnostic and a 30-second run both started, advertised, and stopped cleanly. The console was on the Dragon Ball FighterZ Local Wireless join/search screen. The console showed no room, the host log contained no `JOIN` and no authentication request, and the host reported no error. `dmesg` reported `failed to get tx report from firmware` after each run. The in-kernel `rtw88_8822bu` driver is reported to fail beacon transmission in AP mode with this firmware error, so the host's frames may not have been on air.

**The run is inconclusive, not a clean rejection of security mode 3.** Before another join attempt, confirm the host's frames are on air. A **wildcard** Wi-Fi scan for the LDN SSID is **not** a valid check: the LDN host beacon uses a 32-byte null SSID (`SSIDElement("\x00" * 32)`), and the real network ID is carried in vendor action frames, which a scan does not report. Use a monitor-mode capture on the host's `ldn` interface with `tcpdump`, a second monitor-mode adapter/PC, or a phone Wi-Fi analyzer that shows hidden BSSIDs. The macOS wildcard BSSID comparison is valid only with Location Services permission: without it, macOS returns nil BSSIDs (`E-088`); with it, a local scanner returned real BSSIDs (`E-092`). The later monitor-mode control showed that the current `ldn` host path does not transmit (`E-091`), so this no-key result cannot be interpreted as a console rejection. If a working host path is confirmed on air and the console still shows no room, the no-key mode-3 path is closed. AP-mode `NL80211_CMD_FRAME` beacon injection works (`E-094`), but a broadcast vendor action needs a station entry (`E-093`). A non-LDN unicast control with a temporary station entry was accepted by the kernel (`E-095`); test a real LDN unicast vendor action or use a known-good adapter (`mt7921e` is confirmed by the `kinnay/LDN` README).

Do not run another active host without new explicit approval.

### Phase 2 prod-mode result (2026-10-28/29)

The host was extended to security mode 1 (`--room-file`, `--keys-file`, `--security-mode`, `--challenge`, `--application-data`). The dry run produced an AES-CTR frame of 1,364 bytes with a 1,280-byte payload and an 11-field round-trip decode.

The owner approved one 30-second run on channel 1 with the captured title/scene/SSID/channel and the local keys. The host advertised 373 vendor action frames and 660 beacons on the existing monitor interface; the `ldn` interface saw 655 action frames and 1,222 beacons. The first captured action frame decrypted with `KeyDerivation(protocol=1)` and validated its SHA-256. Its fields matched the Phase 1 room: title `0100a250097f0000`, scene `0`, LDN version `4`, security mode `1`, challenge present, max `2`, app version `26`, 4 bytes of application data, and the same SSID.

The host log ended with `Host stopped. Join events observed: 0.` The owner reports that Dragon Ball FighterZ searches for about one second and then says it did not find any rooms. Neither capture contains a frame from the console. `dmesg` logged one more `failed to get tx report from firmware` (count 3 to 4).

**This is still inconclusive about RF transmission.** The captures were made on the host adapter's own phy and may include loopback. The directed CoreWLAN scan used during the run is invalid (see below). At the time, the next independent check was a second monitor-mode receiver, a phone Wi-Fi analyzer that shows hidden BSSIDs, or the CachyOS PC/`mt7921e` path; the run-3 and AP/monitor sections below later showed that the monitor-mode host path itself does not transmit. Sanitized record: [`research/hardware-observations/2026-10-29-ldn-prod-host.json`](../research/hardware-observations/2026-10-29-ldn-prod-host.json).

### Phase 2 prod-mode repeat (2026-10-28/29)

The owner approved one repeat 30-second run. The console search was triggered **after** the host was already advertising, so the roughly one-second search overlapped the advertisement window. The host again logged `Advertising now` and `Join events observed: 0`. The console again reported no rooms. `dmesg` TX-report failures increased from 4 to 5.

**The run has no valid capture.** The wrapper tried to delete the previous run's pcaps as the unprivileged user; the files were owned by `tcpdump`, so the cleanup failed, and the new `tcpdump` processes exited with `Permission denied`. The wrapper's summary and probe output are from run 1. There is no run-2 frame count, console-frame check, or fresh frame decryption.

**The wildcard BSSID scan was invalid without Location Services.** Ten scans during the run each reported `BSSID not found in 8 scan result(s)`. A post-run control scan returned 10 ambient networks, and `CWNetwork.bssid` was `nil` for every one. macOS 26.3 redacts BSSIDs from unpermitted processes, so the comparison could not distinguish the host from any other network (`E-088`). Granting Location Services to a local scanner later restored real BSSIDs (`E-092`).

The repeat run is therefore inconclusive and identifies two tooling defects, not a console rejection. Sanitized record: [`research/hardware-observations/2026-10-29-ldn-prod-host-run2.json`](../research/hardware-observations/2026-10-29-ldn-prod-host-run2.json).

### Phase 2 prod-mode run 3 and independent scan (2026-10-29)

The wrapper was fixed to use a unique run ID and to remove old tcpdump-owned pcaps with `sudo rm -f`. The owner approved one more 30-second run, with the console search triggered inside the advertisement window and a Location Services-enabled independent scan from the Mac.

The host again logged `Advertising now` and `Host stopped. Join events observed: 0.` The console again reported no rooms. `dmesg` TX-report failures rose from 5 to 6. The wrapper captured 777 packets on the existing monitor interface and 1,373 on the `ldn` interface; the probe found 373 and 656 AES-CTR advertisements for title `0100a250097f0000`, scene `0`.

The Mac ran 20 wildcard CoreWLAN scans with authorization status 3. The host adapter BSSID was absent from all 20, but a hidden ambient BSSID on channel 1 was present in several scans. The captures contained only the host's own frames and no ambient AP beacons. Every injected frame appeared as a pair: one copy with an 8-byte radiotap header and no fields, and one with a 13-byte header, rate 2 (1.0 Mb/s), and `txflags=0x0`.

**The run still does not prove RF transmission.** The independent scan is not a frame capture, and the LDN beacon's 32-byte null SSID may be filtered differently from a normal hidden SSID. Sanitized record: [`research/hardware-observations/2026-10-29-ldn-prod-host-run3.json`](../research/hardware-observations/2026-10-29-ldn-prod-host-run3.json).

### Adapter TX diagnostics (2026-10-29)

Three controls isolated the adapter's transmit path.

**AP mode works.** `hostapd` 2.11 was started on channel 1 with an open test SSID, `TX10LED-TEST`, in `hw_mode=g`. The Mac saw the SSID at -32 dBm with the adapter's BSSID, and the hostapd log reached `AP-ENABLED`. The adapter was restored to monitor mode on channel 1 afterward. Sanitized record: [`research/hardware-observations/2026-10-29-ap-mode-tx.json`](../research/hardware-observations/2026-10-29-ap-mode-tx.json).

**Monitor mode does not transmit.** `Firmware/monitor_beacon_test.py` used the `ldn` package's `MonitorAP` to create two monitor interfaces on the same phy and beacon `TX10LED-MON` on channel 1 for 12 seconds. The script logged `beaconing as <redacted>` and `done`, and the interfaces existed on channel 1. Two CoreWLAN scans during the window did not see the test SSID or the adapter BSSID, while ambient networks on channels 1, 6, 11, and 100 were visible. The same adapter, driver, channel, and Mac had just received the AP-mode beacon at -32 dBm. Sanitized record: [`research/hardware-observations/2026-10-29-monitor-mode-tx.json`](../research/hardware-observations/2026-10-29-monitor-mode-tx.json).

**AP-mode management-frame injection works for beacons.** `Firmware/ap_inject_run.sh` started hostapd 2.11 with `TX10LED-TEST` on channel 1 and waited for `AP-ENABLED`. `Firmware/ap_frame_test.py` then submitted 20 beacon frames with SSID `TX10LED-APINJ` through `NL80211_CMD_FRAME` at 100 ms intervals; every request returned without a netlink error. Twelve Location Services-enabled CoreWLAN scans during the window all saw both `TX10LED-APINJ` and `TX10LED-TEST` at -28 dBm on channel 1 with the adapter BSSID, while ambient networks remained visible. The adapter was restored to monitor mode on channel 1. This proves that the AP-mode beacon half of management-frame injection reaches the air (`E-094`). Sanitized record: [`research/hardware-observations/2026-10-29-ap-mode-frame-injection.json`](../research/hardware-observations/2026-10-29-ap-mode-frame-injection.json).

**The vendor-action half has a source-level limit.** A review of upstream mac80211 and nl80211 found that `NL80211_CMD_FRAME` can send an AP beacon through the normal TX path, but a non-public action frame on an AP interface requires a station entry. `NL80211_ATTR_FRAME_NO_STA` sets `params.no_sta`, yet the upstream code still returns `-ENOLINK` for a non-public action frame with no station, and a broadcast destination is not a station (`E-093`). The LDN advertisement is a vendor action frame (category `0x7f`, OUI `00:22:aa`, type `0x04`), so a broadcast LDN action frame cannot be sent from an AP interface through this path. The remaining AP options are a **unicast** vendor action to a station entry for the console's known MAC, or a different adapter/driver.

**Unicast vendor action works at the kernel level.** The owner approved a bounded follow-up. `Firmware/ap_unicast_run.sh` started hostapd 2.11 with `TX10LED-TEST` on channel 1 and waited for `AP-ENABLED`. `Firmware/ap_unicast_test.py` then added a temporary station entry for the console's MAC, which was recovered locally from the Phase 1 pcap, and submitted five unicast vendor action frames with the non-LDN test OUI `00:11:22` and payload `TX10LED-UNICAST` through `NL80211_CMD_FRAME`. The station entry was added, all five requests returned without a netlink error, and the station entry was removed. The adapter was restored to monitor mode on channel 1 (`E-095`). This confirms the kernel-level station-lookup half of the AP path. It does **not** show that the console received the frame or that its LDN parser reacted: the test used a non-LDN OUI, no independent capture was made, and the console was not instrumented. `dmesg` again reported `failed to get tx report from firmware`. Sanitized record: [`research/hardware-observations/2026-10-29-ap-mode-unicast-vendor.json`](../research/hardware-observations/2026-10-29-ap-mode-unicast-vendor.json).

**The real LDN unicast run is inconclusive because the console was absent.** The owner approved a 60-second run of `Firmware/ap_ldn_run.sh`, which started hostapd 2.11 with `TX10LED-TEST` on channel 1 and waited for `AP-ENABLED`. The first attempt sent 0 advertisements because `rtw88_8822bu` rejected the broadcast-BSSID action frame with `EINVAL`. `Firmware/ap_action_variants.py` isolated the rejection: the 1,388-byte LDN advertisement and a 42-byte control both failed with a broadcast BSSID and succeeded with the AP BSSID; all beacon variants, including the 89-byte null-SSID LDN beacon, were accepted (`E-097`). The rerun used `--variant ap`, and `Firmware/ap_ldn_unicast_test.py` submitted 568 valid AES-CTR advertisements plus 568 null-SSID beacons at 100 ms intervals. All 568 requests returned without a netlink error, the station entry was removed, and hostapd reached `AP-DISABLED` (`E-096`). The console was off/away during the window, so no room appearance or parser reaction was observed. The run is **inconclusive for the LDN hypothesis**, not a negative result. `dmesg` reported `failed to get tx report from firmware` and, after hostapd stopped, a firmware download failure; the adapter could not be brought up until a USB deauthorize/reauthorize cycle, after which monitor mode and RX worked again. Sanitized record: [`research/hardware-observations/2026-10-29-ap-mode-ldn-unicast.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-unicast.json).

**The supervised rerun reached the scan path but not the join path.** The owner ran `Firmware/ap_ldn_run.sh 60` with the console on the Dragon Ball FighterZ local-wireless search screen. The console displayed the room `TX10LED`; selecting it produced `2203-0065` immediately, the search screen closed, and the console returned to the game normally. The hostapd log contains only `AP-ENABLED` and `AP-DISABLED`, with no `IEEE 802.11: authenticated`, `AP-STA-CONNECTED`, or other station event. The exact advertisement count from this run was not preserved in the sanitized record. Sanitized record: [`research/hardware-observations/2026-10-29-ap-mode-ldn-unicast-observed.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-unicast-observed.json).

**The corrected rerun reached authentication and association, but the console left before the LDN exchange.** The owner ran `Firmware/ap_ldn_join_run.sh 90` with the room's 32-character hexadecimal WLAN SSID and the LDN RSN IE. hostapd logged open-system authentication, association with AID 1, `AP-STA-CONNECTED`, and `authorized=1`. About one second later it logged a disassociation from the console with `reason_code=8`, then `AP-STA-DISCONNECTED` and deauthentication due to inactivity. The harness sent 54 advertisements, received 0 `0x88B7` authentication frames, and ended with `joined=False`. The `mon-ldn` monitor saw one 28-byte console data frame (`flags=16`, FCS included), consistent with a 24-byte null-data header and no payload; it is not the 946-byte authentication request. The AP raw socket saw a 20-byte frame with ethertype `0x0006`; its payload was not preserved. The owner saw `2203-0066` after a few seconds and the game popup `unable to join the room`; the console returned to the game normally. Sanitized record: [`research/hardware-observations/2026-10-29-ap-mode-ldn-join-observed.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-join-observed.json).

The WLAN layer succeeded: authentication, association, and authorization all completed. The failure is after association and before the custom LDN authentication exchange. The association response included an RSN IE that the `ldn` package's `MonitorAP` does not send; that mismatch is the leading candidate for the console's disassociation, but it is not proven. A local control showed that `NL80211_CMD_CONTROL_PORT_FRAME` rejects `0x88B7` with `EINVAL`, while an AF_PACKET raw `0x88B7` frame is transmitted as a protected CCMP data frame with KeyID 0 when the station is authorized and the pairwise key is installed (`E-100`). The harness now logs the 802.11 subtype and redacted payload hex, and can write a local pcap on `mon-ldn`. The next test must:

1. Start hostapd with `ssid=<the room's 32-character hexadecimal SSID>`, `ignore_broadcast_ssid=2`, the LDN RSN IE in the beacon/probe response, and **no `assocresp_elements`**, matching the `ldn` `MonitorAP` association response.
2. Accept open-system authentication and association, then install the pairwise CCMP key derived from the same `server_random` used in the advertisement plus the game's LDN passphrase. The passphrase is empty for Dragon Ball FighterZ unless independently verified.
3. Receive the console's `0x88B7` authentication request, verify the challenge token, and send the LDN authentication response with the derived challenge key through the raw authorized-station path.
4. Capture raw frames and a local pcap on `mon-ldn` so the 28-byte null-data frame and the 20-byte ethertype `0x0006` frame can be identified.
5. Record whether the console reaches the `0x88B7` exchange and whether omitting the association-response RSN IE changes the disassociation.

The exact hostapd/RSN mechanics still need a local prototype: `own_ie_override` is used only when the WPA state machine is enabled, and `wpa=0` does not set the privacy bit. A `wep_key0` plus `vendor_elements` configuration can set the privacy bit and append the RSN IE, but the WEP keys must be replaced with the CCMP pairwise key before the console's data frame arrives. A minimal nl80211 AP or a patched hostapd may be cleaner. This is a host implementation problem, not evidence of a console vulnerability.

**Conclusion.** The adapter and `rtw88_8822bu` can transmit in AP mode, and AP-mode `NL80211_CMD_FRAME` puts a test beacon on the air. A unicast vendor action with a temporary station entry is accepted by the kernel, and the real LDN unicast run sent 568 valid advertisements plus 568 null-SSID beacons with the AP BSSID, but monitor-mode injection does not transmit. The current LDN host uses monitor mode, so the no-room results from the plaintext and prod-mode runs are explained by the host path, not by a console rejection. The supervised rerun proved the AP-BSSID advertisement reaches the console; the corrected second run proved the console will authenticate and associate with the room's WLAN SSID and RSN IE, but it left with reason 8 before the `0x88B7` exchange. The next step is the **association-response RSN IE omission, raw-frame diagnostics, and the raw authorized-station `0x88B7` responder**, or a different adapter/driver with working monitor-mode TX. The broadcast-BSSID limit (`E-097`) remains, but the room appearance shows it does not block the scan path. A corrected active run needs new explicit approval.

### 60-second TX check (2026-10-28, invalid)

The owner approved one 60-second diagnostic. The host advertised on channel 1, and three CoreWLAN scans from the Mac's built-in Wi-Fi looked for the 32-character SSID. The SSID did not appear. `dmesg` logged a third `failed to get tx report from firmware` message.

**This check is invalid as a transmission test.** The LDN beacon's SSID is 32 null bytes, and the network ID is in vendor action frames. A wildcard Wi-Fi scan cannot see either. The result neither confirms nor denies that the host transmitted.

A **directed scan for the known SSID** was proposed as a one-sided check, but the control test showed it is **invalid**: `scanForNetworks(withSSID:)` returned `FOUND` for a random non-existent 16-byte SSID, with a nil BSSID and an inconsistent channel. Do not use it as a TX check (`E-086`).

A **wildcard BSSID comparison** was proposed and is valid only with Location Services permission: without it, a post-run control scan returned 10 ambient networks with a nil `CWNetwork.bssid` for every one (`E-088`); after the owner allowed Location Services for a local scanner, a wildcard scan returned 12 networks with real BSSIDs (`E-092`). The run-3 independent scan used that permission and did not see the host BSSID, although it saw a hidden ambient BSSID. The AP/monitor controls then showed that monitor-mode injection does not transmit (`E-090`, `E-091`), so the absence is explained by the host path. A matching BSSID or a captured LDN action frame confirms RF transmission; an absent result from a receiver that can see other BSSIDs is still inconclusive without a frame capture.

### Phase 2 outcomes

| Observation | Meaning | Next |
|---|---|---|
| `JOIN` | The retail console accepted a plaintext, no-challenge LDN network. The station-side authentication parser is reachable without keys. | Phase 3, with separate approval |
| No join, but the host path does not transmit | The monitor-mode injection path is broken; the result cannot distinguish a console rejection from a missing host. | AP-mode beacon injection works (`E-094`), but a broadcast vendor action needs a station entry (`E-093`). A non-LDN unicast control was accepted by the kernel (`E-095`), and the real LDN unicast run sent 568 advertisements with the AP BSSID (`E-096`); the console was off/away, so the run is inconclusive. Rerun with the console in the search screen with new approval, or use a different adapter/driver. Directed scans are invalid (`E-086`); a wildcard BSSID scan requires Location Services (`E-092`). |
| Real LDN unicast sent, console off/away | The host path accepted 568 valid advertisements, but no receiver observed the console. | Rerun with the console in the search screen and record whether the room appears; the AP-BSSID variant may be ignored (`E-097`). |
| Room appears, then `2203-0065` immediately on selection; hostapd logs no auth/assoc | The console accepted the advertisement at the scan layer but could not join the AP. The hostapd WLAN SSID/security did not match the room's 32-character hexadecimal SSID and LDN RSN IE. | Correct the hostapd WLAN configuration and add the `0x88B7` authentication responder; do not treat the error as a parser fault (`E-098`). |
| No join after transmission is confirmed, console stays on the scan screen | The console rejected security mode 3 or the network parameters. | Retry once with prod mode and the owner's keys; if that also fails, the PC-host path is closed |
| Console shows an LDN/network error | The console parsed the advertisement but refused the network. Record the code and whether the console stays responsive. | Do not repeat blindly; analyse the code |
| Console hangs or reboots | A fault occurred before or during authentication. This is a lead, not an exploit. | Stop, record the exact frame and console behavior, power-cycle |

A `JOIN` is a transport result, not a vulnerability. It means we can now ask the console's station-side parser to process controlled authentication responses.

## Phase 3 — malformed authentication responses (not yet built)

Only after Phase 2 produces a `JOIN`, and only with a separate approval:

1. Capture the normal authentication exchange with `tcpdump` so the request/response sequence is known.
2. Build a custom responder that sends one malformed response at a time: wrong version, wrong status, mismatched size fields, truncated payload, oversized payload, wrong challenge length, wrong network ID, wrong server/client random.
3. After each frame, record whether the console disconnects, retries, shows an error, reboots, or produces a crash report.
4. Stop on the first unexpected result. Do not batch malformed frames.

This phase requires a custom harness; the stock `kinnay/LDN` host always sends a well-formed response. The first version of the harness should log the response bytes and have a dry-run mode. It is not part of Phase 1 or 2.

## Safety and recovery

- The host transmits only LDN management/authentication frames. It does not write storage, install anything, or send application data.
- A malformed frame can hang or crash the `ldn` sysmodule or the Wi-Fi firmware. Recovery is to stop the host, restore the adapter, and hold the console's power button until it powers off; then boot normally.
- Do not factory-reset the console as a first response. A wireless hang is not a storage problem.
- Do not run the host while the console is on a screen that writes data or updates firmware.
- Do not use this harness to play or share a game, to bypass the ticket challenge, or to impersonate a GameShare or Virtual Game Card host.
- Do not download `prod.keys`. The only keys this project may use are the owner's local dump from their own console. Do not commit, publish, share, or paste them, and do not use them against anyone else's console.

## Kill criteria

Close D9 as **blocked on tooling/adapter** if:

- the adapter/driver cannot capture or transmit LDN action frames in any usable mode (AP-mode management-frame injection, working monitor-mode TX, or a different adapter/driver) and no known-good adapter or second host is available; or
- the firmware dump cannot be parsed with the available tools, so the static parser comparison cannot proceed.

A no-room result with unconfirmed transmission is **inconclusive**, not a kill.

Close D9 as **negative** if:

- after host transmission is independently confirmed, the console rejects the prod-mode room **and** every plaintext/no-key variant is ignored; or
- Phase 2 succeeds, but every malformed authentication response is rejected cleanly, the console stays responsive, and no crash report appears.

A single reproducible crash/reboot tied to one malformed frame is a **lead**, not a confirmed exploit. It would need a second reproduction, a minimized frame, and an analysis of which parser handled it before any capability claim.

## Related records

- [`docs/RESEARCH-PLAN.md`](RESEARCH-PLAN.md) — D9 and the ranked directions.
- [`research/hypotheses.json`](../research/hypotheses.json) — H-010.
- [`research/entry-points.json`](../research/entry-points.json) — EP-005 local wireless.
- [`research/evidence-ledger.json`](../research/evidence-ledger.json) — E-023, E-035, E-078, E-080, E-081, E-082, E-084, E-085, E-086, E-087, E-088, E-089, E-090, E-091, E-092, E-093, E-094, E-095, E-096, E-097, E-098.
- [`research/hardware-observations/2026-10-28-ldn-phase1.json`](../research/hardware-observations/2026-10-28-ldn-phase1.json) — passive capture.
- [`research/hardware-observations/2026-10-28-ldn-phase2.json`](../research/hardware-observations/2026-10-28-ldn-phase2.json) — plaintext host and invalid TX check.
- [`research/hardware-observations/2026-10-29-ldn-prod-host.json`](../research/hardware-observations/2026-10-29-ldn-prod-host.json) — first prod-mode host run, frame validation, and invalid directed scan.
- [`research/hardware-observations/2026-10-29-ldn-prod-host-run2.json`](../research/hardware-observations/2026-10-29-ldn-prod-host-run2.json) — repeat run, capture failure, and invalid wildcard BSSID scan.
- [`research/hardware-observations/2026-10-29-ldn-prod-host-run3.json`](../research/hardware-observations/2026-10-29-ldn-prod-host-run3.json) — fixed-wrapper run, independent scan, and radiotap analysis.
- [`research/hardware-observations/2026-10-29-ap-mode-tx.json`](../research/hardware-observations/2026-10-29-ap-mode-tx.json) — AP-mode transmit control.
- [`research/hardware-observations/2026-10-29-monitor-mode-tx.json`](../research/hardware-observations/2026-10-29-monitor-mode-tx.json) — monitor-mode transmit control.
- [`research/hardware-observations/2026-10-29-ap-mode-frame-injection.json`](../research/hardware-observations/2026-10-29-ap-mode-frame-injection.json) — AP-mode `NL80211_CMD_FRAME` beacon injection control.
- [`research/hardware-observations/2026-10-29-ap-mode-unicast-vendor.json`](../research/hardware-observations/2026-10-29-ap-mode-unicast-vendor.json) — AP-mode unicast vendor-action control with a temporary station entry.
- [`research/hardware-observations/2026-10-29-ap-mode-ldn-unicast.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-unicast.json) — real LDN unicast run and broadcast-BSSID rejection.
- [`research/hardware-observations/2026-10-29-ap-mode-ldn-unicast-observed.json`](../research/hardware-observations/2026-10-29-ap-mode-ldn-unicast-observed.json) — supervised rerun: room appeared, immediate `2203-0065`, no hostapd auth/assoc event.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — authorization and recovery.
