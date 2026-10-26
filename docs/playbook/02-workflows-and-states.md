# 02 — Workflows, configurable tasks and state machines

**PROPOSED PB-1 functionality throughout.** All decisions refer to immutable versions; state columns below are derived workflow projections, not permission to edit submitted content.

## Primary connected scenario

Organization creates project → saves valid site/AOI version → publishes fictional verification/reward contract → assigns plantation work → nursery declares and independently confirms supply → worker seals claim/evidence → automatic checks → independent planting field visit/decision → 3-month inspection/decision → 6-month inspection/decision → final component eligibility → human payment authorization request → on-chain prerequisite/authorization confirmation → simulated settlement → shared audit/inbox history.

Tasks may be assigned before supply exists, matching the requested demonstration. A plantation claim cannot be submitted until enough supply is confirmed and reserved. Nursery confirmation is not a planting milestone approval. At each handoff the next role receives a shared inbox notification.

## Configurable task types

TaskTypeVersion defines code, title, quantity unit, JSON-schema-like typed form fields, evidence checklist, required supply kind, review method, milestone templates, reward component templates, allowed actors and automatic-check profile. Schema/profile options are selected from server allowlists; organization configuration cannot upload executable code or invent role bypasses. Existing assignments pin a task-type/policy version.

| Code | Measurement and evidence | Independent acceptance / smaller demo |
| --- | --- | --- |
| `propagule_collection` | Count or weight with explicit unit, species/source zone, collection date, collection/receipt photos. | Reviewer accepts collection/receipt quantity. One completion component; no plantation survival claims. |
| `nursery_work` | Shift/hours or seedlings tended, nursery batch reference, work log and photos. | Distinct reviewer accepts logged nursery work. Supply declaration/confirmation is a separate action even when the same nursery is referenced. |
| `plantation` | Seedlings planted, site/AOI, planting date, confirmed supply allocation, geotagged plot/row photos, planting register. | Fully implemented primary slice: field-accepted planting plus 3/6-month follow-ups. |
| `protection_maintenance` | Work units/hours/area, activity subtype (guarding, debris removal, repair), work log and before/after evidence. | Field reviewer accepts maintenance scope; optional recurrence. No seedling supply required by default. |
| `field_monitoring` | Visit/plot observations, method, live/dead/missing counts, dated field report/photos. | Separate reviewer accepts monitoring **work**. A linked survival decision still uses the inspection workflow; worker cannot approve their own reported observations. |

Required fields/checklists are conditional by task type; plantation-specific supply and survival fields are not forced onto seed collection or maintenance. A shared ClaimRevision, EvidenceSet, CheckRun and ReviewDecision model handles all five.

## Fictional contract policy

PolicyVersion is the immutable fictional agreement, not Solidity bytecode. It fixes site revision, task type version, allowed quantity/unit, evidence/review requirements, milestone measurement/threshold/date rules, reward components, caps, rounding, required decision masks and cancellation/dispute behavior.

PB-1 primary policy proposal: 1,000 planted seedlings; 3-month and 6-month inspections from the **accepted planting date**, added as calendar months, clamping to the last valid day if necessary. Recommend a ±14-day inspection window; late visits require a reason and explicit reviewer acceptance. Missing/late status never silently becomes passed. Example thresholds and rates in [synthetic data](15-synthetic-data-and-demo.md) need approval as fictional policy values.

Field inspection stores expected cohort count, measured live/dead/missing counts, denominator, method (census or explicitly configured sampling), measurement time, inspector and sealed evidence. Primary synthetic case uses a census; survival = live / original accepted planted cohort, with missing counted as not alive. A nursery stock count or optional satellite analysis is not that denominator. Replacement plantings create separate cohorts and do not silently increase original-cohort survival.

### Component architecture

| Component kind | Typical prerequisites | PB-1 primary behavior |
| --- | --- | --- |
| `completion_payment` | Independently accepted planting/work; mask `001` for plantation. | Supported architecture and smaller task demo; primary plantation component disabled to avoid double reward. |
| `survival_incentive` | Planting plus configured follow-up decisions, e.g. mask `111`. | Supported architecture; not additionally paid in primary scenario. |
| `final_reward` | Exact policy mask, proposed `111` = planting + 3 months + 6 months. | One final obligation: all three approved before eligibility. |

Each component has its own unique `(assignment, policy_component_version)` obligation. Distinct completion/survival components can be enabled together in another fixture without sharing an authorization or duplicating the same component. UI shows which components are disabled/not contracted rather than listing them as overdue.

## Independent status dimensions

