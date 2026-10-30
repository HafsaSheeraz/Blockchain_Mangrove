# 01 — Decisions and requirements consistency

**PROPOSED implementation specification; reviewed 2026-10-30.** All 17 [PB-1 documents](../playbook/README.md) and four earlier audit/architecture documents were reviewed. Retain their detailed specification except where an issue below explicitly overrides it. Resolution here means resolved in planning, not a tested code fix.

## Locked requirements

| ID | Final requirement |
| --- | --- |
| D01 | Assign 1,000 seedlings. Independently accepted planting quantity Q is an integer, `0<Q<=1000`. Required approved field-survey decisions: PLANTING/M3/M6; M3>=80%, M6>=75%, denominator original accepted cohort Q. Missing/failed/disputed/unapproved/revoked/superseded mandatory inspection blocks final eligibility. |
| D01-F | Only if all requirements pass: `amount_minor=min(Q*1000,1000000)` PKR minor units. Never substitute surviving count. Q1000/live 900/live 820 earns fictional PKR10,000, not PKR8,200. Candidate amount may be shown with blockers, never as payable. |
| D01-C | Primary component is fictional final survival-linked reward, not a universal rule delaying wages. Other policies support separate completion/survival components and obligations. Those components disabled in primary fixture. |
| D02 | Solidity/local EVM; distinct role-bound fictional signer accounts managed by backend runner, no browser wallets. Backend and contract enforce roles/exact versions/milestones/reward authority/replay. Verifier and authorizer differ. No unrestricted publisher bypass. |
| D02-T | Runner controls multiple keys: compromise/collusion can forge attestations. Addresses do not prove independent custody, real identities or field truth. No token/NFT/real transfer/carbon credits; settlement explicitly simulated. |
| RQ-01 | One shared identity/org/project/task/claim/evidence/monitoring/inbox/audit model. |
| RQ-02 | Five configurable task types, plantation complete first; four smaller workflows use same machinery. |
| RQ-03 | Nursery confirms supply only; accepted work needs independent exact-version field review; self-approval blocked. |
| RQ-04 | M3/M6 from accepted planting business date plus 3/6 calendar months, clamp month-end; field route works when satellite insufficient. |
| RQ-05 | Preserve existing scientific algorithms/routes/APIs; business geometry preserves holes and allows no-GMW sites. |
| RQ-06 | Eligibility/human authority/chain confirmation/simulation remain separate. |
| RQ-07 | Explicit authorization and stop after every sprint; PB-2 creates docs/AGENTS only. |

Roles O/N/C/W/V/P/A/S retain meanings in [permissions](../playbook/03-permissions.md). RQ labels are new PB-2 trace IDs. PB-1 used screen/API/test/backlog IDs, not numbered product requirements; work packages cite those actual IDs.

## Consistency report

Critical = invalid authority/duplicate-reward risk; High = correct-implementation blocker; Medium = UX/scope/operational ambiguity. All statuses: **RESOLVED IN SPECIFICATION**.

