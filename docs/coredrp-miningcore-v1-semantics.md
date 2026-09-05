# CoreDRP Miningcore Profile 1.1 — Normative Semantics

**Status:** Draft 0.6 profile-freeze normative registry  
**Profile ID:** `coredrp.miningcore`  
**Profile version:** 1.1  
**Minimum Core:** 1.1  
**Required Mining profile:** `coredrp.mining` 1.1 on every projection scope

This registry is incorporated by `CoreDRP-1-SPEC-0.6.md`. Reference tooling implements these rules but is lower authority.

## 1. Event ownership, placement, authorization and membership

For a non-empty Mining scope:

- `0x0200 MiningcoreAccountingShareEvent`: lane 0;
- `0x0201 BitcoinDirectCoinbaseCandidate`: lane 1;
- `0x0202 CandidateStateUpdate`: lane 1.

Each requires the exact selected Mining 1.1 and Miningcore 1.1 scope contracts required by this registry.

For `MiningcoreAccountingShareEvent`, each projection carries its own `scope`. The primary projection scope MUST equal the enclosing Core `Event.scope`. A paired auxiliary projection MUST use a different scope.

For **every** accounting projection `P`, independently:

- `P.scope` MUST be an exact Mining scope present in the epoch binding with Mining 1.1 and Miningcore 1.1 scope-contract selections;
- the authenticated sender MUST be transport-authorized for `P.scope`; otherwise the event is rejected with `UNAUTHORIZED_SCOPE` before semantic quarantine;
- if completeness mode for `P.scope` at event time `T` is `RELAY_REQUIRED`, durable temporal membership `(sender,P.scope,T)` MUST exist; otherwise the event is rejected with `TEMPORAL_MEMBERSHIP_REQUIRED`;
- every financial effect created by that projection is attributed to `P.scope`, never merely to the enclosing Core scope.

The set of payout-relevant scopes written by one event is exactly `{primary.scope}` plus `paired.scope` when paired is present. Mining checkpoint coverage MUST include every such scope for which the sender has admitted payout-relevant effects during the epoch, subject to the temporal membership/mode and authorization rules in the Core/Mining specification. A nested auxiliary projection therefore cannot escape RequiredSender/completeness accounting.

### 1.1 Exact PoolId mapping

For every projection and candidate/state scope, `UTF8(PoolConfig.Id) == P.scope` (or the enclosing `Event.scope` for candidate/state events) byte-for-byte. The PoolId MUST satisfy the Mining 1–64 byte ASCII scope grammar. Case folding, aliases, trimming, Unicode normalization, fallback to the primary pool and receiver-local scope maps are forbidden. The configured pool lookup and all persistence/idempotency/balance keys MUST use that exact identity. Missing or mismatched PoolId fails negotiation/admission closed with `SEMANTIC_CONTRACT_MISMATCH`, before any effects or sender WAL admission. Parent and auxiliary projections each perform this check independently.

## 2. Frozen semantic-contract allocations

Unknown values MUST fail scope-contract negotiation with `SEMANTIC_CONTRACT_MISMATCH`.

| Field | Allowed value | Meaning |
|---|---:|---|
| `accounting_schema_version` | 3 | projection-local scope + strict Miningcore accounting compatibility in Section 3 |
| `persistence_schema_version` | 1 | atomic PostgreSQL receiver/effect persistence in Section 11 |
| `direct_candidate_validation_version` | 2 | Bitcoin validation in Sections 6 and 10 plus bound network policy |
| `settlement_policy_version` | 5 | resolved scheme/adjustment binding, pruning and quarantine rules in Sections 8–10 and incorporated registries |

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
- satisfy the independent authorization/membership rules in Section 1;
- carry `accounting_id` exactly 16 bytes, non-zero, and valid RFC 9562 UUID bytes;
- carry `reward_basis_satoshis` and require it to be strictly positive;
- have non-empty `share.session_id`;
- have non-empty `share.source_ip`;
- require `share.achieved_share_difficulty > 0` for the Miningcore accounting event even though generic Mining Profile 1.1 permits informational zero;
- set `block_only = false`.

