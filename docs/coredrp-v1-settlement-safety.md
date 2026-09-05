# CoreDRP Mining Settlement Safety Registry — Draft 0.6 Freeze Completion

**Status:** normative Mining Profile 1.1 / Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md` and is authoritative for payout/completeness/pruning semantics that depend on settlement windows. It complements the contiguous scalar `PayoutSafeThrough(scope)` with an explicit settlement-specific predicate so historical waived uncertainty is never silently hidden by a scalar frontier.

## 1. Definitions

For scope `Q`, settlement identifier `K`, and exact evidence interval `[A,B]` (inclusive millisecond boundaries after scheme-specific conversion), define:

`SettlementSafe(Q,K,A,B)`

as a durable receiver-side proof that every relay-dependent event which can affect settlement `K` lies within a time/range whose completeness requirements are satisfied and whose required evidence has not been invalidated or pruned.

`PayoutSafeThrough(Q)` remains the greatest **contiguous** millisecond boundary `T` such that every payout-relevant point up to `T` is PayoutSafe under the applicable temporal policy.

A `RESOLVED_WAIVED` hole is not PayoutSafe. Therefore it permanently prevents the scalar frontier from crossing the hole unless that same uncertainty is later converted to `RESOLVED_RECONCILED` through verified evidence import. A waiver alone never changes this.

## 2. Cross-sender completeness boundary

For a settlement/block boundary `B` and required sender symmetric skew bound `S`, the receiver requires committed trusted checkpoint evidence through at least:

`B + 2*S`.

Checked arithmetic is mandatory. `B+2*S-1` is insufficient; `B+2*S` is sufficient only if every other membership, clock, gap, quarantine, anti-backdating, contract and policy gate is satisfied.

A sender-specific interval proof may substitute only when it proves a required boundary that is no less conservative than `B+2*S` for every physical offset compatible with the fresh observation. The exact interval evidence and derivation parameters are retained with the settlement proof.

## 3. Gap relevance

A gap/uncertainty record is relevant to settlement `K` iff its conservative affected time/range intersects `[A,B]` or the scheme-specific evidence dependency set for `K`.

- `UNRESOLVED` relevant gap => SettlementSafe is false.
- `RESOLVED_RECONCILED` relevant gap => does not block once verified import has restored all required effects/evidence.
- `RESOLVED_WAIVED` relevant gap => SettlementSafe is false unless an explicit settle-without-fence override names the same settlement; that override permits the settlement operationally but does **not** make SettlementSafe true and does not advance `PayoutSafeThrough`.
- A waived gap outside the settlement evidence interval is irrelevant to that settlement, even though it continues to cap the contiguous `PayoutSafeThrough` scalar.

This is the normative gap relevance horizon: relevance is determined by the exact settlement evidence interval/dependency set, not merely by historical existence.

## 4. Scheme matrix

| Scheme | Normal settlement safety requirement | Required evidence interval | Destructive deletion/prune rule |
|---|---|---|---|
| PPLNS | `SettlementSafe` REQUIRED | exact PPLNS share window plus required skew/checkpoint evidence | no farther than `min(window cutoff, SafePruneThrough)` and never remove evidence required by unsettled windows |
| PPLNSBF | `SettlementSafe` REQUIRED | exact PPLNSBF share/block-factor window plus required skew/checkpoint evidence | no farther than `min(window cutoff, SafePruneThrough)` |
| PROP | `SettlementSafe` REQUIRED | round start through block/round boundary plus required skew/checkpoint evidence | no farther than `min(round cutoff, SafePruneThrough)` |
| PPS | payout calculation is not remote-completeness fence gated | each accepted share's durable accounting/idempotency evidence | delete only after the PPS accounting effect is durable, no retry/idempotency/evidence record still depends on it, and SafePruneThrough permits deletion of shared proof material |
| CUSTODIAL_SOLO | payout itself is not remote-completeness fence gated | winning-share/block attribution evidence | winning share and block evidence retained until settlement finality plus SafePruneThrough; ordinary non-winning shares may follow configured SOLO retention only when no settlement/evidence dependency remains |
| DIRECT_SOLO | consensus submission is never recorder/completeness gated | locally persisted candidate/submission evidence | retain candidate/submission/settlement evidence through local finality and SafePruneThrough; recorder state never delays `submitblock` |

Unknown scheme value is invalid negotiation and MUST NOT fall back to another row.

## 5. SafePruneThrough

`SafePruneThrough(Q)` is monotonic but is not permission to destroy records whose specific settlement, gap, override, quarantine, retired-epoch import, policy reconciliation, producer high-water, or candidate evidence remains required.

For contiguous payout evidence, `SafePruneThrough(Q) <= PayoutSafeThrough(Q)`.

For a later settlement proven with `SettlementSafe` beyond an old waived hole, only evidence outside every live settlement dependency may be pruned. The existence of a settlement-specific proof does not raise the contiguous scalar frontier and does not authorize pruning the waived-hole audit record.

## 6. Settlement proof record

A durable `SettlementSafe` proof records at least:

- scope;
- settlement identifier;
- scheme and bound scheme-policy versions;
- exact evidence interval/dependency description;
- required sender set and membership-policy version used;
- per-sender checkpoint sequence/hash/time and effective skew requirement;
- clock-policy/evidence references;
- relevant gap/quarantine status snapshot;
- scope-contract digests;
- resulting boolean decision;
- receiver state version and durable timestamp.

The proof is immutable audit evidence. Re-evaluation under later policy does not rewrite the historical proof; a later correction creates a new reconciliation/audit record.

## 7. Overrides

`SETTLE_WITHOUT_FENCE_OVERRIDE` is operational authorization for one named settlement only. It records why the normal safety predicate was bypassed. It MUST NOT:

- set `SettlementSafe=true`;
- advance `PayoutSafeThrough`;
- convert a waived gap to reconciled;
- authorize unrelated settlements;
- remove required audit evidence.
