# 04 — Connected screens, HTTP contracts and events

All new routes/DTOs/events here are **PROPOSED**. [PB-1 API catalog](../playbook/05-api-contracts.md) remains A01–A78; [shared](../playbook/10-screens-shared.md), [Trust](../playbook/11-screens-trust.md) and [Steward](../playbook/12-screens-steward.md) cards retain fields/layout/errors/tests. This document supplies missing transitions and binding details, not a second competing catalog.

## HTTP freeze and response completeness

Use same-origin HttpOnly session, CSRF+Origin on writes, server-derived actor, project/person scope, current role/conflict checks. Scoped invisible resource 404; visible forbidden action 403. Every POST except login needs Idempotency-Key; PATCH/transition needs If-Match. Response 201 create/200 update/202 durable external-work command/204 logout. Error codes 400/401/403/404/409/413/415/422/428/429/503 and PB-1 error envelope preserved.

Entity responses: `{data:Resource,meta:{request_id},operation?:{id,state,url}}`. List: `{data:Resource[],page:{next_cursor,has_more},meta:{request_id}}`. Every mutable resource has `id,project_id?,row_version,created_at,updated_at,allowed_actions` and ETag; immutable versions have `id,parent_id,version_no,content_digest,published_at?,supersedes_id?`. UUID/date/time/hash formats from PB-1; optional nullable fields explicitly returned null, omitted only when role redaction forbids them. A83 transitions return updated ProjectWorkspace.

Common status projection: `status:{business,eligibility,authorization,blockchain,settlement}` retained. Persist separate `human_state=requested|approved|rejected|cancelled`; `status.authorization=approved_pending_chain|authorized` is a **derived display** from human approval+chain state, never a replacement for either. Null/not_required is not success. Candidate amount is separate from `payable_amount_minor` (null until eligible). Expose `blockers:[{code,resource_id,required_version_id,message}]` and `input_digest`.

Reads A05/A07 → ProjectSummary/Workspace; A10 → SiteVersion; A13/A82 → PolicyVersion; A17 → TaskTypeVersion; A19/A79 → TaskDetail; A22/A75 → AssignmentDetail/Summary; A26/A76 → ClaimDetail/Summary; A31/A81 → EvidenceVersion/Summary; A35/A37 → NurserySummary/Detail; A40/A42 → ReviewSummary/Context; A44/A45/A80 → MilestoneSummary/Detail/InspectionRevision; A49/A51 → ObligationSummary/Detail; A53 → AuthorizationDetail; A56 → SettlementAttempt; A57 → Notification; A59/A60 → AuditSummary/Detail; A61/A77 → Operation; A62 → CheckRun; A65 → Snapshot. Mutations return the created/updated type from that domain plus Operation if queued. Each type includes the fields in its [DB catalog](../playbook/04-database-model.md) and amendments in 05, excluding password/token/key/raw storage path fields and role-prohibited identity/evidence. No GET has a hidden approval side effect.

### Required DTO amendments to PB-1

