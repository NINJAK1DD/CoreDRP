# CoreDRP/1 — Core Durable Relay Protocol

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

**Status:** Draft 0.4 hardening revision  
**Reference implementation target:** Miningcore  
**Normative language:** The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and **OPTIONAL** are interpreted as RFC 2119/RFC 8174 terms only when they appear in all capitals.

---

## 1. Status and conformance

CoreDRP/1 is specification-first and pre-implementation. Draft 0.4 incorporates six independent adversarial review passes across the public Draft 0.1 through Draft 0.3 repository states.

An implementation is conforming only when it satisfies Core plus every selected profile. Generated protobuf types are transport bindings, not a conformance definition.

The normative order of authority is:

1. this specification;
2. numbered error, event-type, ADMIN-action, metric and conformance registries;
3. `.proto` files;
4. reference tooling.

Reference code MUST NOT override the specification. If a test or implementation disagrees with this document, the implementation/test is defective until the normative text itself is intentionally revised.

Draft status means fields and rules may still change through explicit protocol review. No stable interoperability promise exists until CoreDRP/1 is declared stable.

## 2. Layering

CoreDRP Core is domain-independent. It owns authenticated identities, opaque scopes, numbered lanes, epochs, sequence ordering, event time, exact payload bytes, event identity, cryptographic chaining, sender durability, replay, cumulative ACKs, generic checkpoints, gaps, quarantine mechanics, flow control, clock evidence, reconnect, recovery, and administrative digest mechanics.

Mining Profile v1 owns mining-scope syntax, lane meaning, share semantics, temporal membership, temporal completeness-mode policy, PayoutFence/CriticalCheckpoint interpretation, `RequiredSender`, `PayoutSafe`, `PayoutSafeThrough`, `SafePruneThrough`, clock-policy parameters and deterministic mining accounting order.

Miningcore Integration Profile v1 owns PostgreSQL persistence, Miningcore accounting projections, scheme-specific payout/pruning integration, direct-coinbase evidence, operator-facing integration and `miningcore_coredrp_*` metrics.

Dependencies are one-way: Miningcore MAY depend on Mining; Mining MAY depend on Core. Reverse dependencies are forbidden and CI MUST enforce them.

## 3. Terms

**Sender:** process that durably admits events and initiates CoreDRP streams.

**Receiver:** process that verifies and durably commits events.

**Receiver ID:** stable logical receiver/recorder-cluster UUID authenticated by TLS and pinned by the sender.

**Receiver database incarnation:** UUID representing one durable database history. It is stable across ordinary process restart and changes when database history may have rolled back or been replaced.

**Lane:** independent ordered stream identified by an 8-bit number.

**Epoch:** UUID-scoped history of one sender/lane. Sequence numbering resets at an epoch boundary; safety/completeness temporal floors do not.

**Scope:** opaque Core bytes interpreted by selected profiles.

**Durable tail:** highest sender sequence whose complete WAL record is durably flushed.

**Committed sequence:** highest receiver sequence whose effects and stream state are durably committed.

**Remembered ACK:** receiver ACK durably persisted by the sender.

**Checkpoint:** chained Core event proving no later covered event may be introduced at or before its time boundary.

**Temporal floor:** durable cross-epoch lower bound for event time/checkpoint safety.

**Normal epoch transition:** transition in which every old-epoch durable event has been durably committed and ACKed before retirement.

**Exceptional epoch abandonment:** explicit operator action that retires an epoch with an unreplicated suffix while creating an auditable unresolved gap.

## 4. Fixed identifiers and domain separation

Protocol name: `CoreDRP/1`.

Protobuf packages:

- `coredrp.v1`
- `coredrp.mining.v1`
- `coredrp.miningcore.v1`

Permanent profile IDs:

- `PROFILE_ID_MINING = "coredrp.mining"`
- `PROFILE_ID_MININGCORE = "coredrp.miningcore"`

Profile IDs are ASCII, byte-exact, case-sensitive and independent from protobuf package names.

Sender certificate URI SAN:

`urn:coredrp:sender:<uuid>`

Receiver certificate URI SAN:

`urn:coredrp:receiver:<uuid>`

UUID textual form MUST be lower-case canonical form.

Fixed ASCII domain tags:

| Symbol | Exact bytes | Purpose |
|---|---|---|
| `PAYLOAD_DOMAIN` | `CoreDRP1-PAYLOAD` | payload digest |
| `EVENT_DOMAIN` | `CoreDRP1-EVENT` | event chain |
| `GENESIS_DOMAIN` | `CoreDRP1-GENESIS` | epoch genesis |
| `CONTRACT_DOMAIN` | `CoreDRP1-CONTRACT` | epoch binding |
| `ADMIN_DOMAIN` | `CoreDRP1-ADMIN` | privileged request digest |
| `ADMISSION_DOMAIN` | `CoreDRP1-ADMISSION` | local admission identity digest |

No NUL terminators are included. CoreDRP/1 MUST NOT reinterpret an assigned tag.

## 5. Primitive encodings and range validation

Cryptographic encodings use unsigned big-endian `uint8`, `uint16_be`, `uint32_be`, `uint64_be`; signed two's-complement `int64_be`; 32-byte SHA-256 digests; and 16-byte RFC 9562 UUID network order.

Core sequence values are `1..2^63-1`; sequence zero denotes genesis only.

Before any value enters a cryptographic preimage, implementations MUST validate its semantic range. In particular:

- lane `0..255`;
- event type `0..65535`;
- sequence `1..2^63-1`;
- scope length `0..65535`;
- payload length fitting `uint32` plus all negotiated/profile limits;
- Core/profile major/minor `0..2^32-1`;
- all advertised event types before sorting/de-duplication.

