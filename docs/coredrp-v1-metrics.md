# CoreDRP/1 Miningcore Metrics — Draft 0.4

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

This registry is normative for the Miningcore Integration Profile. Metric names use the `miningcore_coredrp_` prefix. Labels MUST contain stable bounded-cardinality identifiers only; miner, worker, IP, relay-event ID, epoch UUID, chain hash and arbitrary error text MUST NOT be labels.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `miningcore_coredrp_connected` | gauge | `sender,lane` | 1 while authenticated stream is active |
| `miningcore_coredrp_spool_events` | gauge | `sender,lane` | retained WAL event count |
| `miningcore_coredrp_spool_bytes` | gauge | `sender,lane` | retained WAL bytes |
| `miningcore_coredrp_spool_oldest_record_age_seconds` | gauge | `sender,lane` | age of oldest unACKed retained record |
| `miningcore_coredrp_fsync_seconds` | histogram | `lane` | sender durable-flush latency |
| `miningcore_coredrp_sequencer_queue_depth` | gauge | `lane` | admission queue depth |
| `miningcore_coredrp_sequencer_wait_seconds` | histogram | `lane` | admission queue wait |
| `miningcore_coredrp_acked_sequence` | gauge | `sender,lane` | sender durably remembered ACK sequence |
| `miningcore_coredrp_durable_tail_sequence` | gauge | `sender,lane` | sender durable tail |
| `miningcore_coredrp_replay_total` | counter | `sender,lane` | replayed events |
| `miningcore_coredrp_reconnect_total` | counter | `sender,lane,reason` | stream reconnect attempts by bounded reason enum |
| `miningcore_coredrp_window_blocked_seconds_total` | counter | `sender,lane` | flow-control blocked time |
| `miningcore_coredrp_recovery_gap` | gauge | `sender,lane` | 1 while unresolved recovery gap exists |
| `miningcore_coredrp_quarantined_events_total` | counter | `sender,lane,scope` | successfully quarantined immutable events |
| `miningcore_coredrp_retention_truncated_total` | counter | `sender,lane` | ACKed retention truncated under policy |
| `miningcore_coredrp_clock_bound_state` | gauge | `sender,lane,state` | one-hot GOOD/BAD/UNKNOWN remote bound state |
| `miningcore_coredrp_clock_unknown_grace_remaining_seconds` | gauge | `sender,lane` | remaining UNKNOWN grace |
| `miningcore_coredrp_clock_recovery_wait_seconds` | gauge | `sender,lane` | remaining durable-time recovery wait |
| `miningcore_coredrp_blocks_blocked_on_fence` | gauge | `pool` | blocks currently settlement-blocked by completeness |
| `miningcore_coredrp_payout_safe_through_unix_seconds` | gauge | `pool` | current PayoutSafeThrough frontier |
| `miningcore_coredrp_safe_prune_through_unix_seconds` | gauge | `pool` | current SafePruneThrough frontier |
| `miningcore_coredrp_safe_prune_lag_seconds` | gauge | `pool` | lag from current time to SafePruneThrough |
| `miningcore_coredrp_unresolved_completeness_gaps` | gauge | `pool` | unresolved payout-relevant gap count |
| `miningcore_coredrp_epoch_abandon_total` | counter | `sender,lane` | exceptional epoch abandonments |
| `miningcore_coredrp_receiver_identity_change_total` | counter | `sender,lane` | unexpected receiver-ID change detections |
| `miningcore_coredrp_receiver_incarnation_change_total` | counter | `sender,lane` | database-incarnation change detections |
| `miningcore_coredrp_admission_idempotency_conflict_total` | counter | `lane` | caller key reused with different admission digest |

`reason` and `state` label values MUST come from a closed implementation enum. Implementations MAY add new metrics under the prefix, but MUST NOT alter the meaning/type/required labels of registry entries within CoreDRP/1 without an explicit profile revision.
