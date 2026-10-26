# Security Policy

## Scope

This repository contains research documentation for a potential software-only jailbreak and a read-only USB inspection tool. It does not contain a working exploit, a payload, a firmware image, or a flashing utility.

Security reports are welcome for:

- A bug that causes the tool to write to a device, send an unintended USB request, or bypass the `--confirm` gate.
- A path traversal, command injection, or unsafe subprocess invocation in the CLI or scripts.
- A way for the tool to expose a full serial number, token, key, or other sensitive data in output or logs.
- A dependency or build issue that affects the tooling.

The project does not accept reports that require exploiting a console, distributing proprietary firmware, or publishing personal data.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Include the affected version or commit, a minimal reproduction, and the impact.

If private reporting is unavailable, open a minimal public issue that says you have a security report and asks the maintainer to enable a private channel. Do not include the exploit details, secrets, or personal data in that issue.

Do not paste full serial numbers, device keys, certificates, tokens, or NAND dumps into an issue, pull request, or chat. Redact serials to a three-character prefix.

## What to expect

This is a volunteer research project. Reports are reviewed on a best-effort basis. There is no guaranteed response time, bounty, or disclosure deadline. Please allow time for investigation before publishing details.

## Supported versions

The project is a research snapshot. The current supported state is the latest commit on the default branch. Older commits are kept for history but may contain outdated conclusions.

## Safe testing

- Use a console you own or have explicit permission to test.
- Do not run the tool with elevated privileges.
- Do not disable macOS System Integrity Protection, install unsigned kernel extensions, or install a privileged driver to make the tool work.
- Do not attempt payload injection, firmware changes, or NAND operations.
- If a test requires a state-changing action, stop and ask the maintainer first.

## Data handling

The tool redacts serial numbers by default and never emits a full serial number. Logs are JSONL and should still be reviewed before sharing. Do not commit local observation files; use the `*.local.json` naming convention, which is ignored by Git.

## License

Security reports and contributions are handled under the repository's MIT license. See [`LICENSE`](LICENSE).