Implementations MUST NOT narrow, truncate, wrap or language-cast wider unvalidated integers before hashing.

## 6. Lane, event and error placement registries

Core lane IDs are `0..255`. Core assigns no application meaning.

Mining Profile v1 fixes lane 0 = SHARE and lane 1 = CRITICAL.

Event-type allocations:

- `0x0001`: Core CompletenessCheckpoint
- `0x0100`: MiningShareEvent
- `0x0200`: MiningcoreAccountingShareEvent
- `0x0201`: BitcoinDirectCoinbaseCandidate
- `0x0202`: CandidateStateUpdate
- `0xF000..0xFFFE`: private/test use
- `0xFFFF`: conformance boundary only

Unknown or unadvertised event types are fatal. Values above `0xFFFF` are `EVENT_TYPE_OUT_OF_RANGE` before hashing.

A known event type used on a forbidden lane or scope form is `INVALID_EVENT_PLACEMENT`, not `SEMANTIC_PAYLOAD_INVALID`. Placement errors are never quarantinable.

## 7. Hard resource limits

Before negotiated limits exist, CoreDRP/1 enforces:

- gRPC message <= 20 MiB;
- Hello <= 256 KiB;
- implementation string <= 128 UTF-8 bytes;
- profile ID <= 64 ASCII bytes;
- profile entries <= 32;
- scope-contract entries <= 1024;
- advertised event types <= 1024;
- scope <= 65535 bytes;
- event payload <= 16 MiB;
- batch events <= 4096;
- batch payload charge <= 16 MiB;
- ChainProbe count `1..256`;
- chain-probe hashes exactly 32 bytes.

A peer MUST reject a limit violation without allocating proportionally unbounded memory.

`RESOURCE_LIMIT_EXCEEDED` is used only for aggregate conditions that can become valid by splitting/retrying. Intrinsic single-object violations use `ATOMIC_RESOURCE_LIMIT_EXCEEDED`, `EVENT_TOO_LARGE`, or another permanent specific code.

The effective limit is the minimum of Core hard, negotiated and profile limits.

## 8. Authentication and stable peer identity

TLS 1.3 with mutual TLS is REQUIRED.

The receiver extracts exactly one sender URI SAN and requires `ClientHello.sender_id` to equal its 16 UUID octets. Zero/multiple CoreDRP sender SANs or mismatch is `UNAUTHORIZED_SENDER`.

The sender extracts exactly one receiver URI SAN and requires `ServerHello.receiver_id` to equal it. Zero/multiple CoreDRP receiver SANs is `INVALID_HANDSHAKE`; unexpected logical receiver-ID change is `RECEIVER_ID_CHANGED`.

Receiver ID is a stable logical cluster identity and MUST NOT change during ordinary restart, rolling deployment, primary failover or database-incarnation rotation. A planned receiver-ID replacement requires explicit operator reconciliation and MUST retain the previous remembered ACK/rollback anchor; changing receiver ID MUST NEVER erase evidence of rollback.

Receiver database incarnation is separate from receiver ID. It changes whenever restored/promoted state may lack an ACKed transaction.

Transport authorization and Mining temporal membership are separate. Revoking transport access MUST NOT rewrite historical completeness membership.

## 9. Handshake validity

First client frame is exactly one `ClientHello`; first server frame is exactly one `ServerHello` or `ProtocolError`. Empty oneofs, second hellos or wrong-direction first frames are `MALFORMED_FRAME`.

Core major mismatch is `PROTOCOL_VERSION_MISMATCH`. For major 1, each minor field advertises the maximum compatible minor and the negotiated minor is the highest common value.

Handshake validity requires fixed-length UUID/hash fields, lane/sequence ranges, internally consistent retained/tail positions, ACK sequence/hash presence pairing, unique event types, unique profile ID/major lines, and unique version-qualified scope-contract entries.

Scope contract uniqueness key is:

`(scope, profile_id, profile_major, profile_minor)`.

A selected scope contract MUST match the selected profile major/minor exactly.

`remembered_contract_binding_digest` is absent only for a freshly approved epoch that has not yet established a binding; after bootstrap it MUST be present, 32 bytes and equal to the sender durable anchor.

## 10. Deterministic profile negotiation

`profile_major` is an exact major. `profile_minor` advertises the highest compatible minor within that major.

For each profile ID the receiver:

1. discards lines whose `minimum_core_*` exceeds negotiated Core version;
2. finds an exact major supported by both peers;
3. selects the highest mutually supported minor;
4. selects at most one version for the profile ID;
5. selects only event types defined by that exact profile version and advertised by both peers;
6. selects only `ScopeContractSupport` entries whose `profile_id/major/minor` exactly equal that selected version.

Mining Profile v1 and Miningcore Profile v1 use **scope-owned semantic digests**. Their `ProfileSupport.semantic_contract_digest` and `ProfileSelection.semantic_contract_digest` MUST therefore be absent. They MUST NOT copy an arbitrary scope digest into the profile-global field.

Profiles that genuinely define global, scope-independent semantics MAY define a profile-global digest in a future compatible revision.

## 11. Epoch contract binding

Before admitting the first event of any epoch, the sender MUST possess durable epoch approval and MUST complete a successful bootstrap handshake that establishes the epoch contract binding.

After the binding is durable, receiver/network outages MUST NOT prevent local admission of event types already permitted by the binding.

Binding digest:

`SHA256(CONTRACT_DOMAIN || uint32_be(core_major) || uint32_be(core_minor) || uint8(lane) || profile_set || scope_contract_set || event_type_set)`

