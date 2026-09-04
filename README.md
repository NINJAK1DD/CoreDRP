# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by [Rob Cooke](AUTHORS.md) in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft / pre-implementation. Not production-ready.**
>
> CoreDRP/1 is under active specification work. Wire formats, identifiers, event allocations, state machines, and test vectors may change until the specification is explicitly declared stable.

CoreDRP is a durable, authenticated, replayable event-relay protocol originally designed for distributed cryptocurrency mining infrastructure. It separates generic relay mechanics from mining semantics and from the Miningcore-specific integration so that the protocol is not tied to a single pool implementation.

Miningcore is the initial and reference implementation target for CoreDRP/1.

## Layering

CoreDRP/1 is defined in three layers:

1. **CoreDRP/1 Core** — domain-independent durable event replication: authenticated sender identity, scopes, numbered lanes, epochs/sequences, exact-byte hashing, sender WAL/replay, durable acknowledgement, clock evidence, checkpoints, gaps, flow control, and recovery.
2. **CoreDRP Mining Profile v1** — mining event semantics and the multi-sender completeness model used by window-based payout systems.
3. **Miningcore Integration Profile v1** — Miningcore persistence, payout/pruning integration, direct-coinbase evidence, configuration, API, metrics, and migration from the legacy ZeroMQ relay.

The dependency direction is intentionally one-way:

```text
CoreDRP Core
    ▲
    │
Mining Profile
    ▲
    │
Miningcore Integration
```

## Repository layout

```text
docs/
  CoreDRP-1-SPEC.md
  coredrp-v1-test-vectors.json
  coredrp-v1-errors.md
  coredrp-v1-metrics.md

protocol/
  coredrp-v1.proto

profiles/mining/
  coredrp-mining-v1.proto

profiles/miningcore/
  coredrp-miningcore-v1.proto

tools/
  verify_test_vectors.py
  check_layer_boundaries.py
```

## Design invariants

CoreDRP/1 is being specified around a small set of non-negotiable guarantees:

- accepted work crosses a sender-side durable boundary before acknowledgement to the submitting client;
- transmission is at-least-once and replayable;
- receiver acknowledgement occurs only after the profile-defined durable commit;
- ordered stream history is protected by an epoch-scoped per-event hash chain;
- integrity-invalid history is never silently skipped;
- durable checkpoints prove the absence as well as the presence of relevant events through a boundary;
- application/profile policy decides the consequences of completeness gaps;
- critical local actions such as mining-node `submitblock` never wait on the remote recorder.

## Draft artifacts

The current working draft is **CoreDRP/1 v0.1**. It is intentionally untagged as a stable release.

Start with [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md).

## Domains

The project domains `coredrp.org`, `coredrp.com`, and `coredrp.dev` have been reserved. A canonical project website may be published later; GitHub is the source of truth during the draft stage.

## Licensing and attribution

CoreDRP uses a split licensing model designed to encourage implementation while preserving clear attribution:

- **Specification and documentation:** [CC BY 4.0](LICENSES/CC-BY-4.0.txt)
- **Protocol definitions, test vectors, tooling and source code:** [Apache-2.0](LICENSES/Apache-2.0.txt)

Copyright © 2026 **Rob Cooke**. See [`NOTICE`](NOTICE), [`AUTHORS.md`](AUTHORS.md), [`CITATION.cff`](CITATION.cff), and [`LICENSE.md`](LICENSE.md).

The canonical attribution is: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

## Contributing

CoreDRP/1 is currently in specification-first development. See [`CONTRIBUTING.md`](CONTRIBUTING.md) before proposing changes.

## Security

Please do not open public issues for vulnerabilities in a deployed CoreDRP implementation. See [`SECURITY.md`](SECURITY.md).

---

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0
