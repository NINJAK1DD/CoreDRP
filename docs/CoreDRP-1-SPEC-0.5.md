# CoreDRP/1 — Core Durable Relay Protocol

**Originally designed and authored by Rob Cooke, 2026.**

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

**Status:** Draft 0.5 hardening revision  
**Reference implementation target:** Miningcore

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, NOT RECOMMENDED, MAY and OPTIONAL are RFC 2119/RFC 8174 terms when written in capitals.

## 1. Status and authority

CoreDRP/1 remains specification-first and pre-implementation. Draft 0.5 incorporates the previous public hardening work plus the two September 2026 adversarial reviews recorded in `docs/reviews/`.

Normative authority is: this Draft 0.5 specification; numbered registries/vectors; protobuf definitions; reference tooling. Draft 0.4 remains historical only and MUST NOT override this document.

## 2. Layering

Core owns authenticated identities, opaque scopes, lanes, epochs, ordering, event time, exact payload bytes, event identity, chaining, sender durability, replay, cumulative ACK, generic checkpoints, gaps, quarantine mechanics, flow control, clock evidence, reconnect/recovery and ADMIN digest mechanics.

Mining owns scope syntax, mining lanes/events, temporal membership/completeness policy, payout safety, clock policy and mining accounting order. Miningcore owns PostgreSQL persistence, accounting projections, payout/pruning integration, direct Bitcoin evidence and metrics. Dependencies are Core <- Mining <- Miningcore only.

## 3. Terms

Sender durably admits events. Receiver durably commits them. Receiver ID is stable logical recorder-cluster identity; receiver database incarnation identifies one durable database history. A lane is one ordered stream. An epoch is one UUID-scoped history of a sender/lane. A normal epoch transition drains all old durable history. Exceptional abandonment retires an undrainable epoch only with durable gap evidence.

## 4. Fixed identifiers and domains

Packages are `coredrp.v1`, `coredrp.mining.v1`, `coredrp.miningcore.v1`. Profile IDs are exact ASCII `coredrp.mining` and `coredrp.miningcore`.

Sender SAN: `urn:coredrp:sender:<uuid>`. Receiver SAN: `urn:coredrp:receiver:<uuid>`.

Domains are exact ASCII without terminator: `CoreDRP1-PAYLOAD`, `CoreDRP1-EVENT`, `CoreDRP1-GENESIS`, `CoreDRP1-CONTRACT`, `CoreDRP1-ADMIN`, `CoreDRP1-ADMISSION`.

## 5. Primitive encodings and ranges

Integers in cryptographic preimages use fixed-width big-endian encodings; event time uses signed `int64_be`; UUIDs use 16 RFC 9562 network-order octets. Sequence is `1..2^63-1`; zero denotes genesis only.

Before hashing: lane `0..255`; event type `0..65535`; sequence `1..2^63-1`; scope `0..65535` bytes; payload fits uint32 and negotiated/profile caps; profile/Core versions fit uint32; profile IDs are ASCII; event time for production events MUST be `0..253402300799999` (through year 9999 UTC). Crypto-only vectors MAY use other signed int64 times only when explicitly marked non-semantic.

All time arithmetic, including `B+2S`, MUST use checked arithmetic and fail closed on overflow.

## 6. Event and lane registry

Mining lane 0 is SHARE; lane 1 is CRITICAL. Types: `0x0001` checkpoint, `0x0100` MiningShareEvent, `0x0200` MiningcoreAccountingShareEvent, `0x0201` BitcoinDirectCoinbaseCandidate, `0x0202` CandidateStateUpdate. `0xF000..0xFFFE` are private/test; `0xFFFF` boundary-test only.

Unknown/unadvertised types are fatal. Known type on forbidden lane/scope form is `INVALID_EVENT_PLACEMENT`, non-quarantinable.

## 7. Hard resource limits

Pre-negotiation maxima: gRPC 20 MiB; Hello 256 KiB; implementation string 128 UTF-8 bytes; profile ID 64 ASCII bytes; 32 profile entries; 1024 scope contracts; 1024 advertised types; scope 65535 bytes; event payload 16 MiB; 4096 events/batch; batch flow charge 16 MiB; ChainProbe count 256.

