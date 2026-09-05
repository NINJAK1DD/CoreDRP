# CoreDRP Mining Temporal Policy Registry — Draft 0.6 Profile Freeze

**Status:** normative Mining Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md` and defines lifecycle, staging, effective-time, reconciliation and evidence rules for temporal sender membership and completeness mode.

## 1. Durable policy generations

Every Mining scope has a monotonically increasing unsigned 64-bit `policy_generation`, starting at 1. A policy generation contains the complete ordered temporal membership/mode delta activated by one ADMIN transition.

Policy generation MUST NOT wrap. At `2^64-1`, no further ordinary activation is possible under this profile version.

Each scope's first explicit temporal policy generation also creates immutable `scope_safety_origin_unix_ms`, equal to the earliest boundary from which payout safety is intended to be proven. The origin MUST NOT be moved backward by an ordinary policy change. Retroactive repair uses the reconciliation path and never invents safety before the durable origin.

### 1.1 Bootstrap generation and initial payout frontier

A scope with no durable temporal-policy generation is in `NO_POLICY` state. In that state `PayoutSafeThrough(scope)` is not yet defined and MUST NOT be consulted as an integer or replaced with an implementation-local sentinel.

The first policy generation is a special deterministic bootstrap transition:

- `policy_generation` MUST equal `1`;
- there MUST be no prior membership interval and no prior completeness-mode interval for the scope;
- the action MUST establish the initial completeness mode using `COMPLETENESS_MODE_CHANGE` from `NO_POLICY` to exactly `NO_RELAY_REQUIRED`; direct bootstrap into `RELAY_REQUIRED` is `ADMIN_ACTION_CONFLICT`;
- `effective_unix_ms` MUST equal the new immutable `scope_safety_origin_unix_ms` exactly;
- the origin MUST be within the Core production event-time range;
- `RequiredStagingSender` for this `NO_POLICY -> initial mode` transition is the empty set because no membership interval is permitted before the origin;
- the bootstrap transition is exempt from the two `PayoutSafeThrough` comparisons in Section 5 because no prior payout frontier exists; every other staging, digest, generation, authorization, audit, future-effective, and atomicity rule still applies.

On successful atomic bootstrap commit, the receiver durably initializes `PayoutSafeThrough(scope) = scope_safety_origin_unix_ms - 1` as the empty-proven-interval predecessor marker defined by the settlement registry.

No other first-generation action is valid. To begin relay-required operation, bootstrap explicitly into `NO_RELAY_REQUIRED`, stage initial `MEMBERSHIP_START` generations, then stage `NO_RELAY_REQUIRED -> RELAY_REQUIRED` at a later clean boundary using Sections 2–5. The membership set at that boundary MUST be nonempty; a transition to `RELAY_REQUIRED` with no members is `ADMIN_ACTION_CONFLICT`. Membership may begin while mode is `NO_RELAY_REQUIRED`. No relay-dependent settlement may be attributed to the initial no-relay interval merely to bypass completeness. A deployment requiring relay from its first operational millisecond MUST complete this administrative setup before accepting that workload.

Each durable policy record stores at least scope, generation, effective time, action/correction kind, affected sender when applicable, prior/new evidence, ADMIN identity/digest, receiver state version, required/observed staging acknowledgements, activation result and audit reason.

## 2. Deterministic sender staging requirement

Core wire does not distribute Mining temporal policy. Policy distribution is an authenticated out-of-band ADMIN prerequisite.

Define `RequiredStagingSender(Q, change, T)` from durable policy state immediately before the proposed boundary `T`:

- bootstrap `COMPLETENESS_MODE_CHANGE(Q, NO_POLICY -> initial_mode, T)`: exactly the empty set;
- `MEMBERSHIP_START(Q,S,T)`: exactly `{S}`;
- `MEMBERSHIP_END(Q,S,T)`: exactly `{S}`;
- `COMPLETENESS_MODE_CHANGE(Q, RELAY_REQUIRED -> NO_RELAY_REQUIRED, T)`: every sender whose membership interval for `Q` contains `T-1`;
- `COMPLETENESS_MODE_CHANGE(Q, NO_RELAY_REQUIRED -> RELAY_REQUIRED, T)`: every sender whose membership interval for `Q` contains `T` under the new generation;
- a mode change where old mode equals new mode is invalid/no-op and MUST NOT create a generation.

The set is derived from durable temporal membership, not connection state, certificate transport authorization, currently active streams, or operator-supplied arbitrary lists.

For any ordinary change:

1. construct the exact generation and effective time;
2. stage the identical generation on every sender in `RequiredStagingSender`;
3. each sender records `(scope,generation,effective_unix_ms,policy_digest32)` and returns authenticated staging acknowledgement;
4. receiver recomputes `RequiredStagingSender`, records it, and verifies every required acknowledgement matches the exact digest;
5. only then may receiver activate the policy generation.

A missing/mismatched acknowledgement is `ADMIN_ACTION_CONFLICT`; old policy remains active.

At/after membership end, the sender stops new payout-relevant admission for that scope before returning local success. A sender entering RELAY_REQUIRED begins admission/checkpoint obligations at the same effective boundary.

## 3. Policy staging digest and exact evidence encoding

The staging digest is:

`SHA256("CoreDRP1-ADMIN" || uint16_be(0x0106) || uint32_be(body_len) || body)`

where body is:

`uint16_be(1) || uint16_be(6)`
`|| field(1, scope_bytes)`
`|| field(2, uint64_be(policy_generation))`
`|| field(3, int64_be(effective_unix_ms))`
`|| field(4, uint8(policy_kind))`
`|| field(5, sender_uuid16_or_zero_length)`
`|| field(6, staged_policy_evidence_v1)`.

`field(id,value) = uint16_be(id) || uint32_be(len(value)) || value` in strictly increasing order.

Field 5 is exactly 16 RFC 9562 bytes for membership kinds and zero length for mode change.

`StagedPolicyEvidenceV1` is:

`uint16_be(1)`
`|| uint8(policy_kind)`
`|| uint16_be(scope_len) || scope`
`|| uint8(has_sender) || [sender_uuid16]`
`|| int64_be(effective_unix_ms)`
`|| uint8(has_mode) || [uint8(mode)]`
`|| uint64_be(policy_generation)`.

- MEMBERSHIP_START (`1`): sender required, mode absent;
- MEMBERSHIP_END (`2`): sender required, mode absent;
- COMPLETENESS_MODE_CHANGE (`3`): sender absent, mode required (`1=RELAY_REQUIRED`, `2=NO_RELAY_REQUIRED`).

Duplicated scope/kind/sender/time/generation inside evidence MUST exactly equal the enclosing staging body. Any mismatch is malformed staging evidence and causes ADMIN activation failure.

This grammar is distinct from reconciliation `PolicyEvidenceV1`.

## 4. Applicable clock uncertainty

Ordinary policy activation uses one exact conservative function.

For proposed change `(Q,change,T)`, let `R = RequiredStagingSender(Q,change,T)`.

For each `S in R`, define `SkewTransition(S,Q,change,T)`:

- **activation/addition** (`MEMBERSHIP_START` or `NO_RELAY_REQUIRED -> RELAY_REQUIRED`): use the effective multi-scope permitted skew after applying the proposed scope-set/policy change;
- **deactivation/removal** (`MEMBERSHIP_END` or `RELAY_REQUIRED -> NO_RELAY_REQUIRED`): use the effective multi-scope permitted skew immediately before `T` while `Q` is still active/required. If a post-change effective skew also exists, use `max(pre_change_skew, post_change_skew)`; the value MUST never become undefined merely because `Q` was the sender's last active clock-governed scope;
- bootstrap with `R` empty: no skew value is required.

This freezes the last-scope removal edge: a sender's final membership/RELAY_REQUIRED scope can be ended using its pre-change clock contract rather than failing because the post-change reducer has no active scope.

Define:

`applicable_clock_uncertainty_ms(Q,change,T) = 2 * max(SkewTransition(S,Q,change,T) for S in R)`.

If `R` is empty, uncertainty is `0`.

The multiplication and addition are checked against the Core production-time range. Unknown/missing **required pre-change or post-change** clock contract data under the rules above fails closed; implementations MUST NOT substitute a receiver-local default.

This is intentionally the same symmetric `2S` uncertainty used by cross-sender completeness. A tighter observed offset interval does not reduce ordinary ADMIN policy separation in Profile 1.1.

## 5. Ordinary effective-time restrictions

This section applies to policy generations `>= 2`. Generation 1 uses the bootstrap rule in Section 1.1.

Ordinary changes MUST be future-effective and satisfy:

- `effective_unix_ms > PayoutSafeThrough(scope)`;
- `effective_unix_ms > PayoutSafeThrough(scope) + applicable_clock_uncertainty_ms(scope,change,effective_unix_ms)`.

Overflow fails closed.

For membership end at `valid_until`, trusted completeness through at least `valid_until - 1` is required for already-required relay history, otherwise explicit uncertainty is created and the operation is not an ordinary clean end.

## 6. Temporal-policy reconciliation correction kinds

`TEMPORAL_POLICY_RECONCILIATION.correction_kind`:

1. INSERT_MISSING_MEMBERSHIP_INTERVAL
2. REPLACE_MEMBERSHIP_INTERVAL
3. CORRECT_MEMBERSHIP_END
4. REPLACE_COMPLETENESS_MODE_INTERVAL
5. REMOVE_ERRONEOUS_MEMBERSHIP_INTERVAL
6. REMOVE_ERRONEOUS_MODE_INTERVAL

Other values are invalid. Membership corrections require sender UUID; mode corrections require sender absent.

## 7. Canonical reconciliation policy evidence bytes

`PolicyEvidenceV1`:

`uint16_be(1)`
`|| uint8(evidence_kind)`
`|| uint16_be(scope_len) || scope`
`|| uint8(has_sender) || [sender_uuid16]`
`|| int64_be(valid_from_unix_ms)`
`|| uint8(has_valid_until) || [int64_be(valid_until_unix_ms)]`
`|| uint8(has_mode) || [uint8(mode)]`
`|| uint64_be(policy_generation)`.

`evidence_kind`: 1 MEMBERSHIP_INTERVAL, 2 COMPLETENESS_MODE_INTERVAL.

Presence rules:

- membership: sender required, mode absent;
- mode: sender absent, mode required;
- present `valid_until > valid_from`;
- scope equals ADMIN scope exactly.

Cross-field correction rules:

- ADMIN field 9 `policy_generation` MUST equal the generation in every present **new** evidence record;
- INSERT: prior absent, new present;
- REMOVE: prior present, new absent;
- REPLACE: prior/new present and prior must match exactly one durable interval being superseded;
- CORRECT_MEMBERSHIP_END: prior/new are membership evidence for same scope, sender, `valid_from`, and prior generation identity; only `valid_until` and new policy generation may change;
- after applying any correction, the resulting membership intervals for one `(scope,sender)` MUST be non-overlapping and canonically ordered, and completeness-mode history for one scope MUST be non-overlapping with exactly one effective mode at any covered time;
- a correction that would create ambiguous overlap is `ADMIN_ACTION_CONFLICT`.

## 8. Reconciliation mutation semantics

The receiver transaction validates idempotency/state version, parses evidence, locks exact policy history, verifies prior evidence byte-for-byte where required, records append-only correction/audit edges, applies the corrected interval set, records the affected range as `POLICY_RECONCILIATION_PENDING`, and commits atomically.

Only verified replay/reconciliation restoring all required evidence clears the scalar-frontier block. Waiver or settlement override MUST NOT clear it, advance `PayoutSafeThrough`, or authorize destructive pruning across unproven history.

## 9. Settlement consequences

A named operational override may permit settlement where the settlement registry allows it, but does not rewrite historical safety, convert uncertainty into evidence, or clear policy reconciliation.

## 10. Future portion of reconciliation

Retroactive correction is receiver/operator repair. If a reconciliation also changes sender behavior at a future boundary, that future portion MUST independently satisfy Sections 2–5 staging and timing rules.
