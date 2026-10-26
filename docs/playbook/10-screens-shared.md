# 10 — Shared application screens

**PROPOSED** except the explicitly existing Home/Analysis routes below. This and documents 11–12 constitute the complete PB-1 screen inventory. Modals, forms and drawer variants live in the named page; they are not undocumented extra routes.

## Shared layout and interaction contract (G)

Authenticated shell: top app name + fictional-demo badge + project selector + unread inbox + signed-in actor/role + logout; left navigation Overview, Projects, My Tasks (Steward), Reviews (Trust), Monitoring, Rewards, Evidence, Audit, Mangrove One, and authorized Administration. Project tabs cross-link the same project IDs. Breadcrumbs persist context; responsive mobile uses a drawer, no mandatory map manipulation for task completion.

Every page: semantic title, loading skeleton, empty state with authorized next action, safe error/retry, accessible inline field errors and focus movement; pending buttons disabled to prevent duplicates; no optimistic approval/payment success. Scope comes from session/server, not URL alone. Forms show exact version/ETag, warn on unsaved navigation, preserve drafts after recoverable errors and show 409 comparison/reload instead of overwriting. Required fields labeled; ISO dates, integer counts, decimal-string quantities, finite geographic inputs; no raw actor, status, hash or payable-amount editing.

All authenticated writes use CSRF/idempotency/ETag rules, all reads have scope checks, all exact evidence selection/download uses A29–A34/A31–A32 from the shared evidence drawer. Each card's API arrow means the request and response DTOs in document 05, not an unspecified future backend. Business changes generate audit/outbox in the same transaction. None on the chain row means no transaction from that page. Notifications are template IDs in document 08. Test IDs are defined in document 14.

## S01 — Login/session

- **Role/route/layout:** anonymous `/login`; logged-in users redirect to `/app`; centered login with fictional account hints, no public signup. G session status in header after success.
- **Fields/validation:** login, password, optional safe internal return path. Both required; trim login only, cap lengths, no password logging; block open redirects/external next URLs.
- **Actions/API:** bootstrap A01 → anonymous CSRF; Sign in A02 `{login,password}` → rotated session/user/projects/roles; Logout A03 →204. Return to safe authorized route or dashboard.
- **Database/chain:** session digest/expiry, login security audit only; **no chain**.
- **Notifications/status:** none; anonymous→authenticated→expired/revoked. Generic failed credentials; 429 retry delay; expired session returns here with safe return path and unsaved-draft guidance.
- **Acceptance:** UI-01, SEC-01/02: login/logout, role switch requires real session, CSRF/login rate limit, safe redirect, no secrets in browser state/logs.

## S02 — Connected dashboard

- **Role/route/layout:** all signed-in roles `/app`; G + role-specific workload cards and shared activity list, no duplicate module dashboards.
- **Fields/actions:** project/date filters; Open assigned task/review/milestone/reward/inbox, Refresh. Filters allowlisted and cannot widen scope.
- **API:** A04 filters → authorized workload counts/cards; A57 unread summary; action navigates to resource page rather than mutating state.
- **Database/chain:** read projections only; **no chain**. Notifications shown, none generated.
- **States/flows:** zero work shows next permitted action; dependency outage shows unavailable card rather than zero; stale counters refresh. No badge implies approved/paid from a total alone.
- **Acceptance:** UI-02, SEC-03: worker sees own tasks/rewards, verifier sees assigned queue, cross-role project totals redacted correctly.

## S03 — Projects catalog

- **Role/route/layout:** authorized members `/projects`; G + project search/status list, fictional label, Create button only O.
- **Fields/actions:** search/code, state/cursor; Open project; Create →T01. Bounded search/no unscoped user filter.
- **API:** A05 query → ProjectSummary[]/cursor, A01 role context.
- **Database/chain:** reads only; **no chain**, no notifications.
- **States/flows:** empty organization vs no membership are distinguished; API invisible-resource rules enforced; query error preserves filters; project published/paused labels include independent chain badge.
- **Acceptance:** UI-03, SEC-03: paging/filtering and cross-organization isolation.

## S04 — Shared project workspace

