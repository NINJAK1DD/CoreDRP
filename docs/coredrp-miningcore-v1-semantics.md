# CoreDRP Miningcore Profile 1.1 — Normative Semantics

**Status:** Draft 0.6 profile-freeze normative registry  
**Profile ID:** `coredrp.miningcore`  
**Profile version:** 1.1  
**Minimum Core:** 1.1  
**Required Mining profile:** `coredrp.mining` 1.1 on every projection scope

This registry is incorporated by `CoreDRP-1-SPEC-0.6.md`. Reference tooling implements these rules but is lower authority.

## 1. Event ownership and placement

For a non-empty Mining scope:

- `0x0200 MiningcoreAccountingShareEvent`: lane 0;
- `0x0201 BitcoinDirectCoinbaseCandidate`: lane 1;
- `0x0202 CandidateStateUpdate`: lane 1.

Each requires the exact selected Mining 1.1 and Miningcore 1.1 scope contracts required by this registry.

For `MiningcoreAccountingShareEvent`, each projection carries its own `scope`. The primary projection scope MUST equal the enclosing Core `Event.scope`. A paired auxiliary projection MUST use a different scope. Every projection scope independently requires exact Mining 1.1 and Miningcore 1.1 scope-contract selections in the epoch binding.

## 2. Frozen semantic-contract allocations

Unknown values MUST fail scope-contract negotiation with `SEMANTIC_CONTRACT_MISMATCH`.

| Field | Allowed value | Meaning |
|---|---:|---|
| `accounting_schema_version` | 2 | scoped accounting projection validity in Section 3 |
| `persistence_schema_version` | 1 | atomic PostgreSQL receiver/effect persistence in Section 11 |
| `direct_candidate_validation_version` | 2 | Bitcoin validation in Sections 6 and 10 plus bound network policy |
| `settlement_policy_version` | 2 | scheme/policy/pruning/quarantine rules in Sections 8–9 and incorporated registries |

All other values are unallocated for Miningcore Profile 1.1 and MUST be rejected.

## 3. Accounting projection validity

`MiningcoreAccountingShareEvent.primary` is REQUIRED.

Primary role MUST be `SINGLE` or `PARENT`; `UNSPECIFIED` and `AUXILIARY` are invalid as primary roles.

- `SINGLE` requires `paired` absent.
- `PARENT` requires `paired` present.
- A present paired projection MUST have role `AUXILIARY`.

Every projection MUST:

- carry non-empty canonical Mining scope bytes;
- contain a `MiningShareEvent` valid under the Mining semantics registry for that projection scope;
- set `preserve_created = true`;
- target a scope present in the epoch binding with exact Mining and Miningcore contracts.

For a SINGLE projection, `primary.scope == enclosing Event.scope`.

For PARENT/AUXILIARY pairs:

- `primary.scope == enclosing Event.scope`;
- `paired.scope != primary.scope`;
- both `accounting_id` fields are REQUIRED, non-empty, and MUST be byte-for-byte identical because they identify one accepted merged-mining proof projected to two chains;
- worker, user agent, source IP, source/cluster source, session ID, `created_unix_ms`, and `achieved_share_difficulty` MUST match exactly;
- miner MAY differ because the parent and auxiliary chains may use different payout addresses;
- block height, assigned difficulty, actual difficulty, network difficulty, candidate fields, reward basis, and PPS liability MAY differ where chain-specific;
- no third/nested projection is representable.

This deliberately matches the Miningcore accounting model: one proof identity, distinct pools/scopes, chain-specific miner identity, and exact equality for the shared proof/session fields.

`accounting_id`, when present on SINGLE, MUST be non-empty.

`reward_basis_satoshis`, when present, MUST be strictly positive for identified ordinary accounting projections.

`pps_calculated_amount`, when present, MUST satisfy the exact Mining `Decimal38Scale24` grammar, be strictly positive, and requires a non-empty `accounting_id`.

