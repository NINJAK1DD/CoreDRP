# CoreDRP/1 — Core Durable Relay Protocol

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

**Status:** Draft 0.3 hardening revision  
**Reference implementation target:** Miningcore  
**Normative language:** The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described by RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

---

## 1. Status and conformance

CoreDRP/1 is specification-first and pre-implementation. Draft 0.3 incorporates the findings from four independent adversarial passes over Drafts 0.1 and 0.2.

An implementation is conforming only if it satisfies the Core rules in this document and every negotiated profile rule. Generated protobuf types alone are not a conformance definition.

The normative order of authority is:

1. this specification;
2. the numbered error, event-type, admin-action and conformance-vector registries;
3. the `.proto` files;
4. reference tooling.

Reference code MUST NOT override the specification.

## 2. Layering

CoreDRP/1 Core is application-neutral. It owns authenticated identity, scopes, lanes, epochs, sequences, event time, exact payload bytes, event identity, chaining, sender durability, replay, cumulative ACKs, generic checkpoints, gaps, quarantine mechanics, flow control, clock evidence, reconnect and recovery.

The CoreDRP Mining Profile v1 owns mining scope semantics, lane meanings, mining share semantics, temporal sender membership, PayoutFence/CriticalCheckpoint interpretation, `RequiredSender`, `PayoutSafe`, `PayoutSafeThrough`, `SafePruneThrough`, and deterministic cross-sender ordering for mining accounting.

The Miningcore Integration Profile v1 owns PostgreSQL schema, Miningcore share/accounting projections, payout/pruning integration, direct-coinbase evidence, operator APIs and Miningcore metrics.

Dependencies are one-way: Miningcore MAY depend on Mining; Mining MAY depend on Core; the reverse directions are forbidden.

## 3. Terms

**Sender**: process that durably admits events and initiates CoreDRP streams.

**Receiver**: process that verifies and durably commits events.

**Lane**: independent ordered durable stream identified by an 8-bit number.

**Epoch**: UUID-scoped logical history of one sender lane. An epoch resets sequence numbering, but it does not reset durable temporal/completeness floors for a continuing sender/lane.

**Scope**: opaque Core byte string interpreted by profiles.

**Durable tail**: highest sender sequence whose complete WAL record has been flushed to durable storage.

**Committed sequence**: highest receiver sequence whose event effects and stream state have durably committed.

**Remembered ACK**: receiver ACK durably persisted by the sender.

**Checkpoint**: Core event proving no later covered event may be introduced at or before its boundary.

**Temporal floor**: durable sender/lane lower bound inherited across epoch transitions. Covered events in a later epoch MUST be strictly newer than any inherited checkpoint floor.

## 4. Fixed identifiers and domain separation

The protocol name is `CoreDRP/1`.

Protobuf packages are `coredrp.v1`, `coredrp.mining.v1`, and `coredrp.miningcore.v1`.

The permanently assigned wire profile identifiers are:

- `PROFILE_ID_MINING = "coredrp.mining"`
- `PROFILE_ID_MININGCORE = "coredrp.miningcore"`

Profile IDs are ASCII, byte-exact and case-sensitive. The protobuf package name is not a substitute for the profile ID.

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

No NUL terminator is included. CoreDRP/1 MUST NOT reinterpret any listed tag.

## 5. Primitive encodings and preimage-range validation

Cryptographic preimages use:

- `uint8`, `uint16_be`, `uint32_be`, `uint64_be`: unsigned big-endian;
- `int64_be`: signed two's-complement big-endian;
- SHA-256 output: exactly 32 bytes;
- UUID: exactly 16 octets in RFC 9562 network order, never platform-specific COM/.NET `Guid.ToByteArray()` order;
- scope length: `uint16_be`;
- payload length: `uint32_be`.

CoreDRP sequence values are `1..2^63-1`. Sequence zero denotes epoch genesis only.

A peer MUST validate **every value that enters any cryptographic preimage before encoding it**. In particular:

- lane MUST be `0..255`;
- event type MUST be `0..65535`;
- sequence MUST be `1..2^63-1`;
- scope length MUST be `0..65535`;
- payload length MUST fit `uint32` and all negotiated/hard bounds;
- Core and profile major/minor values enter contract bindings as `uint32_be` and therefore MUST be `0..2^32-1` exactly as represented on the wire;
- advertised event types MUST be range-checked before de-duplication or sorting.

An implementation MUST NOT narrow, truncate, wrap or language-cast an unvalidated wider integer before hashing.

## 6. Lane, profile and event-type registries

Core lane IDs are `0..255`. Core assigns no application meaning.

Mining Profile v1 fixes lane 0 = SHARE and lane 1 = CRITICAL.

The CoreDRP/1 global event-type space is 16-bit:

- `0x0001`: Core CompletenessCheckpoint
- `0x0100`: MiningShareEvent
- `0x0200`: MiningcoreAccountingShareEvent
- `0x0201`: BitcoinDirectCoinbaseCandidate
- `0x0202`: CandidateStateUpdate
- `0xF000..0xFFFE`: private/test use
- all other values: reserved unless allocated by a later compatible revision
- `0xFFFF`: reserved for conformance boundary testing

Unknown or unadvertised event types are fatal. Event type values above `0xFFFF` are rejected as `EVENT_TYPE_OUT_OF_RANGE` before hashing.

## 7. Hard pre-negotiation resource limits

These limits apply before any negotiated limit exists:

- maximum gRPC message: 20 MiB;
- maximum `ClientHello` or `ServerHello`: 256 KiB;
- maximum implementation string: 128 UTF-8 bytes;
- maximum profile identifier: 64 ASCII bytes;
- maximum profile entries: 32;
- maximum scope-contract entries: 1024;
- maximum advertised event types: 1024;
- maximum Core scope: 65535 bytes;
- maximum event payload: 16 MiB;
- maximum batch event count: 4096;
- maximum batch payload bytes: 16 MiB;
- maximum ChainProbe count: 256;
- every chain probe hash: exactly 32 bytes.

A peer MUST reject an object exceeding a hard limit without allocating proportionally unbounded memory.

The effective limit for a profile object is the minimum of the Core hard limit, the negotiated limit and any stricter profile limit.

