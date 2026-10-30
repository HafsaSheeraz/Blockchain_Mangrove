# 07 — Integrated user journeys and recovery

**PROPOSED.** Every button/read/write maps to [04](04-screen-api-event-matrix.md), module service in 03 and transaction in 05. Retain [PB-1 sequence diagrams](../playbook/09-sequence-diagrams.md) with IC amendments. No UI action creates an unscoped direct chain write.

## Protocol for every action

Read: actor → listed screen/filter/link → Axx GET → session+scope+field redaction → module query service → DB projection → typed response/allowed_actions → same screen or authorized deep link. No outbox/chain/notification for ordinary read. Download adds technical access audit only.

Command: actor → screen form/button → Axx mutation+CSRF+If-Match+Idempotency-Key → session/role/scope/person-conflict validation → named module service → locked DB transition+AuditEvent+outbox/inbox intents → commit → resource/Operation response → worker/job/actor-bound K call → receipt projection and/or notification → next role's own inbox/dashboard → resulting independent statuses. Rollback before commit leaves no external command. Browser cancellation does not roll back committed work.

Validation/401/403/404 returns before business transition;422 leaves draft unchanged;409 returns current version/blockers, user reloads/compares and resubmits intentionally. HTTP202 means durable acceptance, not verification/chain/settlement success. Every mutating action uses this protocol, including those grouped in the action ledger.

## Connected success action ledger

| Actor → screen/button → HTTP | Auth/service/transaction | Outbox/job/chain → inbox/next user → status |
| --- | --- | --- |
| Anonymous → S01 Sign in A01/A02 | anonymous CSRF/rate check; identity.login rotates session | nochain; allrole → S02 authenticated |
| O → T01 Create/Save A06/A08/A09 | orgrole; projects.create/revise; draft project/revision | audit only; nextO T02 |
| O → T02 Save site A11/A09 | org project; sites.save; immutable geometry/revision link | digest pending publication; nextO T03 |
| O → T03 Publish rules A14–A16 | O; policy.validate/publish; fixed D01 immutable | EV-01 → K06 after project/roles; N01 → V/P; nextO T04 |
| O → S04 Publish A12 | O, site/policy/default C/roles valid; project lock/seal | EV-01 → K02/K03/K04/K10/K06; N01; business active/chain pending |
| O → T04 Create/Publish/Assign A20/A71/A72/A21 | O/conflicts; tasks.assign; quantity lock, pin roster/type/site | EV-02 → K07; N02 → W01 assigned (supply may pending) |
| W → W02 Accept/Start A23 | own active assignment; tasks.transition; state+audit | EV-03 → N03 → O; in_progress, no approval |
| N → T06 Declare A38 | N/batch scope; declare_supply; sealed declaration/C snapshot | EV-04 → K11 → N04 → exactC confirmation pending |
| C → T06 Confirm A39 | exactC!=N/W; confirm_supply; observed/accepted inventory | EV-05 → K12 → N05 → N/O/W; confirmed supply only |
| W → S05/W03 Upload/Seal A29–A34 | own subject/signed slot; evidence.validate/seal exact bytes | EV-06 validation; no human approval; valid sealed version |
| W → W03 Submit A24/A25/A28 | ownwork; claim service; reserve stock, freeze revision | EV-07 → checks → K14 → N06/07/08; Vqueue review_ready only after checks |
| O/V → T09 reviewassignment A41/A74 | independent roster; trust.assign/reassign; lock exact subject | EV-08 → K08 if changed, N08 → newV; old approval future use invalid |
| V → W04/T10 Visit/Decide A46–A48/A43 | assigned independent V; trust.record_decision; exact report/check/claim | EV-08 → K15/K16, N09 → W/O; approved work fixesQ/cohort/dates |
| Scheduler → S06 due | unique schedule, parentCompletion; monitoring.schedule | EV-09 → N10/N11 → collector/W/V; M3/M6 due/overdue, nopass |
| W → W04 Follow-up A46–A48 | exact parent/cohort/date/evidence; monitoring.submit | EV-10 → checks/K14 → N12 → V; observation_submitted |
| V → T10 Survey decision A43 | independent report and exact parent; trust.record_decision | EV-10 → K15, N13 → W/O, evaluation job; passed/failed separate from approval |
| Evaluator/P → W05 Evaluate A50 | currentdeps/nohold; rewards.evaluate; append one obligation evaluation | EV-12 → N14 changed → P; eligible only all 3 passed |
| P → W06 Authorize A52 | distinct P/current eligible/economic lock; freeze human approval | EV-13 → K19 → N15/N16 → P; human approved, chain pending/confirmed separate |
| P → W07 Simulate A55 | confirmed authority/nohold; enqueue; fresh RPC preflight then locked receipt insert | EV-14 → local receipt → K21, N18 → W08; simulated_settled/audit pending |
| A → S08 Compare/Report A60/A63/A84 | scoped redacted read/auditor; integrity/export services | read no chain; corruption EV-16 hold; next assigned V/O/P |
| S/O → S09/S04 roles/lifecycle A67/A83 | technical/business scope; role grant orhold/pause | EV-17/16 → K04/K05 → N20/N19; no admin approval bypass |
| P/V/affected W → dispute drawer A68/A70/A54 | scoped open; independent V resolve, P/Ocancel separately | EV-16 → K17/K18/K20; N19 affected roles; hold until resolved/reviewed |
| User → S07 Mark read A58 orS10 Retry A73 | own notification or S reconciled retry | read none; retry same command identity, never duplicate business mutation |

