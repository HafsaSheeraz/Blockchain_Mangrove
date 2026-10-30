# 10 — Development environment, controls and Sprint 0 readiness

**PROPOSED future procedures; no commands here were executed by authoring PB-2.** Baseline app scripts are existing; new service/test/deploy commands become available only in their approved sprint. Repository [AGENTS.md](../../AGENTS.md) governs implementation.

## Exact Sprint 0 readiness checklist

Before starting: user explicitly says “Start Sprint 0” or equivalent; documentation approval alone does not authorize execution.

- [ ] Read PB-2/AGENTS and record scope as WP00 only; mark Sprint 0 IN PROGRESS, othersNOT STARTED.
- [ ] Record Git revision/branch/status; preserve unrelated user changes; create `codex/sprint-0-baseline` only once Sprint 0 authorized.
- [ ] Verify repo write permissions and user-controlled paths; do not change ACL/ownership without explicit permission. PB-2 authoring encountered repository write denial; confirm resolution rather than assuming future access.
- [ ] Inventory actual Node/npm/Python/pip/venv and platform; inspect frontend lock engine constraints and backendDockerPython 3.12 target; never claim README Node 18 is sufficient.
- [ ] Select compatible stable runtime versions (proposed Python 3.12 and Node 24 target subject to lock/tool compatibility), document exact patches. Avoid unrequested package upgrades.
- [ ] Create isolated ignored `backend/.venv-pb2` with selected Python if needed; preserve broken previous venv and existing secret files. Confirm interpreter path before install.
- [ ] Install only baseline manifest/lock dependencies in the approved local environment; network/sandbox escalation uses normal approval process when necessary. No business feature dependencies yet.
- [ ] Create/track sanitized backend/frontend .env.example and precise ignore exceptions; never copy populated .env/credential material into documentation or commits.
- [ ] Set backend GEE_ENABLED=false for deterministic baseline; frontend VITE_API_BASE_URL localport 8001. Do not read/expose live GEE key material or call externalEE as hidden prerequisite.
- [ ] Run existing backend pytest and frontend test/lint/build; record exact commands/workdirs/counts/exit codes/start failures. Investigate within baseline scope; new scientific feature fixes require separate scope.
- [ ] Manually confirm root/analysis navigation, clear API configuration error and liveness/readiness semantics; distinguish config ready from live EE access.
- [ ] Inventory availability of Docker/PostgreSQL/PostGIS/private object store/local EVM tooling read-only for later planning; no database creation/migration/chain compile/deploy/seeds in Sprint 0.
- [ ] Record selected later SQLAlchemy/Alembic/driver/auth/object/chain/E2E package compatibility plan; exact business versions locked in approved owning sprint, not speculative “latest”.
- [ ] Update tracker and Sprint 0 report with all 7 required sections; recommend acceptance only if G0 criteria met; STOP and wait fornext authorization.

## Test/build commands (future execution)

PowerShell from repository root unless workdir shown. Proposed envpath command must be replaced by **actual verified** selected interpreter in report if different.