`block_only = true` requires `block_record_emitted = true` and `statistical_record_emitted = false`. `statistical_record_emitted = true` requires `block_only = false`.

Violations are `SEMANTIC_PAYLOAD_INVALID`.

## 4. Integration field limits

Post-parse limits:

| Field | Limit |
|---|---:|
| direct recipients | 256 entries |
| consensus commitment declarations | 64 entries |
| projection scope | 64 ASCII bytes and Mining scope grammar |
| address metadata | 128 UTF-8 bytes |
| scriptPubKey | 10,000 bytes |
| miner | 256 UTF-8 bytes |
| worker | 128 UTF-8 bytes |

Monetary satoshi values MUST reject negative values and arithmetic overflow.

## 5. Candidate identity and representation

`candidate_id` is exactly 16 RFC 9562 UUID bytes and MUST be UUIDv7 for a newly prepared candidate. Candidate ID is unique within `(scope, selected Miningcore contract)`.

Bitcoin hashes in candidate messages are 32 bytes in canonical RPC/display byte order. `serialized_block` is exact consensus serialization. Script bytes are authoritative; optional address strings are display/audit metadata and MUST map back to the exact script on the network selected by the Mining contract.

The serialized-block cap is the minimum of the Core hard cap, negotiated payload cap, and 4,000,000-byte Miningcore candidate cap.

## 6. Bitcoin direct-candidate validation

Before durable acceptance, a consensus-compatible parser or equivalent verified implementation MUST:

1. parse the entire block with no malformed or trailing bytes;
2. compute `SHA256d(header80)`, reverse to RPC/display order, and match `block_hash`;
3. parse every transaction and require transaction zero to be coinbase;
4. compute the coinbase non-witness txid and match `coinbase_txid`;
5. reject any duplicate txid anywhere in the block before accepting Merkle evidence;
6. compute the complete txid Merkle root using Bitcoin duplicate-last pairing and match the header;
7. apply BIP34 using the receiver-side network policy bound by the Miningcore semantic contract; when active, require the minimally encoded first CScriptNum item to equal `block_height`;
8. when witness serialization exists, validate the highest-index BIP141 witness commitment using coinbase wtxid = zero, a 32-byte coinbase witness reserved value, and `SHA256d(witness_root || reserved_value)`;
9. require every BIP141-pattern coinbase output to be explicitly declared exactly once in `consensus_commitments`;
10. validate each declared consensus commitment as an exact zero-value `(output_index, script_pub_key)` and classify it under the allow-list contained in the bound network policy; sender declaration is evidence, not authority to create a class;
11. verify miner output and declared direct-recipient multiset exactly;
12. consume every coinbase output exactly once as miner/direct recipient or an allowed declared consensus commitment;
13. require `gross_reward_satoshis` to equal the sum of all coinbase outputs and reject negative/overflow/contradictory classifications.

Unknown network policy, activation parameters, or commitment classes fail closed.

## 7. Candidate submission-state graph

New candidate state is `PREPARED`.

Allowed transitions:

- `PREPARED -> SUBMITTED_UNCERTAIN | OBSERVED_ACTIVE | REJECTED | QUARANTINED`;
- `SUBMITTED_UNCERTAIN -> SUBMITTED_UNCERTAIN | OBSERVED_ACTIVE | REJECTED | QUARANTINED`;
- `REJECTED -> OBSERVED_ACTIVE` only on later authoritative chain proof; otherwise it is terminal except quarantine;
- `OBSERVED_ACTIVE -> QUARANTINED` only for evidence investigation;
- `QUARANTINED` is terminal except an explicit audited reconciliation outside this state graph.

`CandidateStateUpdate` MUST reference an existing durable candidate in the same scope. Unknown or cross-scope candidate is `INVALID_STATE_TRANSITION`.

`submission_attempts` never decreases. `definitive_misses <= submission_attempts`. `last_attempt_unix_ms` is absent iff attempts are zero; when attempts increase it MUST be present and nondecreasing. State and counters are validated transactionally against the stored candidate.

