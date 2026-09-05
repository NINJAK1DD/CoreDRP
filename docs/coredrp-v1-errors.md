# CoreDRP/1 Error Registry — Draft 0.5

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

This registry is normative. Numeric values MUST match `protocol/coredrp-v1.proto`.

| Code | Symbol | Disposition | Meaning | Stream survives? | Quarantinable? |
|---:|---|---|---|---|---|
| 0 | ERROR_CODE_UNSPECIFIED | none | Invalid as an emitted error | no | no |
| 1 | PROTOCOL_VERSION_MISMATCH | PERMANENT_CONFIGURATION | No compatible Core major/minor | no | no |
| 2 | INVALID_HANDSHAKE | PERMANENT_CONFIGURATION | Handshake combination invalid | no | no |
| 3 | UNAUTHORIZED_SENDER | PERMANENT_CONFIGURATION | Sender certificate/authorization failure | no | no |
| 4 | UNAUTHORIZED_SCOPE | PERMANENT_CONFIGURATION | Sender is not authorized for a scope/event/checkpoint assertion | no | no |
| 5 | UNKNOWN_EVENT_TYPE | PERMANENT_CONFIGURATION | Event type not known to receiver | no | no |
| 6 | UNADVERTISED_EVENT_TYPE | PERMANENT_CONFIGURATION | Event type absent from persisted negotiated set | no | no |
| 7 | EVENT_VALIDATOR_UNAVAILABLE | STREAM_RETRYABLE | Negotiated validator temporarily unavailable | reconnect | no |
| 8 | SEQUENCE_GAP | OPERATOR_INTERVENTION | Non-contiguous sequence history | no | no |
| 9 | CHAIN_MISMATCH | OPERATOR_INTERVENTION | Batch/event chain verification failed | no | no |
| 10 | SPLIT_LOG | OPERATOR_INTERVENTION | Common reconciliation head differs or cannot be verified | no | no |
| 11 | SENDER_ROLLBACK | OPERATOR_INTERVENTION | Receiver durable state is ahead of sender durable tail | no | no |
| 12 | RECOVERY_GAP | OPERATOR_INTERVENTION | Required replay precedes retained sender history or lost ACKed state cannot be replayed | no | no |
| 13 | EPOCH_NOT_APPROVED | OPERATOR_INTERVENTION | Initial/different epoch lacks durable approval | no | no |
| 14 | EVENT_TOO_LARGE | PERMANENT_CONFIGURATION | Single event exceeds negotiated/profile cap | no | no |
| 15 | SEMANTIC_CONTRACT_MISMATCH | PERMANENT_CONFIGURATION | Selected exact profile/scope semantic digest mismatch | no | no |
| 16 | RECEIVER_DURABILITY_UNAVAILABLE | STREAM_RETRYABLE | Receiver cannot currently provide durable commit | reconnect | no |
| 17 | CLOCK_CONTRACT_VIOLATION | STREAM_RETRYABLE | Clock proof currently BAD/expired beyond permitted recovery policy | yes/reconnect | no |
| 18 | MALFORMED_FRAME | PERMANENT_CONFIGURATION | Frame/handshake/control combination invalid | no | no |
| 19 | EVENT_TYPE_OUT_OF_RANGE | PERMANENT_CONFIGURATION | event_type > 65535 | no | no |
| 20 | LANE_ID_OUT_OF_RANGE | PERMANENT_CONFIGURATION | lane_id > 255 | no | no |
| 21 | SEQUENCE_OUT_OF_RANGE | PERMANENT_CONFIGURATION | sequence is 0 or > INT64_MAX | no | no |
| 22 | RESOURCE_LIMIT_EXCEEDED | STREAM_RETRYABLE | Splittable aggregate/window resource bound exceeded | yes | no |
| 23 | CONTRACT_BINDING_CHANGED | OPERATOR_INTERVENTION | Active epoch capability/version/semantic binding changed | no | no |
| 24 | RECEIVER_ROLLBACK | OPERATOR_INTERVENTION | Same receiver identity/incarnation reports lower durable sequence | no | no |
| 25 | RECEIVER_INCARNATION_CHANGED | OPERATOR_INTERVENTION | Database incarnation changed and requires approved replacement reconciliation | no | no |
| 26 | STREAM_ALREADY_ACTIVE | STREAM_RETRYABLE | Another stream owns sender/lane | no | no |
| 27 | SEMANTIC_PAYLOAD_INVALID | EVENT_QUARANTINABLE | Correctly placed Core-valid event failed profile payload validation | no until resolved | yes |
| 28 | CHECKPOINT_BACKDATED_EVENT | OPERATOR_INTERVENTION | Later covered event time does not exceed checkpoint boundary | no | no |
| 29 | ADMIN_ACTION_CONFLICT | OPERATOR_INTERVENTION | optimistic state-version/precondition check failed | n/a | n/a |
| 30 | IDEMPOTENCY_KEY_CONFLICT | PERMANENT_CONFIGURATION | permanent admission/admin key reused for different canonical request | n/a | n/a |
| 31 | INVALID_STATE_TRANSITION | OPERATOR_INTERVENTION | profile/admin/candidate transition or referential lookup invalid | no | no |
| 32 | INVALID_EVENT_PLACEMENT | PERMANENT_CONFIGURATION | Known event type used on forbidden lane/scope form | no | no |
| 33 | ATOMIC_RESOURCE_LIMIT_EXCEEDED | PERMANENT_CONFIGURATION | Intrinsic single-object limit exceeded | no | no |
| 34 | RECEIVER_ID_CHANGED | OPERATOR_INTERVENTION | Authenticated/pinned logical receiver identity changed unexpectedly | no | no |
| 35 | TEMPORAL_MEMBERSHIP_REQUIRED | PERMANENT_CONFIGURATION | RELAY_REQUIRED payout-relevant event has no membership covering sender/scope/event-time | no | no |
| 36 | EVENT_IDENTITY_MISMATCH | OPERATOR_INTERVENTION | retransmitted/imported event differs from exact authorized immutable identity | no | no |
| 37 | SEMANTIC_RETRY_LIMIT | OPERATOR_INTERVENTION | same immutable semantic failure exceeded bounded retry threshold | no | no |

`ProtocolError.disposition` is redundant transport metadata. This table is authoritative. A received code/disposition mismatch is `MALFORMED_FRAME`.
