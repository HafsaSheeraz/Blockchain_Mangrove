# 09 — Tests and sprint acceptance gates

**PROPOSED tests; none executed by this documentation task.** Retain every [PB-1 test family](../playbook/14-testing-and-operations.md), including UI-01–28, SEC-01–08, DATA-01–02, GEO-01–04, POLICY-01–04, TASK-01–05, SUPPLY-01–04, EVID-01–08, CHECK-01–04, VERSION-01–04, REVIEW-01–04, MON-01–06, REWARD-01–06, PAY-01–06, CHAIN-01–12, NOTIF-01–04, REC-01–06, LEGACY-01–04, FLOW-01–04. PB-1 compound range entries are individual acceptance cases, not claims of existing test functions.

## PB-2 additional acceptance IDs

| ID | Test / mandatory assertion |
| --- | --- |
| P2-01 | Accept Completion D1, approve M3/M6, revoke D1, accept D2 with same Q. Old surveys remain bound D1 and cannot authorize D2 through API or direct RPC. |
| P2-02 | Use 2 confirmed supply sources summing claim quantity; reject duplicate/zero/wrong-project/unconfirmed links and >8; DB races cannot over reserve. Contract checks links/conflicts without pretending to enforce physical inventory. |
| P2-03 | Assignment persists worker/collector/stage roster and exact policy/site. Wrong roster cannot decide; replacement cancels authority/invalidates effective stage before re-review. |
| P2-04 | Configured task 1.25 hours at 500 minor/hour, scale 100 gives 125 atoms and 625 minor; Python/contract agree. Primary scale 1 rejects fractional seedlings and altered profile constants. |
| P2-05 | Race dispute vs simulator using two DB connections. One serialized result: hold-before-receipt prevents effect, or receipt-before-hold retained/disputed; never 2 receipts. |
| P2-06 | Local simulated receipt committed; chain assertion later reverts/reorgs. Receipt stays simulated_settled with audit discrepancy; no re-execution. |
| P2-07 | Logout after valid durable human command does not cancel consent; actual role/account revocation blocks queued signing/settlement. App membership grant alone cannot pretend chain role confirmed. |
| P2-08 | ABI/event selectors, three indexed limit, canonical JCS prefixes, command digest / deployment domain vectors match Python/TypeScript/Solidity. No guessed hashes in accepted demo. |
| P2-09 | Reset local chain to identical address/chainID with new deploymentGeneration: chain keys differ; same economic UUID has existing simulator receipt and cannot settle again. |
| P2-10 | Accurate M6 census 700/1000: reviewer approves report truthfulness, stage fails 75%, final reward ineligible. Never coerce false report rejection or manual eligibility. |
| P2-11 | Worker opens own dispute but cannot reverse own approval; independent V resolves field; P/O separately cancels authority; expired reviewer recovery works without admin approval bypass. |
| P2-12 | Claim/inspection/check/reviewer report exact typed FK/scope/purpose; review_visit does not enqueue self-review; changed input cannot reuse old CheckRun. |
| P2-13 | Project publish/lifecycle: role/site/policy required; suspend holds; technical S cannot business resume/close; new revision preserves old assignment/site. |
| P2-14 | Calendar 3/6 months with month end/leap years; no early visit; grace/late attestation. Primary boundary M3=800/1000 pass 799 fail; M6=750 pass 749 fail; Q900/live 720/live 675 earns 900000 minor after both pass. |
| P2-15 | Confirm physical batch 1100, consume 1000, revise declaration to 1100: available remains 100, not 1100. Reservations/corrections/accounting atomic and historical confirmation retained. |
| P2-16 | S05 authorized list/upload metadata/purpose binding, expired URL/quarantine/slot dedupe/over size/type mismatch; server hash not client claim. |
| P2-17 | N01–N20 correct recipient/scope/deep link; one inbox across modules; replay dedupes, role revocation hides private payload. |
| P2-18 | Authorized business report exact versions/four status dimensions/source modes/fiction label; CSV protected, other worker data redacted; no recalculation of One. |

## Direct-RPC negative suite

