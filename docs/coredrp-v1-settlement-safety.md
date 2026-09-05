# CoreDRP Mining Settlement Safety Registry — Draft 0.6 Profile Freeze

**Status:** normative Mining Profile 1.1 / Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md` and is authoritative for payout/completeness/pruning semantics that depend on settlement windows.

## 1. Safety origin and definitions

Every Mining scope has a durable `scope_safety_origin_unix_ms`, created with its first explicit temporal policy generation. No payout-safety claim exists before that origin.

Before that bootstrap generation commits, `PayoutSafeThrough(Q)` is undefined and MUST NOT be represented by an implementation-local numeric sentinel. The bootstrap transition initializes the control-state value to exactly `scope_safety_origin_unix_ms - 1`.

That predecessor value represents an **empty proven interval** only. It MUST NOT be interpreted as proving any millisecond before the origin.

For scope `Q`, settlement identifier `K`, and exact evidence interval `[A,B]`, define `SettlementSafe(Q,K,A,B)` as a durable receiver-side proof that every relay-dependent event which can affect settlement `K` lies within a time/range whose completeness requirements are satisfied and whose required evidence has not been invalidated or pruned.

A `RESOLVED_WAIVED` hole is not PayoutSafe. Therefore it prevents the scalar frontier from crossing the hole unless that uncertainty is later converted to `RESOLVED_RECONCILED` through verified evidence import.

## 2. Cross-sender completeness boundary

For a settlement/block boundary `B` and required sender symmetric skew bound `S`, the receiver requires committed trusted checkpoint evidence through at least `B + 2*S` using checked arithmetic.

`B+2*S-1` is insufficient; `B+2*S` is sufficient only if every other membership, clock, gap, quarantine, anti-backdating, contract and policy gate is satisfied.

## 3. Gap and quarantine relevance

A gap, temporal-policy uncertainty, or payout-significant quarantine is relevant to settlement `K` iff its conservative affected time/range intersects `[A,B]` or the scheme-specific evidence dependency set for `K`.

- `UNRESOLVED` relevant uncertainty => `SettlementSafe` is false.
- `RESOLVED_RECONCILED` => does not block once verified import/correction has restored all required effects/evidence.
- `RESOLVED_WAIVED` => `SettlementSafe` remains false for an intersecting settlement.
- A waived uncertainty outside the settlement evidence interval is irrelevant to that settlement, even though it continues to cap the contiguous scalar.

Financial quarantine uses the exact lifecycle in `coredrp-v1-quarantine-safety.md`.

## 4. Scheme matrix

| Scheme | Normal settlement safety requirement | Required evidence interval | Destructive deletion/prune rule |
|---|---|---|---|
| PPLNS | `SettlementSafe` REQUIRED | exact share window derived from bound factor + adjustment policy + skew/checkpoint evidence | `SettlementPruneSafe` only |
| PPLNSBF | `SettlementSafe` REQUIRED | exact factor/block-finder dependency set derived from bound policy + adjusted difficulties | `SettlementPruneSafe` only |
| PROP | `SettlementSafe` REQUIRED | round start through block/round boundary plus required skew/checkpoint evidence | `SettlementPruneSafe` only |
| PPS | payout calculation is not remote-completeness fence gated | each accepted share's durable accounting/idempotency evidence | delete only after PPS effect durable and `SettlementPruneSafe`/idempotency rules permit |
| CUSTODIAL_SOLO | payout itself is not remote-completeness fence gated | winning-share/block attribution evidence | winning evidence retained through finality; unrelated evidence may prune via `SettlementPruneSafe` |
| DIRECT_SOLO | consensus submission is never recorder/completeness gated | locally persisted candidate/submission evidence | retain candidate/submission/settlement evidence through local finality |

Unknown scheme is invalid negotiation.

## 5. Contiguous SafePruneThrough and settlement-specific pruning

`SafePruneThrough(Q)` is the monotonic contiguous destructive-prune frontier and MUST satisfy `SafePruneThrough(Q) <= PayoutSafeThrough(Q)`.

A waived hole can permanently cap both contiguous scalars. That does **not** require unbounded retention of every unrelated later record.

Define `SettlementPruneSafe(Q, record_or_interval R)` as true only when all are true:

1. every settlement whose dependency set includes `R` is final and has durable `SettlementSafe` proof or an explicit retention-preserving operational override;
2. `R` does not intersect any `UNRESOLVED` or `RESOLVED_WAIVED` gap/quarantine/policy-audit range that itself must be retained;
3. no live producer idempotency mapping, retired-epoch import, candidate-state proof, reconciliation, or other incorporated registry requires `R`;
4. every proof that depended on `R` contains a valid `SettlementEvidenceSummaryV1` sufficient to survive destruction of the ordinary records;
5. the scheme-specific retention rule permits destruction.

Records later than a permanently capped `SafePruneThrough` MAY therefore be destroyed when `SettlementPruneSafe` is true. The waived-hole/gap/quarantine audit record itself is not removed by this predicate.

## 6. SettlementEvidenceSummaryV1

Before ordinary records needed by a final settlement are destructively removed, the receiver MUST persist an immutable versioned summary with this canonical binary grammar:

`uint16_be(1)`
`|| uint16_be(scope_len) || scope`
`|| uint16_be(settlement_id_len) || settlement_id_bytes`
`|| uint8(payout_scheme)`
`|| settlement_scheme_policy_digest32`
`|| share_difficulty_adjustment_policy_digest32`
`|| mining_scope_contract_digest32`
`|| miningcore_scope_contract_digest32`
`|| int64_be(evidence_from_unix_ms)`
`|| int64_be(evidence_through_unix_ms)`
`|| uint32_be(participant_effect_count)`
`|| participant_effects_digest32`
`|| uint32_be(required_sender_count)`
`|| required_sender_set_digest32`
`|| uint32_be(checkpoint_evidence_count)`
`|| checkpoint_evidence_digest32`
`|| gap_quarantine_policy_snapshot_digest32`
`|| receiver_state_version_uint64`
`|| int64_be(proved_at_unix_ms)`.

Every digest field is exactly 32 bytes. Counts are the exact number of canonical items represented by the corresponding digest. Scope and settlement ID lengths are bounded by their profile/application registries before encoding.

Canonical digest inputs:

- `participant_effects_digest32 = SHA256(uint32_be(count) || repeated(uint32_be(item_len)||item))`, where items are the exact scheme-specific canonical participant/value effect records sorted by the scheme's canonical accounting order;
- `required_sender_set_digest32 = SHA256(uint32_be(count) || repeated(sender_uuid16))`, sender UUIDs sorted lexicographically as RFC 9562 bytes;
- `checkpoint_evidence_digest32 = SHA256(uint32_be(count) || repeated(sender_uuid16 || uint64_be(sequence) || chain_hash32 || int64_be(complete_through_unix_ms) || uint32_be(effective_skew_ms)))`, sorted by sender UUID bytes;
- `gap_quarantine_policy_snapshot_digest32` is the SHA-256 of a versioned, length-delimited canonical list of every relevant gap/quarantine/policy state record identity/status referenced by the proof, sorted by `(kind, raw identity bytes)`.

No database row serialization, JSON, locale formatting or unordered map iteration is allowed.

### 6.1 Scheme-specific participant effect records

- PPLNS/PPLNSBF/PROP: each canonical item contains recipient/accounting identity bytes plus exact settled amount in `Decimal38Scale24` canonical ASCII and the share/effect identity digest used by the settlement.
- PPS: each item contains accounting ID UUID16 plus canonical liability amount and final settlement effect digest.
- CUSTODIAL_SOLO: item contains winning accounting/share identity plus final payout amount/effect digest.
- DIRECT_SOLO: item contains candidate UUID16 plus final submission/settlement state digest.

An implementation that cannot produce this summary MUST retain the underlying ordinary records. Age alone never makes an incomplete summary sufficient.

## 7. Settlement proof record

A durable `SettlementSafe` proof records at least:

- scope and `scope_safety_origin_unix_ms`;
- settlement identifier;
- scheme, `settlement_scheme_policy_digest32`, and embedded `share_difficulty_adjustment_policy_digest32`;
- exact evidence interval/dependency description;
- required sender set and membership-policy generation used;
- per-sender checkpoint sequence/hash/time and effective skew requirement;
- clock-policy/evidence references;
- relevant gap/quarantine/policy status snapshot;
- Mining and Miningcore scope-contract digests;
- resulting boolean decision;
- receiver state version and durable timestamp.

The proof is immutable audit evidence. Re-evaluation under later policy creates a new reconciliation/audit record.

## 8. Overrides

`SETTLE_WITHOUT_FENCE_OVERRIDE` is operational authorization for one named settlement only. It MUST NOT set `SettlementSafe=true`, advance `PayoutSafeThrough`/`SafePruneThrough`, convert waived uncertainty to reconciled, authorize unrelated settlements, or remove required audit evidence.

An override MAY participate in `SettlementPruneSafe` only after the named settlement is final and only for ordinary evidence whose audit dependency is represented durably by `SettlementEvidenceSummaryV1`; it never permits deletion of the waived/unresolved audit record that justified the override.
