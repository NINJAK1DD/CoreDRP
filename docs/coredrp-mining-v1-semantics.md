# CoreDRP Mining Profile 1.1 — Normative Semantics

**Status:** Draft 0.6 freeze-completion normative registry  
**Profile ID:** `coredrp.mining`  
**Profile version:** 1.1  
**Minimum Core:** 1.1

This registry is incorporated by `CoreDRP-1-SPEC-0.6.md`. Where reference tooling disagrees with this registry, this registry is authoritative.

## 1. Scope and placement

Mining scope is exact ASCII `[A-Za-z0-9._-]{1,64}`, case-sensitive, with no Unicode normalization. `MiningShareEvent` is event type `0x0100`, lane 0, and requires non-empty scope. A Mining checkpoint is Core type `0x0001`, lane 0, empty Core scope; its covered Mining scopes are derived from persisted epoch contracts, admitted payout-effect scopes, and temporal policy.

## 2. String and byte limits

After protobuf parsing and before durable acceptance:

| Field | Maximum UTF-8/byte length | Empty allowed |
|---|---:|---|
| `miner` | 256 | **NO** |
| `worker` | 128 | YES |
| `user_agent` | 256 | YES |
| `source_ip` | 64 | YES in generic Mining only |
| `source` | 64 | YES |
| `session_id` | 128 | YES in generic Mining only |
| `candidate_kind` | 64 | NO when present |
| `transaction_confirmation_data` | 4096 | NO when present |
| `candidate_hash` | 128 | NO when present |

Empty `worker` means an unlabelled worker. Empty `user_agent`, `source_ip`, `source`, or `session_id` means the upstream did not supply that optional descriptive value. These empty strings remain exact values; implementations MUST NOT substitute defaults before hashing, admission identity, storage, comparison, or accounting order.

Miningcore accounting semantics may strengthen generic Mining requirements for fields embedded in `0x0200`; those stronger constraints are normative for that event type.

No string is Unicode-normalized before hashing, admission identity, storage, or comparison.

## 3. Difficulty semantics

`difficulty`, `achieved_share_difficulty`, `actual_difficulty`, and `network_difficulty` MUST be finite IEEE-754 binary64 values. NaN, infinities, negative values, and negative zero are invalid.

For accepted-work events:

- `difficulty > 0`;
- `actual_difficulty > 0`;
- `network_difficulty > 0`;
- `achieved_share_difficulty >= 0`.

Zero `achieved_share_difficulty` is allowed only as the explicit informational value represented by a generic Mining event. Miningcore accounting `0x0200` strengthens this to strictly positive.

## 4. Event time and identity

`MiningShareEvent.created_unix_ms` MUST equal the enclosing Core `Event.event_time_unix_ms` exactly. The enclosing Core event time obeys the production range and anti-backdating rules in the Core specification.

`block_height` is an unsigned 64-bit value. Its chain-specific meaning is determined by the selected Mining scope contract.

## 5. Candidate field matrix

If `is_block_candidate == false`, all of the following MUST be absent:

- `candidate_hash`;
- `candidate_kind`;
- `transaction_confirmation_data`;
- `block_reward`.

If `is_block_candidate == true`, `candidate_hash` MUST be present and non-empty. The remaining candidate fields are optional but, when present, MUST be non-empty and satisfy their length/value grammars.

A candidate-field combination that violates this matrix is `SEMANTIC_PAYLOAD_INVALID`; it is quarantinable only because placement and Core history are otherwise valid.

## 6. Decimal38Scale24

`Decimal38Scale24.canonical` is an ASCII decimal string with no sign, exponent, whitespace, leading plus, locale separator, NaN, or infinity. The grammar is:

`(?:0|[1-9][0-9]{0,13})(?:\.[0-9]{0,23}[1-9])?`

The representation has at most 38 decimal digits excluding the point, at most 24 fractional digits, no unnecessary trailing fractional zero, and numeric value less than `100000000000000`.

Fields whose semantics are positive-only MUST reject canonical zero. `block_reward`, when present on a block candidate, is positive-only.

## 7. Frozen semantic-contract numeric allocations

These numeric values are part of Mining Profile 1.1 semantics. Unknown values MUST fail scope-contract negotiation with `SEMANTIC_CONTRACT_MISMATCH`; implementations MUST NOT assign local meanings to unallocated values.

### 7.1 payout_scheme (`uint8`)

| Value | Meaning |
|---:|---|
| 0 | UNSPECIFIED — invalid for a selected scope contract |
| 1 | PPLNS |
| 2 | PPLNSBF |
| 3 | PROP |
| 4 | PPS |
| 5 | CUSTODIAL_SOLO |
| 6 | DIRECT_SOLO |
| 7..255 | unallocated; reject |

### 7.2 completeness_policy_version (`uint16`)

| Value | Meaning |
|---:|---|
| 2 | CoreDRP Mining completeness algorithm defined by Sections 8, 11 and `coredrp-v1-settlement-safety.md`, including conservative cross-sender skew coverage |
| all others | unallocated for Mining 1.1; reject |

### 7.3 retention_policy_version (`uint16`)

