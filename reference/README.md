# CoreDRP experimental crash-tested reference

Copyright © 2026 Rob Cooke. Code: Apache-2.0. Documentation: CC-BY-4.0.

This is a deliberately small **Core 1.1 implementation slice**, using the frozen gRPC service. It implements one sender, lane 0, one approved epoch, and checkpoint type `0x0001`. The application effect is a durable checkpoint projection in PostgreSQL. It advertises **no Mining or Miningcore profiles**. It is not yet a general-purpose or production-conforming CoreDRP endpoint.

The sender uses an append-only length/SHA-256-framed WAL and separately fsynced atomic anchor. Receiver event bytes, application effect, checkpoint and stream head commit in one PostgreSQL transaction with `synchronous_commit=on`; only then is ACK sent. A receiver-ahead reconnect verifies the chain before remembering the missing ACK. Stop-and-wait batches obey event/byte credit, including zero windows. Both TLS endpoints require TLS 1.3, a trusted client/server certificate, hostname verification on the client, and exactly one matching CoreDRP URI SAN.

Sender state retains all records and caller-key mappings. There is **no pruning, automatic corruption repair, epoch replacement, quarantine approval, or holder retirement**. Cap exhaustion stops admission; the explicit `increase-cap` command can add capacity without removing evidence. Full checksummed records beyond a lagging anchor recover; incomplete records, anchor mismatch and middle corruption stop recovery without modifying the evidence. This is intentionally more conservative than the optional torn-tail repair in the specification.

## Development environment

Python 3.12 on Linux with local POSIX filesystems, OpenSSL with TLS 1.3, and PostgreSQL 17 with `fsync` and `full_page_writes` enabled. SQLite or an in-memory substitute is not used for receiver acceptance. Install and generate:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r reference/requirements.txt
.venv/bin/python reference/generate.py
export PYTHONPATH=reference
```

Generated stubs remain under `.build/reference`; the fingerprinted `.proto` sources do not change. Windows CI separately checks source fingerprints with `core.autocrlf=true`; the POSIX reference runtime itself is not supported on Windows.

Use a **dedicated disposable database** whose name begins `coredrp_ref_`. The runtime rejects other database names before creating any tables. Provide its connection string through `COREDRP_REF_DSN`, not command-line arguments or committed files. The lab role must own this empty database. Do not use production credentials. The tests create only the `coredrp_ref` schema and never drop a database or touch Miningcore tables.

## Executable bootstrap and recovery

Provision a CA and two certificates with the appropriate EKU and unique URI SANs:

- sender: `urn:coredrp:sender:<sender UUID>`;
- receiver: `urn:coredrp:receiver:<receiver UUID>` and a DNS SAN matching the configured endpoint, e.g. `localhost`.

The test suite generates temporary certificates automatically. Never commit private keys. The following UUID values are disposable examples; provision fresh identities for a new lab:

```sh
export PYTHONPATH=reference
# Export COREDRP_REF_DSN through your local secret mechanism first.
.venv/bin/python -m coredrp_ref.cli bootstrap \
  --receiver 10000000-0000-4000-8000-000000000001 \
  --incarnation 10000000-0000-4000-8000-000000000002 \
  --sender 10000000-0000-4000-8000-000000000003 \
  --epoch 10000000-0000-4000-8000-000000000004 \
  --admin-id 10000000-0000-4000-8000-000000000005
.venv/bin/python -m coredrp_ref.cli init-sender --wal reference/lab/sender \
  --sender 10000000-0000-4000-8000-000000000003 \
  --epoch 10000000-0000-4000-8000-000000000004
# In another terminal:
.venv/bin/python -m coredrp_ref.cli serve --port 7443 \
  --ca reference/lab/ca.pem --cert reference/lab/receiver.pem --key reference/lab/receiver.key
# Negotiate before first admission:
.venv/bin/python -m coredrp_ref.cli sync --wal reference/lab/sender \
  --receiver 10000000-0000-4000-8000-000000000001 --port 7443 \
  --ca reference/lab/ca.pem --cert reference/lab/sender.pem --key reference/lab/sender.key
.venv/bin/python -m coredrp_ref.cli admit-checkpoint --wal reference/lab/sender \
  --caller-key checkpoint-1 --time 100 --through 99