`profile_set` is sorted by profile ID, major, minor. Entry:

`uint16_be(id_len) || id || uint32_be(major) || uint32_be(minor) || uint8(has_digest) || [digest]`.

For Mining/Miningcore v1, `has_digest=0` because their semantics are scope-owned.

`scope_contract_set` is sorted by scope bytes, profile ID, major, minor. Entry:

`uint16_be(scope_len) || scope || uint16_be(profile_id_len) || profile_id || uint32_be(profile_major) || uint32_be(profile_minor) || 32-byte digest`.

`event_type_set` is ascending unique validated `uint16_be` values preceded by `uint16_be(count)`. Every set has a `uint16_be(count)`.

The binding is immutable for an epoch. Capability withdrawal, selected-version change, scope-contract digest change or selected event-set change produces `CONTRACT_BINDING_CHANGED` while the epoch remains active.

## 12. Mining and Miningcore semantic contracts

### Mining scope contract

Mining v1 canonical source bytes are:

`uint16_be(profile_id_len)||"coredrp.mining"||uint32_be(profile_major)||uint32_be(profile_minor)||uint16_be(scope_len)||scope||uint8(payout_scheme)||uint16_be(coin_id_len)||coin_id||uint16_be(network_id_len)||network_id||uint16_be(completeness_policy_version)||uint16_be(retention_policy_version)||uint8(cross_sender_ordering_policy)||uint32_be(permitted_clock_skew_ms)||uint32_be(max_clock_step_ms)||uint32_be(probe_interval_ms)||uint32_be(probe_processing_max_ms)||uint32_be(evidence_expiry_ms)||uint32_be(unknown_grace_ms)||uint64_be(admission_idempotency_horizon_ms)`.

The digest is SHA-256 of those exact bytes.

Payout schemes: `1=PPLNS`, `2=PPLNSBF`, `3=PROP`, `4=SOLO`, `5=PPS`, `6=DIRECT_SOLO`. Ordering policy 1 means Section 35.

**The current completeness mode is intentionally absent from the immutable semantic contract.** The contract binds the completeness-policy algorithm/version; the effective mode is temporal audited policy under Section 32. This resolves the contradiction between an immutable epoch binding and future-effective mode changes.

`coin_id`/`network_id` match `[a-z0-9._-]{1,64}`.

### Miningcore scope contract

Canonical source bytes:

`uint16_be(profile_id_len)||"coredrp.miningcore"||uint32_be(profile_major)||uint32_be(profile_minor)||uint16_be(scope_len)||scope||uint32_be(accounting_schema_version)||uint32_be(persistence_schema_version)||uint16_be(direct_candidate_validation_version)||uint16_be(settlement_policy_version)`.

Digest is SHA-256.

## 13. Event identity and cryptographic chain

Every Event carries sequence, event type, scope, event time, exact payload bytes and 16-byte immutable relay event UUID. Mining requires UUIDv7.

`payload_hash = SHA256(PAYLOAD_DOMAIN || uint32_be(len(P)) || P)`

`chain[0] = SHA256(GENESIS_DOMAIN || sender_uuid || epoch_uuid || uint8(lane))`

`chain[N] = SHA256(EVENT_DOMAIN || chain[N-1] || sender_uuid || epoch_uuid || uint8(lane) || uint64_be(sequence) || uint16_be(event_type) || relay_event_uuid || uint16_be(scope_len) || scope || int64_be(event_time) || payload_hash)`

Sender hashes exact WAL payload bytes; receiver hashes exact received bytes. Parsed/re-serialized protobuf bytes never replace the original cryptographic evidence.

## 14. Batch validity and event placement

EventBatch contains `1..max_batch_events` contiguous events beginning exactly at `first_sequence`, must not overflow `2^63-1`, and carries a 32-byte terminal chain hash matching the final event.

Mining placement matrix:

| Type | Lane | Scope |
|---|---:|---|
| CompletenessCheckpoint | 0 or 1 | empty |
| MiningShareEvent | 0 | non-empty Mining scope |
| MiningcoreAccountingShareEvent | 0 | non-empty Mining scope |
| BitcoinDirectCoinbaseCandidate | 1 | non-empty Mining scope |
| CandidateStateUpdate | 1 | non-empty Mining scope |

Wrong lane/scope form is `INVALID_EVENT_PLACEMENT`, non-quarantinable.

`MiningShareEvent` non-candidate events MUST omit candidate-only fields. Candidate events MUST carry non-empty candidate hash. Other candidate-field requirements are coin/profile specific.

The receiver verifies entire batch structure/ranges/authorization/placement/chain before durable effects. Normal batch effects are all-or-nothing. Profile payload failure rolls back the batch and returns `SEMANTIC_PAYLOAD_INVALID` for the failing sequence.

## 15. Sender durable admission and idempotency

Acceptance order:

`validate request → resolve admission key → allocate sequence/time/relay ID if new → serialize exact payload → append WAL + idempotency mapping → durable flush → application success`.

A retry-capable caller supplies stable `caller_admission_key`. Before sequence/time/relay-ID allocation, sender computes:

`admission_digest = SHA256(ADMISSION_DOMAIN || uint16_be(event_type) || uint16_be(scope_len) || scope || uint32_be(payload_len) || exact_payload || uint32_be(profile_metadata_len) || profile_metadata)`.

`profile_metadata` is empty unless the selected profile explicitly defines immutable caller-provided metadata that is not already in payload/scope. Generated sequence, event time and relay UUID MUST NOT appear in the digest.

The durable mapping is:

`caller_admission_key -> admission_digest -> relay_event_id -> (lane,epoch,sequence)`.

