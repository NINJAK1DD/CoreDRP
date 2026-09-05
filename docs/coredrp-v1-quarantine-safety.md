# CoreDRP Financial Quarantine Safety Registry — Draft 0.6

**Status:** normative Mining 1.1 / Miningcore 1.1 registry

A Core quarantine advances immutable relay history without applying the quarantined event's ordinary semantic effect. For financial events, that is explicit uncertainty rather than completeness.

## 1. Payout-significant event classes

The following quarantined events are payout-significant:

- Mining share `0x0100` on lane 0;
- Miningcore accounting share `0x0200` on lane 0;
- any event explicitly referenced by a live settlement proof/dependency set;
- any future event type whose incorporated profile registry marks it payout-significant.

Critical-lane candidate/state events are not automatically share-window evidence, but remain payout-significant when a settlement proof depends on them.

## 2. Lifecycle

Each payout-significant quarantine has exactly one safety state:

- `UNRESOLVED`;
- `RESOLVED_RECONCILED`;
- `RESOLVED_WAIVED`.

`QUARANTINE_AND_ADVANCE` creates or retains `UNRESOLVED` state. ACKing the immutable event does not apply its financial effect and does not change this state.

The only Profile 1.1 state transitions are:

- `UNRESOLVED -> RESOLVED_RECONCILED` via ADMIN `0x0008 QUARANTINE_RECONCILIATION`;
- `UNRESOLVED -> RESOLVED_WAIVED` via ADMIN `0x0009 QUARANTINE_WAIVER`.

`RESOLVED_RECONCILED` and `RESOLVED_WAIVED` are terminal safety states. An idempotent retry of the same ADMIN action returns its stored result; a different transition request is `ADMIN_ACTION_CONFLICT`.

### UNRESOLVED

Every settlement whose dependency set intersects the affected event/range has `SettlementSafe = false`. The contiguous payout frontier cannot cross the earliest affected point.

### RESOLVED_RECONCILED

A versioned validator/profile authority has revalidated the same immutable event and the required durable financial effect has been applied atomically with the reconciliation transition. Affected settlements may then be re-evaluated.

### RESOLVED_WAIVED

The operator accepts the missing ordinary financial effect for audit/operations. The affected range remains non-PayoutSafe and cannot become `SettlementSafe` merely because of the waiver. A separate named settlement override may authorize one settlement operationally but creates no safety proof.

## 3. Canonical reconciliation evidence

A reconciliation never edits the quarantined Core event. It proves that the **same immutable payload** now has a deterministic financial interpretation under a named semantic authority.

Let:

- `payload_hash32` be the Core event payload hash already committed by the event chain;
- `validator_profile_digest32` be the exact 32-byte digest/version authority named by ADMIN field 11;
- `mining_scope_contract_digest32` be the selected Mining digest for the financial effect scope;
- `miningcore_scope_contract_digest32` be the selected Miningcore digest for that scope, or 32 zero bytes only for a pure Mining `0x0100` effect with no Miningcore contract;
- the immutable identity fields be sender UUID, lane, epoch UUID, sequence, relay-event UUID, event type and chain hash from the quarantine record.

For each payout-effect scope `Q` produced by the event, define:

`ReconciledEffectEvidenceV1(Q) =`

`uint16_be(1)`
`|| sender_uuid16`
`|| uint8(lane)`
`|| epoch_uuid16`
`|| uint64_be(sequence)`
`|| relay_event_uuid16`
`|| uint16_be(event_type)`
`|| chain_hash32`
`|| uint16_be(scope_len) || scope`
`|| payload_hash32`
`|| validator_profile_digest32`
`|| mining_scope_contract_digest32`
`|| miningcore_scope_contract_digest32`.

All widths/ranges are validated before encoding. Scope bytes are exact ASCII Mining scope bytes. No protobuf serialization, database row encoding, JSON, locale text or implementation-specific metadata enters this evidence.

For an event with one effect scope, ADMIN field 12 `corrected_effect_digest` is:

`SHA256(ReconciledEffectEvidenceV1(Q))`.

For an event with multiple payout-effect scopes, construct one evidence record per scope, sort records by raw scope bytes, reject duplicate scopes, and define:

`corrected_effect_digest = SHA256(uint16_be(scope_count) || repeated(uint32_be(record_len) || record_bytes))`.

This digest identifies the immutable event plus the exact semantic authority/contracts under which its missing financial effects are being applied. The actual application-effect writes remain governed by the profile registry and MUST commit atomically with the transition; matching this digest alone never substitutes for applying those effects.

## 4. Reconciliation transaction

ADMIN `QUARANTINE_RECONCILIATION` MUST:

1. lock the named quarantine and verify immutable identity;
2. require current state `UNRESOLVED`;
3. verify `validator_profile_digest32` is an allowed current authority for revalidation;
4. re-run the versioned/profile semantic validator against the original immutable payload;
5. derive `PayoutEffectScopes` and recompute `corrected_effect_digest` exactly as Section 3;
6. apply every missing financial effect idempotently under the selected scope contracts;
7. write effect rows, reconciliation evidence, affected settlement dependencies, quarantine state transition and receiver state-version increment in one durable transaction;
8. COMMIT before reporting success.

Failure at any step leaves state/effects unchanged and emits no partial reconciliation result.

## 5. Waiver transaction

ADMIN `QUARANTINE_WAIVER` MUST lock/verify the same immutable identity, require current `UNRESOLVED`, append operator/reason audit evidence, transition to `RESOLVED_WAIVED` atomically, and retain the original effect-absence evidence. It MUST NOT apply a synthetic effect or change any safety proof.

## 6. Durable evidence

A quarantine safety record contains at least scope set, sender/lane/epoch/sequence, relay-event ID, event type, immutable payload hash and chain hash, reason, validator/profile authority, affected conservative time/range, settlement references, state, reconciliation/waiver ADMIN identity/digest, corrected-effect digest when reconciled, and receiver state version.

The audit record is never destructively pruned while any settlement/proof or operator audit requirement depends on it.

## 7. Pruning

A reconciled quarantine may cease blocking settlement-specific pruning only after its corrected financial effect and proof record are durable. A waived quarantine's audit record is permanent for the lifetime of the financial history it affects, but it does not force unrelated later evidence outside every live dependency interval to be retained forever.
