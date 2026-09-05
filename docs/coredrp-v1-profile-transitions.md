# CoreDRP Mining Profile Contract-Transition Registry — Draft 0.6

**Status:** normative Mining 1.1 / Miningcore 1.1 registry

This registry defines successor-epoch semantic-contract transition barriers. An epoch UUID change is not permission to reinterpret unsettled financial history.

## 1. Transition classification

For each scope, compare the old and successor selected Mining and Miningcore semantic-contract digests.

### SAME

Both digests are byte-identical. Ordinary epoch rollover is permitted subject to Core epoch rules.

### EXPLICITLY_COMPATIBLE

A future registry version may name a specific old/new digest pair and an exact migration algorithm. Profile 1.1 defines no such non-identical compatible pair.

### FINANCIALLY_INCOMPATIBLE

Any non-identical Mining or Miningcore scope-contract digest not explicitly listed compatible is financially incompatible and requires the migration barrier in Section 3.

This includes changes to payout scheme, settlement scheme/adjustment parameters or digest, completeness/retention/admission policy, network validation policy, accounting schema, persistence schema, direct-candidate validation, or any future financial interpretation field.

## 2. Producer-generation contract boundary

Producer idempotency state survives Core epochs, but an active generation is created under one exact Mining scope-contract digest.

Before activating a successor epoch whose Mining scope-contract digest differs for scope `Q`:

- every active producer generation for `(sender,lane,Q,producer_id)` MUST be durably sealed under the old digest;
- all in-flight admissions in those generations MUST have durable outcomes;
- the durable producer tombstone/high-water state MUST be committed before successor activation;
- the successor epoch starts new active generations only under the new digest.

An active generation MUST NOT straddle two different Mining semantic-contract digests. Failure to seal is `ADMIN_ACTION_CONFLICT`.

## 3. Mechanical financial migration barrier

For old scope-contract pair `C`, define `NoLiveDependencies(Q,C)` as true only when **every** condition below is durably true under explicit database locks/snapshot consistency:

1. no open/unfinalized PPLNS, PPLNSBF or PROP settlement/window whose dependency set records `C`;
2. no unsettled PPS liability/accounting effect accepted under `C`;
3. no unfinalized CUSTODIAL_SOLO winning-share/block attribution under `C`;
4. no PREPARED, SUBMITTED_UNCERTAIN, OBSERVED_ACTIVE or QUARANTINED direct candidate whose proof binds `C`;
5. no `UNRESOLVED` or `RESOLVED_WAIVED` gap/quarantine/policy-reconciliation range whose affected financial history binds `C`;
6. no live settlement override whose audit dependency still references ordinary evidence under `C`;
7. no retained-epoch import/reconciliation operation in progress for effects interpreted under `C`;
8. no active producer generation or in-flight admission under the old Mining digest;
9. every final settlement/proof that depended on deletable old ordinary evidence has the versioned immutable summary required by `coredrp-v1-settlement-safety.md`;
10. every application-specific effect row under `C` is either final/immutable or explicitly named by a future versioned migration action.

`closed-old-state barrier` means exactly `NoLiveDependencies(Q,C) == true`. Implementations MUST NOT replace this predicate with age, epoch retirement, zero currently connected senders, an operator boolean, or a best-effort query that omits any listed dependency class.

Before a FINANCIALLY_INCOMPATIBLE successor scope contract becomes active, the receiver/operator MUST establish one of:

1. `NoLiveDependencies(Q,C) == true`; or
2. **explicit migration:** a future versioned migration action/registry defines exact old→new transformation and preserves old proof identity; or
3. **new scope identity:** operation moves to a distinct scope so old and new financial semantics cannot be confused.

Profile 1.1 defines no implicit migration between non-identical financial contracts.

PPLNS/PPLNSBF/PROP windows MUST NOT silently cross a financially incompatible contract boundary. PPS liabilities already accepted under the old contract remain governed by their immutable accepting evidence and MUST be settled/audited under that evidence.

## 4. Retention and proof binding

Every settlement proof records the exact Mining and Miningcore scope-contract digests and the settlement-scheme-policy/adjustment digest used to derive its dependencies. Pruning and migration-closure decisions MUST use those recorded proof bindings rather than current configuration.

## 5. Receiver activation

The receiver MUST evaluate this registry before recording successor epoch approval/transition for an affected scope. The closure predicate and producer seals MUST be evaluated under the same serializable/explicitly locked activation transaction or under an immutable snapshot/version whose state version is rechecked at commit.

A sender and receiver MUST NOT advertise/accept the successor binding as active while the required producer seals, dependency closure, or explicit migration barrier are incomplete.
