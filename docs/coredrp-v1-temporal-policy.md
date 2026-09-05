# CoreDRP Mining Temporal Policy Registry — Draft 0.6 Freeze Completion

**Status:** normative Mining Profile 1.1 registry

This registry is incorporated by `coredrp-v1-draft06-contracts.md` and defines the lifecycle, staging, effective-time, reconciliation and evidence rules for temporal sender membership and completeness mode.

## 1. Durable policy generations

Every Mining scope has a monotonically increasing unsigned 64-bit `policy_generation`, starting at 1. A policy generation contains the complete ordered temporal membership/mode delta being activated by one ADMIN transition.

Policy generation MUST NOT wrap. If generation is `2^64-1`, no further ordinary policy activation is possible under this profile version; operation fails closed pending a future profile revision/migration.

Each durable policy record stores at least:

- scope;
- policy_generation;
- effective_unix_ms;
- action/correction kind;
- affected sender when applicable;
- old interval/value evidence;
- new interval/value evidence;
- ADMIN idempotency UUID/digest;
- receiver state version;
- staging acknowledgements required and observed;
- activation result;
- audit reason.

## 2. Sender staging requirement

Core wire does not distribute Mining temporal policy. Therefore policy distribution is explicitly an out-of-band ADMIN prerequisite and MUST be coordinated before a policy becomes effective.

For any MEMBERSHIP_START, MEMBERSHIP_END, or COMPLETENESS_MODE_CHANGE that can alter whether a sender may admit payout-relevant events or whether its checkpoints are required:

1. operator constructs the exact new policy generation and effective time;
2. the identical generation is durably staged on every affected sender before receiver activation;
3. each affected sender records `(scope, policy_generation, effective_unix_ms, policy_digest32)` and returns an authenticated administrative staging acknowledgement;
4. the receiver ADMIN transaction records the required sender set and verifies all required staging acknowledgements match the exact policy digest;
5. only then may the receiver activate the policy generation.

A policy MUST NOT become effective at the receiver when any affected sender lacks the identical staged generation.

Sender-side sequencers consult the staged policy at admission time. At/after an effective membership end, a sender MUST stop admitting payout-relevant events for that scope before returning local success. A sender newly entering RELAY_REQUIRED MUST begin participating in the checkpoint/membership regime at the same effective boundary.

If staging cannot be completed, the ADMIN action fails with `ADMIN_ACTION_CONFLICT`; the old policy remains active. No correctly persisted event is intentionally created into a receiver policy that would deterministically reject it.

## 3. Policy staging digest and exact evidence encoding

The staging digest is:

`SHA256("CoreDRP1-ADMIN" || uint16_be(0x0106) || uint32_be(body_len) || body)`

where body is the canonical policy-generation body:

`uint16_be(1)`
`|| uint16_be(6)`
`|| field(1, scope_bytes)`
`|| field(2, uint64_be(policy_generation))`
`|| field(3, int64_be(effective_unix_ms))`
`|| field(4, uint8(policy_kind))`
`|| field(5, sender_uuid16_or_zero_length)`
`|| field(6, staged_policy_evidence_v1)`.

`field(id,value) = uint16_be(id) || uint32_be(len(value)) || value` and fields are already in strictly increasing ID order.

Field 5 presence is represented by length: membership kinds MUST use exactly 16 RFC 9562 sender bytes; COMPLETENESS_MODE_CHANGE MUST use zero-length field 5. No alternate absent encoding is permitted.

Field 6 is exact `StagedPolicyEvidenceV1`:

`uint16_be(1)`
`|| uint8(policy_kind)`
`|| uint16_be(scope_len) || scope`
`|| uint8(has_sender) || [sender_uuid16]`
`|| int64_be(effective_unix_ms)`
`|| uint8(has_mode) || [uint8(mode)]`
`|| uint64_be(policy_generation)`.

Presence and semantic rules are exhaustive:

- MEMBERSHIP_START (`policy_kind=1`): `has_sender=1`, sender REQUIRED, `has_mode=0`; effect is to begin membership at `effective_unix_ms` for that sender/scope;
- MEMBERSHIP_END (`policy_kind=2`): `has_sender=1`, sender REQUIRED, `has_mode=0`; effect is to end the currently open matching membership interval at `effective_unix_ms`;
- COMPLETENESS_MODE_CHANGE (`policy_kind=3`): `has_sender=0`, sender absent, `has_mode=1`, mode REQUIRED and exactly `1=RELAY_REQUIRED` or `2=NO_RELAY_REQUIRED`; effect is to end the currently open mode interval and begin the requested mode at `effective_unix_ms`;
- any other presence combination, mode value, policy kind, scope mismatch, generation mismatch, or effective-time mismatch is `MALFORMED_FRAME` for staged evidence and causes the receiver ADMIN transition to fail `ADMIN_ACTION_CONFLICT` rather than activate mismatched staged policy.

The scope, policy kind, sender, effective time and generation encoded inside `StagedPolicyEvidenceV1` MUST equal fields 1–5 of the enclosing staging body exactly. This deliberate duplication is self-checking and prevents an acknowledgement digest from being replayed against a differently interpreted policy body.

This staging grammar is distinct from reconciliation-only `PolicyEvidenceV1` in Section 7: staging describes one future ordinary operation; reconciliation evidence describes complete historical intervals before/after correction. Implementations MUST NOT substitute one grammar for the other.

