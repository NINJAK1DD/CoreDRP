# CoreDRP/1 Error Registry — Draft 0.2

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

This registry is normative. Numeric values match `protocol/coredrp-v1.proto`.

| Code | Symbol | Disposition | Meaning | Stream survives? | Quarantinable? |
|---:|---|---|---|---|---|
| 0 | ERROR_CODE_UNSPECIFIED | none | Invalid as an emitted error | no | no |
| 1 | PROTOCOL_VERSION_MISMATCH | PERMANENT_CONFIGURATION | No compatible Core major/minor | no | no |
| 2 | INVALID_HANDSHAKE | PERMANENT_CONFIGURATION | Handshake combination invalid | no | no |
| 3 | UNAUTHORIZED_SENDER | PERMANENT_CONFIGURATION | Certificate/authorization failure | no | no |
| 4 | UNAUTHORIZED_SCOPE | PERMANENT_CONFIGURATION | Sender not authorized for scope | no | no |
| 5 | UNKNOWN_EVENT_TYPE | PERMANENT_CONFIGURATION | Event type not known to receiver | no | no |
| 6 | UNADVERTISED_EVENT_TYPE | PERMANENT_CONFIGURATION | Event type not in persisted negotiated set | no | no |
| 7 | EVENT_VALIDATOR_UNAVAILABLE | STREAM_RETRYABLE | Negotiated validator temporarily unavailable | no | no |
| 8 | SEQUENCE_GAP | OPERATOR_INTERVENTION | Non-contiguous sequence history | no | no |
| 9 | CHAIN_MISMATCH | OPERATOR_INTERVENTION | Batch chain verification failed | no | no |
| 10 | SPLIT_LOG | OPERATOR_INTERVENTION | Same epoch/sequence has different hash | no | no |
| 11 | SENDER_ROLLBACK | OPERATOR_INTERVENTION | Receiver is ahead of sender durable tail | no | no |
| 12 | RECOVERY_GAP | OPERATOR_INTERVENTION | Required replay precedes sender retained history | no | no |
| 13 | EPOCH_NOT_APPROVED | OPERATOR_INTERVENTION | New/different epoch lacks durable transition approval | no | no |
| 14 | EVENT_TOO_LARGE | PERMANENT_CONFIGURATION | Single event exceeds negotiated/hard cap | no | no |
| 15 | SEMANTIC_CONTRACT_MISMATCH | PERMANENT_CONFIGURATION | Profile/scope semantic digest mismatch | no | no |
| 16 | RECEIVER_DURABILITY_UNAVAILABLE | STREAM_RETRYABLE | Receiver cannot currently provide durable commit | yes or reconnect | no |
| 17 | CLOCK_CONTRACT_VIOLATION | STREAM_RETRYABLE | Clock proof not presently trustworthy | yes or reconnect | no |
| 18 | MALFORMED_FRAME | PERMANENT_CONFIGURATION | Syntactically representable but semantically malformed frame | no | no |
| 19 | EVENT_TYPE_OUT_OF_RANGE | PERMANENT_CONFIGURATION | event_type > 65535 | no | no |
| 20 | LANE_ID_OUT_OF_RANGE | PERMANENT_CONFIGURATION | lane_id > 255 | no | no |
| 21 | SEQUENCE_OUT_OF_RANGE | PERMANENT_CONFIGURATION | sequence is 0 or > INT64_MAX | no | no |
| 22 | RESOURCE_LIMIT_EXCEEDED | STREAM_RETRYABLE | Aggregate/request resource bound exceeded; peer may split/retry | yes | no |
| 23 | CONTRACT_BINDING_CHANGED | OPERATOR_INTERVENTION | Epoch's persisted capability/semantic binding changed | no | no |
| 24 | RECEIVER_ROLLBACK | OPERATOR_INTERVENTION | Same receiver incarnation reports lower durable sequence | no | no |
| 25 | RECEIVER_INCARNATION_CHANGED | OPERATOR_INTERVENTION | Receiver database incarnation changed; explicit reconciliation required | no | no |
| 26 | STREAM_ALREADY_ACTIVE | STREAM_RETRYABLE | Another stream owns sender/lane | no | no |
| 27 | SEMANTIC_PAYLOAD_INVALID | EVENT_QUARANTINABLE | Core-valid event failed profile validation | no until resolved | yes |
| 28 | CHECKPOINT_BACKDATED_EVENT | OPERATOR_INTERVENTION | Later covered event time does not exceed checkpoint boundary | no | no |
| 29 | ADMIN_ACTION_CONFLICT | OPERATOR_INTERVENTION | optimistic state_version check failed | n/a | n/a |
| 30 | IDEMPOTENCY_KEY_CONFLICT | PERMANENT_CONFIGURATION | idempotency key reused for different canonical request | n/a | n/a |
| 31 | INVALID_STATE_TRANSITION | OPERATOR_INTERVENTION | profile state-machine transition invalid | no | profile-dependent |

A receiver MUST send the disposition listed here for a given Core error code. Profile-specific semantic status may add detail but MUST NOT weaken a Core disposition.