```powershell
# backend workdir D:\MangroveCarbonApp\backend
$env:GEE_ENABLED='false'
.\.venv-pb2\Scripts\python.exe -m pytest tests -q
# frontend workdir D:\MangroveCarbonApp\frontend
npm.cmd ci
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

`npm.cmd` avoids PowerShell script-policy wrapper issues; it does not bypass filesystem/network sandbox approval. Sprint 0 report must capture actual backend environment behavior; historical missing Python/pytest is a known prior limitation, not asserted current test result.

New test scripts **PROPOSED**: frontend `test:e2e` runs Playwright (Sprint 1 harness); contracts `compile,test,node,deploy:local` map to pinned Hardhat CLI(Sprint 5). Backend new tests use same pytest runner. `npm.cmd run test:e2e` and `npm.cmd test` in contracts workdir must not be advertised existing before their package scripts land.

## Local service runbook after owning sprints are authorized

Planned `compose.demo.yml` services: postgres(with PostGIS), private S3-compatible objects, backend, worker, scheduler, SPA proxy, optional persistent local chain. Pin compatible stable image digests/tool versions at implementation; credentials supplied through local secrets. One backend code base, DB queue; no Redis/Celery requirement. Choose one maintained local object-store image in owning sprint and record exact version/license before using it.

After corresponding files exist, planned commands: `docker compose -f compose.demo.yml up -d postgres objects`; backend `python -m alembic upgrade head`; `uvicorn app.main:app --host 127.0.0.1 --port 8001`; worker `python -m app.workers.main`; scheduler `python -m app.workers.scheduler`. Sprint 5 local chain `npm.cmd run node`, then `npm.cmd run deploy:local`; frontend `npm.cmd run dev`. These are proposed command interfaces, not already available executables or actions performed now.

Order: version check → DB/objects → migrations → local EVM deployment generation/contract → actor binding/roles → backend/workers/scheduler/proxy → seed through services → manual checks. UntilSprint 5 display chain awaiting_dependency, not fake confirmed. Dedicated local runner mines 2 observation blocks after receipt when needed for local depth policy.

## Environment inventory (new variables proposed)

| Scope | Variables / requirement |
| --- | --- |
| Existing science | Keep audited GEE_*, CORS_ORIGINS, REQUEST_TIMEOUT_SECONDS, AOI limits, tile hosts and VITE_API_BASE_URL. Secrets backend only. |
| Business DB | BUSINESS_DATABASE_URL, TEST_DATABASE_URL, demo_namespace; restricted app/test DB roles, isolated schema. |
| Session | SESSION_SECRET, SESSION_COOKIE_SECURE, SESSION_ALLOWED_ORIGINS; opaque 8 hours absolute / 30 minutes idle sessions, CSRF, local HTTP exception only. |
| Objects | EVIDENCE_ENDPOINT, EVIDENCE_BUCKET, EVIDENCE_ACCESS_KEY, EVIDENCE_SECRET_KEY, EVIDENCE_MAX_BYTES, EVIDENCE_UPLOAD_TTL_SECONDS; private versioning,10 MiBcap,15 minuteupload. |
| Chain | CHAIN_RPC_URL, CHAIN_ID, CHAIN_DEPLOYMENT_GENERATION, CHAIN_REGISTRY_ADDRESS, CHAIN_EXPECTED_CODE_HASH, CHAIN_CONFIRMATION_DEPTH=2; LOCAL_RUNNER_SIGNER_SECRET_REF; no raw keys frontend/DB/logs. |
| Jobs/simulation | WORKER_LEASE_SECONDS, WORKER_MAX_ATTEMPTS=8, DEMO_NAMESPACE, PAYMENT_MODE=simulated; stable economic receipt key and safe queue health. |

Exact names frozen when BusinessSettings created; separate from existing science Settings to avoid credential/initbehavior changes. All new settings validated at start up with safe errors. Never print complete environment or secret JSON. New `.env.example` files contain placeholders/non secret local defaults only; .gitignore exceptions allow examples, not populated values.

## Coding/change controls

Branches `codex/sprint-N-short-description`; small coherent commits naming WP IDs/domain behavior/tests, no auto generated approval claim. Do not reset user work, force push, auto-merge or commit secrets. Commit/PR publishing only as requested; keep diffs reviewable. Stable old API/DTOs untouched; business changes update PB-2 matrix/schemas/tests in same PR. Breaking published policy/evidence/ABI changes require versioning, migration/recovery plan and explicit scope approval when product semantics change.

Schema additive/ordered DB IDs, reviewed SQL and upgrade from empty/prior version; backup before destructive repair; no automatic downgrade of accepted history. New features need meaningful authorization/invariant/concurrency tests; no tests that merely duplicate a setter. Backend baseline pytest; frontend existing oxlint/build; chain compile/tests; E2E as authored. Optional future backend lint requires pinned tool/scope, not an invented current command.

Documentation should update planned versus actual state, exact files/test commands/results andnewrisk/corrections. Report progress at least everyminute whiletools/work permit; concise findings/next uncertainty, not repetitive unchanged polls. Stop after each authorized sprint report; passing gates does not authorize continuation.

## Recovery/approval boundaries

Read-only inspection/reversible edits/tests/installations necessary within an explicitly approved sprint proceed within that scope; respect normal tool escalation. Explicit approval required for next sprint, scientific algorithm change, lockedD01/D02 change, remote provisioning/cost/public deployment/real data, mass destructive reset/migration, ACL/ownership change, non local chain transaction andpublishing/merging not already requested. Real financial transfers/tokens/NFT/credits are outside current project scope entirely.

Onincident: hold unpaid obligations → stop affected dispatch → reconcile event/nonce/receipt → role-specific revocation/cancel → re-review exact versions → resume only clear valid dependencies. Unknown simulator lookup by economic UUID before retry. BackupDB+object versions+manifests+deployment registry; restore isolated namespace/hash check. Chain reset needs new generation, archives old receipts and preserves economic dedupe. No filesystem-wide or production reset button.
