# CoreDRP Miningcore Profile 1.1 — Normative Semantics

**Status:** Draft 0.5 normative registry  
**Profile ID:** `coredrp.miningcore`  
**Profile version:** 1.1  
**Minimum Core:** 1.1  
**Required Mining profile:** `coredrp.mining` 1.1 on the same scope

This registry is incorporated by `CoreDRP-1-SPEC-0.5.md`. Reference tooling implements these rules but is lower authority.

## 1. Event ownership and placement

For a non-empty Mining scope:

- `0x0200 MiningcoreAccountingShareEvent`: lane 0;
- `0x0201 BitcoinDirectCoinbaseCandidate`: lane 1;
- `0x0202 CandidateStateUpdate`: lane 1.

Each requires both the exact selected Mining 1.1 and Miningcore 1.1 scope contracts in the epoch binding.

## 2. Accounting projection validity

`MiningcoreAccountingShareEvent.primary` is REQUIRED.

Primary role MUST be `SINGLE` or `PARENT`; `UNSPECIFIED` and `AUXILIARY` are invalid as primary roles.

- `SINGLE` requires `paired` absent.
- `PARENT` requires `paired` present.
- A present paired projection MUST have role `AUXILIARY`.

Every projection MUST contain a MiningShareEvent valid under the Mining semantics registry and MUST set `preserve_created = true`.

For PARENT/AUXILIARY pairs, miner, worker, session ID, and `created_unix_ms` MUST match exactly. Chain-specific height, difficulty and candidate fields MAY differ.

`accounting_id`, when present, MUST be non-empty. When both primary and paired accounting IDs are present they MUST differ.

`reward_basis_satoshis`, when present, MUST be non-negative.

`pps_calculated_amount`, when present, MUST satisfy the exact Mining `Decimal38Scale24` grammar and requires a non-empty `accounting_id`.

`block_only = true` requires `block_record_emitted = true` and `statistical_record_emitted = false`. `statistical_record_emitted = true` requires `block_only = false`.

Violations are `SEMANTIC_PAYLOAD_INVALID`.

## 3. Integration field limits

Post-parse limits:

| Field | Limit |
|---|---:|
| direct recipients | 256 entries |
| address metadata | 128 UTF-8 bytes |
| scriptPubKey | 10,000 bytes |
| miner | 256 UTF-8 bytes |
| worker | 128 UTF-8 bytes |

Monetary satoshi values MUST reject negative values and arithmetic overflow.

## 4. Candidate identity and representation

`candidate_id` is exactly 16 RFC 9562 UUID bytes and MUST be UUIDv7 for a newly prepared candidate. Candidate ID is unique within `(scope, selected Miningcore contract)`.

Bitcoin hashes in candidate messages are 32 bytes in canonical RPC/display byte order. `serialized_block` is exact consensus serialization. Script bytes are authoritative; optional address strings are display/audit metadata and MUST map back to the exact script on the network selected by the Mining contract.

The serialized-block cap is 4,000,000 bytes or a stricter negotiated/profile cap.

## 5. Bitcoin direct-candidate validation

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

## 6. Candidate submission-state graph

New candidate state is `PREPARED`.

Allowed transitions:

- `PREPARED -> SUBMITTED_UNCERTAIN | OBSERVED_ACTIVE | REJECTED | QUARANTINED`;
- `SUBMITTED_UNCERTAIN -> SUBMITTED_UNCERTAIN | OBSERVED_ACTIVE | REJECTED | QUARANTINED`;
- `REJECTED -> OBSERVED_ACTIVE` only on later authoritative chain proof; otherwise it is terminal except quarantine;
- `OBSERVED_ACTIVE -> QUARANTINED` only for evidence investigation;
- `QUARANTINED` is terminal except an explicit audited reconciliation outside this state graph.

`CandidateStateUpdate` MUST reference an existing durable candidate in the same scope. Unknown or cross-scope candidate is `INVALID_STATE_TRANSITION`.

`submission_attempts` never decreases. `definitive_misses <= submission_attempts`. `last_attempt_unix_ms` is absent iff attempts are zero; when attempts increase it MUST be present and nondecreasing. State and counters are validated transactionally against the stored candidate.

## 7. Direct submission independence

The submitting edge persists exact candidate/settlement evidence locally before invoking `submitblock`. Recorder, critical-lane, clock, completeness, or payout-fence failure MUST NOT delay local consensus submission.

## 8. Network validation policy binding

Miningcore Profile 1.1 uses `direct_candidate_validation_version = 2` and a required 32-byte `bitcoin_network_policy_digest` in its semantic contract. The digest is recomputed from the canonical network-policy grammar in `coredrp-v1-bitcoin-network-policies.md` using the `network_id` selected by the Mining contract.

Two receivers MUST NOT select the same Miningcore scope-contract digest while using different BIP34 activation heights, genesis/network identities, direct-candidate validation versions, or allowed consensus commitment classes.

## 9. PostgreSQL effect atomicity

For a received batch, state-dependent profile validation, referential checks, application effects, candidate/accounting records, receiver stream head and checkpoint evidence commit in the same durable transaction. A semantic failure rolls back the entire current batch and emits no ACK.
