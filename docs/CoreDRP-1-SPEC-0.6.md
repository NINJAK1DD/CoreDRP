# CoreDRP/1 — Core Durable Relay Protocol

**Originally designed and authored by Rob Cooke, 2026.**  
Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

**Status:** Draft 0.6 implementation-freeze candidate; specification-first and pre-implementation.  
**Wire:** Core 1.1.  
**Reference integration target:** Miningcore.

RFC 2119/RFC 8174 uppercase key words are normative.

## 1. Status and authority

Draft 0.6 supersedes Draft 0.5 for normative interpretation. Earlier drafts remain historical evidence only.

Normative authority, highest first: this specification; incorporated numbered registries; conformance vectors; protobuf definitions; reference tooling. Reference code MUST NOT override the specification or an incorporated registry.

Incorporated registries are: `coredrp-mining-v1-semantics.md`, `coredrp-miningcore-v1-semantics.md`, `coredrp-v1-draft06-contracts.md`, `coredrp-v1-bitcoin-network-policies.md`, `coredrp-v1-admin-actions.md`, `coredrp-v1-errors.md`, `coredrp-v1-error-emission.md`, `coredrp-v1-metrics.md`, and the event/wire registries already in this repository.

## 2. Layering

Core owns authenticated identities, opaque scopes, lanes, epochs, sequencing, event time, exact payload bytes, event identity, chaining, sender durability, replay, cumulative ACK, generic checkpoints, gaps, quarantine mechanics, flow control, clock evidence, reconnect/recovery, and ADMIN digest mechanics.

Mining owns mining scope syntax, lane/event meanings, temporal membership/completeness policy, payout safety, mining clock policy, mining admission identity, and deterministic cross-sender order. Miningcore owns PostgreSQL integration, accounting projection, direct Bitcoin evidence, payout/pruning integration, candidate state, and metrics.

Dependency direction is Core <- Mining <- Miningcore only.

## 3. Terms

A sender durably admits events. A receiver durably commits them. A lane is one ordered stream. An epoch is one UUID-scoped history of one sender/lane. A normal epoch transition drains all durable history. Exceptional abandonment retires an undrainable epoch only with durable gap evidence.

Receiver ID identifies one logical recorder service. Receiver database incarnation identifies one durable database history. `PayoutSafeThrough(scope)` is the greatest receiver-proven time boundary satisfying the Mining completeness rules. `SafePruneThrough(scope)` is the greatest destructible-evidence boundary that does not invalidate required proofs.

## 4. Fixed identifiers and domains

Packages are `coredrp.v1`, `coredrp.mining.v1`, `coredrp.miningcore.v1`. Profile IDs are exact ASCII `coredrp.mining` and `coredrp.miningcore`.

Sender SAN is `urn:coredrp:sender:<uuid>`; receiver SAN is `urn:coredrp:receiver:<uuid>`.

Assigned CoreDRP/1 domains are exact ASCII without terminator: `CoreDRP1-PAYLOAD`, `CoreDRP1-EVENT`, `CoreDRP1-GENESIS`, `CoreDRP1-CONTRACT`, `CoreDRP1-ADMIN`, `CoreDRP1-ADMISSION`. These assignments MUST NOT be reinterpreted. The set closes at stable CoreDRP/1; adding a domain after stable release requires a protocol revision.

## 5. Primitive encodings and ranges

Cryptographic integers use fixed-width big-endian encoding: `uint8`, `uint16_be`, `uint32_be`, `uint64_be`; event time uses signed two's-complement `int64_be`; UUIDs use 16 RFC 9562 network-order bytes; SHA-256 digests are 32 bytes.

Before any value enters any cryptographic preimage: lane is `0..255`; event type `0..65535`; sequence `1..2^63-1`; scope length `0..65535`; payload length fits uint32 and all negotiated/profile caps; Core/profile versions fit uint32; profile IDs are ASCII; production event time is `0..253402300799999` ms. Implementations MUST reject before narrowing, sorting, deduplication, or hashing; they MUST NOT truncate, wrap, or language-cast an unvalidated wider integer.

