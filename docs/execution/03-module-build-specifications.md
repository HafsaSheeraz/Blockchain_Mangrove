# 03 — Executable module build specifications

**PROPOSED throughout.** Module IDs M01–M16 below are authoritative execution owners, not already implemented code. `module(name)` expands to the six proposed backend filenames in 02. Routers use `require_session`, `require_project_scope`, `require_role` and `ensure_independent_actor` where specified; these are proposed shared dependencies. HTTP contracts/fields and detailed page behavior remain in [PB-1 API](../playbook/05-api-contracts.md)/[screens](../playbook/10-screens-shared.md), amended by [04](04-screen-api-event-matrix.md). DB/K/event IDs resolve in 05/06/04.

Each module's DoD requires its stated tests plus auth/conflict/error/retry/manual checks, audit/outbox integration and truthful pending states. No module's UI-only implementation satisfies DoD.

## M01 — Shared shell and authentication

- **Owner/roles/prerequisites:** platform/security owner; anonymous login then all seeded roles. WP01/WP02; DB00–DB02; initial local organization/users from controlled bootstrap.
- **Build:** module(identity); `SessionSchema,LoginRequest,SessionContext`; `bootstrap_session,login,logout,authorize_scope`. A01–A04; session/CSRF/Origin deps. Frontend `src/app/{ApplicationShell,SessionProvider,ProtectedRoute}.jsx`, `src/pages/platform/{Login,Dashboard}.jsx`; S01/S02.
- **Data/integration:** users/sessions/org/project memberships; no duplicate module auth. Logout revokes current session; future command role checks use current membership but not expired browser session.
- **States/failures:** anonymous → authenticated → expired/revoked;401 login redirect,403 CSRF,429 throttle; failed login no session;409 stale client refresh. No passwords in logs or localStorage.
- **Chain/inbox:** no login chain transaction or notification; dashboard consumes shared inbox.
- **Tests/DoD:** UI-01/02, SEC-01–03/08, P2-07; login → role dashboard → logout, forged role denied. Complete only when authenticated server checks and safe redirects work. Related PB-1 F02/F05.

## M02 — Organization and project management

- **Owner/roles/deps:** O business owner; S controls memberships; scoped readers. M01, WP03, DB03. Single fictional org seeded; no organization signup UI.
- **Build:** module(projects); `ProjectDraft,ProjectRevision,ProjectWorkspace`; `create_project,revise_project,publish_project,transition_project`; A05–A09/A12/A83. Session+organization/project role checks. `src/pages/platform/{Projects,ProjectWorkspace,ProjectEditor}.jsx`; S03/S04/T01.
- **Data:** org → project → immutable revision; select exact site/policy plus nursery confirmer; publication creates event/Operation and chain dependency graph, not actual chain success.
- **State/recovery:** draft → configured → active; active↔suspended; closed terminal (new work denied). Save is reversible draft; published correction appends revision.409 stale publish,422 incomplete configuration; chain outage keeps business record and pending status. Suspension holds obligations immediately.
- **Chain/inbox:** K02/K03/K05; EV-01/N01, EV-16/N19; project roster links all modules.
- **Tests/DoD:** UI-03/04/11, DATA-01/02, FLOW-01, P2-13; one project through Trust/Steward, stable code and exact versions, idempotent publish. PB-1 P01.

## M03 — Site/AOI and Mangrove One adapter

