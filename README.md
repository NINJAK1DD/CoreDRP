# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The current working specification is **Draft 0.5**. Start with [`docs/CoreDRP-1-SPEC-0.5.md`](docs/CoreDRP-1-SPEC-0.5.md). Draft 0.4 remains in the repository as historical review context only.

## Draft 0.5 safety focus

- durable sender admission before application success, with permanent lane-namespaced financial idempotency;
- at-least-once replay and cumulative ACK only after durable receiver commit;
- deterministic reconnect plus explicit receiver-ID/database-incarnation replacement reconciliation;
- fully drained normal epoch rollover and scope-complete/wildcard exceptional-abandonment gaps with retired-epoch import;
- temporal membership enforced on RELAY_REQUIRED payout events, not merely used when calculating completeness;
- lane-global checkpoints that require current authorization for every newly asserted covered scope;
- conservative clock interval classification communicated explicitly receiver→sender through Core 1.1 `ClockStateUpdate`;
- flow control charging scope + payload + per-event overhead, so empty payloads and maximum scopes cannot bypass byte windows;
- Bitcoin direct-candidate validation with duplicate-txid rejection, txid Merkle checks, mandatory witness commitments and declared consensus/merge-mining outputs;
- candidate-state referential integrity and transactionally checked monotonic transitions.

## Layering

```text
CoreDRP Core
    ▲
Mining Profile
    ▲
Miningcore Integration
```

CI provides **conformance and regression checks, not a proof of the whole protocol**. It validates document structure, reviewed protobuf fingerprints, registries, cryptographic constructions, state decisions, executable profile/accounting/Bitcoin positive and negative cases, independent-language vector reconstruction, and a bounded TLA+ fault model with mutation controls.

Review dispositions are retained under [`docs/reviews/`](docs/reviews/).

## Licensing and attribution

- Specification/documentation: CC BY 4.0
- Protocol definitions, vectors, tooling and source: Apache-2.0

Copyright © 2026 **Rob Cooke**.

Canonical attribution: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

See `NOTICE`, `AUTHORS.md`, `CITATION.cff`, and `LICENSE.md`.

Canonical project: https://coredrp.org  
Source: https://github.com/NINJAK1DD/CoreDRP
