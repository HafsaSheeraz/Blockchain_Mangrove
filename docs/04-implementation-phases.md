# 04 — Implementation phases and approval decisions

Status: **awaiting user approval**. This document schedules proposed work; it does not authorize it. The current task ends with these four documents. Existing application code/configuration has not been modified.

Read together: [audit](01-repository-audit.md), [architecture and shared model](02-system-architecture.md), [gap/risk register](03-gap-analysis.md).

## 1. Ordered delivery plan

Implement one demonstrable vertical slice at a time. Preserve current environmental analysis and public API contracts while introducing business behavior through additive modules. No calendar estimate is asserted until scope, team availability and university assessment requirements are known.

| Phase | Proposed work / deliverable | Dependency and exit evidence |
| --- | --- | --- |
| 0 — Decisions and reproducible baseline | Resolve approval register below; confirm naming/demo disclosures and blockchain assessment expectations. Repair local Python environment without discarding existing user files, select supported Node/Python versions, run current tests, document clean setup, track sanitized environment templates, select compatible dependency/tool versions. | User approves architecture/scope first. Exit: agreed decisions, existing frontend and backend baseline results, clean-clone setup and separate treatment of live EE access. Do not call backend tests passed until actually executed. |
| 1 — Shared foundation | Add PostgreSQL/PostGIS and migrations, identity/session/RBAC/project memberships, shared IDs/timestamps, audit log, idempotency, private object-store adapter and isolated fictional seeds. Add proposed module routing/navigation. | Phase 0. Exit: data survives restart, migrations up/down or documented forward recovery, access denial/CSRF checks, distinct fictional actors, no app secret in frontend; `/analysis` regression intact. |
| 2 — Registration and environmental context | Implement Project/ProjectRevision registration, immutable AOIVersion, business-specific AOI editor preserving rings and allowing non-mangrove sites. Wrap existing GIS services to store optional AnalysisSnapshots, exact provenance and persisted exports. | Phase 1. Exit: register/reject/request changes on exact revision; AOI changes create a new version; old snapshot persists; live/unavailable/fixture modes clearly labeled. EE failure does not destroy or prevent registration. |
| 3 — Evidence, nursery and claims | Complete upload validation, EvidenceVersion/EvidenceSet sealing/integrity checks; nursery batches/independent confirmations/allocations; claim revisions; assigned independent review; correction/reversal paths. | Phase 2 plus evidence foundation. Exit: submit/approve/reject/changes-requested demonstrated, actor conflict blocked, evidence mutation detectable, stock allocation race prevented, previous approvals bound to previous revisions. |
| 4 — Local blockchain audit | Implement/test minimal audit registry and canonical digest vectors, local EVM deployment, restricted publisher, DB outbox/worker leases, receipt/finality/reorg reconciliation and scoped audit timeline. Backfill earlier demo audit events explicitly with current anchor time. | Phases 1–3 supply stable event schemas; hashing contract is frozen before contract deployment. Exit: independently recompute digest and match local-chain receipt, duplicate event rejected/idempotent, restart/retry/unknown-tx recovery, chain outage visible. No historical event is falsely shown anchored at its original business time. |
| 5 — Steward tasks and follow-up | Task assignment/completion referencing Trust ClaimRevision, worker views, milestone schedules/observations and independent decisions. | Phases 2–4; decisions authoritative in Trust. Exit: worker sees only assigned/private scope, one linked completion claim, policy-required observations demonstrable, overdue/missing/rejected milestones clearly block reward requirements. |
| 6 — Eligibility and simulated payments | Add immutable fictional RewardPolicyVersion, explainable server calculations, holds/revocations, separate PaymentAuthorization, idempotent simulated attempts/status/receipts. Apply approved anchor-finality gate. | Phase 5 and approved policy. Exit: verified completion + required verified follow-up → eligible → independent authorization → simulated_paid. Rejection, changed evidence, chain-pending, duplicate retry and disputed approval cases block/hold appropriately. No real money moves. |
| 7 — Integrated university demo | End-to-end integration tests, CI, migration/backup/restore checks, nested-route hosting, secret/log review, runbook, repeatable fictional seed/reset procedure and scenario walkthrough. Optional public testnet deployment only if approved. | Phases 0–6. Exit: clean setup + saved demo path with EE unavailable; full success/failure walkthrough; evidence/anchor integrity check; recoverable worker restart; explicit simulated payment labels and case-study disclosure. |

