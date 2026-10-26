# 15 — Synthetic data plan and final demonstration

**PROPOSED fixtures/presenter script only. No seeds, images, PDF contracts or transactions are created by this playbook.** All names, quantities, rates, agreements, inspection observations and settlement receipts below are invented university-demo data. Delta Blue Carbon is public contextual inspiration only; no affiliation, private operations or real project boundary is claimed.

## Dataset identity and provenance

Namespace `mangrove-pb1-demo`, fictional organization **Coastal Learning Cooperative**, project **Learning Creek Plantation 01**, code `CLC-PLANT-001`. One connected project hosts the full plantation slice plus small related collection/nursery/maintenance/monitoring tasks. Use deterministic UUIDs derived from namespace/entity code during later seed implementation; chain entity keys depend additionally on actual deployment identity. Do not hardcode fake receipt hashes as if mined.

| Fictional account label | Role / deliberate separation |
| --- | --- |
| `coordinator.demo` / Coordinator A | Organization coordinator, project/site/rules/tasks; no field or payment approval. |
| `nursery.operator.demo` / Nursery Operator B | Declares seedling supply. |
| `nursery.confirmer.demo` / Nursery Confirmer C | Independently counts/confirms supply; not worker or field verifier. |
| `worker.demo` / Community Worker D | Plantation assigned worker and M3/M6 observation collector. |
| `field.verifier.demo` / Field Verifier E | Independently inspects/accepts planting; not claim author or payee. |
| `followup.verifier.demo` / Follow-up Verifier F | Independently inspects/reviews M3/M6; cannot authorize payment. |
| `finance.demo` / Payment Authorizer G | Approves fictional reward after eligibility; not any subject author/reviewer/payee. |
| `auditor.demo` / Auditor H | Scoped redacted audit/integrity view; no workflow changes. |
| `support.worker.demo` / Community Worker I | Smaller task-type examples, separately reviewed by E/F. |
| `system.admin.demo` / Administrator J | Membership/ops only; no business approval bypass. |

Each account gets unique disposable local signer binding where it needs transactions. Passwords generated during isolated seed setup and shown only in local run instructions, never committed in these docs. Signer keys remain local development secrets; they have no mainnet assets. No actual person photos, CNIC/national ID, contact list, bank data or real contracts.

## Synthetic site and agreement

Suggested hand-authored Polygon: `[[[67.300,24.100],[67.304,24.100],[67.304,24.103],[67.300,24.103],[67.300,24.100]]]` in WGS84. Label **synthetic educational extent; restoration suitability/land rights unverified**. Area computed with PostGIS at seed time, not hard-coded or attributed to DBC. Use a separate polygon-with-hole fixture to test preservation; main scenario may use simple exterior.

Agreement code `DEMO-AGREEMENT-001`, title **Fictional plantation and stewardship agreement**, immutable policy version1. Document clauses name accepted quantity, mandatory independent field acceptance, original cohort, census method, calendar-month due dates, thresholds, final component/cap, correction/dispute policy and simulated-only settlement. It is not a real legal contract or DBC agreement.

## Primary fixture values (D01 approval proposal)

| Item | Synthetic value |
| --- | --- |
| Task / assigned cohort | 1,000 seedlings, plantation type; fictional species label Avicennia marina, not a field-verified species claim. |
| Nursery declaration/confirmation | Declare 1,200; observe and confirm 1,100; allocate 1,000 to primary claim, leave 100 available. Supply approval alone earns no plantation reward. |
| Planting date / accepted count | 2026-02-01; independently accepted 1,000. |
| 3-month checkpoint | Due 2026-05-01; visit 2026-05-01; live900/dead70/missing30; survival90%; minimum80%. |
| 6-month checkpoint | Due 2026-08-01; visit 2026-08-01; live820/dead130/missing50; survival82%; minimum75%. |
| Required final component | `final_reward`, PLANTING+M3+M6 mask7. Completion-payment and separate survival-incentive components disabled for this primary agreement. |
| Rate/cap/currency | 1,000 minor PKR = fictional PKR10 per accepted seedling; cap1,000,000 minor PKR; accepted1000 × rate1000 = **1,000,000 minor PKR = PKR10,000**. No deduction/reward formula based on carbon estimates. |
| Window | ±14 days on field visit, late reason + reviewer disposition outside window. Both fixture visits on due date. |
| Settlement | One durable simulator receipt, no funds/asset transfer; record server/chain timestamps actually observed during demo. |

Planting/field-visit dates are **historical synthetic observations**. Record creation, decision submission and blockchain receipt occur at the actual rehearsal time. Do not backdate block timestamps or claim historical chain inclusion. Milestone not-before values are the policy's earliest valid observation date (due minus14 days under the proposed window), while due dates remain May1/Aug1. Date fields are labeled fictional occurrence versus current record/anchor time, so six months requires no hidden clock acceleration.

## Evidence/fixture inventory

Later seed generator creates watermarked **FICTIONAL DEMO** sample assets: synthetic agreement PDF, nursery count sheet, drawn nursery overview, planting register/plot/overview illustrations, verifier planting report, M3/M6 census sheets/plot illustrations and independent follow-up reports. No downloaded identifiable community photographs. Each object has new server-computed bytes/hash/version; canonical fixture manifest lists purpose, generator version and provenance.