## 8. Authentication and sender identity

TLS 1.3 with mutual TLS is REQUIRED.

The receiver MUST extract exactly one `urn:coredrp:sender:` URI SAN. Zero or more than one such SAN is `UNAUTHORIZED_SENDER`. Other SAN types MAY coexist.

`ClientHello.sender_id` MUST equal the 16 RFC 9562 octets of the authenticated SAN UUID. A mismatch is fatal `UNAUTHORIZED_SENDER`.

The receiver MUST authorize the sender for the requested lane and each non-empty event scope before applying that event. Transport authorization is an access-control fact only; it MUST NOT define historical mining completeness coverage.

Security revocation and mining temporal membership are separate states. Revoking transport authorization MUST NOT silently alter payout membership or reinterpret an already-issued checkpoint.

## 9. Core version negotiation and handshake validity

The first client frame MUST be exactly one `ClientHello`. The first server frame MUST be either one `ServerHello` or one `ProtocolError`.

An empty top-level `oneof`, a second hello, or any non-hello first frame is `MALFORMED_FRAME`.

Core major mismatch is unconditional `PROTOCOL_VERSION_MISMATCH`.

For Core major 1, `protocol_minor` means the highest compatible minor supported by that peer. The negotiated Core version is the highest minor not greater than both peers' advertised maxima. Behaviour introduced in minor `n` MUST NOT be used when the negotiated minor is lower than `n`.

Handshake validity requires:

- `sender_id` and `log_epoch` exactly 16 bytes;
- `lane_id <= 255`;
- all sequence values `<= 2^63-1`;
- `earliest_retained_sequence >= 1` and `earliest_retained_sequence <= durable_tail_sequence + 1`;
- remembered ACK sequence/hash either both absent or both present;
- a present remembered ACK sequence in `1..durable_tail_sequence` and its hash exactly 32 bytes;
- receiver ID and receiver database incarnation exactly 16 bytes;
- committed chain hash and current contract-binding digest exactly 32 bytes;
- selected/advertised semantic digests absent only where that profile explicitly permits absence, otherwise exactly 32 bytes;
- all event types range-checked before uniqueness checks;
- duplicate event types forbidden;
- duplicate profile ID/major tuples forbidden;
- **all duplicate `(scope, profile_id)` scope-contract entries forbidden, whether identical or conflicting**;
- every negotiated limit non-zero, within Section 7 and internally consistent.

`remembered_contract_binding_digest` is absent only during first bootstrap of an epoch that has no persisted binding. Once a binding has been persisted, the field MUST be present exactly once, MUST be 32 bytes, MUST equal the sender's durable anchor, and MUST be compared with the receiver's durable binding for that epoch.

Any violation is `INVALID_HANDSHAKE` unless a more specific range/authorization code applies.

## 10. Deterministic profile and semantic-contract negotiation

For CoreDRP/1 profiles, `profile_major` is an exact major and `profile_minor` is the highest compatible minor supported within that major.

For each profile ID, the receiver MUST select at most one version. Selection is deterministic:

1. discard any sender profile line whose `minimum_core_major/minor` is greater than the negotiated Core version using lexicographic `(major, minor)` comparison;
2. require an exact profile-major match supported by both peers;
3. select the highest profile minor no greater than both peers' supported maxima;
4. require the selected line to be one of the sender's advertised profile ID/major lines;
5. reject if the selected semantic-contract digest differs;
6. select only event types defined by the selected profile version and advertised by both sides.

A profile requiring Core 1.3 MUST NOT be selected when Core 1.1 was negotiated.

A semantic-contract digest, when required by a profile, is exactly 32 bytes and uses SHA-256 over the profile's canonical source bytes defined in Section 12. Empty digest is permitted only if the profile explicitly declares that it has no semantic contract; it is never wildcard acceptance.

Digest mismatch is `SEMANTIC_CONTRACT_MISMATCH` and is never silently downgraded.

## 11. Epoch contract binding

Before admitting the first profile event of a new epoch, the sender MUST complete a successful handshake and durably persist the accepted contract binding.

This bootstrap requirement applies only when establishing an epoch binding. Later receiver/network outages MUST NOT prevent local durable admission of event types already authorized by that persisted binding.

The binding digest is:

`SHA256(CONTRACT_DOMAIN || uint32_be(core_major) || uint32_be(core_minor) || uint8(lane_id) || profile_set || scope_contract_set || event_type_set)`

`profile_set` is sorted by ASCII profile ID, then major, then minor. Each entry is:

`uint16_be(id_len) || id_ascii || uint32_be(major) || uint32_be(minor) || uint8(has_digest) || [32-byte digest]`

`has_digest` is exactly `0` or `1`; when `0`, no digest bytes follow; when `1`, exactly 32 digest bytes follow.

`scope_contract_set` is sorted lexicographically by scope bytes then profile ID. `(scope, profile_id)` is a unique key. Each entry is:

`uint16_be(scope_len) || scope || uint16_be(profile_id_len) || profile_id_ascii || 32-byte digest`

`event_type_set` is the ascending unique set of **already range-validated** event types. Each is encoded `uint16_be(event_type)` and the set is preceded by `uint16_be(count)`.

Each set is preceded by `uint16_be(count)`.

The binding is immutable for an epoch. A receiver that withdraws an event type or changes a selected semantic contract while unretired WAL history exists causes `CONTRACT_BINDING_CHANGED`. The sender MUST NOT skip durable events to accommodate a changed contract.

## 12. Canonical Mining and Miningcore semantic-contract digests

### 12.1 Mining scope contract

Mining Profile v1 requires a per-scope digest. Canonical source bytes are:

`uint16_be(profile_id_len) || "coredrp.mining" || uint32_be(profile_major) || uint32_be(profile_minor) || uint16_be(scope_len) || scope || uint8(payout_scheme) || uint16_be(coin_id_len) || coin_id_ascii || uint16_be(network_id_len) || network_id_ascii || uint16_be(completeness_policy_version) || uint16_be(retention_policy_version) || uint8(cross_sender_ordering_policy) || uint8(completeness_mode) || uint32_be(permitted_clock_skew_ms) || uint32_be(max_clock_step_ms) || uint32_be(probe_interval_ms) || uint32_be(probe_processing_max_ms) || uint32_be(evidence_expiry_ms) || uint32_be(unknown_grace_ms)`