All time arithmetic, including `B+2S`, uses checked arithmetic and fails closed on overflow.

## 6. Event/lane placement

Mining lane 0 is SHARE; lane 1 is CRITICAL. Core type `0x0001` is completeness checkpoint. Mining type `0x0100` is MiningShareEvent. Miningcore types `0x0200`, `0x0201`, `0x0202` are accounting share, Bitcoin direct candidate, and candidate state update.

Known event type on forbidden lane or scope form is `INVALID_EVENT_PLACEMENT`, non-quarantinable. Unknown or unadvertised type is fatal according to the error registry.

## 7. Hard resource limits

Pre-negotiation maxima: gRPC message 20 MiB; Hello 256 KiB; implementation string 128 UTF-8 bytes; profile ID 64 ASCII bytes; 32 profile entries; 1024 scope contracts; 1024 advertised event types; scope 65535 bytes; event payload 16 MiB; 4096 events/batch; batch logical flow charge 16 MiB; ChainProbe count 256.

Intrinsic single-object excess is permanent; splittable aggregate excess is retryable. The effective limit is the minimum of hard, negotiated, and profile-specific limits.

## 8. Authentication and authorization

TLS 1.3 mTLS is REQUIRED. Hello UUIDs MUST match the unique corresponding CoreDRP URI SAN. Multiple authoritative CoreDRP sender/receiver URI SAN identities are invalid. Other SAN types MAY coexist but are not CoreDRP identity.

Transport authorization and temporal Mining membership are distinct. Transport authorization gates every new scoped event and every scope newly asserted by a checkpoint. It never rewrites historical membership or checkpoint meaning.

## 9. Handshake validity

First frames are ClientHello then ServerHello or ProtocolError. Empty/wrong-direction/second hello is `MALFORMED_FRAME`.

For sender durable tail `T=0`, earliest retained `E=1`. For `T>0`, `1 <= E <= T+1`. Remembered ACK sequence/hash are both present or both absent; present hash is exactly 32 bytes and the sequence is within sender durable history.

UUIDs and digests use exact lengths. Scope-contract digest is exactly 32 bytes. Duplicate profile-version rows, event types, or version-qualified scope contracts are invalid.

## 10. Core/profile compatibility

Draft 0.6 implementations implement **Core 1.1 only**. They MUST advertise Core major 1, minor 1 and MUST NOT claim Core 1.0 compatibility. Core 1.0 is historical and is not negotiated by a Draft 0.6 endpoint because Core 1.1 changed clock-response semantics and added receiver clock-state signalling.

Each ProfileSupport row is one exact `(profile_id, major, minor)` with an exact minimum Core version. The compatibility registry is normative:

- Mining 1.1 requires Core 1.1;
- Miningcore 1.1 requires Core 1.1 and Mining 1.1 on the same scope.

Select highest mutually supported profile major, then highest minor in that major, after filtering by the negotiated Core version. Mining/Miningcore profile-global semantic digests are absent because semantics are scope-owned.

## 11. Epoch contract binding

Before first event, sender requires durable epoch approval and successful binding negotiation. Binding is immutable within an epoch.

Canonical preimage is:

`CONTRACT_DOMAIN || uint32_be(core_major) || uint32_be(core_minor) || uint8(lane) || uint16_be(profile_count) || profile_entries || uint16_be(scope_contract_count) || scope_contract_entries || uint16_be(event_type_count) || event_types`.

Profile entries are sorted by raw `(profile_id_ascii, major, minor)` and encoded:

`uint16_be(id_len)||id||uint32_be(major)||uint32_be(minor)||uint8(has_digest)||[digest32 if has_digest=1]`.

Scope-contract entries are sorted by raw `(scope_bytes, profile_id_ascii, major, minor)` and encoded:

`uint16_be(scope_len)||scope||uint16_be(id_len)||id||uint32_be(major)||uint32_be(minor)||digest32`.

Event types are range-validated first, unique before encoding, sorted ascending numerically, then encoded as `uint16_be` values. Counts are over encoded entries. Mining/Miningcore profile entries use `has_digest=0`; their scope entries carry exact 32-byte semantic digests.

`contract_binding_digest = SHA256(preimage)`. Draft 0.6 publishes the complete Profile 1.1 preimage/digest in the conformance vectors.

## 12. Semantic contracts

Mining 1.1 and Miningcore 1.1 canonical source grammars are defined in `coredrp-v1-draft06-contracts.md`.

Mining binds scope identity, coin/network, payout scheme, completeness/retention versions, cross-sender ordering, clock parameters, fixed semantic retry threshold, and bounded admission-idempotency policy parameters.

Miningcore binds accounting/persistence schema, direct-candidate validation version, settlement policy, and an exact 32-byte Bitcoin network-policy digest derived from the Mining-selected `network_id`.

Completeness mode remains temporal audited policy and is not immutable scope-contract state.

## 13. Event cryptographic construction

`payload_hash = SHA256(PAYLOAD_DOMAIN || uint32_be(len(P)) || P)`.

`chain[0] = SHA256(GENESIS_DOMAIN || sender_uuid || epoch_uuid || uint8(lane))`.

`chain[N] = SHA256(EVENT_DOMAIN || chain[N-1] || sender_uuid || epoch_uuid || uint8(lane) || uint64_be(N) || uint16_be(type) || relay_event_uuid || uint16_be(scope_len) || scope || int64_be(time) || payload_hash)`.

Exact received/WAL payload bytes are identity. Protobuf reserialization is never canonical evidence.

## 14. Two-phase batch validation

Phase A, before the durable-effect transaction: framing, counts, integer/time ranges, size limits, transport authorization, placement, required scope-contract ownership, and complete chain verification including terminal hash.

Phase B, inside the transaction after stream-state lock: expected epoch/sequence/head, temporal membership, checkpoint coverage authorization, profile semantics, referential state, gap/quarantine state, and application effects.

Any failure rolls back the whole current batch; no prefix is committed from an invalid batch. `semantic_retry_threshold` is exactly contract-bound and defaults to 3 in Mining 1.1. After the threshold of consecutive identical semantic failures at the same immutable event identity, receiver emits `SEMANTIC_RETRY_LIMIT` until configuration/validator changes or explicit quarantine authorization.

## 15. Durable admission identity

Admission digest is:

`SHA256(ADMISSION_DOMAIN || uint8(lane) || uint16_be(type) || uint16_be(scope_len) || scope || uint32_be(request_len) || canonical_request_bytes)`.

MiningShare request encoding is version 1 from the Mining semantics registry: fixed big-endian integers, binary64 big-endian floats, explicit booleans and optional presence markers, exact UTF-8/ASCII length prefixes, no normalization. Generated `created_unix_ms`, Core sequence, log epoch, and relay UUID are excluded.

Mining idempotency policy v3 uses caller key structure `(producer_id_uuid, producer_generation, admission_sequence)` inside `(sender_id,lane_id)`. Detailed digest/result mappings are retained only for one bounded active generation. A sealed generation is summarized by durable `retired_generation_high_water`; any retry naming a retired generation is rejected locally and can never mint another event. This provides permanent no-double-mint safety with bounded detailed state. Exact rules are in the Mining semantics registry.

WAL admission, active-generation mapping, seal/high-water state, and application success obey one durable-before-success boundary.

## 16. Sender WAL, anchor and recovery

WAL records use length plus CRC32C or equivalent framing. Anchor MAY lag WAL but MUST NOT lead it. Recovery verifies anchor before trusting subsequent history.

Corruption/truncation at or before anchor is a safety incident. Corruption after anchor may truncate only a proven unACKed torn tail. Middle corruption fails closed. UnACKed records are never silently evicted.