| API / DTO | Frozen fields/validation and output amendments |
| --- | --- |
| A01/A02 SessionContext | user{id, display_name}, organizations{id, name, roles}, projects{id, roles}, csrf_token, expires_at; password never returned. Login 1–120 chars, password 1–256, rate limit 5 failed/15 minutes per account+IP; generic failure. Session 8 habsolute,30 minutes inactivity, anonymous bootstrap 15 minutes. |
| A06/A09 ProjectDraft | name 3–120, code regex[A-Z0-9-]{3,40}, description<=4000, explicit fictional acknowledgment; site/policy optional until publish; `nursery_confirmer_user_id` selected by O from active C. Project code stable after initial publication. |
| A11 SiteCreate | Polygon only, all rings preserved, finite lon/lat, topology valid, nonempty, area<=100 ha; same vertex/ring/byte caps as existing analysis configuration unless stricter business schema. Store raw JSON immutably; bounds/area/digest server-derived. Synthetic source/label<=120, revision reason 1–2000. |
| A14/A15/A16 PolicyDraft | primary profile `plantation_final_v1`: task plantation, scale 1, assigned cap 1000, rate 1000 minor, cap 1000000 minor, currency PKR, mask 7, M3 bps 8000/M6 bps 7500, offset months 3/6, grace 14 days. Locked primary fields read-only in editor; altered primary profile 422. Other typed component profiles configurable; no retroactive assignment changes. |
| A20/A21/A71/A72 Task/Assignment | title 3–160, instructions<=4000, exact site/type/policy, positive quantity within task cap; required worker and collector and per-required-stage reviewers. O task lock prevents aggregate over assignment; C roster separate. Default collector=worker applied server-side and echoed, never silently absent. |
| A24/A25/A28 ClaimDraft/Submit | work_date required; assignment/site/policy fixed; positive typed quantity; plantation integer<=assigned; species/plot/cohort labels 1–120. Supply 1–8 unique confirmation IDs, positive quantities sum to claimed quantity. evidence_set_id nullable in draft, sealed nonempty on submit. `acknowledgments` allowlisted. Submitted content frozen. |
| A29 UploadSlot | add purpose `agreement|supply|claim|observation|review_visit`, concrete scoped target{assignment_id?, batch_id?, review_assignment_id?, milestone_id?}, declared capture time/location/accuracy/source optional. Exactly required target for purpose, server-derived project/owner. filename<=120/caption<=1000; JPEG/PNG/PDF<=10 MiB,10 files/set, upload 15 minute expiry. |
| A30/A33/A34 Evidence | complete only owned slot/object version; server hash/size/MIME authoritative; draft set includes purpose/target and category/order, bounded 1–10 unique valid versions; seal freezes metadata/order/nonce/canonical bytes. Upload complete 202 validation; seal 200 or 409 validation_pending. |
| A32 Download |200 JSON `{data:{url,expires_at,variant:"original"|"redacted"},meta}`,60 second signed URL, no-store; variant query allowlisted. Original download reauthorized/access-audited; preview sandboxed and never executes inline uploaded PDF/scripts. |
| A36/A38/A39 Supply | batch code 3–40/species 1–120; declaration count positive integer, evidence sealed, date<=today. Snapshot project C when declaration created; output confirmer_id. Confirm/reject/changes_requested enum; accepted<=observed<=declared on approval; accepted=0 on negative outcome, notes required 1–2000; purpose-specific confirmer field evidence. One effective confirmation; correction appends declaration. |
| A41/A43/A74 Review | exact concrete target, stage roster/person conflicts; blocked/error checks cannot approve. Decision binds subject/site/policy/check/report IDs/digests and per-soft-flag resolutions; notes 1–4000; acceptedQ<=claimed, review_visit valid+sealed. Reviewer writes report on another actor's subject; never reviews its own report as a worker claim. |
| A46/A47/A48/A80 Inspection | add base_revision_id? for correction, parent_completion_decision_id, purpose observation/review_visit, exact source_observation_revision_id/review_assignment_id for visits; mismatch 409. Census integer live+dead+missing=Q; Qread-only original. Earliest observation exact due, no early; >due+14 requires late_reason 1–2000 and explicit V acceptance. Future visit 422. Review_visit submission does not recursively create another independent review. |
| A50/A51 Eligibility | exact current dependency IDs/digest returned even on missing/failed; server computes; reason codes missing_m 3, missing_m 6, threshold_failed, disputed, revoked, version_changed. Missing pending, verified below-threshold ineligible, dispute held; no client status input. |
| A52/A54/A55 Authorization/simulation | outcome approved/rejected, exact eligibility revision; approval needs expected_amount_minor/currency comparison+reason; actor/payee uneditable. Cancel reason 1–2000. Simulate must acknowledge true, requires confirmed canonical authority/noholds; duplicate active 409 unless same idempotency key. Unknown simulator outcome 409 reconciliation_required. |
| A68/A70 Dispute | concrete target type+ID, reason 1–4000; Vfield resolution independently authorized; P/Ocancel authority separate command, not assumed V authority. Worker can open but cannot resolve own approval. Held projections returned immediately. |

Dates are business dates rendered Asia/Karachi; timestamps UTC. GPS optional with source/accuracy, uncertainty flagged rather than invented reliable geolocation. All primary surveys census only; sampling requires another policy/profile and is outside the first slice.

## Added API operations

