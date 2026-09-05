# CoreDRP/1 Draft 0.6 error-emission registry

This registry is normative. Every non-UNSPECIFIED `ErrorCode` has one primary emission condition; profiles MAY add diagnostic detail but MUST NOT weaken disposition.

| Symbol | Primary emission condition |
|---|---|
| PROTOCOL_VERSION_MISMATCH | No mutually supported Core major/minor during Hello negotiation. |
| INVALID_HANDSHAKE | Hello/control field combination, fixed length, ASCII, retained-range or uniqueness predicate is invalid and no more specific code applies. |
| UNAUTHORIZED_SENDER | Client sender UUID does not match authenticated sender SAN or sender is not transport-authorized. |
| UNAUTHORIZED_SCOPE | Scoped event is not authorized, or a new lane-global checkpoint would assert completeness for any currently unauthorized covered scope. |
| UNKNOWN_EVENT_TYPE | Receiver has no registered definition for event type. |
| UNADVERTISED_EVENT_TYPE | Event type was not selected into the immutable epoch binding. |
| EVENT_VALIDATOR_UNAVAILABLE | Selected profile validator cannot currently execute for a transient operational reason. |
| SEQUENCE_GAP | EventBatch/stream sequence is not exactly contiguous with expected sequence. |
| CHAIN_MISMATCH | Event/batch cryptographic chain does not match expected previous/terminal hash outside reconnect split-history classification. |
| SPLIT_LOG | Reconnect common head/genesis differs, or a receiver-ahead head cannot be verified from sender evidence. |
| SENDER_ROLLBACK | Receiver committed sequence is greater than sender durable tail. |
| RECOVERY_GAP | Required replay or receiver-replacement replay precedes retained trustworthy sender history. |
| EPOCH_NOT_APPROVED | Presented epoch is neither the current approved epoch nor an explicitly authorized retired-epoch import target. |
| EVENT_TOO_LARGE | Single event payload exceeds negotiated/profile payload maximum. |
| SEMANTIC_CONTRACT_MISMATCH | Required exact-version profile/scope contract is missing or digest differs. |
| RECEIVER_DURABILITY_UNAVAILABLE | Receiver cannot durably commit (for example PostgreSQL unavailable) before ACK. |
| CLOCK_CONTRACT_VIOLATION | Effective local/remote clock policy is BAD or UNKNOWN beyond permitted grace/recovery conditions. |
| MALFORMED_FRAME | Frame direction/oneof/control semantics or redundant disposition is malformed. |
| EVENT_TYPE_OUT_OF_RANGE | event_type exceeds 65535 before hashing. |
| LANE_ID_OUT_OF_RANGE | lane exceeds 255 before hashing. |
| SEQUENCE_OUT_OF_RANGE | event sequence is zero or exceeds INT64_MAX where an event sequence is required. |
| RESOURCE_LIMIT_EXCEEDED | Splittable aggregate/window/request limit exceeded. |
| CONTRACT_BINDING_CHANGED | Active epoch selected profile/version/scope digest/event-set differs from persisted binding. |
| RECEIVER_ROLLBACK | Same receiver identity/incarnation reports durable sequence below sender remembered ACK. |
| RECEIVER_INCARNATION_CHANGED | Authenticated receiver logical ID matches but database incarnation differs and has not been replacement-approved. |
| STREAM_ALREADY_ACTIVE | Another live receiver stream owns the same sender/lane fence. |
| SEMANTIC_PAYLOAD_INVALID | Correctly placed, authorized, chain-valid event fails profile payload semantics and is eligible for explicit quarantine. |
| CHECKPOINT_BACKDATED_EVENT | Later covered event time is not strictly greater than trusted checkpoint floor. |
| ADMIN_ACTION_CONFLICT | expected_state_version or protected ADMIN precondition does not match current durable state. |
| IDEMPOTENCY_KEY_CONFLICT | Same permanent admission/admin key is reused with different canonical request digest. |
| INVALID_STATE_TRANSITION | Candidate/admin/profile transition has invalid predecessor, unknown referent, cross-scope referent or regressing counters/time. |
| INVALID_EVENT_PLACEMENT | Known event type appears on forbidden lane or forbidden empty/non-empty scope form. |
| ATOMIC_RESOURCE_LIMIT_EXCEEDED | Intrinsic object/scope/field size cannot be made valid by splitting/retry. |
| RECEIVER_ID_CHANGED | Authenticated receiver logical ID differs from sender-pinned logical receiver without approved replacement. |
| TEMPORAL_MEMBERSHIP_REQUIRED | RELAY_REQUIRED payout-relevant event has no durable membership interval covering sender/scope/event time. |
| EVENT_IDENTITY_MISMATCH | Quarantine/import/replay bytes or IDs differ from exact immutable authorized event identity. |
| SEMANTIC_RETRY_LIMIT | Same immutable sequence repeatedly returns identical semantic-invalid result beyond configured threshold. |
