# CoreDRP Miningcore Settlement-Scheme Policy Registry — Draft 0.6

**Status:** normative Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md`. It binds payout-scheme parameters and share-difficulty adjustment behavior that change settlement dependency sets into the Miningcore scope semantic contract.

## 1. Canonical digest

`settlement_scheme_policy_digest32 = SHA256(settlement_scheme_policy_source)`.

The Profile 1.1 source grammar is version 2:

`uint16_be(2)`
`|| uint8(payout_scheme)`
`|| share_difficulty_adjustment_policy_digest32`
`|| uint16_be(parameter_count)`
`|| repeated parameters sorted by raw ASCII key`.

`share_difficulty_adjustment_policy_digest32` is exactly 32 bytes and is recomputed from `coredrp-v1-share-difficulty-adjustment-policies.md` using the **resolved effective** behavior of the running Miningcore payout handler.

Each scheme parameter is:

`uint16_be(key_len) || key_ascii || uint16_be(value_len) || value_ascii`.

Keys and values are exact ASCII. Duplicate keys, unknown keys, non-canonical decimal values, locale formatting, exponent notation, NaN and infinity are invalid before hashing. Decimal values use the Mining `Decimal38Scale24` canonical grammar; positive-only parameters reject zero.

The `payout_scheme` MUST equal the value selected by the Mining scope contract. Unknown scheme/parameter/adjustment combinations fail negotiation with `SEMANTIC_CONTRACT_MISMATCH`.

### 1.1 Effective-value rule

Every parameter in this digest is the value the running settlement implementation will actually use **after application configuration, implementation defaults and coin-family resolution have been applied**.

CoreDRP MUST NOT substitute or canonicalize an assumed Miningcore default when the application omitted a configuration value. If the integration cannot observe the resolved effective value, negotiation fails closed. A future upstream default change therefore changes the resolved digest automatically instead of silently preserving an obsolete contract belief.

The same rule applies to `AdjustShareDifficulty`: its resolved effective policy digest is bound directly rather than inferred from coin family or code version.

## 2. Scheme parameters

### PPLNS (`payout_scheme = 1`)

Required resolved parameter:

- `factor`: positive canonical decimal. It is the exact factor used by the running Miningcore PPLNS settlement implementation.

No other scheme parameters are valid.

### PPLNSBF (`payout_scheme = 2`)

Required resolved parameters:

- `factor`: positive canonical decimal;
- `block_finder_percentage`: canonical decimal in `[0,100)`.

No other scheme parameters are valid.

The canonical key order is raw ASCII, therefore `block_finder_percentage` is encoded before `factor` regardless of configuration/declaration order.

### PROP, PPS, CUSTODIAL_SOLO, DIRECT_SOLO (`payout_scheme = 3..6`)

Profile 1.1 defines no generic settlement-window parameters here, therefore `parameter_count = 0`. The adjustment-policy digest remains present. Any later parameter that changes a settlement dependency set requires a new versioned policy definition and changes this digest.

## 3. Reference policies

All reference policies below use adjustment policy `identity` with digest:

`512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf`

### PPLNS factor 2

Source hex:

`000201512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf00010006666163746f72000132`

SHA-256:

`7fab911a63b4a76576088f1ef27337132e0ae7fb55e040cd7df119ed66fa89e0`

### PPLNSBF factor 2, block-finder percentage 5

Source hex (note ASCII-key ordering):

`000202512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf00020017626c6f636b5f66696e6465725f70657263656e746167650001350006666163746f72000132`

SHA-256:

`257845e00475f031c19fd217a4fa86a5fe3c8aa190cf92ac9358377c4445e059`

Boundary digests are published in the Draft 0.6 conformance corpus for `block_finder_percentage = 0` and the largest 24-scale value below 100. The corpus also rejects `2.0`, `+2` and `02` as non-canonical decimal encodings.

## 4. Settlement proof use

Every `SettlementSafe` proof records both `settlement_scheme_policy_digest32` and the embedded `share_difficulty_adjustment_policy_digest32`. Scheme-specific evidence windows MUST be derived from the resolved parameters and adjusted difficulties committed by those digests; receiver-local payout configuration or payout-handler behavior MUST NOT silently replace them.