Every read/navigation button in PB-1 uses the read protocol; every non-read button is covered by its API/domain group here or 04. A84 report is read-only serialized authorized data; never recalculates scientific context.

## Negative journey matrix

| Case / actor/action | API/service result and DB/outbox effect | Recovery / next user / status |
| --- | --- | --- |
| Invalid input at any form |422 field errors, no published mutation/outbox | Same actor corrects retained draft; no misleading success. |
| Unauthorized/mismatched actor |401/403 or scoped 404; security audit only | Login/rightaccount or request legitimate assignment; no chain job. |
| Missing evidence W submits |A28 rejects sealed-checklist precondition 409/422; no stock partial reservation | W adds valid new version/set; if already submitted hard blocked check, A27 new revision; N07. |
| Nursery quantity mismatch |A39 accepted>observed/declaration 422; A28 stock short 409 under batch lock | C corrects observation/new confirmation version orOadjusts task; N05 negative/inline blocker; no planting approval. |
| Rejected claim V decision |A43 immutable rejected outcome, K16, no approved bit | N09 → W; cancel or new revision with reason; old outcome retained. |
| Request corrections |A43 changes_requested exact revision, old checks/claim preserved | N09 → W A27 → new evidenceversion/set → A28 → new checks → N08 V; no inherited approval. |
| Resubmit after approval |A68 immediate hold; Vrevokes approved source before activating replacement | K17/18 and dependent cancel, K14 new subject, independent review; oldsurveys cannot attach to new Completion. |
| Inconclusive satellite |A64 unavailable/no_data/insufficient snapshot stored | W/V complete field observation/report, existing science unchanged; no automatic rejection/pass. |
| Threshold failed |Accurate census accepted A43; review approved but component stage failed | M3<80 orM6<75 → ineligible; N13/N14; no authority. Changed in correct measurement needs new version/review, not checkbox override. |
| Missing M3 orM6 |Evaluation pending_requirements with missing stage blocker | N10/N11 → collector/V; mandatory milestone never waived in primary; cannot authorize. |
| Chain outage |Committed business action + durable queued/retry/unknown chain operation | N17 ops/P/O; human result visible; canonical authority/settlement blocked; reconcile before retry. |
| Duplicate authority |Same idempotency request → existing response; different request while active → 409 | User opens current authority; K19 also rejects direct duplicate; no extra obligation. |
| Simulator known failure |attempt failed, receipt absent, EV-14/N18 | P can retry same economic UUID after fresh checks; new attempt, not new reward. |
| Simulator unknown |attempt unknown, dispatch blocked until receipt lookup | S/P reconcile durable key; adopt existing receipt or prove absence; no blind retry. |
| Approval disputed/reversed |A68 hold before external work; V resolves field, A54 P/Ocancel | N19; hold wins before local receipt or marks already settled disputed; history never erased, refund never invented. |
| Chain reorg/reset |Canonical hash mismatch → orphaned/projection generation change | Hold dependent commands; new deploymentdomain/replay effective inputs; economic key preserved, not paid again. |

## Exact M3/M6 scheduling and outcome rules

