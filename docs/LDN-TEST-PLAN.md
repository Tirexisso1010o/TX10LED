# LDN Pre-Auth Test Plan (D9 / H-010)

> **Status: planned, not executed.** Phase 1 is a passive capture. Phase 2 is an active frame-injection test and requires explicit owner approval. Nothing in this document authorizes game sharing, host spoofing, key use, or console modification.

## What this tests

This is a narrow question about the console's **local-wireless (LDN) parser**, not about Virtual Game Cards and not about GameShare.

- **Virtual Game Cards** are gated by a Nintendo Account, an internet connection, local-wireless proximity, and a server-issued license. A PC cannot act as a linked console; emulating a Switch 2 does not change that.
- **GameShare / `splay`** requires a real Switch 2 host. The host's `AdvertiseData` is ECC-verified, the protocol is not publicly specified, and a PC cannot produce a valid signed host advertisement. A PC can receive LDN frames, but it cannot be a valid GameShare host.
- **LDN pre-auth** is the remaining surface that a PC can reach without a second console and without Nintendo's signing keys. The protocol is documented, the frames are observable, and the parser runs before a station is authenticated.

The known public LDN bug, `CVE-2026-82079`, is a stack overflow fixed in **23.0.0**. The target is on **23.0.1**, so that specific bug is not available. This test is looking for a *different* parser defect. No such defect is known or claimed.

## The key gate

Retail LDN uses security mode 1: advertisement and data frames are AES-encrypted. The key derivation needs `aes_kek_generation_source`, `aes_key_generation_source`, and a master key from `prod.keys`. The owner does not have `prod.keys`, and this project does not download or use them.

There is one no-key path: **security mode 3** (system debug), where LDN frames are plaintext. The `kinnay/LDN` package supports it, and its `create_network` path does not derive a WLAN data key when `security_mode == SECURITY_MODE_SYSTEM_DEBUG`. Retail consoles may reject this development-only mode. That is the central falsifiable question:

> Does the retail 23.0.1 console accept a plaintext, no-challenge LDN network from a PC host?

If yes, the authentication parser is reachable without keys. If no, the no-key path is closed and retail LDN research needs a lawful `prod.keys` source.

## Hardware and host requirements

- A Linux host. The practical platform is CachyOS/Arch with `nl80211`.
- A Wi-Fi adapter that can receive **and transmit** action frames in monitor mode. The `kinnay/LDN` README reports MediaTek and Realtek drivers as the most reliable; `mt7921e` is confirmed.
- Python 3.12 or later.
- `CAP_NET_ADMIN` and `CAP_NET_RAW` (run as root).
- NetworkManager stopped while the dedicated adapter is in monitor mode.
- A wired connection or a second adapter if the host needs internet access during the test.

The adapter must not be the only network path if you need to download packages. Install dependencies first, then stop NetworkManager.

## Phase 0 — verify the adapter

On CachyOS, with the adapter plugged in:

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

Install the user-space tools and the LDN package:

```bash
sudo pacman -S --needed python python-pip iw tcpdump ethtool
python3 -m venv .venv
.venv/bin/pip install ldn
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

Restore the adapter:

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type managed
sudo ip link set wlan0 up
sudo systemctl start NetworkManager
```

### Analyse

Copy the pcap to the repository host (or run the parser on CachyOS) and run:

```bash
.venv/bin/python scripts/ldn_probe.py --pcap ldn-ch6.pcap
.venv/bin/python scripts/ldn_probe.py --pcap ldn-ch6.pcap --json --redact
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

## Phase 2 — plaintext host (active, approval required)

**This phase transmits LDN frames. Do not run it until the owner has explicitly approved this specific test.**

### Console state

Put the console in the **join/scan** role, not the hosting role. For a game, open Local Wireless → Join Room and leave it scanning. For the Virtual Game Cards flow, use the screen that searches for the other console. The console must be actively looking for a network.

### Host

Use the `title_id`, `scene_id`, `ssid`, and `channel` from the Phase 1 capture. The values in the commands below are placeholders; replace them with the captured header fields. Stop NetworkManager so it does not fight the monitor interface:

```bash
sudo systemctl stop NetworkManager

# Build the frame without touching the radio.
sudo -E .venv/bin/python scripts/ldn_host.py \
  --title-id 0100000000001000 \
  --scene-id 1 \
  --ssid 00112233445566778899aabbccddeeff \
  --channel 6 \
  --name TX10LED \
  --dry-run
```

Check the dry-run output: security mode 3, challenge disabled, a valid frame length. Then transmit:

```bash
sudo -E .venv/bin/python scripts/ldn_host.py \
  --title-id 0100000000001000 \
  --scene-id 1 \
  --ssid 00112233445566778899aabbccddeeff \
  --channel 6 \
  --name TX10LED \
  --duration 30 \
  --host --confirm
```

The script hosts a plaintext LDN network and sends no application data. It prints `JOIN` if the console authenticates and registers, `LEAVE` if it disconnects, and `DISCONNECT` if the host tears the network down.

Restore the host afterward:

```bash
sudo systemctl start NetworkManager
```

### Phase 2 outcomes

| Observation | Meaning | Next |
|---|---|---|
| `JOIN` | The retail console accepted a plaintext, no-challenge LDN network. The station-side authentication parser is reachable without keys. | Phase 3, with separate approval |
| No join, console stays on the scan screen | The console rejected security mode 3 or the network parameters. The no-key path is closed. | Record as blocked on keys; stop |
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
- Do not download or use `prod.keys`. If Phase 2 fails, the retail path is blocked on a lawful key source, not on a missing trick.

## Kill criteria

Close D9 as **blocked on keys** if:

- the adapter/driver cannot capture or transmit LDN action frames; or
- the console rejects the plaintext network and every no-key variant is ignored.

Close D9 as **negative** if:

- Phase 2 succeeds, but every malformed authentication response is rejected cleanly, the console stays responsive, and no crash report appears.

A single reproducible crash/reboot tied to one malformed frame is a **lead**, not a confirmed exploit. It would need a second reproduction, a minimized frame, and an analysis of which parser handled it before any capability claim.

## Related records

- [`docs/RESEARCH-PLAN.md`](RESEARCH-PLAN.md) — D9 and the ranked directions.
- [`research/hypotheses.json`](../research/hypotheses.json) — H-010.
- [`research/entry-points.json`](../research/entry-points.json) — EP-005 local wireless.
- [`research/evidence-ledger.json`](../research/evidence-ledger.json) — E-023, E-035, E-078.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — authorization and recovery.
