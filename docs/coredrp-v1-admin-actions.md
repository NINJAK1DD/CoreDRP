# CoreDRP/1 Draft 0.6 ADMIN Action Registry — Freeze Completion

Normative canonical body: `uint16_be(1) || uint16_be(field_count) || repeated(field)` with strictly increasing field IDs. Each field is `uint16_be(field_id) || uint32_be(value_len) || value`. Duplicate/descending IDs are malformed and MUST NOT be sorted into validity.

All executable actions contain field 1 `idempotency_uuid` (16 RFC 9562 bytes) and field 2 `expected_state_version` (exact uint64_be, 8 bytes).

| ID | Action | Additional canonical fields |
|---:|---|---|
| 0x0001 | QUARANTINE_AND_ADVANCE | 3 sender UUID(16), 4 lane(uint8), 5 epoch UUID(16), 6 sequence(uint64), 7 event_type(uint16), 8 relay UUID(16), 9 chain hash(32), 10 reason UTF-8 |
| 0x0002 | GAP_RECONCILIATION | 3 gap UUID(16), 4 retired epoch UUID(16), 5 first sequence(uint64), 6 last sequence(uint64), 7 imported terminal hash(32), 8 reason UTF-8 |
| 0x0003 | GAP_WAIVER | 3 gap UUID(16), 4 reason UTF-8 |
| 0x0004 | NORMAL_EPOCH_TRANSITION | 3 sender UUID(16), 4 lane(uint8), 5 old epoch UUID(16), 6 final sequence(uint64), 7 final hash(32), 8 new epoch UUID(16), 9 inherited temporal floor(int64), 10 inherited checkpoint floor(int64), 11 reason UTF-8 |
| 0x0005 | INITIAL_EPOCH_APPROVAL | 3 sender UUID(16), 4 lane(uint8), 5 new epoch UUID(16), 6 genesis hash(32), 7 initial temporal floor(int64), 8 initial checkpoint floor(int64), 9 reason UTF-8 |
| 0x0006 | EXCEPTIONAL_EPOCH_ABANDON | 3 sender UUID(16), 4 lane(uint8), 5 old epoch UUID(16), 6 last committed/ACKed sequence(uint64), 7 last committed hash(32), 8 old durable tail(uint64), 9 abandoned first sequence(uint64), 10 abandoned last sequence(uint64), 11 new epoch UUID(16), 12 gap-scope mode(uint8: 1 exact-set, 2 wildcard), 13 reason UTF-8 |
| 0x0007 | RECEIVER_REPLACEMENT_APPROVAL | 3 old receiver UUID(16), 4 old database incarnation UUID(16), 5 new receiver UUID(16), 6 new database incarnation UUID(16), 7 sender UUID(16), 8 lane(uint8), 9 reason UTF-8 |
| 0x0008 | QUARANTINE_RECONCILIATION | 3 quarantine UUID(16), 4 sender UUID(16), 5 lane(uint8), 6 epoch UUID(16), 7 sequence(uint64), 8 relay UUID(16), 9 event_type(uint16), 10 chain hash(32), 11 validator/profile evidence digest(32), 12 corrected effect digest(32), 13 reason UTF-8 |
| 0x0009 | QUARANTINE_WAIVER | 3 quarantine UUID(16), 4 sender UUID(16), 5 lane(uint8), 6 epoch UUID(16), 7 sequence(uint64), 8 relay UUID(16), 9 event_type(uint16), 10 chain hash(32), 11 reason UTF-8 |
| 0x0101 | MEMBERSHIP_START | 3 scope, 4 sender UUID(16), 5 effective_unix_ms(int64), 6 policy_generation(uint64), 7 staged_policy_digest(32), 8 reason UTF-8 |
| 0x0102 | MEMBERSHIP_END | 3 scope, 4 sender UUID(16), 5 effective_unix_ms(int64), 6 policy_generation(uint64), 7 staged_policy_digest(32), 8 reason UTF-8 |
| 0x0103 | COMPLETENESS_MODE_CHANGE | 3 scope, 4 effective_unix_ms(int64), 5 mode(uint8), 6 policy_generation(uint64), 7 staged_policy_digest(32), 8 reason UTF-8 |
| 0x0104 | SETTLE_WITHOUT_FENCE_OVERRIDE | 3 scope, 4 settlement identifier bytes, 5 reason UTF-8 |
| 0x0105 | TEMPORAL_POLICY_RECONCILIATION | 3 scope, 4 effective_unix_ms(int64), 5 correction_kind(uint8), 6 optional sender UUID(0 or 16), 7 prior_policy_evidence bytes, 8 new_policy_evidence bytes, 9 policy_generation(uint64), 10 reason UTF-8 |
| 0x0201 | MININGCORE_CAPABILITY_ACTIVATION | 3 scope, 4 capability ASCII, 5 effective_unix_ms(int64), 6 reason UTF-8 |

`admin_digest = SHA256("CoreDRP1-ADMIN" || uint16_be(action_type) || uint32_be(body_len) || body)`.

## 1. Durable idempotency and atomicity

For one ADMIN state domain, idempotency lookup, digest comparison, expected-state-version check, action-specific state locks, state mutation, audit record, state-version increment, and stored result MUST execute in one serializable/explicitly locked durable transaction.

Evaluation order:

1. lookup idempotency UUID;
2. if found with same digest, return original stored result without applying mutation and without requiring current state version to equal the old request's expected version;
3. if found with different digest, `IDEMPOTENCY_KEY_CONFLICT`;
4. for a new key, require current state version == `expected_state_version`, else `ADMIN_ACTION_CONFLICT`;
5. validate action-specific preconditions;
6. atomically apply mutation, append audit/result record, advance state version, and commit.

Exceptional abandonment atomically creates exact/wildcard gap evidence and retires/approves epochs in the same transaction. Receiver replacement preserves prior receiver/ACK audit anchors. GAP_RECONCILIATION imports verified retired-epoch evidence without reactivating the epoch.

## 2. Ordinary temporal-policy actions

MEMBERSHIP_START, MEMBERSHIP_END and COMPLETENESS_MODE_CHANGE are governed by `coredrp-v1-temporal-policy.md`.

Before the receiver transaction may activate one of these actions:

- `policy_generation` MUST be the next generation for the scope;
- `staged_policy_digest` MUST equal the canonical staging digest for the exact generation/action/effective time;
- every affected sender required by the temporal-policy registry MUST have a durable authenticated staging acknowledgement for that exact digest;
- for generation >=2, effective time MUST be beyond `PayoutSafeThrough(scope) + applicable_clock_uncertainty` using checked arithmetic; generation 1 uses the explicit bootstrap exception.

Missing/mismatched staging, stale generation, or protected-frontier conflict is `ADMIN_ACTION_CONFLICT`. The old policy remains active.

## 3. Completeness mode allocation

`COMPLETENESS_MODE_CHANGE.mode`:

- 1 = RELAY_REQUIRED;
- 2 = NO_RELAY_REQUIRED;
- all other values invalid.

## 4. Temporal-policy reconciliation

The complete correction-kind allocation and exact `PolicyEvidenceV1` binary grammar are normative in `coredrp-v1-temporal-policy.md`.

Field 5 correction-kind:

- 1 INSERT_MISSING_MEMBERSHIP_INTERVAL;
- 2 REPLACE_MEMBERSHIP_INTERVAL;
- 3 CORRECT_MEMBERSHIP_END;
- 4 REPLACE_COMPLETENESS_MODE_INTERVAL;
- 5 REMOVE_ERRONEOUS_MEMBERSHIP_INTERVAL;
- 6 REMOVE_ERRONEOUS_MODE_INTERVAL.

Fields 7 and 8 are independently length-delimited ADMIN fields containing exact `PolicyEvidenceV1` bytes or zero length only where the correction-kind explicitly permits absence. They MUST NOT contain implementation-defined JSON, protobuf, database row dumps, or opaque application bytes.

The reconciliation transaction verifies prior evidence against durable history, applies a new correction edge without deleting audit history, records the affected historical range and blocks safety-frontier advancement until the corrected history is re-evaluated/reconciled.

## 5. Gap waiver

GAP_WAIVER changes a gap to `RESOLVED_WAIVED`, which removes operational unresolved status but never proves completeness and never advances `PayoutSafeThrough`.

A settlement exception requires separate `SETTLE_WITHOUT_FENCE_OVERRIDE`; the override does not convert the waived range into PayoutSafe or SettlementSafe evidence.

## 6. Financial quarantine reconciliation

`QUARANTINE_RECONCILIATION` is the only Profile 1.1 operation that may transition payout-significant quarantine from `UNRESOLVED` to `RESOLVED_RECONCILED`.

Before commit, the transaction MUST:

1. lock the quarantine record named by field 3 and require current state `UNRESOLVED`;
2. require fields 4..10 to match the immutable quarantined event identity byte-for-byte;
3. verify the original event bytes/chain identity remain unchanged;
4. validate field 11 against a versioned validator/profile authority allowed by the current incorporated registries;
5. deterministically reconstruct/revalidate the ordinary financial effect under that authority;
6. compute the canonical corrected-effect digest defined by the quarantine registry and require it to equal field 12;
7. atomically apply the missing financial effect idempotently, append reconciliation/audit evidence, transition state to `RESOLVED_RECONCILED`, update affected proof dependencies, advance receiver state version and COMMIT.

If any financial effect write, identity check, authority check or audit write fails, the entire transaction rolls back and quarantine remains `UNRESOLVED`.

A second request with the same ADMIN idempotency UUID/digest returns the original stored result. A different request attempting to reconcile an already reconciled/waived quarantine is `ADMIN_ACTION_CONFLICT` unless the exact idempotent prior result applies.

## 7. Financial quarantine waiver

`QUARANTINE_WAIVER` is the only Profile 1.1 operation that may transition payout-significant quarantine from `UNRESOLVED` to `RESOLVED_WAIVED`.

The transaction MUST lock the named quarantine, require identity fields 4..10 to match the immutable quarantined event, record operator/audit identity plus reason, retain the original event/effect-absence evidence, transition state atomically, and COMMIT. It MUST NOT apply a synthetic financial effect, set SettlementSafe, advance PayoutSafeThrough/SafePruneThrough, or authorize pruning of the quarantine audit record.

## 8. Settlement override

`SETTLE_WITHOUT_FENCE_OVERRIDE` applies to exactly one settlement identifier. The durable result records the settlement, scope, reason, current gap/quarantine/policy state and operator audit identity. It MUST NOT be interpreted as a policy correction, gap/quarantine reconciliation, or reusable safety proof.