The digest is `SHA256(source_bytes)`.

`coin_id` and `network_id` MUST match `[a-z0-9._-]{1,64}`.

Payout scheme values are: `1=PPLNS`, `2=PPLNSBF`, `3=PROP`, `4=SOLO`, `5=PPS`, `6=DIRECT_SOLO`. Zero is invalid for an active Mining scope contract.

`cross_sender_ordering_policy` is fixed to `1` for Mining Profile v1 and means Section 35 ordering.

`completeness_mode` is `1=RELAY_REQUIRED` or `2=NO_RELAY_REQUIRED`. Zero/unknown values are invalid.

Mining-specific source bytes MUST NOT contain Miningcore database/accounting schema versions.

### 12.2 Miningcore scope contract

Miningcore Profile v1 requires a separate per-scope digest. Canonical source bytes are:

`uint16_be(profile_id_len) || "coredrp.miningcore" || uint32_be(profile_major) || uint32_be(profile_minor) || uint16_be(scope_len) || scope || uint32_be(accounting_schema_version) || uint32_be(persistence_schema_version) || uint16_be(direct_candidate_validation_version) || uint16_be(settlement_policy_version)`

The digest is `SHA256(source_bytes)`.

The repository conformance corpus MUST provide source configuration, exact source bytes and expected digest for both profiles.

## 13. Event identity and cryptographic construction

Every Event contains sequence, event_type, scope, event_time_unix_ms, exact payload bytes and a 16-byte `relay_event_id`.

The event ID is immutable and part of the chain preimage. Core requires an RFC 9562 UUID; Mining Profile v1 requires UUIDv7. A sender MUST NOT reuse one `relay_event_id` for two different events.

For exact payload bytes `P`:

`payload_hash = SHA256(PAYLOAD_DOMAIN || uint32_be(len(P)) || P)`

For sender UUID bytes `S`, epoch UUID bytes `E`, lane `L`:

`chain[0] = SHA256(GENESIS_DOMAIN || S || E || uint8(L))`

For sequence `N`, event type `T`, relay-event UUID bytes `R`, scope `Q`, event time `M`, payload hash `H` and previous chain `Cprev`:

`chain[N] = SHA256(EVENT_DOMAIN || Cprev || S || E || uint8(L) || uint64_be(N) || uint16_be(T) || R || uint16_be(len(Q)) || Q || int64_be(M) || H)`

The sender hashes exact payload bytes written to WAL. The receiver hashes exact bytes received. Protobuf reserialization is never canonical evidence.

## 14. Batch validity, legal combinations and atomicity

An EventBatch MUST contain `1..max_batch_events` events; begin at a sequence in `1..2^63-1`; be contiguous; not overflow `2^63-1`; carry a 32-byte terminal hash equal to the computed final chain; and obey hard, negotiated and profile limits.

Before opening a durable-effect transaction, the receiver MUST verify structure, ranges, authorization, legal event/lane/scope combination and the full cryptographic chain.

Mining Profile v1 fixes this matrix:

| Event type | Lane | Scope |
|---|---:|---|
| CompletenessCheckpoint (`0x0001`) | 0 or 1 | empty |
| MiningShareEvent (`0x0100`) | 0 | non-empty Mining scope |
| MiningcoreAccountingShareEvent (`0x0200`) | 0 | non-empty Mining scope |
| BitcoinDirectCoinbaseCandidate (`0x0201`) | 1 | non-empty Mining scope |
| CandidateStateUpdate (`0x0202`) | 1 | non-empty Mining scope |

A known event on the wrong lane or with the wrong scope form is `SEMANTIC_PAYLOAD_INVALID`; it MUST NOT be reinterpreted as another event class.

For `MiningShareEvent`:

- `is_block_candidate=false` requires `candidate_hash`, `candidate_kind`, `transaction_confirmation_data` and `block_reward` all absent;
- `is_block_candidate=true` requires `candidate_hash` present and non-empty; profile/coin rules determine which other candidate fields are required;
- candidate-only fields MUST NOT be populated on non-candidates.

Normal receiver batch effects are all-or-nothing. Any structural/integrity failure commits nothing and is never quarantinable. Semantic failure at sequence `k` rolls back the batch and returns `SEMANTIC_PAYLOAD_INVALID` for `k`.

A previously admitted event is immutable and cannot be "corrected" in place. Progress past a semantic failure is possible only by accepting the exact same bytes after validator/configuration correction, or by the explicit quarantine flow in Section 24.

## 15. Sender durable admission, local idempotency and WAL

Application acceptance ordering is:

`validated work → resolve durable admission idempotency key → lane sequencer allocates sequence/time/id if new → exact payload serialized → complete WAL record and idempotency mapping written → durable flush succeeds → application success acknowledgement`

A sender MUST NOT acknowledge successful durable admission before the flush.

Any caller that may retry an admission after an unknown outcome MUST supply a stable `caller_admission_key`, or the applicable profile MUST provide an equivalent immutable business key. The sender MUST durably bind:

`caller_admission_key → relay_event_id → (lane, epoch, sequence, payload identity)`

in the same durable boundary as the WAL record. Retrying the same key returns the original admission/result and MUST NOT allocate a second event ID. Reusing the same key for different event bytes is a local idempotency conflict and MUST fail closed.

A caller MUST NOT blindly retry an unknown durable-admission outcome without such an idempotency mechanism.

Each lane has an independent bounded admission channel, sequence space, WAL and state anchor. Overflow policy is backpressure, never drop.

A WAL record MUST have local physical-corruption framing independent of the event chain, including a length and CRC32C or cryptographically equivalent record-integrity check.

Crash semantics:

| Failure | Required result |
|---|---|
| before WAL durability | no durable application success may have occurred |
| durable WAL/idempotency mapping, before application response | retry with same key returns the original event |
| after application success | event and admission mapping MUST recover from WAL/state |
| disk full/fsync EIO | stop new admission |
| torn unacknowledged tail | MAY truncate only when proven never durably acknowledged |
| middle-record corruption | fail closed; never skip |
| corrupted acknowledged record | recovery/safety incident; never silently create a new epoch |

