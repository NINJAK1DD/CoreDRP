# CoreDRP Miningcore Bitcoin Network Policy Registry — Draft 0.6 Freeze Completion

This registry is normative for Miningcore Profile 1.1 direct Bitcoin candidate validation. It binds receiver-side network validation policy into the Miningcore scope semantic contract so two receivers cannot negotiate the same scope digest while validating different consensus evidence.

## Canonical policy digest

For a selected Mining scope `network_id`, define:

`bitcoin_network_policy_source = uint16_be(1) || uint16_be(network_id_len) || network_id_ascii || genesis_block_hash_rpc_order_32 || uint64_be(bip34_activation_height) || uint16_be(direct_candidate_validation_version) || uint16_be(commitment_class_count) || repeated(sorted commitment class)`

Each sorted commitment class is:

`uint16_be(class_id_ascii_len) || class_id_ascii`.

Class IDs are exact ASCII and sorted lexicographically by raw bytes. Duplicate class IDs are invalid before hashing.

`bitcoin_network_policy_digest = SHA256(bitcoin_network_policy_source)`.

The Miningcore Profile 1.1 semantic contract includes this exact 32-byte digest.

## Required policy fields

Each supported network policy MUST define:

- exact `network_id` matching the Mining scope contract;
- canonical genesis block hash in RPC/display byte order;
- BIP34 activation height;
- direct-candidate validation version;
- closed allow-list of recognized zero-valued consensus commitment classes.

Unknown network policy fails closed.

## Built-in reference policies

### `mainnet`

- production use: permitted when selected by the Mining contract;
- genesis block hash: `000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f`
- BIP34 activation height: `227931`
- direct-candidate validation version: `2`
- allowed commitment classes: `BIP141`
- source hex: `000100076d61696e6e6574000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f0000000000037a5b000200010006424950313431`
- SHA-256: `0f477ab81c34cfc8ec31e146bd86f6760554e7d803d9522c7b0e0e818f412e3a`

### `synthetic-regtest` conformance policy

This policy exists **only** for deterministic repository conformance. It is not a Bitcoin Core regtest identity and **MUST NOT be selected by any production Mining scope or production receiver configuration**.

- production use: forbidden;
- genesis/network identity hash: 32 bytes of `0x11`;
- BIP34 activation height: `0`;
- direct-candidate validation version: `2`;
- allowed commitment classes: `BIP141`;
- source hex: `0001001173796e7468657469632d7265677465737411111111111111111111111111111111111111111111111111111111111111110000000000000000000200010006424950313431`;
- SHA-256: `16e8587c49b21834ab025cc463ac576b9f4301428e9530303b6bdd779b7394c4`.

A production configuration that names `synthetic-regtest` is invalid even if its digest matches this registry.

## Commitment classes

`BIP141` classifies an exact zero-value coinbase output whose script begins `OP_RETURN 0x24 aa21a9ed <32-byte commitment>` and satisfies the complete BIP141 validation rules in the Miningcore semantics registry.

Additional AuxPoW, sidechain, or chain-specific commitment classes require a new versioned policy definition and therefore change `bitcoin_network_policy_digest`. A sender declaration by itself can never authorize a class absent from this registry/policy.
