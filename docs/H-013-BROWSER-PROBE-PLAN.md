# H-013 — Browser/download capability probe

> **Status: prepared, not run.** The probe is a single page load that only detects download/file APIs. It does not click a download, send a crafted filename, or write to the SD card. It needs explicit approval for the page load.

## Purpose

The SD-card sibling-directory route is closed negative: the Album only traverses `NINTENDO/ALBUM/YYYY/MM/DD` (`E-119`). The remaining free-surface candidate is the captive-portal applet: if it exposes a download or file-system API, a long crafted filename could reach `fs` without SmileBASIC.

Before testing any crafted filename, establish whether the applet can write files at all.

## Probe

`scripts/webkit_download_probe.html` reports:

- `HTMLAnchorElement.download` support and the value it accepts;
- `Blob`, `URL.createObjectURL`, `FileReader`, `fetch`, `XMLHttpRequest`;
- `<input type="file">`, `files`, `webkitdirectory`, `directory`;
- `showSaveFilePicker`, `showOpenFilePicker`, `showDirectoryPicker`;
- `navigator.storage`, `estimate`, `getDirectory`, `persist`;
- `caches`, `indexedDB`, `localStorage`, `sessionStorage`, `serviceWorker`;
- the user agent and origin.

It posts one `download_probe` event to `/fp`; the page status changes to `probe sent`. It does **not** auto-click the download button. The page includes a visible **Run benign TX10TEST.txt download** button; do not press it during this probe. A benign download click is a separate action and needs its own approval.

## Run

Preflight:

```sh
.venv/bin/python scripts/webkit_portal.py --page scripts/webkit_download_probe.html --dry-run
```

The dry run reports the Mac LAN address and the exact console steps. On 2026-10-31 it was `192.168.178.167`, UDP 53/TCP 80, 300-second duration.

Start the portal with the narrow `sudo` exception:

```sh
sudo .venv/bin/python scripts/webkit_portal.py --page scripts/webkit_download_probe.html --duration 300
```

Console:

1. **Settings → Internet → Internet Settings → [active network] → Change Settings**.
2. **DNS Settings → Manual**. Primary DNS: the Mac address from the dry run. Secondary: the router address, or automatic if allowed.
3. Save, then **Test Connection**.
4. Wait for the page to report **probe sent** or up to 30 seconds.
5. Revert DNS to **Automatic** immediately.
6. Stop the portal with Ctrl-C.

The page and the portal log are local-only. Do not serve a crafted filename or press the download button in this probe.

## Interpretation

| Feature result | Meaning |
|---|---|
| No `anchorDownload`, no file picker, no `showSaveFilePicker` | The applet has no download/file-write surface. The browser/download route is closed for this applet. |
| `anchorDownload` present, no picker | A download may still be possible. The next test is a **benign** `TX10TEST.txt` download, with separate approval, to see whether it saves and where. |
| `showSaveFilePicker` present | A file-save picker exists; a later test could select a path. This is unusual for the applet and needs a separate plan. |
| `inputFile` present | A file picker exists; a deep SD-card path could be selected later. It does not by itself pass a crafted path to `fs`. |

A positive feature result is **not** a trigger. Even a confirmed file write would need a long `..\` path and the Switch 1 `fs` binary/exploit for code execution.

## Safety and authorization

- One page load; no download click, no crafted filename, no SD-card write.
- DNS is temporarily set to the Mac and must be reverted immediately.
- The portal binds UDP 53/TCP 80 on the Mac LAN address only, under the existing narrow `sudo` exception.
- **No run is authorized by this document.** A separate explicit approval is required for the page load.

## References

- `E-119` — the SD-card sibling-directory negative.
- `E-112` — the W1 applet reachability and feature baseline.
- `scripts/webkit_download_probe.html` — the probe page.
- `docs/WEBKIT-NDAY-PLAN.md` — the portal and DNS procedure.
