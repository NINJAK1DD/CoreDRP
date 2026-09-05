# CoreDRP Miningcore Request Identity Registry — Draft 0.6

Normative under Miningcore Profile 1.1. Encoding version 1 is allocated for the three request types below. The corresponding ordered, typed schema is `coredrp-v1-request-schemas.json`, incorporated at the same authority. The tables and schema must agree; protobuf serialization/field iteration is not an encoding rule.

## 1. Primitive encoding

Each record starts with `uint16_be(1)` followed by its fields in table order, with no padding or field omission. `u8`, `u16`, `u32`, `u64`, `i64` are exact checked big-endian integers; `bool` is one byte 0/1. `bytes` and `utf8`/`ascii` are `uint32_be(length) || exact bytes`. UUIDs use raw 16 RFC 9562 bytes; `hash32` is raw 32 bytes. Optional `?T` is 0x00 when absent or 0x01 followed by T when present, including present-empty variable bytes. A nested record is `uint32_be(length) || complete record`. Arrays are `uint32_be(count) || repeated(uint32_be(record_length) || record)` in the order specified below. Validate profile ranges, required fields and aggregate Core payload cap before admission; no narrowing, normalization or implicit numeric/boolean coercion. Unknown request keys or missing fields are invalid, including generated `created_unix_ms`.

## 2. Accounting requests (`0x0200`, lane 0)

`MiningcoreAccountingShareRequestV1`: `primary:ProjectionRequestV1`, `paired:?ProjectionRequestV1`.

`ProjectionRequestV1`, in order:

| Field | Encoding |
|---|---|
| scope | bytes (Mining scope) |
| share | MiningShareRequestV1 from Mining semantics §11, length-prefixed |
| accounting_id | uuid16, mandatory nonzero |
| accounting_role | u8 (SINGLE=1, PARENT=2, AUXILIARY=3) |
| reward_basis_satoshis | i64, positive |
| pps_calculated_amount | ?ascii, canonical decimal when present |
| block_only | bool |
| block_record_emitted | bool |
| statistical_record_emitted | bool |
| preserve_created | bool |

Primary then optional paired is exact order. All accounting-schema validity/role/pair rules apply before admission; every projection carries its own scope. `created_unix_ms` is absent from the embedded MiningShare request. Only after idempotency lookup resolves a new request may the sequencer assign one Core time and populate both projections' created values. The request's accepted scope contracts and encoding version are durable with its idempotency mapping.

## 3. Direct candidate requests (`0x0201`, lane 1)

`BitcoinDirectCoinbaseCandidateRequestV1` fields in order:

| Field | Encoding |
|---|---|
| block_height | u64 |
| block_hash | hash32 (RPC/display order) |
| coinbase_txid | hash32 (RPC/display order) |
| serialized_block | bytes (exact consensus bytes) |
| gross_reward_satoshis | i64 |
| miner_script_pub_key | bytes |
| miner_reward_satoshis | i64 |
| recipients | array DirectRecipientRequestV1 |
| miner | utf8 |
| worker | utf8 |
| candidate_id | uuid16 |
| submission_state | u8, PREPARED=1 for a new candidate |
| consensus_commitments | array CommitmentRequestV1 |

`DirectRecipientRequestV1`: `address:?utf8 || script_pub_key:bytes || amount_satoshis:i64` after its version. Sort complete encoded recipient records lexicographically, retaining multiplicity. `CommitmentRequestV1`: `output_index:u32 || script_pub_key:bytes` after its version; sort by numeric output index and reject duplicate indices. Bounds and candidate validation remain mandatory. Metadata presence is part of request identity even though consensus script bytes remain authoritative.

Candidate UUID is generated/persisted by the caller before the first attempt and reused on retry, unlike the sequencer's generated relay UUID. Changing any caller field changes the request digest.

## 4. Candidate state requests (`0x0202`, lane 1)

`CandidateStateUpdateRequestV1`: `candidate_id:uuid16 || state:u8 || submission_attempts:u32 || definitive_misses:u32 || last_attempt_unix_ms:?i64` after version. State/counter/time validity and candidate referential checks remain mandatory. `last_attempt_unix_ms` is caller evidence and is included; it is not the generated Core event time.

## 5. Admission digest

Use the existing Core grammar exactly:

`SHA256("CoreDRP1-ADMISSION" || uint8(lane) || uint16_be(event_type) || uint16_be(scope_len) || scope || uint32_be(request_len) || request)`.

Scope is the enclosing event scope; nested scopes are bound inside the request. Core sequence, epoch, relay UUID and generated Core time are excluded. Unknown protobuf fields are not caller request fields; stable new caller semantics require a newly allocated request grammar, never silently ignoring them. A retransmission of an already admitted immutable event uses Core replay, not a reconstructed new admission.
