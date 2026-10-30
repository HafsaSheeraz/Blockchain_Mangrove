# 11 — Locked synthetic demonstration and formula verification

All operational records/assets/rates/agreements/settlements are **PROPOSED fictional fixtures**. Reuse [PB-1 actor/site/evidence inventory and presenter script](../playbook/15-synthetic-data-and-demo.md), amended here. No seed/assets/contract transactions are created by PB-2.

## Fixed scenario

Fictional organization Coastal Learning Cooperative; project Learning Creek Plantation 01, codeCLC-PLANT-001; synthetic geometry remains PB-1 rectangle with explicit no-tenure/no-suitability/no-DBC-boundary claim. Species label Avicennia marina is fictional record metadata, not field verified. Same separate coordinator, No per at or, C confirmer, Wworker, V planting, V followup, P finance, A auditor, Sadmin actors; support worker for smaller flows. Unique personID/address per deployment; no signer key committed.

One main task assigned 1,000 seedlings; declare 1,200, independently confirm 1,100, allocate 1,000; primary planting date 2026-02-01 and independently accepted Q1,000. M3 due 2026-05-01, earliest visit May 1, graceendMay 15; M6 due 2026-08-01, earliest Aug 1, graceendAug 15. Reminders earlier are notifications only, not valid surveys. This explicitly overrides PB-1's ±14 early visit proposal.

M3 census live 900/dead 70/missing 30, threshold 8000 bps; M6 live 820/dead 130/missing 50, threshold 7500 bps. Each census denominator original accepted Q=1000; independent approved report+correct parent required. Both mandatory. Primary component final_reward only; completion/survival components disabled in primary, available in other policies.

```text
eligible = current independent planting approval
       AND current independent M3 approval with liveM3*10000 >= Q*8000
       AND current independent M6 approval with liveM6*10000 >= Q*7500
       AND no missing/failed/disputed/revoked/stale mandatory dependency
amount_minor = min(Q*1000,1000000) only when eligible
amount_PKR = amount_minor / 100
```

Human authorization and canonical blockchain authority are later independent steps; eligibility alone cannot settle. This final survival-linked component is not a rule delaying all wages. Accepted quantity drives amount; neither live counts nor carbon numbers are payment base.

## Required calculation/negative fixture vectors

| Case | AcceptedQ / M3 / M6 / dependencies | Expected result |
| --- | --- | --- |
| Main |1000 /900 /820, all approved, current, noholds |Eligible,1000000 minor=PKR10000; not 820000 minor. |
| Exact boundaries |1000 /800 /750 |Eligible at inclusive 80%/75%, PKR10000. |
| M3 low |1000 /799 /820 |Ineligible, mandatoryM3 failed, no payable amount. |
| M6 low |1000 /900 /749 |Ineligible, mandatoryM6 failed, no payable amount. |
| Partial accepted planting |900 /720 /675, original cohort 900, all approved |Eligible,900000 minor=PKR9000, not 675000. Separate fixture, not editing main. |
| Missing either |1000 /missing /820 or 1000/900/missing |Pending requirements; authority API/direct RPC blocked. |
| Submitted not approved |1000 /900 pending review /820 |Pending requirements; numbers alone are not approval. |
| Disputed/revoked |Main measurements, but any mandatory decision held/revoked |Held/revoked, no final authority/dispatch. |
| Replaced parent |D1 Q1000 surveys; D1 revoked, newD2 Q1000 |OldsurveyscannotqualifyD2; new parent-linked reports/review required. |
| Wrong primary constants |Attempt rate 900 ormask 1 orM6 threshold 7000 |Primary profile validation/contract revert, not new primary policy. |
| Separate completion component |Configured policy only mask 1, valid work |ItsownobligationcanpaywithoutM3/M6; does not pay primary final early. |
| Fractional other task |Configured 1.25 hours, scale 100, rate 500 minor/hour |625 minor after valid completion; no integer seedling coercion. |

Counts include explicit dead/missing rows summing Q. Replacement seedlings form a new cohort/task, not silent original survival boost. For partial acceptance, inventory release only if report explicitly identifies unplanted returned stock; consumed-but-unaccepted stock remains consumed and is not recycled as available.

## Fixture generation controls

Namespace `mangrove-pb2-demo`; retain PB-1 human-friendly names but use new manifest version with deterministic namespace/entity UUIDs. Actor/account bootstrap may directly seed identity only; completed business state must pass normal services/guards, not SQL approved flags. Runtime seed command planned `python -m scripts.seed_demo --namespace mangrove-pb2-demo` from backend; actual CLI implemented WP17, not available yet.

Generate watermarked FICTIONAL DEMO agreement/register/nursery/plot/census/reviewer report assets; no real person/ID/bank data. Server calculates actual bytes/hashes. Synthetic occurred dates historical; recorded_at/decision submission/receipt block times actual run. Never backdate chain or replace failed live action with fixture success.

If EE context is unavailable, store fixture mode insufficient/unavailable context and perform real software field-inspection workflow against synthetic observations. Never invent live satellite carbon output or convert pixel count to seedlings. Optional persisted real context requires provenance/access; still not physical work proof.

## Presenter acceptance checklist

1. Show fictional case/custody/simulated payment disclosures and existing One analysis boundary.
2. O creates project/site/rules, primary read-onlyD01 constants, publishes; show immutable IDs/actual chain pending then receipts.
3. O assigns plantation before stock; W accepts/starts in own session; shared project/assignment IDs.
4. N declares 1200, C confirms 1100; show no planting approval and available 1100.
5. W uploads/seals/submits 1000; show private evidence hash/version, checks, reserved 1000/available 100; N08 handoff.
6. IndependentVrecordsfieldvisitandaccepts 1000; show exact claim+report+decision, parent Completion key; final eligibility still pending M3/M6.
7. W/collector records M3 historical census; context insufficient route; V followup independently approves 900/1000; final still pending M6.
8. RepeatM6 at 820/1000; showboththresholdpassesandacceptedQbasedPKR10000; VandPdistinct.
9. P authorizes exact evaluation; show human approved versus chain pending/local confirmed; direct RPC negative case with missing stage or wrong amount reverts in isolated variant.
10. P explicitly dispatches simulation; WseesoneSIMULATEDreceipt, chain audit pending/confirmed separate; no actual transfer.
11. A views timeline/compares canonical digests/exports safe report; show correction version history and one shared inbox.
12. Demonstrate isolated failures:missing evidence/correction, wrongC/selfV, quantity race, missingM3/M6, lowM6, chain outage/unknown simulator/dispute, duplicate authority. Retry does not duplicate economic receipt.

Four smaller typed tasks retain PB-1 collection/nursery/maintenance/monitoring forms with same claims/evidence/review/policy engine. Monitoring work acceptance doesnot itself approve primary survival. Their completion-only rewards are separate from primary presenter total.

Reset/restore only explicit isolated namespace+deployment, target verified; preserveDB/object manifest/signer binding metadata/economic receipts where replaying same economic namespace. Fresh chain uses new generation, never old receipts as current proof. Final run manifest records revision, runtime versions, policy/digests/receipt IDs/test results/limits without secrets.
