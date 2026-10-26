# 14 — Testing plan and operational acceptance

**PROPOSED future tests/runbooks.** This delivery validates documentation only; no app/contract implementation or new feature test pass is claimed. Historical baseline is 139 frontend tests passed, backend environment unable to run. Tests below are meaningful acceptance contracts for later work.

## Acceptance catalog

| ID range | Required cases |
| --- | --- |
| UI-01–UI-10 | S01–S10 respectively: authentication, dashboard, projects, workspace, evidence, monitoring, inbox, audit, access, operations; G accessibility/loading/empty/error/409/responsive cases on each. |
| UI-11–UI-20 | T01–T10 respectively: project/site/rules/task/nursery/catalog/detail/review workflows, all field/action/error/correction behavior from screen cards. |
| UI-21–UI-28 | W01–W08 respectively: my tasks, assignment, submission, inspection, eligibility list/detail, authority, settlement; exact four-dimension statuses. |
| SEC-01 | Anonymous/bootstrap/login/logout/expiry, cookie/token rotation, generic failure, safe return URL. |
| SEC-02 | CSRF+Origin on all mutations, rate limits, no credentials in logs/browser bundle. |
| SEC-03 | Every list/detail/download cross-org/project/worker access denial, including guessed UUIDs and filters. |
| SEC-04 | Submitter/worker/collector/supply actor/verifier/authorizer conflicts at assignment and action; multi-role person cannot self-approve. |
| SEC-05 | Signed upload/download expiry/object-key/type restrictions; original vs redacted scope; evidence usage without leaks. |
| SEC-06 | Own notification reads only; recipient authorization after membership revoke; safe deep links. |
| SEC-07 | Revoked role/account/session at queued signer/settlement execution; admin no business bypass; reviewer replacement safe. |
| SEC-08 | Forged actor/status/amount/hash fields and cross-project FKs rejected; no secrets in serialized errors. |
| DATA-01 | Published immutability, unique version/obligation/event constraints and FK scope; direct repository illegal edit rejected. |
| DATA-02 | Transaction rollback leaves no outbox/intents; sorted locks avoid inventory/obligation races; deadlock retry bounded. |
| GEO-01–04 | Ring/hole preservation end-to-end; malformed/topology/nonfinite/oversized input rejected; geodesic area cap; no-GMW business site accepted and old site remains pinned. |
| POLICY-01–04 | Immutable policy binding; allowlisted task schema; completion/survival/final components independent; mask/threshold/formula/cap/currency invalid inputs and exact arithmetic parity. |
| TASK-01–05 | Each of the five types through shared assign→submit→check→review→eligibility machinery, with type-appropriate fields/supply and correction. Plantation is full M3/M6 flow; other four smaller. |
| SUPPLY-01 | Declaration vs confirmation vs planting distinct; independent confirmer required. |
| SUPPLY-02 | Submit against unconfirmed/exhausted/wrong-project stock fails. |
| SUPPLY-03 | Concurrent claims cannot over-reserve stock; consumed quantity, partial acceptance, rejection/cancellation accounted correctly. |
| SUPPLY-04 | Revision transfer/release atomic; approved stock not silently recycled; chain supply commitment no milestone bit. |
| EVID-01–04 | Bounded upload/quarantine/retry; server MIME/hash detection; sealed exact manifest/JCS vectors; new version preserves original bytes and references. |
| EVID-05–08 | Scope/redaction/metadata trust; malicious filename/parser content/size; expired/lost object recovery; corrupted file digest mismatch holds dependents and cannot match old commitment. |
| CHECK-01–04 | Hard block, soft flagged-with-resolution, provider error vs success, stale input/profile rerun. No automatic check approves field work. |
| VERSION-01–04 | One shared claim across modules; exact claim/evidence/site/policy/check/field-report approval; changed evidence needs new review; stale/concurrent corrections/revocations hold obligations without duplicate rewards. |
| REVIEW-01–04 | Assigned independent review; visit/report required; changes-requested/rejected/corrected cycle; reviewer reassignment/revoked key invalidates future use but keeps historical attribution. |
| MON-01 | Calendar months (Jan31→Apr30/Jul31, leap-year cases), dates in Asia/Karachi and separate record/visit/anchor times. |
| MON-02 | Scheduler one approaching/due/overdue notification each; no repeated unchanged reminders. |
| MON-03 | Original census denominator; live+dead+missing and bps cross-multiplication; replacements separate cohort. |
| MON-04 | Independent M3/M6 field decision; insufficient satellite context supported; no automated survival pass. |
| MON-05 | Missing/late/rejected inspections block exact required component; late reason/window explicitly reviewed. |
| MON-06 | Revised observation cannot reuse prior checks/decision; context errors/no-data do not erase field records. |
| REWARD-01–03 | Primary final requires planting+M3+M6; missing/revoked dependency blocks; separate completion/survival component produces distinct obligation and disabled components not payable. |
| REWARD-04–06 | Integer/Decimal amount/cap/rounding parity, unique obligation under concurrent evaluation/revisions, authorization rechecks exact current policy/decision set and holds. |
| PAY-01–03 | Distinct authorizer, human approval ≠ chain authority, no dispatch without current confirmed chain/isExecutable and no holds. |
| PAY-04–06 | Concurrent retry one obligation-key simulator receipt; unknown outcome reconciled before retry; already-simulated settlement disputed/corrected without erasure/fake refund; settlement/audit pending split. |
| CHAIN-01 | Direct unauthorized global/project role calls revert; bound actor cannot be rebound or used in another project. |
| CHAIN-02 | Fresh event/subject/decision/auth keys, duplicate event reverts, conflicting digest quarantined, deployment-domain isolation. |
| CHAIN-03 | Published policy immutable; masks/components bounded; no token/value entrypoints. |
| CHAIN-04 | Supply declaration/confirmation distinct roles; cannot satisfy planting; wrong assignment/worker/source rejected. |
| CHAIN-05 | Direct RPC missing milestone, wrong reviewer, self-approval or stale subject/evidence/prerequisite pointer rejected. |
| CHAIN-06 | Too-early/future inspection/cohort mismatch/threshold failure and wrong amount/cap/currency rejected. |
| CHAIN-07 | One active authority per obligation; cancelled/reissued authorities cannot generate duplicate simulated obligation. |
| CHAIN-08 | Revocation/pause/cancel/reviewer-role withdrawal makes isExecutable false; recovery/reassignment retains old history. |
| CHAIN-09 | Canonical receipt status/depth and block hash; tx hash alone never confirmed; orphaned chain holds downstream. |
| CHAIN-10 | ABI/JCS/SHA-256/keccak vectors and event field decoding; ancillary audit cannot set approval bits. |
| CHAIN-11 | Only simulator service records one simulated receipt after valid authority; records no actual financial transfer. |
| CHAIN-12 | Bounded storage/loops, numeric overflow edges, repeated direct-call adversarial transitions and state-machine invariant/fuzz tests. |
| NOTIF-01–04 | Event/template/recipient dedupe, rollback/delivery restart, correct handoff/deep link/privacy, read-state independence and unchanged reminder suppression. |
| REC-01–06 | DB commit/crash; post-send/pre-receipt crash; unknown tx/nonce/event reconciliation; review/dispute/authority race; simulator success before audit crash; deployment reset/DB+object restore. |
| LEGACY-01–04 | Existing frontend/backend regression; scientific DTO/routes unchanged; science modes/warnings/export semantics intact; new adapter context never changes reward or fakes live/no-data values. |
| FLOW-01 | Full primary scenario with separate actors, exact digests, both follow-ups, final authority and simulated receipt. |
| FLOW-02 | Changes requested + corrected evidence + re-review, prior version preserved. |
| FLOW-03 | Insufficient satellite → field pass, missing/failing follow-up → no final reward. |
| FLOW-04 | Chain outage/reorg/dispute/unknown simulator → truthful holds/no duplicate reward. |