| ID | Proposed method/path (prefix /api/v 1) | Request → response / authorization |
| --- | --- | --- |
| A79 | GET /tasks/{id} | selected revision query? → TaskDetail including full editor/bootstrap fields/history; Owrite context or scoped read. |
| A80 | GET /inspection-revisions/{id} | → immutable/draft revision with purpose, parent/cohort/report links and ETag if draft; owner/assigned V/scoped read. |
| A81 | GET /projects/{id}/evidence-versions | category/purpose/owner=me/cursor → authorized metadata versions; no public object URLs. |
| A82 | GET /policy-versions/{id} | → full policy/components/requirements/canonical agreement/digest; scoped read. |
| A83 | POST /projects/{id}/transitions | {action:suspend|resume|close, reason} → ProjectWorkspace+Operation; O; Sonlysuspend for technical integrity incident. Close requires no unresolved settlements/authority; resume requires explicit current-role/prerequisite reconciliation. |
| A84 | GET /projects/{id}/report | format=json|csv, scope=authorized, as_of_event_id? → bounded business report bytes with schema_version/generated_at/exact source refs/statuses/fictional label; A/O/P/Wrole-redacted, no-store; no new science calculation. |

## Screen-to-service/event matrix

G=PB-1 shared layout/validation; API IDs locate exact HTTP request/response above or PB-1. Service method's DB write set/state/recovery is defined in 03/05. EV table below expands outbox and next-role recipient. Read actions emit no business notifications or chain commands; download access audit is technical only.

| Screen / proposed route / actor | Buttons/forms → APIs and service owner | Outbox → chain/job → notification → next user | Acceptance |
| --- | --- | --- | --- |
| S01 /login, all | Login/logout A01–A03 → identity | Session only; nextS02; no chain/inbox | UI-01, SEC-01/02 |
| S02 /app, all | Filter/refresh A04/A57 | Read cards → ownwork/review/reward | UI-02 |
| S03 /projects, scoped | List/create A05 → T01 | Read only | UI-03 |
| S04 /projects/:projectId, O/scoped | Publish A12; dispute A68; lifecycle A83 → projects | EV-01/16 → K02/03/05 → N01/19 → project/affected roles | UI-04, P2-13 |
| S05 /projects/:projectId/evidence, scoped | List A81, upload/seal A29–A34, download A32, integrity A63 → evidence | EV-06 validation/integrity → job; mismatch N19 → V/O/P | UI-05, EVID |
| S06 /projects/:projectId/monitoring, scoped | A44/A45; context A64/A65 → monitoring/sites | EV-09 duejobs → N10/11 → W/V; context no survival bit | UI-06, MON |
| S07 /notifications, own | A57/A58 read → notifications | Read state only, resource link → next screen | UI-07, NOTIF |
| S08 /projects/:projectId/audit, scopedA | A59/A60/A63/A84 report → audit | Read/export none; integrity incident EV-16 | UI-08, P2-18 |
| S09 /admin/access, S | A66/A67 roles → identity/admin | EV-17 → K01/04 → N20 → target/O | UI-09, SEC-07 |
| S10 /admin/operations, S | A77/A61/A73/A78 → chain/admin | EV-11 retry → samejob/K → N17 on meaningful failure | UI-10, REC |
| T01 /projects/new or /projects/:id/edit, O | A06/A08/A09/A12 → projects | Draft none; publishEV-01 → K02/03 → N01 | UI-11 |
| T02 /projects/:id/site, O | A10/A11/save A09/context A64 → sites | EV-01 publish digest; context job only | UI-12, GEO |
| T03 /projects/:id/rules, O | A13–A16/A82 → policies | EV-01 → K06 → N01 → V/P | UI-13, POLICY |
| T04 /projects/:id/tasks, O | A17–A21/A71/A72/A79 → policies/tasks | EV-02 → K07 → N02 → W01/W02 | UI-14, TASK |
| T05 /projects/:id/nursery, N | A35/A36 → nursery | Empty batch no chain/fanout; nextT06 | UI-15 |
| T06 /nursery/:batchId, N/C | A37–A39 → nursery | EV-04/05 → K11/12 → N04/05 → C/N/O/W | UI-16, SUPPLY |
| T07 /projects/:id/claims, scoped | A76 → claims list; A41 assign → trust | EV-08 → N08 → Vqueue | UI-17 |
| T08 /claims/:id, scoped | A26/A27/A62/A68 → trust/screening | CorrectionEV-07 checks; disputeEV-16 hold → N19 | UI-18, VERSION |
| T09 /reviews, V/O | A40/A41/A74 → trust | EV-08 → K08 if roster change → N08 → newV | UI-19, REVIEW |
| T10 /reviews/:id, V | A42, A46–A48 visit, A43 decision → trust | EV-08/10 → K15/16 → N09/13 → W; EV-12 evaluator | UI-20 |
| W01 /my/tasks, W | A75 list → tasks | Read → W02 | UI-21 |
| W02 /assignments/:id, W | A22/A23 accept/start/cancel → tasks | EV-03 → K09 cancel only → N03 → O; nextW03 | UI-22 |
| W03 /assignments/:id/submit, W | A24/A25/A27/A28/evidence → trust | EV-07 → check job/K14 → N06/07/08 → V | UI-23, CHECK |
| W04 /milestones/:id/inspection, W/V | A45–A48/A80/optional context → monitoring | EV-10 → checks/K14 observation → N12 → V; review visit only feeds decision | UI-24, MON |
| W05 /projects/:id/rewards, W/P/O | A49/A50 → rewards | EV-12 evaluation → N14 changed only → P/W06 | UI-25 |
| W06 /rewards/:id, P/scoped | A51/A52/A68 → rewards/trust | EV-13 → K19 → N15/16 → PW07; rejected no authority | UI-26 |
| W07 /authorizations/:id, P/scoped | A53/A54/A55 → rewards/settlement | EV-13/14 → K20/job/K21 → N15/18 → W08 | UI-27, PAY |
| W08 /settlements/:id, own/scoped | A56/A53 refresh; retry via W07 | Read none; disputeEV-16, receipt retained | UI-28 |