| Aggregate/dimension | Allowed progression and meaning |
| --- | --- |
| Project | `draft → configured → active → suspended | closed`. Active requires saved site, published policy and complete project-role assignments; chain state separately pending/confirmed. |
| Policy | `draft → published → superseded`. Existing assignments retain published version; no retroactive edits. |
| Assignment | `assigned → accepted → in_progress → submitted → verified_complete`; `changes_requested`, `rejected`, `cancelled` are explicit outcomes. Supply may still be pending while assigned. |
| Claim revision | `draft → submitted → checking → review_ready | checks_blocked → under_review → approved | changes_requested | rejected`. Failure to run checks is `checks_error`, not approval or rejection. |
| Supply | `declared → confirmation_pending → confirmed | changes_requested | rejected`; reservations `reserved → consumed | released`, bounded by confirmed stock. |
| Evidence version | `upload_pending → quarantined → valid | rejected`; sealed sets reference only valid versions. No in-place replacements after sealing. |
| Automatic checks | `queued → running → passed | passed_with_flags | blocked | error`. Findings include severity, exact input hashes and check-version. Flags require acknowledgment, not silent dismissal. |
| Review/inspection | `assigned → visit_recorded → decision_submitted → approved | changes_requested | rejected`; pending chain projection does not rewrite business outcome. |
| Milestone | `scheduled → due → observation_submitted → under_review → passed | failed`; derived `overdue`, and explicit `waived` only if permitted by a new approved policy (not enabled in primary fixture). |
| Eligibility | `pending_requirements → eligible | ineligible`; later `held | revoked` after dispute/reversal. Computed by server on exact decision versions, independently from chain. |
| Human authorization | `not_requested → requested → approved_pending_chain | rejected | cancelled`; on-chain authorization confirmation projects `authorized`. Human request alone is not executable authority. |
| Blockchain operation | `not_required | queued → submitting → submitted → mined → confirmed`; plus `retry_wait`, `unknown`, `reverted`, `orphaned`, `blocked`. Local `confirmed` means the configured local receipt-depth rule, not public consensus finality. |
| Settlement | `not_requested → queued → processing → simulated_settled | failed | unknown`; `held` when an authorization/decision is disputed. `simulated_settled` is never displayed as a real payment. |
| Notification | `pending → delivered` (in-app row exists); per-recipient `unread → read`. Delivery/read does not imply task acceptance or chain confirmation. |

A combined summary may say “Eligible · authorization pending · chain queued · not settled”, but APIs retain the four independent fields. No blockchain function transfers value. Local gas uses disposable development accounts solely to execute the demonstration.

## Automatic-check gate

CheckRun seals inputs and profile version. Hard failures: missing required evidence, invalid geometry/quantity/date, unconfirmed/exhausted supply, wrong scope, corrupted/unsafe upload, contract mismatch. Review may not approve blocked/error checks. Soft flags: duplicate hash across claims, GPS outside tolerance, capture timestamp mismatch, uncertain metadata or overlapping activity. Reviewer must document resolution and field findings for flags. Only deterministic input corrections/new versions clear hard failures; privileged users cannot click “ignore all”.

## Exact-version acceptance and correction

Decision binds `(claim_revision_id, evidence_set_hash, policy_version_id, AOI_version_id, check_run_id)` or the analogous inspection revision. Field acceptance also binds the reviewer's inspection evidence set. On-chain commitments reference the resulting combined decision digest and the submitted subject/evidence hashes.

Changes requested create a new draft revision that explicitly supersedes the previous revision. A corrected submission reruns checks; old decisions do not migrate. If approved work has already established obligations, open a dispute, hold its reward/authorization/settlement, revoke the chain subject/decisions as applicable and reassess dependents before activating a replacement. No deletion of history.

Use transactions for claim-revision activation and allocation transfer: release the superseded unconsumed reservation only while reserving the replacement under locks; approved consumed stock cannot be released into inventory without an explicit inventory correction. Revised work is not a second payable obligation: obligation key remains assignment + component.

When verification is reversed, append reversal records and chain invalidation commands, hold unpaid work immediately in the DB, and notify worker/organization/authorizer. A pending local-chain cancellation prevents settlement dispatch. If simulation already settled, append a disputed/correction receipt state; do not erase or fabricate a refund. A mined chain transaction may exist while off-chain state is held; both remain visible.

## Temporal semantics

Event occurrence, server record time, satellite acquisition range, field visit time, checkpoint due date, chain receipt time and simulator settlement time are separate fields. Store timestamps UTC; render Asia/Karachi dates/times with zone labels. Primary demo uses historically dated synthetic observations and current submission/anchor times, so six months can be demonstrated without a hidden accelerated clock. Do not assert a field observation is real-time because its record was created today.