Sender spool has durable cap/high-water thresholds; before exhaustion stop new work, and at cap fail new admission rather than accept in memory.

## 17. Flow control

Per-event logical charge is `32 + len(scope) + len(payload)`. `window_bytes` counts charge of unACKed transmitted events; `window_events` counts those events.

Zero in either dimension pauses all EventBatch traffic, including empty payloads. Control/heartbeat/clock traffic remains allowed. WindowUpdate MUST NOT exceed handshake-negotiated maxima.

## 18. Single-writer and duplicate-receiver fencing

Sender fence is `(sender_id,lane_id)` across epochs. Receiver permits one active stream per sender/lane and uses durable ownership plus row/CAS protection around stream effects.

Independent receiver database histories use distinct receiver IDs or an explicit receiver-replacement approval. One sender stream MUST NOT treat competing uncoordinated durable histories as one logical receiver.

## 19. Reconnect and receiver replacement

Evaluate in exact order: receiver ID mismatch; database-incarnation mismatch; epoch approval; `C>T` sender rollback; `C<R` receiver rollback; bootstrap genesis mismatch; chain mismatch at `C`; `C+1<E` recovery gap; `C>R` verifiable -> adopt ACK; `C>R` unverifiable -> SPLIT_LOG; otherwise resume.

Hash equality at `C` proves equality of the committed prefix because each chain value commits every predecessor.

Receiver replacement uses ADMIN `0x0007`, preserves prior receiver/ACK audit anchor, and applies the same chain rules before repin/adopt/replay. Lost ACKed history that is not retained becomes `RECOVERY_GAP`; mismatch becomes `SPLIT_LOG`.

## 20. ACK semantics

ACK means receiver event effects, evidence, stream head, and checkpoint state durably committed. ACK is cumulative and monotonic.

Sender validates ACK then durably remembers receiver ID/incarnation, sequence/hash before ACK-dependent sender WAL pruning. Sender ACK persistence is a sender replay/prune property; **it is not part of receiver-side PayoutSafe proof**.

`Ack.committed_at_unix_ms` is operational metadata and MUST NOT be used as event-time, clock, completeness, payout, or checkpoint evidence.

## 21. Receiver transaction semantics

Within one durable transaction: configure required durability; lock stream state; verify receiver/epoch/sequence/head/floors; temporal membership and policy; profile semantics and referential state; exact application effects/evidence; authorized gap/quarantine state; committed head/checkpoint update; COMMIT. Only after COMMIT may ACK be emitted.

## 22. Epoch lifecycle

Initial epoch requires ADMIN `0x0005`. Normal transition `0x0004` requires receiver committed = sender remembered ACK = sender durable tail = final sequence with matching hash.

Exceptional abandonment `0x0006` is one atomic privileged state transition: it verifies the old state, records exact or wildcard gap evidence covering the abandoned suffix, retires the old epoch, approves the new epoch, and records inherited temporal/checkpoint floors in one transaction. No intermediate state may expose a retired epoch without its gap evidence.

If any abandoned record scope is unknown/corrupt, create a lane-wide wildcard gap relevant to every applicable old-epoch scope. Retired-epoch reconciled import verifies old tombstone, exact chain/range/event identities and applies missing effects idempotently without making that epoch current.

## 23. Error model

The error registry is authoritative. `ProtocolError.disposition` is redundant informational metadata and MUST equal the registry; mismatch is `MALFORMED_FRAME`.

Structural, authorization, placement, clock, identity, chain, rollback, membership, and epoch errors are never quarantinable. Only correctly placed/Core-valid profile semantic payload failures may enter quarantine handling.

## 24. Quarantine

Quarantine authorization names sender/lane/epoch/sequence/type/relay UUID/chain hash. Sender retransmits exact immutable bytes. Receiver re-verifies identity/chain and atomically stores evidence plus watermark before ACK.

