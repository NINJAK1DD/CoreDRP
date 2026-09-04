# CoreDRP/1 — Core Durable Relay Protocol

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

**Status:** Draft 0.2 hardening revision  
**Reference implementation target:** Miningcore  
**Normative language:** The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described by RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

---

## 1. Status and conformance

CoreDRP/1 is specification-first and pre-implementation. This draft incorporates the first two independent adversarial reviews of the public v0.1 repository.

An implementation is conforming only if it satisfies the Core rules in this document and every negotiated profile rule. Generated protobuf types alone are not a conformance definition.

The normative order of authority is:

1. this specification;
2. the numbered error registry and test-vector corpus;
3. the `.proto` files;
4. reference tooling.

Reference code MUST NOT override the specification.

## 2. Layering

CoreDRP/1 Core is application-neutral. It owns authenticated identity, scopes, lanes, epochs, sequences, event time, exact payload bytes, event identity, chaining, sender durability, replay, cumulative ACKs, generic checkpoints, gaps, quarantine mechanics, flow control, clock evidence, reconnect and recovery.

The CoreDRP Mining Profile v1 owns mining scope semantics, lane meanings, mining share semantics, temporal sender membership, PayoutFence/CriticalCheckpoint interpretation, PayoutSafe and SafePruneThrough.

The Miningcore Integration Profile v1 owns PostgreSQL schema, Miningcore share/accounting projections, payout/pruning integration, direct-coinbase evidence, operator APIs and Miningcore metrics.

Dependencies are one-way: Miningcore MAY depend on Mining; Mining MAY depend on Core; the reverse directions are forbidden.

## 3. Terms

**Sender**: process that durably admits events and initiates CoreDRP streams.

**Receiver**: process that verifies and durably commits events.

**Lane**: independent ordered durable stream identified by an 8-bit number.

**Epoch**: UUID-scoped logical history of one sender lane.

**Scope**: opaque Core byte string interpreted by profiles.

**Durable tail**: highest sender sequence whose complete WAL record has been flushed to durable storage.

**Committed sequence**: highest receiver sequence whose event effects and stream state have durably committed.

**Remembered ACK**: receiver ACK durably persisted by the sender.

**Checkpoint**: Core event proving no later covered event may be introduced at or before its boundary.

## 4. Fixed identifiers and domain separation

The protocol name is `CoreDRP/1`.

Protobuf packages are `coredrp.v1`, `coredrp.mining.v1`, and `coredrp.miningcore.v1`.

The sender certificate identity URI is:

`urn:coredrp:sender:<uuid>`

The UUID MUST be lower-case canonical textual form.

The following ASCII strings are fixed for CoreDRP/1:

| Symbol | Exact ASCII bytes | Purpose |
|---|---|---|
| `PAYLOAD_DOMAIN` | `CoreDRP1-PAYLOAD` | payload digest |
| `EVENT_DOMAIN` | `CoreDRP1-EVENT` | per-event chain |
| `GENESIS_DOMAIN` | `CoreDRP1-GENESIS` | epoch/lane genesis |
| `CONTRACT_DOMAIN` | `CoreDRP1-CONTRACT` | epoch contract binding |
| `ADMIN_DOMAIN` | `CoreDRP1-ADMIN` | privileged-request digest |

No NUL terminator is included. CoreDRP/1 MUST NOT reinterpret any listed tag. Additional tags require a protocol revision.

## 5. Primitive encodings

Cryptographic preimages use:

- `uint8`, `uint16_be`, `uint32_be`, `uint64_be`: unsigned big-endian;
- `int64_be`: signed two's-complement big-endian;
- SHA-256 output: exactly 32 bytes;
- UUID: exactly 16 octets in RFC 9562 network order, never platform-specific COM/.NET `Guid.ToByteArray()` order;
- scope length: `uint16_be`;
- payload length: `uint32_be`.

CoreDRP sequence values are `1..2^63-1`. Sequence zero denotes epoch genesis only.

A receiver MUST reject out-of-range lane, sequence, event type or length values before constructing a hash preimage.

## 6. Lane and event-type registries

Core lane IDs are `0..255`. Core assigns no application meaning.

Mining Profile v1 fixes lane 0 = share and lane 1 = critical.

The CoreDRP/1 global event-type space is 16-bit:

- `0x0001`: Core CompletenessCheckpoint
- `0x0100`: MiningShareEvent
- `0x0200`: MiningcoreAccountingShareEvent
- `0x0201`: BitcoinDirectCoinbaseCandidate
- `0x0202`: CandidateStateUpdate
- `0xF000..0xFFFE`: private/test use
- all other values: reserved unless allocated by a later compatible draft/revision
- `0xFFFF`: reserved for conformance boundary testing