Intrinsic single-object excess is permanent (`ATOMIC_RESOURCE_LIMIT_EXCEEDED`/`EVENT_TOO_LARGE`); splittable aggregate excess is retryable `RESOURCE_LIMIT_EXCEEDED`.

## 8. Authentication, authorization and identities

TLS 1.3 mTLS is REQUIRED. Sender/receiver Hello UUIDs MUST match their unique CoreDRP URI SANs. Ordinary receiver restart/failover MUST preserve receiver ID. Database history uncertainty MUST mint a new database incarnation.

Transport authorization and Mining temporal membership are distinct. Transport authorization does not rewrite history, but it is an admission condition for every new scoped event and for every scope newly asserted by a lane-global checkpoint.

## 9. Handshake validity

First frames are ClientHello then ServerHello/ProtocolError. Empty/wrong-direction/second hello is `MALFORMED_FRAME`.

For an empty sender epoch (`T=0`) `E` MUST equal 1. Otherwise `1 <= E <= T+1`. Remembered ACK sequence/hash are both present or absent; present ACK is within retained/durable history and hash length is 32.

All UUIDs/digests have exact lengths. Scope-contract digest MUST be exactly 32 bytes; zero-length is invalid. Profile IDs MUST be ASCII. Duplicate exact profile-version rows, event types or version-qualified scope-contract keys are invalid.

## 10. Deterministic Core/profile negotiation

Core major must match. For Core major 1, each peer advertises maximum Core minor; choose highest common minor.

Each `ProfileSupport` row describes one **exact** `(profile_id, profile_major, profile_minor)` version with its own minimum Core version. Peers MAY advertise multiple rows for one major and multiple majors. Discard rows requiring a newer Core version; choose highest mutually supported major, then highest mutually supported minor in that major. This makes rising per-minor Core requirements expressible and deterministic.

Mining/Miningcore global semantic digest MUST be absent; their semantics are scope-owned. Selected scope contracts MUST match selected exact profile version.

## 11. Epoch contract binding

Before first event, sender needs durable epoch approval plus successful bootstrap negotiation. Outage after binding MUST NOT stop admission **solely because negotiation cannot refresh**; clock, WAL durability, storage pressure, authorization, membership and other safety gates still apply.

Binding is SHA-256 over CONTRACT domain, Core version, lane, sorted selected profile set, sorted version-qualified scope contracts and sorted selected event types. Mining/Miningcore profile entries use `has_digest=0`; scope-contract entries carry exact 32-byte digest.

Binding is immutable within an epoch.

## 12. Semantic contracts

Mining scope contract binds profile version, scope, payout scheme, coin/network, completeness/retention policy versions, cross-sender order, clock parameters and admission-idempotency policy version. Completeness mode is temporal policy, not immutable contract state.

Draft 0.5 financial Mining admissions use **permanent idempotency tombstones**: the previous finite retry horizon is removed. The semantic contract therefore binds `admission_idempotency_policy_version=2`, not a finite expiry duration.

Miningcore scope contract binds accounting/persistence schema, direct-candidate validation version and settlement-policy version. Draft 0.5 requires `direct_candidate_validation_version >= 2` for the duplicate-txid and consensus-output rules in Section 41.

## 13. Event cryptographic construction

`payload_hash = SHA256(PAYLOAD_DOMAIN || uint32_be(len(P)) || P)`.

`chain[0] = SHA256(GENESIS_DOMAIN || sender_uuid || epoch_uuid || uint8(lane))`.

`chain[N] = SHA256(EVENT_DOMAIN || chain[N-1] || sender_uuid || epoch_uuid || uint8(lane) || uint64_be(N) || uint16_be(type) || relay_event_uuid || uint16_be(scope_len) || scope || int64_be(time) || payload_hash)`.

Exact received/WAL payload bytes are identity; protobuf reserialization is never canonical evidence.

## 14. Two-phase batch validation

