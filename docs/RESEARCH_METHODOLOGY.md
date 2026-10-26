# Research Methodology

## Research questions

The investigation is organized around six questions:

1. Does Atmosphère support firmware 23.0.1?
2. Does the current hekate release support that firmware?
3. Does a documented software-only exploit chain apply to an unmodified Switch OLED?
4. Does a proposed method require a modchip, a hardware vulnerability, prior modification, an external payload injector, or another prerequisite?
5. Is the method independently reproduced and maintained?
6. What can be established through USB without booting or modifying the console?

The questions are deliberately separate. A "yes" to question 1 or 2 does not answer question 3.

## Source hierarchy

Sources are weighted in this order:

1. **Primary project sources** — official release notes, changelogs, source code, and protocol documentation from the project that owns the component.
2. **Maintained community guides** — the NH Switch Guide and Switchbrew, used for hardware and entry-point behavior that is not documented by Nintendo.
3. **Vendor documentation** — Nintendo support pages, NVIDIA/NVD advisories, and USB vendor databases.
4. **Secondary discussion** — GitHub issues and community reports, used only to corroborate a primary source or to identify a question that needs primary verification.

A secondary source alone does not produce a `VERIFIED` claim.

## Search strategy

The initial snapshot reviewed:

- Atmosphère releases, changelog, FAQ, and the issue tracker around firmware 23.0.x;
- hekate releases and the bootloader documentation;
- the NH Switch Guide's Getting Started, RCM, Modchip, and firmware-update pages;
- Switchbrew's hardware, boot-mode, Capmtp/PTP, Internet Browser, 23.0.0, 23.0.1, and System Flaws pages;
- libmtp's device table and PTP implementation;
- NVD's CVE-2018-6242 record and the CVE-2026-82079 record;
- Nintendo's OLED model and serial-location support page, and its September 2026 security advisory;
- the `ns2jb` write-up and repository, and the archived PegaSwitch repository;
- the installed OpenCode version, its configuration schema, and its v2 permissions documentation.

Searches were performed on **2026-10-26**. The source register records a retrieval date and a snapshot note for each source. The snapshot is not a byte-for-byte archive; it records the version, tag, commit, or page state that was observed.

## Status labels

| Label | Meaning | Minimum evidence |
|---|---|---|
| **VERIFIED** | Directly supported by an authoritative or primary source, with no reviewed contradiction. | At least one source; scope stated. |
| **PARTIALLY VERIFIED** | Indirect evidence, a related but not identical model, or a primary claim with a material gap. | At least one source; gap stated. |
| **UNVERIFIED** | Plausible or user-reported, but not independently checked. | A source is optional; the missing check is stated. |
| **DISPROVEN** | Contradicted by an authoritative source or direct evidence. | At least one source; the contradiction is stated. |
| **UNKNOWN** | Insufficient evidence; neither supported nor contradicted. | A source is optional; the limit is stated. |

Two rules matter:

- **Do not turn absence of evidence into impossibility.** If the public record does not decide a question, use `UNKNOWN`.
- **Do not turn firmware support into exploit support.** A release note that adds firmware support is not an entry-point disclosure.

The conclusion "no publicly documented software-only path exists" is labeled `DISPROVEN` for the claim that such a path exists **within the reviewed public documentation**. The separate claim "no undisclosed exploit exists" is labeled `UNKNOWN`.

## Evidence ledger

Each entry in [`research/evidence-ledger.json`](../research/evidence-ledger.json) has:

- a stable ID (`E-001`, ...);
- a single, falsifiable claim;
- a status and confidence;
- a scope;
- source IDs that resolve in `research/sources.json`;
- the evidence itself, quoted or summarized;
- limitations;
- a last-reviewed date.

The compatibility matrix references evidence IDs rather than restating claims. The validator rejects a matrix entry that points to a missing evidence entry, and an evidence entry that points to a missing source.

## Compatibility matrix

The matrix separates:

- **firmware** compatibility;
- **hardware** identity;
- **entry-point** availability;
- **USB** capabilities;
- **target identity** verification.

Each row has an `applies_to_target` value and an `in_scope` flag. A documented method that requires hardware modification is `VERIFIED` as a method but `in_scope: false` for this project. An undisclosed method is `UNKNOWN`, not `VERIFIED`.

The validator includes a guard against the specific failure mode this project is trying to avoid: a `VERIFIED` software-only entry point that applies to the OLED target. That combination must not appear without new, reviewed evidence.

## Entry-point matrix

[`research/entry-points.json`](../research/entry-points.json) is the detailed surface-by-surface record. It covers bootROM/RCM, recovery mode, browser/WebKit, PTP/MTP, local wireless, Bluetooth, game saves/cartridges, system services/sysmodules, kernel/TrustZone, and hardware fault injection/modchip.

Each surface records:

- the access required and whether it is software-only;
- whether the surface is reachable on the target;
- whether a public chain is documented for the exact target;
- the evidence status and the basis for it;
- whether the surface leads to Atmosphère;
- the evidence and source IDs that support the row.

The compatibility matrix references the detailed file through `entry_point_analysis` rather than duplicating the surfaces. The validator checks the summary counts, the target fields, the lead references, and the evidence/source cross-references.

## Reproducing the research state

```bash
# Validate schemas, cross-references, summary counts, and secret patterns
python3 scripts/validate_research.py
```

The validator checks:

- unique IDs and required fields;
- allowed status labels;
- source and evidence cross-references;
- target-field consistency between the entry-point and compatibility records;
- entry-point summary counts and lead/surface references;
- high-confidence secret patterns.

The Markdown renderer and mocked USB test suite are planned, not implemented. Until they exist, the JSON files are the source of truth and `docs/ENTRY-POINTS.md` is maintained alongside them by hand.

## Handling conflicts

When sources disagree:

1. Prefer the source closest to the component owner.
2. Prefer a newer maintained release over an older forum post.
3. Record the disagreement in the evidence entry's limitations.
4. Downgrade the status rather than choosing a convenient answer.
5. If the conflict cannot be resolved, use `UNKNOWN` or `PARTIALLY VERIFIED` and state what evidence would resolve it.

## Updating the research

A meaningful update should:

- add or revise a source with a retrieval date and snapshot;
- add or revise an evidence entry;
- update the entry-point and compatibility matrix references;
- update the readable docs;
- run the validator (and the mocked tests once implemented);
- record the change in the decision log if it changes a project-level conclusion.

Do not update the conclusion merely because a new firmware or CFW release exists. Ask whether the new release changes the **entry point** picture, not only the firmware-support picture.

## What this methodology does not do

- It does not prove that a private exploit does not exist.
- It does not audit every firmware binary or every hardware revision.
- It does not replace hands-on hardware validation.
- It does not provide legal advice about warranty, terms of service, or modification laws.
- It does not authorize state-changing work on the console.

Those limits are recorded in [`research/known-limitations.md`](../research/known-limitations.md).
