# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The current working specification is **Draft 0.4**, incorporating six independent adversarial review passes over the public Draft 0.1 through Draft 0.3 repository states.

Start with [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md).

## Core guarantees

- sender-side durable admission before application success, with domain-separated retry-safe admission identity and bounded idempotency retention;
- at-least-once replay with cumulative ACK only after durable receiver commit;
- epoch-scoped cryptographic history with explicit initial approval, fully drained normal rollover, and gap-recording exceptional abandonment;
- deterministic reconnect precedence including receiver logical identity, database incarnation, rollback, split-log and bootstrap-genesis checks;
- sender and receiver single-writer fencing;
- immutable event quarantine without rewriting admitted bytes or laundering completeness gaps;
- conservative clock-bound classification with strictest-policy aggregation across scopes;
- fail-closed temporal Mining membership/completeness-mode policy, `PayoutSafe` and `SafePruneThrough` semantics;
- deterministic cross-sender accounting order (not a claim of physical cross-sender causality);
- full Bitcoin direct-candidate structural evidence checks, including transaction Merkle roots and SegWit witness commitments;
- local mining `submitblock` never waits on the recorder.

## Layering

```text
CoreDRP Core
    ▲
Mining Profile
    ▲
Miningcore Integration
```

CI enforces this dependency direction and checks specification integrity, complete protobuf syntax/package/wire compatibility, error/event/metric registries, cryptographic/contract/admission/ADMIN vectors, state-machine decisions, executed negative profile/accounting cases, legacy and SegWit Bitcoin evidence, independent C# vectors, protobuf compilation/linting, and positive plus deliberately-negative TLA+ model checks.

## Licensing and attribution

- Specification/documentation: CC BY 4.0
- Protocol definitions, vectors, tooling and source: Apache-2.0

Copyright © 2026 **Rob Cooke**.

Canonical attribution: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

See `NOTICE`, `AUTHORS.md`, `CITATION.cff`, and `LICENSE.md`.

Canonical project: https://coredrp.org  
Source: https://github.com/NINJAK1DD/CoreDRP
