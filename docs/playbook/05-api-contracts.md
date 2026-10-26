# 05 — API contracts

**PROPOSED `/api/v1` APIs only.** Existing scientific endpoints remain unchanged (historical audit lists them). Operation IDs below are referenced by screen cards and tests; they are not existing handlers. Prefix every relative path below with `/api/v1`.

## Common wire contract

- JSON UTF-8; UUIDs as strings; UTC ISO timestamps; business dates `YYYY-MM-DD`; decimal quantities as canonical strings; money integers in minor PKR units; hashes `0x` + 64 lowercase hex digits. Reject unknown mutable fields and client-asserted actor/scope.
- Session cookie + CSRF/Origin rules from permissions document. `Idempotency-Key` required on every POST command, login excepted. `If-Match: "<row_version>"` required on draft PATCH and transitions involving mutable projections. Server supplies `ETag`/`row_version`; omitted precondition 428, stale 409.
- List response `{data:[...],page:{next_cursor,has_more}}`, stable `(created_at,id)` cursor, default 25/max 100; authorized scope and allowlisted filters only. GET detail returns `{data:{...},meta:{request_id}}`.
- Synchronous create 201, synchronous update 200, logout 204. Commands with external work return 202 and `{data:resource,operation:{id,state,url},meta:{request_id}}`. 202 means durable DB acceptance, not successful anchoring or settlement. Command idempotent replay returns its prior resource/operation without creating side effects.
- Error `{error:{code,message,field_errors:[{path,code,message}],retryable,current_version?,blocking_refs?},meta:{request_id}}`. Codes: 400 malformed input; 401 session; 403 role/conflict/CSRF; 404 invisible/not found; 409 transition, reused key/different digest, duplicate business obligation or stale revision; 413 bytes; 415 type; 422 validation; 428 precondition; 429 rate limit; 503 dependency unavailable. Same idempotency key/different payload is never treated as a retry.
- `status` objects expose dimensions separately: `business`, `eligibility`, `authorization`, `blockchain`, `settlement`. `allowed_actions` is server-derived and does not replace reauthorization on command. Sensitive raw keys/URLs/worker data are omitted from other roles' DTOs.
- Writes atomically create AuditEvent + outbox intents unless explicitly stated. Notifications are eventual; business response must not wait for inbox delivery. All async operations have A61 polling with retryability and safe failure details.

## Endpoint catalog

