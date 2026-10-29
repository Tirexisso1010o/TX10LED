# Firmware Analysis

> **Status: owner dump and keys present locally; `ldn` and `splay` identified, `miiEdit` decrypted for identification, content extraction blocked by key coverage.** `Firmware/prod.keys.txt` and `Firmware/Firmware.23.0.1` are owner-supplied artifacts from a modded 23.0.1 Switch that the owner no longer has; the dump and keys remain valid local artifacts, but the source console is not available for further dumps. Both are ignored by git and must never be committed, published, or shared. The dump is NCA-only and the key file stops at key generation 0x14 (20.0.0), so the 23.0.1 program/data NCAs that use the newer generation cannot be decrypted. The meta NCAs use generation 0x00 and are readable; the `ldn` and `splay` CNMTs were parsed. The only program NCA at key generation `0x15` (`miiEdit`) decrypted with `key_area_key_application_14` and verified its section-0 master hash; it is a Mii editor applet, not a remote-input surface. No `hactool` or `nxdump` is installed. This document defines the read-only handling and analysis plan; it does not authorize obtaining firmware or keys from anyone else.

## What is present

| Artifact | Details | Handling |
|---|---|---|
| `Firmware/prod.keys.txt` | 222 keys, no malformed lines; master keys through `master_key_14` and key-area keys through `key_area_key_application_14` | Local only; ignored by git; never paste values |
| `Firmware/Firmware.23.0.1/` | 238 NCA files, about 325 MB; 76 program, 121 meta, 38 data, 3 public-data NCAs | Local only; ignored by git; do not publish decrypted output |

The keys decrypt the Phase 1 LDN advertisement with key-derivation protocol 1, which confirms they match the LDN key derivation (`E-081`). They do **not** cover the 23.0.1 NCA key generation: 96 of the 238 NCAs use key generation `0x17`, including 67 of the 76 program NCAs, which needs `key_area_key_application_16`, and the file stops at `0x14`. The firmware dump's version is owner-reported and folder-named 23.0.1; it has not been independently verified with a firmware tool.

## First read-only result (2026-10-29)

All 238 NCA headers decrypted as valid NCA3 with the owner's `header_key`. The `ldn` sysmodule is identified:

| Field | Value |
|---|---|
| Title ID | `0100000000000018` (`ldn`) |
| Title version | `0x5c0004b0` (1543505072) |
| Meta NCA | `5bc39286ff59b4bd3abc2bbca467e86c.cnmt.nca` |
| Program NCA | `755bcf33085ed666cbbcf34de83d1cb0.nca` |
| Content type | Program |
| Size | 556,544 bytes |
| Key generation | `0x17` (23.0.0) |
| Effective key-area index | `0x16` (the header's `crypto_type2` minus one) |
| Section 0 | 556,032-byte AES-CTR PartitionFS, `0xc00`–`0x87e00` |
| Required key | `key_area_key_application_16` |
| Present in key file | **No** (file stops at `_14`) |
| Program content extraction | **Blocked** |
| Metadata extraction | **Successful** |

The `ldn` **meta** NCA decrypts with `key_area_key_application_00`, so the CNMT is readable even though the program content is not. The CNMT reports title version `0x5c0004b0` and the program NCA's SHA-256; that hash matches the local `755bcf...` file exactly, which confirms the local NCA is intact and matches its metadata. The program NCA's key area and section remain encrypted with the missing `key_area_key_application_16`.

The dump contains no `package1`, `package2`, KIP, or other non-NCA file. Package1 lives in the BOOT0 partition, so this dump cannot support the warmboot direction. The sanitized record is [`research/hardware-observations/2026-10-29-firmware-inventory.json`](../research/hardware-observations/2026-10-29-firmware-inventory.json).

To unblock `ldn` and `splay` extraction, the owner would need a key set that includes `key_area_key_application_15` and `key_area_key_application_16` (or `master_key_15`/`master_key_16` plus the generation sources). To unblock package1 analysis, the owner would need a 23.0.1 BOOT0/package1 dump from a console they own or control. The original modded 23.0.1 source console is no longer available, and the remaining modded console runs 22.0.0, so a matching dump is not currently obtainable. Do not download either.

## Second read-only result (2026-10-29): program key coverage and `splay`

The program NCAs were grouped by key generation. The distribution explains why only one program could be decrypted:

| Program key generation | Count | Notes |
|---|---:|---|
| `0x07` | 1 | `flog` (`01008bb00013c000`), an NES emulator, not a system surface. |
| `0x15` | 1 | `miiEdit` (`0100000000001009`), a Mii editor applet. |
| `0x16` | 7 | Not decryptable with the supplied keys. |
| `0x17` | 67 | Includes `ldn` and `splay`; needs `key_area_key_application_16`. |
| **Total** | **76** | |

The `miiEdit` program NCA is `c5d032046782d4bd6fc4b5c012a4e110.nca` (16,103,424 bytes, key generation `0x15`, crypto type 2). Its section-0 master hash verified with `key_area_key_application_14`, and its ExeFS PFS0 contains `main`, `main.npdm`, `rtld`, and `sdk`; the NPDM name is `miiEdit`. This confirms that the local header/key-area/AES-CTR path is correct. It does **not** provide the missing `key_area_key_application_16` (which covers NCA key generation `0x17`), and `miiEdit` is not a remote-input surface (`E-103`).

The `splay` program NCA is `b837233731cc2c6b3bc384489be7d46a.nca` (6,722,560 bytes, key generation `0x17`, crypto type 2), so its key area and section remain encrypted. The `splay` meta NCA is `e481ece5d922f9a3776493f891fa0ef9.cnmt.nca` (3,584 bytes, key generation `0x00`, crypto type 0). Its CNMT is readable:

| Field | Value |
|---|---|
| Title ID | `0100000000001048` (`splay`) |
| Title version | `0x5c0004b0` (1543505072) |
| Content meta type | `1` (SystemProgram) |
| Content count | 1 |
| Content ID | `b837233731cc2c6b3bc384489be7d46a` |
| Content type | `1` (Program) |
| Content size | `0x669400` (6,722,560) |
| Program NCA SHA-256 (from CNMT) | `b837233731cc2c6b3bc384489be7d46ab0cc50982747a54bfd7b014e57017812` |
| Matches local program NCA | **Yes** |

The CNMT match confirms the local `splay` program NCA is intact and correctly paired with its metadata. It does not decrypt the program content (`E-103`). The public GameShare/`splay` review is recorded in `E-102`: no public `splay`/GameShare vulnerability was found, and no post-20.0.0 `splay` security fix is documented.

## What is installed

| Tool | Purpose | Location |
|---|---|---|
| `capstone` 5.0.7 | AArch64 disassembly from Python | Repository `.venv` |
| `pyelftools` | ELF/KIP/NSO structure parsing | Repository `.venv` |
| `hactool` | Decrypt and unpack NCA, package1 (`pk11`), KIP, NSO, RomFS | **Not installed** |

A local Python script (not part of the repository) decrypted the NCA headers, the key-generation-`0x15` `miiEdit` section, and the `ldn`/`splay` meta CNMTs. It does not replace `hactool` for RomFS, KIP, or package1 extraction.

`hactool` is not in `PATH` on macOS or in the OrbStack VM, and no local build was found. The documented build is:

```bash
git clone https://github.com/SciresM/hactool.git
cd hactool
cp config.mk.template config.mk
git submodule update --init --recursive
make -j4
```

This downloads **tool source only**, not firmware or keys. Building it is allowed; using it against the owner's local dump is allowed. Do not download prebuilt key files or firmware.

## What a dump needs

1. **Switch 1 firmware 23.0.1.** The owner's dump is folder-named 23.0.1 and is the right platform. A Switch 2 dump would be a different platform and is not useful for this target.
2. **`prod.keys` matching the console.** Package1 on Mariko is RSA-signed and AES-encrypted; NCAs and KIPs need keys. The owner's keys decrypt the LDN advertisement but stop at key generation 0x14, so they do not cover the 23.0.1 NCA key generation used by `ldn` and `splay` (`0x17`). A matching key set must include the generation used by the target NCAs; the key-generation-`0x15` `miiEdit` program is the only program that decrypts with the current file.
3. **A lawful source.** A dump from a console you own that already runs CFW, or a dump you already possess. The owner's 23.0.1 artifacts come from a modded 23.0.1 Switch that is no longer available; the remaining modded console runs 22.0.0 and cannot supply 23.0.1 keys or BOOT0. This project does not use dumps downloaded from the internet, and does not help obtain them.

## Handling rules

- Keep the dump and keys **outside version control**. They currently live under `Firmware/`, which `.gitignore` excludes along with `Firmware.*/` and `prod.keys*`.
- Never commit firmware, keys, certificates, or decrypted system modules. `.gitignore` covers the common extensions and `firmware/`/`Firmware/`/`keys/` directories.
- Do not paste key values or full serial numbers into issues, chat, or commits.
- Keep extracted NCAs, KIPs, NSOs, and package1 images in a local-only directory such as `Firmware/extracted/` or outside the repository entirely.
- Analysis is read-only. Nothing in this workflow writes to the console.

## Analysis plan

### 1. Triage

- Inventory every file: type, size, SHA-256.
- Parse the plaintext NCA headers (`NCA3` magic at `0x200`, content type at `0x205`, program ID at `0x210`) to map each file to a title.
- Identify package1, package2, the KIP list, and each sysmodule NCA.
- Locate `ldn` and record its NCA, title ID, and content type before attempting extraction.
- Locate `splay` and `miiEdit`; record their key generations and which program NCAs are decryptable with the supplied keys.
- Record which components are Mariko-specific.

### 2. LDN parser (D9)

- Decrypt the `ldn` program NCA with a key set that covers its key generation (`0x17` for this dump).
- The current key file stops at `0x14`, so this step is **blocked**. The header-level identification is recorded in [`research/hardware-observations/2026-10-29-firmware-inventory.json`](../research/hardware-observations/2026-10-29-firmware-inventory.json).
- Once decrypted, extract the NSO, then disassemble the advertisement/authentication parser with Capstone.
- Compare the station-side and host-side paths against the 23.0.0 fix for `CVE-2026-82079`.
- Audit: frame length fields, participant indices, challenge length, and any copy from the action-frame payload.
- Record a tooling or key-coverage gap if the NCA cannot be decrypted.

### 2b. GameShare / `splay` parser

- The `splay` program NCA is key generation `0x17`, so the same key-coverage gap applies. Its meta CNMT is readable and already matches the local program NCA (`E-103`).
- Once a key set covering generation `0x17` is available, decrypt the program NCA, extract the ExeFS, and identify the NACP/JPEG and stream setup paths.
- Audit: NACP field lengths, JPEG metadata and decoder handoff, stream framing, and any copy from host-supplied data.
- Do not spoof a GameShare host or send crafted data to the console; that requires a Switch 2 host and separate approval.

### 3. Stage 3: package1 and warmboot

This is the decisive missing stage. Warmboot is package1 section 0.

- **Blocked:** the owner's dump is NCA-only and contains no package1. Package1 is stored in BOOT0, so a separate 23.0.1 BOOT0/package1 image is required. The modded 23.0.1 source console is no longer available, and the remaining modded console is on 22.0.0; a matching image is not currently obtainable.
- Once available, decrypt and extract package1 (`-t pk11`).
- Split section 0 (warmboot), section 1 (NX bootloader), section 2 (Secure Monitor).
- Disassemble the warmboot and TSEC payloads with Capstone.
- Audit: length fields, indices, pointer arithmetic, and data copied from the boot medium before Horizon verifies anything.
- Rank candidates by whether they are reachable before Horizon starts and whether the input is attacker-influenced.

### 4. Stages 1–2: sysmodules and browser

- `fs` (`Path::Normalize`, `GetEntryType`), `ldr`, `ns`, `ssl`, `bsd`, and `sfdnsres`.
- The NetFront/WebKit browser components, if present as NROs.
- Audit IPC handlers for unchecked lengths, integer overflow, and path handling.

### 5. Diff

If a second firmware version is available, diff the same components. Differences highlight security-relevant changes; they mostly reveal *fixed* bugs, so they inform bug classes and code regions rather than yielding a live exploit.

### 6. Candidate register

Each candidate gets a record with component, firmware applicability, reachability, prerequisites, expected capability, test procedure, and kill criteria — the same schema as `research/hypotheses.json`.

## What this can and cannot prove

- **Can:** identify candidate memory-safety defects, map trust boundaries, and produce falsifiable hypotheses.
- **Confirmed locally:** the header, key-area, AES-CTR section, PFS0, and CNMT path works for the key-generation-`0x15` `miiEdit` program and for the `0x00` meta NCAs. This does not extend to the `0x17` `ldn`/`splay` program NCAs.
- **Cannot:** confirm exploitability without executing the code. Validation would need an emulator or a hardware test, which is outside the current authorization.
- **Likelihood:** a candidate is plausible; a complete, working chain is not. The code is mature and heavily audited, and even a real stage-3 bug would need a delivery path.

## Related records

- [`docs/GAP-ANALYSIS.md`](GAP-ANALYSIS.md) — why stage 3 is the bottleneck.
- [`research/hypotheses.json`](../research/hypotheses.json) — candidate schema.
- [`docs/SAFETY_AND_RECOVERY.md`](SAFETY_AND_RECOVERY.md) — authorization boundary.