Phase A occurs before opening the durable-effect transaction: framing, counts, integer ranges, event time, payload/scope limits, authorization, placement, required scope-contract ownership and complete chain verification.

Phase B occurs inside the transaction after stream-state lock: expected epoch/sequence/head, temporal membership, checkpoint coverage authorization, profile semantics, referential state and application effects.

A semantic-invalid event rolls back the batch. Repeated failure of the same immutable sequence MUST NOT loop forever: after a configured but contract-bound retry threshold (default 3 consecutive identical `SEMANTIC_PAYLOAD_INVALID` outcomes), receiver returns `SEMANTIC_RETRY_LIMIT`/operator intervention until validator/configuration changes or quarantine is explicitly authorized.

## 15. Durable admission identity

Caller idempotency namespace is exactly `(sender_id, lane_id, caller_admission_key)`.

Before sequence/time/relay-ID allocation, sender hashes **profile-defined caller request bytes**, not the final generated event payload:

`admission_digest = SHA256(ADMISSION_DOMAIN || uint8(lane) || uint16_be(type) || uint16_be(scope_len) || scope || uint32_be(request_len) || canonical_request_bytes)`.

For MiningShareEvent Profile 1.1, canonical caller-request encoding version 1 is frozen as follows. All strings are exact UTF-8 bytes with no normalization and are encoded as `uint32_be(byte_len)||bytes`. Every `double` MUST first satisfy the Mining finite/non-negative-zero rules and is encoded as its IEEE-754 binary64 bit pattern in network/big-endian byte order. Booleans are exactly one byte `0x00` or `0x01`. Optional values are encoded with a one-byte presence marker: `0x00` when absent; `0x01||value` when present. Optional byte/string values encode the present value as `uint32_be(byte_len)||bytes`. `block_reward`, when present, uses the exact canonical ASCII `Decimal38Scale24.canonical` bytes with a uint32 length prefix.

The exact request preimage is:

`uint16_be(1)`
`|| uint64_be(block_height)`
`|| lp32_utf8(miner)`
`|| lp32_utf8(worker)`
`|| lp32_utf8(user_agent)`
`|| ieee754_binary64_be(difficulty)`
`|| ieee754_binary64_be(achieved_share_difficulty)`
`|| ieee754_binary64_be(actual_difficulty)`
`|| ieee754_binary64_be(network_difficulty)`
`|| lp32_utf8(source_ip)`
`|| lp32_utf8(source)`
`|| lp32_utf8(session_id)`
`|| uint8(is_block_candidate ? 1 : 0)`
`|| optional_lp32_bytes(candidate_hash)`
`|| optional_lp32_utf8(candidate_kind)`
`|| optional_lp32_utf8(transaction_confirmation_data)`
`|| optional_lp32_ascii(block_reward.canonical)`.

`created_unix_ms` is intentionally excluded because the lane sequencer generates it only after idempotency resolution. Core sequence, epoch sequence, log epoch and relay UUID are likewise excluded. No protobuf serialization, JSON serialization, locale formatting, native-endian float representation, omitted-default heuristic or field reordering is permitted as a substitute for this grammar. Future canonical request encodings require a new Mining profile minor or a new explicitly versioned request grammar; permanent tombstones retain the request-encoding version used by the original admission.

The sender resolves the permanent tombstone first; same namespace key+digest returns the original admission forever, and the same namespace key with a different digest is `IDEMPOTENCY_KEY_CONFLICT`. Financial Mining callers MUST NOT be able to mint a second event by waiting for tombstone expiry.

WAL + idempotency mapping cross one durable flush boundary before application success.

## 16. Sender WAL, anchor and corruption recovery

WAL records use length plus CRC32C/equivalent local framing. Anchor MAY lag WAL but MUST NOT lead it. Recovery first verifies anchor record/hash. Corruption/truncation before or at anchor is a safety incident: do not trust the anchor, do not skip, do not create a new epoch. Corruption after the anchor may truncate only a proven unACKed torn tail; middle corruption fails closed.