## Test layers and tooling

Unit: date/calendar logic, schema/quantity/unit constraints, component evaluator, canonical digest vectors, conflict predicates and status reducers. Frontend Vitest/Testing Library cover observable UI behavior and client validation, not arbitrary implementation internals. Backend pytest tests domain services and authorized HTTP routes.

Integration: disposable real PostgreSQL/PostGIS transactions, private local object storage and local EVM; fake external EE only for deterministic business tests, clearly distinguished from optional live EE smoke. Contract tests execute direct calls independent of FastAPI to prove the chain itself enforces guards. Compare integer reward calculations between Python and Solidity against identical fixtures.

E2E: browser automation through each role login and screen cards, including direct unauthorized API requests. Use isolated namespace/deployment/object prefix per run. Run concurrency tests with independent DB connections/processes; a single-thread in-memory fake cannot establish allocation/duplicate-payment protection. Property/state-machine tests assert never: approval on stale evidence, authorization without required active decisions, two settled receipts for one obligation.

CI after implementation: supported runtime setup → dependency lock install → migrations → backend/frontend regression → contract tests → domain integration → critical E2E → build/lint. Tests may use local services; no secret/private EE asset required for default pipeline. Do not repeat broad suites without a reason once the change's required checks pass.

## Runtime and recovery runbook specification

1. Validate sanitized config and runtime versions. Start DB/PostGIS and object store; apply migrations; start local EVM and record new deployment identity/code hash; bind seeded actors/project roles through controlled setup; start FastAPI, workers, scheduler and SPA/proxy. No populated secret files in Git.
2. Health: existing `/health` liveness and `/ready` config-only behavior remain documented. Proposed business health checks (e.g. `/api/v1/system/readiness`) check DB/schema/object-store/worker heartbeat; chain degradation is explicit capability status. Do not make every page unavailable because EE is down. Health payload contains no credential/endpoint secrets; ops-only diagnostics for details.
3. Observe outbox lag, stale leases, queue errors, unknown tx, confirmation lag, simulator unknowns and audit/inbox delivery. Safe correlation IDs link requests/events/commands/attempts. Alert only meaningful changes/blocking conditions, not every scheduler poll.
4. Snapshot/backup DB and immutable object versions/manifests with deployment registry. Restore into isolated namespace; validate object hashes and replay/read chain receipts against matching deployment. A fresh chain needs new deployment identity and explicit re-publication, not a claim of old confirmations.
5. For unknown chain outcome: inspect stored command digest/nonce/signed tx hash, query canonical event/receipt, reconcile; retry only proven absent compatible command. For unknown simulator: lookup obligation-key receipt first. For integrity/reversal: hold in DB immediately, revoke/cancel chain, reassess exact dependent versions before resume.
6. Reset synthetic demo only by explicit selected namespace and deployment; verify absolute object/DB target scope before destructive reset. Preserve exported demo run audit if needed. No broad filesystem deletion or production reset button.

## Exit gate

No critical security/immutability/duplicate-reward/chain-prerequisite test may be waived for the demo. Optional live EE availability is reported separately and fixture mode labeled. All 28 new screen cards and the two existing pages have observable success/error/correction behavior; direct-RPC negative demonstration passes; receipt is explicitly simulated. This document does not itself claim any of those future tests passed.
