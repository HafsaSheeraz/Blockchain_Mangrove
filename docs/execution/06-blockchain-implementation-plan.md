# 06 — Implementable Solidity/local-chain plan

**PROPOSED contract specification, not compiled/deployed code.** Retain [PB-1 Solidity interface/storage/guard definitions](../playbook/06-solidity-contract.md) except explicit changes here. Contract name `MangroveWorkflowRegistry`; non-upgradeable; local EVM31337; distinct backend-held role signers, no browser wallet/asset/token/payable function. D02 is locked, not an open custody decision.

## Typed ABI and policy amendments

Method registry below names every retained method; PB-1 signatures unchanged unless amended here. Use the following **replacement** struct/signature declarations in the later implementation, not alongside old overloaded variants. Unchanged primary keys are bytes 32. Dates encode valid GregorianYYYYMMDD integers, not chain timestamps; actual chain receipt time remains separate.

```solidity
enum TaskKind { PropaguleCollection, NurseryWork, Plantation, Maintenance, FieldMonitoring }
enum PolicyProfile { ConfiguredComponents, PlantationFinalV1 }
enum Stage { Completion, Month3, Month6 }
struct PolicyInput {
    bytes32 key; bytes32 project; bytes32 policyDigest; bytes32 siteDigest;
    TaskKind taskKind; PolicyProfile profile;
    bool requiresSupply; uint32 unitScale; uint8 requiredStageMask;
}
struct ComponentConfig {
    bytes32 key; uint8 requiredMask; uint64 rateMinor; uint64 capMinor;
    bytes3 currency; uint16 month3MinSurvivalBps; uint16 month6MinSurvivalBps;
}
struct AssignmentInput {
    bytes32 key; bytes32 project; bytes32 policy;
    address worker; address collector; address[3] reviewers;
    uint64 assignedAtoms;
}
struct SupplyLink { bytes32 supply; uint64 quantityAtoms; }
struct SubjectInput {
    bytes32 key; bytes32 assignment; Stage stage;
    bytes32 contentDigest; bytes32 evidenceDigest; bytes32 allocationDigest;
    bytes32 parentCompletionDecision;
    uint64 claimedAtoms; uint32 observedOn;
}
struct DecisionInput {
    bytes32 key; bytes32 subject; bytes32 decisionDigest; bytes32 fieldEvidenceDigest;
    bytes32 parentCompletionDecision;
    uint64 acceptedAtoms; uint64 liveCount; uint64 cohortCount;
    uint32 inspectedOn; bool lateAccepted; bytes32 lateReasonDigest;
}
function registerProject(bytes32 eventId, bytes32 project,
    bytes32 organization, bytes32 siteDigest, address supplyConfirmer) external;
function setSupplyConfirmer(bytes32 eventId, bytes32 project,
    address confirmer, bytes32 reasonDigest) external;
function publishPolicy(bytes32 eventId, PolicyInput calldata input,
    ComponentConfig[] calldata components) external;
function declareSupply(bytes32 eventId, bytes32 supply, bytes32 project,
    uint64 declaredAtoms, bytes32 evidenceDigest) external;
function confirmSupply(bytes32 eventId, bytes32 supply, uint64 acceptedAtoms,
    bytes32 decisionDigest, bytes32 confirmationEvidenceDigest) external;
function commitSubject(bytes32 eventId, SubjectInput calldata input,
    SupplyLink[] calldata supplies) external;
function approveMilestone(bytes32 eventId, DecisionInput calldata input) external;
```

The fragments are ABI specification inside Mark down, not deployable implementation. Retained AssignmentInput now identifies task kind through its immutable policy, eliminating caller-supplied arbitrary task-type labels. Retain PB-1 structs/functions for actor binding, roles, revisions, pause, revocation, authorization, ancillary audit and getters with storage fields updated to these types.

**Primary profile contract guards:** taskKind=Plantation, requiresSupply=true, scale 1, requiredStageMask 7, one payable final component, rate 1000, cap 1000000, currency PKR, M3 bps 8000, M6 bps 7500; assignedAtoms<=1000. Wrong constant reverts InvalidPrimaryPolicy. Configured-component policies support separate completion/survival and four smaller tasks; rates/requirements stay versioned. At most 8 components and 8 unique supply links. Nonplantation Completion-only policies require no survival fields.

