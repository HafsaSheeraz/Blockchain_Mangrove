# 07 — Evidence, automatic checks and monitoring

**PROPOSED.** Mangrove One's existing analysis is reused for context; private uploads, immutable evidence, checks and milestone inspection are new.

## Evidence protocol

1. Authorized form requests A29 upload slot for its project. Server limits object count, byte size and allowed category/MIME; proposes JPEG/PNG/PDF, maximum 10 MiB/file and 10 files/submission. Random storage keys and immutable object versions; no client path interpolation. Unused slot expires after 15 minutes.
2. Browser sends bytes to private signed slot with required headers. A30 complete references object version; server independently reads bytes, detects size/MIME, hashes SHA-256 and validates structure. Slot cannot finalize twice into different bytes. Quarantine pending validation; malformed image/PDF or executable/polyglot mismatch rejected. Antivirus integration is optional hardening, not silently claimed present.
3. EvidenceVersion records server hash plus untrusted capture/EXIF declarations separately. Do not strip/transform originals in place; generate redacted preview as another version linked to original. Downloads require fresh authorization and short expiry/no-store.
4. A33 assembles category/order/exact version IDs; A34 seals a canonical manifest containing project/subject purpose, version IDs/hashes, detected MIME/sizes and declared metadata with provenance. Sealed sets immutable. Worker submission A28 and field decision A43 send the digest as a stale-input check; backend recomputes/compares stored canonical bytes.
5. Replace a rejected/wrong upload with a new EvidenceVersion and new set/subject revision. Old evidence remains attached to historical decisions. Integrity recheck A63 rereads object version and compares raw-byte hash; corruption holds affected decisions/obligations and alerts authorized reviewers/operations.

Use RFC 8785 JCS UTF-8 canonical JSON for structured commitments. Quantities/measurements are canonical decimal **strings**; integer counts/money bounded below JavaScript's exact-number limit; arrays have specified deterministic ordering. JCS defines invariant JSON serialization, not a geometry canonicalization or a truth verifier. [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).

`fileDigest = SHA256(original bytes)`; `setDigest = SHA256("Mangrove/EvidenceSet/PB1\0" || canonicalManifest)`; `decisionDigest = SHA256("Mangrove/Decision/PB1\0" || canonicalDecision)`. Store prefix/schema and canonical bytes. Polygon hash commits accepted normalized ring sequence/precision; rotated/reversed equivalent rings may hash differently intentionally unless an explicitly versioned geometry normalization is adopted. Never use current cache keys as evidence hashes.

Decision manifest binds subject/claim revision and evidence digest, policy/site/task-type versions, checks run/findings resolutions, field inspection revision/evidence, reviewer actor commitment/outcome/accepted measures/times. Add a random manifest nonce for any guessable private fields; only the digest goes on-chain. Access permission remains required to reveal canonical preimage.

## Required evidence by plantation stage

| Stage | Required set categories and validation |
| --- | --- |
| Fictional contract | Synthetic agreement PDF or canonical structured agreement export; policy version/approval history. |
| Supply declaration | Nursery batch log, available-count record, nursery overview image, operator/date. Confirmation adds distinct confirmer visit/count report. |
| Plantation claim | Planting register, plot/row photo, site overview photo, work date/quantity, species/cohort code, supply allocation links; optional GPS with accuracy/source. |
| Planting field decision | Reviewer field-visit report/photographs, accepted count and method, visit time/location, conflict attestation and explicit flag resolutions. |
| M3/M6 | Field census sheet, live/dead/missing counts tied to original cohort, plot photos, observer date/method, environmental context sufficiency and independent review field report. |
| Authorization/settlement | Frozen eligibility calculation and human approval reason; simulator receipt is generated, never uploaded as proof of real payment. |

Template minima are bounded configurable rules; they are fictional university-demo requirements, not attributed to DBC or a certification standard.

## Automatic-check pipeline

Check worker reads a sealed immutable input and writes one versioned CheckRun. Profile steps: scope/assignment ownership → required fields/unit/quantity/date → site topology/bounds → evidence validation/integrity/categories → policy/version consistency → nursery allocation (plantation only) → duplicate/overlap/metadata flags. Store findings and input digest; no checker mutates evidence or awards approval.

| Check | Result / consequence |
| --- | --- |
| Missing required category, invalid object/hash, zero/invalid count, wrong project/version | Hard blocked; cannot queue field decision until corrected in new revision. |
| Unconfirmed or insufficient supply; aggregate reservation race | Transaction rejects submission or hard block; organization/nursery handoff, never mark as planted. |
| Self-intersection, dropped hole, invalid coordinate/date interval/oversized AOI | Hard blocked. Business AOI may have no GMW mangroves; this is not a blocker. |
| Repeated raw evidence hash in unrelated claims | Soft flag with matches visible only within authorized scope; reviewer investigates. Not automatic fraud proof. |
| GPS outside AOI/tolerance, low accuracy, missing EXIF/date discrepancy | Soft flag unless policy explicitly requires a reliable location; independent field visit and reason required. |
| Site intersects old GMW / GEDI coverage | Context only, `sufficient`, `insufficient`, `no_data` or `unavailable`. No planting/survival decision generated. |
| Checker/provider failure | `error`, retry safe check run after dependency recovery; never turn into `passed`. |

Worker receives failed-check detail and can create corrected revision. Verifier receives passed/flagged submissions only once required hard checks pass. Soft flags must have per-finding resolution in A43. After input changes, old checks cannot be reused by matching only the assignment ID.

## 3/6-month monitoring lifecycle

Milestone requirements are created deterministically when the assignment binds its published policy; due dates become fixed when planting is accepted. Do not create duplicate M3/M6 on repeated approval events. Base date is the accepted planting business date, not chain mining/submission date. Existing fixture records historical observation dates; current record/anchor timestamps stay current.

At due-14 days notify collector/worker and organization; at due date notify assigned collector/verifier; at due+14 days mark overdue if no accepted observation and notify organization/verifier. Unique schedule key prevents repeated notifications every poll. Inspection can be recorded late with reason; acceptance requires policy's late-review rule. No automatic waiver or assumed 100% survival.

PB-1 census denominator is original accepted planted count; live+dead+missing must equal it, and thresholds compare integer cross-products, avoiding float rounding. If sample method is later enabled, policy must define sampling frame/denominator/uncertainty and new check profile; a sample proportion cannot silently replace a census measure under the same policy.

If satellite context is insufficient, collector selects `satellite_insufficient`, records why and submits field census/evidence. Independent field reviewer visits/reviews and records a decision. That route is fully supported, not a fallback that falsely upgrades satellite confidence. `context_status` and `milestone_passed` remain separate fields.

## GIS adapter behavior

A64 launches a bounded job against immutable site version and explicit region/date config, calling existing Python scientific services without changing coefficients/masks. Save exact request/result, source modes/assets, scientific fingerprint, code revision, warnings/assumptions and bytes of any accepted export. Private source asset access may fail; preserve `unavailable` error safely and allow field work to continue.

Existing `/analysis` remains its current frontend; proposed contextual links include site/milestone parameters consumed only by a new adapter page/saved snapshot panel, not an undocumented change to the science endpoint. New project map can reuse raster layers and formatters unchanged but must not pass business geometry through the old hole-dropping normalizer. Preserve OSM attribution and descriptor expiry; temporary tile URLs never enter sealed scientific/evidence manifests.

No imagery model estimates seedling survival in PB-1. No satellite pixel/shot count is a verified seedling count, payment quantity or certified carbon credit. Tests EVID-01–EVID-08 and MON-01–MON-06 enforce these boundaries.
