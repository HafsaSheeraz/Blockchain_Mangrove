# Mangrove application — agent instructions

## Authorization and document authority

The current request authorizes PB-2 documentation/planning and this AGENTS.md only. Do not start Sprint 0, modify application source, install packages, migrate databases, compile/deploy contracts, run seeds or create transactions until the user explicitly authorizes a named sprint. A later explicit user instruction controls the active scope.

Read [PB-2 index](docs/execution/README.md), [decisions](docs/execution/01-decisions-and-consistency.md), [backlog](docs/execution/08-sprint-backlog-and-dependencies.md) and [tracker](docs/execution/12-progress-tracker.md). Preserve PB-1 as historical detail; PB-2 named resolutions govern conflicts. Proposed designs are not implemented features.

## Approved architecture and invariants

- Extend React/Vite/Leaflet and FastAPI/Google Earth Engine as one modular monolith. Share identity, organizations, projects, tasks, claims, evidence, monitoring, notifications and audit. Use PostgreSQL/PostGIS, private versioned objects, a DB outbox/job queue and local Solidity EVM.
- Preserve scientific algorithms, coefficients, masks, warnings, routes and APIs. Mangrove One supplies environmental context, never proof of planting or seedling survival. New business geometry preserves polygon holes and allows degraded/no-GMW sites.
- Locked D01: assign 1,000 seedlings; independently accepted planting Q × PKR 10, capped at PKR 10,000. Independent M3 >=80% and M6 >=75% field results are both mandatory. Missing, failed, disputed, unapproved, revoked or stale dependencies block the final reward. Use accepted Q, not live count. Other policies support separate completion and survival components; do not describe this as a universal wage-delay policy.
- Locked D02: distinct role-bound fictional local signers held by backend runner; no browser wallets. Backend and Solidity enforce critical role, exact-version, parent-milestone, threshold, authorization and replay rules. No unrestricted publisher bypass. Disclose custodial and field-truth limits.
- No real financial transfers, cryptocurrency tokens, NFTs, carbon credits, real-person operational data or partnership claims. All operational fixtures, agreements and rates are fictional; receipts say SIMULATED.
- Block self-approval by person identity in the backend and address in the contract. Submitted evidence and accepted revisions are immutable. Corrections append versions and require re-review. Economic obligation identity survives revisions, retries and chain reset.
- Commit domain state, audit and outbox/intents atomically. Run external EE/object/RPC work after commit. Do not substitute process memory for durable jobs. Keep eligibility, human approval, chain confirmation and simulation separate.

## Sprint control and reporting

Work only the expressly authorized sprint and work packages. Use codex/sprint-N-short-description branches by default after authorization. Preserve user changes; no destructive resets, force pushes, auto-merges or unrequested publishing. Keep commits small and coherent, with WP IDs and meaningful behavior/test descriptions. Do not commit secrets or private generated evidence.

Each sprint ends with: (1) implemented behavior, (2) exact files modified, (3) test commands, counts and exit codes, (4) incomplete items, (5) manual verification steps/results, (6) known risks and recovery, (7) recommended next sprint. Update tracker honestly. STOP after the report and await explicit next-sprint instruction. Only user acceptance marks ACCEPTED. Documentation never counts as implemented code.

## Tests, quality and migrations

Existing baseline commands: selected backend interpreter runs python -m pytest tests -q with GEE_ENABLED=false; frontend runs npm.cmd test, npm.cmd run lint and npm.cmd run build. Future contract/E2E scripts require their owning sprint; exact workdirs/commands are in [runbook](docs/execution/10-dev-environment-and-runbook.md).

Run meaningful authorization, invariant, concurrency and regression checks. Distinguish failed-to-start, passed, failed, skipped and not run. Historical 139 frontend passes are not a fresh baseline. Use disposable real PostgreSQL/PostGIS, objects and local EVM for integration; direct-RPC negative tests establish contract guards independently of FastAPI. Do not write tests that merely mirror setters.

Follow DB00–DB14 migration order, typed scoped FKs and transaction locks. Prefer additive changes and forward repair. Back up before destructive repair; no automatic downgrade or deletion of accepted history.

## Secrets, fixtures and changes

Sanitized example files contain placeholders only and have precise ignore exceptions. Never print populated environments, credential JSON, session tokens, signer keys or signed evidence URLs. Backend secrets do not belong in VITE_* variables. Keys stay outside DB/browser/logs.

Use isolated, watermarked fictional fixtures and service-level seed guards; never create completed demo state with SQL approved/paid flags. API/ABI changes update schemas, matrix, vectors, versions, migration/recovery notes and tests in the same reviewable change.

Explicit permission is required for the next sprint, locked-policy/scientific changes, ACL/ownership changes, remote/paid/public provisioning, real-data ingestion, destructive bulk resets and unrequested publishing/merging. Routine necessary reversible work/tests inside an approved sprint do not require repeated confirmation; obey tool sandbox escalation. No messaging other people or spawning subagents without direct authorization.

Report concise findings and remaining work at least every minute when tools permit. Do not circumvent OS or sandbox permissions.