- **Owner/roles/deps:** O owns site; V/W consume scoped context. M02, WP03 (site)/WP12 context; DB03/DB11.
- **Build:** module(sites), `SiteVersionCreate,AnalysisSnapshotRequest,SnapshotDetail`; `save_site_version,capture_context,get_snapshot`; A10/A11/A64/A65. New `SiteEditor.jsx`, `ContextSnapshotPanel.jsx`, `businessGeometry.js`; T02/S06, existing E01/E02 preserved.
- **Data:** valid Polygon/raw JSON/digest/geodesic area; optional snapshot references same site and milestone. Adapter `backend/app/integrations/gis_adapter.py` calls existing science services, supplements provenance, stores exact bytes/results. No stock/reward writes.
- **States/failures:** saved site immutable; snapshot queued → live/fixture/no_data/unavailable. Holes and finite coordinates retained; invalid topology/area>100 ha rejected; no-GMW allowed. EE error leaves field workflow usable; failed snapshot can retry a new operation without rewriting old source mode.
- **Chain/inbox:** site digest via project/policy; no survival bit from context; no routine fanout.
- **Tests/DoD:** GEO-01–04, LEGACY-01–04, MON-04/06, UI-12; context errors/no-data and hole preservation visible. PB-1 P01/P04.

## M04 — Policy and configurable task definitions

- **Owner/roles/deps:** O, V/P/W scoped read. M02/M03; WP03/WP04; DB04.
- **Build:** module(policies) and task-type schema support in module(tasks); `PolicyDraft,PolicyComponent,TaskTypeVersion`; `validate_policy,publish_policy,publish_task_type`; A13–A20/A71/A72/A79/A82. `RulesEditor.jsx,TaskConfiguration.jsx`; T03/T04.
- **Data:** site/type/policy/task versions and component requirements; canonical structured agreement avoids PDF/upload dependency. Primary profile immutable D01; other five-type configurations allowed within server schema/role allowlists.
- **State/failures:** drafts → published → superseded; reject duplicate components/unknown milestones/invalid thresholds/unit mismatch; new policy applies only to future pinned assignments. No code execution from configuration.
- **Chain/inbox:** K06 policy/task type commitment with primary constants; EV-01/N01. No reward issued at publish.
- **Tests/DoD:** POLICY-01–04, UI-13/14, CHAIN-03, P2-04/14; API/contract/draft preview agree on primary formula/mask 7. PB-1 P02.

## M05 — Worker assignment

- **Owner/roles/deps:** O assigns, W accepts/starts, V fixed stage roster. M04/M01; WP04; DB05.
- **Build:** module(tasks); `AssignmentCreate,AssignmentTransition,AssignmentDetail`; `assign_task,accept_assignment,start_assignment,cancel_assignment`; A21–A23/A75/A79. `MyTasks.jsx,AssignmentDetail.jsx`; W01/W02/T04.
- **Data:** pin exact task/policy/site; worker/collector/stage reviewer roster; create unique obligation/milestone templates later enriched without duplicates. Total assignment quantities bounded under task lock.
- **State/failures:** assigned → accepted → in_progress → submitted → verified_complete; rejected/changes_requested/cancelled explicit. Assignment may precede nursery supply. Claim submit cannot. Wrong worker 403, over-quantity 422, duplicate 409, stale 409. Submitted/accepted work cancel uses dispute, preserves history.
- **Chain/inbox:** K07/K08/K09; initial pre-Sprint 5 chain state awaiting_dependency; EV-02/03 → N02/03; next worker W01.
- **Tests/DoD:** TASK-01–05, UI-21/22, SEC-04, P2-03; complete accept/start/cancel with ownership, no checkbox approval. PB-1 P03.

## M06 — Nursery supply and confirmation

- **Owner/roles/deps:** N declares, assigned C confirms; O roster/inventory owner. M02/M05/M07; WP06; DB07.
- **Build:** module(nursery); `BatchCreate,SupplyDeclaration,SupplyDecision,InventorySummary`; `declare_supply,confirm_supply,reserve_supply,consume_supply,release_supply`; A35–A39, project default C via A09. `NurseryBatches.jsx,NurseryBatch.jsx`; T05/T06.
- **Data:** snapshot C per declaration, exact evidence and observations; stock rows locked in sorted order; same-project positive allocations; multiple confirmations supported up to 8 per claim.
- **State/failures:** declared → confirmed/rejected/changes_requested; reserved → consumed/released. accepted<=observed<=declared; mismatch 422; insufficient/unconfirmed supply 409; same-person confirmation 403. New declaration/reversal not editing consumed counts; revisions transfer unconsumed reservations atomically.
- **Chain/inbox:** K10–K13; supply state never Completion approval; EV-04/05 → N04/05 to C, N, O, affected W.
- **Tests/DoD:** SUPPLY-01–04, UI-15/16, P2-02/15; concurrency prevents over-reservation and self-confirmation. PB-1 T01-B.

