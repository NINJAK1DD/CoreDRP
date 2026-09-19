# Development review implementation — 19 September 2026

Reviewed base: `ef2adf8cf6331d518caa2ef6f1be67c760cbc353`.

| Finding / next step | Implementation and evidence |
|---|---|
| Canonical BAD interval rule disagrees with registry | §29 explicitly restricts wholly-outside intervals to PROBE_EVIDENCE; verified wall-step/processing causes may carry an overlap, never a wholly GOOD or inverted interval. Matching vectors cover both reasons. |
| Processing overrun bypasses freshness | Both probe-backed paths use one age/remaining-lifetime function. Vectors cover age 0, expiry−1, expiry, expiry+1, negative age and optional bounds. Registry explicitly preserves existing BAD/RECOVERING and UNKNOWN-grace state when stale input establishes no fresh state. |
| Windows CRLF breaks byte fingerprints | `.gitattributes` enforces LF for `.proto`; the dedicated Windows CI job enables `core.autocrlf=true` before checkout and runs the unchanged fingerprint gate. |
| Minimal reference | `reference/` implements the frozen gRPC service for lane 0/checkpoint events, durable sender WAL/anchor, TLS 1.3 mutual authentication, pinned URI identities, initial epoch provisioning, PostgreSQL atomic evidence/effect/head commit, ACK persistence, replay and owner fencing. |
| Automated failures | Local WAL tests kill actual processes around persistence. Dedicated PostgreSQL CI kills receiver/sender around commit and ACK boundaries, restarts both, and checks one effect plus eventual remembered ACK. Atomic invalid-batch rollback, immutable replay, zero-window control traffic, TLS rejection and administrative idempotency are covered. |
| Miningcore shadow milestone | Offline one-scope PPLNS harness compares retained accounting payloads to an explicit baseline export shape in the isolated database. Missing staging/membership/clock/checkpoint or waived uncertainty blocks shadow eligibility; mismatches have explicit differential output. Live Miningcore exporting and full profile admission remain the next milestone, not claimed implemented here. |
| Administrative workflows | Executable privileged local bootstrap, sender initialization, verified inspection and reconnect recovery. No implicit receiver replacement, corruption erasure, lost-holder retirement or production payout. Canonical remote ADMIN/policy distribution and crash-tested activation remain explicitly planned. |

All 19 existing Python conformance gates and the local sender/WAL tests are runnable without PostgreSQL. The full live suite requires a dedicated `coredrp_ref_*` database and fails rather than skips when it is absent. This workspace cannot switch to PostgreSQL's required non-root identity, so the real PostgreSQL acceptance evidence is supplied by both CI paths. Full run results are recorded on the PR.

This is a bounded experimental implementation slice, not a complete Core/Mining/Miningcore implementation or a security audit. It retains all evidence and rejects unsupported profile/epoch changes. The [reference guide](../../reference/README.md) specifies runtime assumptions, exact commands, acceptance boundaries and remaining work. The formal model remains a bounded safety check; demonstrated finite-fault drain is not a general liveness proof.
