# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft 0.6 implementation-freeze candidate / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The canonical working specification is [`docs/CoreDRP-1-SPEC-0.6.md`](docs/CoreDRP-1-SPEC-0.6.md). [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md) is intentionally only a pointer to that canonical version. Draft 0.5 and earlier specifications/semantic corpora remain historical reference only.

## Draft 0.6 freeze-completion focus

The freeze-completion pass closes the final policy-composition, lifecycle and repository-authority findings without changing the Core 1.1 protobuf wire. In particular it:

- defines cross-sender payout completeness conservatively as `B + 2S`, with checked overflow and exact boundary vectors;
- binds `ClockStateUpdate` freshness to sender-local monotonic probe age, prevents delayed GOOD revival and prevents repeated UNKNOWN updates from restarting grace;
- defines multi-scope lane clock policy as an element-wise minimum across active scopes;
- makes Mining admission-generation state scope-qualified, bounds producer registrations, and defines uint64 exhaustion behavior;
- freezes every safety-significant numeric allocation in the Mining and Miningcore semantic contracts;
- defines complete PPLNS/PPLNSBF/PROP/PPS/custodial-SOLO/direct-SOLO settlement and retention behavior;
- freezes `TEMPORAL_POLICY_RECONCILIATION` correction kinds and exact policy-evidence bytes;
- requires future membership/mode policy generations to be durably staged on all affected senders before receiver activation;
- preserves `PayoutSafeThrough` as a truthful contiguous scalar while adding settlement-specific `SettlementSafe` proof for windows that no longer intersect an old waived hole;
- qualifies formal membership/clock proofs by epoch/policy and models unresolved/reconciled/waived gaps plus temporal-policy reconciliation;
- separates historical vectors from current conformance, restores structural `buf breaking` checks alongside exact protobuf byte fingerprints, and gates normative registry integrity.

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
- exact reviewed protobuf Git/SHA-256 fingerprints **and** structural `buf breaking` compatibility against `main`;
- current Core 1.1 hash-chain vectors;
- current Mining admission/request-identity vectors;
- Draft 0.6 contract/clock/ADMIN vectors;
- freeze-completion policy/completeness/idempotency/settlement vectors;
- state-machine decisions;
- Mining/Miningcore/accounting/Bitcoin evidence;
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