Changed bytes are `EVENT_IDENTITY_MISMATCH`, never a correction of the original event.

## 25. Gaps and resolution semantics

Gap scope is exact scope or wildcard lane scope and records sender/lane/epoch/range, conservative time bounds, chain evidence, classification, status, and audit provenance.

Statuses have payout meaning:

- `UNRESOLVED`: blocks PayoutSafe for every relevant range/scope;
- `RESOLVED_RECONCILED`: verified import has restored the missing effects/evidence, so the reconciled range no longer blocks PayoutSafe;
- `RESOLVED_WAIVED`: uncertainty is accepted administratively but completeness was not proved; the waived range **never becomes PayoutSafe** and MUST NOT advance `PayoutSafeThrough`.

A waiver may support an explicit `SETTLE_WITHOUT_FENCE_OVERRIDE` for a named settlement, but that override is distinct from PayoutSafe and does not manufacture or advance the safety frontier.

## 26. Checkpoints and authorization

Mining checkpoints are lane-global with empty Core scope. Covered scopes derive from persisted epoch scope contracts plus temporal membership/mode at checkpoint time.

Before accepting a new checkpoint, receiver verifies sender authorization for every scope it would cover. Revoked scope authorization rejects the checkpoint with `UNAUTHORIZED_SCOPE` until policy is ended/reconciled or uncertainty is explicitly recorded. Historical checkpoints are never reinterpreted after later revocation.

## 27. Anti-backdating

After trusted checkpoint boundary `T`, every later covered event in the same or successor epoch has event time strictly greater than `T`. Sender and receiver enforce. Violation is `CHECKPOINT_BACKDATED_EVENT`, non-quarantinable.

## 28. Event time

Lane sequencer assigns nondecreasing production-range event time and persists the last assigned value. Mining `created_unix_ms` equals Core event time. Successor epoch floor is max(old last event, old trusted checkpoint, inherited floor).

A wall-clock step beyond effective `max_clock_step_ms` makes local clock BAD; it never just moves the floor arbitrarily.

## 29. Clock probes and ClockStateUpdate validity

Receiver owns authoritative `t1`, keyed by unique outstanding probe ID. ClockProbeResponse supplies sender `t2/t3` only. Unknown, duplicate, or expired response is discarded. Receiver-local receive time is `t4`. Checked arithmetic is mandatory.

For a valid probe: reject `t3<t2`; `L=t3-t4`; `U=t2-t1`; `rtt=(t4-t1)-(t3-t2)`. GOOD iff `[L,U]` lies wholly inside permitted skew; BAD iff wholly outside; UNKNOWN otherwise/no fresh evidence. Different-time intervals MUST NOT be intersected.

ClockStateUpdate generation is **stream-local**. It starts at 1 after each successfully negotiated authenticated stream and increases strictly within that stream. Sender resets remembered generation only when a new ServerHello establishes a new stream; generations are never compared across reconnects.

For each ClockStateUpdate, sender validates before trust:

- generation > last accepted generation in this stream;
- `evidence_valid_for_ms` is `1..effective_evidence_expiry_ms`;
- `effective_permitted_skew_ms` equals the strictest currently bound lane policy, never a receiver-selected looser value;
- GOOD requires lower/upper bounds both present, `lower <= upper`, and `-S <= lower <= upper <= S`;
- BAD with bounds requires an interval wholly outside `[-S,S]`;
- UNKNOWN MUST NOT claim a fully GOOD interval;
- a present probe ID refers to a valid receiver observation for this stream;
- enum/reason/state combinations follow the state matrix in the conformance registry.

Contradictory or out-of-policy state update is `CLOCK_CONTRACT_VIOLATION`; structurally malformed presence/ranges are `MALFORMED_FRAME`.

## 30. Clock policy, BAD latch, grace, recovery

Multi-scope lane uses the strictest active clock parameters. Local BAD or remote BAD stops covered admission/checkpoints.