UnACKed records are never silently evicted. Sender spool has a configured durable byte cap and high-water thresholds; before cap exhaustion stop new client/miner work, then fail new admission rather than accepting in memory.

## 17. Deterministic flow control

Per-event logical charge is `32 + len(scope) + len(payload)` bytes. The fixed 32-byte overhead represents sequence/type/time/relay-ID/accounting overhead; protobuf/HTTP2 framing remains governed by message limits.

`window_bytes` counts charge for unACKed transmitted events; `window_events` counts those events. Zero for either dimension pauses all EventBatch transmission, including empty-payload events. Heartbeats/clock/control frames remain allowed. WindowUpdate cannot exceed negotiated maxima.

## 18. Single-writer and duplicate-receiver fencing

Sender fence is `(sender_id,lane_id)` across epochs. Receiver permits one active stream per sender/lane and, in PostgreSQL, uses lifetime advisory/lease fencing plus row lock/CAS.

Two independent receiver databases are separate logical receivers and therefore require distinct receiver IDs or explicit replacement approval; sender MUST NOT fan one stream to competing uncoordinated durable histories as if both were the same receiver.

## 19. Reconnect precedence and receiver replacement

Evaluate exactly: (1) receiver ID mismatch; (2) database-incarnation mismatch; (3) epoch approval; (4) `C>T` sender rollback; (5) `C<R` receiver rollback; (6) bootstrap `C=R=0` genesis mismatch -> SPLIT_LOG; (7) at the sole ordinary reconciliation point `C`, if `C>0` chain hash differs -> SPLIT_LOG; (8) `C+1<E` recovery gap; (9) `C>R` with verifiable hash -> adopt ACK; (10) `C>R` unverifiable -> SPLIT_LOG; (11) `C==R` matching -> resume.

Comparing the hash at `C` is sufficient because the chain commits every predecessor; ChainProbe is diagnostic and never required for ordinary reconciliation.

Receiver replacement/incarnation approval is ADMIN action `0x0007`. It preserves previous receiver/ACK anchor and allows audited repin only after the same chain checks: `C==R` matching -> repin; `C>R<=T` verifiable -> adopt then repin; `C<R` -> replay lost ACKed history only when all required records remain, otherwise RECOVERY_GAP; mismatch -> SPLIT_LOG. Logical receiver-ID replacement requires explicit old-ID -> new-ID approval in addition to these checks.

## 20. ACK semantics

ACK means receiver effects/evidence/head/checkpoint state durably committed. ACK is cumulative/monotonic. Sender validates ACK then durably remembers receiver ID/incarnation, sequence/hash before prune eligibility. Commit-success/ACK-loss is normal replay.

## 21. Receiver transaction semantics

Within one transaction: durability policy; stream lock; receiver/epoch/sequence/head/floor checks; temporal membership and referential checks; profile semantic validation; exact evidence/effects; authorized gap/quarantine records; committed head/checkpoint updates; COMMIT. Any failure rolls back and emits no ACK.

## 22. Epoch lifecycle and exceptional recovery

Initial epoch requires ADMIN `0x0005`. Normal transition `0x0004` requires receiver committed == remembered ACK == durable tail == final sequence with matching hash.

Exceptional abandonment `0x0006` atomically retires the old epoch and records the exact abandoned suffix. If every abandoned record's scope can be proven, create per-scope gaps for all affected scopes. If any scope attribution is unknown/corrupt, create a **lane-wide wildcard gap** that poisons every applicable scope in the old epoch binding until resolved/waived. PayoutSafe relevance MUST treat wildcard gap as relevant to all those scopes.

Exact abandoned WAL records MUST be retained until reconciliation or waiver permits conversion to durable gap/audit evidence under the retention policy.

`RESOLVED_RECONCILED` uses an audited retired-epoch import path: verify retired epoch tombstone, exact old chain, sequence/range and event identities; apply missing effects idempotently without making the old epoch current; then resolve the gap atomically. Waiver never fabricates completeness.

## 23. Error model

Registry disposition is authoritative. Structural, authorization, placement, clock proof, identity, chain, rollback, membership and epoch errors are never quarantinable. Only correctly placed/Core-valid profile semantic payload failures may be quarantined.

