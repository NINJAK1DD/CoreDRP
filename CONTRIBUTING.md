# Contributing to CoreDRP

> Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

CoreDRP/1 is currently in **draft / pre-implementation** status. Contributions are welcome, but protocol changes should be treated as specification changes rather than ordinary refactors.

## Before proposing a protocol change

A change affecting any of the following should include a specification rationale and corresponding test-vector or compatibility impact where applicable:

- hash-domain tags or preimages;
- UUID or integer byte order;
- event-type allocations;
- lane allocations;
- protobuf field numbers;
- handshake/version negotiation;
- acknowledgement or durability semantics;
- clock-state transitions;
- epoch/recovery rules;
- completeness checkpoint or gap semantics;
- mining-profile payout/completeness rules.

## Layer boundaries

The Core layer MUST remain domain-independent. Mining semantics belong in `profiles/mining`; Miningcore-specific persistence or payout details belong in `profiles/miningcore` or the Miningcore repository itself.

The intended dependency direction is:

```text
protocol/ <- profiles/mining/ <- profiles/miningcore/
```

Reverse imports are not permitted.

## Pull requests

Keep protocol changes focused. Where a change alters stable bytes or hashes, update:

- `docs/CoreDRP-1-SPEC.md`;
- the relevant `.proto` file;
- `docs/coredrp-v1-test-vectors.json`;
- the error registry or metrics appendix if applicable;
- CI/regression checks.

Until CoreDRP/1 is declared stable, breaking changes are permitted when clearly documented. Once stable, breaking wire or hash changes require a new protocol major version.
