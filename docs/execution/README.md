# PB-2 — Master execution index

PB-2.0, 2026-10-30 (Asia/Karachi). **Documentation/planning only. Sprint 0 is NOT STARTED and requires explicit authorization.**

PB-2 refines the existing [PB-1 index](../playbook/README.md), preserving its 28 proposed screen IDs,78 API IDs, detailed screen cards and permission matrix. All new business routes/tables/components/jobs/contracts are **PROPOSED**. Only explicitly labeled EXISTING items describe implemented repository functionality.

| Document | Execution artifact |
| --- | --- |
| [01 — Decisions and consistency](01-decisions-and-consistency.md) | Locked D01/D02, engineering decisions, issue IDs/severity/source/resolution. |
| [02 — Implementation architecture](02-implementation-architecture.md) | Existing/proposed boundaries, code layout, ownership and invariants. |
| [03 — Module build specifications](03-module-build-specifications.md) | M01–M16: services, prerequisites, transitions, recovery, tests and DoD. |
| [04 — Screen/API/event matrix](04-screen-api-event-matrix.md) | Connected screens/actions, API/DTO amendments, domain events and recipients. |
| [05 — Database/migration order](05-database-and-migration-order.md) | ERD refinements, constraints, cyclic FKs, locks and DB00–DB14. |
| [06 — Blockchain plan](06-blockchain-implementation-plan.md) | ABI amendments, K01–K31 guards, typed events/errors, reconciliation/reset. |
| [07 — Integrated journeys](07-integrated-workflow-sequences.md) | Action-to-next-user protocol, negative paths and sequence diagrams. |
| [08 — Sprint backlog](08-sprint-backlog-and-dependencies.md) | WP00–WP17: files, dependencies, checks, outputs and rollback. |
| [09 — Tests and acceptance](09-testing-and-acceptance-gates.md) | PB-1 tests plus P2-01–P2-18, sprint gates and evidence requirements. |
| [10 — Environment/runbook](10-dev-environment-and-runbook.md) | Exact Sprint 0 readiness checklist, future commands, config/secrets/recovery. |
| [11 — Synthetic demo](11-demo-data-and-walkthrough.md) | Locked fixture/formula cases, five task types, presenter checks. |
| [12 — Progress tracker](12-progress-tracker.md) | Distinguishes planning from IMPLEMENTED/TESTED/ACCEPTED code. |
| [AGENTS.md](../../AGENTS.md) | Architecture/coding controls and stop-after-sprint instructions. |

## Authority and preserved sources

Latest user instruction → locked D01/D02 → PB-2 resolutions → unchanged PB-1 detail → earlier proposals. Do not implement conflicting interpretations. The original [audit](../01-repository-audit.md), [architecture](../02-system-architecture.md), [gaps](../03-gap-analysis.md) and [phases](../04-implementation-phases.md) remain historical and unchanged. Audit source revision: `17d75b5d323f71839bab5703c4690d77cdc2e1cb`; clean PB-2 review base: `cc0cd29`.

**EXISTING:** React/Vite/Leaflet, FastAPI/Earth Engine AOI/context/maps/exports; frontend `/` and `/analysis`; no application login, persistent business database, Trust/Steward or Solidity implementation. Historical 139 frontend tests passed; backend environment was unable to run tests. These are prior results, not a PB-2 test run.

## Final implementation order

Sprint 0 baseline → 1 database/identity/shell/outbox → 2 project/site/rules/assignments → 3 evidence/nursery/claims → 4 screening/independent planting review → 5 Solidity/local-chain integration → 6 M3/M6 monitoring → 7 eligibility/authorization/simulation → 8 integrated inbox/audit/reporting/five-type acceptance/demo. Minimal audit/outbox/inbox begins Sprint 1 so each handoff can be tested; Sprint 8 hardens it.

Every sprint needs explicit user authorization, ends with an acceptance report and stops. Passing tests does not authorize the next sprint. Prioritize the complete plantation vertical slice, not all visual screens first.

No outstanding product-policy decision blocks the local plan. Runtime/tool availability and fresh baseline failures are Sprint 0 readiness checks, currently unverified. No installation, migrations, contract compilation/deployment, seeds, feature execution or transactions belong to this documentation task. **Wait for an explicit instruction to start Sprint 0.**

## Archive placement

The user selected an archive because Windows denied direct repository writes. Extract the delivery archive into the repository root so its `docs/execution/` directory and `AGENTS.md` land at the requested paths. The archive contains only those14 documentation files, not application source or replacements for PB-1. This staged review copy includes unchanged reference documents solely so its links are readable before placement; those reference copies are not in the archive.
