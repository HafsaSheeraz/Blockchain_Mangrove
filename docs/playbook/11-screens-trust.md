# 11 — Trust and configuration screens

**PROPOSED.** Shared shell/validation/async/error conventions G in [shared screens](10-screens-shared.md) apply to every card. All API IDs resolve to document 05; DB/contract behavior resolves to documents 04/06. None of these screens exists in the current repository.

## T01 — Create or revise project

- **Access/route/layout:** O `/projects/new` and `/projects/:projectId/edit`; G + wizard steps Identity → Site → Rules → Roles → Review. Edit route is the same page bound to a draft; published content offers New revision.
- **Fields/validation:** fictional organization read-only, name/code/description, case-study disclaimer acknowledgment. Name 3–120/code unique in namespace/description bounded; no claim of DBC affiliation. Site/policy references selected only from own project in later steps.
- **Buttons/API:** Create A06 →draft project/revision; Save A09 →ETag draft; New revision A08 with base/reason; Continue site→T02; Review/Activate A12 after checklist; A07 bootstrap on edit.
- **DB/chain:** create/update draft revision, audit; publish seals exact site/policy links. No chain on draft save; activation queues registerProject/roles/policy in dependency order.
- **Notifications/transitions:** N01 only publish; draft→configured→active with independent chain pending. Incomplete site/rules/role roster blocks publish; duplicate code field error; 409 reload draft; corrections create revision, not overwrite registered facts.
- **Tests:** UI-11, FLOW-01, SEC-03, DATA-01: idempotent create/publish, immutable old revision, validation and namespace isolation.

## T02 — Site/AOI registration

- **Access/route/layout:** O write/scoped readers `/projects/:projectId/site`; G + full map, coordinate/bounds/area summary, saved version list and source/provenance panel. Show no official tenure/DBC boundary claim.
- **Fields/validation:** site label, Polygon geometry with holes, source (`synthetic_drawn`/`synthetic_import`), reason for new version; WGS84 finite ranges, closed rings, topology, complexity cap, positive geodesic area, proposed business maximum 100 ha. GeoJSON import is a new bounded text/file form, not existing capability; reject MultiPolygon rather than discard pieces. No GMW-overlap requirement.
- **Buttons/API:** Draw/Edit/Import/Reset unsaved geometry; Save new version A11→SiteVersion, A10 history; select reference in draft A09; optional context A64/A65 with explicit dates/source mode; Open One `/analysis` without mutating project.
- **DB/chain:** immutable SiteVersion + raw input/normalized hash; project draft reference only if explicitly saved. Site digest anchored at project publication; optional snapshot context has no milestone approval effect.
- **Notifications/transitions:** no routine notification until N01 publish; draft geometry→saved version, context queued/live/no-data/unavailable independently. Invalid geometry remains editable with reasons; revised active site requires project/policy/task revision, no silent retargeting of old claims.
- **Tests:** UI-12, GEO-01–04, LEGACY-02: holes survive, no-data/degraded site allowed, area cap and import validation, old claims remain at original site.

## T03 — Fictional contract and verification/reward rules

- **Access/route/layout:** O edit, V/P/A/W scoped read `/projects/:projectId/rules`; G + version selector, contract summary, evidence/review tab, PLANTING/M3/M6 timeline, component table and computed examples.
- **Fields/validation:** task type/site version, synthetic agreement reference; independent field-review requirement; 3/6 month offsets, window/method/threshold; evidence profile; component code/kind/enabled, rate_minor/unit/cap/currency, required milestone mask; reason. Fixed primary offsets, disallow self-approval/automatic satellite-survival options. Positive bounded rates/caps, thresholds 0–100%, no duplicate components, enabled component requires Completion and known milestones. Show money in PKR plus read-only minor units.
- **Buttons/API:** A13/A17 load; Create draft A14; Save A15; Publish A16 with fictional acknowledgment; use A09 to pin published policy in project draft. Preview calculation never pays anything.
- **DB/chain:** policy/component/requirement versions immutable on publish; audit/outbox. publishPolicy sends exact digest and enforcement parameters after project chain registration; no change to existing assignments.
- **Notifications/transitions:** N01 published; draft→published→superseded. Validation blocks publish; chain rejection shows operation status without editing published rules; correction uses new policy and explicit future assignment scope. No retroactive rate/threshold edit.
- **Tests:** UI-13, POLICY-01–04, CHAIN-03/05: primary mask111, architecture supports separate completion/survival, server/contract amount parity.

