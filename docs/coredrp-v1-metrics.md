# CoreDRP/1 Miningcore Metrics — Draft 0.1

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

Miningcore metrics use the `miningcore_coredrp_` prefix.

Planned stable metrics include:

- `miningcore_coredrp_connected{sender,lane}`
- `miningcore_coredrp_spool_events{sender,lane}`
- `miningcore_coredrp_spool_bytes{sender,lane}`
- `miningcore_coredrp_spool_oldest_record_age_seconds{sender,lane}`
- `miningcore_coredrp_fsync_seconds{lane}`
- `miningcore_coredrp_sequencer_queue_depth{lane}`
- `miningcore_coredrp_sequencer_wait_seconds{lane}`
- `miningcore_coredrp_acked_sequence{sender,lane}`
- `miningcore_coredrp_durable_tail_sequence{sender,lane}`
- `miningcore_coredrp_replay_total{sender,lane}`
- `miningcore_coredrp_reconnect_total{sender,lane}`
- `miningcore_coredrp_window_blocked_seconds_total{sender,lane}`
- `miningcore_coredrp_recovery_gap{sender,lane}`
- `miningcore_coredrp_quarantined_events_total{sender,lane,scope}`
- `miningcore_coredrp_retention_truncated_total{sender,lane}`
- `miningcore_coredrp_clock_bound_state{sender,lane}`
- `miningcore_coredrp_clock_unknown_grace_remaining_seconds{sender,lane}`
- `miningcore_coredrp_clock_recovery_wait_seconds{sender,lane}`
- `miningcore_coredrp_blocks_blocked_on_fence{pool}`
- `miningcore_coredrp_safe_prune_lag_seconds{pool}`
- `miningcore_coredrp_unresolved_completeness_gaps{pool}`

Exact types, labels, and help strings are frozen in v0.2 before dashboards are considered stable.