Unknown or unadvertised event types are fatal. Event type values above `0xFFFF` are rejected as `EVENT_TYPE_OUT_OF_RANGE` before hashing.

## 7. Hard pre-negotiation resource limits

These limits apply before any negotiated limit exists:

- maximum gRPC message: 20 MiB;
- maximum `ClientHello` or `ServerHello`: 256 KiB;
- maximum implementation string: 128 UTF-8 bytes;
- maximum profile identifier: 64 ASCII bytes;
- maximum profile lines: 32;
- maximum scope-contract lines: 1024;
- maximum advertised event types: 1024;
- maximum Core scope: 65535 bytes;
- maximum event payload: 16 MiB;
- maximum batch event count: 4096;
- maximum batch payload bytes: 16 MiB;
- maximum ChainProbe count: 256;
- every chain probe hash MUST be exactly 32 bytes.

A peer MUST reject an object exceeding a hard limit without allocating proportionally unbounded memory.

## 8. Authentication and sender identity

TLS 1.3 with mutual TLS is REQUIRED.

The receiver MUST extract exactly one `urn:coredrp:sender:` URI SAN. Zero or more than one such SAN is `UNAUTHORIZED_SENDER`. Other SAN types MAY coexist.

`ClientHello.sender_id` MUST equal the 16 RFC 9562 octets of the authenticated SAN UUID. A mismatch is fatal `UNAUTHORIZED_SENDER`.

The receiver MUST authorize the sender for the requested lane and every non-empty scope before accepting events.

Security revocation and mining temporal membership are separate states. Revoking transport authorization MUST NOT silently alter payout membership.

## 9. Core version negotiation

The first client frame MUST be exactly one `ClientHello`. The first server frame MUST be either one `ServerHello` or one `ProtocolError`.

An empty top-level `oneof`, a second hello, or any non-hello first frame is `MALFORMED_FRAME`.

Core major mismatch is unconditional `PROTOCOL_VERSION_MISMATCH`.

For major 1, the receiver selects the highest minor version not greater than both peers' supported minor. Behaviour introduced in minor `n` MUST NOT be used when the negotiated minor is lower than `n`.

Duplicate profile tuples, duplicate event types, conflicting duplicate scope contracts, or malformed presence combinations make the handshake invalid.

Handshake validity additionally requires:

- `sender_id` and `log_epoch` exactly 16 bytes;
- `lane_id <= 255`;
- `earliest_retained_sequence`, `durable_tail_sequence`, remembered ACK and committed sequence each `<= 2^63-1`;
- `earliest_retained_sequence >= 1` and `earliest_retained_sequence <= durable_tail_sequence + 1`;
- remembered ACK sequence/hash are either both absent or both present;
- a present remembered ACK sequence is in `1..durable_tail_sequence` and its hash is exactly 32 bytes;
- receiver ID and receiver database incarnation exactly 16 bytes;
- committed chain hash and contract binding digest exactly 32 bytes;
- selected/advertised semantic digests either absent where permitted or exactly 32 bytes;
- every negotiated limit non-zero, within the hard limits of Section 7, and internally consistent.

Any violation is `INVALID_HANDSHAKE` unless a more specific range/authorization code applies.

## 10. Profile and semantic-contract negotiation

A selected profile MUST exactly match one sender-advertised profile ID/major and a mutually supported minor.

A semantic contract digest, when present, MUST be exactly 32 bytes. A profile defines the source bytes and hash algorithm for its semantic contract. CoreDRP/1 requires SHA-256 for every negotiated semantic-contract digest.

Mining Profile scope contracts are per scope. The Mining Profile contract source MUST include every financially relevant interpretation required to prevent divergent payout semantics, including profile version, payout-scheme family, accounting schema version, replay/retention horizon semantics, coin/network identity and completeness-policy version.

Empty digest means that the relevant profile explicitly defines no semantic contract. It MUST NOT be treated as wildcard acceptance.

A digest mismatch is `SEMANTIC_CONTRACT_MISMATCH`; it is never silently downgraded.

## 11. Epoch contract binding

Before admitting the first profile event of a new epoch, the sender MUST have completed a successful handshake for that epoch and MUST durably persist the accepted contract binding.

This bootstrap requirement applies only when establishing or changing an epoch contract. Afterward, receiver/network outages MUST NOT prevent local durable admission of already-authorized event types under the persisted binding.

The contract binding digest is:

`SHA256(CONTRACT_DOMAIN || uint16_be(core_major) || uint16_be(core_minor) || uint8(lane_id) || profile_set || scope_contract_set || event_type_set)`