Unacknowledged records MUST NEVER be evicted.

## 16. Durable sender anchor, temporal floor and pruning

The per-lane durable state includes at least:

- sender_id, lane_id, active log_epoch;
- last durable sequence and chain hash;
- last assigned event time;
- inherited temporal floor and last trusted checkpoint floor;
- oldest retained sequence;
- remembered receiver ID and database incarnation;
- remembered ACK sequence/hash;
- epoch contract-binding digest;
- permanent retired-epoch tombstones;
- durable admission-idempotency records still required for replay/deduplication.

The anchor MUST be written only after the WAL flush it describes. It may lag WAL but MUST NEVER lead it.

Anchor replacement MUST use write-temp, file flush, atomic rename/replace and directory metadata flush where required for crash durability.

On recovery, the anchor's sequence/hash MUST match WAL exactly; recovery scans forward.

Sender pruning ordering is:

`validate ACK → durably persist ACK anchor → only then make WAL <= ACK eligible for pruning`

Pruning MUST NOT remove evidence still required by unresolved idempotency, quarantine, gap, epoch or settlement state.

## 17. Deterministic flow control and pressure

`max_batch_payload_bytes` and `window_bytes` use **payload-only byte accounting**:

`payload_charge(batch) = Σ len(Event.payload)`

Scope bytes, event metadata, protobuf tags, HTTP/2 framing and gRPC framing do not contribute to these two logical counters. They remain bounded by the full-message hard cap in Section 7.

`window_events` counts events not yet cumulatively ACKed. `window_bytes` counts payload charge for those same unACKed transmitted events. Sender and receiver MUST compute the same counters using the rule above.

Heartbeats and clock probes MUST continue while event flow is window-blocked.

Pressure response is alert → stop new client/miner connections before accepted work is endangered → fail closed if durable admission cannot continue.

## 18. Stream handshake and sender/receiver single-writer fencing

A sender MUST hold an exclusive local or external fence over **`(sender_id,lane_id)`**, not over the epoch. The active epoch and every epoch transition are state protected beneath that lane-wide fence. Two processes using different epochs for the same sender/lane MUST NOT both durably admit work.

The receiver MUST allow at most one active stream per `(sender_id,lane_id)`. CoreDRP/1 uses first-writer-wins: a second stream receives `STREAM_ALREADY_ACTIVE`.

A PostgreSQL receiver MUST additionally hold a lifetime advisory/lease lock for the stream and serialize every commit with a row lock or equivalent compare-and-swap on durable stream state.

## 19. Reconnect reconciliation

Let `C` = receiver committed sequence, `R` = sender remembered ACK or zero, `T` = sender durable tail, and `E` = sender earliest retained sequence. Sequence comparisons are within one approved epoch.

| Condition | Result |
|---|---|
| `C == R` and hashes match | resume/replay from `C+1` |
| `C > R`, `C <= T`, sender verifies receiver hash | lost ACK; durably adopt receiver ACK then continue |
| `C < R` on same receiver incarnation | `RECEIVER_ROLLBACK`; stop |
| `C > T` | `SENDER_ROLLBACK`; stop |
| receiver requires sequence `< E` | `RECOVERY_GAP`; stop |
| common sequence hash differs | `SPLIT_LOG`; stop |
| different unapproved epoch | `EPOCH_NOT_APPROVED`; stop |
| receiver database incarnation changed | explicit restore/replacement reconciliation; never choose longest history |

No best-effort fallback exists.

A restored/promoted receiver database that might have lost ACKed transactions MUST mint a fresh database incarnation before serving CoreDRP.

## 20. ACK semantics

ACK means the receiver's profile effects, required exact raw/quarantine evidence, chain head, committed sequence and committed hash all durably committed.

ACKs MUST be monotonic. Equal duplicate ACK is valid. Lower ACK on the same receiver incarnation is `RECEIVER_ROLLBACK`.

An ACK MUST NOT advance beyond sender durable tail and its hash MUST equal the sender's locally computed chain at that sequence.

`Ack.committed_at_unix_ms` is operational metadata only. It MUST NOT be used as clock evidence, completeness evidence, event time, payout time or checkpoint proof.

Commit-success/ACK-loss is normal and follows Section 19.

## 21. Receiver transaction semantics

After complete batch validation, a conforming receiver transaction MUST atomically:

1. set/verify required durability policy;
2. lock current stream state;
3. validate epoch/sequence/chain head and inherited temporal/checkpoint floor;
4. validate profile semantics and legal event/lane/scope combination;
5. write exact evidence/event identity and application/profile effects;
6. write any explicitly authorized quarantine/gap records;
7. advance committed sequence/hash;
8. update checkpoint/completeness state;
9. COMMIT.

Anything fails → ROLLBACK → no ACK.

Miningcore MUST NOT route ordinary CoreDRP ingestion through the legacy receiver recovery-journal fallback.

## 22. Epoch transitions and inherited completeness floor

A new epoch is permitted only after a durable administrative transition records:

`old_epoch + final_sequence + final_chain_hash + old_last_event_time + old_last_trusted_checkpoint + inherited_temporal_floor → new_epoch + new_genesis + lane + operator + reason + timestamp`

The transition is performed while the sender retains its `(sender_id,lane_id)` writer fence.

For a continuing lane:

`new_epoch.temporal_floor = max(old_last_event_time, old_last_trusted_checkpoint, inherited_temporal_floor)`

The first new-epoch event MUST have `event_time_unix_ms >= temporal_floor`, and every event class covered by the inherited checkpoint MUST have `event_time_unix_ms > old_last_trusted_checkpoint`.

A new epoch MUST NOT make `PayoutSafeThrough` or `SafePruneThrough` regress or permit later history to introduce covered work at/before an already-proven boundary.

Retired epoch UUIDs are permanent tombstones and MUST survive event pruning. A retired epoch MUST NEVER become current again.

At sequence `2^63-1`, an approved epoch transition is mandatory; wrapping is forbidden.

