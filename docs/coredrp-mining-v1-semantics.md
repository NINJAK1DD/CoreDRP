# CoreDRP Mining Profile 1.1 — Normative Semantics

**Status:** Draft 0.5 normative registry  
**Profile ID:** `coredrp.mining`  
**Profile version:** 1.1  
**Minimum Core:** 1.1

This registry is incorporated by `CoreDRP-1-SPEC-0.5.md`. Where a reference validator disagrees with this registry, this registry is authoritative.

## 1. Scope and placement

Mining scope is exact ASCII `[A-Za-z0-9._-]{1,64}`, case-sensitive, with no Unicode normalization. `MiningShareEvent` is event type `0x0100`, lane 0, and requires non-empty scope. A Mining checkpoint is Core type `0x0001`, lane 0, empty Core scope; its covered Mining scopes are derived from the persisted epoch contracts and temporal policy.

## 2. String and byte limits

After protobuf parsing and before durable acceptance:

| Field | Maximum UTF-8/byte length |
|---|---:|
| `miner` | 256 |
| `worker` | 128 |
| `user_agent` | 256 |
| `source_ip` | 64 |
| `source` | 64 |
| `session_id` | 128 |
| `candidate_kind` | 64 |
| `transaction_confirmation_data` | 4096 |
| `candidate_hash` | 128 |

`miner` MUST be non-empty. Other strings MAY be empty only where the application semantics permit it; no string is normalized before hashing, admission identity, storage, or comparison.

## 3. Difficulty semantics

`difficulty`, `achieved_share_difficulty`, `actual_difficulty`, and `network_difficulty` MUST be finite IEEE-754 binary64 values. NaN, infinities, negative values, and negative zero are invalid.

For accepted-work events:

- `difficulty > 0`;
- `actual_difficulty > 0`;
- `network_difficulty > 0`;
- `achieved_share_difficulty >= 0`.

Zero `achieved_share_difficulty` is allowed only as the explicit informational value represented by the event; the other three quantities are strictly positive.

## 4. Event time and identity

`MiningShareEvent.created_unix_ms` MUST equal the enclosing Core `Event.event_time_unix_ms` exactly. The enclosing Core event time obeys the production range and anti-backdating rules in the Core specification.

`block_height` is an unsigned 64-bit value. Its chain-specific meaning is determined by the selected Mining scope contract.

## 5. Candidate field matrix

If `is_block_candidate == false`, all of the following MUST be absent:

- `candidate_hash`;
- `candidate_kind`;
- `transaction_confirmation_data`;
- `block_reward`.

If `is_block_candidate == true`, `candidate_hash` MUST be present and non-empty. The remaining candidate fields are optional but, when present, MUST satisfy their length and value grammars.

A candidate field combination that violates this matrix is `SEMANTIC_PAYLOAD_INVALID`; it is quarantinable only because placement and Core history are otherwise valid.

## 6. Decimal38Scale24

`Decimal38Scale24.canonical` is an ASCII decimal string with no sign, exponent, whitespace, leading plus, locale separator, NaN, or infinity. The grammar is:

`(?:0|[1-9][0-9]{0,13})(?:\.[0-9]{0,23}[1-9])?`

The representation has at most 38 decimal digits excluding the point, at most 24 fractional digits, no unnecessary trailing fractional zero, and numeric value less than `100000000000000`.

Fields whose semantics are positive-only MUST reject canonical zero. `block_reward`, when present on a block candidate, is positive-only.

## 7. Temporal membership and completeness

Membership intervals are half-open `[valid_from_unix_ms, valid_until_unix_ms)`. Under `RELAY_REQUIRED`, a payout-relevant lane-0 Mining event at time `T` requires durable membership for `(sender,scope,T)`; transport authorization alone is insufficient. Missing membership fails closed with `TEMPORAL_MEMBERSHIP_REQUIRED`.

Normal membership/mode changes effective at or before the current `PayoutSafeThrough(scope)` are forbidden. Retroactive correction uses the privileged temporal-policy reconciliation path defined by the Core specification and ADMIN registry.

## 8. Canonical cross-sender order

When Mining accounting requires a deterministic total order across senders, sort by:

1. `event_time_unix_ms` ascending;
2. sender UUID RFC 9562 bytes lexicographically;
3. Core sequence ascending;
4. relay-event UUID bytes lexicographically.

Database insertion order MUST NOT be used as a tie-breaker. This is an accounting order, not a claim of physical cross-sender causality.

## 9. Admission idempotency policy v3

Mining Profile 1.1 Draft 0.5 uses `admission_idempotency_policy_version = 3` and binds `max_admission_records_per_generation` in the Mining semantic contract.

The local caller admission key is structurally:

`producer_id_uuid(16 RFC9562 bytes) || uint64_be(producer_generation) || uint64_be(admission_sequence)`.

For each `(sender_id,lane_id,producer_id)`:

- `producer_generation` starts at 1 and only the current active generation may accept new admissions;
- new `admission_sequence` values are exactly monotonic (`last_new_sequence + 1`); retries reuse the original sequence;
- while a generation is active, the sender retains the exact mapping from admission sequence to admission digest and original Core admission result;
- the active generation MUST NOT exceed `max_admission_records_per_generation` records;
- before exceeding the bound, the producer MUST durably seal the generation after all in-flight admissions have durable outcomes;
- sealing atomically advances a durable `retired_generation_high_water` and discards the per-admission map for that sealed generation;
- any request naming `producer_generation <= retired_generation_high_water` is rejected locally as `CALLER_ADMISSION_GENERATION_RETIRED` and can never create another Core event;
- the next active generation is exactly `retired_generation_high_water + 1`.

Thus detailed retry state is bounded to the active generation while the permanent no-double-mint property is represented by one compact high-water record per producer. A sealed-generation retry may no longer retrieve the historical response, but it can never mint a second financial event.

The generation map, seal record, high-water record, and admitted WAL record cross a durability boundary before application success. Caller producer IDs MUST be stable within one durable producer identity and MUST NOT be shared by independent durability domains.

## 10. Canonical MiningShare request bytes

Canonical caller-request encoding version 1 is the exact byte grammar defined in Section 15 of the Core specification. It covers the stable caller-supplied share fields, uses fixed big-endian numbers and explicit optional-presence markers, and excludes generated Core sequence, log epoch, relay UUID, and `created_unix_ms`.

No protobuf, JSON, locale, native-endian, or omitted-default serialization is an acceptable substitute.

## 11. Validation result

A correctly placed event that violates this registry is `SEMANTIC_PAYLOAD_INVALID`. Structural range, lane, scope, contract-ownership, authorization, membership, clock, chain, and anti-backdating failures use their Core errors and are not converted into profile-semantic quarantine.