`profile_set` is sorted by ASCII profile ID, then major, then minor. Each entry is:

`uint16_be(id_len) || id_ascii || uint16_be(major) || uint16_be(minor) || uint8(has_digest) || [32-byte digest]`

`scope_contract_set` is sorted lexicographically by scope bytes then profile ID. Each entry is:

`uint16_be(scope_len) || scope || uint16_be(profile_id_len) || profile_id_ascii || 32-byte digest`

`event_type_set` is ascending unique `uint16_be(event_type)` values preceded by `uint16_be(count)`.

Each set is preceded by a `uint16_be(count)`.

The binding is immutable for an epoch. A receiver that withdraws an event type or changes a selected semantic contract while unretired WAL history exists causes `CONTRACT_BINDING_CHANGED` at handshake. The sender MUST NOT skip already-durable events to accommodate a changed contract.

## 12. Event identity and event model

Every Event contains sequence, event_type, scope, event_time_unix_ms, exact payload bytes and a 16-byte `relay_event_id`.

The event ID is part of the cryptographic preimage and MUST be immutable. Core requires an RFC 9562 UUID; Mining Profile v1 requires UUIDv7.

The receiver MUST preserve the exact received payload bytes for any retained raw/quarantine evidence. Parsed semantic meaning and cryptographic identity are distinct; reserialized protobuf bytes MUST NOT replace the original bytes as chain evidence.

## 13. Cryptographic construction

For exact payload bytes `P`:

`payload_hash = SHA256(PAYLOAD_DOMAIN || uint32_be(len(P)) || P)`

For sender UUID bytes `S`, epoch UUID bytes `E`, lane `L`:

`chain[0] = SHA256(GENESIS_DOMAIN || S || E || uint8(L))`

For event sequence `N`, event type `T`, relay event UUID bytes `R`, scope `Q`, event time `M`, payload hash `H` and previous chain `Cprev`:

`chain[N] = SHA256(EVENT_DOMAIN || Cprev || S || E || uint8(L) || uint64_be(N) || uint16_be(T) || R || uint16_be(len(Q)) || Q || int64_be(M) || H)`

Every variable-width field is length-prefixed. The sender hashes exact serialized payload bytes written to the WAL. The receiver hashes exact bytes received. Protobuf serialization is never considered canonical.

The normal wire carries only the batch terminal chain hash, not per-event payload or chain hashes.

## 14. Batch validity and atomicity

An EventBatch MUST:

- contain at least one event;
- contain at most negotiated and hard event-count limits;
- have `first_sequence` in `1..2^63-1`;
- contain contiguous event sequences;
- have event 0 sequence exactly `first_sequence`;
- not overflow `2^63-1`;
- have a 32-byte terminal hash exactly equal to the computed final event chain;
- obey negotiated event and payload limits.

Before opening a durable-effect transaction, the receiver MUST verify structure, ranges, authorization and the cryptographic chain across the entire batch.

On any structural/integrity failure, the receiver commits nothing and MUST NOT offer quarantine.

Normal receiver batch effects are all-or-nothing. Semantic failure of event `k` rolls back the entire batch and returns `SEMANTIC_PAYLOAD_INVALID` with sequence `k`. The sender MAY retry a strict prefix ending at `k-1` as a new valid batch. The invalid event itself requires correction or operator quarantine before progress can pass it.

## 15. Sender durable admission and WAL

Application acceptance ordering is:

`validated work → lane sequencer allocates sequence/time/id → exact payload serialized → complete WAL record written → durable flush succeeds → application success acknowledgement`

A sender MUST NOT acknowledge successful durable admission before the flush.

Each lane has an independent bounded admission channel, sequence space, WAL and state anchor. Overflow policy is backpressure, never drop.

A WAL record MUST have local physical-corruption framing independent of the event chain, including a length and CRC32C or cryptographically equivalent record-integrity check.

Crash semantics:

| Failure | Required result |
|---|---|
| before WAL durability | no durable application success may have occurred |
| durable WAL, before application response | caller may retry; event remains recoverable |
| after application success | event MUST recover from WAL |
| disk full/fsync EIO | stop new admission |
| torn unacknowledged tail | MAY truncate only when proven never durably acknowledged |
| middle-record corruption | fail closed; never skip |
| corrupted acknowledged record | recovery/safety incident; never silently create a new epoch |

Unacknowledged records MUST NEVER be evicted.

## 16. Durable sender anchor and pruning

The per-lane anchor includes at least:

- sender_id, lane_id, log_epoch;
- last durable sequence and chain hash;
- last assigned event_time;
- oldest retained sequence;
- remembered receiver ID and database incarnation;
- remembered ACK sequence/hash;
- epoch contract binding digest.