quantityAtoms=exact DecimalQuantity*unitScale. Allowed scales 1/10/100/1000/10000; pricing=floor(acceptedAtoms*rateMinor/unitScale), capped. Primary scale 1 means acceptedAtoms=accepted seedlings. Numeric limits: stored money/atoms<=9,007,199,254,740,991 and intermediate multiplication uint 256. Primary census counts integers<=acceptedQ. No scaled numeric type is a cryptocurrency token.

## Date and parent-decision enforcement

Typed read signatures are also frozen for K29–K31:

```solidity
struct AuthorizationRecord {
    bytes32 obligation; bytes32 assignment; bytes32 policy; bytes32 component;
    address authorizer; uint64 amountMinor; bytes3 currency;
    bytes32[3] subjects; bytes32[3] decisions;
    bytes32 parentCompletion; bytes32 prerequisiteDigest;
    bool cancelled; bool simulatedSettled;
}
function getPolicy(bytes32 key) external view
    returns (PolicyInput memory, ComponentConfig[] memory);
function getAssignment(bytes32 key) external view
    returns (AssignmentInput memory, bool cancelled, uint32[2] memory dueOn,
             bytes32[3] memory subjects, bytes32[3] memory decisions,
             uint32 rosterVersion);
function getSubject(bytes32 key) external view
    returns (SubjectInput memory, SupplyLink[] memory, address author, bool effective);
function getDecision(bytes32 key) external view
    returns (DecisionInput memory, address reviewer, bool effective);
function getAuthorization(bytes32 key) external view
    returns (AuthorizationRecord memory);
```

Unknown keys revert a documented unknown-resource error rather than returning an ambiguous zero-filled approved record. Stage encoding is Completion=0, Month3=1, Month6=2; component masks remain1/2/4. K16 outcome encoding is1=Rejected,2=ChangesRequested; no numeric outcome grants approval.

Completion subject's observedOn is accepted planting business date. Contract pure helper `addCalendarMonths(date,n)`: validate date, parse y=date/10000, m=(date/100)%100, d=date%100; totalMonths=12*y+(m-1)+n; y 2=totalMonths/12, m 2=totalMonths%12+1; d 2=min(d, daysInMonth(y 2, m 2)); return y 2*10000+m 2*100+d 2. Gregorian leap rule divisible 4 except centuries unless divisible 400; supported 2000–2099. Off-chain Python uses identical vectors. DueM3/M6 computed by contract from exact Completion subject date, not trusted caller-supplied minimum timestamps.

Dates are date-only fields; date Today derives from `block.timestamp+18000` seconds for fixed Asia/Karachi+05 demonstration locale. Visit/report cannot be future; Completion visit>=planting date. Follow-up observation/report dates>=computed stage due; both include lateAccepted+nonzero lateReasonDigest if beyond due+14 days. A pure bounded date-add-days helper handles the 14-day grace; reminders may start 14 days before due but early observations never pass.

Follow-up SubjectInput.parentCompletionDecision must equal active effective Completion decision; DecisionInput repeats it; stored parent mandatory. Contract `stageValid` checks active subject, active effective decision, exact parent, matching original cohort, role/conflicts and evidence commitments. Completion correction/replacement invalidates every dependent stage even if count unchanged. An accepted survey may be recorded below threshold; `milestonePassed(component,stage)` then false. Authorize and isExecutable independently evaluate both thresholds.

## Storage and signer binding

Stage-specific fields are strict. Completion: parentCompletionDecision=zero; acceptedAtoms positive; liveCount/cohortCount=zero; supply links required only when policy.requiresSupply. Follow-up: SubjectInput.claimedAtoms=original accepted cohort, parentCompletionDecision nonzero; supplies empty and allocationDigest zero (inventory is not reserved again); DecisionInput.acceptedAtoms=zero, liveCount/cohortCount supplied and bound to that exact parent. K23 validates the supply recorded on Completion, not a new supply on each survey.