Environmental fixture may use an approved stored context snapshot only if available/provenance documented; otherwise use a **fixture-mode unavailable/insufficient-context example** and complete field inspection. Do not invent live EE carbon numbers. Existing real scientific output, if obtained later with authorized access, is labeled live/persisted context and kept separate from synthetic field data.

Negative variants: corrupt bytes after validation (isolated object copy), reused photo hash, missing required planting register, wrong-project stock, 1,200 reservation against1,100 confirmed, wrong verifier, M3 missing, M6 live700/dead250/missing50 (70%, below75%), revised evidence set, chain RPC unavailable, unauthorized direct RPC authorization, unknown simulator response, disputed accepted claim. Never damage the sole success fixture to demonstrate failure; use isolated variant records/namespaces with explicit links.

## Smaller task-type demonstrations

| Type | Small flow using same engine |
| --- | --- |
| Propagule collection | Worker I collects fictional100 propagules, receipt/photo/register, E accepts100, completion-only component; separate supply type, not automatically planting stock. |
| Nursery work | Worker I logs fictional4 hours tending batch, supervisor log/photo, F accepts work; no automatic confirmation of supply by work acceptance. |
| Protection/maintenance | Fictional2-hour debris clearing log/before-after evidence, E accepts; no supply/M3/M6 unless that task's policy explicitly requires it. |
| Field monitoring | Worker I records a fictional plot census/report, F accepts monitoring work. That accepted task does not itself approve the primary plantation's survival milestone; primary subject still independently reviewed. |

Example completion-only rates may be small fixture values (e.g. collection100 minor PKR/unit, hours500 minor PKR/hour) under separate fictional component policies, not paid in the main presenter total. Architecture exercises independent components without double-counting primary final reward. No smaller task bypasses evidence, exact-version review or conflicts.

## Presenter walkthrough (after future implementation)

| Step / actor | Screen/action | Observable evidence and next handoff |
| --- | --- | --- |
| 0 / presenter | Show fictional-case disclosure and existing One `/analysis`. | Existing GIS context/scientific limitations; no partnership/real payment claim. |
| 1 / O | T01 create, T02 site, T03 rules, S04 publish. | One project/site/policy versions; PLANTING/M3/M6 required; chain pending then actual local registration/rules events; N01. |
| 2 / O → W | T04 publish plantation/assign; W01/W02 accept/start. | Same assignment/policy, N02/N03; supply pending allowed here. |
| 3 / N → C | T05/T06 declare1200, distinct C confirms1100. | Supply confirmed distinct from planting; inventory1100, no approved planting/reward; N04/N05. |
| 4 / W | W03 upload/seal/submit1000. | Exact evidence+claim revision, reserve1000, real server hashes/check statuses; N06→N08. |
| 5 / V E | T09/T10 record independent field visit/approve1000. | No self-approval, accepted planting decision digest/field report; chain approveMilestone Completion; M3/M6 scheduled, eligibility still pending. |
| 6 / W → V F | S06/W04 M3 observation with insufficient satellite context; field report and T10 approve. | Due May1, census90%, independent field decision/chain stage; final still blocked by M6; N10/N12/N13. |
| 7 / W → V F | W04 M6 observation/report; T10 approve. | Due Aug1, census82%, exact second follow-up decision; eligibility becomes eligible once current requirements satisfied; N14. |
| 8 / P | W05/W06 verify formula/requirements then Authorize. | Human approved_pending_chain vs chain confirmed distinct; premature direct RPC call shown to revert in negative variant; actual RewardAuthorized event. |
| 9 / P → W | W07 acknowledge simulation/dispatch; W08 receipt. | One PKR10,000 fictional simulated receipt, no transfer; settlement chain-audit can lag; N18 worker notification. |
| 10 / A | S08/S05 inspect exact versions/digests and chain receipt. | Recompute evidence/set/decision commitment, actual local tx/deployment/canonical status, same shared records across modules. |
| 11 / presenter | FLOW-02/03/04 failure variant. | Changes requested needs new version; missing/70%-M6 blocks reward; chain outage/unknown settlement holds, retry no duplicate. |

Start with editable/semi-complete fixture set for live clicks, and a separate completed reference set for recovery if a service is unavailable. Present fixtures as such; never replace a failed live action with a fake success screen. Presenter can inspect queued operations/inbox to show eventual consistency.

## Seed/reset and reproducibility

Later seed code is idempotent by namespace/entity code and fails if expected existing schema/digest differs. It creates actual evidence bytes and mines actual local transactions, captures outputs and then verifies them. Completed demo records may be pre-seeded through the same services/guards, never by bypassing approved decisions in DB inserts.

Reset only isolated namespace/object prefix and recorded local deployment; verify target identity and preserve a run manifest if needed. A chain reset requires new deployment-scoped keys/receipts. Tests use separate DB/schema/object prefix; do not reuse user `.env` secrets or delete unrelated workspace files. No reset is executed by this documentation task.