The anchor MUST be written only after the WAL flush it describes. It may lag the WAL but MUST NEVER lead it.

Anchor replacement MUST use write-temp, file flush, atomic rename/replace and directory metadata flush on filesystems where that is required for crash durability.

On recovery, the anchor's claimed sequence/hash MUST match the WAL exactly; recovery then scans forward.

Sender pruning ordering is:

`validate ACK → durably persist ACK anchor → only then make WAL <= ACK eligible for pruning`

A crash after ACK persistence but before prune is harmless. Pruning before ACK persistence is forbidden.

## 17. Flow control and pressure

Receiver window limits are advisory upper bounds below hard limits.

Heartbeats and clock probes MUST continue while event flow is window-blocked.

Pressure response:

1. alert on rising admission/spool pressure;
2. stop accepting new client/miner connections before existing accepted work is endangered;
3. if durable admission cannot continue, fail closed.

Share and critical lanes SHOULD use separate devices on high-rate deployments. Separate sequencers provide scheduling isolation, not physical I/O isolation.

## 18. Stream handshake and single-writer fencing

A sender MUST hold an exclusive local lock/fencing mechanism covering `(sender_id,lane_id,log_epoch)` for the lifetime of the writer.

The receiver MUST allow at most one active stream per `(sender_id,lane_id)`. CoreDRP/1 uses first-writer-wins: a second stream receives `STREAM_ALREADY_ACTIVE`.

A receiver backed by PostgreSQL MUST additionally hold a lifetime advisory/lease lock for the stream and serialize every commit with a row lock or equivalent compare-and-swap on durable stream state.

## 19. Reconnect reconciliation

Let:

- `C` = receiver committed sequence;
- `R` = sender remembered ACK sequence, or 0 if none;
- `T` = sender durable tail;
- `E` = sender earliest retained sequence.

All comparisons are within the same approved epoch.

| Condition | Result |
|---|---|
| `C == R` and hashes match | resume/replay from `C+1` |
| `C > R`, `C <= T`, sender can verify receiver hash | lost ACK; durably adopt receiver ACK then continue |
| `C < R` on same receiver database incarnation | `RECEIVER_ROLLBACK`; stop |
| `C > T` | `SENDER_ROLLBACK`; stop |
| receiver requires sequence `< E` | `RECOVERY_GAP`; stop |
| common sequence hash differs | `SPLIT_LOG`; stop |
| different unapproved epoch | `EPOCH_NOT_APPROVED`; stop |
| receiver database incarnation changed | explicit restore/replacement reconciliation; never choose longest history |

No best-effort fallback exists.

A restored or promoted receiver database that might have lost acknowledged transactions MUST mint a fresh database incarnation before serving CoreDRP.

## 20. ACK semantics

ACK means the receiver's profile effects, exact raw/quarantine evidence as required, chain head, committed sequence and committed hash have all durably committed.

ACKs MUST be monotonic. A duplicate equal ACK is valid. A lower ACK on the same receiver incarnation is `RECEIVER_ROLLBACK`, not a harmless stale response.

An ACK MUST NOT advance beyond sender durable tail and its hash MUST equal the sender's locally computed chain hash at that sequence.

Commit-success/ACK-loss is normal: on reconnect the sender verifies the receiver's higher committed hash, durably adopts it, then continues.

## 21. Receiver transaction semantics

After complete batch integrity validation, a conforming receiver transaction MUST atomically:

1. set/verify required durability policy;
2. lock current stream state;
3. validate the expected epoch/sequence/chain head;
4. validate profile semantics;
5. write raw/event identity and application/profile effects;
6. write any quarantine/gap records included by an explicit operator action;
7. advance committed sequence and chain hash;
8. update current checkpoint state where applicable;
9. COMMIT.

Anything fails → ROLLBACK → no ACK.

Miningcore MUST NOT route CoreDRP ordinary ingestion through the legacy receiver recovery-journal fallback.

## 22. Epoch transitions

A new epoch is permitted only after a durable administrative transition records:

`old_epoch + final_sequence + final_chain_hash → new_epoch + new_genesis + lane + operator + reason + timestamp`

Retired epoch UUIDs are permanent tombstones and MUST survive event pruning.

A retired epoch MUST NEVER become current again.

At sequence `2^63-1`, an approved epoch transition is mandatory; sequence wrapping is forbidden.

## 23. Error model

Every protocol error has a numeric code and disposition. The normative mapping is in `docs/coredrp-v1-errors.md`.

Disposition classes are:

- `STREAM_RETRYABLE`;
- `OPERATOR_INTERVENTION`;
- `PERMANENT_CONFIGURATION`;
- `EVENT_QUARANTINABLE`.

