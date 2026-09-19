# Read-only Miningcore PPS shadow comparison

Copyright © 2026 Rob Cooke. Documentation: CC-BY-4.0.

The adapter compares **one Bitcoin PPS pool/scope and one bounded time interval**.
It reads actual Miningcore tables in an isolated restored database, using a single
PostgreSQL REPEATABLE READ, READ ONLY transaction. It has no SQL write path,
wallet RPC, payout call or Mining profile advertisement. Its only outputs are
exclusive-create JSON snapshot/report files.

PPS is the first live-schema adapter because `pps_share_credits` has a durable
`(poolid, accountingid)` key and balance credits have exact `pps-share:<id>` tags.
PPLNS `balance_changes` entries do not provide the equivalent direct accounting
identity. The separate fixture-backed PPLNS harness remains available.

## Prepare an isolated source

Restore the relevant Miningcore database into `miningcore_shadow_<name>`, keeping
shares, PPS credits, accounting groups and balance changes together. Use a
read-only login granted SELECT on `public.shares`, `public.pps_share_credits` and
`public.balance_changes`; supply its DSN through `MININGCORE_SHADOW_DSN`.
The adapter rejects other database names (except `coredrp_ref_*` test databases).
Use a private destination for snapshots because miner addresses are included.
Worker names, IP addresses, user agents and connection credentials are excluded.

Prepare a policy JSON file from the configuration/history applicable to the
whole interval, for example:

```json
{"scope":"btc1","scheme":"PPS","coin":"bitcoin","retained_percent":"99","from":"2026-09-19T00:00:00Z","until":"2026-09-20T00:00:00Z"}
```

`retained_percent` is the percentage paid to miners (99 means a 1% deduction),
not the operator fee percentage. A single-policy interval is required; split at
policy changes. These are operator-supplied comparison inputs, not authenticated
activation/staging proof. Other schemes, coins and uncovered intervals fail.

```sh
export PYTHONPATH=reference
# Set MININGCORE_SHADOW_DSN through your local secret mechanism.
python -m coredrp_ref.miningcore_shadow export --scope btc1 \
  --from 2026-09-19T00:00:00Z --until 2026-09-20T00:00:00Z \
  --policy reference/lab/pps-policy.json --output reference/lab/pps-snapshot.json
# Offline comparison requires no database credentials:
python -m coredrp_ref.miningcore_shadow compare \
  --input reference/lab/pps-snapshot.json --output reference/lab/pps-report.json
```

The time interval is inclusive at `--from`, exclusive at `--until`; timezone-aware
values are required and normalized to UTC. Queries are parameterized and schema
qualified. Statement/lock/connect timeouts and a 10,000-row limit per collection
bound a capture. The exporter rejects overflow rather than silently comparing a
truncated population; split the interval or review the bound for larger captures.

## What the report establishes

The snapshot preserves binary64 difficulty bits and exact decimal amounts. A
SHA-256 digest detects changed export bytes; it is **not** an authenticated source
signature. The reviewed schema revision is recorded, but the adapter does not
claim to detect the source application's running binary version.

For each accounting ID the report:

1. Matches retained share and credit identity, recipient, difficulty, reward basis
   and timestamp; identifies missing counterparts or missing accounting IDs.
2. Recomputes the scale-24 PPS liability using the CoreDRP exact-rational algorithm
   and the supplied retained percentage; records both values and an exact delta
   for every mismatch.
3. Checks that the scale-12 credited amount is within the permitted rounding/carry
   bounds, and that the tagged balance entry agrees with the stored credit.
4. Lists precision/carry differences individually. A possible carry is explicitly
   **unverified** without historical opening/closing remainder evidence.

`accounting_matches` means the checked retained-row arithmetic and ledger links
agree. It does not certify complete retention, a historical configuration,
consensus validity, reserve solvency, recipient ownership, or remainder history.
An empty population does not count as agreement. A missing retained share is a
reported evidence gap, even if normal Miningcore retention explains its absence.

Every report has `shadow_only: true` and `eligible: false`. Current database rows
cannot prove authenticated temporal policy/admission history, relay clock and
checkpoint completeness, uncertainty reconciliation, or historical remainder
state. Those missing proofs are always named as payout blockers; no boolean in
an operator JSON file can turn them into approval. Report matches are useful
reconciliation evidence, never a production payment authorization.

## Source and acceptance evidence

The adapter was reviewed against Miningcore
[`2702579`](https://github.com/NINJAK1DD/miningcore/tree/2702579ca7281509572dbf722fbffcf306c99aed),
including the [PPS persistence transaction](https://github.com/NINJAK1DD/miningcore/blob/2702579ca7281509572dbf722fbffcf306c99aed/src/Miningcore/Persistence/Postgres/Repositories/ShareRepository.cs)
and [schema](https://github.com/NINJAK1DD/miningcore/blob/2702579ca7281509572dbf722fbffcf306c99aed/src/Miningcore/Persistence/Postgres/Scripts/createdb.sql).
CI loads that byte-verified complete schema into real PostgreSQL, then exercises
exports and mismatches with independent synthetic accounting rows. It verifies
read-only enforcement, snapshot consistency during concurrent writes, exact
numeric capture, scope isolation, missing rows, source tampering, CLI replay,
output preservation, and overflow rejection. No production database has been
accessed, and no actual Miningcore service has been run for these tests.

The next deployment check is to run these same export/compare commands against
your isolated restored database and investigate its report. Full payout
eligibility still requires the authenticated policy and Mining profile work
listed in the reference guide; this adapter does not silently implement or waive
those protocol obligations.
