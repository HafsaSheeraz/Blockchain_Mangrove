# 02 — Implementation architecture

All new paths here are **PROPOSED**. Preserve the [existing audit](../01-repository-audit.md) and [PB-1 boundaries](../playbook/01-baseline-and-architecture.md): one React/FastAPI modular monolith, shared PostgreSQL/PostGIS, private objects, DB-backed worker/scheduler and local EVM. Trust and Steward view the same records; One supplies context.

## Data owners

| Owner | Canonical responsibility / cross-module use |
| --- | --- |
| identity | user/org/project membership/session; all APIs reuse authorization dependencies. |
| projects/sites | project/site versions and roster; GIS adapter snapshots reference same site version. |
| policies/tasks | published type/policy/task versions, assignments/collector/stage roster and obligation templates. |
| nursery | declarations/confirmation/inventory; claims reserve through shared transaction service. |
| evidence/screening | exact bytes/sealed manifests/check inputs; no copied mutable attachments. |
| trust/monitoring | claims/reviews/decisions; monitoring owns milestones/observations and uses same decision service. |
| rewards/settlement | exact evaluations, human authority, simulated receipt; no token/worker balance. |
| audit/notifications | shared immutable events/outbox/operations, receipt projections and own inbox. |

## Proposed file conventions

`backend/app/modules/<name>/` contains `router.py,schemas.py,models.py,repository.py,service.py,permissions.py,__init__.py` as needed. Names: identity, projects, sites, policies, tasks, nursery, evidence, screening, trust, monitoring, chain, rewards, settlement, notifications, audit, administration. Avoid empty layers with no purpose.

Shared: `backend/app/business/{database,unit_of_work,errors,authorization,idempotency,events,canonicalization}.py`; `backend/app/workers/{main,outbox,scheduler,chain_reconciler}.py`; `backend/app/integrations/{gis_adapter,object_store,local_signers,payment_simulator}.py`; `backend/migrations/versions/`; `backend/scripts/{seed_demo,reset_demo}.py`. Do not replace existing scientific Pydantic models with business ORM records.

Frontend: `src/app/{ApplicationShell,SessionProvider,ProtectedRoute}.jsx`, pages under `src/pages/{platform,trust,steward}/`, shared business components under `src/components/business/`, `src/services/{businessApi,sessionApi}.js`, hole-preserving `src/utils/businessGeometry.js`. Page filenames follow 04. Existing raster/legend/formatting code can be composed unchanged.

Contract: `contracts/contracts/{IMangroveWorkflowRegistry,MangroveWorkflowRegistry}.sol`, `contracts/test/`, `contracts/scripts/deploy.ts`, `contracts/hardhat.config.ts`, locked package manifest. No proxy/token/browser-wallet packages.

Only approved sprint integration edits existing `backend/app/main.py`, `frontend/src/App.jsx`, manifests and hosting/proxy configuration to register new behavior. Preserve `/`, `/analysis`, scientific API/DTOs, coefficients, masks, scientific warnings and exports. A scientific change needs separate explicit scope and validation.

## Request/effect invariant

Authenticate+CSRF → scope/conflict check → expected-version/idempotency → deterministic locks → domain+AuditEvent+outbox/inbox intent transaction → commit → response. External objects/EE/RPC work runs after commit. No DB lock held waiting on those services. Local simulator RPC preflight occurs outside transaction; receipt insertion re-locks obligation and compares captured dependency digest before committing.

Durable command captures actor/person/signer binding. Logout/session expiry does not erase valid consent. Signing rechecks active account/role/scope/current subject/holds/canonical dependencies. Revocation immediately holds affected commands. Chain-critical permissions granted only when on-chain grant is confirmed, even if app membership row already exists.

Org signs project/policy/assignment; N supply declaration; C confirmation; W submitted subject; V exact field decision; P authority; restricted simulator service settlement assertion. System checks/evaluations/inbox jobs never impersonate human approvals. Admin may pause, never bypass milestone guards.

## Status/science boundary

Keep [PB-1 states](../playbook/02-workflows-and-states.md) with IC-19: accepted work is not final-reward-ready. Accurate accepted survey below threshold gives approved review + failed milestone + ineligible reward. Missing survey stays pending; disputed/revoked dependencies hold. No manual eligible toggle or science-generated survival pass.

Store exact context/provenance/warnings/export bytes; EE unavailable does not block field records. Existing public science endpoints keep current semantics. New business endpoints authenticated; readiness distinguishes DB/objects/worker/chain/EE capability and does not rename existing `/ready`.

Local course scope: one seeded organization/project, online responsive UX, full plantation plus four small typed workflows. No real payroll/identity, public hosting, offline sync, external messaging, DAO or ML survival proof.
