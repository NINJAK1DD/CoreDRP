# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The current working specification is **Draft 0.3**, incorporating four independent adversarial passes over the public Draft 0.1 and Draft 0.2 repository state.

Start with [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md).

## Core guarantees

- sender-side durable admission before application success, with retry-safe local admission identity;
- at-least-once replay with cumulative ACK only after durable receiver commit;
- epoch-scoped per-event cryptographic history with temporal/completeness floors inherited across epochs;
- deterministic reconnect/rollback/split-log handling;
- sender and receiver single-writer fencing;
- explicit quarantine without rewriting immutable admitted events or laundering completeness gaps;
- clock-bounded completeness checkpoints;
- fail-closed Mining membership, `PayoutSafe` and `SafePruneThrough` semantics;
- deterministic cross-sender mining accounting order;
- local mining `submitblock` never waits on the recorder.

## Layering

```text
CoreDRP Core
    ▲
Mining Profile
    ▲
Miningcore Integration
```

CI enforces this dependency direction and checks specification integrity, the complete protobuf wire surface, registries, cryptographic/contract/ADMIN vectors, state-machine vectors, profile and Bitcoin evidence semantics, independent C# vectors, protobuf compilation/linting, and positive plus deliberately-negative TLA+ model checks.

## Licensing and attribution

- Specification/documentation: CC BY 4.0
- Protocol definitions, vectors, tooling and source: Apache-2.0

Copyright © 2026 **Rob Cooke**.

Canonical attribution: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

See `NOTICE`, `AUTHORS.md`, `CITATION.cff`, and `LICENSE.md`.

Canonical project: https://coredrp.org  
Source: https://github.com/NINJAK1DD/CoreDRP
