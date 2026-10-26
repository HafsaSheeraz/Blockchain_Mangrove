# 03 — Gap analysis and reuse plan

Status: analysis/proposals for approval, 2026-10-25. **Verified** refers to [audited source](01-repository-audit.md); remedies below are **proposed**, not implemented. Priority: P0 = foundation/correctness blocker; P1 = needed for an end-to-end defensible demo; P2 = later hardening or optional capability. Priority does not authorize implementation.

## 1. Reuse without source changes

"Reuse unchanged" means the existing behavior remains usable as-is within its current scope. It does not mean a new module will work without new composition, routes or adapters.

| Existing capability | Unchanged reuse | Boundary |
| --- | --- | --- |
| React/Vite SPA and `/analysis` | Keep environmental analysis available as Mangrove One context. | New navigation/business routes require additive work. |
| `RasterTileLayers`, `LayerControls`, `LayerLegend` | Render existing descriptor shapes in new map views. | Temporary tiles are presentation, not durable evidence. |
| `StudyAreaMap` | Existing one-polygon analysis use with current props/callbacks. | Read-only/project-specific/multiple-polygon behavior is not already supported as a general shared map API. |
| `StudyAreaSetup`, request builder | Existing study/date selection and live analysis request preparation. | Business project IDs must not replace catalog `study_area` keys. |
| `utils/formatters.js`, coordinate conversion | Units/display and `[lon,lat]` ↔ Leaflet conversions. | Money eligibility must use integer/Decimal backend calculations. |
| Existing analysis/metadata/map endpoints | Obtain environmental context and current descriptor contracts. | No approval, persistence or task semantics. |
| EE auth/mask/quality-filter/biomass/stock helpers | Continue existing scientific approximation and no-data behavior. | Live access is unverified; not a planting/survival verifier. |
| `ExportDocument` and JSON/CSV/PDF renderers | Produce readable scientific context attachments. | A wrapper must persist exact versions/bytes before they serve as evidence. |
| Request IDs, CORS configuration, tile URL allowlist, CSV/filename protection | Preserve useful baseline guards. | These do not constitute business authorization, complete upload security or durable auditing. |
| Existing tests | Regression protection for current API/UI behavior. | Do not treat mocked EE results as live scientific validation. |
| Existing design variables/assets | Visual consistency in new screens. | Brand harmonization and fictional-case disclosures require additions. |

## 2. Extensions to existing code after approval

| Area | Verified limitation | Proposed extension |
| --- | --- | --- |
| Frontend routing/layout | Only Home and Analysis; navigation local to Home. | Add module navigation, authenticated session context and scoped Trust/Steward/audit pages while keeping old routes. |
| API client | JSON fetch without identity/CSRF; broad generic errors. | Add a separate business API client with credentials, CSRF, structured conflict/error handling and idempotency. Keep scientific client contracts stable. |
| Geometry handling | Frontend normalization drops holes; backend Polygon-only with incomplete topology checks. | New version-preserving project geometry contract and server topology/area validation. Reject unsupported shapes explicitly; do not silently simplify a submitted boundary. |
| Analysis page assumptions | Known-no-mangrove overlap blocks Run Analysis. | Do not inherit this gate for restoration registration/claims. New parent flow permits degraded sites and records optional GIS no-data context. |
| GIS snapshots | In-memory results and display dataset labels; no persisted analysis identity. | Adapter stores exact response/export, AOI version, source asset IDs, code/method fingerprints, timestamps and warnings. |
| Export semantics | Cache miss recomputes; fresh generated timestamps; PDF map depends on network. | Persist the particular export bytes accepted into an evidence set; retrieve by evidence version later. |
| Timeout/resource control | HTTP 504 stops waiting but not running EE operation. | Bound admission/queues, instrument actual work and move slow tasks to durable jobs if necessary. Apply an overall PDF/network budget. |
| Middleware | Body limit depends on declared Content-Length; readiness returns 200 even when unready. | Cumulative byte/streaming guards for new uploads; separate business readiness check with appropriate status. |
| Auth/CORS | `allow_credentials=False`, no session/CSRF. | Same-origin deployment or explicitly tested credentialed cross-origin cookie configuration. |
| Hosting | SPA rewrites cover only `/` and `/analysis`. | Add rewrites for approved new nested routes and API proxy configuration. |
| Configuration/logging | LOG_LEVEL setting not wired into logging startup; env examples ignored. | Track sanitized examples, document actual startup behavior, configure safe logs and separate future secret domains. |

## 3. Missing domain capabilities

All rows below are **absent** from the audited code, not partly implemented by similarly named GIS models.

