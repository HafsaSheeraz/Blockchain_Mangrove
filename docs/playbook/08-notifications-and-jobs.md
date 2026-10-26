# 08 — Shared notifications and background processing

**PROPOSED:** one authenticated in-app inbox, shared across all three modules. No email, SMS, WhatsApp or third-party messaging in PB-1. Deep links point to the same scoped project/task/claim/inspection/authorization record; no parallel notification identity per module.

## Notification contract and matrix

Each intent uses `(audit_event_id,recipient_id,template_id,channel=in_app)` unique key. Recipients are computed server-side from project/assignment/review relationships. Notification carries a safe summary, resource route, stage/reason category, occurrence time and read state; sensitive evidence, signed URLs, passwords and actual bank data are forbidden. Recheck recipient scope on delivery/read; membership revocation hides inaccessible links rather than exposing a historical payload.

| ID / trigger | Recipients | Deep link / purpose |
| --- | --- | --- |
| N01 project/policy published | Scoped O, assigned V/P/A | Project overview/rules; includes version and chain pending badge. |
| N02 task assigned | Assigned W | Assignment; accept/start work. |
| N03 assignment accepted/cancelled | O, affected W | Assignment; next action/status. |
| N04 supply declaration submitted | Assigned C; O summary | Nursery batch; count/confirm. |
| N05 supply confirmed/rejected/changes requested | N, O, affected assigned W | Batch; approved supply explicitly not planting approval. |
| N06 claim submitted/checks queued | W receipt; O summary | Claim; pending checks. |
| N07 hard checks blocked/error | W; O; operations admin on system error only | Claim/check panel; correct inputs or await dependency repair. |
| N08 review ready/assigned/reassigned | Assigned V; previous V cancellation notice on reassignment | Exact review assignment; inspect/decide. |
| N09 claim decision | W, O; P summary when appropriate | Exact claim revision/decision; rejected/changes requested reason or accepted work. |
| N10 inspection approaching/due | Collector/W, assigned V, O | Milestone with actual due/window dates. |
| N11 inspection overdue | Collector/W, V, O | Monitoring board/milestone; no automatic pass. |
| N12 inspection submitted | Assigned V; W receipt | Inspection/review; independent field review next. |
| N13 follow-up decision | W, O; P if component ready | Milestone/decision; accepted/failed/changes requested. |
| N14 eligibility evaluated/changed | W own, P, O summary | Obligation; component prerequisites/amount/blockers. Notify only changed result/input digest, not every reevaluation. |
| N15 human authorization approved/rejected/cancelled | W, P, O | Authorization; distinguish approved_pending_chain from authorized. |
| N16 chain command confirmed | Actor and next-action role; avoid routine fanout to all members | Owning resource; e.g. P sees ready-to-settle after authorization. Group noncritical commitment confirmations in audit view. |
| N17 chain failed/unknown/orphaned | Operations S; affected P/O if blocking money; actor sees inline status | Operation/resource; pending/retry/hold instructions, no raw secret RPC errors. |
| N18 simulator queued/settled/failed/unknown | W own, P; O summary | Settlement; always prefix simulated. Unknown means reconcile, not blind retry. |
| N19 dispute/reversal/integrity mismatch | W affected, O, assigned V, P; S only integrity/system error | Dispute and held obligation; explain affected exact versions. |
| N20 membership/role change | Target user, O, auditor; S operations acknowledgment | Access page or permitted project; chain grant status if applicable. |

Business event creates an intent inside its transaction; inbox delivery after commit can lag without changing the result. Mark-read A58 creates read state only: no chain write, no fanout, no obligation side effect. Browser polls inbox/unread counts modestly (proposed 30 seconds while visible) and refreshes after actions. Real-time sockets are not needed initially.

## Worker catalog and dependencies

