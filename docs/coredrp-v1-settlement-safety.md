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
`|| uint32_be(uncertainty_record_count)`
`|| uncertainty_snapshot_digest32`
`|| uint64_be(receiver_state_version)`
`|| int64_be(proved_at_unix_ms)`.

Every digest field is exactly 32 bytes. Counts are the exact number of canonical items represented by the corresponding digest. Scope and settlement ID lengths are validated before encoding. `evidence_from_unix_ms <= evidence_through_unix_ms` is required. No database row serialization, JSON, locale formatting, protobuf serialization, unordered map iteration or implementation-defined identity encoding is permitted.

### 6.1 ParticipantEffectV1

Each participant effect begins:

`uint16_be(1) || uint8(effect_kind)`.

`effect_kind` allocation:

- `1 = WINDOW_ACCOUNTING_EFFECT` for PPLNS/PPLNSBF/PROP;
- `2 = PPS_LIABILITY_EFFECT`;
- `3 = CUSTODIAL_SOLO_EFFECT`;
- `4 = DIRECT_SOLO_EFFECT`.

For kinds 1–3, the complete record is:

`uint16_be(1)`
`|| uint8(effect_kind)`
`|| accounting_id_uuid16`
`|| uint16_be(miner_len) || miner_utf8`
`|| uint16_be(amount_len) || amount_decimal_ascii`
`|| effect_identity_digest32`.

For kind 4:

`uint16_be(1)`
`|| uint8(4)`
`|| candidate_id_uuid16`
`|| uint16_be(miner_len) || miner_utf8`
`|| uint16_be(amount_len) || amount_decimal_ascii`
`|| effect_identity_digest32`.

`accounting_id_uuid16` and `candidate_id_uuid16` use RFC 9562 bytes. `miner_utf8` is the exact Miningcore payout identity string used by the final effect, without normalization. `amount_decimal_ascii` is positive Mining `Decimal38Scale24` canonical ASCII. `effect_identity_digest32` is the immutable application-effect identity digest already stored by the final settlement/accounting transaction; it MUST bind the underlying accepted share/candidate/effect identity and final destination/amount semantics.

Construct every participant record, reject duplicate record bytes, sort the complete records lexicographically by raw bytes, then define:

`participant_effects_digest32 = SHA256(uint16_be(1) || uint32_be(participant_effect_count) || repeated(uint32_be(record_len) || record_bytes))`.

A scheme whose final effects cannot be represented by one of these allocated kinds MUST retain ordinary evidence until a future registry version allocates a representation.

### 6.2 Required sender-set bytes

Sender UUIDs are RFC 9562 bytes, unique and sorted lexicographically. Define:

`required_sender_set_bytes = uint16_be(1) || uint32_be(required_sender_count) || repeated(sender_uuid16)`.

`required_sender_set_digest32 = SHA256(required_sender_set_bytes)`.

### 6.3 CheckpointEvidenceV1

Each record is exactly:

`uint16_be(1)`
`|| sender_uuid16`
`|| uint64_be(sequence)`
`|| chain_hash32`
`|| int64_be(complete_through_unix_ms)`
`|| uint32_be(effective_skew_ms)`.

There MUST be exactly one checkpoint evidence record per required sender for the settlement proof. Sort records by sender UUID bytes; duplicate sender UUID is invalid. Define:

`checkpoint_evidence_digest32 = SHA256(uint16_be(1) || uint32_be(checkpoint_evidence_count) || repeated(uint32_be(record_len) || record_bytes))`.

### 6.4 UncertaintyRecordV1 and status allocation

Each relevant gap/quarantine/policy record retained by the proof is represented exactly as:

`uint16_be(1)`
`|| uint8(kind)`
`|| uint8(status)`
`|| uint16_be(identity_len) || identity_bytes`.

`kind` allocation:

- `1 = GAP`;
- `2 = QUARANTINE`;
- `3 = TEMPORAL_POLICY_RECONCILIATION`.

`status` allocation:

- `1 = UNRESOLVED`;
- `2 = RESOLVED_RECONCILED`;
- `3 = RESOLVED_WAIVED`;
- `4 = POLICY_RECONCILIATION_PENDING` (valid only for kind 3).

Valid kind/status combinations are: GAP or QUARANTINE with status 1,2,3; TEMPORAL_POLICY_RECONCILIATION with status 2,3,4. Unknown values/combinations are invalid.

Identity bytes are fully defined by kind:

- GAP: exactly `gap_uuid16`;
- QUARANTINE: `sender_uuid16 || uint8(lane) || epoch_uuid16 || uint64_be(sequence) || relay_event_uuid16 || uint16_be(event_type)`;
- TEMPORAL_POLICY_RECONCILIATION: `admin_idempotency_uuid16 || uint64_be(policy_generation)`.

Construct records, reject duplicate `(kind,identity_bytes)`, sort by raw `(kind, identity_bytes)`, and define:

`uncertainty_snapshot_digest32 = SHA256(uint16_be(1) || uint32_be(uncertainty_record_count) || repeated(uint32_be(record_len) || record_bytes))`.

An empty relevant uncertainty set is represented by count 0 and the digest of exactly `uint16_be(1)||uint32_be(0)`; it is never represented by zero bytes or a zero digest.

### 6.5 Reconstruction rule

An auditor with the retained summary plus the canonical participant/sender/checkpoint/uncertainty records MUST be able to reconstruct every digest byte-for-byte. Any implementation unable to persist these canonical records or independently reconstruct all four digests MUST retain the underlying ordinary evidence and MUST NOT claim `SettlementPruneSafe` on that basis.

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
