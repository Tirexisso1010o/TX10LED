# USB Integration

## Purpose

The USB tool is an **inspection-first** macOS tool. It exists to answer a narrow question:

> What does the host see when a Nintendo Switch is connected, and what identity does the console report through its documented PTP interface?

It is not a payload injector, a firmware flasher, a shell, or a general-purpose remote-control client.

## Architecture

```text
CLI (argparse)
  ├── doctor       environment and repository checks
  ├── list         one-shot enumeration
  ├── watch        polling connect/disconnect events
  ├── classify     offline VID:PID explanation
  ├── compat       read the research matrix
  └── ptp-info     opt-in device open + PTP GetDeviceInfo
        │
        ├── enumeration (stdlib)
        │     ├── system_profiler SPUSBDataType -json
        │     └── ioreg -a -p IOUSB -l -w 0 (plist fallback)
        │
        ├── classification (pure)
        │     └── known Switch modes + safety notes
        │
        ├── PTP (optional pyusb)
        │     ├── USB bulk transport
        │     ├── PTP container framing
        │     └── DeviceInfo parser
        │
        └── output
              ├── human-readable tables
              ├── JSON (serials redacted)
              └── JSONL structured logs (serials redacted)
```

The base enumeration path has **no third-party dependencies**. `pyusb` is imported lazily and only for `ptp-info`.

## Enumeration

### Primary backend: `system_profiler`

```bash
system_profiler SPUSBDataType -json
```

The parser walks the `SPUSBDataType` array and any nested `_items` arrays. It reads:

- `_name`
- `manufacturer`
- `serial_num`
- `vendor_id`
- `product_id`
- `location_id`
- `device_speed` (when present)

Vendor and product IDs are normalized to integers and rendered as `vvvv:pppp` in lowercase hexadecimal.

### Fallback backend: `ioreg`

```bash
ioreg -a -p IOUSB -l -w 0
```

`ioreg` emits an XML property list. The parser walks `IORegistryEntryChildren` recursively and keeps dictionaries that contain both `idVendor` and `idProduct`. It reads `USB Product Name`, `USB Vendor Name`, `USB Serial Number`, `locationID`, and `bDeviceClass` when available.

The fallback is used when `system_profiler` fails or times out. An empty but successful `system_profiler` result is treated as a valid empty bus, not as a reason to retry.

### What enumeration does not do

- It does not open a USB device.
- It does not claim an interface.
- It does not send a control transfer.
- It does not read or write storage.
- It does not kill or restart a system daemon.

## Recognized modes

| Mode | VID:PID | Interpretation | Safety note |
|---|---|---|---|
| `switch_normal` | `057e:2000` | Nintendo Switch normal USB mode | Identification only; no firmware query |
| `switch_ptp` | `057e:201d` | Switch / Switch Lite PTP album mode | Read-only `GetDeviceInfo` is supported |
| `switch2_ptp` | `057e:2061` | Switch 2 PTP album mode | Not the OLED target |
| `switch_rcm` | `0955:7321` | NVIDIA Tegra APX / Switch RCM | RCM is reachable; payload injection is not possible on Mariko |
| `switch_pro_controller` | `057e:2009` | Switch Pro Controller | Not a console |
| `joycon_left` | `057e:2006` | Left Joy-Con | Not a console |
| `joycon_right` | `057e:2007` | Right Joy-Con | Not a console |
| `joycon_grip` | `057e:200e` | Joy-Con charging grip | Not a console |
| `nintendo_unknown` | vendor `057e` | Nintendo device with an unrecognized product ID | No control capability claimed |
| `unknown` | anything else | Unrecognized USB device | No control capability claimed |

The tool never interprets a known ID as proof of exploitability. The RCM classification in particular says only that the device is in RCM; it does not say that a payload can be accepted.

## PTP identity probe

### Why PTP

Switch system firmware 11.0.0 and later expose a PTP/MTP album-transfer interface when the console is on **Settings → Data Management → Manage Screenshots and Videos → Copy to PC via USB**. The documented PTP surface is limited to operations `0x1001`–`0x100A`.

Switchbrew documents the relevant mapping:

- DeviceInfo `Serial Number` = `GetSerialNumber`
- DeviceInfo `Device Version` = `SystemVersion DisplayVersion`

That makes `GetDeviceInfo` a read-only way to observe the console's reported model, firmware display version, and serial prefix.

### USB shape

The PTP interface is expected to use:

- interface class `0x06` (still image)
- subclass `0x01`
- protocol `0x01`
- one bulk IN endpoint
- one bulk OUT endpoint
- optionally an interrupt IN endpoint for events

The tool selects the first matching interface. If no matching interface is found, it reports an unsupported mode instead of guessing.

### PTP container framing

A PTP container starts with a 12-byte little-endian header:

```text
offset  size  field
0       4     length (header + parameters or payload)
4       2     type (1 = command, 2 = data, 3 = response, 4 = event)
6       2     operation/response code
8       4     transaction ID
12      ...   parameters (u32 each) or data payload
```

`GetDeviceInfo` is operation `0x1001`. A successful response is code `0x2001` (`OK`); `0x2000` is `Undefined`. A data phase may precede the response.

The parser validates:

- the minimum and maximum container length;
- the container type;
- the transaction ID;
- the response code;
- the DeviceInfo field bounds and string lengths.

### Session behavior

By default, `ptp-info` sends **only** `GetDeviceInfo`. Some PTP devices require `OpenSession` before they answer. If the device returns `SessionNotOpen` (`0x2003`), the tool exits with code `5` and explains the `--allow-session` option.

With `--allow-session`, the tool may send:

1. `OpenSession` (`0x1002`) with session ID `1`
2. `GetDeviceInfo` (`0x1001`)
3. `CloseSession` (`0x1003`)

No object transfer, storage mutation, property write, or payload operation is sent. The session is closed in a `finally` block.

### DeviceInfo parsing

The parser follows the PTP DeviceInfo layout:

```text
StandardVersion                 u16
VendorExtensionID               u32
VendorExtensionVersion          u16
VendorExtensionDescription      PTP string
FunctionalMode                  u16
OperationsSupported             u32 count + u16[]
EventsSupported                 u32 count + u16[]
DevicePropertiesSupported       u32 count + u16[]
CaptureFormats                  u32 count + u16[]
ImageFormats                    u32 count + u16[]
Manufacturer                    PTP string
Model                           PTP string
DeviceVersion                   PTP string
SerialNumber                    PTP string
```

A PTP string is a one-byte character count followed by UTF-16LE code units, including the terminating null. The parser strips the terminator and rejects truncated or oversized fields.

## Safety gates

### Dry run

```bash
switch-usb-probe ptp-info --dry-run
```

The dry run enumerates devices, selects a PTP candidate, and prints the plan. It does not import `pyusb`, open the device, or send a request. The JSON output includes `"opened": false`.

### Confirmation

```bash
switch-usb-probe ptp-info --confirm
```

Without `--confirm`, `ptp-info` behaves as a dry run even if `--dry-run` is omitted. This is intentional: opening a device should be an explicit act.

### Session opt-in

```bash
switch-usb-probe ptp-info --confirm --allow-session
```

Only use this after the tool reports that the device requires a session. It still performs identity queries only.

### Timeouts

`--timeout` sets the enumeration and USB transfer timeout in seconds. A timed-out operation exits with code `4`. The tool does not retry indefinitely and does not leave a session open intentionally.

### Cancellation

`watch` handles `SIGINT` and exits with code `130`. PTP operations use bounded USB timeouts; a user interrupt is reported as a cancellation rather than a successful probe.

## macOS permissions and busy devices

### `ptpcamerad`

macOS includes `ptpcamerad`, which can claim a camera/PTP interface. If the interface is busy, the tool reports exit code `3` with a hint. It does **not**:

- kill `ptpcamerad`;
- run `sudo`;
- disable System Integrity Protection;
- install a privileged driver;
- detach a kernel driver silently.

Close applications that may be using the device and try again. If the interface remains busy, stop and investigate rather than escalating privileges.

### libusb

`pyusb` needs a working libusb backend. On Apple Silicon, a Homebrew libusb installation is commonly at `/opt/homebrew/lib/libusb-1.0.dylib`. The `doctor` command checks common locations and reports what it finds. Installing libusb system-wide is not required by this repository and must be discussed before it is attempted.

### Permissions

USB access on macOS usually works for non-HID devices without elevation. If access is denied, the tool reports a permission error. Do not work around it with `sudo`; investigate the device claim and the macOS version instead.

## Privacy and logging

- Full serial numbers are never emitted. The tool keeps a short prefix and replaces the rest with `***`.
- JSON output uses `serial_prefix`, not `serial_number`.
- JSONL logs pass through the same redaction function.
- `--log-file` writes structured logs to a local file. Review logs before sharing them.
- The repository ignores `*.local.json` and `*.local.md` so local observations do not get committed accidentally.
- Do not commit NAND dumps, keys, certificates, tokens, or proprietary firmware.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success, including an intentional dry run |
| `2` | No matching device |
| `3` | Permission denied or interface busy |
| `4` | Timeout |
| `5` | Unsupported mode, input, or missing optional dependency |
| `130` | Cancelled |

## Commands

```bash
# Environment, optional dependency, research data, and bus checks
PYTHONPATH=src python3 -m switch_usb_probe doctor

# Enumerate all USB devices
PYTHONPATH=src python3 -m switch_usb_probe list

# Only recognized console devices
PYTHONPATH=src python3 -m switch_usb_probe list --switch-only

# JSON output
PYTHONPATH=src python3 -m switch_usb_probe list --json

# Watch for connect/disconnect events
PYTHONPATH=src python3 -m switch_usb_probe watch --switch-only --interval 1.0

# Offline VID:PID explanation
PYTHONPATH=src python3 -m switch_usb_probe classify --vid 0x057e --pid 0x201d

# Read-only PTP plan
PYTHONPATH=src python3 -m switch_usb_probe ptp-info --dry-run

# Read-only PTP identity query, after confirming the device
PYTHONPATH=src python3 -m switch_usb_probe ptp-info --confirm
```

## Testing

The mocked test suite is planned, not implemented. It will cover:

- `system_profiler` JSON parsing, nested hubs, empty buses, and malformed output;
- `ioreg` plist fallback and timeout handling;
- unknown devices and unsupported modes;
- connect/disconnect diffing;
- cancellation;
- permission and busy errors;
- dry-run and confirmation gates;
- PTP container encoding/decoding;
- DeviceInfo parsing and bounds checks;
- the assertion that the default path sends only `GetDeviceInfo`;
- serial redaction;
- research data validation.

No real hardware is required for CI. Until the test suite exists, `python3 scripts/validate_research.py` validates the research data and the CLI has been exercised with `doctor`, `classify`, and `compat`.

## Limitations

- OLED enumeration as `057e:201d` is only partially verified until hardware validation is recorded.
- PTP behavior may vary by firmware revision.
- `ptpcamerad` behavior is a macOS implementation detail and can change.
- A PTP response can be spoofed by modified firmware; it is an observation, not an integrity attestation.
- The tool does not attempt to bypass any access control or console protection.