Same key/digest within the contract-bound idempotency horizon returns the original admission. Same key with different digest is `IDEMPOTENCY_KEY_CONFLICT` and fails closed.

The Mining contract binds `admission_idempotency_horizon_ms`. Sender MUST retain a compact key/digest tombstone for at least that horizon after original durable admission, even if WAL/effect rows are pruned. Callers MUST NOT retry the key after the horizon. The Core invariant therefore applies for the defined retry horizon, not indefinitely.

WAL records have independent length + CRC32C/equivalent physical-integrity framing. UnACKed events are never evicted.

## 16. Sender durable anchor and pruning

Per-lane durable state includes sender/lane, active epoch, last durable sequence/hash, last event time, temporal/checkpoint floors, oldest retained sequence, receiver ID/database incarnation, remembered ACK sequence/hash, contract binding, retired epoch tombstones and idempotency tombstones still within their required horizon.

Anchor may lag WAL but MUST NEVER lead it. Replacement uses temp write, file flush, atomic rename/replace and directory metadata flush where required.

Recovery validates the anchor against WAL then scans forward.

Pruning order:

`validate ACK → durably persist ACK/receiver anchor → only then prune ACKed WAL`.

Never prune evidence required by unresolved gap/quarantine/epoch/settlement state or still-active idempotency horizons.

## 17. Flow control and WindowUpdate

Logical `payload_charge(batch) = Σ len(Event.payload)`.

`window_events` counts transmitted events not cumulatively ACKed; `window_bytes` counts their payload charge. Metadata/scope/protobuf/HTTP framing do not contribute to these logical counters but remain bounded by message caps.

Negotiated `ServerHello.window_events/window_bytes` define maxima. `WindowUpdate` MAY only reduce or restore current windows within those negotiated maxima. Values larger than negotiated maxima are `MALFORMED_FRAME`.

A `WindowUpdate` value of zero is legal and means pause that dimension; it MUST NOT close the stream. Heartbeats and clock probes remain allowed while event flow is paused.

Pressure policy is backpressure, then stop new clients/miners before accepted work is endangered, then fail closed when durable admission cannot continue.

## 18. Single-writer fencing

Sender holds exclusive fence over `(sender_id,lane_id)` for every durable admission and epoch transition. Epoch is state protected beneath that fence; different-epoch processes cannot simultaneously admit.

Receiver permits at most one active stream per `(sender_id,lane_id)`. Second stream gets `STREAM_ALREADY_ACTIVE`.

PostgreSQL implementations hold a stream-lifetime advisory/lease lock and serialize commits through durable row lock/CAS state.

## 19. Reconnect reconciliation precedence

Let `C` receiver committed sequence, `R` sender remembered ACK (0 if none), `T` sender durable tail and `E` sender earliest retained sequence. Let `same_receiver_id`, `same_incarnation`, `approved_epoch`, and common-sequence hash verification be independently known.

Conditions overlap, so implementations MUST evaluate in this exact order:

1. receiver ID differs from pinned logical receiver → `RECEIVER_ID_CHANGED`;
2. database incarnation differs → `RECEIVER_INCARNATION_CHANGED`;
3. epoch is not the currently approved epoch → `EPOCH_NOT_APPROVED`;
4. `C > T` → `SENDER_ROLLBACK`;
5. `C < R` on the same receiver identity/incarnation → `RECEIVER_ROLLBACK`;
6. any common sequence that must match has different hash → `SPLIT_LOG`;
7. receiver needs sequence `C+1 < E` → `RECOVERY_GAP`;
8. `C > R` and receiver chain at `C` is verifiable from retained/durable sender evidence → `ADOPT_ACK` (durably remember C/hash, then continue);
9. `C > R` but sender cannot verify receiver hash → `SPLIT_LOG`;
10. `C == R` with matching chain state → `RESUME` from `C+1`.

At bootstrap (`C=R=0`) there is no remembered ACK hash. Receiver's `committed_chain_hash` MUST equal locally computed `chain[0]` genesis for the approved epoch; otherwise `SPLIT_LOG`.

No best-effort longest-history selection exists.

## 20. ACK semantics

ACK means profile effects, required evidence, committed sequence/hash and relevant checkpoint state durably committed.

ACK is cumulative and monotonic. Equal duplicate ACK is valid. Lower ACK on same receiver identity/incarnation is rollback evidence.

ACK cannot exceed sender durable tail and its hash must match sender evidence at that sequence.

`committed_at_unix_ms` is operational metadata only and MUST NOT contribute to event time, clock, payout or completeness proof.

## 21. Receiver transaction semantics

After complete batch verification, one durable transaction:

1. enables/verifies required durability;
2. locks stream state;
3. validates receiver identity/incarnation, epoch, expected sequence/hash and temporal floors;
4. validates event placement and profile semantics;
5. writes exact evidence/application effects;
6. writes explicitly authorized quarantine/gap records;
7. advances committed sequence/hash;
8. updates checkpoint/completeness state;
9. commits.

Any failure rolls back and sends no ACK.

Miningcore ordinary CoreDRP ingest MUST NOT use the legacy receiver recovery-journal fallback.

## 22. Initial epochs, normal transitions and exceptional abandonment

### Initial epoch

First-ever epoch for `(sender_id,lane_id)` requires durable `INITIAL_EPOCH_APPROVAL` before bootstrap handshake. Approval binds sender UUID, lane, initial epoch UUID, computed genesis hash, initial temporal/checkpoint floor, operator/authority, reason and timestamp. The contract-binding digest is attached after successful bootstrap negotiation and becomes immutable for that epoch.