- **Role/route/layout:** scoped members `/projects/:projectId`; G + overview, immutable version badges, progress across supply/planting/M3/M6/reward, project navigation to T02/T03/T04/T05/T07/S06/W05/S08. Worker sees assigned subset.
- **Fields/actions:** read name/code/site/policy, lifecycle/chain statuses. O Edit draft/new revision →T01; Activate project after checklist; Open failed operation; Dispute drawer with reason.
- **API:** A07 → ProjectWorkspace; A12 `{expected_site_version_id,expected_policy_version_id}` →202 operation; A68 reason/target →dispute and holds; A69/A61 status.
- **Database/chain:** publication locks project and seals version; audit/outbox; dispute appends/holds. Chain registerProject and dependent roles/policy publication; dispute revocations as applicable, never delete old events.
- **Notifications/status:** N01 publication, N19 dispute; draft/configured/active/suspended/closed independent from chain queued/confirmed. Incomplete configuration blocks Activate with specific checklist. Chain failure leaves configured business record visible; retry via operations policy, not duplicate creation.
- **Acceptance:** UI-04, FLOW-01, REC-01: one project across modules; required site/policy/roles, idempotent publish, no science-based activation requirement.

## S05 — Evidence library and integrity viewer

- **Role/route/layout:** scoped users `/projects/:projectId/evidence`; G + category/version list, authorized preview, usage timeline and upload/replace/seal drawers. W only own/assigned evidence; A redacted view.
- **Fields/validation:** filename, caption, category, declared capture time/location/accuracy, bytes; required checklist and MIME/size caps; immutable version ID and server hash read-only.
- **Actions/API:** Upload A29→signed slot, object PUT→A30 validation operation; A31 detail; A32 download; A33/A34 set/seal; A63 integrity recheck→operation; poll A61. Replace creates new version, not overwrite.
- **Database/chain:** upload/quarantine/evidence/version/set rows; integrity audit; no standalone chain proof on upload. Commitments reach chain only through subject/decision sealing/submission. Integrity mismatch triggers affected holds/revocation work, not an automatic false chain match.
- **Notifications/status:** none for routine upload/read; N19 mismatch, N07 input rejection when submitted checks affected. Pending validation prevents seal; safe preview failure allows download if valid; invalid object cannot enter a submission.
- **Acceptance:** UI-05, EVID-01–08, SEC-05: exact bytes/version/digest, private scope, mismatched MIME, expired slot, failed upload retry, old decision cannot point to new bytes.

## S06 — Shared monitoring board

- **Role/route/layout:** scoped `/projects/:projectId/monitoring`; G + PLANTING/M3/M6 rows, calendar/list toggle, site/context panel and milestone detail drawer. W own, V assigned, O/A project scope, P requirement summary.
- **Fields/actions:** filter stage/due/status/assignee; Open milestone; Record inspection→W04; View review→T10; optional Capture environmental context with region/dates/source mode. No “auto verify survival” action.
- **API:** A44 query →milestone rows, A45 detail; A64 `{region_key,start_date,end_date,milestone_id,mode}`→snapshot operation, A65 stored context; A61 poll.
- **Database/chain:** reads and optional AnalysisSnapshot/job only; **no milestone approval chain write** from context capture. Due scheduler owns reminders; A64 records context audit only.
- **Notifications/status:** N10/N11 supplied by scheduler, N12/N13 after inspection/review elsewhere; context unavailable/insufficient alongside independent milestone due/passed/failed. No-data permits field inspection; wrong context dates corrected by a new snapshot, not altered old provenance.
- **Acceptance:** UI-06, MON-01–06: correct calendar months, missing inspections stay pending/overdue, field route available when satellite insufficient.

## S07 — Shared notifications inbox

- **Role/route/layout:** own inbox `/notifications`; G + unread/all filters, timestamped summaries, owning-resource links.
- **Fields/actions/API:** filter/cursor, Open item, Mark read A58 `{read:true}`; A57 →Notification[] with count; no mark-another-user-read control.
- **Database/chain:** own read_at only; **no chain**, no notification fanout. Resource permissions rechecked when opening.
- **States/flows:** empty/unread/read/delivery delayed; inaccessible former membership shows unavailable target without sensitive retained content; mark-read failure preserves unread badge and can retry idempotently.
- **Acceptance:** UI-07, NOTIF-01–04, SEC-06: one inbox from every module, dedupe, correct recipient, no data leakage after revocation.

