# CoreDRP Miningcore Share-Difficulty Adjustment Policy Registry — Draft 0.6

**Status:** normative Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md`. It binds the exact transformation applied to accepted share difficulty before any settlement scheme computes score/window dependencies.

## 1. Canonical digest

`share_difficulty_adjustment_policy_digest32 = SHA256(share_difficulty_adjustment_policy_source)`.

The source grammar is:

`uint16_be(1)`
`|| uint16_be(policy_id_len) || policy_id_ascii`
`|| uint16_be(parameter_count)`
`|| repeated parameters sorted by raw ASCII key`.

Each parameter is:

`uint16_be(key_len) || key_ascii || uint16_be(value_len) || value_ascii`.

Policy IDs, keys and values are exact ASCII. Duplicate keys, unknown keys, locale formatting, exponent notation, NaN, infinity, leading plus, unnecessary leading integer zero, and unnecessary trailing fractional zero are invalid before hashing.

Every decimal parameter uses the Mining `Decimal38Scale24` canonical grammar and any positive-only parameter MUST reject zero.

The digest MUST represent the **resolved effective adjustment behavior used by the running Miningcore payout handler**. It MUST NOT encode a guessed upstream default or an operator's unresolved configuration text.

If an integration cannot map its effective `AdjustShareDifficulty` behavior to one of the policies below, Miningcore Profile 1.1 negotiation fails closed with `SEMANTIC_CONTRACT_MISMATCH`. A future profile revision may allocate additional adjustment policies.

## 2. Profile 1.1 adjustment policies

### `identity`

`parameter_count = 0`.

For every accepted share difficulty `D`:

`AdjustedDifficulty(D) = D`.

### `constant_multiplier`

Required parameter:

- `multiplier`: positive `Decimal38Scale24` canonical decimal.

For every accepted share difficulty `D`:

`AdjustedDifficulty(D) = D * multiplier`.

The multiplication is performed in the settlement implementation's exact numeric domain, and the multiplier's canonical decimal value is part of the contract. Overflow/invalid numeric conversion fails settlement evaluation closed; it MUST NOT silently fall back to identity.

No other parameters are valid.

## 3. Reference policies

### Identity

Source hex:

`000100086964656e746974790000`

SHA-256:

`512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf`

### Constant multiplier 256

Source hex:

`00010013636f6e7374616e745f6d756c7469706c6965720001000a6d756c7469706c6965720003323536`

SHA-256:

`99081a8e8af2a531e8eff832b128badea32ed188e59245e1a9845942480b1b34`

## 4. Settlement use

PPLNS/PPLNSBF scoring/window calculations MUST use `AdjustedDifficulty` from the policy whose digest is bound by the selected settlement-scheme policy. Receiver-local or application-local adjustment behavior MUST NOT replace it.

PROP/PPS/SOLO integrations still bind an adjustment-policy digest so the selected Miningcore scope contract completely records the active payout handler behavior; Profile 1.1 uses `identity` when no adjustment exists.
