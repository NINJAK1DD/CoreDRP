# CoreDRP/1 Draft 0.6 ADMIN Action Registry

Normative canonical body: `uint16_be(1) || uint16_be(field_count) || repeated(field)` with strictly increasing field IDs. Each field is `uint16_be(field_id) || uint32_be(value_len) || value`. Duplicate/descending IDs are malformed and MUST NOT be sorted into validity.

All actions contain field 1 `idempotency_uuid` (16 RFC 9562 bytes) and field 2 `expected_state_version` (exact uint64_be, 8 bytes).

| ID | Action | Additional canonical fields |
|---:|---|---|
| 0x0001 | QUARANTINE_AND_ADVANCE | 3 sender UUID(16), 4 lane(uint8), 5 epoch UUID(16), 6 sequence(uint64), 7 event_type(uint16), 8 relay UUID(16), 9 chain hash(32), 10 reason UTF-8 |
| 0x0002 | GAP_RECONCILIATION | 3 gap UUID(16), 4 retired epoch UUID(16), 5 first sequence(uint64), 6 last sequence(uint64), 7 imported terminal hash(32), 8 reason UTF-8 |
| 0x0003 | GAP_WAIVER | 3 gap UUID(16), 4 reason UTF-8 |
| 0x0004 | NORMAL_EPOCH_TRANSITION | 3 sender UUID(16), 4 lane(uint8), 5 old epoch UUID(16), 6 final sequence(uint64), 7 final hash(32), 8 new epoch UUID(16), 9 inherited temporal floor(int64), 10 inherited checkpoint floor(int64), 11 reason UTF-8 |
| 0x0005 | INITIAL_EPOCH_APPROVAL | 3 sender UUID(16), 4 lane(uint8), 5 new epoch UUID(16), 6 genesis hash(32), 7 initial temporal floor(int64), 8 initial checkpoint floor(int64), 9 reason UTF-8 |
| 0x0006 | EXCEPTIONAL_EPOCH_ABANDON | 3 sender UUID(16), 4 lane(uint8), 5 old epoch UUID(16), 6 last committed/ACKed sequence(uint64), 7 last committed hash(32), 8 old durable tail(uint64), 9 abandoned first sequence(uint64), 10 abandoned last sequence(uint64), 11 new epoch UUID(16), 12 gap-scope mode(uint8: 1 exact-set, 2 wildcard), 13 reason UTF-8 |
| 0x0007 | RECEIVER_REPLACEMENT_APPROVAL | 3 old receiver UUID(16), 4 old database incarnation UUID(16), 5 new receiver UUID(16), 6 new database incarnation UUID(16), 7 sender UUID(16), 8 lane(uint8), 9 reason UTF-8 |
| 0x0101 | MEMBERSHIP_START | 3 scope, 4 sender UUID(16), 5 effective_unix_ms(int64), 6 reason UTF-8 |
| 0x0102 | MEMBERSHIP_END | 3 scope, 4 sender UUID(16), 5 effective_unix_ms(int64), 6 reason UTF-8 |
| 0x0103 | COMPLETENESS_MODE_CHANGE | 3 scope, 4 effective_unix_ms(int64), 5 mode(uint8), 6 reason UTF-8 |
| 0x0104 | SETTLE_WITHOUT_FENCE_OVERRIDE | 3 scope, 4 settlement identifier bytes, 5 reason UTF-8 |
| 0x0105 | TEMPORAL_POLICY_RECONCILIATION | 3 scope, 4 effective_unix_ms(int64), 5 correction-kind(uint8), 6 optional sender UUID(16), 7 prior/new policy evidence bytes, 8 reason UTF-8 |
| 0x0201 | MININGCORE_CAPABILITY_ACTIVATION | 3 scope, 4 capability ASCII, 5 effective_unix_ms(int64), 6 reason UTF-8 |

`admin_digest = SHA256("CoreDRP1-ADMIN" || uint16_be(action_type) || uint32_be(body_len) || body)`.

## Durable idempotency and atomicity

For one ADMIN state domain, idempotency lookup, digest comparison, expected-state-version check, state mutation, audit record, state-version increment, and stored result MUST execute in one serializable/explicitly locked durable transaction.

Evaluation order is:

1. lookup idempotency UUID;
2. if found with same digest, return the original stored result without applying mutation and without requiring the current state version to equal the old request's expected version;
3. if found with different digest, `IDEMPOTENCY_KEY_CONFLICT`;
4. for a new key, require current state version == `expected_state_version`, otherwise `ADMIN_ACTION_CONFLICT`;
5. validate action-specific preconditions;
6. atomically apply mutation, append audit/result record, advance state version, and commit.

Exceptional abandonment atomically creates exact/wildcard gap evidence and retires/approves epochs in the same transaction. Receiver replacement preserves prior receiver/ACK audit anchors. GAP_RECONCILIATION imports verified retired-epoch evidence without reactivating the epoch.

## Temporal-policy restrictions

Ordinary MEMBERSHIP_START, MEMBERSHIP_END, and COMPLETENESS_MODE_CHANGE MUST be future-effective beyond `PayoutSafeThrough(scope) + applicable_clock_uncertainty`. An ordinary action effective at or before that protected boundary is `ADMIN_ACTION_CONFLICT`.

Retroactive correction uses `0x0105 TEMPORAL_POLICY_RECONCILIATION`. It records historical uncertainty and blocks further `PayoutSafeThrough` advancement for the affected scope until reconciled/waived; it MUST NOT silently rewrite a previously proven frontier.

## Gap waiver

GAP_WAIVER changes a gap to `RESOLVED_WAIVED`, which removes the operational unresolved status but never proves completeness and never advances `PayoutSafeThrough`. A settlement exception requires the separate `SETTLE_WITHOUT_FENCE_OVERRIDE`; the override does not convert the waived range into PayoutSafe evidence.
