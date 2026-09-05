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

### UNRESOLVED

Every settlement whose dependency set intersects the affected event/range has `SettlementSafe = false`. The contiguous payout frontier cannot cross the earliest affected point.

### RESOLVED_RECONCILED

A versioned validator/profile correction or audited reconciliation has produced the required durable financial effect while preserving immutable Core history and proof identity. Affected settlements may then be re-evaluated.

### RESOLVED_WAIVED

The operator accepts the missing ordinary financial effect for audit/operations. The affected range remains non-PayoutSafe and cannot become `SettlementSafe` merely because of the waiver. A separate named settlement override may authorize one settlement operationally but creates no safety proof.

## 3. Durable evidence

A quarantine safety record contains at least scope, sender/lane/epoch/sequence, relay-event ID, event type, immutable chain hash, reason, validator/profile version, affected conservative time/range, settlement references, state, reconciliation/waiver ADMIN identity, and receiver state version.

The audit record is never destructively pruned while any settlement/proof or operator audit requirement depends on it.

## 4. Pruning

A reconciled quarantine may cease blocking settlement-specific pruning only after its corrected financial effect and proof record are durable. A waived quarantine's audit record is permanent for the lifetime of the financial history it affects, but it does not force unrelated later evidence outside every live dependency interval to be retained forever.
