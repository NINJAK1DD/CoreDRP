# CoreDRP Miningcore Settlement-Scheme Policy Registry — Draft 0.6

**Status:** normative Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md`. It binds payout-scheme parameters that change settlement dependency sets into the Miningcore scope semantic contract.

## 1. Canonical digest

`settlement_scheme_policy_digest32 = SHA256(settlement_scheme_policy_source)`.

The source grammar is:

`uint16_be(1)`
`|| uint8(payout_scheme)`
`|| uint16_be(parameter_count)`
`|| repeated parameters sorted by raw ASCII key`.

Each parameter is:

`uint16_be(key_len) || key_ascii || uint16_be(value_len) || value_ascii`.

Keys and values are exact ASCII. Duplicate keys, unknown keys, non-canonical decimal values, locale formatting, exponent notation, NaN and infinity are invalid before hashing. Decimal values use the shortest non-negative base-10 representation with no leading plus, no unnecessary leading integer zero and no trailing fractional zero.

The `payout_scheme` MUST equal the value selected by the Mining scope contract. Unknown scheme/parameter combinations fail negotiation with `SEMANTIC_CONTRACT_MISMATCH`.

## 2. Scheme parameters

### PPLNS (`payout_scheme = 1`)

Required parameters:

- `factor`: positive canonical decimal. It is the exact score/window factor used by the reference Miningcore `PPLNSPaymentScheme`. If omitted by application configuration, CoreDRP canonicalizes the Miningcore default as `2` before hashing.

No other parameters are valid.

### PPLNSBF (`payout_scheme = 2`)

Required parameters:

- `factor`: positive canonical decimal; Miningcore default `2`;
- `block_finder_percentage`: canonical decimal in `[0,100)`; Miningcore default `5`.

No other parameters are valid.

### PROP, PPS, CUSTODIAL_SOLO, DIRECT_SOLO (`payout_scheme = 3..6`)

Profile 1.1 defines no generic settlement-window parameters here, therefore `parameter_count = 0`. Any later parameter that changes a settlement dependency set requires a new versioned policy definition and changes this digest.

## 3. Reference PPLNS policy

For `payout_scheme = 1`, `factor = 2`:

source hex:

`00010100010006666163746f72000132`

SHA-256:

`8218444045964b49331e0e7e74590574ac552f522aa482b2aa60d7fca2637725`

## 4. Settlement proof use

Every `SettlementSafe` proof records the selected `settlement_scheme_policy_digest32`. Scheme-specific evidence windows MUST be derived from the parameters committed by that digest; receiver-local payout configuration MUST NOT silently replace them.
