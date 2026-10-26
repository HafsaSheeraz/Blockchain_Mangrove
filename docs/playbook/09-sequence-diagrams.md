# 09 — Cross-module sequence diagrams

**PROPOSED.** DB writes include audit/outbox atomically. Chain and inbox are eventual independent consumers. HTTP 202 never claims downstream confirmation. “Next user” reads the same shared resource in their role's screen.

## Project, policy and assignment

```mermaid
sequenceDiagram
    actor O as Organization
    participant UI as React shared shell
    participant API as FastAPI project services
    participant DB as PostgreSQL/PostGIS
    participant CW as Chain worker
    participant EVM as Local EVM
    participant NW as Inbox worker
    actor W as Assigned worker
    O->>UI: Save project, AOI, rules and task
    UI->>API: A06/A11/A14-A16/A20/A72
    API->>DB: Validate scope; persist immutable versions
    UI->>API: A12 publish; A21 assign
    API->>DB: Lock; write state + audit + dependent outbox
    API-->>UI: 202 project/assignment; chain queued
    CW->>DB: Lease registration / role / policy / assignment commands
    CW->>EVM: Actor-specific transactions in dependency order
    EVM-->>CW: Receipts / role and assignment events
    CW->>DB: Canonical receipt/depth projection
    NW->>DB: Deliver N01/N02 once
    W->>UI: Open inbox → assignment
    UI->>API: A22 then A23 accept/start
    API->>DB: Shared assignment transition + N03 intent
    API-->>UI: Current assignment and allowed actions
```

## Supply, evidence, checks and independent planting decision

```mermaid
sequenceDiagram
    actor N as Nursery operator / confirmer
    actor W as Worker
    participant UI as React
    participant API as FastAPI Trust/evidence
    participant OBJ as Private objects
    participant DB as Database/outbox
    participant J as Checks and chain workers
    participant EVM as Local EVM
    participant IN as Shared inbox
    actor V as Independent field verifier
    N->>API: A38 declaration; distinct confirmer A39
    API->>DB: Confirm supply + audit/outbox, no planting approval
    J->>EVM: declareSupply / confirmSupply
    API-->>IN: N05 supply handoff intent
    W->>UI: Complete assigned plantation
    UI->>API: A29 upload slot
    API-->>UI: Bounded signed private upload
    UI->>OBJ: Upload bytes/version
    UI->>API: A30 complete; A33-A34 seal
    J->>OBJ: Read/hash/validate exact bytes
    J->>DB: Valid EvidenceVersion / manifest
    UI->>API: A28 submit exact claim/evidence version
    API->>DB: Lock inventory, reserve supply, audit/check outbox
    API-->>UI: 202 checking / chain pending
    J->>DB: CheckRun passed or flagged / ready
    J->>EVM: commitSubject
    J->>IN: N08 review-ready
    V->>UI: Open assigned exact-version review
    V->>API: A46-A48 field visit with separate report
    V->>API: A43 decision with exact subject/check/report digests
    API->>DB: Conflict checks; immutable decision; milestone schedule; outbox
    J->>EVM: approveMilestone signed by bound verifier
    EVM-->>J: MilestoneApproved or revert
    J->>DB: Receipt / canonical confirmation projection
    J->>IN: N09 worker decision and N10 future monitoring intents
```

## Follow-up with insufficient satellite evidence

```mermaid
sequenceDiagram
    participant SCH as Due-date scheduler
    participant DB as Shared database
    participant IN as In-app inbox
    actor C as Field collector
    participant API as FastAPI monitoring/GIS adapter
    participant ONE as Existing Mangrove One services
    actor V as Independent verifier
    participant CH as Chain worker / local EVM
    SCH->>DB: Lease M3/M6 schedule unique key
    SCH->>IN: N10 due / N11 overdue
    C->>API: A64 optional environmental snapshot
    API->>ONE: Existing AOI context request
    ONE-->>API: Sparse/no-data/unavailable context
    API->>DB: Snapshot and context insufficient, no survival inference
    C->>API: A46-A48 census + field evidence
    API->>DB: Freeze inspection/checks; review handoff
    API-->>IN: N12 assigned verifier
    V->>API: A43 approve/reject exact inspection version + field report
    API->>DB: Decision, effective milestone, eligibility command
    CH->>CH: commitSubject / approveMilestone / receipt checks
    CH->>DB: Chain state independent of human decision
    API-->>IN: N13 decision / N14 eligibility changed
    Note over DB,CH: Repeat independently for 3 and 6 calendar months
```

## Eligibility → authorization → simulated settlement

```mermaid
sequenceDiagram
    participant E as Eligibility worker
    participant DB as PostgreSQL
    participant IN as Shared inbox
    actor P as Payment authorizer
    participant API as FastAPI Steward
    participant CW as Chain worker
    participant EVM as Local contract
    participant SIM as Payment simulator
    actor W as Worker
    E->>DB: Read exact PLANTING/M3/M6 + policy; lock obligation
    E->>DB: Append eligible evaluation / fixed amount / N14
    IN-->>P: Open reward obligation
    P->>API: A52 approve human authorization
    API->>DB: Recheck current eligible inputs/conflicts/holds; outbox
    API-->>P: 202 approved_pending_chain
    CW->>EVM: authorizeReward expected amount/prerequisite digest
    EVM->>EVM: Roles + versions + mask + threshold + replay guards
    EVM-->>CW: RewardAuthorized receipt
    CW->>DB: Confirm canonical local depth; authority authorized
    IN-->>P: N16 ready for simulated settlement
    P->>API: A55 acknowledge_simulated
    API->>DB: Lock authority/obligation; queue settlement
    SIM->>DB: Recheck no holds and known outcome
    SIM->>EVM: isExecutable (fresh read)
    EVM-->>SIM: true
    SIM->>DB: Unique obligation-key simulated receipt
    CW->>EVM: recordSimulatedSettlement receipt commitment
    CW->>DB: Audit tx status (may still be pending)
    IN-->>W: N18 simulated settlement receipt
    Note over DB,EVM: Human approval, chain confirmation and simulation stay separate
```

## Changes requested, dispute and uncertain delivery

```mermaid
sequenceDiagram
    actor V as Independent verifier
    participant API as FastAPI
    participant DB as Database/outbox
    participant JOB as Workers
    participant EVM as Local EVM
    participant IN as Inbox
    actor W as Worker / next user
    V->>API: A43 changes_requested OR A68 dispute
    API->>DB: Append exact-version outcome; hold dependencies if approved subject
    API-->>IN: N09 correction OR N19 hold
    W->>API: A27 new revision; new sealed evidence; A28 submit
    API->>DB: Preserve prior evidence/decision; checks rerun
    JOB->>EVM: Revoke old approved subject/decision before replacement (if needed)
    EVM--xJOB: RPC timeout / outcome unknown
    JOB->>DB: Mark unknown; no downstream settlement
    JOB->>EVM: Query eventId/commandDigest/nonce/receipt
    alt identical command canonical
        JOB->>DB: Reconcile success; continue dependency order
    else absent and positively safe to retry
        JOB->>EVM: Retry same command identity
    else conflict or orphan
        JOB->>DB: Hold/manual recovery; do not duplicate obligation
        JOB-->>IN: N17 operations and affected role
    end
```

These diagrams complement, rather than replace, the explicit permission/transaction rules. Successful inbox delivery is not a prerequisite for data correctness; the next user can always find their authorized queue directly.