## T04 — Task types, tasks and assignment configuration

- **Access/route/layout:** O write/project readers `/projects/:projectId/tasks`; G + five-type selector, task list, type-config drawer, task editor, worker/reviewer roster and Assign drawer.
- **Fields/validation:** type version, title/instructions, site/policy, quantity/unit, due date, checklist; type drawer allowlisted schema/profile/template options only. Worker/collector and three stage reviewers from eligible project memberships, assigned quantities bounded by published task. Supply may be pending at assignment; planting submit requires confirmed stock later.
- **Buttons/API:** A17/A18 read/create type version; A19 list; A20 create draft/A71 edit/A72 publish; A66 eligible roster; A21 assign `{worker_id,quantity,collector_id?,reviewer_ids}`→assignment/chain operation; Open assignment→W02. A21 DTO includes fixed independent reviewer roster for contract.
- **DB/chain:** type/task versions, assignment, milestones/obligation templates, audit/outbox; registerAssignment only after project/policy/roles confirmed. Assignment acceptance occurs on W02, not by coordinator impersonation.
- **Notifications/transitions:** N02 assignment, N03 worker acceptance/cancel; task draft→published, assignment assigned. Missing role/type/unit mismatch blocks; conflict denied; change published task/type uses new version; unstarted assignment cancellation audited, no deletion of completed work.
- **Tests:** UI-14, TASK-01–05, SEC-04, CHAIN-04: all five types use same architecture, pending supply assignment allowed, no duplicate/over-quantity assignment.

## T05 — Nursery batches catalog

- **Access/route/layout:** N create/scoped C/O/V readers `/projects/:projectId/nursery`; G + species/batch list and available/reserved/consumed counts; Create drawer.
- **Fields/validation:** fictional batch code/species; unique code within project, allowlisted species labels or bounded fictional text. No planting accepted quantity here.
- **Buttons/API:** A35→batch summaries; A36 `{code,species}`→batch; Open→T06. Read-only worker gets allocation summary via W02 rather than all private nursery records.
- **DB/chain:** NurseryBatch + audit on create; **no chain** until declaration/confirmation. No notification for empty batch creation.
- **Transitions/flows:** empty batch→declared through T06; duplicate code recoverable field error; inventory shows confirmed/allocated separately, never treats nursery headcount as field planting acceptance.
- **Tests:** UI-15, SUPPLY-01: catalog scope, code validation, supply-vs-planting labels.

## T06 — Supply declaration and independent confirmation

- **Access/route/layout:** N declare, assigned C confirm, O/V read `/nursery/:batchId`; G + declaration version, count/evidence, independent confirmation panel and allocation ledger.
- **Fields/validation:** declaration quantity/unit/available date/sealed nursery evidence; confirmer visit date, observed/accepted quantity, confirmation evidence, outcome/notes. Positive integer counts, accepted<=observed<=declared; exact declaration/evidence version, confirmer != declarer/beneficiary worker. Partial counts explicitly visible.
- **Buttons/API:** A37 bootstrap; Upload/Seal shared drawer; Submit declaration A38→immutable declaration; Confirm/Reject/Request changes A39→SupplyConfirmation/pending chain if approved; View operation A61. N corrects with new declaration base+reason A38.
- **DB/chain:** declaration/confirmation/evidence refs; inventory effective only confirmed quantities; declareSupply/confirmSupply actor signatures; confirmations never call approveMilestone or create reward eligibility.
- **Notifications/transitions:** N04 C handoff; N05 N/O/W result. Declared→confirmed/rejected/changes_requested; conflict/stale version denied; business-confirmed stock permits claim reservation/submission while chain supply pending blocks subject-chain publication until confirmed; allocation release/correction explicit, no editing consumed stock.
- **Tests:** UI-16, SUPPLY-01–04, CHAIN-04: self-confirm denial, version bind, concurrent over-allocation and nursery cannot approve planting.

## T07 — Shared claims catalog