Run calls directly against deployed disposable local contract rather than mocking API guards. Map wrong project role/self-review to CHAIN-01/05; missingM3/M6 or low threshold to CHAIN-05/06; wrong primary profile/amount to CHAIN-03/06/P2-04; stale parent to P2-01; repeated event/new key duplicate authority to CHAIN-02/07; revoked/pause/cancelled prerequisites to CHAIN-08; ancillary audit “approval” attempt to CHAIN-10; unauthorized simulator to CHAIN-11; new deployment/economic retry to P2-09. Every failing transaction must leave workflow state unchanged; events emitted in reverted tx do not count.

## Test layers

Unit: typed DTO validators, conflict rules, exact amount/date/manifest algorithms, state reducers. Integration: real disposable PostgreSQL/PostGIS transactions, private local objects and local EVM; concurrent independent connections, not in-memory fake proof. Backend pytest + frontend Vitest/TestingLibrary remain existing tools; add Playwright harness with authorized Sprint 1 shell work, contract test toolchain in Sprint 5. Fake EE permitted only for labeled deterministic business tests; optional live EE smoke separate and never silently required for final field-based slice.

E2E grows each sprint through login → project → task → supply → claim → review → monitoring → authority → simulation, using real APIs and separate roles. A test fixture that directly sets approved/paid flags cannot establish end-to-end acceptance. Smaller task types share engine. Test expected domain output/errors, not implementation setters.

## Acceptance gates

| Gate / sprint | Work packages / acceptance evidence | Required test and manual focus |
| --- | --- | --- |
| G0 /0 | WP00; supported runtime/clean setup, sanitized examples, fresh legacy baseline | Existing backend/frontend test counts, lint/build exit codes; record oldvenv issue actual state, optional EE separate. No migrations/contracts. |
| G1 /1 | WP01/02; durable identity/scope/shell/outbox/inbox | SEC/DATA/NOTIF baseline, UI-01/02/07/09/10; login/denial/restart/job dedupe; legacy routes still work. |
| G2 /2 | WP03/04; register project/site/rules, assign/accept task | GEO/POLICY/TASK, UI-03/04/11–14/21/22; no-GMW/hole/pinned rules/independent roster. |
| G3 /3 | WP05/06; private evidence, supply, submitted claim | EVID/SUPPLY/VERSION, UI-05/15–18/23, P2-02/15/16;1100 confirmed → 1000 reserved, concurrency denial. |
| G4 /4 | WP07/08; checks and independent accepted planting | CHECK/REVIEW/VERSION/P2-12, UI-19/20/24; hard failure/correction/selfapproval/report purpose. |
| G5 /5 | WP09/10; actual role-restricted local chain + recovery | CHAIN-01–12/REC/P2-01/02/04/07–09; direct RPC negative cases, actual receipts, nonce/reset/outage. |
| G6 /6 | WP11/12; both scheduled field checkpoints | MON/P2-01/10/14; missing/failed/inconclusive/late pathways, original cohort, source provenance. |
| G7 /7 | WP13/14; final component formula, authority, simulator | REWARD/PAY/P2-05/06/09; missing either blocks; PKR10000 not 8200; duplicates/unknown/dispute blocked. |
| G8 /8 | WP15–17; allfive types, complete handoffs/report/demo | All applicable UI/domain/contract/E2E/legacy checks, restore, FLOW-01–04; truthful local run manifest/fiction label. |

All required checks for delivered scope must pass before recommending acceptance. Critical privacy/self-approval/stale-version/duplicate-reward/chain-prerequisite failures cannot be waived as “demo-only”. A non blocking optional live EE limitation may be explicitly documented, not fabricated as success. A blocked baseline stops dependent implementation until fixed or user authorizes a concretely scoped resolution; do not silently weaken tests.

## Future commands and reporting

Exact commands/workdirs/availability in [10](10-dev-environment-and-runbook.md). Preserve raw counts/exit codes and safe bounded logs; distinguish attempted, failed-to-start, passed, failed, skipped, notrun. Do not quote prior 139 passes as a new result. Compile/lint output is not security certification.

For each sprint report:1 what implemented;2 filesmodified;3 commands/results;4 incomplete items;5 manual steps/results;6 risks;7 recommended next sprint. User accepts in response; only then tracker ACCEPTED. Stop after report even if next sprint looks straightforward.
