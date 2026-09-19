# Real-service PPS arithmetic compatibility evidence

Copyright © 2026 Rob Cooke. Documentation: CC-BY-4.0.

The user-supplied 19 September 2026 report describes 40 accepted Stratum shares
from a running Miningcore Bitcoin regtest service, followed by backup, isolated
restore and read-only comparison. The test used Miningcore
`be2add3d66c8f97b50265262a746d1980ec50e96` and CoreDRP
`253d1e15eab8782d2a69bf5273fbc489ef76084e`.

The backup SHA-256 was independently verified as
`910f2fa0743c021533ac866efc3f241d4b8a5b0d5de7624f119d0530cd7ad411`.
The exact reference arithmetic and all report deltas were independently
recomputed. The service run and restore provenance are from the supplied report;
this regression does not claim another service execution or independent restore.
No private database backup, miner addresses, credentials or logs are committed.

`tests/fixtures/pps-regtest-arithmetic.json` retains the numerical inputs,
provenance hashes and immutable expected results. All 40 observed discrepancies
are `calculated_liability_mismatch`: legacy Miningcore decimal conversion gives
`10.64516129032258064516129`, while CoreDRP's exact binary64 rational calculation
gives `10.645161290322581103779573`. The aggregate reference-minus-legacy
amount is `0.00000000000001834473132` test BTC.

The test freezes this mismatch without tolerance and checks a separate synthetic
exact-arithmetic case. Changing a retained liability is never part of comparison.
Even an arithmetic match remains payout-ineligible without authenticated policy,
clock/checkpoint/gap and historical remainder evidence.

The accompanying Miningcore migration uses version 0 for historical decimal
arithmetic and explicit version 1 for CoreDRP PPSLiabilityV1 arithmetic. It records
an immutable per-pool UTC activation boundary, preserves legacy replay hashes and
liabilities, adds the version to new relay/journal/credit evidence, and carries
existing recipient remainders forward. All writers/relays must be upgraded and
legacy journals drained before activation. Fee-policy changes are separate.
The current decimal transport rejects exact results it cannot represent; it must
not silently round them to claim conformance.

The shadow comparator always compares with CoreDRP arithmetic. Historical
version-0 mismatches therefore remain visible after migration; a migration is
not grounds to relabel old reports as matching. Test old and new intervals
separately, retaining their policy settings and original evidence.
