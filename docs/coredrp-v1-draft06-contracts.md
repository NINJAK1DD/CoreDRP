# CoreDRP/1 Draft 0.6 Semantic-Contract Registry

This registry is normative under Section 1 of `CoreDRP-1-SPEC-0.6.md`.

This registry also explicitly incorporates `coredrp-v1-clock-state.md` as the normative Core 1.1 `ClockStateUpdate` validity/state-transition subregistry referenced by Sections 29–30 of the canonical Draft 0.6 specification. The clock-state subregistry is therefore part of the incorporated-registry authority tier, not merely an example vector or reference-tool convention.

## Mining Profile 1.1

Canonical source bytes:

`uint16_be(profile_id_len) || "coredrp.mining" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint8(payout_scheme) || uint16_be(coin_id_len) || coin_id_ascii || uint16_be(network_id_len) || network_id_ascii || uint16_be(completeness_policy_version) || uint16_be(retention_policy_version) || uint8(cross_sender_ordering_policy) || uint32_be(permitted_clock_skew_ms) || uint32_be(max_clock_step_ms) || uint32_be(probe_interval_ms) || uint32_be(probe_processing_max_ms) || uint32_be(evidence_expiry_ms) || uint32_be(unknown_grace_ms) || uint16_be(admission_idempotency_policy_version) || uint32_be(max_admission_records_per_generation)`

Draft 0.6 requires:

- `admission_idempotency_policy_version = 3`;
- `max_admission_records_per_generation` in `1..100000000` and operationally chosen so one active generation is bounded on durable storage;
- `semantic_retry_threshold = 3` exactly for CoreDRP/1 Draft 0.6. This fixed threshold is part of the normative profile semantics; changing it requires a new profile minor.

The semantic-retry threshold is therefore not a free receiver setting even though it is not separately encoded in the source bytes: Profile 1.1 Draft 0.6 fixes it to 3.

Reference `btc1` parameters use `max_admission_records_per_generation = 1000000`.

Reference source hex:

`000e636f72656472702e6d696e696e670000000100000001000462746331010007626974636f696e00076d61696e6e65740002000101000007d0000000fa00001388000000fa00003a980001d4c00003000f4240`

SHA-256:

`d21a908c547bcd177ed82b19ccf16bc6ea75b7631d86b38c3e86480b9e9f3307`

## Miningcore Profile 1.1

Canonical source bytes:

`uint16_be(profile_id_len) || "coredrp.miningcore" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint32_be(accounting_schema_version) || uint32_be(persistence_schema_version) || uint16_be(direct_candidate_validation_version) || uint16_be(settlement_policy_version) || bitcoin_network_policy_digest32`

The `bitcoin_network_policy_digest32` MUST be exactly 32 bytes and MUST be recomputed from `coredrp-v1-bitcoin-network-policies.md` for the Mining-selected `network_id` and selected `direct_candidate_validation_version`.

Reference `btc1` uses Bitcoin mainnet network policy digest:

`0f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`

Reference source hex:

`0012636f72656472702e6d696e696e67636f726500000001000000010004627463310000000100000001000200010f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`

SHA-256:

`37b8c1cfbf0f8cc636c113f01b4942f323fa8e4d697c0eae9dcde5e94b2c4a79`

## Sorting and text rules

Profile IDs, coin IDs, network IDs, and commitment-class IDs are exact ASCII. Canonical sorts are by raw bytes, not locale/platform collation. Duplicate entries are rejected before hashing.

## Epoch contract binding

The complete outer epoch contract-binding grammar is Section 11 of the canonical Draft 0.6 specification. Draft 0.6 vectors publish the full structured entries, reconstructed preimage, and digest for Core 1.1 / Mining 1.1 / Miningcore 1.1.
