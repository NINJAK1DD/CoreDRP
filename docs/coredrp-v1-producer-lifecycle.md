# CoreDRP Mining Producer Lifecycle Registry — Draft 0.6

**Status:** normative Mining Profile 1.1 registry

This registry refines Mining admission idempotency policy v3 for producer registration, retirement, reuse and semantic-contract transitions.

## 1. Namespace

Producer state is keyed by `(sender_id,lane_id,scope,producer_id_uuid)`.

A producer UUID is a durable identity within that namespace, not a reusable slot.

## 2. Registration and permanent retirement

At most 1024 producer UUIDs may be active/registered for one `(sender,lane,scope)`.

Registration is an explicit durable administrative action. An unregistered producer cannot admit a Core event.

When a producer is removed/retired:

- every in-flight admission must have a durable outcome;
- the active generation must be sealed;
- detailed active-generation mappings may be retired according to the Mining idempotency rules;
- a compact durable **producer tombstone** is written containing at least producer UUID, final `retired_generation_high_water`, scope, sender/lane identity and retirement audit identity.

The producer tombstone is permanent for the lifetime of the sender durability identity. It is not deleted merely because application rows, WAL segments, or old settlement records age out.

A producer UUID present in the tombstone set MUST NEVER be registered again in the same `(sender,lane,scope)` namespace. Attempted re-registration fails locally before WAL admission.

Therefore an old `(producer_uuid,generation,sequence)` financial identity can never become available for a second event after removal.

## 3. Replacement producer

Operational replacement requires a fresh UUID not present in active registry or permanent tombstones. A fresh UUID starts at generation 1 / sequence 1 and has no identity collision with the retired producer.

## 4. Counter exhaustion

Admission sequence and producer generation are unsigned 64-bit and never wrap. Sequence max seals the generation. Generation max permanently exhausts that producer and requires retirement/replacement with a fresh UUID.

## 5. Scope-contract transition

Every active producer generation records the exact Mining semantic-contract digest under which it was opened.

Before an epoch activates a different Mining semantic-contract digest for that scope, all active generations MUST be sealed under the old digest as required by `coredrp-v1-profile-transitions.md`. No active generation straddles two different admission-policy contracts.

## 6. Conformance cases

Current conformance MUST include:

- same producer UUID in different scopes is a different namespace;
- unregistered producer rejection;
- registry cardinality bound;
- sequence/generation exhaustion;
- remove producer then attempt to re-register the same UUID => permanent rejection;
- successor contract with changed admission parameters while an active generation exists => transition blocked until seal.