| Value | Meaning |
|---:|---|
| 1 | CoreDRP Mining retention algorithm defined by `coredrp-v1-settlement-safety.md` and Miningcore scheme rules |
| all others | unallocated for Mining 1.1; reject |

### 7.4 cross_sender_ordering_policy (`uint8`)

| Value | Meaning |
|---:|---|
| 1 | canonical order in Section 9 |
| all others | unallocated for Mining 1.1; reject |

### 7.5 admission_idempotency_policy_version (`uint16`)

| Value | Meaning |
|---:|---|
| 3 | scope-qualified bounded producer generations in Section 10 |
| all others | unallocated for Mining 1.1; reject |

`semantic_retry_threshold` is fixed at exactly 3 for Mining Profile 1.1 and is not a receiver-local tuning knob.

## 8. Temporal membership, payout-effect scopes and cross-sender completeness

Membership intervals are half-open `[valid_from_unix_ms, valid_until_unix_ms)`.

Define `PayoutEffectScopes(E)` as the exact set of Mining scopes into which event `E` creates payout-relevant durable effects.

- For `0x0100 MiningShareEvent`, `PayoutEffectScopes(E) = {Event.scope}`.
- For `0x0200 MiningcoreAccountingShareEvent`, `PayoutEffectScopes(E)` is defined by the Miningcore registry and contains the primary projection scope plus the paired auxiliary projection scope when present.

For **every** `Q in PayoutEffectScopes(E)` independently:

- the sender MUST be transport-authorized for `Q`;
- exact selected Mining scope contract must exist for `Q`;
- if mode `(Q,T)` is `RELAY_REQUIRED`, durable temporal membership `(sender,Q,T)` MUST exist.

Missing transport authorization is `UNAUTHORIZED_SCOPE`. Missing required membership is `TEMPORAL_MEMBERSHIP_REQUIRED`. These failures are non-quarantinable and occur before application effects commit.

A sender that has admitted payout-relevant effects into scope `Q` during an epoch is part of that scope's completeness history even when `Q != Event.scope` of the containing event. Checkpoint coverage and RequiredSender evaluation MUST therefore include `Q`; embedded/auxiliary scopes cannot bypass completeness by being nested inside another Core event scope.

For a settlement/block boundary `B` and symmetric maximum permitted skew `S` for a required sender, receiver completeness evidence MUST cover at least:

`required_complete_through(B,S) = B + 2*S`.

The addition and multiplication use checked arithmetic against the Core production-time range. Overflow fails closed and the boundary is not payout-safe.

A tighter sender-specific offset interval MAY replace the `B+2S` requirement only if the implementation can prove from one fresh clock observation that its derived required boundary is **no less conservative** than the symmetric rule for all real event times compatible with that observation. The derivation and evidence MUST be durable with the settlement proof. Implementations that do not implement such a proof MUST use `B+2S` exactly.

Conformance boundaries are:

- checkpoint completeness `B+2S-1` => insufficient;
- checkpoint completeness `B+2S` => sufficient, subject to all other safety gates;
- any overflow while computing `B+2S` => fail closed.

Ordinary membership/mode changes at or behind the protected payout frontier plus clock uncertainty are forbidden by the Core temporal-policy registry. Retroactive correction uses the privileged temporal-policy reconciliation path and never silently rewrites already-proven history.

## 9. Canonical cross-sender order

When Mining accounting requires a deterministic total order across senders, sort by:

1. `event_time_unix_ms` ascending;
2. sender UUID RFC 9562 bytes lexicographically;
3. Core sequence ascending;
4. relay-event UUID bytes lexicographically.

Database insertion order MUST NOT be used as a tie-breaker. This is an accounting order, not a claim of physical cross-sender causality.

## 10. Admission idempotency policy v3

Mining Profile 1.1 uses `admission_idempotency_policy_version = 3` and binds `max_admission_records_per_generation` in each Mining scope contract.

The local caller admission key is structurally:

`producer_id_uuid(16 RFC9562 bytes) || uint64_be(producer_generation) || uint64_be(admission_sequence)`.

The durable namespace is exactly:

`(sender_id, lane_id, scope, producer_id)`.

A producer identity therefore belongs to **one Mining scope within one sender/lane durability domain**. The same `producer_id` MUST NOT be reused for another scope under the same sender/lane. This makes the per-scope semantic-contract capacity unambiguous.

For each namespace:

- `producer_generation` starts at 1 and only the current active generation may accept new admissions;
- new `admission_sequence` values are exactly monotonic (`last_new_sequence + 1`); retries reuse the original sequence;
- while a generation is active, the sender retains the exact mapping from admission sequence to admission digest and original Core admission result;
- the active generation MUST NOT exceed that scope contract's `max_admission_records_per_generation` records;
- before exceeding the bound, the producer MUST durably seal the generation after all in-flight admissions have durable outcomes;
- sealing atomically advances durable `retired_generation_high_water` and discards the detailed per-admission map for that sealed generation;
- any request naming `producer_generation <= retired_generation_high_water` is rejected locally as `CALLER_ADMISSION_GENERATION_RETIRED` and can never create another Core event;
- the next active generation is exactly `retired_generation_high_water + 1`.