An implementation MUST use the registry's disposition and MUST NOT infer retryability from whether an error happened to be delivered on a closing stream.

## 24. Quarantine

Quarantine is allowed only when Core structure, sequence, authorization and chain integrity are valid and the profile payload is semantically invalid.

Never quarantinable:

- chain mismatch;
- sequence gap;
- malformed ordering/frame;
- split history;
- sender/receiver rollback;
- impossible/unapproved epoch;
- unauthorized scope;
- unknown/unadvertised event type.

An operator-approved quarantine-and-advance transaction MUST retain:

- sender, lane, epoch, sequence;
- relay_event_id;
- exact original payload/event bytes needed for proof;
- payload hash and chain hash;
- event type and scope;
- validator/profile version;
- semantic contract digest;
- rejection reason;
- operator, timestamp, idempotency key and state version.

ACK may advance past a quarantined event only after that record and stream watermark durably commit together.

## 25. Core completeness-gap records

Core owns the existence and lifecycle of a gap; profiles own its consequences.

A gap record contains scope, lane, epoch, sequence/range, neighbouring trusted event-time bounds when known, classification, state, and immutable audit provenance.

If time coverage cannot be proven, the interval is conservative/open-ended from the last trusted boundary. A missing sequence MUST NOT be assigned a falsely precise timestamp range merely by interpolation.

Resolution states are `RESOLVED_RECONCILED` and `RESOLVED_WAIVED`. Waiver records accepted uncertainty; it does not rewrite history as complete.

## 26. Completeness checkpoints

Core event type `0x0001` is CompletenessCheckpoint.

CoreDRP Mining Profile v1 uses **lane-global checkpoints**: the enclosing Event.scope MUST be empty. One checkpoint covers every currently authorized Mining scope on that sender/lane for which the profile declares the checkpoint applicable.

The payload `complete_through_unix_ms` MUST equal the enclosing `Event.event_time_unix_ms`.

On lane 0 the Mining Profile interprets it as PayoutFence. On lane 1 it is CriticalCheckpoint.

Idle periodic checkpoints are REQUIRED because they prove absence of accepted events during quiet intervals.

## 27. Checkpoint anti-backdating

Once a valid checkpoint with boundary `T` has been sequenced, every later event class covered by that checkpoint MUST have `event_time_unix_ms > T`.

The sender sequencer MUST enforce this before durable admission and the receiver MUST independently verify it.

A violation is `CHECKPOINT_BACKDATED_EVENT` and is not quarantinable because it invalidates the completeness claim.

A sender SHOULD checkpoint slightly behind trusted current time rather than at an optimistic wall-clock edge.

## 28. Event-time assignment

Event time is assigned inside the single-consumer lane admission sequencer.

Within an epoch, assigned event times MUST NOT decrease. The durable anchor stores the last assigned event time.

Minor local clock jitter MAY be clamped monotonically only within the configured `maxClockStep`. A detected forward or backward step beyond that threshold makes local clock state BAD.

Ordinary Mining share Created time is the Core event time; the receiver MUST NOT replace it with receipt time.

All relayed event classes are subject to the negotiated/profile future-time bound.

## 29. Clock probe mathematics

Clock probes are authenticated and bound to the active stream.

For receiver transmit `t1`, sender receive `t2`, sender transmit `t3`, receiver receive `t4`, reject `t3 < t2`.

Without assuming symmetric delay, sender-minus-receiver offset is conservatively bounded by:

`[t3 - t4, t2 - t1]`

The interval width is uncertainty.

The receiver MUST use the best/minimum-RTT observations over a rolling window, expire stale evidence, cap sender probe-processing duration, prevent active probe-ID reuse and use a monotonic local clock to detect receiver wall-clock steps.

The midpoint/symmetric-delay estimate MUST NOT be used as the financial safety bound.

## 30. Clock health, grace and recovery

Local clock state: GOOD or BAD.

Remote bound state: GOOD, BAD or UNKNOWN.

Rules:

- local BAD → stop covered-lane admission and checkpoint advancement regardless of remote state;
- remote BAD → stop covered-lane admission and checkpoint advancement;
- remote UNKNOWN + local GOOD + grace active → admission MAY continue, but trusted checkpoints MUST NOT advance;
- remote UNKNOWN + grace expired → stop covered-lane admission;
- remote GOOD + local GOOD → normal operation.

Grace preserves ingestion availability only. It MUST NOT create new completeness certainty. `PayoutSafe` cannot advance beyond the last boundary proven before UNKNOWN.