Every non-UNSPECIFIED Core error code MUST have an explicit emission condition in this specification or an incorporated normative registry row, and CI checks the cross-reference.

## 24. Quarantine

Quarantine uses exact immutable event identity. Operator authorization names sender/lane/epoch/sequence/type/relay-ID/chain hash. Sender retransmits identical bytes; receiver stores exact evidence plus watermark atomically. Changed bytes are `EVENT_IDENTITY_MISMATCH`, not quarantine.

## 25. Gaps

Gap scope may be exact scope or wildcard lane scope. It records sender/lane/epoch/range, conservative time bounds, chain evidence, classification and audit provenance. Wildcard gaps are relevant to every scope whose selected contract/membership could have been affected.

Resolution is reconciled import or explicit waiver. Reconciliation never reactivates retired epoch.

## 26. Checkpoints and authorization

Mining checkpoints have empty Core scope but their covered set derives from immutable epoch scope contracts plus temporal membership/mode at the checkpoint time.

Before accepting a **new** checkpoint, receiver MUST verify sender remains authorized to assert completeness for every scope that checkpoint would cover. If any covered scope authorization was revoked, reject checkpoint (`UNAUTHORIZED_SCOPE`) until membership is ended/reconciled or a gap/waiver records uncertainty. Historical checkpoints are never reinterpreted after later revocation.

## 27. Anti-backdating

After trusted checkpoint T, every later covered event in this or successor epoch has event time >T. Sender and receiver enforce. Violation is non-quarantinable `CHECKPOINT_BACKDATED_EVENT`.

## 28. Event time

Lane sequencer assigns nondecreasing event time within production range from Section 5 and persists last assigned value. Mining `created_unix_ms` equals Core event time. Cross-epoch floor is max(old last event, old trusted checkpoint, inherited floor). A step larger than effective maxClockStep makes local clock BAD rather than moving the floor arbitrarily.

## 29. Clock probes and sender-facing state

Receiver stores authoritative `t1` keyed by unique outstanding `probe_id`; `ClockProbeResponse` does not carry authoritative `t1`. Unknown, duplicate or expired probe responses are discarded. `t4` is receiver-local receive time. Arithmetic is checked.

For valid probe: reject `t3<t2`; `L=t3-t4`, `U=t2-stored_t1`, `rtt=(t4-t1)-(t3-t2)`. GOOD iff interval fully within permitted skew; BAD iff wholly outside; UNKNOWN otherwise/no fresh evidence. Do not intersect different-time intervals.

Receiver emits monotonic-generation `ClockStateUpdate` whenever effective state changes and periodically while GOOD. Sender treats the state as valid only for `evidence_valid_for_ms` measured on local monotonic time. Expiry without newer update becomes remote UNKNOWN. A newer definitive BAD overrides older GOOD regardless of RTT ranking.

## 30. Clock policy and grace

Multi-scope lane uses strictest active policy. Local BAD or receiver-reported BAD stops covered admission/checkpoints. Remote UNKNOWN may continue admission only within grace and never advances trusted checkpoints; expiry stops admission. Recovery from BAD requires trusted UTC not behind last durable time plus three fresh GOOD observations spanning at least one effective probe interval.

Receiver wall-clock step detection compares wall and monotonic elapsed deltas: `abs(delta_wall-delta_monotonic) > maxClockStep => BAD`.

## 31. Mining event admission and ownership

Mining scope is exact `[A-Za-z0-9._-]{1,64}` ASCII. For every payout-relevant lane-0 MiningShareEvent or MiningcoreAccountingShareEvent at event time M while mode is RELAY_REQUIRED, durable temporal membership `(sender,scope,M)` MUST exist. Missing membership is `TEMPORAL_MEMBERSHIP_REQUIRED` and fails closed; a transport-authorized but unlisted sender cannot contribute financial work outside the completeness set.

Event ownership requirements: `0x0100` requires Mining(scope); `0x0200`, `0x0201`, `0x0202` each require both Mining(scope) and Miningcore(scope) exact selected version/digest in epoch binding.