| Requirement | Proposed addition | Priority / dependency |
| --- | --- | --- |
| Shared user identity and project roles | Seeded fictional accounts, sessions, scoped membership and conflict checks. | P0 before business writes. |
| Persistent records | PostgreSQL/PostGIS, migrations, transaction/repository layer, fixtures and backup/restore. | P0. |
| Project registration | Project/AOI revisions, synthetic agreement, submission/registration decisions. | P0 domain foundation. |
| Nursery confirmation | Batch observation, independent decision, allocatable quantities and reservation accounting. | P1 after project/evidence/identity. |
| Restoration work claims | Claim revisions, activity/quantity/unit/location/time and shared task-completion linkage. | P1 after project/evidence/nursery for planting. |
| Independent verification | Assigned reviews of exact sealed revisions; rejection, changes requested, conflict of interest and reversal handling. | P0 policy; P1 implementation. |
| Evidence/versioning | Private objects, upload validation, immutable versions/sets, server hashes and scoped download. | P0. |
| Worker tasks | Assignments, worker-owned submission, task status and claim references. | P1. |
| Follow-up milestones | Dated criteria, observations, independent decisions, overdue/no-observation states. | P1. |
| Verified reward eligibility | Immutable fictional policy versions, approved-input calculation, holds and duplicate constraints. | P1 after verification/milestones. |
| Payment authorization/status | Separate authorizer, frozen obligation, idempotent simulated adapter and receipts/failures. | P1 after eligibility. |
| Blockchain audit | Contract/tooling, local chain, RPC/signer, outbox publisher, receipt/finality/reorg reconciliation and timeline. | P0 design; P1 implementation. |
| Operational confidence | Integration tests with real DB/object-store/local-chain boundaries, CI, health checks, seed/reset, runbook. | P1 acceptance. |
| Offline field collection / real payments | Offline synchronization, actual provider integration and operational controls. | P2; excluded from proposed initial demo. |

## 4. Technical risk register

| ID / priority | Verified basis or proposed-system risk | Impact and proposed mitigation |
| --- | --- | --- |
| R01 / P0 | Existing API accepts anonymous requests; no authorization layer. | Any future user-supplied role/project ID could expose or mutate records. Enforce session + project/ownership checks server-side for all business endpoints, including downloads. |
| R02 / P0 | No persistent business storage; caches are per process. | Restart/scale-out loses state and cannot safely account for rewards. Introduce database transactions/migrations before any workflow demo is called persistent. |
| R03 / P0 | Evidence files/versions/sealed submissions do not exist. | Later uploads or AOI edits could invalidate prior approvals. Seal exact immutable versions, append decisions/corrections and retain original bytes. |
| R04 / P0 | Frontend strips polygon holes; server validates bounding dimensions rather than full topology. | Incorrect boundaries/area and changed evidence meaning. Preserve rings, check topology/geographic area, reject unsupported geometry, version accepted geometry. |
| R05 / P0 | Hashes in current code identify cache inputs, not public commitments. | Misrepresenting these hashes as blockchain proof undermines project claims. Add explicit canonicalization protocol, actual local-chain receipts and integrity comparison. |
| R06 / P0 | Proposed async DB/chain/payment integration can fail between systems. | Duplicate payouts or missing anchors after crashes. Transactional outbox, unique obligations/event IDs, worker leases, idempotency and reconciliation. |
| R07 / P1 | EE assets under `mangroves123` require runtime access not established by this audit. | Live demo may fail even if `/ready` says ready. Verify authorization in approved setup; offer clearly labeled saved demo fixtures for business walkthrough, never fake live calculations. |
| R08 / P1 | Global overlay and regional calculations use different GMW sources; 2020 masks and sparse GEDI. | Misleading claims about planting sites/survival/current restoration. Persist source/date and warnings; keep registration independent of mask overlap and verification independent of GIS estimates. |
| R09 / P1 | Height-to-biomass factor is approximate and not locally calibrated. | Carbon estimates could be misused as certified removals or reward basis. Keep context-only; rewards depend on approved fictional work/milestone policy. |
| R10 / P1 | Four-thread timeout executor does not cancel running work; caches have no general size bound. | Repeated timeout requests can occupy threads/quotas and consume memory. Admission limits, worker isolation/job design, bounded caches and load tests. |
| R11 / P1 | PDF generation follows timeout-wrapped analysis, but render/tile fetching is outside that wrapper; PNG temp file used. | Total request may exceed provider deadline despite analysis timeout. Set whole-export budget, tile limits/fallback and temporary-file cleanup checks. |
| R12 / P1 | Content-Length guard can be absent/spoofed; overlap endpoint has weaker limits. | Oversized or complex public requests can consume memory/EE quotas. Streaming request limits, consistent geometry validation and rate limiting. |
| R13 / P1 | Cache keys use exact JSON representation; success results lack normal refresh; fingerprints do not identify complete immutable datasets. | Equivalent AOIs create separate caches; stored assets may change; reanalysis differs. Distinguish cache hash from canonical evidence hash, save exact snapshots and source/code provenance. |
| R14 / P1 | `GmwCoverageCheckRequest` checks exterior ring only; AnalyzeRequest forms distinct-point tuples before fully validating nested point structures. | Malformed nested geometry may not produce a clean validation response. Adversarial payload tests and shared robust server validation; this is a source-level concern, not a reproduced exploit. |
| R15 / P1 | CORS/security headers are present, but no rate limits or durable audit; logs include geometry hashes and service exceptions. | Operational abuse or sensitive metadata leakage in future workflows. Scoped logs/redaction, rotation, role audit, rate limits; avoid evidence/private URLs in logs. |
| R16 / P1 | Proposed relayer holds a publisher key and app enforces reviewer roles. | Chain authenticates publisher, not independently the human verifier; key compromise can anchor false data. Disclose trust boundary, isolate signer, restrict contract role, record role changes and decide whether actor signatures are required. |
| R17 / P1 | Public blockchain commitments are persistent; photos may contain identifying location/EXIF. | Privacy exposure cannot be fixed by deleting a DB row. Use fictional identities, private originals, redacted views, opaque references and privacy-reviewed commitments. |
| R18 / P1 | Real-world case inspiration with no partnership/private data. | Demo could imply endorsement or authentic operational/payroll data. Persistent fictional-case disclosure and cited public context; no copied private workflow/contract claims. |
| R19 / P1 | No duplicate/overlap business checking exists. | Same work/evidence may support multiple rewards; nursery inventory can be overused. Unique reward keys and allocation locks; flag overlapping claims/reused photo hashes for review. Shared photos/overlapping AOIs are signals, not automatic proof of fraud. |
| R20 / P1 | Proposed approvals can later be disputed/reversed. | Old eligibility may be paid after source approval changes. Recheck dependencies at authorization and execution, hold unpaid obligations, append corrections for already simulated-paid entries. |
| R21 / P1 | Existing backend venv is broken, system Python lacks pytest; no CI config. | No backend passing baseline can currently be claimed. Repair approved development environment, execute tests and establish CI before implementation acceptance. |
| R22 / P1 | README Node 18 minimum conflicts with locked Vite 8.1.5 engine; env examples ignored; Python transitive dependencies unlocked. | Fresh clone/deployment may fail or drift. Document/pin supported runtimes, track sanitized examples, lock dependencies and test clean setup. |
| R23 / P1 | Deployment guide disagrees with timeout/temp-file source; readiness is configuration-only HTTP 200. | False readiness/availability assumptions. Correct docs in approved maintenance phase and verify deployment probes, EE diagnostics and business DB/object-store/chain health separately. |
| R24 / P2 | OSM and EE tiles are external dependencies; source/attribution duties and limits apply. | Blank maps/slow PDFs or inappropriate repeated tile access. Preserve attribution, bound/cache permitted fetching, verify terms at deployment and permit map-unavailable exports. |

