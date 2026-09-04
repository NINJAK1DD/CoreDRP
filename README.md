# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The current working specification is **Draft 0.2**, a hardening revision incorporating two independent adversarial reviews of the public v0.1 repository.

Start with [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md).

## Core guarantees

- sender-side durable admission before application success;
- at-least-once replay with cumulative ACK only after durable receiver commit;
- epoch-scoped per-event cryptographic history;
- deterministic reconnect/rollback/split-log handling;
- explicit quarantine without laundering completeness gaps;
- clock-bounded completeness checkpoints;
- Mining `PayoutSafe` and `SafePruneThrough` semantics;
- local mining `submitblock` never waits on the recorder.

## Layering

```text
CoreDRP Core
    ▲
Mining Profile
    ▲
Miningcore Integration
```

CI enforces this dependency direction and checks specification integrity, protobuf compilation/lint, wire compatibility, registries, cryptographic vectors, C# vectors, and profile-aware payload vectors.

## Licensing and attribution

- Specification/documentation: CC BY 4.0
- Protocol definitions, vectors, tooling and source: Apache-2.0

Copyright © 2026 **Rob Cooke**.

Canonical attribution: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

See `NOTICE`, `AUTHORS.md`, `CITATION.cff`, and `LICENSE.md`.

Canonical project: https://coredrp.org  
Source: https://github.com/NINJAK1DD/CoreDRP
