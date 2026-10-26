# Contributing

Thanks for helping with this research. The project values reproducible evidence and a strict read-only boundary more than speed.

## Before you start

- Read [`docs/SAFETY_AND_RECOVERY.md`](docs/SAFETY_AND_RECOVERY.md).
- Do not test on a console you do not own or have permission to use.
- Do not open a public issue containing a full serial number, keys, tokens, NAND dumps, or proprietary firmware.
- Security-sensitive reports go through [`SECURITY.md`](SECURITY.md), not the public issue tracker.

## What is in scope

- Corrections and additions to the evidence ledger, source register, and compatibility matrix.
- Improvements to the read-only macOS USB inspection tooling.
- Tests, documentation, accessibility, and reproducibility improvements.
- New public sources that materially change a compatibility conclusion.

## What is out of scope

- Exploit development, payload injection, or RCM payload tools.
- Firmware updates or downgrades, flashing, NAND operations, or boot-configuration changes.
- Modchip installation instructions or automation.
- Claims that a method works without reproducible evidence.
- Copying third-party code without checking its license and attribution requirements.

## Evidence rules

Every material claim must be recorded in `research/evidence-ledger.json` and referenced by the compatibility matrix or documentation.

1. Use one of the five status labels: `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `DISPROVEN`, `UNKNOWN`.
2. Add or update the source in `research/sources.json` with a URL, retrieval date, and snapshot note.
3. State the scope and the limitations. "Works on Switch" is not the same as "works on OLED on 23.0.1".
4. Separate firmware compatibility from exploit compatibility.
5. Prefer primary sources: official releases, source code, protocol documentation, and maintained guides. Label secondary sources.
6. Do not turn an absence of evidence into a claim of impossibility. Use `UNKNOWN` when the evidence does not decide the question.
7. Do not include a full serial number. A three-character prefix is enough for model-family checks.

## Generated files

`docs/SOURCES.md`, `research/evidence-ledger.md`, and `research/compatibility-matrix.md` are generated. Edit the JSON source of truth, then run:

```bash
python3 scripts/render_research.py --write
python3 scripts/render_research.py --check
```

## Development setup

The base tooling uses only the Python standard library.

```bash
python3 --version
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/validate_research.py
python3 scripts/render_research.py --check
```

The optional PTP probe needs `pyusb` in a repository-local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[ptp]'
```

Do not install system-wide packages, change macOS security settings, or run privileged commands as part of a contribution.

## Code style

- Target Python 3.11 or newer.
- Use type hints for public functions and dataclasses for structured records.
- Keep the base package free of third-party dependencies.
- Prefer explicit error types and documented exit codes over bare exceptions.
- Do not log full serial numbers. Use `switch_usb_probe.redact` for any device-derived string.
- Keep hardware access behind the `ptp-info` command and its `--confirm` gate.

## Tests

- Add mocked tests for new USB parsing, classification, PTP, cancellation, and error paths.
- Do not require real hardware in CI.
- A test is not "passed" unless it actually ran. Record the command and result in the pull request.
- Include a negative test when adding a safety check.

## Commits and pull requests

- Make coherent commits with descriptive messages.
- Do not stage unrelated files.
- Do not force-push, rewrite published history, or delete branches.
- In the pull request, list:
  - the claim or behavior changed;
  - the evidence or test that supports it;
  - any hardware that was used;
  - any remaining uncertainty.

## License

By contributing, you agree that your contribution is licensed under the repository's MIT license. Third-party material must retain its own license and attribution.