## 32. Temporal membership and mode

Membership/mode intervals are append-only, non-overlapping half-open `[from,until)`. Missing mode fails closed. `RequiredSender(Q,T)` is membership covering T when mode is RELAY_REQUIRED. Empty membership is safe only under explicit NO_RELAY_REQUIRED interval covering T.

For integer-millisecond time, ending membership at `valid_until` requires final trusted completeness through at least `valid_until-1` when interval is non-empty; otherwise create gap/waiver. Future-effective changes cannot silently invalidate already-proven frontier.

## 33. PayoutSafe scope

PayoutSafe requires known durable mode, all RequiredSenders complete, clock-valid checkpoints, no relevant exact/wildcard gap or payout-significant quarantine, durable policy/contract evidence and anti-backdating guarantees. A checkpoint contributes to PayoutSafe only after its event sequence and checkpoint effect are durably committed by the receiver and the cumulative ACK covering that sequence is durably remembered by the sender. Sender-side checkpoint creation alone is never payout-safe evidence. It is a safety statement under the Section 43 non-Byzantine authenticated-sender assumption; it does not prove a compromised sender truthful.

`PayoutSafeThrough` is monotonic. Cross-sender boundary uses checked `B+2S` unless tighter conservative interval proof exists.

## 34. SafePruneThrough

SafePruneThrough is monotonic and never exceeds PayoutSafeThrough for payout evidence. Never prune receiver/epoch anchors, membership/mode history, unresolved/resolved gap/quarantine/waiver audit, retired-epoch import evidence, permanent financial idempotency tombstones or settlement evidence still required.

## 35. Mining scheme and order

PPLNS/PPLNSBF/PROP settlement requires PayoutSafe; prune no farther than SafePruneThrough and scheme cutoff. PPS and custodial SOLO have profile-defined non-fence behavior; direct submission never waits for remote completeness.

Cross-sender accounting order is event time, sender UUID bytes, sequence, relay UUID bytes. It is deterministic accounting order, not physical causality.

## 36. Direct-candidate independence

Submitting edge durably records exact candidate/settlement evidence before submitblock. Recorder/critical-lane/completeness failure cannot delay local consensus submission.

## 37. PostgreSQL durability and promotion

CoreDRP committed-state transaction requires `fsync=on`, `synchronous_commit=on` or stronger and logged durable tables. A promoted history that may omit ACKed transactions mints a new database incarnation and follows Section 19 replacement reconciliation before traffic.

## 38. Failure decision table

| Failure/detection | Required action | Recovery |
|---|---|---|
| PostgreSQL unavailable before COMMIT | no ACK; sender spools; `RECEIVER_DURABILITY_UNAVAILABLE` | reconnect/retry after durable DB returns |
| sender WAL fsync/disk full | stop new admission; never memory-accept | repair storage; verify WAL/anchor before resume |
| torn unACKed WAL tail after anchor | truncate only proven unACKed torn records | replay remaining WAL |
| middle WAL corruption or corruption <= anchor | stop; never skip/new epoch automatically | restore trusted copy or exceptional abandonment + wildcard/exact gaps |
| commit succeeded, ACK lost | receiver reports C>R | verify hash, adopt ACK |
| same-incarnation C<R | `RECEIVER_ROLLBACK` | operator reconciliation/replay if evidence retained |
| C>T | `SENDER_ROLLBACK` | operator intervention; never longest-history guess |
| receiver ID/incarnation changes | stop before ordinary reconcile | ADMIN receiver replacement approval + Section 19 matrix |
| duplicate sender writer | fence denies second | remove stale owner only with fencing proof |
| same logical receiver on separate DB histories | identity/incarnation conflict | explicit replacement; do not dual-own |
| split common head | `SPLIT_LOG` | operator investigation/import; no automatic choice |
| semantic poison sequence | rollback; bounded retries | quarantine/validator fix; then resume |
| spool high-water/cap | stop new client work before cap; fail new admission at cap | drain receiver or expand durable capacity |

