# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft 0.6 implementation-freeze candidate / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The canonical working specification is [`docs/CoreDRP-1-SPEC-0.6.md`](docs/CoreDRP-1-SPEC-0.6.md). Draft 0.5 and earlier specifications remain historical reference only.

## Draft 0.6 focus

Draft 0.6 closes the final cross-component safety and interoperability findings from the latest adversarial review of merged PR #6. In particular it:

- makes receiver-side `PayoutSafe` depend only on receiver-observable durable checkpoint evidence, while retaining sender ACK persistence for replay/WAL pruning;
- restores the complete generic epoch contract-binding byte grammar and publishes a Core 1.1 / Mining 1.1 / Miningcore 1.1 preimage+digest;
- moves Mining and Miningcore semantic rules into incorporated normative registries instead of leaving them implicit in test code;
- freezes malformed/stale `ClockStateUpdate`, stream-local generation lifecycle, BAD latching and recovery;
- explicitly states that Draft 0.6 endpoints implement Core 1.1 only and MUST NOT advertise Core 1.0 compatibility;
- replaces unbounded permanent per-share idempotency tombstones with a bounded active producer generation plus permanent retired-generation high-water safety;
- rejects ordinary retroactive membership/mode changes behind the payout frontier;
- distinguishes reconciled gaps from waived uncertainty so waiver cannot manufacture `PayoutSafe`;
- binds Bitcoin network validation policy into the Miningcore semantic contract;
- strengthens ADMIN atomic idempotency semantics, metric coverage, raw SHA-256 wire fingerprints and TLA+ mutation controls.

## Layering

```text
CoreDRP Core 1.1
    ▲
Mining Profile 1.1
    ▲
Miningcore Profile 1.1
```

CI checks canonical document structure, layer boundaries, error/event/metric registries, exact protobuf fingerprints, historical crypto vectors, Draft 0.5 compatibility vectors, Draft 0.6 freeze vectors, state-machine decisions, profile/accounting/Bitcoin evidence, Buf lint, independent .NET reconstruction, the positive TLA+ model and realistic unsafe mutations.

These checks are conformance/regression tests, not a proof of the complete protocol.

## Licensing and attribution

- Specification/documentation: CC BY 4.0
- Protocol definitions, vectors, tooling and source: Apache-2.0

Copyright © 2026 **Rob Cooke**.

Canonical attribution: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

Canonical project: https://coredrp.org  
Source: https://github.com/NINJAK1DD/CoreDRP