Remote UNKNOWN from startup/ordinary evidence expiry may use configured UNKNOWN grace; it never advances trusted checkpoints. **BAD is latched**: expiry of BAD evidence produces `RECOVERING`, not a fresh UNKNOWN grace that resumes admission. RECOVERING continues to block covered admission/checkpoint advancement.

Exit BAD/RECOVERING only when trusted UTC is not behind durable last event time and at least three fresh GOOD observations span at least one effective probe interval. A newer definitive BAD resets recovery evidence. Receiver wall-step detection compares wall and monotonic elapsed deltas; excessive divergence is BAD.

## 31. Mining event admission and ownership

Mining scope is exact `[A-Za-z0-9._-]{1,64}` ASCII. Under RELAY_REQUIRED, every payout-relevant lane-0 MiningShareEvent or MiningcoreAccountingShareEvent at event time `M` requires durable temporal membership `(sender,scope,M)`. Transport-authorized but temporally unlisted sender fails with `TEMPORAL_MEMBERSHIP_REQUIRED`.

`0x0100` requires Mining(scope). `0x0200`, `0x0201`, `0x0202` require both Mining(scope) and Miningcore(scope) exact selected versions/digests.

Payload semantics are exactly the incorporated Mining/Miningcore semantics registries.

## 32. Temporal membership/mode and retroactivity

Membership and completeness-mode intervals are append-only, non-overlapping, half-open `[from,until)`. Missing mode fails closed. `RequiredSender(Q,T)` is membership covering `T` when mode at `T` is RELAY_REQUIRED. Empty membership is payout-safe only under an explicit NO_RELAY_REQUIRED interval.

Ending non-empty membership at `valid_until` requires trusted completeness through at least `valid_until-1` ms or creates uncertainty/gap.

An ordinary membership start/end or mode change with `effective_unix_ms <= PayoutSafeThrough(scope)` MUST be rejected with `ADMIN_ACTION_CONFLICT`. Ordinary future changes must also be beyond the current frontier plus applicable clock uncertainty.

Retroactive correction uses an explicitly audited temporal-policy reconciliation operation. It MUST block further safety-frontier advancement for the affected scope, record the historical uncertainty, and MUST NOT silently redefine or move backward a previously proven frontier. Settlement requiring an exception uses the separate settle-without-fence override.

## 33. PayoutSafe

Receiver decides PayoutSafe using receiver-observable durable facts only.

`PayoutSafe(Q,T)` requires: durable known mode at T; when RELAY_REQUIRED, all `RequiredSender(Q,T)` have receiver-committed trusted checkpoint evidence through the required skew-adjusted boundary; each checkpoint satisfied clock policy; no relevant UNRESOLVED gap; no relevant RESOLVED_WAIVED uncertainty covering T; no payout-significant unresolved quarantine; policy/contract evidence durable before use; anti-backdating and epoch-floor invariants preventing later covered history at/before T.

A checkpoint contributes immediately after the receiver transaction that commits its event/effect/checkpoint proof. Sender ACK receipt/persistence is **not required** for PayoutSafe and cannot be used as a receiver-side proof prerequisite because it is not receiver-observable on a healthy stream.

`PayoutSafeThrough(Q)` is greatest durably proven T and is monotonic. A waiver never advances it.

## 34. SafePruneThrough

`SafePruneThrough(Q)` is monotonic and, for payout evidence, never exceeds `PayoutSafeThrough(Q)`. It constrains destructive removal of receiver evidence and sender/application state needed for proofs.

Never prune receiver/epoch anchors, policy history needed for proof, unresolved/reconciled/waived gap audit, quarantine/override audit, retired-epoch import evidence, producer generation high-water records, or settlement evidence still required.

Sender WAL pruning additionally requires sender-durable remembered ACK per Section 20.

## 35. Mining schemes and order