A logical foundation table may be created earlier than its UI. Do not implement reward/payment rules ahead of the verification/evidence versions they depend on. Avoid rebuilding the GIS pipeline to make the workflow demo appear complete.

### Minimum successful demonstration

One fictional coordinator registers a fictional Sindh project against a versioned polygon. A second fictional participant confirms nursery stock. A worker completes a task and submits a claim with sealed synthetic evidence. An independent verifier approves that revision, then approves the required follow-up observations. Audit commitments reach the configured chain confirmation/finality state. A separate authorizer approves the frozen fictional reward; the simulator reports simulated payment and a receipt. An auditor compares an evidence digest to the recorded commitment.

Also demonstrate: a rejected claim; a revised evidence version that needs re-review; missing follow-up preventing eligibility; an unauthorized actor denied access; and a chain/payment retry that produces no duplicate obligation. Display historical event time, anchor publication/confirmation time and payment-simulator time separately.

## 2. Approval register

User-provided constraints already fixed: analysis/documentation only for this task; reuse Mangrove One for GIS; fictional users/contracts/rates/activities; Delta Blue Carbon is public inspiration with no partnership/private operational data. These do not need reconfirmation.

The following decisions **do** need approval before dependent implementation. Recommendations are proposed defaults, not accepted decisions.

| ID | Decision requiring approval | Recommended default and implication |
| --- | --- | --- |
| A01 | Architecture and hosting scope | Extend React/FastAPI as a modular monolith; shared PostgreSQL/PostGIS, private object storage, separate backend worker. Requires new local/deployment services and configuration. Keep current GIS routes stable. |
| A02 | Product naming and navigation | Present Mangrove One (existing Carbon Explorer), MangroveTrust and MangroveSteward as modules of one educational platform. Approve whether old public branding should change later. |
| A03 | Blockchain assessment requirement | Start with a minimal backend-published Solidity audit registry. This proves committed data integrity/publisher attribution, not independently wallet-signed human decisions. If the rubric requires direct user wallets, contract-enforced workflow or payout, select that scope before implementation. |
| A04 | Chain environment and tooling | Local EVM first, one contract toolchain (Hardhat proposed); optional Sepolia later after checking availability. Approve whether a public explorer link is required for assessment. No mainnet funds or token issuance. |
| A05 | Identity and separation of duties | Seeded password/session accounts with project roles; distinct submitter, independent verifier, worker/payee and payment authorizer. Workers do not need wallets initially. Approve whether one coordinator may also administer users; sensitive self-approval remains blocked. |
| A06 | Registration and nursery confirmation authority | Assigned registrar reviews project revision; distinct nursery confirmer reviews declared batches; independent verifier handles claims/milestones. Approve required role assignments, conflict rules and nursery quantity reservation/release policy. |
| A07 | Geometry and geographic scope | Initial business AOI is valid Polygon with preserved holes; no MultiPolygon initially. Fictional Sindh case sites, not claimed DBC boundaries. Allow degraded sites outside current GMW coverage; approve maximum project area and extent policy. |
| A08 | Evidence and privacy | Private originals, synthetic/sample-safe files, bounded JPEG/PNG/PDF uploads proposed; server hashes and immutable sealed manifests; redacted audit view. Approve evidence checklist per activity, allowed types/size, retention/deletion and public-versus-authenticated audit visibility. No real national IDs/bank details/worker photos. |
| A09 | Eligibility and follow-up business rules | Require independently approved work and all policy-required milestones. Suggested demo checkpoints: 30 and 90 days after completion, with seeded historical dates or a clearly labeled demo clock. Approve observation measures, survival/quality thresholds, grace periods, tranche rules and dispute handling. These are fictional policy choices, not DBC practice. |
| A10 | Fictional reward amounts and units | Fixed policy-version rates, explicit units/caps and integer minor-unit PKR amounts; no linkage to estimated carbon stocks. Approve exact fictional rates, quantity rounding, maximum obligations and whether follow-up earns a separate tranche. No rates are assumed approved here. |
| A11 | Anchor gate and finality | Allow business submission/review while anchors pending; hold payment authorization until required verification anchors meet configured finality. Approve exact local/public-chain finality criteria and outage behavior. Mined/confirmed/finalized labels must be distinct. |
| A12 | Payment scope | Simulated adapter only, status `simulated_paid`, no bank/crypto transfer. Approve whether showing a test-token transfer is an additional assessment requirement; that would require a separately designed payment contract/security model. |
| A13 | GIS availability and offline demo | Existing live EE remains optional context. Permit saved snapshots/fixtures explicitly labeled by mode for repeatable demo. Approve access to runtime EE setup during implementation; successful `/ready` alone is insufficient. No new scientific model or carbon-credit certification. |
| A14 | Resource provisioning and costs | Local PostgreSQL/PostGIS + object-store service + local chain for development; select hosting/account/budget before any remote provisioning or paid service use. Existing deployment artifacts do not establish available accounts/entitlements. |
| A15 | Delivery target and exclusions | Online responsive demo, one coherent seeded vertical slice first. Confirm deadline/team constraints and whether offline capture, multilingual UI, maps on mobile, external identity provider or public deployment are assessment necessities. Otherwise defer them. |