## 39. Heartbeats, drain and ChainProbe

Heartbeats/Goodbye are operational only. ChainProbe is authenticated admin diagnostic, count 1..256, never mutates stream/reconciliation state.

## 40. Miningcore accounting and candidate referential integrity

Financial decimals use canonical Decimal38Scale24. Accounting projection rules remain SINGLE vs PARENT+AUXILIARY with non-empty distinct IDs, nonnegative reward basis, canonical PPS amount, preserved Created and consistent block/statistical flags.

Candidate ID is unique within `(scope, Miningcore contract)`. CandidateStateUpdate MUST reference an existing durable candidate in the same enclosing scope; unknown/cross-scope candidate is `INVALID_STATE_TRANSITION`. State, attempts, misses and last-attempt monotonicity are checked transactionally against stored prior candidate state.

## 41. Bitcoin evidence and injective validation

Receiver uses a consensus-compatible parser/library and validates the entire block. It MUST verify block hash; parse every transaction; require tx0 coinbase; verify coinbase non-witness txid; reject **any duplicate txid anywhere in the block** before accepting Merkle evidence; and compute the complete txid Merkle root.

BIP34 activation is receiver-side network configuration, not inferred from a network-name string and not supplied by the candidate. The selected Mining scope/network parameters MUST provide the activation height (mainnet is 227931; synthetic-regtest vectors use 0; every other supported network uses its authoritative configured value). At every height greater than or equal to that configured activation, the coinbase first script item MUST equal the candidate block height as minimally encoded CScriptNum. Unknown or missing activation parameters fail closed.

If any transaction uses witness serialization, the block MUST contain a valid BIP141 witness commitment. The highest matching `OP_RETURN 0x24 aa21a9ed <32>` output is authoritative for witness-root comparison, but **every** coinbase output matching the BIP141 commitment pattern MUST be explicitly present exactly once in `BitcoinDirectCoinbaseCandidate.consensus_commitments`. There is no implicit “recognized but undeclared” acceptance path. Duplicate declaration of one output index, omission of a BIP141-pattern output, wrong declared script/index/value, or declaration of an output that does not classify under the receiver-side allow-list is invalid.

Consensus/merge-mining commitment classification is receiver-side policy keyed by `(network_id, direct_candidate_validation_version)`. A declaration is evidence about which exact coinbase output the sender intends to classify; it is **not authority to invent a new commitment class**. For each declared `(output_index, exact script_pub_key)`, the receiver MUST first verify the exact zero-valued coinbase output and then classify its script under the configured allow-list. If no allowed class matches, reject the candidate. Draft 0.5 conformance parameters include class `BIP141`; additional AuxPoW/sidechain commitment classes require an explicitly versioned profile/network rule before they are accepted.

After commitment classification, receiver verifies miner/direct outputs and requires the gross reward to equal the sum of all coinbase outputs. Each coinbase output is consumed exactly once by the direct-recipient/miner classification or by one validated declared consensus-commitment classification; double classification and unclassified remaining outputs fail closed.

Address metadata, when supplied, is validated using network_id from the selected Mining scope contract. Candidate message does not duplicate network_id.

Conformance MUST include 4-tx and 3-tx blocks, witness-bearing multi-tx block, duplicate-txid CVE pair, missing/undeclared witness commitment, duplicate commitment declaration, disallowed commitment class, configured BIP34 mismatch, bad Merkle, bad block hash, bad coinbase txid, bad reserved value, bad reward and trailing bytes.

## 42. ADMIN actions

Assigned Core actions include quarantine, gap reconcile/waive, normal transition, initial epoch, exceptional abandon and `0x0007 RECEIVER_REPLACEMENT_APPROVAL`; Mining actions membership/mode/override; Miningcore capability activation.

Canonical TLV fields arrive **already strictly increasing** and unique. Verifiers MUST reject descending or duplicate IDs; they MUST NOT sort malformed input before validation. Integer widths are exact. ADMIN corpus includes positive vectors for initial/normal/exceptional/replacement actions and negatives for duplicate IDs, descending IDs and wrong-width uint64.