`block_only` is not part of ordinary `0x0200` accounting schema 3. Direct/block-only evidence uses the dedicated candidate path (`0x0201` and its state updates) rather than an ordinary accounting projection. `block_record_emitted` and `statistical_record_emitted` remain audit facts for the ordinary statistical accounting record; neither may be used to bypass the dedicated candidate semantics.

For a SINGLE projection, `primary.scope == enclosing Event.scope`.

For PARENT/AUXILIARY pairs:

- `primary.scope == enclosing Event.scope`;
- `paired.scope != primary.scope`;
- both `accounting_id` fields MUST be byte-for-byte identical because they identify one accepted merged-mining proof projected to two chains;
- worker, user agent, source IP, source/cluster source, session ID, `created_unix_ms`, and `achieved_share_difficulty` MUST match exactly;
- miner MAY differ because the parent and auxiliary chains may use different payout addresses;
- block height, assigned difficulty, actual difficulty, network difficulty, candidate fields, reward basis, and PPS liability MAY differ where chain-specific;
- no third/nested projection is representable.

### 3.1 Accounting ID mapping to Miningcore

The 16 bytes are RFC 9562 network-order UUID bytes. The corresponding canonical Miningcore textual accounting identity is exactly the lowercase 32-character hexadecimal UUID with no separators, equivalent to `Guid.ToString("N").ToLowerInvariant()` for the same UUID value.

All-zero UUID is invalid. Implementations MUST NOT hash, store or compare .NET `Guid.ToByteArray()` mixed-endian bytes as the CoreDRP accounting identity.

### 3.2 PPS amount

For a PPS scope, `pps_calculated_amount` is REQUIRED and MUST equal `PPSLiabilityV1` in `coredrp-v1-settlement-scheme-policies.md` under the accepting scope contract. Both producer pre-admission and receiver semantic validation recompute that exact formula. For non-PPS scopes this field MUST be absent. Presence/absence, canonical amount, eligibility and exact equality are validation requirements; a positive amount alone is insufficient. A Miningcore integration MUST replace its live-configuration PPS validator with this contract-bound validator for CoreDRP effects. Because `accounting_id` is mandatory, PPS never creates an anonymous financial effect.

Violations of Section 3 are `SEMANTIC_PAYLOAD_INVALID` except the authorization/membership controls in Section 1, which use their dedicated errors and are non-quarantinable.

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

This section, `coredrp-v1-settlement-safety.md`, `coredrp-v1-settlement-scheme-policies.md`, and `coredrp-v1-share-difficulty-adjustment-policies.md` are jointly normative. Mining `payout_scheme` selects exactly one scheme row and the Miningcore scope contract binds the exact resolved scheme/adjustment digest.

| Scheme | Settlement rule | Deletion/retention rule |
|---|---|---|
| PPLNS | requires `SettlementSafe` for the exact window derived from bound factor and adjusted share difficulties | use settlement-specific prune safety in the settlement registry; retain all evidence referenced by live/unsettled windows |
| PPLNSBF | requires `SettlementSafe` for the exact window derived from bound factor, block-finder percentage and adjusted share difficulties | use settlement-specific prune safety; retain all evidence referenced by live/unsettled windows |
| PROP | requires `SettlementSafe` from round start through settlement boundary | use settlement-specific prune safety |
| PPS | payout is not remote-completeness fence gated; each accepted share must already have durable accounting/idempotency effect | delete only after accounting is durable, retry/idempotency dependency is retired, and no live proof/audit dependency remains |
| CUSTODIAL_SOLO | payout is not remote-completeness fence gated | winning share and block/settlement evidence retained through settlement finality; non-winning shares may follow configured retention when no evidence dependency remains |
| DIRECT_SOLO | consensus submission is never recorder/completeness gated | exact candidate/submission/settlement evidence retained through local finality; `submitblock` never waits on recorder state |

A `SETTLE_WITHOUT_FENCE_OVERRIDE` may permit one named settlement but does not turn the settlement into `SettlementSafe`, does not advance `PayoutSafeThrough`, and does not relax evidence retention for audit.