## 8. Settlement and retention scheme matrix

This section, `coredrp-v1-settlement-safety.md`, and `coredrp-v1-settlement-scheme-policies.md` are jointly normative. Mining `payout_scheme` selects exactly one row and the Miningcore scope contract binds the exact scheme-policy digest.

| Scheme | Settlement rule | Deletion/retention rule |
|---|---|---|
| PPLNS | requires `SettlementSafe` for the exact window derived from bound `factor` | use settlement-specific prune safety in the settlement registry; retain all evidence referenced by live/unsettled windows |
| PPLNSBF | requires `SettlementSafe` for the exact window derived from bound `factor` and block-finder percentage | use settlement-specific prune safety; retain all evidence referenced by live/unsettled windows |
| PROP | requires `SettlementSafe` from round start through settlement boundary | use settlement-specific prune safety |
| PPS | payout is not remote-completeness fence gated; each accepted share must already have durable accounting/idempotency effect | delete only after accounting is durable, retry/idempotency dependency is retired, and no live proof/audit dependency remains |
| CUSTODIAL_SOLO | payout is not remote-completeness fence gated | winning share and block/settlement evidence retained through settlement finality; non-winning shares may follow configured retention when no evidence dependency remains |
| DIRECT_SOLO | consensus submission is never recorder/completeness gated | exact candidate/submission/settlement evidence retained through local finality; `submitblock` never waits on recorder state |

A `SETTLE_WITHOUT_FENCE_OVERRIDE` may permit one named settlement but does not turn the settlement into `SettlementSafe`, does not advance `PayoutSafeThrough`, and does not relax evidence retention for audit.

## 9. Payout-significant quarantine

A quarantined event is payout-significant when it is a lane-0 Mining share or Miningcore accounting event, or when an incorporated settlement registry marks its effect as a dependency of an unsettled financial result.

Payout-significant quarantine has the same safety lifecycle as a completeness gap:

- `UNRESOLVED`: event is durably quarantined/ACKed but its ordinary financial effect is absent; every intersecting `SettlementSafe` decision is false and the contiguous frontier is capped at the earliest affected point;
- `RESOLVED_RECONCILED`: a versioned validator/profile correction or verified reconciliation has produced the required durable financial effect without changing immutable Core history; the affected settlement may be re-evaluated;
- `RESOLVED_WAIVED`: operator accepts missing financial effect for audit/operations; it never becomes `SettlementSafe`, never advances `PayoutSafeThrough`, and does not authorize destructive deletion of its audit record.

`QUARANTINE_AND_ADVANCE` by itself creates/retains `UNRESOLVED` financial uncertainty. It MUST NOT manufacture completeness or settlement safety.

## 10. Network and settlement policy binding

Miningcore Profile 1.1 uses `direct_candidate_validation_version = 2` and requires both:

- `bitcoin_network_policy_digest32`, recomputed from `coredrp-v1-bitcoin-network-policies.md` using the Mining-selected `network_id`;
- `settlement_scheme_policy_digest32`, recomputed from `coredrp-v1-settlement-scheme-policies.md` using the Mining-selected `payout_scheme` and effective Miningcore payout configuration.

Two receivers MUST NOT select the same Miningcore scope-contract digest while using different Bitcoin validation policy or different settlement-window/configuration parameters.

The `synthetic-regtest` network policy is test-only and MUST NOT be selected by a production Mining scope.

## 11. Direct submission independence and PostgreSQL atomicity

The submitting edge persists exact candidate/settlement evidence locally before invoking `submitblock`. Recorder, critical-lane, clock, completeness, or payout-fence failure MUST NOT delay local consensus submission.

For a received batch, state-dependent profile validation, referential checks, application effects, candidate/accounting records, receiver stream head, checkpoint evidence, quarantine/gap state, and financial proof dependencies commit in the same durable transaction. A semantic failure rolls back the entire current batch and emits no ACK.
