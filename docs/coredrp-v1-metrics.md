# CoreDRP/1 Miningcore Metrics — Draft 0.6

**Originally designed and authored by Rob Cooke, 2026.**  
Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

This registry is normative for the Miningcore Integration Profile. Metric names use the `miningcore_coredrp_` prefix. Labels MUST be stable bounded-cardinality identifiers only. Miner, worker, source IP, relay-event ID, epoch UUID, chain hash, arbitrary error text and caller admission key MUST NOT be labels.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `miningcore_coredrp_connected` | gauge | `sender,lane` | authenticated stream active |
| `miningcore_coredrp_spool_events` | gauge | `sender,lane` | retained WAL event count |
| `miningcore_coredrp_spool_bytes` | gauge | `sender,lane` | retained WAL bytes |
| `miningcore_coredrp_spool_oldest_record_age_seconds` | gauge | `sender,lane` | oldest unACKed retained record age |
| `miningcore_coredrp_fsync_seconds` | histogram | `lane` | sender durable-flush latency |
| `miningcore_coredrp_sequencer_queue_depth` | gauge | `lane` | admission queue depth |
| `miningcore_coredrp_sequencer_wait_seconds` | histogram | `lane` | admission queue wait |
| `miningcore_coredrp_acked_sequence` | gauge | `sender,lane` | sender durably remembered ACK |
| `miningcore_coredrp_durable_tail_sequence` | gauge | `sender,lane` | sender durable tail |
| `miningcore_coredrp_replay_total` | counter | `sender,lane` | replayed events |
| `miningcore_coredrp_reconnect_total` | counter | `sender,lane,reason` | reconnect attempts |
| `miningcore_coredrp_window_blocked_seconds_total` | counter | `sender,lane` | flow-control blocked time |
| `miningcore_coredrp_recovery_gap` | gauge | `sender,lane` | unresolved recovery gap exists |
| `miningcore_coredrp_quarantined_events_total` | counter | `sender,lane,scope` | immutable events quarantined |
| `miningcore_coredrp_retention_truncated_total` | counter | `sender,lane` | ACKed retention truncations |
| `miningcore_coredrp_clock_bound_state` | gauge | `sender,lane,state` | one-hot GOOD/BAD/UNKNOWN/RECOVERING state |
| `miningcore_coredrp_clock_unknown_grace_remaining_seconds` | gauge | `sender,lane` | remaining UNKNOWN grace |
| `miningcore_coredrp_clock_recovery_wait_seconds` | gauge | `sender,lane` | BAD/RECOVERING wait |
| `miningcore_coredrp_blocks_blocked_on_fence` | gauge | `pool` | settlement-blocked blocks |
| `miningcore_coredrp_payout_safe_through_unix_seconds` | gauge | `pool` | receiver-proven payout frontier |
| `miningcore_coredrp_safe_prune_through_unix_seconds` | gauge | `pool` | safe destructive-prune frontier |
| `miningcore_coredrp_safe_prune_lag_seconds` | gauge | `pool` | lag to safe prune frontier |
| `miningcore_coredrp_unresolved_completeness_gaps` | gauge | `pool` | unresolved payout-relevant gaps |
| `miningcore_coredrp_waived_completeness_ranges` | gauge | `pool` | waived ranges that remain non-PayoutSafe |
| `miningcore_coredrp_epoch_abandon_total` | counter | `sender,lane` | exceptional epoch abandonments |
| `miningcore_coredrp_receiver_identity_change_total` | counter | `sender,lane` | receiver-ID change detections |
| `miningcore_coredrp_receiver_incarnation_change_total` | counter | `sender,lane` | database-incarnation changes |
| `miningcore_coredrp_admission_idempotency_conflict_total` | counter | `lane` | active key reused with different digest |
| `miningcore_coredrp_admission_generation_records` | gauge | `sender,lane,producer` | detailed records in active producer generation |
| `miningcore_coredrp_admission_generation_bytes` | gauge | `sender,lane,producer` | durable bytes used by active generation detail |
| `miningcore_coredrp_admission_generation` | gauge | `sender,lane,producer` | current producer generation |
| `miningcore_coredrp_admission_retired_generation_high_water` | gauge | `sender,lane,producer` | compact retired-generation high-water |
| `miningcore_coredrp_temporal_policy_reconciliation_active` | gauge | `pool` | retroactive policy reconciliation blocks frontier advancement |

`reason` and `state` come from closed enums. `producer` is a bounded configured producer ordinal/alias, never raw arbitrary caller input. Implementations MAY add metrics under the prefix but MUST NOT change the type/meaning/required labels of these entries within the profile version.