EXISTING E01 `/` and E02 `/analysis` remain as audited. Their current science requests/results never write claim/milestone/reward state. The new report drawer/incident actions belong to S08/S04, not unlisted pages. Inspection correction links preserve `base_revision_id`; read-only users never see submit controls.

## Domain event / consumer registry

All events carry event_id, schema_version=PB-2, project_id, aggregate_id, exact_revision_id?, actor_id, occurred_at, recorded_at, input_digest, request_id. Outbox uniqueness(event_id, consumer, step); recipients server derived; no raw files/secrets/signed URLs. N IDs expand recipient/deep-link rules in [PB-1 notifications](../playbook/08-notifications-and-jobs.md).

| Event | Meaning / consumer and next actor |
| --- | --- |
| EV-01 | project/site/policy publication; chain project/policyplanner, N01 → O/V/P/A. Draft save only audit, nochain. |
| EV-02 | task assignment; chain K07, N02 → assigned W. |
| EV-03 | assignment accept/start/cancel; N03 → O/W, chain K09 on cancellation. |
| EV-04 | supply declaration; chain K11, N04 → snapshottedC. |
| EV-05 | supply decision; chain K12 approval or ancillary negative outcome, N05 → N/O/affected W. |
| EV-06 | upload complete/validation/integrity; object validation job; N19 only integrity incident. |
| EV-07 | claim submitted/check result; checks → K14 onready, N06 W/N07 blocked/N08 V. |
| EV-08 | review assigned/reassigned/planting decision; K08/15/16, N08 V/N09 W/O; completion acceptance schedules milestones. |
| EV-09 | checkpoint approaching/due/overdue; scheduler, N10/N11 → W/collector/V/O. |
| EV-10 | inspection submitted/independent survival decision; checks, K14/K15, N12 V/N13 W/O, eligibilityevaluation. |
| EV-11 | chain canonical state change; receipt projector, N16 next role/N17 S+blocking P/O. |
| EV-12 | eligibility evaluated; unique obligation lock, N14 → W/P/O only on changed input/result. |
| EV-13 | authority approved/rejected/cancelled; K19/K20, N15 → W/P/O. |
| EV-14 | simulator queued/result; durable receipt, K21 after local commit, N18 → W/P/O summary. |
| EV-15 | report generated/evidence download; access audit only, no chain or fanout. |
| EV-16 | dispute/reversal/integrity hold; invalidate projections, K05/13/17/18/20 as appropriate actors, N19 affected roles. |
| EV-17 | membership/actor binding change; K01/04, N20 target/O/A; immediate app revocation holds. |

Notifications are eventual independently of chain delivery; each event/recipient/template delivered at most once by constraint. A58 creates no new domain fanout. See 07 for failure/status/correction handoffs, not just the success table.
