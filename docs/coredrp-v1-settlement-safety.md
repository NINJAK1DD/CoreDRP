# CoreDRP Mining Settlement Safety Registry — Draft 0.6 Profile Freeze

**Status:** normative Mining Profile 1.1 / Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md` and is authoritative for payout/completeness/pruning semantics that depend on settlement windows.

## 1. Safety origin and definitions

Every Mining scope has a durable `scope_safety_origin_unix_ms`, created with its first explicit temporal policy generation. No payout-safety claim exists before that origin.

Before that bootstrap generation commits, `PayoutSafeThrough(Q)` is undefined and MUST NOT be represented by an implementation-local numeric sentinel. The bootstrap transition in `coredrp-v1-temporal-policy.md` initializes the control-state value to exactly `scope_safety_origin_unix_ms - 1`.

That predecessor value represents an **empty proven interval** only. While `PayoutSafeThrough(Q) < scope_safety_origin_unix_ms`, the set `[scope_safety_origin_unix_ms, PayoutSafeThrough(Q)]` is empty and no time is payout-safe by virtue of the scalar. It MUST NOT be interpreted as proving any millisecond before the origin. Once the frontier reaches the origin, it takes its ordinary contiguous meaning.

For scope `Q`, settlement identifier `K`, and exact evidence interval `[A,B]` (inclusive millisecond boundaries after scheme-specific conversion), define:

`SettlementSafe(Q,K,A,B)`

as a durable receiver-side proof that every relay-dependent event which can affect settlement `K` lies within a time/range whose completeness requirements are satisfied and whose required evidence has not been invalidated or pruned.

After bootstrap, `PayoutSafeThrough(Q)` is the greatest contiguous millisecond boundary `T >= scope_safety_origin_unix_ms` such that every payout-relevant point in `[scope_safety_origin_unix_ms,T]` is PayoutSafe under the applicable temporal policy. The one allowed value below the origin is the bootstrap predecessor marker described above.

A `RESOLVED_WAIVED` hole is not PayoutSafe. Therefore it prevents the scalar frontier from crossing the hole unless that uncertainty is later converted to `RESOLVED_RECONCILED` through verified evidence import. A waiver alone never changes this.

## 2. Cross-sender completeness boundary

For a settlement/block boundary `B` and required sender symmetric skew bound `S`, the receiver requires committed trusted checkpoint evidence through at least:

`B + 2*S`.

Checked arithmetic is mandatory. `B+2*S-1` is insufficient; `B+2*S` is sufficient only if every other membership, clock, gap, quarantine, anti-backdating, contract and policy gate is satisfied.

A sender-specific interval proof may substitute only when it proves a required boundary that is no less conservative than `B+2S` for every physical offset compatible with the fresh observation. The exact interval evidence and derivation parameters are retained with the settlement proof.

## 3. Gap and quarantine relevance

A gap, temporal-policy uncertainty, or payout-significant quarantine is relevant to settlement `K` iff its conservative affected time/range intersects `[A,B]` or the scheme-specific evidence dependency set for `K`.

- `UNRESOLVED` relevant uncertainty => `SettlementSafe` is false.
- `RESOLVED_RECONCILED` => does not block once verified import/correction has restored all required effects/evidence.
- `RESOLVED_WAIVED` => `SettlementSafe` remains false for an intersecting settlement. A named settle-without-fence override may permit the settlement operationally but does not make it safe and does not advance `PayoutSafeThrough`.
- A waived uncertainty outside the settlement evidence interval is irrelevant to that settlement, even though it continues to cap the contiguous scalar.

Financial quarantine uses the exact lifecycle in `coredrp-v1-quarantine-safety.md`.

## 4. Scheme matrix

| Scheme | Normal settlement safety requirement | Required evidence interval | Destructive deletion/prune rule |
|---|---|---|---|
| PPLNS | `SettlementSafe` REQUIRED | exact share window derived from bound settlement-scheme policy plus skew/checkpoint evidence | `SettlementPruneSafe` only; never remove evidence required by live/unsettled windows |
| PPLNSBF | `SettlementSafe` REQUIRED | exact factor/block-finder dependency set derived from bound settlement-scheme policy | `SettlementPruneSafe` only |
| PROP | `SettlementSafe` REQUIRED | round start through block/round boundary plus required skew/checkpoint evidence | `SettlementPruneSafe` only |
| PPS | payout calculation is not remote-completeness fence gated | each accepted share's durable accounting/idempotency evidence | delete only after PPS effect durable and `SettlementPruneSafe`/idempotency rules permit |
| CUSTODIAL_SOLO | payout itself is not remote-completeness fence gated | winning-share/block attribution evidence | winning evidence retained through finality; unrelated evidence may prune via `SettlementPruneSafe` |
| DIRECT_SOLO | consensus submission is never recorder/completeness gated | locally persisted candidate/submission evidence | retain candidate/submission/settlement evidence through local finality; recorder never delays `submitblock` |

Unknown scheme is invalid negotiation.

## 5. Contiguous SafePruneThrough and settlement-specific pruning

`SafePruneThrough(Q)` is the monotonic contiguous destructive-prune frontier and MUST satisfy:

`SafePruneThrough(Q) <= PayoutSafeThrough(Q)`.

During bootstrap it may equal the same predecessor marker but MUST NOT advance until its normal proof predicates hold.

A waived hole can permanently cap both contiguous scalars. That does **not** require unbounded retention of every unrelated later record.

Define `SettlementPruneSafe(Q, record_or_interval R)` as true only when all are true:

1. every settlement whose dependency set includes `R` is final and has durable `SettlementSafe` proof or an explicit retention-preserving operational override;
2. `R` does not intersect any `UNRESOLVED` or `RESOLVED_WAIVED` gap/quarantine/policy-audit range that itself must be retained;
3. no live producer idempotency mapping, retired-epoch import, candidate-state proof, reconciliation, or other incorporated registry requires `R`;
4. every proof that depended on `R` contains sufficient immutable digest/summary evidence to survive destruction of the underlying ordinary record;
5. the scheme-specific retention rule permits destruction.

Records later than a permanently capped `SafePruneThrough` MAY therefore be destroyed when `SettlementPruneSafe` is true. The waived-hole/gap/quarantine audit record itself is not removed by this predicate.

Implementations MUST NOT infer `SettlementPruneSafe` merely from event age or from one settlement proof if another live dependency exists.

## 6. Settlement proof record

A durable `SettlementSafe` proof records at least:

- scope and `scope_safety_origin_unix_ms`;
- settlement identifier;
- scheme and `settlement_scheme_policy_digest32`;
- exact evidence interval/dependency description;
- required sender set and membership-policy generation used;
- per-sender checkpoint sequence/hash/time and effective skew requirement;
- clock-policy/evidence references;
- relevant gap/quarantine/policy status snapshot;
- Mining and Miningcore scope-contract digests;
- resulting boolean decision;
- receiver state version and durable timestamp.

The proof is immutable audit evidence. Re-evaluation under later policy creates a new reconciliation/audit record.

## 7. Overrides

`SETTLE_WITHOUT_FENCE_OVERRIDE` is operational authorization for one named settlement only. It MUST NOT:

- set `SettlementSafe=true`;
- advance `PayoutSafeThrough` or `SafePruneThrough`;
- convert waived uncertainty to reconciled;
- authorize unrelated settlements;
- remove required audit evidence.

An override MAY participate in `SettlementPruneSafe` only after the named settlement is final and only for ordinary evidence whose audit dependency is represented durably elsewhere; it never permits deletion of the waived/unresolved audit record that justified the override.