The `0x0106` domain-local discriminator is reserved by this registry solely for policy staging digests and MUST NOT be used as an executable receiver mutation without a future ADMIN-registry allocation.

## 4. Ordinary policy kinds

| Value | Meaning |
|---:|---|
| 1 | MEMBERSHIP_START |
| 2 | MEMBERSHIP_END |
| 3 | COMPLETENESS_MODE_CHANGE |
| other | invalid |

Completeness mode values:

| Value | Meaning |
|---:|---|
| 1 | RELAY_REQUIRED |
| 2 | NO_RELAY_REQUIRED |
| other | invalid |

## 5. Ordinary effective-time restrictions

Ordinary changes MUST be future-effective and satisfy both:

- `effective_unix_ms > PayoutSafeThrough(scope)`;
- `effective_unix_ms > PayoutSafeThrough(scope) + applicable_clock_uncertainty_ms` using checked arithmetic.

The second condition is the effective rule; the first is stated explicitly to make zero-uncertainty behavior obvious. Overflow fails closed.

For membership end at `valid_until`, the sender and receiver require trusted completeness through at least `valid_until - 1` for already-required relay history, or the transition creates explicit uncertainty/gap and cannot be treated as ordinary clean end.

## 6. Temporal-policy reconciliation correction kinds

`TEMPORAL_POLICY_RECONCILIATION` field 5 `correction_kind` has exactly these values:

| Value | Meaning |
|---:|---|
| 1 | INSERT_MISSING_MEMBERSHIP_INTERVAL |
| 2 | REPLACE_MEMBERSHIP_INTERVAL |
| 3 | CORRECT_MEMBERSHIP_END |
| 4 | REPLACE_COMPLETENESS_MODE_INTERVAL |
| 5 | REMOVE_ERRONEOUS_MEMBERSHIP_INTERVAL |
| 6 | REMOVE_ERRONEOUS_MODE_INTERVAL |
| other | invalid / `MALFORMED_FRAME` |

Membership corrections require sender UUID. Mode corrections require sender UUID absent.

## 7. Canonical reconciliation policy evidence bytes

`prior_policy_evidence` and `new_policy_evidence` are not opaque. They use canonical `PolicyEvidenceV1`:

`uint16_be(1)`
`|| uint8(evidence_kind)`
`|| uint16_be(scope_len) || scope`
`|| uint8(has_sender) || [sender_uuid16]`
`|| int64_be(valid_from_unix_ms)`
`|| uint8(has_valid_until) || [int64_be(valid_until_unix_ms)]`
`|| uint8(has_mode) || [uint8(mode)]`
`|| uint64_be(policy_generation)`.

`evidence_kind`:

- 1 = MEMBERSHIP_INTERVAL;
- 2 = COMPLETENESS_MODE_INTERVAL.

Presence rules:

- MEMBERSHIP_INTERVAL: sender REQUIRED, mode absent;
- COMPLETENESS_MODE_INTERVAL: sender absent, mode REQUIRED;
- `valid_until`, when present, MUST be greater than `valid_from`;
- scope MUST equal ADMIN field 3 scope exactly;
- prior evidence generation identifies the existing durable record being corrected;
- new evidence generation is the generation being inserted/activated by reconciliation.

For INSERT corrections, prior evidence field is zero-length and new evidence is present. For REMOVE corrections, prior evidence is present and new evidence is zero-length. For REPLACE/CORRECT corrections, both are present.

## 8. Reconciliation mutation semantics

The reconciliation ADMIN transaction:

1. validates idempotency and expected state version;
2. parses prior/new evidence with Section 7 grammar;
3. locks the exact scope policy history;
4. verifies prior evidence matches the durable record byte-for-byte where required;
5. records the correction and historical affected interval;
6. applies the corrected interval set while preserving append-only audit history;
7. marks the affected historical range `POLICY_RECONCILIATION_PENDING`;
8. blocks advancement of `PayoutSafeThrough(scope)` across or beyond the affected uncertainty until verified replay/reconciliation establishes all completeness evidence required by the corrected policy;
9. commits mutation, audit, state version and stored ADMIN result atomically.

Only verified reconciliation that restores the required evidence clears the scalar-frontier reconciliation block for the affected range. `RESOLVED_WAIVED`, `GAP_WAIVER`, or `SETTLE_WITHOUT_FENCE_OVERRIDE` MUST NOT clear that scalar block and MUST NOT permit `PayoutSafeThrough` to cross unproven history. They may affect operational settlement handling only as defined by the settlement registry.

A reconciliation never deletes the prior audit record. It supersedes its policy interpretation through an explicit correction edge.

## 9. Settlement consequences

Reconciliation can restore normal scalar safety only after required event/checkpoint evidence is re-evaluated under the corrected policy and any newly required missing history is reconciled.

A policy waiver or settlement override may permit a specifically named operational settlement where the settlement registry allows it, but it does not clear `POLICY_RECONCILIATION_PENDING`, rewrite historical `PayoutSafeThrough`, convert unproven history into safe evidence, or authorize destructive pruning across that uncertainty.

## 10. Sender staging and reconciliation

A retroactive reconciliation does not pretend affected senders could have known the corrected past policy. It is receiver/operator repair of historical policy and must record that fact.

For a future portion of a reconciliation that changes sender behavior going forward, the new policy generation MUST still satisfy Section 2 staging before its future effective boundary.
