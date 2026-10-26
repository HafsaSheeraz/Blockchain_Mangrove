# Mangrove application — engineering execution playbook

Version: **PB-1**, 2026-10-25 (Asia/Karachi). Status: **documentation specification; implementation not started**.

This is the master index for one connected application containing MangroveTrust, MangroveSteward and Mangrove One. The user's latest product decisions are authoritative. Every new route, table, job, notification and Solidity function in this directory is **PROPOSED**. Only items explicitly labeled **EXISTING** describe repository functionality.

## Reading and execution order

| Document | Engineering deliverable |
| --- | --- |
| [01 — Baseline and connected architecture](01-baseline-and-architecture.md) | Preserved repository findings, approved direction, ownership and runtime boundaries. |
| [02 — Workflows, task types and state machines](02-workflows-and-states.md) | Primary plantation path, five configurable task types, exact-version approvals, reward components and corrections. |
| [03 — Roles and permissions](03-permissions.md) | Project/organization scope, field-level access, conflicts of interest and signer mapping. |
| [04 — Database model and ERD](04-database-model.md) | Tables, keys, constraints, transaction/locking rules, migrations and indexes. |
| [05 — API contracts](05-api-contracts.md) | Endpoint catalog, request/response DTOs, errors, optimistic concurrency and asynchronous operations. |
| [06 — Solidity contract specification](06-solidity-contract.md) | Concrete local-EVM interface, storage, role/transition guards, milestone authorization, replay rules, events and trust limits. |
| [07 — Evidence, checks and environmental monitoring](07-evidence-checks-and-monitoring.md) | Upload/sealing protocol, checks, 3/6-month inspections, GIS reuse and integrity. |
| [08 — Notifications and background processing](08-notifications-and-jobs.md) | Shared inbox, event/recipient matrix, scheduler, outbox, retry and reconciliation. |
| [09 — Cross-module sequences](09-sequence-diagrams.md) | Frontend → API → database → workers → chain/inbox → next user, including failure paths. |
| [10 — Shared application screens](10-screens-shared.md) | Login, dashboard, projects, project workspace, evidence, monitoring, notifications, audit and administration. |
| [11 — Trust and configuration screens](11-screens-trust.md) | Project creation/site, fictional contract rules, task configuration, nursery, claim versions and field-review screens. |
| [12 — Steward and payment screens](12-screens-steward.md) | Worker tasks/submission, inspections, eligibility, authorization and simulated settlement. |
| [13 — Delivery plan and sprint backlog](13-delivery-backlog.md) | Dependency graph, executable work packages, completion evidence and implementation order. |
| [14 — Testing and operational acceptance](14-testing-and-operations.md) | Test IDs, unit/integration/E2E/contract/recovery tests, deployment and restore plan. |
| [15 — Synthetic data and demo walkthrough](15-synthetic-data-and-demo.md) | Fictional actors, project/AOI, dated inspections, exact amounts, fixtures and presenter script. |
| [16 — Decisions and traceability](16-decisions-and-traceability.md) | Resolved decisions, remaining approval choices, requirement/screen/API/test coverage. |

The screen documents are the complete proposed route inventory. A screen card names its API operation IDs, database writes, chain action, notification IDs, status/error/correction paths and acceptance tests. Shared screen/API rules apply to every card; an explicit **none** means no side effect, not an unspecified requirement. Drawers and tabs are documented with their owning screen rather than introduced as hidden pages.

## Precedence and historical documents

The original [repository audit](../01-repository-audit.md), [system architecture](../02-system-architecture.md), [gap analysis](../03-gap-analysis.md), and [implementation phases](../04-implementation-phases.md) remain unchanged as historical analysis. PB-1 supersedes their proposed **30/90-day** follow-ups with **3/6 calendar months**, and their minimal publisher-only registry with the explicit **role-restricted milestone/authorization contract** in document 06. It also makes shared notifications and monitoring first-class modules.

The earlier architecture was approved **in principle**, not already implemented. Existing source remains React/Vite + Leaflet, FastAPI + Earth Engine, two frontend routes and no persistent business database/authentication/contracts. Previous frontend test result: 139 passed; backend test environment blocked. Those are historical audit results, not a new test run for nonexistent functionality.

## Locked product baseline

- One authentication/session system and shared organizations, projects, tasks, claims, evidence, monitoring, notifications and audit records.
- One fictional plantation project is the primary end-to-end slice. Five task types use common assignment, submission, evidence, review and reward components.
- Nursery confirmation proves supply only. Accepted planting requires independent field review of an exact claim revision and sealed evidence set.
- Both the 3-month and 6-month inspections are recorded. Recommended primary policy requires verified planting **and both** follow-ups for the single final reward; that exact fictional policy is called out for approval.
- Eligibility, human authorization, blockchain confirmation and simulated settlement are independent statuses.
- PostgreSQL/PostGIS + private evidence + Solidity/local EVM; no real payments, cryptocurrency tokens, NFTs or carbon-credit issuance.
- Mangrove One remains environmental context. Field inspections may decide survival when satellite evidence is insufficient.
- Fictional actors/agreements/rates/activity/settlements; public Delta Blue Carbon inspiration without partnership or private operational data.

## Definition of playbook completion

All named screens and state-changing actions have permission checks, explicit API/schema linkage, transaction effects, audit/notification behavior, chain involvement and tests. The remaining decision list is short and concrete; engineering defaults do not reopen approved architecture. No migrations, application source, Solidity source, infrastructure or seed execution is part of this documentation delivery.