### Normal epoch transition

Normal retirement is allowed only when all old durable history is replicated:

`receiver_committed == sender_remembered_ACK == sender_durable_tail == transition.final_sequence`

and final hashes agree.

Transition records old epoch/final sequence/hash/last event/checkpoint/floor → new epoch/genesis plus operator/reason/time. The lane writer fence is retained through transition.

### Exceptional epoch abandonment

If the old epoch cannot drain, normal transition is forbidden. An operator MAY use explicit `EXCEPTIONAL_EPOCH_ABANDON` only after durably recording the abandoned suffix `(old_epoch, first_missing_sequence..old_durable_tail, neighbouring time bounds, final known chain evidence)` as an unresolved completeness/recovery gap. That gap retains normal payout/pruning consequences until reconciled or waived. Accepted-but-unreplicated events MUST NEVER disappear merely because an epoch is retired.

New temporal floor is `max(old_last_event_time, old_last_trusted_checkpoint, inherited_floor)`. Covered new events are strictly greater than inherited checkpoint floor.

Retired epoch UUIDs are permanent tombstones. At `2^63-1`, drain/transition is mandatory; no wrapping.

## 23. Error model

`docs/coredrp-v1-errors.md` is the normative code/disposition registry. Wire disposition is redundant and mismatch is `MALFORMED_FRAME`.

`EVENT_QUARANTINABLE` is reserved for correctly placed, Core-valid events whose profile payload semantics are invalid. Structural, placement, authorization, rollback, epoch, hash and checkpoint-proof failures are never quarantinable.

## 24. Quarantine progression

Rejected event bytes are immutable.

1. batch containing invalid payload rolls back;
2. sender retains exact WAL bytes;
3. operator approves quarantine for exact sender/lane/epoch/sequence/type/relay-ID/chain hash + expected state version;
4. sender retransmits identical event bytes;
5. receiver re-verifies history/identity and atomically writes quarantine evidence plus watermark;
6. ACK may then advance.

Changing the event is never a repair. Validator/config correction may allow the same bytes to validate normally.

Quarantine evidence retains exact payload/event bytes, hashes, validator/profile version, scope contract digest, reason, operator, time and idempotency audit.

## 25. Gap semantics

Core gap records include scope/lane/epoch, sequence range, conservative neighbouring time bounds, classification, state and immutable audit provenance.

Missing sequence timestamps are not interpolated. Unknown coverage remains open-ended from the last trusted boundary until later proof closes it.

Resolution is `RESOLVED_RECONCILED` or `RESOLVED_WAIVED`. Waiver records accepted uncertainty; it never rewrites history as complete.

Exceptional epoch abandonment MUST create a gap before the old epoch can be retired.

## 26. Completeness checkpoints

Core event `0x0001` is CompletenessCheckpoint. Mining uses lane-global checkpoints with empty Event.scope.

Covered scopes derive from the persisted epoch scope-contract set plus temporal membership/mode state effective at the checkpoint boundary, never from mutable current transport authorization.

Checkpoint payload `complete_through_unix_ms` equals enclosing event time exactly.

Lane 0 = PayoutFence; lane 1 = CriticalCheckpoint.

Idle periodic checkpoints are required.

## 27. Anti-backdating

After checkpoint `T`, every later covered event in that epoch or any approved successor epoch MUST have `event_time_unix_ms > T`.

Sender enforces before durable admission; receiver independently verifies against durable inherited checkpoint floor.

Violation is `CHECKPOINT_BACKDATED_EVENT`, non-quarantinable.

## 28. Event-time assignment

Single-consumer lane sequencer assigns event time. Within epoch event times do not decrease; successor epochs inherit Section 22 floors.

Clock jitter may be clamped monotonically only within effective `maxClockStep`. Larger forward/backward wall-clock step makes local clock BAD.

Mining share Created equals Core event time and receiver does not rewrite it.

## 29. Clock probe mathematics and deterministic sample selection

For receiver send `t1`, sender receive `t2`, sender send `t3`, receiver receive `t4`, reject `t3<t2` or negative/non-sensical elapsed durations.

Conservative sender-minus-receiver offset interval:

`L = t3 - t4`

`U = t2 - t1`

Round-trip network uncertainty score:

`rtt = (t4 - t1) - (t3 - t2)`.

Only fresh authenticated probes whose processing duration is within policy are candidates. The active clock observation is the fresh candidate with minimum non-negative `rtt`; ties choose the latest `t4`. Implementations MUST NOT intersect offset intervals sampled at different times because the physical offset may have changed.

For permitted skew `S`:

- GOOD iff `L >= -S` and `U <= +S`;
- BAD iff `U < -S` or `L > +S`;
- UNKNOWN otherwise (interval overlaps the allowed boundary or no fresh usable sample exists).

Midpoint/symmetric-delay estimates MUST NOT drive financial safety.

## 30. Clock policy aggregation, grace and recovery

One sender/lane may carry multiple scopes. Lane admission/checkpoint safety uses the strictest effective policy among all active covered scope contracts:

- permitted skew = minimum;
- `maxClockStep` = minimum;
- probe processing maximum = minimum;
- evidence expiry = minimum;
- UNKNOWN grace = minimum;
- probe interval = minimum (probe at least as frequently as every active scope requires).

Local BAD or remote BAD stops covered admission/checkpoint advancement. Remote UNKNOWN + local GOOD during grace MAY continue admission but MUST NOT advance trusted checkpoints. Grace expiry stops admission. GOOD+GOOD is normal.

Recovery from BAD requires trusted UTC reaching/passing durable last event time plus at least three fresh GOOD probes spanning at least one effective probe interval.