## M07 — Evidence upload, sealing and versioning

- **Owner/roles/deps:** subject author uploads, V reviews, A redacted access. M01/M02; WP05; DB06; private versioned object adapter.
- **Build:** module(evidence); `UploadSlot,CompleteUpload,EvidenceVersion,EvidenceSet`; `issue_upload,finalize_upload,validate_object,seal_set,check_integrity`; A29–A34/A63/A81. `EvidenceLibrary.jsx,EvidenceUploader.jsx,EvidenceSetEditor.jsx`; S05 and shared drawers.
- **Data:** exact bytes/object version/server hash; immutable category/order/capture provenance; purpose and scoped concrete subject/assignment target. Sealed set never gains a new file; replace creates version/set/revision.
- **State/failures:** pending → quarantined → valid/rejected; draft set → sealed. Size/type/expired slot invalid; no seal pending/rejected object. Corruption immediately holds affected unpaid obligations, not silent replace. Retry same upload completion idempotent.
- **Chain/inbox:** manifest bound into subject/decision only; no universal evidence approval; EV-06 integrity → N19; normal uploads no fanout.
- **Tests/DoD:** EVID-01–08, SEC-05, UI-05, P2-12/16; private exact bytes recover after restart. PB-1 F04.

## M08 — Automated screening

- **Owner/roles/deps:** technical screening service; W corrects, V resolves flags. M05/M06/M07; WP07; DB08.
- **Build:** module(screening); `CheckRun,Finding,CheckInput`; `enqueue_checks,run_checks,classify_findings`; A28/A48 submit plus A62/A61; `CheckResults.jsx` in T08/W03/T10.
- **Data:** sealed subject hash/check profile/version; hard/soft findings; same input+profile coalesces, reruns append outcomes. Checks never mutate subject or decide field truth.
- **State/failures:** queued → running → passed/passed_with_flags/blocked/error. Hard fail → new correction revision; engine failure → safe retry, no pass. Cross-scope/missing evidence/stock fail; duplicate-photo/GPS uncertain flagged for field resolution.
- **Chain/inbox:** commitSubject waits for passed/flagged valid input; no approval bit from screening; EV-07 → N06/07/08; reviewer receives ready exact revision.
- **Tests/DoD:** CHECK-01–04, UI-18/23, VERSION-03, P2-12; missing evidence and checker outage clearly different. PB-1 T02-B.

## M09 — Independent field verification

- **Owner/roles/deps:** assigned V; O assigns independent roster; W cannot approve. M08 and base observation/report persistence; WP08; DB09.
- **Build:** module(trust); `ReviewAssignment,DecisionCreate,ReviewContext,DisputeResolution`; `assign_review,record_decision,reassign_review,resolve_field_dispute`; A26/A27/A40–A43/A68–A70/A74/A80. `Claims.jsx,ClaimDetail.jsx,ReviewQueue.jsx,FieldReview.jsx`; T07–T10.
- **Data:** exact claim/evidence/site/policy/check + independent report revision; typed FK target; separate observational author and report author. Conflicts checked assignment and commit. Verified quantity<=claim<=assignment; true acceptedQ fixes cohort.
- **State/failures:** review_ready → under_review → approved/rejected/changes_requested. Wrong actor 403, stale 409, missing visit 422; corrections create new version/recheck/review. Revoked reviewer recovery invalidates future use, does not rewrite prior attribution.
- **Chain/inbox:** K14–K18/K08; EV-08/16 → N09/13/19; W gets correction/decision, P gets readiness summary only.
- **Tests/DoD:** REVIEW/VERSION families, UI-17–20, SEC-04/07, P2-01/11/12. Accepted planting is not final eligibility. PB-1 T03-B.