## 23. Error model and wire disposition

Every protocol error has a numeric code and normative disposition in `docs/coredrp-v1-errors.md`.

Disposition classes are `STREAM_RETRYABLE`, `OPERATOR_INTERVENTION`, `PERMANENT_CONFIGURATION`, and `EVENT_QUARANTINABLE`.

`ProtocolError.disposition` on the wire is **informational redundancy only**. The registry is authoritative. A receiver MUST transmit the registry value. A peer that receives a disposition that disagrees with the registry MUST treat the frame as `MALFORMED_FRAME` and MUST NOT use the contradictory wire value to weaken handling.

## 24. Quarantine and immutable rejected-event progression

Quarantine is allowed only when Core structure, sequence, authorization, legal event identity and chain integrity are valid and profile semantics are invalid.

A rejected durable event is immutable. "Correction" never means rewriting sequence `k`; it means correcting receiver validator/configuration so the same bytes become valid, or using an explicit operator action.

Normative quarantine progression is:

1. receiver rejects sequence `k`; batch rolls back and no receiver durable progress passes `k`;
2. sender retains the exact event in WAL;
3. operator durably authorizes quarantine for exact `(sender,lane,epoch,sequence,event_type,relay_event_id,chain_hash)` plus expected state version;
4. sender retransmits the **same immutable event bytes**;
5. receiver re-verifies exact chain/event identity and atomically stores quarantine evidence plus the advanced watermark;
6. only then may ACK advance through `k`.

Never quarantinable: chain mismatch, sequence gap, malformed ordering/frame, split history, sender/receiver rollback, impossible/unapproved epoch, unauthorized scope, unknown/unadvertised event type, or checkpoint backdating.

A quarantine record retains sender/lane/epoch/sequence, relay ID, exact original bytes, payload/chain hashes, event type/scope, validator/profile version, semantic contract digest, rejection reason, operator/timestamp, idempotency key and state version.

## 25. Core completeness-gap records

Core owns the existence/lifecycle of a gap; profiles own consequences.

A gap records scope, lane, epoch, sequence/range, conservative neighbouring event-time bounds, classification, resolution state and immutable audit provenance.

If time coverage cannot be proven, the interval is conservative/open-ended from the last trusted boundary. Missing sequences MUST NOT be assigned false precision by interpolation.

Resolution states are `RESOLVED_RECONCILED` and `RESOLVED_WAIVED`. Waiver records accepted uncertainty; it does not rewrite history as complete.

## 26. Completeness checkpoints and immutable coverage set

Core event `0x0001` is CompletenessCheckpoint.

Mining Profile v1 uses lane-global checkpoints: enclosing Event.scope MUST be empty.

A checkpoint's covered Mining scopes are determined from the **persisted epoch contract scope set plus temporal membership effective at the checkpoint boundary**, not from current transport authorization. Historical checkpoint meaning MUST NOT change when certificate/authorization policy changes later.

The payload `complete_through_unix_ms` MUST equal enclosing `Event.event_time_unix_ms`.

Lane 0 interprets it as PayoutFence; lane 1 as CriticalCheckpoint.

Idle periodic checkpoints are REQUIRED to prove absence of accepted events during quiet intervals.

## 27. Checkpoint anti-backdating

Once a valid checkpoint boundary `T` is sequenced, every later event class covered by that checkpoint MUST have event time `> T`, including after an epoch transition.

Sender enforces before durable admission; receiver independently verifies against the inherited durable checkpoint floor.

Violation is `CHECKPOINT_BACKDATED_EVENT` and is never quarantinable.

## 28. Event-time assignment across epochs

Event time is assigned inside the single-consumer lane sequencer.

Within one epoch, assigned event times MUST NOT decrease. Across an approved epoch transition, the new epoch MUST inherit Section 22's temporal floor; it does not reset time ordering.

Minor local clock jitter MAY be clamped only within configured `maxClockStep`. A forward/backward step beyond it makes local clock BAD.

Ordinary Mining share Created is Core event time; receiver MUST NOT replace it with receipt time.

All relayed event classes obey negotiated/profile future-time bounds.

## 29. Clock probe mathematics

Clock probes are authenticated and bound to the active stream.

For receiver transmit `t1`, sender receive `t2`, sender transmit `t3`, receiver receive `t4`, reject `t3 < t2`.

Without assuming symmetric delay, sender-minus-receiver offset is bounded by `[t3-t4, t2-t1]`; interval width is uncertainty.

Receiver MUST use best/minimum-RTT observations over a rolling window, expire stale evidence, cap sender probe-processing duration, prevent active probe-ID reuse and use a monotonic local clock to detect receiver wall-clock steps.

The midpoint/symmetric-delay estimate MUST NOT be used as the financial safety bound.

## 30. Clock health, grace and recovery

Local clock state is GOOD/BAD. Remote bound state is GOOD/BAD/UNKNOWN.

- local BAD → stop covered admission and checkpoints;
- remote BAD → stop covered admission and checkpoints;
- remote UNKNOWN + local GOOD + grace active → admission MAY continue; trusted checkpoints MUST NOT advance;
- remote UNKNOWN + grace expired → stop covered admission;
- remote GOOD + local GOOD → normal.

Grace preserves ingestion only; `PayoutSafe` cannot advance beyond the last boundary proven before UNKNOWN.

Recovery from BAD requires trusted UTC to reach/pass durable last event time plus at least three fresh good remote probes spanning at least one probe interval.

Mining Profile v1 defaults: skew 2000 ms; `maxClockStep` 250 ms; probe interval 5 s; probe processing max 250 ms; evidence expiry 15 s; UNKNOWN grace 120 s. Stricter deployments are allowed. Looser values change the Mining semantic-contract digest.

## 31. Mining scope, payload and numeric semantics

Mining scope is exact ASCII `[A-Za-z0-9._-]{1,64}`; comparison is byte-exact/case-sensitive; no Unicode normalization/case folding.

Lane 0 is SHARE; lane 1 is CRITICAL.

Mining share `created_unix_ms` MUST equal Core event time.

Difficulty fields MUST be finite. Negative zero, NaN and infinities are invalid. Difficulty quantities used for accepted work MUST be strictly positive. `achieved_share_difficulty` MAY be zero only when the profile explicitly identifies the event as informational rather than accepted work.