Default Mining parameters: skew 2000 ms; max step 250 ms; probe interval 5s; processing max 250ms; evidence expiry 15s; UNKNOWN grace 120s. Looser scope values change that scope's immutable semantic digest.

## 31. Mining scope and share semantics

Mining scope is exact ASCII `[A-Za-z0-9._-]{1,64}`, case-sensitive, no normalization.

Difficulty values are finite; NaN/infinities/negative zero invalid. Accepted-work `difficulty`, `actual_difficulty` and `network_difficulty` are strictly positive. `achieved_share_difficulty` may be zero only for explicitly informational cases.

Mining share Created equals Core event time. Candidate field combinations obey Section 14.

## 32. Temporal membership and completeness mode

Membership and completeness mode are independent **temporal policy state**, not immutable scope-contract values.

Membership intervals and completeness-mode intervals are half-open `[valid_from,valid_until)`, append-only/audited, with no overlap or ambiguity for the same subject/scope.

Completeness modes: `RELAY_REQUIRED` and `NO_RELAY_REQUIRED`. Missing/unknown mode fails closed.

`RequiredSender(Q,T)` is a sender whose durable membership contains T when the durable mode schedule for Q at T is `RELAY_REQUIRED`.

Empty membership is payout-safe only when an explicit durable `NO_RELAY_REQUIRED` interval covers T. Missing membership/mode configuration never creates vacuous safety.

Membership start/end and mode changes are privileged. Normal changes are future-effective beyond current safety frontier plus clock uncertainty. Retroactive changes require reconciliation/waiver and MUST NOT silently invalidate an already-proven frontier.

Ending a required sender without completeness through deactivation boundary creates unresolved gap unless waived.

## 33. PayoutSafe

`PayoutSafe(Q,T)` requires:

1. durable known completeness mode at T;
2. if RELAY_REQUIRED, every `RequiredSender(Q,T)` has trusted lane-0 checkpoint evidence through required skew-adjusted boundary;
3. each checkpoint used satisfied clock policy;
4. no unresolved relevant recovery/completeness gap;
5. no unresolved payout-significant quarantine;
6. membership/mode/semantic-contract state relied on was durable before use;
7. anti-backdating and epoch-floor invariants prevent later covered history at/before T.

`PayoutSafeThrough(Q)` is greatest durably proven T and is monotonic.

With symmetric maximum skew S, peer completeness for block timestamp B requires at least `B+2S` unless a tighter interval proof is demonstrably more conservative.

PPS/SOLO are not fence-gated; direct submission is never remote-gated.

## 34. SafePruneThrough

`SafePruneThrough(Q)` is greatest boundary through which destructible evidence may be removed without invalidating required proofs. For payout evidence it never exceeds `PayoutSafeThrough(Q)` and is monotonic.

Never prune epoch approvals/tombstones, temporal floors, chain/ACK/receiver anchors, membership/mode history, gap/quarantine/waiver/override audits or still-required settlement evidence.

Safety discovery after pruning is an incident, not permission to silently move frontiers backward.

## 35. Scheme behavior and canonical cross-sender order

Miningcore integration:

- PPLNS/PPLNSBF settlement requires PayoutSafe; prune through `min(scheme cutoff, SafePruneThrough)`;
- PROP likewise with round cutoff;
- custodial SOLO payout not fence-gated; winning-share deletion only through `min(block.Created, SafePruneThrough)`;
- PPS accounting not fence-gated and follows its retention contract;
- direct-coinbase SOLO never waits for receiver/fence.

Canonical cross-sender accounting order:

1. event time;
2. sender UUID bytes;
3. sequence;
4. relay event UUID bytes.

This is a deterministic **accounting order**, not proof of physical cross-sender arrival causality. Clocks may differ within permitted bounds. Database insertion order MUST NOT break ties.

## 36. Direct candidate independence

Submitting edge persists exact candidate/settlement evidence locally before `submitblock`. Recorder, critical-lane or completeness-fence failure never delays local submission.

Critical lane is durable evidence replication, not consensus-submission latency.

## 37. PostgreSQL durability

Transactions advancing CoreDRP committed state require PostgreSQL `fsync=on`, `SET LOCAL synchronous_commit=on` or stronger, no unlogged durable CoreDRP state, and atomic stream/effect commit.

Standby promotion that may omit ACKed transactions creates a new database incarnation before serving CoreDRP and invokes Section 19 reconciliation.

## 38. Failure semantics

PostgreSQL unavailable: no ACK, backpressure, sender spools, retryable durability error.

Sender disk/fsync failure: stop durable admission.

Middle WAL corruption: fail closed; never skip/create epoch automatically.

Commit/ACK loss: normal Section 19 path.

Duplicate sender/receiver: fencing prevents concurrent ownership.

Split history: operator intervention.

Partial batch: rollback all current batch effects.

Epoch cannot be used to discard accepted-but-unreplicated work; Section 22 drain/gap rule applies.

## 39. Heartbeats, drain and ChainProbe

Heartbeats are direction-specific operational traffic and never clock/completeness proof.

Goodbye is advisory; durable stream state is authoritative.

ChainProbe is authenticated, local-admin-triggered, rate-limited diagnostic traffic only. Count `1..256`; results never mutate stream state.

## 40. Monetary and Miningcore accounting projection semantics

Financial coin-unit decimals use `Decimal38Scale24.canonical`: `0` or `[1-9][0-9]{0,13}` optionally followed by `.` plus 1..24 digits whose last digit is nonzero. No sign/exponent/whitespace/leading zero/trailing fractional zero/NaN/infinity. Values < 100000000000000 and <=38 total digits. Positive-only fields reject zero. Monetary values MUST NOT use `double`.

