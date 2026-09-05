# CoreDRP

**Core Durable Relay Protocol**

**Originally designed and authored by Rob Cooke in 2026.**  
Originally developed for the Miningcore project.

> **Status: Draft 0.6 implementation-freeze candidate / pre-implementation. Not production-ready.**

CoreDRP is a durable, authenticated, replayable event-relay protocol with a domain-independent Core, reusable Mining Profile, and Miningcore Integration Profile.

The canonical working specification is [`docs/CoreDRP-1-SPEC-0.6.md`](docs/CoreDRP-1-SPEC-0.6.md). [`docs/CoreDRP-1-SPEC.md`](docs/CoreDRP-1-SPEC.md) is intentionally only a pointer to that canonical version. Draft 0.5 and earlier specifications/semantic corpora remain historical reference only.

## Draft 0.6 final Profile 1.1 freeze focus

This pass closes the remaining Miningcore financial-integration findings while leaving Core 1.1 wire unchanged. In particular it:

- treats every Miningcore accounting projection scope—including auxiliary merged-mining scope—as an independent transport-authorization, temporal-membership, scope-contract and checkpoint-completeness boundary;
- tightens Miningcore accounting schema 3 to the actual accounting layer requirements: nonzero RFC 9562 accounting UUID, positive reward basis, non-empty session/source IP, positive achieved share difficulty, `preserve_created=true`, and `block_only=false`;
- freezes the RFC 9562 UUID-byte to Miningcore lowercase `Guid.ToString("N")` accounting-ID mapping;
- makes payout-significant quarantine recoverable only through canonical atomic `QUARANTINE_RECONCILIATION` / `QUARANTINE_WAIVER` ADMIN actions with exact immutable-event/effect evidence;
- defines last-scope temporal-policy deactivation using conservative pre-change clock skew, widened by post-change skew when present;
- binds **resolved effective** PPLNS/PPLNSBF configuration instead of assumed upstream defaults;
- binds Miningcore `AdjustShareDifficulty` behavior through a versioned share-difficulty-adjustment policy digest included in the settlement policy;
- adds PPLNSBF multi-key ordering/boundary vectors and canonical-decimal negatives;
- makes financially incompatible epoch migration closure mechanical through `NoLiveDependencies`;
- requires `SettlementEvidenceSummaryV1` before destructive pruning can discard ordinary settlement evidence;
- retains permanent producer tombstones, truthful contiguous payout/prune frontiers, interval-specific later settlement proofs, full Bitcoin/SegWit evidence checks, and descriptor-derived structural wire baselining.

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
- ordinary `buf breaking` against `main` on PRs and against an isolated previous push revision on direct pushes;
- current Core 1.1 hash-chain vectors;
- current Mining admission/request-identity vectors;
- Draft 0.6 final Profile 1.1 contract/clock/policy/quarantine/migration vectors;
- accounting-schema-v3 merged-mining plus strict parsed-protobuf safety vectors;
- settlement-scheme and share-difficulty-adjustment policy digests, including PPLNSBF ordering/boundaries;
- current Bitcoin candidate/SegWit/CVE-class evidence vectors;
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