## S08 — Project audit timeline / commitment detail

- **Role/route/layout:** scoped `/projects/:projectId/audit`; G + filters, event timeline and expandable event detail/digest/receipt/subject-version panel. A redacted by default, worker own subset.
- **Fields/actions/API:** filter event/resource/chain state; A59 list →audit rows; A60 detail; A61 operation; Copy digest, Open exact revision, Recheck private evidence A63 if permitted. Local tx viewer panel, no fake public explorer URL.
- **Database/chain:** reads plus integrity-operation audit; no chain mutation merely to view or compare. Display actual deployment, canonical block/hash, local confirmation depth and signature actor.
- **Notifications/status:** none from read; mismatch N19, blocking chain issues N17. Pending/submitted/mined/confirmed/reverted/orphaned distinct; corrected/revoked events retained. Missing chain service shows unavailable, not confirmed.
- **Acceptance:** UI-08, CHAIN-09/10, EVID-08: exact hash comparisons, old/new version history, no authorizer/settlement conflation.

## S09 — Access administration

- **Role/route/layout:** S only `/admin/access`; G + project selector, role roster, fictional actor/signer binding metadata, membership-change drawer. O may see roster read-only through S04, not admin action.
- **Fields/actions/API:** select existing seeded user/project/allowlisted role, grant/revoke, mandatory reason; A66 roster→members; A67 →membership/role-chain operation; A61 poll. No plaintext keys/passwords or person rebinding UI.
- **Database/chain:** membership change/audit/outbox; setProjectRole; initial signer binding is controlled setup, not user editable. Revocation holds queued affected commands and may hold unexecuted authority.
- **Notifications/status:** N20; DB membership changes immediate, chain propagation pending visible. Failed role tx blocks dependent commands. Wrong or self-conflicting role grant does not permit business self-approval.
- **Acceptance:** UI-09, SEC-04/07, CHAIN-01/08: admin has no implicit approve/payment action; role revocation effective despite queued work.

## S10 — Operations / reconciliation

- **Role/route/layout:** S operational metadata `/admin/operations`; G + dependency/queue/lease/error/chain deployment panels; no unscoped original evidence content.
- **Fields/actions/API:** project/type/state filter A77 list, A61 detail; Retry reconciled operation A73 `{reason}`. Commands marked unknown require receipt/event/nonce reconciliation before Retry becomes allowed; no “force success”.
- **Database/chain:** lease/retry audit/operation updates; workers may resubmit same reconciled chain command; no independent signing from browser. Deployment reset is a future local runbook action, not a production browser button.
- **Notifications/status:** N17 and failure recovery, no repeated unchanged reminders. Error vs unknown vs orphaned vs held shown separately; unrecoverable business prerequisites route to owner correction/review, not admin override.
- **Acceptance:** UI-10, REC-01–06: crash/restart, nonce/event lookup, no duplicate side effects, safe errors/redacted logs.

## E01/E02 — Existing Mangrove One pages

**EXISTING:** `/` Home and `/analysis` Analysis with their audited fields/actions/API calls and scientific behavior. PB-1 preserves them. Home remains public; scientific analysis remains the current public endpoint surface until a separately approved access change. Authenticated shell links “Mangrove One” to `/analysis` and context snapshots to S06; adding navigation must not replace or rewrite calculations.

Home renders static/reference content; no DB/chain/notifications. Analysis selects region/custom polygon/date, draws/edits geometry, runs existing analysis, toggles raster layers and downloads JSON/CSV/PDF. Existing requests are `/api/analyze`, `/api/analyze/map-layers`, `/api/map/gmw-layer`, `/api/map/gmw-coverage-check`, `/api/gee/carbon/stock-summary` and exports, with current validation/error/no-data/stale-input handling. They remain environmental context and do not change claim/milestone/reward states. Tests: legacy suite plus LEGACY-01–04. Any hole-preserving project editor is new T02, not a claim that existing Analysis already preserves holes.