## 9. Payout-significant quarantine

A quarantined event is payout-significant when it is a lane-0 Mining share or Miningcore accounting event, or when an incorporated settlement registry marks its effect as a dependency of an unsettled financial result.

Payout-significant quarantine has the same three-state lifecycle as a completeness gap, but transitions are governed by the canonical ADMIN actions in `coredrp-v1-admin-actions.md` and the exact evidence grammar in `coredrp-v1-quarantine-safety.md`.

`QUARANTINE_AND_ADVANCE` creates/retains `UNRESOLVED` uncertainty and MUST NOT manufacture completeness or settlement safety. Only `QUARANTINE_RECONCILIATION` may create `RESOLVED_RECONCILED`; only `QUARANTINE_WAIVER` may create `RESOLVED_WAIVED`.

## 10. Network and settlement policy binding

Miningcore Profile 1.1 uses `direct_candidate_validation_version = 2` and requires both:

- `bitcoin_network_policy_digest32`, recomputed from `coredrp-v1-bitcoin-network-policies.md` using the Mining-selected `network_id`;
- `settlement_scheme_policy_digest32`, recomputed from `coredrp-v1-settlement-scheme-policies.md` using the Mining-selected `payout_scheme`, the **resolved effective** Miningcore payout parameters, and the resolved `share_difficulty_adjustment_policy_digest32`.

Two receivers MUST NOT select the same Miningcore scope-contract digest while using different Bitcoin validation policy, settlement-window/configuration parameters, or share-difficulty adjustment behavior.

The `synthetic-regtest` network policy is test-only and MUST NOT be selected by a production Mining scope.

## 11. Direct submission independence and PostgreSQL atomicity

The submitting edge persists exact candidate/settlement evidence locally before invoking `submitblock`. Recorder, critical-lane, clock, completeness, or payout-fence failure MUST NOT delay local consensus submission.

For a received batch, state-dependent profile validation, projection-scope authorization/membership, referential checks, application effects, candidate/accounting records, receiver stream head, checkpoint evidence, quarantine/gap state, and financial proof dependencies commit in the same durable transaction. A semantic failure rolls back the entire current batch and emits no ACK.

## 12. Caller-request identity and accounting group uniqueness

The canonical request encodings in `coredrp-v1-miningcore-requests.md` are mandatory for event types `0x0200`, `0x0201` and `0x0202`. They exclude sequencer-generated Core identity/time. After resolving a new request's idempotency key, the sequencer assigns event time and sets both accounting projections' `share.created_unix_ms` to that exact value. Retrying the original request never supplies or regenerates this timestamp.

For `0x0200`, the receiver stores a global durable `accounting_id -> (original Core event identity, accounting_group_digest32)` mapping within its logical accounting database, shared by all senders, scopes and epochs. `AccountingGroupV1 = uint16_be(1) || accounting_uuid16 || uint32_be(request_len) || MiningcoreAccountingShareRequestV1 || int64_be(assigned_event_time) || payload_hash32`; its SHA-256 is the group digest. The canonical request is reconstructed from the accepted payload excluding generated time; original identity is `(sender,epoch,lane,sequence,relay_event_id)`.

First use locks/inserts the global UUID and commits the group digest, exact projection set and all effects with the receiver head in one transaction. Concurrent first use is serialized by database uniqueness, never check-then-insert outside the transaction. Replay of the original immutable Core event with identical group/evidence returns its prior result and applies no effect. Any second distinct Core event reusing that accounting UUID is `INVALID_STATE_TRANSITION`, including byte-identical application content. Any conflicting digest or original event evidence is also `INVALID_STATE_TRANSITION`; neither case is quarantinable, neither advances the stream or mutates financial state. Parent/auxiliary projections form one atomic group and therefore share the single UUID legitimately.

The mapping/tombstone survives pruning, epoch changes and receiver recovery for the lifetime of the accounting namespace. It cannot be recreated as a new group after retention expiry. Sender pre-admission performs the same identity-conflict check where its durable evidence permits; receiver global uniqueness remains authoritative for cross-sender races.