For accepted date 2026-02-01: M3 due 2026-05-01, graceendMay 15; M6 due 2026-08-01, graceendAug 15. Early visit rejected. A reminder onApr 17/Jul 18 is not an admissible survey. Late visits can be independently accepted only with recorded late reason; missing/failed/unapproved cannot be waived. Dates clamp month end, never replace 3 calendar months with 90 days.

Primary original cohortQ; each census live+dead+missing=Q, missing counts not alive. Accepted physical report below threshold stores truthful review approved plus milestone failed; contract K19 still rejects it. Counterexamples and exact amounts in 11.

## Sequence: submission, checks and independent decision

```mermaid
sequenceDiagram
 actor W as Worker
 participant UI as Shared React screen
 participant API as FastAPI
 participant DB as PostgreSQL
 participant JOB as Evidence / checks worker
 participant C as Local EVM runner
 participant IN as Shared inbox
 actor V as Field verifier
 W->>UI: Upload exact bytes / seal / submit
 UI->>API: A29-A34 then A28 with CSRF / ETag / idempotency
 API->>DB: Scope + inventory locks; revision / audit / outbox commit
 API-->>UI: 202 checking, chain awaiting dependencies
 JOB->>DB: Validate exact input and append CheckRun
 alt Hard failure
 JOB->>IN: N07 correction to worker
 W->>API: A27 new revision and evidence version
 else Ready / soft flags
 C->>C: K14 actor-bound subject commitment
 JOB->>IN: N08 exact reviewer assignment
 V->>API: A46-A48 independent report, A43 exact-version decision
 API->>DB: Conflict checks / decision / cohort / outbox atomically
 C->>C: K15 independent signer and contract guards
 JOB->>IN: N09 worker; monitoring schedule
 end
```

## Sequence: mandatory follow-ups to final simulated reward

```mermaid
sequenceDiagram
 actor W as Collector / worker
 actor V as Independent verifier
 participant API as FastAPI monitoring / reward
 participant DB as Shared DB / outbox
 participant CH as Local Solidity contract
 participant IN as Inbox
 actor P as Payment authorizer
 participant SIM as Local simulator
 W->>API: A48 M3 / M6 exact parent and census evidence
 API->>DB: Immutable observation + checks / review handoff
 API->>IN: N12 verifier
 V->>API: A43 field survey decision plus independent report
 API->>DB: Store effective decision and stage pass/fail
 API->>CH: Durable runner K15 after commit
 API->>DB: Evaluate PLANTING + M3 >=80 + M6 >=75
 alt Any missing / failed / disputed
 API->>IN: Blocker to worker / authorizer, no final eligibility
 else All requirements passed
 API->>IN: N14 eligible, accepted quantity based amount
 P->>API: A52 human approval of exact evaluation
 API->>DB: Freeze authority / outbox
 API->>CH: K19 recomputes prerequisites / amount / replay rules
 CH-->>API: Canonical success receipt + local depth
 API->>IN: N16 authorizer ready to simulate
 P->>API: A55 simulated-only acknowledgement
 SIM->>CH: isExecutable preflight
 SIM->>DB: Re-lock, compare digest/holds; insert unique local receipt
 API->>CH: K21 receipt assertion via outbox
 API->>IN: N18 fictional receipt, chain audit separate
 end
```

## Sequence: reversal and uncertain delivery

```mermaid
sequenceDiagram
 actor U as Affected user / verifier
 participant API as FastAPI
 participant DB as Obligation / dispute DB
 participant R as Chain reconciler
 participant CH as Local EVM
 participant SIM as Simulator
 U->>API: A68 dispute
 API->>DB: Lock obligation; immediate hold + audit/outbox
 SIM->>DB: Attempt receipt transaction
 DB-->>SIM: Held unless receipt already existed
 API->>CH: Actor-specific revoke/cancel command after consent
 CH--xR: RPC response lost
 R->>DB: Unknown outcome, no downstream dispatch
 R->>CH: Query event digest / nonce / receipt / canonical block
 alt Identical canonical success
 R->>DB: Reconcile receipt, continue only valid dependencies
 else Absent and safe to retry
 R->>CH: Same command identity / reconciled nonce
 else Conflict / reorg
 R->>DB: Block and notify operations; retain prior history
 end
 Note over DB,SIM: Existing simulated receipt never erased or executed twice
```

Notification delivery can lag; next role can always find own authorized queue. These diagrams show orchestration, not synchronous internal HTTP calls between modules in the same backend.