PPLNS/PPLNSBF/PROP settlement requires PayoutSafe. Destructive pruning is no farther than scheme cutoff and SafePruneThrough. PPS and custodial SOLO follow their profile-defined non-fence semantics. Direct consensus submission never waits for remote completeness.

Canonical cross-sender accounting order is event time, sender UUID bytes, sequence, relay UUID bytes.

## 36. Direct candidate independence

Submitting edge durably records exact candidate/settlement evidence locally before `submitblock`. Recorder, critical-lane, completeness, or payout-fence failure MUST NOT delay local submission.

## 37. PostgreSQL durability

Transactions advancing receiver durable state require PostgreSQL `fsync=on`, `SET LOCAL synchronous_commit=on` or stronger, logged tables, and atomic stream/effect commit. Standby promotion that may omit ACKed transactions creates a new database incarnation before serving CoreDRP.

## 38. Failure decision table

- PostgreSQL unavailable before COMMIT: no ACK, sender spools, retry after durable DB returns.
- sender fsync/disk failure: stop new durable admission; never memory-accept.
- torn unACKed WAL tail after verified anchor: truncate only proven torn unACKed records.
- middle WAL corruption or corruption at/before anchor: fail closed; restore trusted evidence or exceptional abandonment with exact/wildcard gaps.
- commit succeeded/ACK lost: ordinary reconnect may adopt verifiable receiver head.
- same-incarnation receiver rollback, sender rollback, split history, identity/incarnation changes: operator reconciliation per Sections 19/22.
- duplicate sender/receiver ownership: fencing denies concurrent ownership.
- semantic poison event: rollback batch; threshold then SEMANTIC_RETRY_LIMIT; quarantine/validator fix as applicable.
- spool high-water/cap: stop client work before cap and fail new admissions at cap.

## 39. Heartbeats, drain, ChainProbe

Heartbeats and Goodbye are operational only. Their timestamps/state are not clock/completeness proof. ChainProbe is authenticated admin diagnostic traffic, count 1..256, rate-limited, and never mutates reconciliation state.

## 40. Miningcore accounting and candidate state

Every Miningcore accounting semantic rule is normative in `coredrp-miningcore-v1-semantics.md`: SINGLE vs PARENT+AUXILIARY, projection consistency, exact decimal grammar, ID/reward/PPS constraints, preserve-created, block/statistical flags, and post-parse limits.

Candidate IDs and state transitions, attempts/misses/last-attempt monotonicity, same-scope referential integrity, UUID/hash/script representation, and direct-candidate limits are also normative there.

## 41. Bitcoin evidence and network-policy binding

Receiver performs the full parser/Merkle/witness/duplicate-txid/BIP34/output classification defined by the Miningcore semantics registry.

Receiver-side Bitcoin validation policy is not free configuration once a scope contract is selected. `coredrp-v1-bitcoin-network-policies.md` defines a canonical `bitcoin_network_policy_digest` over network ID, network/genesis identity, BIP34 activation, direct-candidate validation version, and closed commitment-class allow-list. The Miningcore scope semantic contract carries this digest.

Two receivers using different network-validation policy MUST produce different Miningcore semantic digests and cannot silently interoperate under one epoch binding.

## 42. ADMIN canonical encoding and atomicity

ADMIN TLV v1 is `uint16_be(1)||uint16_be(field_count)||fields` with strictly increasing unique field IDs. Each field is `uint16_be(field_id)||uint32_be(value_len)||value`. Integer widths are exact. Malformed order/duplicates are rejected, never sorted into validity.

Every request includes 16-byte idempotency UUID and uint64 expected-state-version. `admin_digest = SHA256(ADMIN_DOMAIN || uint16_be(action_type) || uint32_be(body_len) || body)`.

ADMIN idempotency lookup, same-key/digest replay check, expected-state-version check, mutation, audit record, and stored result MUST occur in one durable serializable/locked state transition. Same key+same digest returns the original stored result without reapplying effects. Same key+different digest is `IDEMPOTENCY_KEY_CONFLICT`. State-version mismatch is `ADMIN_ACTION_CONFLICT`.