## M10 — Follow-up scheduling and field survival

- **Owner/roles/deps:** W/assigned collector observes, distinct V independently visits/decides. M09/M04/M03; WP11/WP12; DB11, existing DB09 reports.
- **Build:** module(monitoring); `MilestoneDetail,ObservationDraft,ReviewVisitDraft`; `schedule_followups,record_observation,submit_observation,evaluate_survival`; A44–A48/A80; W04/S06 and `MonitoringBoard.jsx,InspectionEditor.jsx`.
- **Data:** parent Completion decision FK, originalQ/cohort, due/grace windows, census counts, evidence and independent report. Schedule from accepted planting date; follow-ups cannot migrate to replacement parent.
- **State/failures:** scheduled → due/overdue → observation_submitted → under_review → passed/failed. Missing pending; verified low survey fails threshold even if review approved; disputed held. Satellite insufficient follows same field form. Dates early 422, late requires reason and V acceptance; count mismatch 422.
- **Chain/inbox:** K14/K15 exact parent; EV-09/10 → N10–N13; next V review, then evaluator.
- **Tests/DoD:** MON-01–06, FLOW-03, P2-01/10/14; both mandatory, no science-derived survival. PB-1 M01.

## M11 — Blockchain commitments and enforcement

- **Owner/roles/deps:** restricted actor-bound runner; technical ops admin, all business signers. M04/M06/M09; WP09/WP10; DB10/base DB02.
- **Build:** module(chain), `ChainCommand,ReceiptProjection`; `plan_commands,sign_command,submit_command,reconcile_command,reset_deployment`; A61/A73/A77/A78 read/ops; `ChainStatus.jsx` S08/S10/W07. Solidity/K/events in 06.
- **Data:** immutable actor binding, deployment generation, chain commands/dependencies, nonce+signed bytes+tx hash before send, receipt/canonical depth; no raw keys in DB.
- **State/failures:** queued → submitted → mined → confirmed; unknown/reverted/orphaned/retry_wait/blocked explicit. Duplicate event reconciles; conflicting digest quarantined; chain reset archives old projections/new domain, no economic reset.
- **Notifications:** EV-11 → N16/17; permission changes EV-17/N20. Ancillary audit cannot mutate workflow.
- **Tests/DoD:** CHAIN-01–12, REC-01–06, P2-01/02/04/08/09; direct RPC negative calls reject invalid workflow independently of API. PB-1 C01–C04.

## M12 — Eligibility and payment authorization

- **Owner/roles/deps:** evaluator computes, separate P authorizes. M09/M10/M11; WP13; DB12.
- **Build:** module(rewards); `EligibilityEvaluation,ObligationDetail,AuthorizationRequest`; `evaluate_obligation,request_authority,cancel_authority`; A49–A54/A68; `RewardList.jsx,RewardDetail.jsx,AuthorizationDetail.jsx`; W05–W07.
- **Data:** stable assignment+component obligation, exact dependency rows/digest/formula snapshot; unique active authority; person/signature conflicts, only current effective decisions.
- **State/failures:** pending_requirements → eligible/ineligible; held/revoked when source disputed; human approved_pending_chain/rejected/cancelled distinct. Chain confirmed projects authorized.422 wrong amounts;409 missing/stale/duplicate; no client eligible toggle. Q*1000 cap 1 m, never live count.
- **Chain/inbox:** K19/K20; EV-12/13 → N14/15/16/17; next P dispatch only after canonical authority.
- **Tests/DoD:** REWARD/PAY-01–03, CHAIN-05–08, P2-01/05/14; missing either survey prevents final. PB-1 M02/M03.

## M13 — Simulated settlement/history

