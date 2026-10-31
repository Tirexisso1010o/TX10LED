# H-013 — File-picker capability probe

> **Status: prepared, not run.** One page load; the owner selects a benign SD-card file; the page reports only name/size/type. It does not read or upload the file, and it does not send a crafted path.

## Purpose

The download route is closed negative: the captive-portal applet has no HTML download attribute, no save/open/directory picker, and no `navigator.storage`/`caches` API (`E-120`). The applet does expose `<input type=file>`. This probe asks whether that input actually opens a picker and what metadata it exposes.

A picker is not a trigger. The page would receive a `File` object, not the full fs path; a long-path `..\` trigger is speculative. But it is the only remaining free browser file surface.

## Probe

`scripts/webkit_file_picker_probe.html`:

- shows one `<input type=file>` and a status line;
- posts `file_picker_ready` on load;
- on selection, posts `file_picker` with `name`, `size`, `type`, `lastModified`, `webkitRelativePath`;
- on cancel, posts `file_picker_cancel`;
- never reads the file contents and never uploads it.

The page and portal logs are local-only.

## Run

Preflight:

```sh
.venv/bin/python scripts/webkit_portal.py --page scripts/webkit_file_picker_probe.html --dry-run
```

Start the portal with the narrow `sudo` exception:

```sh
sudo .venv/bin/python scripts/webkit_portal.py --page scripts/webkit_file_picker_probe.html --duration 300
```

Console:

1. **Settings → Internet → Internet Settings → [active network] → Change Settings**.
2. **DNS Settings → Manual**. Primary DNS: the Mac address from the dry run (`192.168.178.167` on 2026-10-31).
3. Save, then **Test Connection**.
4. The page should say **ready; choose a file**.
5. Press the file input. If a picker opens, navigate to the SD card and select the benign control screenshot `NINTENDO/ALBUM/2026/10/27/2026102700452400-57B4628D2267231D57E0FC1078C0596D.jpg`.
6. Do not select anything outside the SD card. Do not rename or copy files.
7. Revert DNS to **Automatic** immediately.
8. Press **Ctrl-C** in the portal Terminal.

The page reports only metadata. If no picker opens, or the file cannot be selected, the browser file surface is closed for this applet.

## Interpretation

| Result | Meaning |
|---|---|
| No picker, or picker opens but no file can be selected | The browser file surface is closed. Stop this route. |
| Picker opens and the control file is selected; page reports its name/size | The picker works. A later deep/long-path test would need a crafted card, and the page still would not see the full path. |
| Picker opens but shows no SD-card files | The applet restricts the picker to another location. The browser file surface is closed for the SD-card path. |

A successful selection is **not** a trigger. It does not show that the applet passes the selected path to `fs`, and it does not provide code execution.

## Safety and authorization

- One page load; the owner selects a benign file; no file contents are read, uploaded, or written.
- The SD card is read-only to this test; do not rename or copy files.
- DNS is temporary and must be reverted immediately.
- The portal binds UDP 53/TCP 80 on the Mac LAN address under the existing narrow `sudo` exception.
- **No run is authorized by this document.** A separate explicit approval is required for the page load.

## References

- `E-120` — the download capability negative.
- `E-119` — the SD-card sibling-directory negative.
- `docs/H-013-BROWSER-PROBE-PLAN.md` — the download probe.
- `scripts/webkit_file_picker_probe.html` — the page.