Temporal policy actions additionally enforce Section 32 retroactivity rules. Gap waiver follows Section 25 and cannot manufacture PayoutSafe.

## 43. Security boundary

mTLS/hash chains protect authenticated transport and consistent anchored history, not Byzantine truth. PayoutSafe assumes authenticated senders follow protocol except detectable faults. An attacker controlling all unkeyed history and anchors can recompute a chain; stronger threat models require independently protected signed/HMAC anchors or transparency storage. No 0-RTT application data.

## 44. Conformance and CI

CI validates canonical spec structure; incorporated registries; protobuf compilation/lint; layer direction; error/event/metric consistency; SHA-256 wire fingerprints; cryptographic, semantic-contract, epoch-binding, admission, ADMIN, profile, Bitcoin, reconnect, policy, clock, gap, idempotency, and WAL/state vectors; independent C# reconstruction; and a bounded TLA+ model with realistic unsafe mutations.

These are conformance/regression checks, not proof of the entire protocol.

## 45. Formal model

Model distinguishes WAL tail, sender ACK, receiver durable state, receiver-committed checkpoint evidence, epochs/retirement, atomic exceptional transition evidence, gap status, writer ownership, clock/membership proof gates, and payout/prune frontiers.

Payout frontier advances from receiver-committed checkpoint proof and policy gates without sender ACK dependency. ACK remains relevant to sender prune safety. Model mutations MUST include: prune without remembered ACK, ACK before receiver commit, normal epoch transition without drain, payout advance without receiver evidence/policy gates, and exceptional transition without atomically recorded gap evidence.

## 46. Evolution

Draft 0.6 still uses Core wire 1.1. Safety-significant new frame alternatives require a negotiated Core revision. Tags 10..15 remain available for compatible future Core-minor evolution; 16..31 remain reserved. Stable numbers are never reused.

Draft 0.6 endpoints do not advertise Core 1.0 compatibility. Profile compatibility is explicit in Section 10 and the compatibility registry.

## 47. Out of scope

CoreDRP does not standardize Byzantine consensus, independent-database active/active consensus, automatic retroactive payout compensation, global standards governance, or arbitrary network consensus rules outside versioned profile policy.

## 48. Miningcore reference requirements

Miningcore implementation uses dedicated CoreDRP ingest, PostgreSQL durability, sender/receiver fencing, bounded-generation permanent no-double-mint admission safety, temporal-membership enforcement, scope-contract ownership, explicit gap/waiver semantics, receiver replacement approval, canonical accounting order, network-policy-bound Bitcoin candidate validation, candidate referential integrity, and the normative metrics registry.

## 49. Required freeze corpus

Before stable release, corpus includes: lane/type/scope/sequence/hash/UUID boundaries; complete Core 1.1/Profile 1.1 compatibility cases; full Draft 0.6 epoch-binding preimage/digest; semantic-contract and network-policy digests; reconnect/receiver replacement; WAL/anchor failure ordering; bounded producer-generation idempotency and retired-generation rejection; event-time overflow; ClockStateUpdate malformed/stale/BAD-latch/reconnect-generation cases; temporal policy retroactivity; exact/reconciled/waived gap payout semantics; flow charge/zero windows; Mining/Miningcore semantic positives and negatives; Bitcoin odd/even Merkle, duplicate txid, SegWit/BIP34/network-policy negatives; ADMIN replay/conflict/retroactivity; and realistic formal mutations.

Crypto-only high-sequence vectors carry explicit synthetic previous-chain anchors and are never represented as reachable history.

## 50. Authorship

CoreDRP — Core Durable Relay Protocol was originally designed and authored by **Rob Cooke** in 2026 and originally developed for the Miningcore project.

Canonical project: `https://coredrp.org`  
Source: `https://github.com/NINJAK1DD/CoreDRP`

<!-- COREDRP-SPEC-END:50 -->