| ID | Method / path | Request → response; permission / side effect |
| --- | --- | --- |
| A01 | GET `/session` | Anonymous/authenticated bootstrap → user, organization/project role summaries, csrf_token, expires_at; no password data. |
| A02 | POST `/session/login` | login/password + anonymous CSRF → rotated session/user context; rate limit; generic failure. |
| A03 | DELETE `/session` | CSRF → 204; revoke session and clear cookie. |
| A04 | GET `/dashboard` | optional project filter → authorized counts, due work/reviews, payment states, latest safe notifications. |
| A05 | GET `/projects` | cursor/state → ProjectSummary[]; scope filtered. |
| A06 | POST `/projects` | `{name,code,description}` → draft Project + initial revision; O in organization. |
| A07 | GET `/projects/{id}` | → ProjectWorkspace (revision/site/policy summaries, allowed actions, states, module counts). |
| A08 | POST `/projects/{id}/revisions` | `{base_revision_id,reason}` → new mutable revision; no overwrite of published revision. |
| A09 | PATCH `/project-revisions/{id}` | name/description/site_version_id/policy_version_id → updated draft; O + ETag. |
| A10 | GET `/projects/{id}/site-versions` | → SiteVersion[] incl geometry/bounds/hash/area/source. |
| A11 | POST `/projects/{id}/site-versions` | `{site_id?,base_version_id?,geometry,label,source,reason}` → immutable SiteVersion; O; validate full polygon. |
| A12 | POST `/project-revisions/{id}/publish` | `{expected_site_version_id,expected_policy_version_id}` → active revision + chain operation; O; complete roles/config required. |
| A13 | GET `/projects/{id}/policy-versions` | → PolicyVersion[] and components/requirements. |
| A14 | POST `/projects/{id}/policy-versions` | PolicyDraft including site/type version/criteria/components → draft policy. |
| A15 | PATCH `/policy-versions/{id}` | mutable policy fields → draft; ETag, O; no published edits. |
| A16 | POST `/policy-versions/{id}/publish` | `{acknowledge_fictional:true}` → immutable hash/version; chain policy command deferred until project registration if necessary. |
| A17 | GET `/task-types` | → five codes, published versions/form schemas/checklists/templates in org. |
| A18 | POST `/task-types/{code}/versions` | bounded allowlisted config → new published TaskTypeVersion; O; cannot insert executable rules. |
| A19 | GET `/projects/{id}/tasks` | type/status/assigned_to=me/cursor → TaskSummary/AssignmentSummary[] in scope. |
| A20 | POST `/projects/{id}/tasks` | TaskDraft → draft TaskRevision; O. |
| A21 | POST `/task-revisions/{id}/assignments` | `{worker_id,quantity,collector_id,reviewer_ids:{COMPLETION,M3?,M6?}}` → assignment + chain operation; O; published task/site/policy, valid membership, independent reviewer roster, bounded total allocations; plantation UI labels COMPLETION as PLANTING. |
| A22 | GET `/assignments/{id}` | → Task/Assignment/claim/supply/milestone/component summary; owner W or relevant scoped roles. |
| A23 | POST `/assignments/{id}/transitions` | `{action:"accept"|"start"|"cancel",reason?}` → assignment; W own accept/start, O cancel if no conflicting settled work; ETag. |
| A24 | POST `/assignments/{id}/claims` | ClaimDraft → Claim + draft revision; W own; unique claim per assignment. |
| A25 | PATCH `/claim-revisions/{id}` | claimed quantity/date/site/form/evidence_set_id/supply allocations → draft; W, ETag. |
| A26 | GET `/claims/{id}` | → revisions, exact evidence/check/review references, allowed actions and four status dimensions. |
| A27 | POST `/claims/{id}/revisions` | `{base_revision_id,reason}` → correction draft; reject if dispute/approved replacement protocol unresolved. |
| A28 | POST `/claim-revisions/{id}/submit` | `{evidence_set_digest,policy_version_id,acknowledgments}` → immutable submitted claim + check operation; atomic inventory reservation. |
| A29 | POST `/projects/{id}/evidence/uploads` | `{asset_id?,filename,declared_mime,size_bytes,caption}` → UploadSlot `{upload_id,object_upload_url,required_headers,expires_at}`; authorized subject participant. |
| A30 | POST `/evidence/uploads/{id}/complete` | `{object_version,declared_sha256?}` → quarantined EvidenceVersion + validation operation; server recomputes hash/size/MIME. |
| A31 | GET `/evidence-versions/{id}` | → metadata, validation/integrity state and authorized usage; no permanent public object URL. |
| A32 | GET `/evidence-versions/{id}/download` | → short-lived signed URL/expiry or stream with no-store; authorization + access audit; original/redacted variant explicit. |
| A33 | POST `/projects/{id}/evidence-sets` | `{items:[{evidence_version_id,category,order}]}` → draft set. |
| A34 | POST `/evidence-sets/{id}/seal` | `{expected_item_ids}` → immutable manifest/digest; reject pending/rejected objects; exact-version validation. |
| A35 | GET `/projects/{id}/nursery-batches` | → batch/declaration/confirmation/inventory summaries. |
| A36 | POST `/projects/{id}/nursery-batches` | `{code,species}` → batch; assigned N. |
| A37 | GET `/nursery-batches/{id}` | → declaration history, sealed evidence, confirmations, reserved/consumed/available quantities. |
| A38 | POST `/nursery-batches/{id}/declarations` | `{quantity,unit,available_date,evidence_set_id,base_declaration_id?}` → immutable declaration; N, sealed set; notify C. |
| A39 | POST `/supply-declarations/{id}/confirmations` | `{outcome,observed_quantity,accepted_quantity,visit_date,evidence_set_id,notes}` → SupplyConfirmation + chain command for approval; C distinct from declarer. Reject/changes-requested append outcomes, not inventory. |
| A40 | GET `/reviews` | assignee=me/status/subject_type → queue; V own, O safe assignment view. |
| A41 | POST `/projects/{id}/review-assignments` | `{claim_revision_id? ,inspection_revision_id?,verifier_id}` → assignment; O; exactly one subject, no conflict, verifier matches the assignment's current stage roster; use A74 for a different reviewer. Review-ready jobs may create the same deterministic assignment automatically; no duplicate reviewer notification. |
| A42 | GET `/review-assignments/{id}` | → exact subject/policy/checks/evidence and field-visit/decision form context; assigned V. |
| A43 | POST `/review-assignments/{id}/decisions` | DecisionDTO → immutable decision + chain command on approved outcome; V; field inspection required, exact versions and flags checked. |
| A44 | GET `/projects/{id}/milestones` | status/due/assigned_to=me → shared monitoring rows with due dates/inspection/context states. |
| A45 | GET `/milestones/{id}` | → criteria, cohort, due/window, observation/review history, related work. |
| A46 | POST `/milestones/{id}/inspections` | InspectionDraft + `{purpose:"observation"|"review_visit",review_assignment_id?}` → inspection revision; assigned collector for observation or assigned V for review_visit; planting review uses PLANTING milestone tied to submitted claim. A verifier report never becomes the worker's observation or replaces its active revision. |
| A47 | PATCH `/inspection-revisions/{id}` | method/date/counts/notes/context/evidence_set → draft; own inspector + ETag. |
| A48 | POST `/inspection-revisions/{id}/submit` | exact evidence digest/late reason → submitted observation + checks/review handoff; independent reviewer required if submitter is W. V may submit a field visit and decide another person's claim/observation, but cannot approve their own standalone monitoring-work claim. |
| A49 | GET `/projects/{id}/eligibilities` | → reward obligations/component states and safe input summaries; W own, P/O/A scoped. |
| A50 | POST `/reward-obligations/{id}/evaluate` | `{expected_dependency_ids:[...]}` optional concurrency expectation → appended EligibilityEvaluation; service, P or O trigger; result calculated server-side. |
| A51 | GET `/reward-obligations/{id}` | → exact policy formula, requirements/decisions, eligibility history, amount, authorization/chain/settlement states. |
| A52 | POST `/reward-obligations/{id}/authorizations` | `{outcome:"approved"|"rejected",eligibility_evaluation_id,expected_amount_minor?,currency?,reason}` → human approval pending chain + operation, or rejected authorization history without chain authority; P independent. Approval requires expected amount/currency; client amount is comparison only, never authority. Rejection does not occupy active authority slot. |
| A53 | GET `/payment-authorizations/{id}` | → frozen inputs, authorizer, chain prerequisite/command states and settlement links. |
| A54 | POST `/payment-authorizations/{id}/cancel` | `{reason}` → immediate DB hold + cancellation chain command; P/O authorized dispute path, cannot erase settlement receipt. |
| A55 | POST `/payment-authorizations/{id}/settlements` | `{acknowledge_simulated:true}` → queued attempt + operation; P, only if confirmed chain authorization/no holds; simulator service executes. |
| A56 | GET `/settlement-attempts/{id}` | → simulated status/reference/amount/failure/reconciliation and audit status. |
| A57 | GET `/notifications` | unread/cursor → own safe inbox entries/count. |
| A58 | POST `/notifications/{id}/read` | `{read:true}` → own read state; no chain event or notification fanout. |
| A59 | GET `/projects/{id}/audit-events` | aggregate/type/cursor → append-only scoped timeline with business/chain/inbox times. |
| A60 | GET `/audit-events/{id}` | → canonical commitment, actor pseudonym, exact subject links, deployment/receipt and integrity metadata in scope. |
| A61 | GET `/operations/{id}` | → durable operation state/dependencies/result/error/retry_after; owning scope only. |
| A62 | GET `/check-runs/{id}` | → profile/input digest/findings/status; no raw private evidence in response. |
| A63 | POST `/evidence-versions/{id}/integrity-checks` | `{expected_sha256?}` → server re-read/hash operation → match/mismatch; V/A authorized version; caller digest not trusted. |
| A64 | POST `/site-versions/{id}/analysis-snapshots` | `{region_key,start_date,end_date,milestone_id?,mode:"live"|"fixture"}` → operation; fixture mode enabled only isolated demo namespace. |
| A65 | GET `/analysis-snapshots/{id}` | → stored result/provenance/units/warnings/mode/export refs; no reanalysis side effect. |
| A66 | GET `/projects/{id}/memberships` | → role roster/conflict-safe summaries; O/S and scoped summaries to V/P. |
| A67 | POST `/projects/{id}/membership-changes` | `{user_id,role,action:"grant"|"revoke",reason}` → membership + role chain operation; S; actor binding fixed. |
| A68 | POST `/projects/{id}/disputes` | `{target_type,target_id,reason}` → dispute + immediate holds; O/V/P or affected W; no unilateral approval reversal by worker. |
| A69 | GET `/disputes/{id}` | → scope-filtered dispute/dependency/correction history. |
| A70 | POST `/disputes/{id}/resolve` | `{outcome:"uphold"|"reverse",replacement_revision_id?,reason}` → decision reversal/holds/revalidation commands; independent assigned V and P for authorization consequences; S cannot adjudicate. |
| A71 | PATCH `/task-revisions/{id}` | TaskDraft fields → draft + ETag; O. |
| A72 | POST `/task-revisions/{id}/publish` | `{acknowledge_requirements:true}` → immutable task revision; O; site/type/policy valid. |
| A73 | POST `/operations/{id}/retry` | `{reason}` → same command requeued after reconciliation; S operations scope; not a bypass for invalid/revoked business inputs. |
| A74 | POST `/review-assignments/{id}/reassign` | `{verifier_id,reason}` → replacement assignment + chain roster command; O; conflict checks; hold/cancel active authority and revoke/review affected approval before replacement becomes effective. |
| A75 | GET `/assignments` | assigned_to=me/project_id/type/status/cursor → authorized assignment summaries across projects; W own, O scoped roster. |
| A76 | GET `/projects/{id}/claims` | status/type/assignment/cursor → scoped ClaimSummary[] with current revision and version-bound decisions. |
| A77 | GET `/operations` | project/type/state/cursor → S-only operational summaries without evidence payloads or signer secrets. |
| A78 | GET `/system/readiness` | DB/schema/object-store/worker capability status and explicit chain/EE degradation; safe summary only, detailed failure diagnostics S-only. Does not replace or relabel existing `/ready`. |

