# CoreDRP/1 Draft 0.5 semantic-contract registry

This registry is normative under Section 1 of `CoreDRP-1-SPEC-0.5.md`.

## Mining Profile 1.1

Canonical source bytes:

`uint16_be(profile_id_len) || "coredrp.mining" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint8(payout_scheme) || uint16_be(coin_id_len) || coin_id_ascii || uint16_be(network_id_len) || network_id_ascii || uint16_be(completeness_policy_version) || uint16_be(retention_policy_version) || uint8(cross_sender_ordering_policy) || uint32_be(permitted_clock_skew_ms) || uint32_be(max_clock_step_ms) || uint32_be(probe_interval_ms) || uint32_be(probe_processing_max_ms) || uint32_be(evidence_expiry_ms) || uint32_be(unknown_grace_ms) || uint16_be(admission_idempotency_policy_version)`

Draft 0.5 requires `admission_idempotency_policy_version = 2`, meaning permanent financial tombstones in namespace `(sender_id,lane_id,caller_admission_key)`. No finite horizon field appears in Profile 1.1.

Reference btc1 source bytes:

`000e636f72656472702e6d696e696e670000000100000001000462746331010007626974636f696e00076d61696e6e65740002000101000007d0000000fa00001388000000fa00003a980001d4c00002`

SHA-256:

`ce91f9fbec9c1ed1a87e30231f77ba22f1ec14042abe19c8602f11943fbd73bc`

## Miningcore Profile 1.1

Canonical source bytes:

`uint16_be(profile_id_len) || "coredrp.miningcore" || uint32_be(1) || uint32_be(1) || uint16_be(scope_len) || scope || uint32_be(accounting_schema_version) || uint32_be(persistence_schema_version) || uint16_be(direct_candidate_validation_version) || uint16_be(settlement_policy_version)`

Draft 0.5 requires `direct_candidate_validation_version >= 2` for duplicate-txid rejection and declared consensus-commitment output classification.

Reference btc1 source bytes:

`0012636f72656472702e6d696e696e67636f72650000000100000001000462746331000000010000000100020001`

SHA-256:

`b1d788efea7814d3c43f1e5a1d2cafdde14e259361824bf25ac2e14784afa1d7`

## Sorting and string rules

Profile IDs, coin IDs and network IDs are ASCII. Every canonical sort in contract binding is over raw byte strings, not locale or platform string ordering. Non-ASCII profile IDs are invalid at handshake.