| Issue | Severity | Affected source | Resolution / PB-2 authority |
| --- | --- | --- | --- |
| IC-01 | High | PB-1 16,13 B00; earlier 04 | D01/D02 locked; D03 not defined, remove as execution dependency. |
| IC-02 | Critical | PB-1 02/05/06/15 | Accepted Q drives formula; survival counts gate only. D01-F/[11](11-demo-data-and-walkthrough.md). |
| IC-03 | High | PB-1 02/06/07/15 early ±14-day window | E01: no early inspection. Earliest valid observation is exact due date;14-day grace after due; late reason and independent acceptance required after grace. Reminder 14 days before. [07](07-integrated-workflow-sequences.md). |
| IC-04 | Critical | PB-1 06 stage pointers | Follow-ups pin exact parent Completion decision; equal replacement count cannot revive old M3/M6. [06](06-blockchain-implementation-plan.md), P2-01. |
| IC-05 | Critical | PB-1 04 multiple allocations vs 06 scalar supply | Subject uses bounded 1–8 unique SupplyLinks + allocation-manifest commitment; on-chain scope/conflicts/effectiveness; DB inventory sums. [05](05-database-and-migration-order.md)/[06](06-blockchain-implementation-plan.md), P2-02. |
| IC-06 | High | PB-1 04 missing reviewer/collector columns vs 06 | Explicit stage roster/history, collector and parent-decision FKs. [05](05-database-and-migration-order.md), P2-03. |
| IC-07 | High | PB-1 A38/A39 and N04 assigned C | O chooses project default C; declaration snapshots it; exact C required by API/chain; N cannot select itself. [04](04-screen-api-event-matrix.md)/[06](06-blockchain-implementation-plan.md). |
| IC-08 | High | PB-1 04 migration order/FK cycles | Stable parents before revisions; nullable current pointers then explicit FK alterations; audit/outbox base Sprint 1. [05](05-database-and-migration-order.md). |
| IC-09 | High | PB-1 03 assisted drafts vs 05 W-only writes | Initial delivery has no coordinator-assisted claim writes. O assigns/reads; W authors/submits. [03](03-module-build-specifications.md). |
| IC-10 | High | PB-1 S05 list and task/inspection detail gaps | Add A79–A84 for missing reads/lifecycle/report; inspection corrections extend A46. [04](04-screen-api-event-matrix.md). |
| IC-11 | High | PB-1 05 abbreviated DTOs | Define projection fields/nullability/ETags, upload metadata, review purpose and request/response mapping. [04](04-screen-api-event-matrix.md). |
| IC-12 | Critical | PB-1 06 uint 32 vs fractional task quantities | quantityAtoms/unitScale, integer parity/rounding; immutable taskType/requiresSupply policy fields. [06](06-blockchain-implementation-plan.md), P2-04. |
| IC-13 | Critical | PB-1 04/06/08 dispute/dispatch race | Lock obligation, final local receipt insertion and dependency recheck atomic. Stable economic key across all retries. [05](05-database-and-migration-order.md)/[07](07-integrated-workflow-sequences.md), P2-05. |
| IC-14 | High | PB-1 06 assertion after authority revoked | Local simulated receipt survives later chain-audit failure; discrepancy/hold and ancillary audit, never re-settle. [06](06-blockchain-implementation-plan.md), P2-06. |
| IC-15 | High | PB-1 03/06 session expiry vs durable commands | Logout does not revoke valid durable consent; current account/role/subject/hold rechecked. Revocation immediately holds; chain grants must confirm. [02](02-implementation-architecture.md), P2-07. |
| IC-16 | High | PB-1 06 named events/domain incomplete | K registry, typed events/errors/ABI delta and reset-generation domain. [06](06-blockchain-implementation-plan.md), P2-08. |
| IC-17 | High | PB-1 06/08 reset dedupe | Economic obligation UUID independent of chain deployment; chain key deployment-scoped; resetting chain cannot pay again. [06](06-blockchain-implementation-plan.md), P2-09. |
| IC-18 | High | PB-1 policy/site persistence before evidence | Canonical structured agreement and raw site JSON stored in DB; optional PDF/object copy later; no Sprint 2 → 3 circular dependency. [05](05-database-and-migration-order.md). |
| IC-19 | Medium | PB-1 accepted-work/final-result status | verified_complete means accepted work only. Accepted accurate low-survival survey: review approved, milestone failed, eligibility ineligible. [07](07-integrated-workflow-sequences.md), P2-10. |
| IC-20 | High | PB-1 13 late inbox/audit dependencies | Audit/outbox/minimal inbox Sprint 1; feature handoffs tested progressively, polish Sprint 8. [08](08-sprint-backlog-and-dependencies.md). |
| IC-21 | Medium | Earlier registrar/publisher proposal vsPB-1 | Organization publication is registration; no extra registrar or publisher-only workflow; preserve PB-1 API IDs over earlier illustrative aliases. |
| IC-22 | High | PB-1 A70 V/P joint actor ambiguity | V resolves field finding; P/O cancels authority; commands record each actor; hold clears only after prerequisites reconciled. [07](07-integrated-workflow-sequences.md), P2-11. |
| IC-23 | Medium | PB-1 A32 “URL or stream” and caps | Fix 200 JSON signed URL/expiry; safe preview; exact form caps/error codes. [04](04-screen-api-event-matrix.md). |
| IC-24 | High | PB-1 recursive visits/checks/current decision | Exactly-one typed subject FK, immutable purpose/check input, verifier visit is decision evidence, never self-reviewed subject. [05](05-database-and-migration-order.md), P2-12. |
| IC-25 | Medium | PB-1 broad stack/tool versions | One modular backend and DB queue; no Redis/Celery/microservices/offline/wallet scope. Select stable compatible versions only in authorized Sprint 0. [10](10-dev-environment-and-runbook.md). |
| IC-26 | High | Earlier source/documentation discrepancies | EE auth≠app login; cache hash≠blockchain proof; timeout≠work cancellation; preserve warnings/holes limitation/historical tests. [02](02-implementation-architecture.md). |
| IC-27 | High | PB-1 06 trusted minimum timestamps | Contract computes exact Gregorian M3/M6 dates from the accepted planting subject; no caller-supplied minimum date can weaken the calendar requirement. [06](06-blockchain-implementation-plan.md), P2-14. |
| IC-28 | Medium | PB-1 human state includes chain-derived labels | Persist human_state independently; approved_pending_chain/authorized are derived display states only, with raw chain state retained. [04](04-screen-api-event-matrix.md). |

Engineering defaults: E01 due-to-due+14 grace; E02 original cohort census, missing counts not alive; E03 floor to minor unit for fractional quantity pricing (primary integer exact); E04 canonical local receipt+two subsequent locally mined blocks, not public finality; E05 same-origin sessions/CSRF, no public signup; E06 private versioned local objects/in-app inbox; E07 immutable primary policy profile, other component policies allowed; E08 one seeded org, no org signup/CRUD UX; E09 distinct fixed user → local actor binding; E10 explicit sprint stop. None alters locked product policy.

No outstanding product decision remains. Tool/service availability and fresh baseline are Sprint 0 readiness work, not a reason to mark an unstarted sprint BLOCKED. No security or scientific assurance follows from documentation alone.