### 10.1 Overflow

Both `producer_generation` and `admission_sequence` are unsigned 64-bit counters and MUST NOT wrap.

- Before incrementing `admission_sequence == 2^64-1`, the current generation MUST be sealed; no new admission may be created in that generation.
- If `producer_generation == 2^64-1`, that producer identity is permanently exhausted after sealing and MUST NOT start another generation. A replacement producer UUID requires explicit durable producer registration.
- Overflow or attempted wrap is a permanent local admission failure and MUST NOT create a Core event.

### 10.2 Producer registry and bounded durable state

Producer UUIDs are not caller-created free-form cardinality. Each sender maintains a durable authorized producer registry keyed by `(lane,scope,producer_id)`.

Mining Profile 1.1 permits at most **1024 registered producer IDs per `(sender,lane,scope)`**. Registration/removal is an explicit local administrative operation; an admission request for an unregistered producer is rejected before WAL admission. Removing a producer creates/retains the permanent producer tombstone defined by `coredrp-v1-producer-lifecycle.md`; the same UUID cannot later be registered again in that namespace.

A deployment requiring more than 1024 producers for one scope requires a future Mining profile revision or an explicitly partitioned sender identity.

Thus detailed retry state is bounded to one active generation per registered producer and the permanent no-double-mint property is represented by one compact high-water/tombstone record per producer.

The generation map, seal record, high-water record, producer-registration/tombstone record, and admitted WAL record cross a durability boundary before application success.

## 11. Canonical MiningShare caller-request bytes

Canonical request encoding version 1 is frozen here byte-for-byte. It is independent of protobuf serialization and is the `canonical_request_bytes` input to the Core admission digest.

Encoding helpers:

- `lp32_utf8(s) = uint32_be(len(UTF8(s))) || UTF8(s)` with exact UTF-8 bytes and no normalization;
- `optional_lp32_bytes(v) = 0x00` when absent, otherwise `0x01 || uint32_be(len(v)) || v`;
- `optional_lp32_utf8(s) = 0x00` when absent, otherwise `0x01 || lp32_utf8(s)`;
- `optional_lp32_ascii(s) = 0x00` when absent, otherwise `0x01 || uint32_be(len(ASCII(s))) || ASCII(s)`;
- a boolean is exactly one byte `0x00` or `0x01`;
- each difficulty double is first validated by Section 3, then encoded as the exact IEEE-754 binary64 bit pattern in network/big-endian byte order.

The exact ordered grammar is:

`uint16_be(1)`
`|| uint64_be(block_height)`
`|| lp32_utf8(miner)`
`|| lp32_utf8(worker)`
`|| lp32_utf8(user_agent)`
`|| ieee754_binary64_be(difficulty)`
`|| ieee754_binary64_be(achieved_share_difficulty)`
`|| ieee754_binary64_be(actual_difficulty)`
`|| ieee754_binary64_be(network_difficulty)`
`|| lp32_utf8(source_ip)`
`|| lp32_utf8(source)`
`|| lp32_utf8(session_id)`
`|| uint8(is_block_candidate ? 1 : 0)`
`|| optional_lp32_bytes(candidate_hash)`
`|| optional_lp32_utf8(candidate_kind)`
`|| optional_lp32_utf8(transaction_confirmation_data)`
`|| optional_lp32_ascii(block_reward.canonical)`.

`block_reward.canonical`, when present, MUST already satisfy Section 6 before encoding.

`created_unix_ms` is intentionally excluded because the lane sequencer assigns it only after idempotency resolution. Core sequence, log epoch, relay-event UUID, receiver state, and protobuf unknown fields are likewise excluded.

No protobuf serialization, JSON serialization, locale formatting, native-endian floating representation, omitted-default heuristic, field-number iteration, or field reordering is an acceptable substitute. Future caller-request grammars require an explicit Mining profile revision or explicitly versioned grammar; the request-encoding version used for an active admission mapping is durable with that mapping.

## 12. Settlement safety and contiguous frontier

The normative settlement/window rules are in `coredrp-v1-settlement-safety.md`.

`PayoutSafeThrough(scope)` retains its literal meaning: every time in the contiguous interval up to that frontier is PayoutSafe under the applicable temporal policy. A `RESOLVED_WAIVED` hole therefore caps this scalar frontier until the hole is reconciled; implementations MUST NOT advance the scalar across a known non-safe interval.

Windowed settlement is not forced to use that scalar as its only proof. `SettlementSafe(scope, settlement_id, evidence_from, evidence_through)` may prove a later settlement safe when its exact required evidence interval excludes every unresolved/waived hole. This predicate is auditable and settlement-specific; it MUST NOT mutate or imply a higher `PayoutSafeThrough` value.

## 13. Validation result

A correctly placed event that violates this registry is `SEMANTIC_PAYLOAD_INVALID`. Structural range, lane, scope, contract-ownership, authorization, membership, clock, chain, anti-backdating, producer-registration, or temporal-policy failures use their Core/profile control errors and are not converted into profile-semantic quarantine.