Recovery from BAD requires both trusted UTC to reach/pass durable `last_event_time` and a fresh set of good remote probes confirming offset within `permittedClockSkew`. A single good sample is insufficient; Mining Profile v1 requires at least three good probes spanning at least one probe interval.

Mining Profile v1 default clock contract is:

- `permittedClockSkew = 2000 ms`;
- local `maxClockStep = 250 ms`;
- probe interval = 5 s;
- probe processing duration maximum = 250 ms;
- remote-bound evidence expires after 15 s;
- UNKNOWN admission grace = 120 s.

Deployments MAY use stricter values. Looser values are a semantic-contract change and MUST produce a different scope semantic-contract digest.

## 31. Mining scope and lane semantics

Mining scope is the exact configured pool identifier encoded as ASCII bytes matching:

`[A-Za-z0-9._-]{1,64}`

Comparison is byte-exact/case-sensitive. No Unicode normalization or case folding occurs.

Lane 0 is SHARE. Lane 1 is CRITICAL.

Mining share payload `created_unix_ms` MUST equal Core event time.

Difficulty fields MUST be finite. Negative zero, NaN and infinities are invalid. Network/difficulty quantities used for accepted work MUST be strictly positive; informational achieved values MAY be zero only where the profile explicitly permits it.

## 32. Temporal sender membership

Membership intervals are half-open:

`[valid_from, valid_until)`

If `valid_until` exists, it MUST be greater than `valid_from`.

Membership history is append-only/audited.

Revoking sender transport authorization MUST NOT alter membership.

Ending membership for a sender that has not supplied trusted completeness through the deactivation boundary MUST create an unresolved completeness gap or require an explicit audited waiver.

A membership change SHOULD take effect at a future boundary comfortably beyond permitted clock skew.

## 33. PayoutSafe

For mining scope `Q` and time boundary `T`, `PayoutSafe(Q,T)` is true only when all are true:

1. every `RequiredSender(Q,T)` has trusted lane-0 checkpoint evidence through at least the required skew-adjusted boundary;
2. every checkpoint used met the clock contract;
3. no unresolved recovery/completeness gap can cover a relevant event at or before `T`;
4. no unresolved payout-significant quarantine covers the interval;
5. membership and semantic-contract state relied upon were durably established before use;
6. checkpoint anti-backdating guarantees no later valid history may introduce covered work at or before `T`.

For cross-sender Mining completeness with symmetric maximum trusted skew `S`, a block with sender timestamp `B` requires peer completeness at least `B + 2S`, unless a tighter per-sender interval proof defined by the implementation is demonstrably more conservative.

A scope with no required relay members is trivially PayoutSafe.

PPS and SOLO are not payout-fence gated. Direct block submission is never gated on remote completeness.

## 34. SafePruneThrough

`SafePruneThrough(Q)` is derived from the same proof system and MUST NOT exceed the latest boundary whose evidence may safely be destroyed.

For evidence used to reconstruct payout correctness:

`SafePruneThrough(Q) <= PayoutSafeThrough(Q)`

Both boundaries are monotonically nondecreasing. Discovery that an earlier safety decision was wrong is a safety violation, not permission to silently move a monotonic frontier backward after evidence has been destroyed.

Never prune epoch tombstones, durable chain/ACK anchors, membership history, unresolved/resolved gap and quarantine audit records, override records or settlement evidence still required by an integration profile.

## 35. Mining scheme consequences

Miningcore integration rules:

- PPLNS/PPLNSBF: settlement requires PayoutSafe; prune through `min(scheme cutoff, SafePruneThrough)`.
- PROP: settlement requires PayoutSafe; prune through `min(round cutoff, SafePruneThrough)`.
- custodial SOLO: payout is not fence-gated, but share deletion for the winning miner MUST be time-bounded to `created <= min(block.Created, SafePruneThrough)`.
- PPS: per-share accounting is not fence-gated and follows independent accounting retention.
- direct-coinbase SOLO: remote receiver/fences MUST NEVER gate local `submitblock`.

## 36. Direct candidate independence

A submitting edge MUST durably persist exact direct-candidate/settlement evidence locally before attempting `submitblock`.

Recorder unavailability, critical-lane failure or stale PayoutFence MUST NOT delay local submission.

Critical-lane delivery is durable evidence replication, not part of block-submission latency.

## 37. PostgreSQL durability conformance

For the transaction advancing CoreDRP committed state:

- PostgreSQL `fsync` MUST be enabled;
- `SET LOCAL synchronous_commit = on` or a stronger synchronous setting is REQUIRED;
- unlogged tables MUST NOT hold CoreDRP durable ledger/state;
- receiver effects and stream watermark MUST commit atomically.

If an HA target may be promoted without containing every ACKed transaction, promotion MUST mint a new receiver database incarnation and invoke rollback/replay reconciliation before serving traffic.

