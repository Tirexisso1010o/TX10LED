# Known Limitations

This document records what the research and tooling cannot establish. It is part of the evidence, not a disclaimer appended at the end.

## Scope limitations

- **Public sources only.** The conclusion is based on public releases, documentation, source code, and maintained guides reviewed on 2026-10-26. It is not an audit of private research, unpublished exploits, or every firmware binary.
- **No proof of impossibility.** "No publicly documented software-only path" is not the same as "no software-only path can exist". The ledger labels the existence of an undisclosed exploit `UNKNOWN`.
- **Hardware family, not a laboratory teardown.** The OLED is identified as Mariko/Tegra X1+ from public hardware documentation. This project has not opened the console or inspected its board.
- **User-reported target identity.** The model `HEG-001` and firmware `23.0.1` are user-reported until manually confirmed and, optionally, observed through PTP.
- **No exploit development.** The project does not attempt to find, develop, or validate a new vulnerability. It records what is publicly documented.

## Firmware and release limitations

- Atmosphère 1.12.1's release notes explicitly add support for firmware **23.0.0** and describe 23.0.0 changes. Firmware **23.0.1** support is established by the maintained NH Switch Guide compatibility checker and community issue discussion. The distinction is recorded in E-001.
- A new Atmosphère or hekate release can change firmware compatibility without changing the entry-point picture.
- A firmware update can burn eFuses and is not a reversible troubleshooting step.
- Open issues and regressions can exist even when a firmware is listed as supported. Firmware support is not a guarantee of bug-free operation.
- Switchbrew's 23.0.1 page has an unfilled `Security flaws fixed` placeholder. The absence of a listed security fix is not proof that 23.0.1 contains none; the official change-log describes a stability update.

## Entry-point limitations

- **`ns2jb` is not a target-specific result.** It is packaged for Switch 2 on 23.0.1. The author says the chain was also tested on Switch 1, but the model and firmware are not stated and the Switch 1 version is not packaged. No OLED/Mariko 23.0.1 test is documented. It does not provide kernel, bootROM, CFW, or persistence.
- **`UNKNOWN` surfaces are not cleared.** Browser/WebKit, local wireless, Bluetooth, game saves/cartridges, and kernel/TrustZone remain `UNKNOWN` where no public 23.0.1 chain was found. A public flaw list can lag private research.
- **A fixed flaw is not the whole surface.** CVE-2026-82079 is fixed in 23.0.0, but that does not prove the local-wireless stack has no other vulnerabilities. The same applies to the 23.0.0 `bsdsocket` and `audio` fixes.
- **Historical entry points are not current ones.** PegaSwitch targets early firmware and the Fake News entry point; Caffeine targets patched Erista 4.1.0. Neither applies to Mariko/OLED on 23.0.1.
- **Public exploit availability is not established.** CVE-2026-82079's CVE record contains no exploit code, and the linked HackerOne report was not accessible in this review. The ledger labels exploit availability `UNKNOWN`.
- **A userland primitive is not a boot chain.** Even a successful userland/sysmodule compromise would still need a kernel or bootROM stage to launch Atmosphère persistently.
- **The entry-point matrix records public documentation, not absolute exploitability.** `DISPROVEN` means the known public method is patched or the documented surface does not execute code; it does not prove that no private method exists.

## USB limitations

- The OLED's enumeration as `057e:201d` is only **partially verified** until a real hardware observation is recorded.
- PTP behavior is documented by reverse engineering and can vary by firmware revision.
- The PTP interface may be claimed by `ptpcamerad` or another macOS process. The tool reports a busy device rather than killing the process.
- A PTP `DeviceInfo` response can be spoofed by modified firmware. It is an observation, not an integrity attestation.
- Stock USB does not expose a shell, ADB, firmware-query service, or general-purpose remote-control interface.
- USB enumeration cannot establish exploitability, boot state, CFW access, or NAND contents.
- `system_profiler` and `ioreg` output formats are macOS implementation details and may change across releases.
- The tool does not support Windows or Linux enumeration backends. The research data is platform-independent, but the CLI's enumeration path is macOS-first.

## Research-process limitations

- Search results can be incomplete. A source that was not indexed, not public, or not in the reviewed languages could change a conclusion.
- The source register records snapshots, not byte-for-byte archives. Links can rot or change after the retrieval date.
- Community guides are maintained by volunteers. They are high-quality secondary sources, not Nintendo statements.
- The validator checks schema, cross-references, summary counts, and high-confidence secret patterns. It cannot prove that a prose claim is true.
- The test suite uses mocked devices. It verifies parsing and safety behavior, not real USB firmware behavior.

## Safety and legal limitations

- Modchip installation is out of scope and carries warranty, safety, and bricking risks.
- Console modification may affect warranty coverage and may violate service terms or local law.
- This repository does not provide legal advice.
- The project does not authorize firmware changes, NAND operations, or payload injection.

## What would improve confidence

- A redacted hardware observation from the target OLED in PTP mode, recording the model, firmware display version, and serial prefix.
- A manual confirmation of the model and firmware from the console settings.
- A maintained source that documents an OLED-specific PTP product ID or behavior.
- Independent reproduction of the compatibility conclusion on another OLED.
- A packaged, reproducible Switch 1 version of the `ns2jb` chain, with the model and firmware identified.
- An independent OLED/Mariko 23.0.1 test of a userland/sysmodule chain.
- A public chain connecting a userland/sysmodule primitive to kernel or bootROM access on Mariko.
- A public 23.0.1-specific browser, local-wireless, or Bluetooth chain.
- A public, reproducible entry point that changes the software-only conclusion. If one appears, the matrix and evidence ledger must be updated rather than patched with an unsupported claim.