For every Plantation policy unitScale=1 and requiresSupply=true. Nonplantation configured policies are Completion-only (mask1); their monitoring-work records do not become plantation survival approvals. Primary profile requires all three stages and reviewers; unused stage reviewer slots in Completion-only assignments are zero. Numeric cross-products cast to uint256 before multiplication.

Retain PB-1 actor/address uniqueness, scoped role bitsORG1/N2/C4/W8/V16/P32 plus global creator/admin/simulator. Add project default supply confirmer; declarations snapshot expected confirmer. Changing default affects only new declarations. Claim supply list checks every declaration's expected confirmer/current C role and disallows reviewer/worker conflict with any supply participant. Store allocations/list digest; contract checks positive unique links summing Completion claimedAtoms when supply required; DB alone enforces physical inventory capacity/reservations across claims.

Policy stores explicit taskKind/profile/site/scale/supply flag and bounded component rules. Assignment pins it and roster; subject pins claim/inspection evidence version and parent; decision pins subject and independent field evidence; authority pins policy/component/subject+decision set/prerequisite digest/frozen amount. Ancillary audit cannot set any of these transitions.

Actor keys stay in runner secret configuration. Only current backend-authorized role command selects corresponding bound actor signer. Immutable address → fictional user binding does not prove real identities, independence or data truth; runner/admin compromise remains a declared trust boundary.

## Deployment domain, commitments and replay

Before deployment create random deploymentGeneration bytes 32, pass it to constructor with admin. `domain=keccak256(abi.encode("Mangrove/PB-2",block.chainid,address(this),deploymentGeneration))`. Keys use `keccak256(abi.encode(domain,entityType,uuidBytes16))`; commit exact ABI tuple schemas in tests. New generation changes domain even if local reset repeats chainID/address/genesis/code.

Structured manifest SHA256 prefixes change to Mangrove/EvidenceSet/PB-2 and Mangrove/Decision/PB-2 plus NUL; canonical JCS UTF8 and exact bytes retained. File hash remains SHA256 raw bytes. `commandDigest=keccak256(abi.encode(domain,msg.sender,functionSelector,typedArgumentsWithoutEventId))`. Store usedEvents[eventId] only after successful guards. Event ID deterministic from audit UUID/command step/deploymentGeneration; same-key retry reverts on-chain, runner reconciles identical canonical command rather than resending; conflicting digest blocks.

Stable economic obligation UUID=assignment UUID+policyComponentUUID within demo namespace, independent of deployment. On-chain obligationKey hashes deploymentdomain+those mapped keys. Simulator dedupe uses economic UUID; resetting chain or replacing authorization does not reset receipt uniqueness.

## K method/guard registry

These are **PROPOSED method IDs** for traceability. Each row inherits nonzero input/current role/scoped project/unused event guards where relevant. Read getters do not require business signing.

