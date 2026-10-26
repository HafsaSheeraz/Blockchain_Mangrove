# 03 — Permission matrix and actor separation

**PROPOSED.** Shared session identity; users belong to an organization and project memberships. All checks apply in FastAPI and to lists, detail reads, exports, downloads, notifications and background job payloads. UI hiding is convenience, never security. Cross-organization requests return 404 for resources not visible to the caller; authenticated forbidden actions on visible resources return 403.

## Roles

`O` organization coordinator; `N` nursery operator/declarer; `C` nursery confirmer; `W` community worker; `V` independent field verifier; `P` payment authorizer; `A` project auditor; `S` system administrator. One fictional organization can contain multiple individuals/roles, but conflicts are evaluated on person ID, not on the currently selected role.

| Action | O | N | C | W | V | P | A | S |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Create organization project | Yes | — | — | — | — | — | — | Manage access only |
| Edit draft site/policy/task types; publish | Own org/project | — | — | — | Read policy | Read policy | Read | — |
| Assign workers/reviewers | Project | — | — | — | — | — | Read | Membership administration only |
| Read project overview | Scoped | Scoped | Scoped | Assigned subset | Assigned reviews | Payment subset | Scoped | Operational metadata only |
| Declare nursery stock | Read | Assigned nursery | Read | Allocation summary | Read needed supply | — | Redacted read | — |
| Confirm nursery supply | — | Never own | Assigned; conflict check | — | — | — | Read decision | — |
| Accept/start task | — | Own work if assigned W | — | Own assignment | — | — | — | — |
| Draft/submit work claim | Coordinator may assist draft; cannot impersonate worker submission | — | — | Own assignment | — | — | Redacted read | — |
| Record field observation | Read | — | — | Own observation if configured | Assigned inspector | — | Read | — |
| Approve/reject planting or survival | — | — | — | Never own | Assigned and independent | — | Read | — |
| Evaluate eligibility | Read | — | — | Own read | Read supporting review | Read | Read | System job; no admin override |
| Request/approve payment authority | Read | — | — | Own read | — | Assigned, independent | Read | — |
| Dispatch simulator | — | — | — | — | — | Request only | — | Dedicated service principal only |
| View settlement | Project totals | — | — | Own | — | Scoped | Redacted | Operational errors only |
| Original evidence/download | Subject/project need only | Own nursery | Assigned nursery | Own claim | Assigned review | Minimal approved receipt/summary | Redacted by default | No default content access |
| Mark notification read | Own inbox only | Own | Own | Own | Own | Own | Own | Own |
| View shared audit | Scoped | Relevant nursery | Relevant nursery | Own work redacted | Assigned | Payment scope | Scoped redacted | Operational scope |
| Grant membership / rotate demo signers | — | — | — | — | — | — | Read grants | Yes, audited; no retrospective identity rewriting |

No role may edit a submitted claim/evidence/policy/decision. Draft assistance records `prepared_by`; the assigned worker must submit as `submitted_by` unless an explicit future assisted-submission policy is approved. PB-1 does not add that bypass.

## Conflict rules (server invariants)

- Verifier person differs from claim submitter, assigned worker, nursery declarer/confirmer for that claim, and payee. The reviewer must not be the organization coordinator who configured/assigned this work. Block on assignment **and** decision submission because roles can change later.
- Supply confirmer differs from supply declarer and beneficiary worker for that allocation; confirmation assignment lists the relevant nursery/project.
- Payment authorizer differs from payee, claim submitter and field verifier for any prerequisite; organization coordinator cannot authorize an obligation they submitted as worker. PB-1 fixture uses a fully separate finance person.
- A role switch is not a new identity. Separate accounts controlled by the same actual human are not proven independent by software; demo explicitly uses fictional people.
- Project suspension, deactivated account, revoked role, expired session or superseded target blocks new approval. Already-recorded decisions remain historical and may trigger a dispute review; role revocation alone does not silently rewrite them.
- A verifier cannot reassign a review to themselves; coordinator assignment rejects conflicts. A system admin can manage membership but receives no implicit content/decision authority.

## On-chain identity and permissions

Each seeded fictional actor has one unique local-EVM address and actor commitment; bind it to User once per deployment. FastAPI selects the caller's bound signer for authorized chain commands; a generic publisher key cannot impersonate a verifier in contract storage. Signer keys remain in local backend secret configuration, never the SPA or DB. Document 06 defines project-scoped role bits, immutable actor binding and guards.

This is a **custodial demo**: the backend can access the local actor keys. Distinct on-chain addresses enforce address separation and transaction attribution, not independent real-world key custody or real identity. A future noncustodial wallet UX would change the threat model and is outside PB-1.

Admin can grant/revoke roles and pause projects but cannot bypass milestone guards in the authorization function. A powerful admin could still grant roles to colluding actors; all grants are events and this governance trust remains disclosed. DB outbox workers must recheck account/role/scope before signing and settlement workers must recheck holds before execution.

## Session and request requirements

Proposed same-origin HttpOnly session cookie, Secure outside local HTTP, SameSite=Lax, opaque token stored as digest with expiry/revocation. Bootstrap session endpoint issues a CSRF token; require CSRF + Origin validation for every authenticated mutation including logout. Login uses an anonymous CSRF bootstrap and rate limiting; no public account registration. Return generic login failure, rotate session on login, and audit login/membership changes without passwords/tokens.

Reject IDs from client that assert actor identity; derive actor from session. Query filters may narrow authorization, never widen it. Evidence download URLs expire quickly and cannot be used to access another object's version. Outbox/notification recipients are computed from current scoped membership and event context, not accepted from caller-supplied recipient arrays.

Acceptance tests: SEC-01 through SEC-08 in [testing](14-testing-and-operations.md). Include every matrix denial, double-role self-approval, forged user ID, cross-project FK injection, private download and revoked-role queued signer execution.
