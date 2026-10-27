# Firmware Analysis

> **Status: tooling ready, no firmware present.** This document defines how a lawful dump would be handled. It does not authorize obtaining one.

## What is installed

| Tool | Purpose | Location |
|---|---|---|
| `hactool` | Decrypt and unpack NCA, package1 (`pk11`), KIP, NSO, RomFS | Built locally from `SciresM/hactool`, not committed |
| `capstone` 5.0.7 | AArch64 disassembly from Python | Repository `.venv` |
| `pyelftools` | ELF/KIP/NSO structure parsing | Repository `.venv` |

`hactool` is built with its bundled mbedTLS. Reproduce with:

```bash
git clone https://github.com/SciresM/hactool.git
cd hactool
cp config.mk.template config.mk
git submodule update --init --recursive
make -j4
```

## What a dump needs

1. **Switch 1 firmware 23.0.1.** A Switch 2 dump is a different platform and is not useful for this target.
2. **`prod.keys` matching the console.** Package1 on Mariko is RSA-signed and AES-encrypted; NCAs and KIPs need keys. Without keys, a dump is opaque.
3. **A lawful source.** A dump from a console you own that already runs CFW, or a dump you already possess. This project does not use dumps downloaded from the internet, and does not help obtain them.

## Handling rules

- Keep the dump and keys **outside the repository**, for example `~/switch-fw/23.0.1/`.
- Never commit firmware, keys, certificates, or decrypted system modules. `.gitignore` covers the common extensions and `firmware/`/`keys/` directories.
- Do not paste keys or full serial numbers into issues, chat, or commits.
- Analysis is read-only. Nothing in this workflow writes to the console.

## Analysis plan

### 1. Triage

- Inventory every file: type, size, SHA-256.
- Identify package1, package2, the KIP list, and each sysmodule NCA.
- Record which components are Mariko-specific.

### 2. Stage 3 first: package1 and warmboot

This is the decisive missing stage. Warmboot is package1 section 0.

- Decrypt and extract package1 (`-t pk11`).
- Split section 0 (warmboot), section 1 (NX bootloader), section 2 (Secure Monitor).
- Disassemble the warmboot and TSEC payloads with Capstone.
- Audit: length fields, indices, pointer arithmetic, and data copied from the boot medium before Horizon verifies anything.
- Rank candidates by whether they are reachable before Horizon starts and whether the input is attacker-influenced.

### 3. Stages 1–2: sysmodules and browser

- `fs` (`Path::Normalize`, `GetEntryType`), `ldr`, `ns`, `ssl`, `bsd`, and `sfdnsres`.
- The NetFront/WebKit browser components, if present as NROs.
- Audit IPC handlers for unchecked lengths, integer overflow, and path handling.

### 4. Diff

If a second firmware version is available, diff the same components. Differences highlight security-relevant changes; they mostly reveal *fixed* bugs, so they inform bug classes and code regions rather than yielding a live exploit.

### 5. Candidate register

Each candidate gets a record with component, firmware applicability, reachability, prerequisites, expected capability, test procedure, and kill criteria — the same schema as `research/hypotheses.json`.

## What this can and cannot prove

- **Can:** identify candidate memory-safety defects, map trust boundaries, and produce falsifiable hypotheses.
- **Cannot:** confirm exploitability without executing the code. Validation would need an emulator or a hardware test, which is outside the current authorization.
- **Likelihood:** a candidate is plausible; a complete, working chain is not. The code is mature and heavily audited, and even a real stage-3 bug would need a delivery path.

## Related records

- [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md) — why stage 3 is the bottleneck.
- [`research/hypotheses.json`](../research/hypotheses.json) — candidate schema.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — authorization boundary.