## 3. Decisions deliberately not inferred from repository

The repository does not establish legal restoration rights, DBC project boundaries, real nursery operators or confirmation practices, official planting evidence requirements, real wages/contracts, survival thresholds, an accredited verifier, any wallet ownership, deployed contract address, database provider, funded account or permission to make real payments. None of these can be derived from the current GIS AOI catalog or its carbon results.

The public case-study source supports context only. It does not validate this proposed workflow. [Delta Blue Carbon public overview](https://deltabluecarbon.com/).

## 4. Change and acceptance controls

- Future schema/API changes should be additive first, with migrations and rollback/recovery notes. New business DTOs should not overload existing AnalysisResults or StudyAreaInfo.
- Keep current scientific coefficients/masks/output semantics stable unless a separate approved change revisits them. Correct misleading documentation/UI language as an explicit maintenance item, not as an undocumented scientific rewrite.
- Pin selected dependencies after compatibility checks; do not choose versions from guesses or treat the existing Router advisory paragraph as current assurance.
- Require meaningful authorization, concurrency, immutability, outbox recovery and simulated-payment tests from the gap analysis. Report external-service tests separately from mocked tests.
- Label all fixture-backed outputs and all simulated payments. Preserve exact evidence versions used for submitted decisions and make failures/no-data states visible.
- Any optional public testnet or deployment work follows the approved scope, with reviewable configuration and no secrets in commits or browser builds.

## 5. Current completion and stop point

Completed in this task: four architecture documents and an evidence-based repository review; frontend baseline 139 tests passed. Backend baseline remains unverified because the existing venv cannot launch and available Python lacks pytest. No environment repair, migration, dependency installation, application-code change, smart contract deployment, blockchain transaction or payment was performed.

**Approval requested:** approve or amend A01–A15, especially blockchain proof expectations (A03), follow-up/reward rules (A09–A10), and simulated payment scope (A12). Implementation starts only after your approval; phase 0 then resolves any remaining scope/environment decisions.