MiningShareEvent candidate-field combinations obey Section 14.

## 32. Temporal sender membership and fail-closed completeness mode

Membership intervals are half-open `[valid_from, valid_until)`. If `valid_until` exists it MUST be greater than `valid_from`.

For scope `Q` and boundary `T`:

`RequiredSender(Q,T)` is a sender whose durable temporal membership for `Q` contains `T` and whose scope contract at `T` has `completeness_mode=RELAY_REQUIRED`.

A scope with an empty/missing membership table is **not** automatically safe. Vacuous safety is permitted only when an explicit, durable, semantic-contract-bound `NO_RELAY_REQUIRED` policy was already effective for that scope/boundary.

Membership start and end are both privileged actions. Membership history is append-only/audited. Transport revocation does not alter membership.

A membership change MUST NOT retroactively invalidate an already-proven `PayoutSafeThrough`. Normal membership activation/end MUST therefore be future-effective beyond the current safety frontier and clock uncertainty. A retroactive change is allowed only through an explicit reconciliation/waiver action that proves historical completeness or records the accepted uncertainty before the change becomes effective.

Ending a required sender without trusted completeness through the deactivation boundary creates an unresolved gap unless an explicit waiver is committed.

## 33. PayoutSafe and PayoutSafeThrough

For Mining scope `Q` and boundary `T`, `PayoutSafe(Q,T)` is true only when:

1. completeness mode for `Q,T` is durably known;
2. if mode is `RELAY_REQUIRED`, every `RequiredSender(Q,T)` has trusted lane-0 checkpoint evidence through the required skew-adjusted boundary;
3. every checkpoint used met the clock contract;
4. no unresolved recovery/completeness gap can cover relevant work at/before `T`;
5. no unresolved payout-significant quarantine covers the interval;
6. membership and semantic contracts used in the proof were durable before use;
7. anti-backdating plus inherited epoch floor prevent later valid history from introducing covered work at/before `T`.

`PayoutSafeThrough(Q)` is the greatest durably proven `T` for which `PayoutSafe(Q,T)` holds under the immutable evidence/state used to advance the frontier. It is monotonically nondecreasing.

For cross-sender completeness with symmetric maximum trusted skew `S`, a block timestamp `B` requires peer completeness at least `B+2S`, unless a tighter per-sender interval proof is demonstrably more conservative.

PPS and SOLO are not payout-fence gated. Direct block submission is never gated on remote completeness.

## 34. SafePruneThrough

`SafePruneThrough(Q)` is the greatest boundary through which destructible evidence may be removed without invalidating any required current/future proof. It MUST NOT exceed `PayoutSafeThrough(Q)` for payout-reconstruction evidence and is monotonically nondecreasing.

Discovery that an earlier safety decision was wrong is a safety incident, not permission to silently move a frontier backward after evidence destruction.

Never prune epoch tombstones, temporal floors, chain/ACK anchors, membership history, unresolved/resolved gap/quarantine audit records, override records or settlement evidence still required by a profile.

## 35. Mining scheme consequences and deterministic cross-sender ordering

Miningcore integration rules:

- PPLNS/PPLNSBF: settlement requires PayoutSafe; prune through `min(scheme cutoff, SafePruneThrough)`;
- PROP: settlement requires PayoutSafe; prune through `min(round cutoff, SafePruneThrough)`;
- custodial SOLO: payout is not fence-gated, but winning-miner share deletion is bounded to `created <= min(block.Created, SafePruneThrough)`;
- PPS: per-share accounting is not fence-gated and follows independent accounting retention;
- direct-coinbase SOLO: receiver/fences MUST NEVER gate local `submitblock`.

For any mining accounting operation requiring a total order across senders, including PPLNS/PPLNSBF boundary selection, the order is ascending by:

1. `event_time_unix_ms`;
2. sender UUID RFC 9562 bytes lexicographically;
3. sequence;
4. `relay_event_id` RFC 9562 bytes lexicographically.

Database physical/insertion order MUST NOT break ties. Ordering policy value `1` in Section 12 means exactly this ordering.

## 36. Direct candidate independence

A submitting edge MUST durably persist exact direct-candidate/settlement evidence locally before attempting `submitblock`.

Recorder unavailability, critical-lane failure or stale PayoutFence MUST NOT delay local submission. Critical-lane delivery is evidence replication, not part of block-submission latency.

## 37. PostgreSQL durability conformance

For a transaction advancing CoreDRP committed state:

- PostgreSQL `fsync` MUST be enabled;
- `SET LOCAL synchronous_commit = on` or stronger is REQUIRED;
- unlogged tables MUST NOT hold durable CoreDRP ledger/state;
- receiver effects and stream watermark MUST commit atomically.

If an HA target may be promoted without every ACKed transaction, promotion MUST mint a new receiver database incarnation and invoke reconciliation before serving traffic.

## 38. Failure semantics

**PostgreSQL unavailable:** no ACK for uncommitted data; apply backpressure; sender keeps spooling; report `RECEIVER_DURABILITY_UNAVAILABLE` with retryable disposition.

**Sender disk/fsync failure:** stop new durable admission; never accept only in memory.

**Corrupted WAL middle record:** fail closed; never skip or automatically create a new epoch.

**Commit succeeds, ACK lost:** Section 19 lost-ACK path.

**Duplicate sender:** lane-wide sender fence prevents admission; receiver also rejects second stream.

**Duplicate receiver:** DB/advisory fencing prevents concurrent ownership.

**Split history:** `SPLIT_LOG`, operator intervention.

**Partial batch failure:** whole batch rolls back; no ACK.

## 39. Heartbeats, drain and ChainProbe

Client/server heartbeats are direction-specific. Heartbeat timestamps and fields MUST NOT contribute to clock/completeness proof.

A graceful sender/receiver MAY send Goodbye. It is advisory; durable state remains authoritative.

ChainProbe is authenticated local-admin diagnostic only, rate-limited, never healthy-path flow. `count` is `1..256`; each returned hash is 32 bytes; results never mutate durable stream state.

