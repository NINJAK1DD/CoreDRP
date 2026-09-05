# CoreDRP Miningcore Settlement-Scheme Policy Registry — Draft 0.6

**Status:** normative Miningcore Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md`. It binds payout-scheme parameters and share-difficulty adjustment behavior that change settlement dependency sets into the Miningcore scope semantic contract.

## 1. Canonical digest

`settlement_scheme_policy_digest32 = SHA256(settlement_scheme_policy_source)`.

The Profile 1.1 source grammar is version 3:

`uint16_be(3)`
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

### PPS (`payout_scheme = 4`)

Required resolved parameter: `retained_reward_percentage`, a positive canonical decimal in `(0,100]`. Resolve it as exactly `100 - sum(positive effective reward-recipient percentages)` using exact decimal rationals. Negative/non-finite/invalid configured percentages fail negotiation rather than being silently dropped. The result must be representable in `Decimal38Scale24`; a nonpositive result fails negotiation. Missing effective configuration is not zero fees. No other PPS parameter is valid. Grammar version 3 binds the `PPSLiabilityV1` algorithm and Bitcoin-family eligibility below.

### PROP, CUSTODIAL_SOLO, DIRECT_SOLO (`payout_scheme = 3,5,6`)

Profile 1.1 defines no generic settlement-window parameters here, therefore `parameter_count = 0`. The adjustment-policy digest remains present. Any later parameter that changes a settlement dependency set requires a new versioned policy definition and changes this digest.

## 3. Reference policies

All reference policies below use adjustment policy `identity` with digest:

`512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf`

### PPLNS factor 2

Source hex:

`000301512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf00010006666163746f72000132`

SHA-256:

`779cd6c162373a543660f304d11eab7b19faace462be46886833fd2fa025276a`

### PPLNSBF factor 2, block-finder percentage 5

Source hex (note ASCII-key ordering):

`000302512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf00020017626c6f636b5f66696e6465725f70657263656e746167650001350006666163746f72000132`

SHA-256:

`174a892aa504af2e2bdd27357c3e0206aa0ed6e80ca0476a669ed85234c78feb`

Boundary digests are published in the Draft 0.6 conformance corpus for `block_finder_percentage = 0` and the largest 24-scale value below 100. The corpus also rejects `2.0`, `+2` and `02` as non-canonical decimal encodings.

## 4. Settlement proof use

Every `SettlementSafe` proof records both `settlement_scheme_policy_digest32` and the embedded `share_difficulty_adjustment_policy_digest32`. Scheme-specific evidence windows MUST be derived from the resolved parameters and adjusted difficulties committed by those digests; receiver-local payout configuration or payout-handler behavior MUST NOT silently replace them.

## 5. PPLNSScoreV1 and PPLNSBFScoreV1

These algorithms are selected by settlement policy source version 3 and Miningcore `settlement_policy_version = 5`. They deliberately replace host `decimal` casts and arithmetic; an unmodified Miningcore payout handler is not conforming.

For each eligible accepted accounting projection, obtain positive finite binary64 adjusted assigned difficulty `D` from the bound adjustment policy and positive finite binary64 network difficulty `N`. Compute `q = roundTiesToEven_binary64(exact(D) / exact(N))` with exactly one IEEE-754 binary64 round-to-nearest, ties-to-even, including gradual underflow (no flush-to-zero). There is no intermediate rounding. Overflow/non-finite result fails the settlement closed; positive input rounding to zero also fails closed rather than disappearing from the dependency set. `score` is the exact rational represented by q's bits. Conversion to the accumulation domain is lossless numerator/denominator conversion, with unbounded integer precision. No binary64-to-host-decimal cast or 15/17-digit formatting is allowed.

Let `F` be the exact positive decimal rational bound by `factor`. Select only eligible shares at/before the settlement boundary from a consistent snapshot. Visit the canonical Mining Section 9 full tuple in **descending** order (reverse every component): `(event_time_unix_ms, sender_uuid_rfc9562, sequence, relay_event_uuid_rfc9562)`. The accepted accounting UUID is unique per scope; duplicate effects are not counted twice. A repeated full tuple with conflicting evidence is corruption and fails closed.

Initialize exact rational `total=0`. While `total < F`, take the next share with exact score `s`; set `contribution=min(s,F-total)` and `fraction=contribution/s`; retain this share and its fraction in the evidence; set `total=total+contribution` exactly. Stop immediately at `total == F`; do not consume an older share. Equality is exact, with no epsilon. The final boundary share may be partial. If complete available history reaches the scope origin with `total < F`, the window contains all eligible available shares; this is an underfilled window, not permission to cross an incompatible contract or unknown history. Missing required history prevents `SettlementSafe`. Exhausting memory/precision capacity fails closed with no financial commit or evidence deletion; saturation, wrap and approximate fallback are forbidden.

PPLNSBF uses the identical window/cutoff. Its bound block-finder percentage does not change the score or factor: it reserves that exact percentage of the final distributable reward for the proven block finder, and apportions the remainder by window contributions. The finder evidence remains a dependency even when outside the score window. PPLNS apportions the entire distributable reward by contributions. For either scheme, the final distributable reward and its recipient deductions MUST be retained as immutable settlement inputs, not re-read from live configuration. Zero total produces no share allocation and MUST NOT divide by zero.

For a distributable amount `R` in `Decimal38Scale24`, compute each per-accounting contribution amount using exact rationals (`R * contribution / total`, after the PPLNSBF finder reserve). Truncate each per-accounting amount toward zero to 24 fractional digits once; retain zero contributions too. PPLNSBF finder allocation is a separate amount added to that finder's accounting identity before this one truncation (or its own identity if outside the window). Aggregate the resulting canonical per-accounting amounts by exact miner bytes for the balance credit. Retain the nonnegative remainder as undistributed settlement dust; do not silently assign it to one miner. No rounding or database decimal overflow may change a dependency window; unrepresentable final amounts fail closed.

### 5.1 Full-tuple pagination

Every page MUST use the same immutable snapshot and the full tuple above as a strict exclusive cursor, with exactly the same byte-wise UUID ordering as the sort. The next descending page selects tuples `< last_tuple`; a timestamp-only predicate is forbidden. Persist all cursor components, including sender and relay UUIDs, in RFC 9562 order, never .NET mixed-endian or database-specific UUID collation order. `ReadSharesBeforeAsync` with `ORDER BY created DESC` and a timestamp-only cursor MUST NOT be reused unchanged by a CoreDRP settlement implementation. Page size must not change selected identities, fractions, amount allocations or evidence interval.

## 6. PPSLiabilityV1

PPSLiabilityV1 currently allocates Bitcoin-family eligibility to exact Mining `coin_id = "bitcoin"` only, with a Bitcoin network policy allocated in `coredrp-v1-bitcoin-network-policies.md` for that scope's exact network ID. The test-only synthetic policy remains non-production. Unknown coin-family mapping or network policy fails negotiation closed; neither a ticker nor receiver-local inference establishes eligibility.

Treat positive `reward_basis_satoshis` as an exact integer, positive finite **assigned** share difficulty and network difficulty as their exact binary64 rationals, and the bound retained percentage as its exact decimal rational. Achieved difficulty and `AdjustShareDifficulty` do not enter PPSLiabilityV1. Compute exactly:

`liability = reward_basis_satoshis / 100000000 * assigned_difficulty / network_difficulty * retained_reward_percentage / 100`.

Truncate toward zero to 24 decimal fractional places once (`floor(liability * 10^24) / 10^24` for positive liability). Encode canonical `Decimal38Scale24`, reject zero or overflow. Intermediate host binary64 division, decimal casts/rounding and live fee configuration are forbidden. Compare the canonical embedded amount byte-for-byte to this result before accepting an effect. Fees are applied exactly once; downstream recording MUST NOT deduct current recipient percentages again. Replay, quarantine revalidation and settlement of an accepted liability use its immutable accepting contract and input evidence. A fee change requires a new bound digest and financial migration barrier, never reinterpretation of an existing liability.

## 7. PROPScoreV1 and PROPAllocationV1

PROP selects every eligible accounting projection in the exact durable round interval `[round_start,block_boundary]` from one immutable snapshot under the accepting contracts. It uses the same positive finite adjusted difficulty, one correctly rounded binary64 quotient, lossless rational conversion, error handling and canonical full-tuple order as PPLNSScoreV1. There is no factor or partial boundary: every selected share has contribution equal to its score and fraction exactly 1. Duplicate accounting identities fail closed. Apply the same exact rational reward allocation, per-accounting scale-24 truncation, per-miner aggregation and retained dust rules with no finder reserve. An empty/zero-total round cannot produce a share allocation and must retain its unresolved settlement evidence.

## 8. Block-finder linkage

Before allocating a PPLNSBF reserve, the settlement MUST bind its exact accepted block hash and height to exactly one accepted winning accounting projection with `share.is_block_candidate=true`, matching candidate hash/height and the same scope/contract. Its accounting UUID and exact miner bytes are the finder identity, even outside the score window. An application `block.Miner` string alone is insufficient. Missing, conflicting or ambiguous linkage fails settlement closed and retains evidence; never invent a new accounting UUID for a balance row. Retain that source payload and its Core identity with the audit bundle. If the finder is also in the window, combine its finder and window amounts before the single truncation.