# Run the same sync command to drain; repeat safely after either process restarts.
.venv/bin/python -m coredrp_ref.cli inspect --wal reference/lab/sender
```

Bootstrap is a privileged **local lab provisioning command**, not a network ADMIN service or a complete implementation of ADMIN action encodings/state-version semantics. Its transaction persists receiver/incarnation, one initial epoch, binding, and idempotent audit request. Reusing an admin UUID with changed inputs or trying to replace an existing epoch fails. Recovery uses `inspect` and `sync` with the original identities. Rollback, changed receiver/incarnation, missing history and corruption stop with named errors; do not delete the anchor to bypass them.

All sender durability paths for one host must share the same provisioned parent directory. The sender takes both a path lock and a `(sender,lane)` lock in that parent's `sender-fences` directory. Copying an identity onto another host/durability root is unsupported and requires an external deployment fence. Receiver processes sharing the database use a PostgreSQL session advisory lock plus durable owner generation and row checks; a lost session cannot silently reconnect and retain its old ownership. Unsupported lane/profile/epoch requests are rejected, never downgraded.

See [tested recovery operations](RECOVERY.md) for bounded reconnects, capacity increases, storage-error handling and the failure acceptance contract.

## Acceptance tests

```sh
PYTHONPATH=reference .venv/bin/python -m pytest -q reference/tests/test_wal.py
# With the disposable PostgreSQL database and COREDRP_TEST_PG_CONTAINER available:
PYTHONPATH=reference .venv/bin/python -m pytest -q reference/tests
```

The PostgreSQL suite does not silently skip when configuration is missing. The CI job provisions PostgreSQL and executes the full suite on pushes and PRs. The tests use real SIGKILL on separate sender/receiver processes, not thrown exceptions standing in for a crash:

| Boundary/scenario | Required outcome |
|---|---|
| Before WAL write | No event reported durable; retry admits once |
| After WAL fsync / after anchor fsync | Restart recovers one immutable event and idempotent caller result |
| Immediately before receiver commit | No durable effect or head advancement; recovery drains once |
| Immediately after receiver commit, before ACK | One effect; restart both sides and verify/adopt the missing ACK |
| Before sender ACK persistence | One effect, old sender ACK; reconnect adopts verified receiver head |
| After sender ACK persistence | Remembered ACK survives restart |
| Exact replay / altered replay / invalid terminal hash | One effect / rejection / no prefix commit |
| Zero window followed by control-plane credit | No batch accepted at zero; progress resumes after credit |
| Spool exhaustion / corrupt WAL / competing writers | Fail closed without eviction or duplicate effects |
| TLS 1.2 / absent client cert / wrong receiver URI identity | Connection/admission rejected |

These tests demonstrate eventual drain for the tested finite faults, assuming a healthy database and filesystem, valid certificates, positive credit, available network and explicit retry with unchanged identities. They do not prove general liveness, power-loss/storage-controller durability, Byzantine peer resistance, or production-scale resource isolation. Fault injection requires the explicitly named `COREDRP_TEST_CRASH` environment variable and is for isolated tests only.

## Miningcore shadow milestone

`python -m coredrp_ref.shadow` provides an **offline** one-scope PPLNS comparison using the retained accounting corpus. It parses original accounting payloads, recomputes exact reference allocation, compares to a separately supplied baseline export shape, persists only shadow reports, and blocks eligibility on differences or missing policy staging, membership, clock, checkpoint or unresolved/waived evidence. Tests exercise each blocked condition. It cannot issue payouts.

This is the fixture-backed bridge for milestone 3, **not a live Miningcore integration**. The next implementation PR should add a read-only exporter from an isolated Miningcore instance, explain each differential result, implement authenticated policy distribution/staging and actual Mining clock/checkpoint handling, and add an accounting adapter to receiver transactions only after those profile obligations are covered. Do not advertise Mining 1.1 merely because the offline arithmetic agrees.

## Administrative follow-up and limits

Before a full profile integration: implement the canonical ADMIN request/state-version transaction and authenticated policy distribution; persist issuance holders and all-history admission cutoffs; crash-test staging ACK, membership end and activation races; support explicit audited epoch transitions and recovery gaps; and enforce Mining clock BAD/recovery and producer-lifecycle rules at admission. The reference currently has no remote admin endpoint.

A permanently lost policy holder still blocks ordinary activation on its old scope. The supported design alternative remains a distinct scope with preserved old evidence. No executable workflow here retires a holder or repins a changed receiver automatically. These actions need the separate fencing/reconciliation proof required by the registries.

Transport foundation: [grpclib server API](https://grpclib.readthedocs.io/en/latest/server.html) and [client API](https://grpclib.readthedocs.io/en/latest/client.html). Database durability settings: [PostgreSQL WAL configuration](https://www.postgresql.org/docs/current/runtime-config-wal.html).
