# CoreDRP/1 Draft 0.6 Semantic-Contract Registry — Profile Freeze

This registry is normative under Section 1 of `CoreDRP-1-SPEC-0.6.md`.

It incorporates these subregistries at the same normative authority tier:

- `coredrp-mining-v1-semantics.md`;
- `coredrp-miningcore-v1-semantics.md`;
- `coredrp-v1-clock-state.md`;
- `coredrp-v1-temporal-policy.md`;
- `coredrp-v1-settlement-safety.md`;
- `coredrp-v1-settlement-scheme-policies.md`;
- `coredrp-v1-bitcoin-network-policies.md`;
- `coredrp-v1-producer-lifecycle.md`;
- `coredrp-v1-profile-transitions.md`;
- `coredrp-v1-quarantine-safety.md`.

Reference vectors/tools are lower authority.

## 1. Mining Profile 1.1 canonical source

Canonical source bytes remain:

`uint16_be(profile_id_len) || "coredrp.mining" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint8(payout_scheme) || uint16_be(coin_id_len) || coin_id_ascii || uint16_be(network_id_len) || network_id_ascii || uint16_be(completeness_policy_version) || uint16_be(retention_policy_version) || uint8(cross_sender_ordering_policy) || uint32_be(permitted_clock_skew_ms) || uint32_be(max_clock_step_ms) || uint32_be(probe_interval_ms) || uint32_be(probe_processing_max_ms) || uint32_be(evidence_expiry_ms) || uint32_be(unknown_grace_ms) || uint16_be(admission_idempotency_policy_version) || uint32_be(max_admission_records_per_generation)`.

Legal values:

- `payout_scheme`: 1 PPLNS, 2 PPLNSBF, 3 PROP, 4 PPS, 5 CUSTODIAL_SOLO, 6 DIRECT_SOLO;
- `completeness_policy_version = 2`;
- `retention_policy_version = 1`;
- `cross_sender_ordering_policy = 1`;
- `admission_idempotency_policy_version = 3`;
- `semantic_retry_threshold = 3`;
- `max_admission_records_per_generation` in `1..100000000`.

Producer lifecycle, permanent retirement, and cross-contract sealing are additionally normative through the incorporated producer/transition registries; those rules do not change this source grammar.

Reference `btc1` Mining source/digest remain:

`000e636f72656472702e6d696e696e670000000100000001000462746331010007626974636f696e00076d61696e6e65740002000101000007d0000000fa00001388000000fa00003a980001d4c00003000f4240`

`d21a908c547bcd177ed82b19ccf16bc6ea75b7631d86b38c3e86480b9e9f3307`

## 2. Miningcore Profile 1.1 canonical source

Canonical source bytes are now:

`uint16_be(profile_id_len) || "coredrp.miningcore" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint32_be(accounting_schema_version) || uint32_be(persistence_schema_version) || uint16_be(direct_candidate_validation_version) || uint16_be(settlement_policy_version) || bitcoin_network_policy_digest32 || settlement_scheme_policy_digest32`.

Legal values are exact:

- `accounting_schema_version = 2` (projection-local scope + shared merged-mining proof identity);
- `persistence_schema_version = 1`;
- `direct_candidate_validation_version = 2`;
- `settlement_policy_version = 2` (scheme-policy binding, interval pruning and quarantine lifecycle).

Both digests MUST be exactly 32 bytes and recomputed from their normative registries for the Mining-selected `network_id` and `payout_scheme`.

Reference `btc1` uses:

- Bitcoin mainnet policy digest `0f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`;
- PPLNS settlement policy (`factor=2`) digest `8218444045964b49331e0e7e74590574ac552f522aa482b2aa60d7fca2637725`.

Reference Miningcore source hex:

`0012636f72656472702e6d696e696e67636f726500000001000000010004627463310000000200000001000200020f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a8218444045964b49331e0e7e74590574ac552f522aa482b2aa60d7fca2637725`

SHA-256:

`2bded7fc35e478999d00b0d9089bb6fc280f255458b70e64649826273a48a801`

## 3. Clock composition

Multi-scope effective clock policy is the element-wise minimum in `coredrp-v1-clock-state.md`. Temporal-policy `applicable_clock_uncertainty` is exactly the deterministic function in `coredrp-v1-temporal-policy.md`.

## 4. Completeness and settlement composition

Cross-sender completeness uses checked `B+2S`. Settlement dependency sets and scheme-specific pruning use `coredrp-v1-settlement-safety.md` plus the bound settlement-scheme policy digest.

## 5. Temporal policy

Completeness mode remains temporal audited state rather than immutable scope-contract state. Membership/mode lifecycle, deterministic staging sender set, safety origin and correction semantics are in `coredrp-v1-temporal-policy.md`.

## 6. Sorting/text rules

Profile IDs, coin IDs, network IDs, settlement policy keys/values and commitment-class IDs are exact ASCII where their registries require ASCII. Canonical sorts are raw-byte sorts. Duplicate entries are rejected before hashing.

## 7. Epoch contract binding and migration

The outer epoch contract-binding grammar remains Section 11 of the canonical specification. Every numeric value is validated before sorting/deduplication/hashing.

A successor epoch with changed Mining or Miningcore scope-contract digest is additionally subject to `coredrp-v1-profile-transitions.md`; a changed digest is not permission to reinterpret active producer generations or unsettled financial history.