## 38. Failure semantics

**PostgreSQL unavailable:** receiver emits/records `RECEIVER_DURABILITY_UNAVAILABLE` with retryable disposition, sends no ACK for uncommitted data, applies backpressure and allows sender spooling.

**Disk/fsync failure at sender:** stop new durable admission; never accept in memory.

**Corrupted WAL middle record:** fail closed; do not skip or create a new epoch automatically.

**Commit succeeds, ACK lost:** normal reconnect lost-ACK path.

**Duplicate sender:** local single-writer fence prevents admission; receiver rejects second active stream.

**Duplicate receiver:** database/advisory fencing prevents concurrent stream ownership.

**Split history:** `SPLIT_LOG`, operator intervention.

**Partial batch failure:** entire current batch transaction rolls back; no ACK.

## 39. Heartbeats, drain and ChainProbe

Client and server heartbeat messages are direction-specific. Heartbeat timestamps and fields MUST NOT contribute to clock/completeness proof.

A graceful sender or receiver MAY send Goodbye. Goodbye is advisory; durable stream state remains authoritative.

ChainProbe is diagnostic only. A healthy stream does not issue probes. Receiver initiation MUST be tied to an authenticated local administrative action, rate-limited, `count` MUST be `1..256`, and response size is bounded accordingly. Probe results never mutate durable stream state.

## 40. Monetary and numeric representation

Financial coin-unit decimal values use `Decimal38Scale24.canonical`.

Grammar:

`0` or `[1-9][0-9]{0,13}` optionally followed by `.` and `1..24` decimal digits, with the final fractional digit non-zero.

No sign, exponent, whitespace, leading zeroes, trailing fractional zeroes, NaN or infinity is allowed.

Values MUST be `< 100000000000000` and have at most 38 total decimal digits and scale 24.

Fields that require positive amounts reject `0`.

No `double` value may directly represent a monetary amount.

Mining Profile string/resource limits after payload parsing are: miner 256 UTF-8 bytes, worker 128, user-agent 256, source IP 64, source 64, session ID 128, candidate kind 64, transaction-confirmation data 4096. Miningcore direct-recipient count is at most 256, address metadata at most 128 UTF-8 bytes, and scriptPubKey at most 10,000 bytes. Exceeding a profile bound is semantic payload invalidity and MUST NOT cause unbounded allocation.

## 41. Miningcore Bitcoin representations and candidate state

Bitcoin `block_hash` and `coinbase_txid` are exactly 32 bytes in canonical RPC/display digest order: decoding the canonical 64-character RPC hex produces the transmitted bytes.

`serialized_block` is exact raw consensus-wire block bytes.

`script_pub_key` is exact raw script bytes and is authoritative. Recipient `address`, if present, is display/audit metadata and MUST either validate to exactly that script on the configured network or cause semantic rejection.

Bitcoin serialized block payload cap is 4,000,000 bytes for the Bitcoin profile.

Candidate ID is a 16-byte UUIDv7.

Initial BitcoinDirectCoinbaseCandidate state MUST be PREPARED.

Allowed transitions:

- PREPARED → SUBMITTED_UNCERTAIN, OBSERVED_ACTIVE, REJECTED, QUARANTINED
- SUBMITTED_UNCERTAIN → SUBMITTED_UNCERTAIN, OBSERVED_ACTIVE, REJECTED, QUARANTINED
- REJECTED → OBSERVED_ACTIVE only when later authoritative chain observation proves the block active; otherwise terminal except QUARANTINED
- OBSERVED_ACTIVE → QUARANTINED only for evidence-integrity/operator investigation; not back to PREPARED/REJECTED
- QUARANTINED is terminal unless an explicit audited reconciliation action records a replacement state outside this event transition graph.

`submission_attempts` never decreases. `definitive_misses <= submission_attempts`. `last_attempt` is absent iff attempts are zero.

## 42. Privileged actions and ADMIN digest

Privileged actions include quarantine-and-advance, completeness-gap waiver/reconciliation, settle-without-fence, membership end, capability activation and epoch transition approval.

Every request carries a client-generated idempotency key and expected state version. The action transaction MUST atomically write the idempotency record and protected state mutation.

Same key + same canonical request digest returns the original result. Same key + different digest is `IDEMPOTENCY_KEY_CONFLICT`. State-version mismatch is `ADMIN_ACTION_CONFLICT`.

For action type `A` and profile-defined canonical request bytes `B`:

`admin_digest = SHA256(ADMIN_DOMAIN || uint16_be(A) || uint32_be(len(B)) || B)`