## 40. Monetary and numeric representation

Financial coin-unit decimal values use `Decimal38Scale24.canonical`.

Grammar: `0` or `[1-9][0-9]{0,13}` optionally followed by `.` and `1..24` decimal digits with final fractional digit non-zero. No sign, exponent, whitespace, leading zero, trailing fractional zero, NaN or infinity.

Values are `<100000000000000`, at most 38 total decimal digits, scale at most 24. Positive-only fields reject `0`. `double` MUST NOT represent monetary amounts.

Post-parse profile limits: miner 256 UTF-8 bytes, worker 128, user-agent 256, source IP 64, source 64, session ID 128, candidate kind 64, transaction-confirmation data 4096. Miningcore direct-recipient count <=256, address metadata <=128 UTF-8 bytes, scriptPubKey <=10000 bytes.

## 41. Miningcore Bitcoin evidence consistency and candidate state

Bitcoin `block_hash` and `coinbase_txid` are exactly 32 bytes in canonical RPC/display digest order: decoding the canonical 64-character RPC hex yields the transmitted bytes.

`serialized_block` is exact raw Bitcoin consensus serialization. `script_pub_key` is exact raw script bytes and is authoritative; optional address metadata MUST map to that script on the configured network.

For BitcoinDirectCoinbaseCandidate the receiver MUST perform self-consistency validation before durable semantic acceptance:

1. parse the serialized block using Bitcoin consensus serialization and reject malformed/trailing bytes;
2. compute `SHA256d(header80)`, reverse digest bytes to canonical display order, and require equality with `block_hash`;
3. extract transaction 0, require it is coinbase, compute its non-witness txid in canonical display order, and require equality with `coinbase_txid`;
4. require the coinbase height commitment to equal `block_height` where BIP34 height commitment is mandatory for the configured network/height;
5. require `miner_script_pub_key` and `miner_reward_satoshis` to match the designated miner coinbase output;
6. require the `DirectRecipient` multiset `(script_pub_key, amount_satoshis)` to match the designated additional direct-pay coinbase outputs exactly; optional addresses must validate to their scripts;
7. require every coinbase output to be accounted for by the profile's miner/recipient classification and require `gross_reward_satoshis` to equal the sum of coinbase output values;
8. reject negative amounts, overflow or contradictory duplicate classifications.

The chain proves evidence immutability, not correctness; these semantic checks make the evidence internally auditable.

Bitcoin serialized block profile cap is 4,000,000 bytes. Candidate ID is a 16-byte UUIDv7. Initial candidate state MUST be PREPARED.

Allowed state transitions:

- PREPARED → SUBMITTED_UNCERTAIN, OBSERVED_ACTIVE, REJECTED, QUARANTINED
- SUBMITTED_UNCERTAIN → SUBMITTED_UNCERTAIN, OBSERVED_ACTIVE, REJECTED, QUARANTINED
- REJECTED → OBSERVED_ACTIVE only when later authoritative chain observation proves active; otherwise terminal except QUARANTINED
- OBSERVED_ACTIVE → QUARANTINED only for evidence-integrity/operator investigation
- QUARANTINED terminal unless explicit audited reconciliation records a replacement state outside this graph.

`submission_attempts` never decreases; `definitive_misses <= submission_attempts`; `last_attempt` absent iff attempts are zero.

## 42. Privileged actions and canonical ADMIN encoding

Privileged action type IDs are globally fixed:

- `0x0001` Core quarantine-and-advance
- `0x0002` Core gap reconciliation
- `0x0003` Core gap waiver
- `0x0004` Core epoch-transition approval
- `0x0101` Mining membership start
- `0x0102` Mining membership end
- `0x0103` Mining completeness-mode change
- `0x0104` Mining settle-without-fence override
- `0x0201` Miningcore capability activation

Action IDs MUST NOT be reused.

Every admin request carries a client-generated idempotency UUID and expected state version. The mutation transaction atomically writes idempotency record and protected state change.

Canonical request body `B` is TLV version 1:

`uint16_be(1) || uint16_be(field_count) || repeated(field)`

where fields are sorted by strictly increasing `field_id`, no duplicate IDs, and each field is:

`uint16_be(field_id) || uint32_be(value_len) || value_bytes`.

Field values use the exact primitive encodings from Section 5: UUID = 16 RFC 9562 bytes; unsigned/signed integers = fixed-width big-endian stated by that action schema; scope/string = exact validated bytes without terminator. Optional absent fields are omitted. JSON is never canonical input to this digest.

All actions include field `1=idempotency_uuid(16)` and field `2=expected_state_version(uint64_be)`.

Core quarantine action additionally uses: `3=sender_uuid`, `4=lane(uint8)`, `5=epoch_uuid`, `6=sequence(uint64)`, `7=chain_hash(32)`, `8=reason_utf8`.

Core gap reconciliation/waiver uses: `3=gap_uuid`, `4=resolution_reason_utf8`.

Core epoch approval uses: `3=sender_uuid`, `4=lane(uint8)`, `5=old_epoch_uuid`, `6=final_sequence(uint64)`, `7=final_chain_hash(32)`, `8=new_epoch_uuid`, `9=inherited_temporal_floor(int64)`, `10=inherited_checkpoint_floor(int64)`, `11=reason_utf8`.

Mining membership start/end uses: `3=scope`, `4=sender_uuid`, `5=effective_unix_ms(int64)`, `6=reason_utf8`.

Mining completeness-mode change uses: `3=scope`, `4=effective_unix_ms(int64)`, `5=mode(uint8)`, `6=reason_utf8`.

Mining settle-without-fence uses: `3=scope`, `4=block_or_settlement_id_bytes`, `5=reason_utf8`.

Miningcore capability activation uses: `3=scope`, `4=capability_ascii`, `5=effective_unix_ms(int64)`, `6=reason_utf8`.

`admin_digest = SHA256(ADMIN_DOMAIN || uint16_be(action_type) || uint32_be(len(B)) || B)`.

Same idempotency key + same digest returns the original result. Same key + different digest is `IDEMPOTENCY_KEY_CONFLICT`. State-version mismatch is `ADMIN_ACTION_CONFLICT`.

