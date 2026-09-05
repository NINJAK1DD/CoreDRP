# CoreDRP/1 Draft 0.6 Semantic-Contract Registry — Profile Freeze

This registry is normative under Section 1 of `CoreDRP-1-SPEC-0.6.md`.

It incorporates these subregistries at the same normative authority tier:

- `coredrp-mining-v1-semantics.md`;
- `coredrp-miningcore-v1-semantics.md`;
- `coredrp-v1-clock-state.md`;
- `coredrp-v1-temporal-policy.md`;
- `coredrp-v1-settlement-safety.md`;
- `coredrp-v1-settlement-scheme-policies.md`;
- `coredrp-v1-share-difficulty-adjustment-policies.md`;
- `coredrp-v1-bitcoin-network-policies.md`;
- `coredrp-v1-producer-lifecycle.md`;
- `coredrp-v1-profile-transitions.md`;
- `coredrp-v1-quarantine-safety.md`;
- `coredrp-v1-validator-authorities.md`, `coredrp-v1-miningcore-requests.md`.

Reference vectors/tools are lower authority.

## 1. Mining Profile 1.1 canonical source

Canonical source grammar remains:

`uint16_be(profile_id_len) || "coredrp.mining" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint8(payout_scheme) || uint16_be(coin_id_len) || coin_id_ascii || uint16_be(network_id_len) || network_id_ascii || uint16_be(completeness_policy_version) || uint16_be(retention_policy_version) || uint8(cross_sender_ordering_policy) || uint32_be(permitted_clock_skew_ms) || uint32_be(max_clock_step_ms) || uint32_be(probe_interval_ms) || uint32_be(probe_processing_max_ms) || uint32_be(evidence_expiry_ms) || uint32_be(unknown_grace_ms) || uint16_be(admission_idempotency_policy_version) || uint32_be(max_admission_records_per_generation)`.

Legal values:

- `payout_scheme`: 1 PPLNS, 2 PPLNSBF, 3 PROP, 4 PPS, 5 CUSTODIAL_SOLO, 6 DIRECT_SOLO;
- `completeness_policy_version = 4`;
- `retention_policy_version = 1`;
- `cross_sender_ordering_policy = 1`;
- `admission_idempotency_policy_version = 3`;
- `semantic_retry_threshold = 3`;
- `max_admission_records_per_generation` in `1..100000000`.

Reference `btc1` Mining source/digest (completeness policy 4):

`000e636f72656472702e6d696e696e670000000100000001000462746331010007626974636f696e00076d61696e6e65740004000101000007d0000000fa00001388000000fa00003a980001d4c00003000f4240`

`deb1d84a84128c180a91e9bd13fe73bc8a5f46e5a88f2d23f2617cecd68f2ac2`

## 2. Miningcore Profile 1.1 canonical source

Canonical source bytes are:

`uint16_be(profile_id_len) || "coredrp.miningcore" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint32_be(accounting_schema_version) || uint32_be(persistence_schema_version) || uint16_be(direct_candidate_validation_version) || uint16_be(settlement_policy_version) || bitcoin_network_policy_digest32 || settlement_scheme_policy_digest32`.

Legal values are exact:

- `accounting_schema_version = 3` — strict ordinary Miningcore accounting compatibility, projection-local authorization/membership and non-block-only accounting;
- `persistence_schema_version = 1`;
- `direct_candidate_validation_version = 2`;
- `settlement_policy_version = 5` — exact score/cutoff arithmetic, bound PPS liability, canonical effect identities, exact PoolId mapping, canonical Miningcore requests, global accounting uniqueness, retained source/reward audit inputs, and financial safety hardening. Versions 3 and 4 are historical and MUST NOT negotiate as version 5; the financial migration barrier applies.

Both digests MUST be exactly 32 bytes and recomputed from their normative registries for the Mining-selected network/payout configuration.

Reference `btc1` uses:

- Bitcoin mainnet policy digest `0f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`;
- share-difficulty adjustment policy `identity` digest `512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf`;
- PPLNS resolved factor `2` settlement-policy digest `779cd6c162373a543660f304d11eab7b19faace462be46886833fd2fa025276a`.

Reference Miningcore source hex:

`0012636f72656472702e6d696e696e67636f726500000001000000010004627463310000000300000001000200050f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a779cd6c162373a543660f304d11eab7b19faace462be46886833fd2fa025276a`

SHA-256:

`6ecd5753448cc09f2ecda289a9b77b31b83dbc0391f83d402620f309f6b83979`

## 3. Clock composition

Multi-scope effective clock policy is the element-wise minimum in `coredrp-v1-clock-state.md`. Temporal-policy transition uncertainty, including last-scope deactivation, is exactly the deterministic function in `coredrp-v1-temporal-policy.md`.

## 4. Completeness and settlement composition

Cross-sender completeness uses checked `B+2S`. Every payout-effect scope, including a Miningcore auxiliary projection scope, is independently authorization/membership gated and participates in checkpoint/RequiredSender history. Settlement dependency sets and scheme-specific pruning use `coredrp-v1-settlement-safety.md` plus the bound resolved settlement-scheme/adjustment policy digest.

## 5. Temporal policy and quarantine

Completeness mode remains temporal audited state rather than immutable scope-contract state. Membership/mode lifecycle, deterministic staging sender set, safety origin and correction semantics are in `coredrp-v1-temporal-policy.md`.

Payout-significant quarantine state transitions and corrected-effect evidence are in `coredrp-v1-quarantine-safety.md` and the ADMIN action registry. `QUARANTINE_RECONCILIATION` field 11 MUST name an authority digest allocated by `coredrp-v1-validator-authorities.md`; receiver-local authority digests are forbidden.

## 6. Sorting/text rules

Profile IDs, coin IDs, network IDs, settlement/adjustment policy IDs/keys/values and commitment-class IDs are exact ASCII where their registries require ASCII. Canonical sorts are raw-byte sorts. Duplicate entries are rejected before hashing.

## 7. Epoch contract binding and migration

The outer epoch contract-binding grammar remains Section 11 of the canonical specification. Every numeric value is validated before sorting/deduplication/hashing.

A successor epoch with changed Mining or Miningcore scope-contract digest is subject to `coredrp-v1-profile-transitions.md`; the closed-old-state barrier is exactly its `NoLiveDependencies` predicate unless an explicit migration/new scope identity is used.