No email/SMS send, token transfer, wallet balance, NFT or credit endpoints exist in this design. Object-store upload uses the A29 bounded signed slot, not a second unscoped upload API. Read/download access logging is explicitly permitted but never sends inbox fanout.

## Named request DTOs

`TaskDraft`: `{title,type_version_id,policy_version_id,site_version_id,quantity:"1000",unit:"seedling",due_date,instructions,evidence_profile_id}`. Unit/type/config compatibility enforced; assigned quantities across workers cannot exceed task quantity without a new task revision. `ClaimDraft`: `{work_date,claimed_quantity:"1000",unit:"seedling",site_version_id,policy_version_id,form:{species,plot_ref},evidence_set_id,supply:[{confirmation_id,quantity:"1000"}]}`.

`PolicyDraft`: `{site_version_id,task_type_version_id,verification:{method:"field_visit",independent:true},milestones:[{code:"M3",offset_months:3,window_days:14,method:"census",minimum_survival_bps:8000},{code:"M6",offset_months:6,window_days:14,method:"census",minimum_survival_bps:7500}],components:[{code:"final_reward",kind:"final_reward",enabled:true,rate_minor:1000,unit:"seedling",cap_minor:1000000,requires:["PLANTING","M3","M6"]}],evidence_profile_id}`. These numbers are **proposed fictional defaults**, approval decision D01, not validated DBC practice. Policy DTO rejects a required-mask that references a nonexistent milestone, duplicate payable component codes, negative rates or a policy without independent review.