| ID | Method | Essential checks/effect |
| --- | --- | --- |
| K01 | bindActor | Global admin; one address and actorcommitment binding forever per deployment; ActorBound. |
| K02 | registerProject | Creator/organization actor; new key; site+org+default C; initial ORG grant; no tenure claim. |
| K03 | commitProjectRevision | ORG; new immutable revision/site digest; old assignments/policies untouched. |
| K04 | setProjectRole | Global admin, bound target, known role bits; auditable grant/revoke; never rewrites old decisions. |
| K05 | setProjectPaused | ORG/admin; reason; blocks new approval/authority/settlement; permits revocation/cancel/recovery. |
| K06 | publishPolicy | ORG; immutable policy, valid type/scale/mask/components; primary constants checked exactly. |
| K07 | registerAssignment | ORG; policy/project match; activeW/collector and required V roster independent; quantity positive/cap. |
| K08 | replaceReviewer | ORG, new independent V; cancel active authority first; invalidate old stage approval for future use; preserve history; re-review. |
| K09 | cancelAssignment | ORG, reason; cancelled prevents future authority/execution, settled history remains. |
| K10 | setSupplyConfirmer | ORG, bound active C; affects future declarations only; prior confirmer snap retained. |
| K11 | declareSupply | N; snapshot project C distinct from N; positive atoms, exact evidence. |
| K12 | confirmSupply | Exactly snapshotted activeC, notN; positive accepted<=declared; immutable decision/evidence. No planting bit. |
| K13 | revokeSupply | OriginalactiveC or ORG administrative hold; reason; dependent stage/authority invalid; no history erase. |
| K14 | commitSubject | Completion author=W, followup author=collector; exact assignment/policy; valid date/evidence; effective supply links if required; followup exact parent; replacement cannot bypass effective approval. |
| K15 | approveMilestone | Assigned current V distinct from subject author/W/collector/coordinator/all related N/C; active exact subject+report; Completion accepted<=claimed<=assigned; followup count/cohort/date/parent checks; stores accepted survey even if threshold fails. |
| K16 | commitOutcome | AssignedindependentV; rejected/changes_requested only; no approved bit; effective approval needs explicit revocation first. |
| K17 | revokeSubject | IndependentstageV; reason; subject in active, dependent stages/authority non executable; no preimage erase. |
| K18 | revokeDecision | IndependentstageV; reason; decision ineffective; keep evidence/historical actor. |
| K19 | authorizeReward | ActiveP different from W/collector/coordinator/subject authors/all prerequisite V; unpaused/uncancelled/not settled; all required current parent-linked decisions effective; required thresholds met; exact amount/digest; one active authority. |
| K20 | cancelAuthorization | OriginalactiveP or ORGhold; record cancelled; cannot unset settled obligation. |
| K21 | recordSimulatedSettlement | RestrictedSIMULATOR, current isExecutable; new receipt; set settled obligation once; no asset transfer. |
| K22 | commitAudit | Allowed project participant; ancillary digest only; cannot approve, authorize, clear hold or mark settled. |
| K23 | isExecutable | Current authority/not cancelled, project active, assignment active, not settled, exact current pointer/parent/digest/roles/supply/thresholds; false if anything changed. |
| K24 | commitmentOf | Read immutable subject content commitment. |
| K25 | commandDigestOf | Read used event command hash for reconciliation. |
| K26 | activeDecision | Read assignment/stage pointer (caller still must inspect validity). |
| K27 | activeAuthorizationOf | Read obligation authority pointer, not proof of current executability. |
| K28 | obligationOf | Read derive deployment-scoped obligationkey. |
| K29 | getPolicy | Typed immutable PolicyInput/components getter. |
| K30 | getAssignment | Typed assignment/roster/due/cancellation getter. |
| K31 | getSubject/getDecision/getAuthorization | Typed record getters matching amended structs/history/effectiveness. |

K02 default C may be bound before project C role is granted; K11 waits for canonical role grant. Bootstrap order avoids requiring a role on a nonexistent project. No global admin can skip K15/K19 guards. Reassignment/role grant cannot resurrect an old decision as another actor's attestation.

`prerequisiteDigest=keccak256(abi.encode(domain,assignmentKey,policyKey,componentKey,requiredMask,subjectKeys[3],decisionKeys[3],parentCompletionKey))`; zero unused stage slots. K19 computes expected amount internally, compares caller expected; profile PKR fixed. K23 recomputes full validity rather than relying on stored booleanalone.

## Typed events and errors

`MilestoneApproved` denotes acceptance of the exact field attestation. It is not an unconditional reward-pass signal: an accepted accurate census below a component threshold remains failed for that component. Projections evaluate the recorded counts and policy; K19 independently rejects below-threshold reward authorization.

One common event preserves every business-command receipt:

```solidity
event CommandCommitted(bytes32 indexed eventId, bytes32 indexed project,
    bytes32 indexed subject, address actor, bytes4 selector, bytes32 commandDigest);
event ActorBound(address indexed actor, bytes32 indexed actorCommitment);
event MilestoneApproved(bytes32 indexed eventId, bytes32 indexed assignment,
    bytes32 indexed decision, uint8 stage, bytes32 subject,
    bytes32 parentCompletion, bytes32 decisionDigest, bytes32 fieldEvidenceDigest,
    uint64 acceptedAtoms, uint64 liveCount, uint64 cohortCount);
event RewardAuthorized(bytes32 indexed eventId, bytes32 indexed obligation,
    bytes32 indexed authorization, bytes32 assignment, bytes32 component,
    address actor, uint64 amountMinor, bytes3 currency, bytes32 prerequisiteDigest);
event SimulatedSettlementRecorded(bytes32 indexed eventId, bytes32 indexed obligation,
    bytes32 indexed authorization, bytes32 receiptDigest);
```