For `MiningcoreAccountingShareEvent`:

- `primary` is REQUIRED;
- primary role MUST be SINGLE or PARENT; UNSPECIFIED/AUXILIARY primary is invalid;
- SINGLE requires `paired` absent;
- PARENT requires `paired` present and paired role AUXILIARY;
- paired projection MUST have same miner, worker, session ID and `created_unix_ms` as primary; chain-specific height/difficulty/candidate fields MAY differ;
- accounting IDs, when present, MUST be non-empty and primary/paired IDs MUST differ;
- `reward_basis_satoshis`, when present, MUST be >=0;
- `pps_calculated_amount`, when present, MUST parse canonically and requires non-empty `accounting_id`;
- `preserve_created` MUST be true for every CoreDRP projection;
- `block_only=true` requires `block_record_emitted=true` and `statistical_record_emitted=false`;
- `statistical_record_emitted=true` implies `block_only=false`.

Violations are `SEMANTIC_PAYLOAD_INVALID` and are quarantinable only because placement/history remain valid.

Post-parse limits: miner 256 UTF-8 bytes, worker 128, user agent 256, source IP 64, source 64, session 128, candidate kind 64, confirmation data 4096, direct recipients <=256, address metadata <=128, scriptPubKey <=10000.

## 41. Bitcoin evidence consistency, Merkle commitment and candidate state

Bitcoin hashes are transmitted as 32 bytes in canonical RPC/display order. `serialized_block` is exact consensus serialization. Script bytes are authoritative; address strings are audit/display metadata that must map to the exact script on configured network.

Receiver MUST use a consensus-compatible Bitcoin parser/library or equivalent verified implementation and before durable acceptance MUST:

1. parse entire block with no malformed/trailing bytes;
2. compute `SHA256d(header80)`, display-order it, require `block_hash`;
3. parse all transactions, require tx0 coinbase;
4. compute non-witness txid of coinbase and require `coinbase_txid`;
5. compute txid Merkle root of **all** transactions using Bitcoin duplicate-last pairing and require exact header merkle root;
6. when witness serialization/commitment rules apply, compute witness Merkle root with coinbase wtxid treated as zero, extract the 32-byte coinbase witness reserved value, locate the BIP141 witness-commitment output (`OP_RETURN 0x24 aa21a9ed <32>`; highest matching output index is authoritative) and require `SHA256d(witness_root || reserved_value)` equality;
7. verify BIP34 height commitment where mandatory;
8. verify miner output script/value;
9. verify declared DirectRecipient multiset exactly matches designated direct-pay outputs;
10. permit separately identified zero-value consensus commitment outputs (including BIP141 witness commitment) outside the miner/direct-recipient set while still counting every coinbase output in gross reward;
11. require gross reward equals sum of all coinbase outputs and reject negative/overflow/contradictory classification.

Chain proves immutability, not correctness; these checks bind header, transaction body, witness data and payout evidence together.

Bitcoin serialized-block profile cap is 4,000,000 bytes. Candidate ID is UUIDv7. Initial candidate state PREPARED.

Allowed transitions: PREPARED → SUBMITTED_UNCERTAIN/OBSERVED_ACTIVE/REJECTED/QUARANTINED; SUBMITTED_UNCERTAIN → itself/OBSERVED_ACTIVE/REJECTED/QUARANTINED; REJECTED → OBSERVED_ACTIVE only on later authoritative chain proof, otherwise terminal except quarantine; OBSERVED_ACTIVE → QUARANTINED only for evidence investigation; QUARANTINED terminal except explicit audited reconciliation outside this graph.

Attempts never decrease; definitive misses <= attempts; last-attempt absent iff attempts zero.

## 42. Privileged actions and canonical ADMIN encoding

Assigned action IDs:

- `0x0001` quarantine-and-advance
- `0x0002` gap reconciliation
- `0x0003` gap waiver
- `0x0004` normal epoch-transition approval
- `0x0005` initial epoch approval
- `0x0006` exceptional epoch abandon-and-transition
- `0x0101` membership start
- `0x0102` membership end
- `0x0103` completeness-mode change
- `0x0104` settle-without-fence override
- `0x0201` Miningcore capability activation

ADMIN body TLV v1:

`uint16_be(1)||uint16_be(field_count)||fields sorted by strictly increasing field_id`.

Field: `uint16_be(field_id)||uint32_be(value_len)||value_bytes`. No duplicate IDs. UUIDs use RFC bytes; integers fixed-width big-endian; strings/scopes exact validated bytes; absent optional fields omitted. JSON is never canonical digest input.

Every request includes `1=idempotency_uuid(16)` and `2=expected_state_version(uint64)`.

Normal epoch transition includes sender, lane, old epoch, final sequence/hash, new epoch, inherited temporal/checkpoint floors and reason. Receiver committed sequence/hash and sender durable tail/remembered ACK MUST be checked against the normal-drain condition in the same protected state transition.

Initial epoch approval includes sender, lane, new epoch, genesis hash, initial temporal/checkpoint floor and reason; it has no old epoch/final sequence.

Exceptional abandonment includes sender/lane/old epoch, last receiver committed/ACKed sequence/hash, old durable tail, abandoned first/last sequence, conservative time bounds, new epoch/floors and reason; transaction MUST create the unresolved gap atomically with retirement approval.

Membership/mode actions include scope, effective time and reason; membership additionally includes sender UUID.

`admin_digest = SHA256(ADMIN_DOMAIN || uint16_be(action_type) || uint32_be(len(B)) || B)`.

