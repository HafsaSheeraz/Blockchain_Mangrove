# 06 — MangroveWorkflowRegistry Solidity specification

**PROPOSED contract, not implemented, compiled, deployed or audited.** This document specifies a concrete Solidity interface and normative transition rules for later implementation. It intentionally contains no executable `.sol` file. It replaces the earlier publisher-only registry proposal: the local EVM must actually reject unauthorized or premature reward authorization.

## Deployment and trust model

One non-upgradeable `MangroveWorkflowRegistry`, Solidity 0.8.x compiler pinned during approved foundation work, OpenZeppelin AccessControl for global admin/service roles, plus project-scoped role bits. OpenZeppelin documents role-based access control; the workflow guards below are this project's design, not provided automatically by that library. [OpenZeppelin access control](https://docs.openzeppelin.com/contracts/5.x/access-control).

Local EVM first, fixed configured chain ID (proposed 31337), unique deployment ID derived from chain/genesis/deployment transaction/address/code hash. PB-1 uses separate backend-controlled demo keys for fictional actors. Workers do not install wallets. Transactions must be signed by the actor's bound local key, not one universal relayer. Admin has role-management/pause powers, not a bypass around authorization guards. No payable functions, transfers, ERC20, ERC721, NFT, credit or balance ledger.

Contract storage is publicly observable even if Solidity marks it private. Only opaque IDs, fictional addresses/amounts, digests, rule parameters and statuses belong on-chain; private evidence/identity data stays off-chain. [Solidity security considerations](https://docs.soliditylang.org/en/latest/security-considerations.html).

## Contract storage and identities

Keys are bytes32 values derived by `keccak256(abi.encode(deploymentDomain, entityType, UUID))`; store the exact mapping in DB. Entity IDs are distinct from SHA-256 evidence/manifest/decision commitments, which are also bytes32. The domain includes chain ID, contract address and schema; never reuse audit IDs across a reset deployment.

- `actorIdOf[address]` / `addressOfActor[actorCommitment]`: immutable unique actor binding per deployment. Admin registers a new actor once; disabled keys may be paused/revoked, not rebound to another person. Address distinction cannot prove real human independence.
- `projectRoles[projectKey][address]`: bits `ORG=1`, `NURSERY_OPERATOR=2`, `NURSERY_CONFIRMER=4`, `WORKER=8`, `VERIFIER=16`, `AUTHORIZER=32`. Global `ORG_CREATOR_ROLE`, `DEFAULT_ADMIN_ROLE`, `SIMULATOR_ROLE` handled separately.
- Project: owner/organization commitment/site digest, registered flag, paused flag. Organization owner initially has ORG. Membership transactions follow registration before policy/assignment commands.
- Policy: project, digest, immutable ComponentConfig[] and `published=true`. At most 8 components, masks restricted to 1/3/5/7 and appropriate task-stage definitions; no unbounded user loops.
- Assignment: project/policy/type, coordinator/worker/collector, `reviewers[3]`, assigned quantity, cancellation flag, active subject/decision keys per stage. M3/M6 minimum observation timestamps are bound when the Completion decision accepts the actual planting business date, not guessed at assignment time. For the proposed ±14-day window, not-before is due date minus14 days; the separate due date still uses3/6 calendar months. FastAPI handles upper-window/late-review rules. For primary case collector is worker; reviewers are independent fictional field verifiers.
- Supply: exact declaration/evidence commitment, declarer, confirmer, accepted quantity and effective flag. It proves confirmation of supply only; inventory reservation is enforced in FastAPI/Postgres.
- Subject: exact immutable claim/inspection revision commitment, evidence digest, assignment/stage, author, optional supply key, claimed count and observed timestamp, effective flag. Stage `Completion` is labeled `PLANTING` for plantation.
- Decision: subject key, reviewer, combined decision digest, field-report evidence digest, accepted quantity/live/cohort values and effective flag. All metadata/digest records remain historical after revocation.
- Authorization: obligation key, authorization key, assignment/component, amount/currency, authorizer, prerequisite decision keys/digest, effective/cancelled flags. `activeAuthorization[obligation]` prevents two active authorities.
- `settledObligations[obligation]` and simulated receipt digest: prevent a second recorded simulated settlement. They are audit states, not asset ownership or transfer.
- `usedEvents[eventId] = commandDigest`; every mutating business command consumes one event ID. Reusing it reverts even with same digest; delivery layer recognizes an already-confirmed identical command before resubmitting. Different command under same event ID is a hard conflict.

## Solidity interface (normative ABI proposal)

The implementation must expose the following ABI, with contract-specific errors/events. Array sizes are bounded as specified; string descriptions/photos are never stored.

```solidity
interface IMangroveWorkflowRegistry {
    enum Stage { Completion, Month3, Month6 }
    struct ComponentConfig {
        bytes32 key;
        uint8 requiredMask; // Completion=1, Month3=2, Month6=4
        uint64 rateMinor;  // integer minor PKR per accepted unit
        uint64 capMinor;
        bytes3 currency;   // bytes3("PKR")
        uint16 month3MinSurvivalBps;
        uint16 month6MinSurvivalBps;
    }
    struct AssignmentInput {
        bytes32 key;
        bytes32 project;
        bytes32 policy;
        bytes32 taskType;
        address worker;
        address collector;
        address[3] reviewers;
        uint32 assignedQuantity;
    }
    struct SubjectInput {
        bytes32 key;         // exact claim/inspection revision key
        bytes32 assignment;
        Stage stage;
        bytes32 contentDigest;
        bytes32 evidenceDigest;
        bytes32 supply;      // required for plantation completion
        uint32 claimedCount;
        uint64 observedAt;
    }
    struct DecisionInput {
        bytes32 key;
        bytes32 subject;
        bytes32 decisionDigest;
        bytes32 fieldEvidenceDigest;
        uint32 acceptedCount; // completion only
        uint32 liveCount;     // follow-up only
        uint32 cohortCount;   // original accepted cohort
        uint64 inspectedAt;
        uint64 month3NotBefore; // Completion decision only; zero otherwise
        uint64 month6NotBefore; // Completion decision only; zero otherwise
    }
    function bindActor(address actor, bytes32 actorCommitment) external;
    function registerProject(bytes32 eventId, bytes32 project,
        bytes32 organization, bytes32 siteDigest) external;
    function commitProjectRevision(bytes32 eventId, bytes32 project,
        bytes32 revision, bytes32 revisionDigest, bytes32 siteDigest) external;
    function setProjectRole(bytes32 eventId, bytes32 project,
        address actor, uint8 roles, bool enabled) external;
    function setProjectPaused(bytes32 eventId, bytes32 project,
        bool paused, bytes32 reasonDigest) external;
    function publishPolicy(bytes32 eventId, bytes32 project,
        bytes32 policy, bytes32 policyDigest, bytes32 siteDigest,
        ComponentConfig[] calldata components) external;
    function registerAssignment(bytes32 eventId,
        AssignmentInput calldata input) external;
    function replaceReviewer(bytes32 eventId, bytes32 assignment,
        Stage stage, address replacement, bytes32 reasonDigest) external;
    function cancelAssignment(bytes32 eventId, bytes32 assignment,
        bytes32 reasonDigest) external;
    function declareSupply(bytes32 eventId, bytes32 supply,
        bytes32 project, uint32 declaredCount,
        bytes32 evidenceDigest) external;
    function confirmSupply(bytes32 eventId, bytes32 supply,
        uint32 acceptedCount, bytes32 decisionDigest,
        bytes32 confirmationEvidenceDigest) external;
    function revokeSupply(bytes32 eventId, bytes32 supply,
        bytes32 reasonDigest) external;
    function commitSubject(bytes32 eventId,
        SubjectInput calldata input) external;
    function approveMilestone(bytes32 eventId,
        DecisionInput calldata input) external;
    function commitOutcome(bytes32 eventId, bytes32 project,
        bytes32 subject, uint8 outcome, bytes32 decisionDigest) external;
    function revokeSubject(bytes32 eventId, bytes32 subject,
        bytes32 reasonDigest) external;
    function revokeDecision(bytes32 eventId, bytes32 decision,
        bytes32 reasonDigest) external;
    function authorizeReward(bytes32 eventId, bytes32 authorization,
        bytes32 assignment, bytes32 component,
        uint64 expectedAmountMinor, bytes32 prerequisiteDigest) external;
    function cancelAuthorization(bytes32 eventId, bytes32 authorization,
        bytes32 reasonDigest) external;
    function recordSimulatedSettlement(bytes32 eventId,
        bytes32 authorization, bytes32 receiptDigest) external;
    function commitAudit(bytes32 eventId, bytes32 project,
        bytes32 subject, bytes32 payloadDigest) external;
    function isExecutable(bytes32 authorization) external view returns (bool);
    function commitmentOf(bytes32 subject) external view returns (bytes32);
    function commandDigestOf(bytes32 eventId) external view returns (bytes32);
    function activeDecision(bytes32 assignment, Stage stage)
        external view returns (bytes32);
    function activeAuthorizationOf(bytes32 obligation)
        external view returns (bytes32);
    function obligationOf(bytes32 assignment, bytes32 component)
        external view returns (bytes32);
}
```

`bindActor` uses AccessControl admin events in addition to a binding event and is not a business approval. Expose typed read getters for stored Policy/Assignment/Subject/Decision/Authorization in the implementation; ABI tuples exactly mirror storage fields above. `commitOutcome` supports rejected/changes-requested decisions and never sets an approval bit. `commitAudit` records ancillary events only; it cannot set milestone/authorization/settlement state.

## Normative guards and transition algorithms

Every mutation validates known registered actor, nonzero keys/digests, project existence, caller role/scope, correct deployment, unused event ID and immutable key uniqueness. Apply checks before effects; no external value calls exist. Store commandDigest and emit event only in the successful transaction. Global role changes use AccessControl admin checks plus explicit project membership events; default admin cannot call `authorizeReward` without satisfying all normal actor/milestone guards.

| Function | Required checks and effects |
| --- | --- |
| registerProject | Global ORG_CREATOR caller, bound actor, unused project; store owner/org/site, grant caller project ORG, emit ProjectRegistered. Registration is organization attestation, not proof of tenure. |
| commitProjectRevision | Project ORG, new revision key/digest/site commitment; append revision/current-site projection, never change old revision/policy/assignment. Subsequent policy publication binds its explicit siteDigest. A12 maps initial publish to registration and later publish to this function. |
| setProjectRole | Global admin, existing project/bound target, allowlisted bits; grant/revoke only requested bits; event. Cannot edit old decisions or actor identity. |
| setProjectPaused | Project ORG or global admin; reason digest; pause blocks new subjects/approvals/authority/settlement but permits revocation/cancellation/recovery logs. |
| publishPolicy | Project ORG, unpaused, immutable new policy key/site digest, 1–8 components, unique component keys, valid mask/positive rate/cap/currency/thresholds <=10000. Require Completion in every payable mask. Store site commitment, complete rule array and digest atomically; assignments retain it despite future project revision. |
| registerAssignment | ORG, same project/published policy; worker/collector bound WORKER, each required reviewer bound project VERIFIER distinct from worker, collector and coordinator; positive assigned quantity. Save participants and versioned reviewer roster. Follow-up minimum timestamps are established by accepted Completion decision. |
| replaceReviewer | ORG; bound project VERIFIER replacement independent of worker/collector/coordinator/supply actors; reason required. Cancel any active authority first. Atomically invalidate prior stage approval for future use, emit its invalidation plus ReviewerReplaced, update roster and require fresh independent review. This is administrative re-review, not an org approval/rejection of work. Old decision/reviewer remains historical. This path works when prior reviewer key/role was revoked. |
| cancelAssignment | ORG, reason required; set cancelled, invalidate future executability and emit AssignmentCancelled. Does not erase accepted work or simulator receipts. Submitted/accepted work cancellation requires the app dispute protocol. |
| declareSupply | Project NURSERY_OPERATOR, positive count, new supply key/evidence commitment. |
| confirmSupply | Project NURSERY_CONFIRMER, caller != declarer, 0 < accepted <= declared, unconfirmed key; store confirmation evidence/decision digest. Worker/confirmer conflicts are also checked when subject references supply. |
| revokeSupply | Original confirmer with active role or project ORG administrative hold; reason required; mark supply ineffective, emit SupplyRevoked. Any dependent Completion/authority fails effective-supply checks until new confirmation/review; old inventory/work history retained. |
| commitSubject | Completion author = assignment worker; follow-up author = collector. Caller still has WORKER role. Exact assignment/project/policy; nonzero evidence/content hash; observation not future. Plantation Completion requires effective confirmed supply in same project, confirmer != worker, positive claimed <= assigned. Before replacing active subject, previous one must be unapproved or explicitly revoked and no executable authority may be bypassed. Mark prior unapproved subject superseded; preserve commitment; activate new key. |
| approveMilestone | Caller exactly assigned stage reviewer, currently project VERIFIER; differs from subject author, worker, collector, coordinator and relevant supply declarer/confirmer. Subject is active/effective, not already approved, immutable version/digests present; independent field report required. Completion: 0 < accepted <= claimed <= assigned; bind verifier-attested M3/M6 not-before timestamps computed by FastAPI from accepted planting date, ordered strictly after that date and each other. Nonplantation completion-only schedule fields zero. Follow-up: Completion has effective approval; subject observedAt and inspectedAt >= bound stage minimum, inspectedAt >= subject observedAt and <= block.timestamp; cohort equals accepted Completion count; 0 <= live <= cohort; schedule fields zero. M6 may exist before M3 is approved but cannot alone satisfy a mask requiring M3. Store exact approved decision and stage pointer; changed Completion invalidates dependent schedules/approvals. |
| commitOutcome | Assigned independent reviewer for subject; outcome rejected or changes-requested only; binds subject and decision digest; clears no existing approval silently. Approved subject requires explicit revoke before changed outcome. |
| revokeSubject / revokeDecision | Assigned independent reviewer for stage with current role (or the same reviewer recording correction); reason mandatory. Mark non-effective, emit Revoked. Completion revocation invalidates dependent M3/M6/authorization executability by prerequisite checks. No erasure; pending settlements held. No arbitrary worker/admin reversal. |
| authorizeReward | Project AUTHORIZER distinct from worker, collector, coordinator, subject authors and all prerequisite reviewers. Assignment/policy/component exact, assignment not cancelled, project unpaused, referenced supply effective, obligation not settled and no active uncancelled authority. Recompute required approvals and current pointers. Every prerequisite subject/decision effective; follow-up survival `live*10000 >= cohort*thresholdBps`; Completion acceptedCount known. Compute `min(acceptedCount*rateMinor,capMinor)` in uint256; reject overflow/out-of-range and mismatch with expectedAmountMinor/currency. Prerequisite digest must equal computed digest of policy/component/active subject+decision keys. Store authority/pointers/digest; emit RewardAuthorized. No transfer. |
| cancelAuthorization | Original authorizer with current role, or project ORG for dispute hold; reason; mark cancelled. Cannot erase or unset settled obligation. New authority permitted only if never settled and prior authority cancelled. |
| isExecutable | True only if authority effective/not cancelled, assignment not cancelled, project unpaused, obligation not settled, current prerequisite pointers/digests still match recorded authority, no revoked subject/decision or referenced supply, required worker/collector/authorizer/reviewer roles still active, and policy thresholds still satisfied. Return false rather than implying old approval is permanently usable. |
| recordSimulatedSettlement | Global SIMULATOR service, isExecutable true, new receipt digest; mark obligation settled once and emit **SimulatedSettlementRecorded**. This records a simulator assertion; it is not chain payment. |
| commitAudit | Project participant with appropriate scope and fresh event ID; store ancillary digest/event; never changes verification/eligibility authority. |

`prerequisiteDigest = keccak256(abi.encode(deploymentDomain, assignmentKey, policyKey, componentKey, requiredMask, currentSubjectKeys[3], currentDecisionKeys[3]))`; use zero for stages not required. `obligationKey = keccak256(abi.encode(deploymentDomain, assignmentKey, componentKey))`. Rates/caps and serialized monetary values are bounded to 9,007,199,254,740,991 minor units for exact cross-language JSON integers even though Solidity uses uint64. Direct local RPC calls must fail the same checks as API-originated calls. Solidity does not inspect private evidence bytes; a nonzero digest alone is not quality validation.

## Events and errors

Every business event includes indexed eventId/projectKey plus the subject key, actor and canonical command digest where relevant. Required events: `ActorBound`, `ProjectRegistered`, `ProjectRoleChanged`, `ProjectPauseChanged`, `PolicyPublished`, `AssignmentRegistered`, `SupplyDeclared`, `SupplyConfirmed`, `SubjectCommitted`, `MilestoneApproved`, `OutcomeCommitted`, `SubjectRevoked`, `DecisionRevoked`, `RewardAuthorized`, `AuthorizationCancelled`, `SimulatedSettlementRecorded`, `AuditCommitted`.

MilestoneApproved includes assignment, stage, subject/decision keys, subject evidence/field evidence/decision commitments and accepted count or live/cohort counts. RewardAuthorized includes obligation/auth keys, component, frozen amount/currency and prerequisite digest. No event contains evidence URLs, names or free-text reasons; reason digests refer to private authorized records.

Custom errors: `UnknownActor`, `WrongProjectRole`, `WrongReviewer`, `SelfApproval`, `ProjectPaused`, `UnknownPolicy`, `ImmutableKeyExists`, `EventReplay`, `StaleSubject`, `InvalidEvidenceDigest`, `InvalidSupply`, `InvalidQuantity`, `TooEarlyObservation`, `MissingMilestone`, `SurvivalThresholdNotMet`, `PrerequisiteChanged`, `AmountMismatch`, `ActiveAuthorizationExists`, `AlreadySimulatedSettled`, `InvalidTransition`. Additional events: `ProjectRevisionCommitted`, `ReviewerReplaced` (old/new actor, stage/reason), `AssignmentCancelled`, `SupplyRevoked`.

## What is enforced where

| Rule | Contract | FastAPI/Postgres |
| --- | --- | --- |
| Local actor address/project role and reviewer roster | Yes | Real session/user scope and signer mapping also required. |
| No self-approval | Address checks | Person/account/organization conflict checks, including multi-role/alias governance. |
| Evidence/decision exact commitment and revision pointer | Stores/checks immutable references | Validates bytes, metadata, sealed manifests, access and content/check profile. |
| Nursery confirms supply, not planting | Separate function; no milestone bit | Inventory reservations, observation records, over-allocation locks and units. |
| Required milestones/survival threshold/fixed integer reward amount | Yes for configured component | Computes same values and checks inspection method/denominator, field quality, date rules/late reasons. |
| 3/6-calendar-month schedule | Enforces configured minimum timestamps | Computes calendar arithmetic, due/windows, reminders and fictional date provenance. Contract cannot discover truthful observation dates. |
| Single active authority / replay / changed prerequisites | Yes | Idempotent commands, obligation uniqueness, holds, outbox ordering and simulator dedupe. |
| Blockchain confirmations / reorganizations | Contract cannot know its own later canonicality | Receipt depth/block hash reconciliation, never treat tx hash as confirmed. |
| Simulated settlement | Records one service assertion | Simulator creates receipt, ensures no real transfer and reconciles retries. |
| Planting truth, survival truth, real identity, land rights, partnership, carbon removal | **No** | Human demo attestations and private synthetic data; also not independently proved by FastAPI. |

## Delivery, replay and finality protocol

DB command records exact ABI inputs, actor binding and dependency operations. Submit registerProject → role grants → publishPolicy → registerAssignment → supply commitments → subject → decisions → authorization. Workers serialize nonce per signer, use leased commands and persisted nonces/tx hashes; role changes cannot rewrite a queued command actor.

Before retry, query event command digest: if identical in canonical chain, reconcile instead of resending; if conflicting, block/quarantine. Unknown transaction outcome stays unknown until receipt/nonce/event lookup resolves. Receipt status 0 means reverted, not business rejection. Local confirmation policy proposal: canonical success receipt plus two subsequent mined blocks; label it “local confirmed”, never “mainnet finalized”. Recheck receipt block hashes after restart; orphaned prerequisites hold downstream authority/settlement.

Simulator executes only after canonical confirmed authorization, current DB holds checked and fresh `isExecutable` true. Its stable idempotency key is **obligationKey**, surviving cancelled/reissued authorization IDs. After simulated receipt is durable, enqueue recordSimulatedSettlement; while that audit tx is pending, show simulated settlement and chain audit pending separately. Receipt replay/reconciliation never initiates another simulated obligation.

Required contract tests and direct-RPC negative tests: CHAIN-01–CHAIN-12 in [testing](14-testing-and-operations.md). Interface is a specification, not a claim of compiled correctness or security certification.