## 43. Security boundary

mTLS and hash chains protect authenticated transport and consistent history, not Byzantine truth. PayoutSafe assumes authenticated senders follow protocol and clocks except for detectable faults. Stronger storage compromise resistance needs independently protected signed/HMAC anchors or transparency storage. No 0-RTT application data.

## 44. Conformance and CI claims

CI validates document structure/encoding, canonical protobuf wire fingerprints, layer boundaries, error/event/metric registries, cryptographic/contract/admission/ADMIN vectors, executable positive/negative profile and Bitcoin cases, state decisions and bounded formal model. These are **conformance checks, not a proof of the whole protocol**.

Every non-UNSPECIFIED error code must be referenced by spec/registry emission rules. State-vector dispatch uses explicit `case_kind`, never case-name prefixes. Temporal membership/mode boundaries, authorized-but-unlisted sender, wildcard gap relevance and PayoutSafe conditions are executed.

## 45. Formal-model requirements

The model MUST include independent state variables for durable WAL vs anchor, remembered ACK, receiver durable state, sender checkpoint vs receiver-committed checkpoint evidence, current/retired epochs, gap scope/range, receiver rollback observation/detection, writer ownership, membership/clock proof gates and payout/prune frontiers. PayoutSafeThrough MUST NOT advance from sender-created checkpoint state alone: the model requires a receiver-committed checkpoint effect, sender remembered ACK covering that checkpoint, durable membership proof, clock proof and no unresolved current gap. Checked invariants include writer uniqueness, ACK/prune ordering, normal drain, exceptional exact/wildcard gap coverage, cross-epoch temporal floor, payout-evidence gating, PayoutSafeThrough monotonicity and SafePruneThrough<=PayoutSafeThrough.

Mutation controls modify legitimate actions rather than add a purpose-built unsafe action: at minimum prune-to-receiverDurable, remember-ACK-before-commit, normal-transition-without-drain and payout-advance-without-evidence; CI requires each mutation to violate an invariant. Deadlock checking remains off only for explicitly terminal operator-intervention states; liveness scenarios for normal drain/recovery are separately bounded and exercised.

## 46. Evolution and reservations

Safety-significant frame alternatives require negotiated Core minor. Draft 0.5 Core minor is 1. Top-level tags 10..15 remain available for compatible minor evolution; 16..31 are reserved. Stable numeric allocations are never reused. Protobuf syntax/package/service identities are compatibility-critical.

## 47. Out of scope

CoreDRP does not standardize Byzantine consensus, independent-database active/active receiver consensus, automatic payout compensation or global standards governance.

## 48. Miningcore reference requirements

Miningcore implements dedicated CoreDRP ingest, PostgreSQL durability, sender/receiver fencing, permanent financial admission idempotency, temporal-membership enforcement, exact scope-contract ownership, wildcard gaps, receiver replacement approval, canonical accounting order, direct-candidate validation v2 and candidate referential integrity.

## 49. Required conformance corpus

Before stable release include: lane/type/scope/sequence/hash/UUID boundaries; exact-version profile negotiation with multiple majors/minors and per-version Core minima; scope digest length/ASCII negatives; reconnect precedence; receiver replacement; WAL/anchor corruption; permanent idempotency with canonical MiningShare request reconstruction; event-time bounds/overflow; clock state wire transitions and replay/expiry; membership intervals and unlisted sender; checkpoint revocation; wildcard gaps/retired import; flow charge including max scope/empty payload/zero windows; Bitcoin multi-tx odd/even, duplicate txid, SegWit declaration/commitment negatives and configured BIP34 mismatch; candidate referential negatives; ADMIN ordering negatives; realistic formal mutations including payout-evidence removal.

## 50. Authorship

CoreDRP — Core Durable Relay Protocol was originally designed and authored by **Rob Cooke** in 2026 and originally developed for the Miningcore project.

Canonical project: `https://coredrp.org`  
Source: `https://github.com/NINJAK1DD/CoreDRP`

<!-- COREDRP-SPEC-END:50 -->