Same idempotency key + same digest returns original result; same key + different digest is conflict. State-version mismatch is `ADMIN_ACTION_CONFLICT`.

## 43. Security boundary

mTLS authenticates peers and transport. Explicit authorization controls sender/lane/scope.

The SHA-256 chain detects corruption, replay and divergent history when trusted anchors survive. It is not Byzantine consensus and does not make a compromised authenticated sender truthful. An attacker controlling all history/anchors can recompute an unkeyed chain.

Applications needing stronger storage-compromise resistance SHOULD use independently protected signed/HMAC anchors or external transparency storage.

No 0-RTT application data.

## 44. Specification, compatibility and CI integrity

CI MUST verify:

- UTF-8/control-byte integrity, exact sections 1..50, minimum size and terminal sentinel;
- protobuf compilation/lint, syntax/package identities, complete messages/fields/oneofs/enums/services/RPC/reserved baseline;
- Core←Mining←Miningcore boundaries with negative self-tests;
- error/event/metric registry consistency;
- cryptographic, semantic-contract and ADMIN vectors;
- positive and **executed** negative profile validators;
- reconnect precedence including overlapping conditions, bootstrap and unapproved epoch;
- WAL/idempotency, normal/exceptional epoch transition, writer fencing, membership/mode and clock-state vectors;
- legacy and SegWit Bitcoin evidence vectors, txid Merkle validation and BIP141 witness commitment;
- independent C# cryptographic/contract verification;
- a TLA+ fault model with separate fault/detection transitions plus at least one deliberate unsafe mutation proven detectable.

Deleted protobuf fields reserve number and SHOULD reserve name.

The compatibility checker MUST reject protobuf syntax/edition changes and unexpected services in any protocol/profile file, not only the Core file.

## 45. Normative safety invariants

Machine-testable invariants include:

`ACK <= receiver durable <= sender durable tail`

`prune <= durably remembered ACK`

`same sender/lane/epoch/sequence => identical chain hash`

`at most one sender writer(sender,lane)`

`retired epoch never current`

`normal epoch transition => old receiver committed == old remembered ACK == old durable tail == final sequence`

`exceptional epoch transition with abandoned suffix => unresolved gap exists before retirement`

`new temporal floor >= max(old event time, old trusted checkpoint, old floor)`

`checkpoint(T) => every later covered event time > T`

`unknown membership/mode => NOT PayoutSafe`

`unresolved relevant gap/quarantine => NOT PayoutSafe`

`PayoutSafeThrough monotonic`

`SafePruneThrough <= PayoutSafeThrough` and monotonic

`same caller admission key + same admission digest within idempotency horizon => same relay event ID/admission`

`unexpected receiver ID/incarnation/rollback cannot clear remembered ACK evidence`

## 46. Evolution

CoreDRP/1 evolves through negotiated Core minors, profile versions, event types and version-qualified scope contracts.

Sender never emits a type absent from persisted epoch binding. Unknown/unadvertised types remain fatal even if protobuf preserves unknown fields.

Safety-significant top-level frame alternatives require explicit negotiated minor support.

After stable release, event/admin/error/enum numbers and protobuf field numbers are never reused. Package and syntax declarations are compatibility-critical.

## 47. Out of scope

CoreDRP/1 does not standardize independent-database active/active receiver consensus, automatic retroactive payout compensation, historical statistics rebuilding, remote-durable Stratum admission, Byzantine consensus against malicious authenticated peers/storage, or global standards governance.

## 48. Miningcore reference requirements

Miningcore MUST preserve sender event time; use dedicated CoreDRP ingest; enforce PostgreSQL durability and sender/receiver fencing; persist sender UUID mapping without reuse; use durable caller admission idempotency for retry-capable financial admissions; uniquely identify receiver share effects using relay event identity; use Section 35 canonical accounting order; expose the metric registry; persist direct candidate evidence before submitblock; and perform Section 41 full structural/Merkle/witness consistency checks centrally.

A Miningcore implementation MUST implement the Section 40 accounting validity matrix before applying financial projection effects.

## 49. Conformance corpus requirements

Before stable CoreDRP/1, repository tests MUST contain and execute:

- lanes 0/1/255, boundary event type, max/empty scope/payload and max/zero sequences;
- UUID network-order trap and exact preimages;
- version-qualified scope-contract bindings and profile-global-digest absence for Mining/Miningcore;
- canonical ADMIN vectors including initial/normal/exceptional epoch actions;
- reconnect precedence overlap cases, bootstrap genesis, receiver-ID/incarnation, unapproved epoch, unverifiable higher receiver ACK;
- normal drain and exceptional abandonment gap cases;
- admission digest + retention-horizon cases;
- clock GOOD/BAD/UNKNOWN classification and multi-scope strictest-policy aggregation;
- invalid placement separate from invalid payload;
- Miningcore accounting SINGLE/PARENT+AUX valid and invalid matrices;
- Bitcoin legacy and SegWit candidate vectors with all-transaction Merkle root and BIP141 witness commitment;
- WAL crash ordering, quarantine positions, membership/mode fail-closed behavior and deterministic cross-sender ties;
- formal-model unsafe mutation controls.

Crypto-only high-sequence vectors MUST carry explicit synthetic previous-chain anchors and MUST NOT be described as reachable history.

## 50. Authorship

CoreDRP — Core Durable Relay Protocol was originally designed and authored by **Rob Cooke** in 2026 and originally developed for the Miningcore project.

Canonical project: `https://coredrp.org`  
Source repository: `https://github.com/NINJAK1DD/CoreDRP`

<!-- COREDRP-SPEC-END:50 -->