`InspectionDraft`: `{visit_date,method:"census",original_cohort_count:1000,live_count:900,dead_count:70,missing_count:30,location:{lon,lat,accuracy_m,source},context_status:"satellite_insufficient",analysis_snapshot_id?,notes,evidence_set_id,late_reason?}`. PLANTING visit uses accepted planted count plus planting-visit evidence instead of survival counts; discriminated schema by milestone code prevents mixing them.

`DecisionDTO`: `{subject_revision_id,subject_evidence_digest,policy_version_id,check_run_id,field_inspection_revision_id,outcome:"approved"|"rejected"|"changes_requested",accepted_quantity?,flag_resolutions:[{finding_id,resolution}],notes}`. Claim approval requires PLANTING field visit; follow-up decision requires submitted M3/M6 inspection. The person who recorded their own worker monitoring claim cannot decide that claim. Assigned independent V may record their field visit directly and sign the decision on the worker's subject; the decision binds both evidence sets.

## Example submission and pending response

```http
POST /api/v1/claim-revisions/claim-rev-uuid/submit
Content-Type: application/json
Idempotency-Key: submit-plantation-rev-1
If-Match: "4"
X-CSRF-Token: <session-bound token>

{"evidence_set_digest":"0x<64-hex>","policy_version_id":"policy-uuid","acknowledgments":["fictional_demo","statement_of_work"]}
```

