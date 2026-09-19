# Recovery operations and acceptance contract

Copyright © 2026 Rob Cooke. Documentation: CC-BY-4.0.

Stop admission while diagnosing storage errors. Keep the sender identity, epoch,
receiver pins, caller keys and complete WAL/anchor together. Commands below use
`PYTHONPATH=reference` and the Python environment from the reference guide.

| Diagnosis | Executable action | Required result |
|---|---|---|
| Network/receiver/database temporarily unavailable | Repeat `sync` with `--attempts 5 --retry-delay 1 --timeout 10` and the original TLS/receiver arguments | Each attempt reopens and verifies WAL; a verified receiver-ahead head recovers a lost ACK; transient attempts are bounded |
| Logical spool capacity exhausted | Provision enough actual disk space, then `python -m coredrp_ref.cli increase-cap --wal PATH --cap BYTES` | Only increases the persisted cap; no pruning, identity changes or record deletion; retry the original caller key |
| OS disk full or failed write/fsync | Restore healthy storage, then `inspect --wal PATH`; retry the original caller key only after successful inspection | The failed handle cannot report further success; recovery syncs a complete suffix before anchoring it |
| Partial write, corrupt record or anchor, missing history | Stop; preserve an offline copy of the entire durability root for reconciliation | `inspect` fails closed; no automatic truncation, anchor deletion, repinning or new epoch |
| Changed receiver identity/incarnation or rollback | Restore the intended endpoint and reconcile receiver storage against the retained history | Automatic retry does not approve replacement; `sync` stops on identity/chain mismatch |
| Another local writer owns this identity | Stop the unintended duplicate through deployment tooling, then reopen | Never unlink lock files or copy the identity into another durability root |

`inspect` verifies evidence and may durably adopt a complete suffix; it is not a
forensic read-only command. Take an offline copy first when preserving an incident.
Capacity increases do not reclaim acknowledged records: this reference still
retains its entire history. The operator must arrange long-term capacity.

No success is returned after a persistence error. A failed fsync/rename can have
an ambiguous durable outcome, so replay the *same* caller key and original input
instead of inventing a replacement event. A directory fsync failure after rename
can leave either anchor version after a machine failure; both refer only to
previously fsynced WAL data. Reopening establishes the actual durable state.

## Failure tests

The CI PostgreSQL container is disposable. `COREDRP_TEST_PG_CONTAINER` identifies
that container for the two real `docker restart` tests. Local full-suite runs must
provide the equivalent isolated container and `COREDRP_REF_DSN`; absence fails
explicitly. Do not point restart tests at any shared service. The production
runtime has no Docker/container control path.

Tests cover:

- EIO/ENOSPC at WAL write/fsync and anchor write/fsync/replace/directory fsync;
- partial WAL writes and failed ACK persistence, including attempted reuse of a failed handle;
- a TCP proxy severing an encrypted batch partway through transmission;
- stream resets before ingest and after commit (lost ACK), without process death;
- PostgreSQL restart with an open transaction and after commit, plus terminated database sessions;
- repeated zero/reduced/restored credits while draining a backlog;
- bounded reconnects and verified receiver-ahead ACK adoption;
- the executable capacity-increase workflow and permanent-error retry rejection.

`COREDRP_TEST_IO`, `COREDRP_TEST_ERRNO`, `COREDRP_TEST_DISCONNECT` and
`COREDRP_TEST_CRASH` are explicit lab-only fault controls; unset them for ordinary
use. IO injection demonstrates software handling of OS errors, not a physical
power-loss or storage-controller guarantee. TCP tests use actual TLS/gRPC bytes
and PostgreSQL, not a mocked transport.

Eventual drain here assumes a finite backlog, restored storage and database
availability, valid certificates, available network, eventual sufficient credit,
a bounded interval long enough for an attempt, and continued explicit retry if
the attempt budget expires. Corruption and identity changes deliberately require
operator reconciliation; no automatic liveness claim applies to them.