## 5. Testing gaps and acceptance focus

The 139 passing frontend tests support the existing UI only. Backend suites are available but were not runnable in the current environment. Neither result establishes Trust/Steward correctness because those modules do not exist.

After approval, prioritize tests of observable failure-prone behavior:

- Unauthorized project access/download, forged role or worker ID, submitter-as-verifier, payee-as-authorizer, session expiry/CSRF.
- Polygon holes preserved end-to-end, malformed/self-intersecting/oversized geometry rejected, degraded/no-mangrove site registration allowed.
- Exact evidence bytes/manifests hashed on server; modified file fails integrity; a new version cannot inherit an old approval.
- Nursery over-allocation prevented under concurrent claims; cancellation/rejection releases reservations correctly.
- Verification changes-requested/rejection/reversal, missing/overdue/rejected milestone and incomplete evidence all prevent eligibility.
- Concurrent eligibility/authorization requests yield one obligation; retry/unknown payment outcomes cannot produce duplicate simulated payments.
- Worker crash after DB commit, after chain submission and before receipt persistence; duplicate/reordered events, wrong chain/registry, dropped/reorged receipt and recovery.
- Snapshot/export served from exact accepted version after application restart and source/cache changes.
- Full seeded flow with real PostgreSQL transactions, local object store and local EVM; existing scientific API/UI regression tests remain intact.

## 6. Scope choices that reduce implementation risk

Proposed first delivery: one codebase, one project-scoped identity model, one persistent database, one evidence store, one minimal registry contract, local EVM and simulated payments. Worker field UX starts online and responsive. Persisted snapshots make the business demo resilient to EE unavailability, with explicit source-mode labels.

Defer microservices, token issuance, carbon-credit issuance/trading, production financial transfers, offline synchronization, DAO voting, public evidence publication and real-person data ingestion. Defer GIS algorithm changes unless specifically approved; scientific correctness claims should remain within the existing approximation and audit limitations.

Approval decisions and ordered implementation gates: [04 — Implementation phases](04-implementation-phases.md).