```json
{
  "data": {
    "id": "claim-uuid",
    "revision_id": "claim-rev-uuid",
    "row_version": 5,
    "evidence_set_id": "set-uuid",
    "status": {"business":"checking","eligibility":"pending_requirements","authorization":"not_requested","blockchain":"queued","settlement":"not_requested"},
    "allowed_actions": ["view_evidence","view_checks"]
  },
  "operation": {"id":"operation-uuid","state":"queued","url":"/api/v1/operations/operation-uuid"},
  "meta": {"request_id":"request-uuid"}
}
```

UUID/hash placeholders above are illustrative, not literal accepted values. An approval response likewise returns an immutable decision and pending chain operation; it must not invent a transaction hash before submission. A reverted chain command leaves the recorded human decision visible, marks its chain state failed and prevents authorization until reconciled/corrected.

## Projection DTO requirements

ProjectWorkspace includes `site_version_id`, `policy_version_id`, source-mode badges and module counts; AssignmentDetail includes exact task/policy version, assigned actor and supply requirements; ClaimDetail includes revision history/checks/decisions; MonitoringRow includes due/window/observation/milestone/context state; ObligationDetail includes per-requirement `expected`, `observed`, `decision_id`, `effective`, `chain_status` and blockers. AuthorizationDetail never conflates human approval with confirmed chain authority. Notification includes `id,template_id,summary,resource_route,created_at,read_at`; AuditDetail includes chain/deployment identity and canonicality. Operation includes `state,dependency_operation_ids,attempt_count,next_attempt_at,last_safe_error,result_ref`.

Detail GETs expose role-filtered fields consistently with the screen inventory; A01/A07/A22/A42/A51 are the principal form-bootstrap requests, eliminating unstated frontend lookups. Shared evidence upload/seal uses A29–A34 on all forms.