Other workflow events use exact shared signature `EventName(bytes32 indexed eventId,bytes32 indexed project,bytes32 indexed subject,address actor,bytes32 payloadDigest)`: ProjectRegistered, ProjectRevisionCommitted, ProjectRoleChanged, ProjectPauseChanged, PolicyPublished, AssignmentRegistered, ReviewerReplaced, AssignmentCancelled, SupplyConfirmerChanged, SupplyDeclared, SupplyConfirmed, SupplyRevoked, SubjectCommitted, OutcomeCommitted, SubjectRevoked, DecisionRevoked, AuthorizationCancelled, AuditCommitted. Their payloadDigest is SHA256 canonical event payload containing prior/current roster/role/state/reason commitments as appropriate. Full input/calldata+typed getters available for authorized reconstruction; no evidence URLs/names/free-text reasons.

Events allow at most 3 indexed fields on non anonymous logs. Freeze typed ABI/test vectors before implementation; do not rely on guessed selectors. [Solidity ABI](https://docs.soliditylang.org/en/latest/abi-spec.html). Role administration uses maintained AccessControl but all workflow guards are project-specific. [AccessControl](https://docs.openzeppelin.com/contracts/5.x/access-control).

Retain PB-1 custom errors as zero-argument errors, plus InvalidPrimaryPolicy, InvalidParentDecision, InvalidDate, InvalidScale, ConfirmerMismatch, InvalidSupplyLinks, AssignmentCancelledError. Same error used consistently in direct RPC tests; no sensitive payload strings. Standard AccessControl denial errors may surface before a custom workflow guard and tests must accept the documented precedence.

## Reconciliation/reset and trusted facts

Unknown-resource custom errors are UnknownProject, UnknownAssignment, UnknownSubject, UnknownDecision and UnknownAuthorization, in addition to UnknownPolicy from PB-1. All are zero-argument errors. Their selection is deterministic by lookup order; tests distinguish unknown resources from known but ineffective/revoked records.

Persist nonce, signed bytes/hash before send; lease/serialize per signer. Submit dependencies registerproject → roles/default C → policy → assignment → supply → subject → decision → authority → settlement assertion. Lookup event digest/nonce/receipt before retry; successful receipt status 1 + same canonical block hash +2 subsequent locally mined blocks = local confirmed. Runner explicitly mines observation blocks under local demo setting to avoid waiting forever on idleautomine; do not backdate field or block time.

Orphaned/reverted/unknown commands stop downstream dispatch. Reconcile receipt and current getter state; do not treat tx hash as success. New local chain generation archives prior projections and replays only still-effective decisions in dependency order, preserves DB receipt UUID dedupe. Reset tool requires exact namespace/deployment verification and explicit authorized sprint/reset scope.

Local simulator may already have a durable simulated receipt when later K21 audit fails due to cancellation/reorg. Preserve local success with audit_discrepancy; block reauthorization/re-execution by economic UUID, retain reason/incident and append ancillary K22 if appropriate. Never force K21 valid or fake chain confirmation.

Contract independently checks roles/address separation/current versions/parents/date arithmetic/masks/threshold comparisons/integer amount/replay/one active authority/one settled assertion. FastAPI/DB validate actual file bytes/access/inventory/unit semantics/current human consent; local runner custody and claimed visit/count truth remain trusted off chain. Neither contract nor FastAPI independently sees physical planting, honest census, real identity, tenure or carbon removal.

DirectRPC tests must bypass FastAPI and fail wrong role, self review, wrong parent, stalesubject, missingM3/M6, low threshold, wrong primary constants, wrong amount, replay, duplicate authority, revoked prerequisite, publisher audit bypass and reset-economic duplication. Detailed IDs in 09.