## 43. Security boundary

mTLS authenticates peers and transport. Authorization is explicit per sender/lane/scope.

The unkeyed SHA-256 chain detects accidental corruption, inconsistent history, replay and divergent branches when at least one trusted anchor survives. It is NOT independently tamper-proof against an attacker able to rewrite all history and anchors, and CoreDRP is not Byzantine consensus or proof that a compromised authenticated sender is truthful.

Applications needing total-storage-compromise resistance SHOULD add independently protected signed/HMAC anchors or external append-only transparency storage.

No 0-RTT application data is permitted.

## 44. Specification, compatibility and CI integrity

Every normative text/source artifact MUST be valid UTF-8, contain no NUL/control corruption, and pass integrity checks.

CI MUST verify:

- UTF-8/text integrity;
- exactly contiguous top-level sections 1..50, minimum normative size and terminal sentinel;
- section cross-reference resolution;
- protobuf compilation and linting;
- Core ← Mining ← Miningcore dependency/name boundaries plus negative self-tests;
- error enum ↔ error registry parity;
- event-type allocation consistency;
- all wire-visible messages, fields, oneofs, enums, numeric enum values, services/RPCs and reserved ranges against the compatibility baseline;
- fixed domain tags;
- positive/negative cryptographic vectors;
- Mining/Miningcore semantic-contract source/digest vectors;
- profile-aware semantic vectors including all declared negative cases;
- reconnect, rollback, recovery-gap, quarantine, membership, epoch-floor and WAL crash-ordering state vectors;
- independent C# UUID/hash/contract/ADMIN verification;
- a TLA+ model that contains explicit crash/fault/reconnect/epoch/writer transitions plus a mutation/self-test capable of demonstrating invariant failure.

Deleted protobuf fields MUST reserve field number and SHOULD reserve name.

## 45. Normative safety invariants

Machine-testable invariants include:

`ACK_sequence <= receiver_durable_sequence`

`sender_prune_sequence <= sender_durably_remembered_ACK`

`common(sender,lane,epoch,sequence) => chain_hash identical`

`at_most_one_sender_writer(sender,lane)`

`retired_epoch never becomes current again`

`new_epoch.temporal_floor >= max(old_last_event_time, old_last_trusted_checkpoint, old_temporal_floor)`

`checkpoint(T) => every later covered event in every later approved epoch has event_time > T`

`unresolved_gap_at_or_before(T) => NOT PayoutSafe(T)`

`unresolved_payout_quarantine_at_or_before(T) => NOT PayoutSafe(T)`

`unknown_membership_or_completeness_mode => NOT PayoutSafe`

`PayoutSafeThrough` monotonically nondecreasing

`SafePruneThrough <= PayoutSafeThrough`

`SafePruneThrough` monotonically nondecreasing

`same caller_admission_key => same relay_event_id and same immutable admission`

## 46. Protocol evolution

CoreDRP/1 uses negotiated Core minors, profile versions, advertised event types and semantic-contract digests.

A sender MUST NOT emit a type not accepted in the persisted epoch binding. Unknown/unadvertised types remain fatal even though protobuf preserves unknown fields.

Adding a safety-significant top-level frame alternative requires an explicitly negotiated compatible Core minor; protobuf unknown-field preservation alone is insufficient.

Event-type numbers, admin-action numbers, enum numeric values and protobuf field numbers are never reused after stable release. Compatibility baseline changes require explicit protocol review.

## 47. Out of scope for CoreDRP/1

CoreDRP/1 does not standardize receiver active/active HA across independent databases, automatic retroactive payout compensation, historical statistics rebuilding, remote-durable Stratum admission, Byzantine consensus against fully malicious authenticated senders/storage, or external standards governance.

## 48. Reference implementation requirements

Miningcore MUST:

- preserve sender event time;
- use dedicated CoreDRP ingest with no ordinary legacy recovery-journal fallback;
- use `SET LOCAL synchronous_commit = on`;
- enforce sender-lane single-writer ownership and receiver transactional/advisory fencing;
- persist sender UUID mapping/ordinals without reuse;
- make local durable admission retries idempotent before using `relay_event_id` as a financial effect key;
- uniquely identify receiver share effects by `(poolid, senderordinal, relayeventid)` or equivalent partition-safe key;
- use Section 35 total ordering whenever equal-time shares can affect a financial window;
- expose completeness, gap, clock, spool, replay and quarantine metrics;
- retain local direct-candidate evidence before `submitblock` and validate Section 41 self-consistency at the recorder.

## 49. Conformance-test requirements

Before CoreDRP/1 is declared stable, the repository MUST contain and execute:

- hash/genesis vectors for lanes 0, 1 and 255;
- type `0xFFFF` boundary and out-of-range rejection;
- empty payload/scope and max 65535-byte scope with exact preimage bytes;
- sequence above `2^32`, sequence `2^63-1`, sequence-zero rejection;
- negative event time and recognizable UUID byte-order trap;
- contract-binding vectors using actual Mining/Miningcore semantic digests, including both `has_digest=1` and `has_digest=0` branches;
- canonical ADMIN vectors for Core-owned actions;
- semantically valid checkpoint, Mining, Miningcore-accounting, BitcoinDirectCoinbaseCandidate and CandidateStateUpdate examples;
- malformed/invalid-combination profile vectors;
- reconnect/rollback/recovery-gap cases;
- WAL crash-ordering and local admission-idempotency cases;
- cross-epoch temporal-floor and checkpoint cases;
- duplicate sender/receiver fencing cases;
- quarantine at representative batch positions;
- membership/completeness-mode fail-closed cases;
- deterministic cross-sender ordering tie cases.

Hash-primitive vectors that jump directly to high sequence values MUST be labelled `crypto_only` and include an explicit synthetic previous-chain anchor; they MUST NOT be presented as reachable event history from genesis.

## 50. Authorship

CoreDRP — Core Durable Relay Protocol was originally designed and authored by **Rob Cooke** in 2026 and was originally developed for the Miningcore project.

The canonical project is `https://coredrp.org` and the source repository is `https://github.com/NINJAK1DD/CoreDRP`.

<!-- COREDRP-SPEC-END:50 -->
