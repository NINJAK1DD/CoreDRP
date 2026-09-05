# CoreDRP/1 Draft 0.6 Semantic-Contract Registry — Freeze Completion

This registry is normative under Section 1 of `CoreDRP-1-SPEC-0.6.md`.

It explicitly incorporates these subregistries into the same normative authority tier:

- `coredrp-mining-v1-semantics.md`;
- `coredrp-miningcore-v1-semantics.md`;
- `coredrp-v1-clock-state.md`;
- `coredrp-v1-temporal-policy.md`;
- `coredrp-v1-settlement-safety.md`;
- `coredrp-v1-bitcoin-network-policies.md`.

Reference vectors/tools are lower authority than these registries.

## 1. Mining Profile 1.1 canonical source

Canonical source bytes:

`uint16_be(profile_id_len) || "coredrp.mining" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint8(payout_scheme) || uint16_be(coin_id_len) || coin_id_ascii || uint16_be(network_id_len) || network_id_ascii || uint16_be(completeness_policy_version) || uint16_be(retention_policy_version) || uint8(cross_sender_ordering_policy) || uint32_be(permitted_clock_skew_ms) || uint32_be(max_clock_step_ms) || uint32_be(probe_interval_ms) || uint32_be(probe_processing_max_ms) || uint32_be(evidence_expiry_ms) || uint32_be(unknown_grace_ms) || uint16_be(admission_idempotency_policy_version) || uint32_be(max_admission_records_per_generation)`.

The numeric fields do not merely carry implementation-selected version labels. Their legal values/meanings are frozen by the Mining semantics registry:

- `payout_scheme`: 1 PPLNS, 2 PPLNSBF, 3 PROP, 4 PPS, 5 CUSTODIAL_SOLO, 6 DIRECT_SOLO;
- `completeness_policy_version = 2` exactly;
- `retention_policy_version = 1` exactly;
- `cross_sender_ordering_policy = 1` exactly;
- `admission_idempotency_policy_version = 3` exactly;
- `semantic_retry_threshold = 3` exactly for Profile 1.1;
- `max_admission_records_per_generation` MUST be `1..100000000`.

Unknown/unallocated numeric semantics fail negotiation with `SEMANTIC_CONTRACT_MISMATCH`.

`max_admission_records_per_generation` applies to the scope-qualified producer namespace `(sender,lane,scope,producer_id)`; it is not a lane-global producer bound.

Reference `btc1` parameters use:

- payout scheme 1 (PPLNS);
- completeness policy 2;
- retention policy 1;
- cross-sender order 1;
- admission policy 3;
- max records/generation 1,000,000.

Reference source hex:

`000e636f72656472702e6d696e696e670000000100000001000462746331010007626974636f696e00076d61696e6e65740002000101000007d0000000fa00001388000000fa00003a980001d4c00003000f4240`

SHA-256:

`d21a908c547bcd177ed82b19ccf16bc6ea75b7631d86b38c3e86480b9e9f3307`

## 2. Miningcore Profile 1.1 canonical source

Canonical source bytes:

`uint16_be(profile_id_len) || "coredrp.miningcore" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint32_be(accounting_schema_version) || uint32_be(persistence_schema_version) || uint16_be(direct_candidate_validation_version) || uint16_be(settlement_policy_version) || bitcoin_network_policy_digest32`.

Legal values are exact:

- `accounting_schema_version = 1`;
- `persistence_schema_version = 1`;
- `direct_candidate_validation_version = 2`;
- `settlement_policy_version = 1`.

Unknown values fail negotiation with `SEMANTIC_CONTRACT_MISMATCH`.

`bitcoin_network_policy_digest32` MUST be exactly 32 bytes and MUST be recomputed from `coredrp-v1-bitcoin-network-policies.md` for the Mining-selected `network_id` and direct-candidate validation version.

Reference `btc1` uses Bitcoin mainnet network policy digest:

`0f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`

Reference source hex:

`0012636f72656472702e6d696e696e67636f726500000001000000010004627463310000000100000001000200010f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`

SHA-256:

`37b8c1cfbf0f8cc636c113f01b4942f323fa8e4d697c0eae9dcde5e94b2c4a79`

## 3. Clock-parameter composition

When multiple active Mining scopes share one sender/lane, the effective clock policy is the element-wise minimum defined by `coredrp-v1-clock-state.md`. This composition rule is part of Mining Profile 1.1 semantics even though the individual scope source bytes continue to carry each scope's own values.

## 4. Completeness composition

For a required sender and settlement boundary `B`, symmetric skew `S` requires checkpoint completeness through at least `B+2S` using checked arithmetic. The exact settlement/window and waived-hole semantics are in `coredrp-v1-settlement-safety.md`.

## 5. Temporal policy composition

Completeness mode remains temporal audited policy and is not immutable scope-contract state. Membership/mode lifecycle, sender staging, policy generation and retroactive correction are exactly `coredrp-v1-temporal-policy.md`.

## 6. Sorting and text rules

Profile IDs, coin IDs, network IDs, and commitment-class IDs are exact ASCII. Canonical sorts are by raw bytes, not locale/platform collation. Duplicate entries are rejected before hashing.

## 7. Epoch contract binding

The complete outer epoch contract-binding grammar is Section 11 of the canonical Draft 0.6 specification. Draft 0.6 vectors publish structured entries, independently reconstructed preimage, and digest for Core 1.1 / Mining 1.1 / Miningcore 1.1.

Every numeric field is range/semantic validated **before** sorting, deduplication, narrowing, or hashing. Unknown semantic-contract allocation values are not hashable aliases for future semantics; they are rejected negotiation inputs.