| Job | Durable input / output | Retry and safety |
| --- | --- | --- |
| Upload validation | Upload ID/object version → valid/rejected EvidenceVersion + findings | Same bytes version; bounded downloads/parser time; interrupted quarantine resumable. |
| Automatic checks | sealed subject/profile digest → CheckRun/findings | Unique input/profile run, error retained; no approval on failure. |
| GIS snapshot | immutable site/date/source → stored result/export or unavailable/no-data | Bound external work; source mode never rewritten to live; existing EE timeout limitation disclosed. |
| Chain submitter | ChainCommand actor/ABI/event ID/dependencies → signed tx attempt | Only when dependencies confirmed; recheck actor role, signer binding, holds; nonce serialized per address. |
| Chain reconciler | pending tx/event/nonce → canonical receipt/status projection | Receipt status, block hash and local depth checks; unknown/orphaned stops downstream work. |
| Eligibility evaluator | obligation + exact effective decisions/policy → evaluation | Lock obligation; coalesce same digest; no duplicate rewards. |
| Milestone scheduler | milestone/policy due/window → N10/N11 jobs | Calendar-month dates, unique schedule key, no repeated unchanged reminders. |
| Inbox delivery | intent/event/template/recipient → notification row | Insert-on-conflict prevents duplicate inbox items; recheck scope. |
| Simulator | authority + stable obligation idempotency key → durable receipt | Confirm chain, DB holds, fresh isExecutable; reconcile unknown before retry; no network financial provider. |
| Settlement audit | durable simulator receipt → chain recordSimulatedSettlement | Can lag settlement; never simulate a second payment to repair a missing audit tx. |

Workers share backend code and database but own separate queues/leases so a hung EE call does not starve chain/notification delivery. Use DB outbox/jobs first; Redis/Celery is not a mandatory new service. Leases expire and recover on restart. Suggested retries 5s, 15s, 60s, 5m, then 15m with jitter, maximum 8 attempts before blocked/manual review; business-invalid/authorization errors do not retry automatically.

One AuditEvent may produce multiple chain commands. Derive stable command/event IDs from `(audit_event_id,command_kind,step_index,deployment_id)`, not random IDs per retry. Keep audit event identity separate from each command's replay key. A role-grant command cannot be skipped because a later subject/decision command already exists.

## Failure and recovery rules

- DB rollback: no outbox/inbox/chain command survives. Do not send external side effects before commit.
- Crash after DB commit: outbox lease worker delivers later. Crash after chain send but before tx persistence: use recorded signed-transaction hash/nonce and event lookup; no blind new-nonce duplicate.
- Failed chain approval: DB human decision remains visible; chain status blocks reward authorization. Invalid contract prerequisite is a design/data issue, not a reason to relabel approval confirmed.
- Chain reset: create new deployment identity, archive previous receipts as historical, replay compatible committed state in dependency order only through an explicit demo reset action. Never point old receipts at a new contract.
- Notification failure: retry inbox delivery, not the original business mutation. Avoid mass duplicate notifications during projection rebuild; uniqueness keys stay stable.
- Unknown simulator attempt: query durable simulator receipt by obligation key. If receipt exists, adopt it; if not and positively proven unexecuted, retry same obligation key. Do not generate a new economic key from a replacement authorization.
- Dispute/integrity error: immediate DB hold, cancel/stop queued work, enqueue chain revocation/cancellation, notify next actors. Already settled demo receipts remain historical and marked disputed.

Automatic integrity detection may request an administrative chain pause using the registered system-admin authority, with system-origin audit provenance. It must not impersonate a verifier to reverse a field decision. An assigned independent reviewer resolves the resulting dispute and signs any decision revocation; P/O handles cancellation under contract permissions. Unpaid dispatch is already blocked by the immediate DB hold while human resolution is pending.

## Operational visibility

Operation DTO records last safe error, attempts, next retry, dependency blockers and allowed retry action. Operations panel is S-only metadata; role-sensitive content remains scoped. A73 retries only reconciled retriable commands, never bypasses invalid business state. Capture queue age, last worker heartbeat, stale leases, unknown tx count, orphaned receipts, held obligations, inbox lag and simulator unknowns. Keep request/event/command IDs across logs; redact signed URLs and signer/session secrets.
