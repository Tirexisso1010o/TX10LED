# Hardware Observations

This directory holds **real, redacted observations** from hardware. Do not create a file here from a guess, a template, or another console's data.

## Rules

- Record only what was actually observed.
- Keep the serial to a three-character prefix. Never write a full serial.
- Do not include NAND dumps, keys, certificates, tokens, or proprietary firmware.
- Record the host OS, the command, the exit code, and the relevant output.
- If a command was not run, say so. Do not fill the field with an assumed value.
- If the console was modified, say so. A modchipped console is not an unmodified target.
- Use `YYYY-MM-DD-<mode>.json` for the filename.
- Local, unredacted work files should use `*.local.json` and are ignored by Git.

## Template

Copy `TEMPLATE.json` to a dated filename and replace the placeholders with observed values. Remove fields that do not apply rather than inventing values.

## What counts as evidence

A PTP `DeviceInfo` response is evidence of what the console reported. It is not proof of exploitability, boot state, or integrity. Record that limitation in the observation.
