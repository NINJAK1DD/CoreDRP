# CoreDRP/1 Miningcore Metrics — Draft 0.6 Final Profile Freeze

**Originally designed and authored by Rob Cooke, 2026.**  
Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

This registry is normative for the Miningcore Integration Profile. Metric names use the `miningcore_coredrp_` prefix. Labels MUST be stable bounded-cardinality identifiers only. Miner, worker, source IP, relay-event ID, epoch UUID, chain hash, arbitrary error text, caller admission key and raw producer UUID MUST NOT be labels.

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
| `miningcore_coredrp_financial_quarantine_unresolved` | gauge | `pool` | payout-significant quarantines still UNRESOLVED |
| `miningcore_coredrp_financial_quarantine_reconciled_total` | counter | `pool` | canonical QUARANTINE_RECONCILIATION transitions committed |
| `miningcore_coredrp_financial_quarantine_waived_total` | counter | `pool` | canonical QUARANTINE_WAIVER transitions committed |
| `miningcore_coredrp_retention_truncated_total` | counter | `sender,lane` | ACKed retention truncations |
| `miningcore_coredrp_clock_bound_state` | gauge | `sender,lane,state` | one-hot GOOD/BAD/UNKNOWN/RECOVERING state |
| `miningcore_coredrp_clock_evidence_age_seconds` | gauge | `sender,lane` | sender-local monotonic age of active probe-backed clock evidence |
| `miningcore_coredrp_clock_evidence_remaining_seconds` | gauge | `sender,lane` | freshness remaining after sender-local probe-age reduction |
| `miningcore_coredrp_clock_unknown_grace_remaining_seconds` | gauge | `sender,lane` | remaining non-extending UNKNOWN grace |
| `miningcore_coredrp_clock_recovery_wait_seconds` | gauge | `sender,lane` | BAD/RECOVERING wait |
| `miningcore_coredrp_blocks_blocked_on_fence` | gauge | `pool` | settlement-blocked blocks |
| `miningcore_coredrp_payout_safe_through_unix_seconds` | gauge | `pool` | contiguous receiver-proven payout frontier |
| `miningcore_coredrp_safe_prune_through_unix_seconds` | gauge | `pool` | safe destructive-prune frontier |
| `miningcore_coredrp_safe_prune_lag_seconds` | gauge | `pool` | lag to safe prune frontier |
| `miningcore_coredrp_settlement_safe_total` | counter | `pool,scheme,result` | settlement-specific safety decisions; result is closed `safe|unsafe|override` |
| `miningcore_coredrp_settlement_summary_records` | gauge | `pool` | retained SettlementEvidenceSummaryV1 records |
| `miningcore_coredrp_settlement_prune_blocked_missing_summary` | gauge | `pool` | final evidence cannot prune because required V1 summary is absent |
| `miningcore_coredrp_unresolved_completeness_gaps` | gauge | `pool` | unresolved payout-relevant gaps |
| `miningcore_coredrp_waived_completeness_ranges` | gauge | `pool` | waived ranges that remain non-PayoutSafe and cap the contiguous scalar frontier |
| `miningcore_coredrp_epoch_abandon_total` | counter | `sender,lane` | exceptional epoch abandonments |
| `miningcore_coredrp_receiver_identity_change_total` | counter | `sender,lane` | receiver-ID change detections |
| `miningcore_coredrp_receiver_incarnation_change_total` | counter | `sender,lane` | database-incarnation changes |
| `miningcore_coredrp_admission_idempotency_conflict_total` | counter | `lane` | active key reused with different digest |
| `miningcore_coredrp_admission_registered_producers` | gauge | `sender,lane,scope` | bounded registered producer count |
| `miningcore_coredrp_admission_generation_records` | gauge | `sender,lane,scope,producer` | detailed records in active producer generation |
| `miningcore_coredrp_admission_generation_bytes` | gauge | `sender,lane,scope,producer` | durable bytes used by active generation detail |
| `miningcore_coredrp_admission_generation` | gauge | `sender,lane,scope,producer` | current producer generation |
| `miningcore_coredrp_admission_retired_generation_high_water` | gauge | `sender,lane,scope,producer` | compact retired-generation high-water |
| `miningcore_coredrp_temporal_policy_generation` | gauge | `pool` | active policy generation |
| `miningcore_coredrp_temporal_policy_staging_pending` | gauge | `pool` | future policy generation waiting for sender staging acknowledgements |
| `miningcore_coredrp_temporal_policy_reconciliation_active` | gauge | `pool` | retroactive policy reconciliation blocks scalar frontier advancement |
| `miningcore_coredrp_profile_migration_live_dependencies` | gauge | `pool,dependency` | live dependency classes preventing NoLiveDependencies closure; dependency is a closed registry value |
| `miningcore_coredrp_projection_scope_access_failures_total` | counter | `pool,reason` | embedded projection rejected for closed reason `unauthorized|membership` |

`reason`, `state`, `scheme`, `result` and `dependency` come from closed enums/registries. `producer` is a bounded configured producer ordinal/alias, never raw arbitrary caller input. Implementations MAY add metrics under the prefix but MUST NOT change the type/meaning/required labels of these entries within the profile version.