- **Access/route/layout:** scoped `/projects/:projectId/claims`; G + type/worker/current-version/check/review/status table. W sees own, V assigned, P summaries, A redacted.
- **Fields/actions/API:** filter type/status/assignment, A76→ClaimSummary[]; Open exact revision→T08, worker New submission→W03, coordinator Assign review→T09/A41. Filters never imply access to all workers.
- **DB/chain:** reads only; no chain/no notification simply browsing.
- **Transitions/flows:** empty catalog links to permitted task action; show checking/blocked/approved exact version separately from anchor. Prior revision available in history, never mixed with current approval badge. Load error retains filters/retry.
- **Tests:** UI-17, SEC-03, VERSION-01: one claim visible through Trust and Steward, revision-specific status.

## T08 — Claim revision, checks and decisions

- **Access/route/layout:** scope-filtered `/claims/:claimId`; G + revision selector, work summary, sealed evidence, automatic checks, independent field report, monitoring/reward links and audit drawer.
- **Fields/actions/API:** A26 bootstrap/A62 check detail/A31 evidence/A60 audit; W Create correction A27 base/reason→W03; O Assign reviewer A41; authorized Open dispute A68 reason; A69 dispute/A61 pending operation. Read-only claim fields; never edit approved content inline.
- **DB/chain:** new draft revision or dispute/hold only from explicit action; viewing has none. Corrected submitted subject commits new digest; approved predecessor invalidation/review required before replacement; no fabricated successful anchor during correction.
- **Notifications/transitions:** N08 reviewer assignment, N19 dispute; exact claim revision checking→review_ready→approved/rejected/changes_requested; revision edits do not inherit old approval. Check errors retry through operation policy; hard failures require correction, flags require V resolution. Submitted empty/no-data science remains context only.
- **Tests:** UI-18, VERSION-01–04, CHECK-01–04, REC-04: stale corrections, exact approvals, held rewards after reversal.

## T09 — Review queue and assignment

- **Access/route/layout:** V own queue; O assignment view `/reviews`; G + claim/inspection tabs, due/flag badges and review assignment/reassignment drawer.
- **Fields/validation/actions:** filter project/type/status; O selects exact ready subject + eligible verifier, mandatory reassignment reason. A40→queue, A66 roster; A41 create/A74 reassign→new assignment+chain roster operation; Open→T10. Cannot choose a conflicted reviewer or bypass blocked checks.
- **DB/chain:** review assignment/notifications; reassignment holds dependent authority and replaces contract reviewer only with explicit prior-approval invalidation/re-review; never preserve old approval as new reviewer's work.
- **Notifications/transitions:** N08 new/previous reviewer; assigned→visit/review; no available independent verifier shows actionable roster blocker. Concurrent review decision vs reassignment locks same aggregate and returns conflict to loser.
- **Tests:** UI-19, SEC-04/07, REVIEW-01–04, REC-04: assignment and decision conflict checks, revoked/rotated reviewer recovery.

## T10 — Independent field review and decision

- **Access/route/layout:** assigned independent V `/reviews/:reviewAssignmentId`; G + side-by-side exact subject/policy/check/evidence and field-visit/decision form; worker cannot access decision controls.
- **Fields/validation:** read subject/site/policy/evidence digest/check profile; record independent verifier visit via W04 `purpose=review_visit`, field report/photos/inspection date, accepted planting quantity or verified survival counts; flag-resolution reasons; outcome/decision notes. Must bind exact target revision and verifier report. Counts match validated census or request subject correction; no final approval of blocked checks, wrong policy, missing visit, self-conflicted author or superseded subject.
- **Buttons/API:** A42→ReviewContext; Record field visit A46–A48; Approve/Reject/Request changes A43 DecisionDTO→immutable decision/chain operation; Open target/history links; poll A61. Client repeats explicit acceptance summary, no generic approve-current-version call.
- **DB/chain:** lock subject/review; store decision, accepted quantities, inventory consumption and milestones/eligibility jobs; chain approveMilestone for approval, commitOutcome for reject/changes; report/subject evidence commitments separate and bound.
- **Notifications/transitions:** N09 planting/N13 follow-up, N14 changed eligibility, N16/N17 chain outcome; submitted decision remains human-approved if chain fails, authority blocked until resolved. Correction to signed decision uses dispute/reversal, never PATCH. Reject retains evidence and sends worker next action.
- **Tests:** UI-20, REVIEW-01–04, MON-04, CHAIN-05–08, VERSION-02: exact-version decision, self-approval denial, field necessity, wrong-date/threshold cases and chain failure separation.