Each profile defining an admin action MUST define `A` and canonical `B` byte construction. JSON text is not canonical unless the profile explicitly defines a canonical JSON scheme.

## 43. Security boundary

mTLS authenticates peers and transport. Authorization is explicit per sender/lane/scope.

The Core hash chain is unkeyed SHA-256. It provides strong detection of accidental corruption, inconsistent history, replay and divergent branches when at least one trusted anchor survives. It is NOT independently tamper-proof against an attacker able to rewrite all historical events, hashes and anchors.

Applications needing protection against total storage compromise SHOULD add independently protected signed/HMAC anchors or external append-only transparency storage.

No 0-RTT application data is permitted.

## 44. Specification and CI integrity

Every normative text/source artifact MUST be valid UTF-8, contain no NUL/control corruption, and pass repository integrity checks.

CI MUST verify:

- UTF-8/text integrity;
- contiguous top-level section numbering;
- section cross-reference resolution;
- protobuf compilation;
- layer dependency/name boundaries;
- error enum ↔ error registry parity;
- event-type allocation consistency;
- fixed domain tags;
- positive and invalid cryptographic vectors;
- profile-aware vector semantics;
- wire field-number/type compatibility against the committed baseline manifest.

Deleted protobuf fields MUST reserve both field number and preferably name.

## 45. Normative safety invariants

The following are machine-testable invariants:

`ACK_sequence <= receiver_durable_sequence`

`sender_prune_sequence <= sender_durably_remembered_ACK`

`common(sender,lane,epoch,sequence) => chain_hash identical`

`unresolved_gap_at_or_before(T) => NOT PayoutSafe(T)`

`unresolved_payout_quarantine_at_or_before(T) => NOT PayoutSafe(T)`

`SafePruneThrough <= PayoutSafeThrough`

`PayoutSafeThrough` monotonically nondecreasing

`SafePruneThrough` monotonically nondecreasing

`retired_epoch` never becomes current again

`checkpoint(T) => every later covered event has event_time > T`

A PlusCal/TLA+ model of sender WAL → transport → receiver commit → ACK → sender ACK persistence → prune SHOULD be maintained as an additional design check.

## 46. Protocol evolution

CoreDRP/1 uses negotiated core minor versions, profile versions, advertised event types and semantic-contract digests.

A sender MUST NOT emit an event type not accepted for the persisted epoch binding.

Unknown/unadvertised types remain fatal even though protobuf preserves unknown fields.

Adding a new safety-significant top-level frame alternative requires an explicitly negotiated compatible minor; protobuf unknown-field preservation alone is insufficient.

Event-type ranges and protobuf field numbers are never reused after release.

## 47. Out of scope for CoreDRP/1

CoreDRP/1 does not standardize:

- receiver active/active HA across independent databases;
- automatic retroactive payout compensation;
- historical statistics sample rebuilding;
- remote-durable Stratum admission policy;
- consensus against a fully malicious storage administrator;
- external standards governance or public registry allocation.

## 48. Reference implementation requirements

Miningcore MUST:

- preserve sender event time;
- use dedicated CoreDRP ingest with no ordinary legacy recovery-journal fallback;
- use `SET LOCAL synchronous_commit = on`;
- enforce single active stream and transactional row/advisory fencing;
- persist sender UUID mapping/ordinals without reuse;
- uniquely identify share effects by `(poolid, senderordinal, relayeventid)` or an equivalent partition-safe key;
- expose completeness, gap, clock, spool, replay and quarantine metrics;
- retain local direct-candidate evidence before `submitblock`.

## 49. Conformance-test requirements

Before CoreDRP/1 is declared stable, the repository MUST contain:

- hash/genesis vectors for lane 0, lane 1 and lane 255;
- type `0xFFFF` boundary vector and out-of-range rejection;
- empty payload and empty scope;
- maximum 65535-byte scope and oversize rejection;
- sequence above `2^32`, sequence `2^63-1`, sequence zero rejection;
- negative/pre-1970 event time;
- a recognizable UUID byte-order trap (`00112233-4455-6677-8899-aabbccddeeff`);
- exact preimage hex in addition to hash outputs;
- contract-binding digest vector;
- ADMIN digest vector;
- semantically valid Core checkpoint vector;
- semantically valid Mining and Miningcore payload vectors;
- malformed protobuf/profile vectors;
- reconnect/rollback/recovery-gap cases;
- WAL crash-ordering cases.

## 50. Authorship

CoreDRP — Core Durable Relay Protocol was originally designed and authored by **Rob Cooke** in 2026 and was originally developed for the Miningcore project.

The canonical project is `https://coredrp.org` and the source repository is `https://github.com/NINJAK1DD/CoreDRP`.
