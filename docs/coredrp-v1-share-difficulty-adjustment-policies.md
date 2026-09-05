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

For every accepted finite positive binary64 share difficulty `D`:

`AdjustedDifficulty(D) = D` with the exact original binary64 bit pattern.

### `constant_multiplier`

Required parameter:

- `multiplier`: positive `Decimal38Scale24` canonical decimal.

The arithmetic domain is **fully specified** and MUST NOT depend on the host language's decimal, binary64, extended-precision, FMA, or arbitrary-precision defaults.

Let the accepted share difficulty `D` be the exact finite positive IEEE-754 binary64 value represented by its 64 bits. Convert those bits to the exact rational value `D_exact` defined by IEEE-754 (including subnormal values if an implementation accepts them as an input difficulty). Parse canonical decimal multiplier text containing integer digits `I` and `s` fractional digits as the exact rational `M_exact = integer(I_without_point) / 10^s`.

Compute the mathematical rational product:

`P_exact = D_exact * M_exact`.

Then convert **once** from `P_exact` to IEEE-754 binary64 using round-to-nearest, ties-to-even (IEEE-754 `roundTiesToEven`). No intermediate binary64 rounding of the decimal multiplier and no multiply of two already-rounded binary64 operands is conforming.

The resulting finite positive binary64 value is `AdjustedDifficulty(D)`. If correct rounding would produce positive infinity, zero by underflow, NaN, or any non-positive value, settlement evaluation fails closed and the affected settlement is not safe/evaluable under this policy version. Implementations MUST NOT clamp, saturate, substitute identity, or use a wider result without the final binary64 rounding.

This algorithm makes the output bit pattern identical across implementations. Conformance vectors include a case where ordinary host-language `double * double` produces a result one ULP different from the required exact-rational single-round result.

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

The policy digest is unchanged by this arithmetic clarification because the arithmetic algorithm is part of the fixed Profile 1.1 meaning of policy ID `constant_multiplier`; a different rounding algorithm requires a new policy ID/profile revision.

## 4. Settlement use

PPLNS/PPLNSBF scoring/window calculations MUST use the binary64 `AdjustedDifficulty` bit pattern produced by Section 2 from the policy whose digest is bound by the selected settlement-scheme policy. Receiver-local or application-local adjustment behavior MUST NOT replace it.

When a settlement accumulates multiple adjusted difficulty values, any additional score accumulation/arithmetic required by the scheme MUST follow the scheme's own frozen arithmetic rules; the adjustment policy defines only the per-share transformation above.
