# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft 0.6 implementation-freeze candidate / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The canonical working specification is [`docs/CoreDRP-1-SPEC-0.6.md`](docs/CoreDRP-1-SPEC-0.6.md). [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md) is intentionally only a pointer to that canonical version. Draft 0.5 and earlier specifications/semantic corpora remain historical reference only.

## Draft 0.6 profile-freeze focus

The current pass closes the final integration/profile findings without redesigning Core 1.1. In particular it:

- aligns Miningcore merged-mining accounting with the actual Miningcore model: one shared proof/accounting ID projected to distinct parent/auxiliary scopes, with chain-specific miner identities allowed;
- adds projection-local scope to the Miningcore profile wire using field 10 before profile freeze;
- binds PPLNS/PPLNSBF payout-window configuration through a canonical settlement-scheme-policy digest;
- defines exact temporal-policy staging sender sets and `applicable_clock_uncertainty = 2 * max(required sender skew)`;
- permanently tombstones retired producer UUIDs and seals active producer generations before changed admission contracts;
- defines financially incompatible semantic-contract migration barriers across epochs;
- preserves `PayoutSafeThrough`/`SafePruneThrough` as truthful contiguous frontiers while adding settlement-specific pruning for unrelated later evidence beyond a permanent waived hole;
- gives payout-significant quarantine explicit unresolved/reconciled/waived financial semantics;
- makes verified sender-processing-limit clock evidence deterministically BAD;
- defines durable scope safety origin and strict temporal-reconciliation cross-field/non-overlap rules;
- splits current accounting and Bitcoin profile vectors from superseded historical profile fixtures;
- restores a full committed protobuf structural baseline (messages, fields, enums, oneofs, services, packages and reserved ranges) alongside exact reviewed byte fingerprints and `buf breaking`.

## Layering

```text
CoreDRP Core 1.1
    ▲
Mining Profile 1.1
    ▲
Miningcore Profile 1.1
```

## Current normative/conformance surface

Current CI checks:

- canonical Draft 0.6 specification structure and normative registry integrity;
- layer, error, event and metric registries;
- exact reviewed protobuf Git/SHA-256 fingerprints;
- committed descriptor-derived protobuf structural baseline;
- `buf breaking` against `main` on PRs and against the previous push SHA on direct pushes;
- current Core 1.1 hash-chain vectors;
- current Mining admission/request-identity vectors;
- Draft 0.6 contract/clock/profile-lifecycle vectors;
- accounting-schema-v2 merged-mining vectors;
- current Bitcoin candidate/SegWit evidence vectors;
- freeze-completion policy/completeness/idempotency/settlement vectors;
- state-machine decisions;
- protobuf compilation and Buf lint;
- independent .NET reconstruction;
- positive TLA+ model and realistic unsafe mutations.

Historical Draft 0.4 vectors are retained under `docs/historical/` for audit provenance only and are **non-normative/non-conformance** for the current draft.

These checks are conformance/regression tests, not a proof of the complete protocol.

## Licensing and attribution

- Specification/documentation: CC BY 4.0
- Protocol definitions, vectors, tooling and source: Apache-2.0

Copyright © 2026 **Rob Cooke**.

Canonical attribution: **“CoreDRP — Core Durable Relay Protocol, originally designed and authored by Rob Cooke in 2026.”**

Canonical project: https://coredrp.org  
Source: https://github.com/NINJAK1DD/CoreDRP