- **Owner/roles/deps:** P requests, restricted local simulator executes, W reads own. M12; WP14; DB13.
- **Build:** module(settlement), `SettlementRequest,SettlementAttempt,SimulatedReceipt`; `enqueue_settlement,execute_simulation,reconcile_simulation`; A55/A56/A53; `SettlementDetail.jsx` W08.
- **Data:** economic obligationUUID dedupe across chain reset/authority replacement; atomic durable local receipt; executing authority/amount retained; one receipt per obligation.
- **State/failures:** queued → processing → simulated_settled/failed/unknown/held. Known failure safe retry same key; unknown lookup first; dispute wins serialization before receipt or marks existing receipt disputed after. Chain audit may remain pending/reverted after local success; no second simulation.
- **Chain/inbox:** K21 ancillary discrepancy K22; EV-14/N18, EV-16/N19; W sees explicit fictional receipt.
- **Tests/DoD:** PAY-04–06, REC-03/05, UI-27/28, P2-05/06/09. No financial provider/real transfer package. PB-1 S01-B/S02-B.

## M14 — Notifications/activity

- **Owner/roles/deps:** shared platform event/inbox owner; each role own inbox. Foundation WP02, handoffs all features, final WP15; DB01/DB14.
- **Build:** module(notifications), workers/outbox/scheduler; `NotificationIntent,Notification,ReadState`; `resolve_recipients,deliver_once,mark_read`; A57/A58/A04; `Notifications.jsx,InboxBadge.jsx` S07/S02.
- **Data:** immutable AuditEvent references, event/recipient/template uniqueness, scope checked delivery/read; no separate module inboxes.
- **State/failures:** intent pending → delivered; own unread → read; worker crash retries delivery only. Revoked access hides target/payload; no duplicate on replay; meaningful change notifications, not polling spam.
- **Chain/inbox:** consumes EV-01–EV-17 and PB-1 N01–N20; none for read-state mutation; never signs a chain approval.
- **Tests/DoD:** NOTIF-01–04, SEC-06, UI-07, P2-17; all next-role handoffs observable throughout vertical slice. PB-1 F03/T04-B.

## M15 — Audit/reporting

- **Owner/roles/deps:** A scoped audit, W own, O/P role-redacted summaries. M14/M11; WP15; DB01/DB10/DB14.
- **Build:** module(audit); `AuditDetail,BusinessReport`; `get_timeline,verify_commitment,export_business_report`; A59/A60/A63/A84; `AuditTimeline.jsx,BusinessReportDrawer.jsx` S08.
- **Data:** exact versions, before/after status, signer/deployment/canonical receipts, scientific source modes; report manifest generated from authorized immutable snapshot, not rerun science.
- **State/failures:** reads no workflow mutation; export JSON/CSV with no-store/formula protection, capped authorized scope; missing chain shows pending/unavailable; mismatch holds dependencies through integrity protocol. Corrections retained.
- **Chain/inbox:** reads K23–K31, audit-only K22 if needed; report reads no inbox fanout.
- **Tests/DoD:** UI-08, EVID-08, LEGACY-03, P2-08/18; no fake explorer link or conflated payment proof. PB-1 S04-B.

## M16 — Administration/demo setup

- **Owner/roles/deps:** S technical operations only; fixture actors separate. Foundation WP00–02, final WP17; DB02/DB14.
- **Build:** module(administration); `MembershipChange,OperationDetail,Readiness`; `change_membership,retry_operation,assess_readiness`; A66/A67/A73/A77/A78/A83 permitted admin pause only. `AccessAdmin.jsx,Operations.jsx`; S09/S10; later seed/reset/deploy CLI proposed in 10.
- **Data:** grants/revocations, signer bindings/deployment registry, leases/run manifests; no raw keys/content bypass.
- **State/failures:** membership active/revoked, chain grant pending/confirmed; retries only after reconciled absence, never force success. Chain reset explicitly creates generation and preserves economic receipts; no production reset UI.
- **Chain/inbox:** K01/K04/K05; EV-17/N20, EV-11/N17; technical pause allowed, human review never impersonated.
- **Tests/DoD:** SEC-07, REC families, UI-09/10, P2-07/09/13; reproducible safe namespace setup and report of actual results. PB-1 S04-B/S05-B.
