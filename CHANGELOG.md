# Changelog

## Admission and retained-audit hardening — 2026-09-05

- Require durable all-history admission/commit checks before permission withdrawal, including membership end and previously ACKed/pruned events.
- Allocate canonical Miningcore caller requests and activated-policy evidence; enforce global accounting UUID uniqueness with permanent replay tombstones.
- Retain original settlement payloads and immutable reward/deduction inputs; define PROP arithmetic and exact winning-share linkage.
- Advance completeness policy 3 → 4 and settlement policy 4 → 5; regenerate contract/effect/summary digests without changing protobuf.
- Restore Python and independent C# ADMIN epoch-action encodings, add clock/time and duplicate/oversized input regressions, and make SingleWriter independently mutation-testable.
- Explicitly retain the bounded safety model scope and permanent-holder recovery limitation.

## Financial hardening — 2026-09-05

- Freeze PPLNS/PPLNSBF exact score/cutoff and full-tuple pagination; bind PPS retained percentage, eligibility and exact liability arithmetic.
- Define reconstructible per-accounting EffectIdentityV1 records and same-miner contribution aggregation before destructive pruning.
- Reject unsafe bootstrap, pending-policy migration and missing sender payout-effect admission evidence; require exact PoolId identity.
- Clarify critical candidate waiver-only recovery and explicitly incorporate validator authority.
- Advance completeness policy to 3, settlement policy to 4 and settlement-scheme source to 3; regenerate affected digests. Core wire is unchanged.
- Add Python, parsed-protobuf and independent C# financial conformance coverage.

## Draft 0.5 — completeness, clock, recovery and evidence hardening

- added Core 1.1 receiver→sender `ClockStateUpdate` with replay-safe generations and local evidence expiry;
- removed echoed receiver `t1` from authoritative clock computation and froze unique outstanding probe semantics;
- qualified post-binding outage admission so clock, WAL, storage, authorization and membership safety gates still apply;
- changed Mining financial admission identity to permanent `(sender,lane,key)` tombstones and caller-request bytes, including lane in the digest;
- made exact profile support rows version-specific, selecting highest mutually supported major then minor with a Core minimum per exact version;
- enforced temporal membership on RELAY_REQUIRED payout-relevant event admission and scope-contract ownership per event type;
- required new lane-global checkpoints to be authorized for every scope they newly assert;
- added per-scope/wildcard exceptional-abandonment gaps, retained abandoned evidence and retired-epoch import reconciliation;
- added audited receiver logical-ID/database-incarnation replacement approval and deterministic repin/replay/recovery-gap matrix;
- changed flow-control byte charge to fixed per-event overhead + scope + payload, with zero windows pausing all EventBatch traffic;
- bounded production event time and required checked time arithmetic;
- expanded WAL/anchor/spool failure semantics and separated pre-transaction structural checks from in-transaction semantics;
- bounded repeated immutable semantic failures with operator-intervention state;
- added duplicate-txid rejection for CVE-2012-2459 Merkle malleability and executable positive/negative Bitcoin evidence cases;
- added declared consensus/merge-mining commitment outputs to the Miningcore candidate wire;
- tightened BIP34 wording to network activation parameters/minimal CScriptNum and clarified network source from the Mining scope contract;
- added candidate-state referential/same-scope/monotonic transaction rules;
- replaced finite idempotency-horizon state vectors with permanent financial-idempotency cases;
- added receiver replacement, wildcard gaps, unlisted sender, checkpoint revocation, clock-state expiry/replay, event-time, flow-charge and scope-contract ownership vectors;
- added supplemental exact-version negotiation, admission, ADMIN ordering, scope digest/ASCII and candidate referential conformance vectors;
- replaced the hand-maintained protobuf surface parser gate with exact reviewed protobuf blob fingerprints;
- removed unused Core imports from profile protobuf files;
- reduced README assurance language and added an in-repository adversarial review disposition trail.

## Draft 0.4 — transition, negotiation and evidence hardening

- required normal epoch transitions to fully drain receiver commit, sender remembered ACK and sender durable tail before retirement;
- added explicit exceptional epoch abandonment that atomically records an unresolved gap for any accepted-but-unreplicated suffix;
- added durable first-epoch approval/bootstrap semantics and permanent initial/normal/exceptional ADMIN action allocations;
- separated stable logical receiver identity from receiver database incarnation and made unexpected receiver-ID change operator-intervention state;
- made Mining completeness mode temporal audited policy rather than an immutable semantic-contract value;
- version-qualified every scope semantic contract and made Mining/Miningcore profile-global semantic digests explicitly absent;
- added a domain-separated local admission digest and contract-bound admission-idempotency retry horizon;
- split invalid event placement from quarantinable payload-invalid events and separated atomic resource-limit failures from retryable aggregate pressure;
- froze exact reconnect evaluation precedence, bootstrap genesis matching, unverifiable higher-receiver handling and receiver-ID behavior;
- froze deterministic GOOD/BAD/UNKNOWN clock classification and strictest active multi-scope clock-policy aggregation;
- defined WindowUpdate zero as pause and prohibited updates above handshake-negotiated maxima;
- froze the Miningcore accounting projection validity matrix for SINGLE and PARENT/AUXILIARY effects;
- required Bitcoin candidate validation to bind all transactions to the header Merkle root and validate BIP141 witness commitments;
- added a synthetic SegWit direct-candidate vector and executed positive/negative share, accounting, placement and Bitcoin semantic checks;
- expanded state vectors for reconnect overlaps, epoch draining/abandonment, receiver identity, clock state, idempotency horizon and WindowUpdate;
- strengthened TLA+ so non-durable admission can be lost on crash, faults precede detection, retired re-entry is attempted/refused, and epoch transitions model drain/gap requirements;
- promoted the Miningcore metrics registry to Draft 0.4 normative status and added CI consistency checks;
- hardened protobuf compatibility checks for syntax/edition and unexpected services across all profile files;
- extended layer-boundary vocabulary self-tests for txid/wtxid, UTXO, mempool, fee, ledger, SegWit and witness terminology.

## Draft 0.3 — cross-epoch and conformance hardening

- made temporal/checkpoint completeness floors survive approved epoch transitions;
- widened sender single-writer fencing to `(sender_id,lane_id)` across epoch changes;
- froze CoreDRP Mining and Miningcore wire profile IDs and deterministic profile/minimum-Core negotiation;
- changed epoch contract version encoding to `uint32_be`, matching wire version widths;
- froze independently reproducible Mining and Miningcore semantic-contract source grammars and vectors;
- formalized fail-closed temporal membership, `RequiredSender`, `PayoutSafe`, `PayoutSafeThrough` and non-vacuous no-member behavior;
- made membership start/end and completeness-mode changes privileged and non-retroactive without reconciliation/waiver;
- added sender durable admission idempotency so unknown local outcomes cannot mint a second financial event;
- froze legal event/lane/scope and candidate-field combinations;
- made quarantine progression retransmit and store the exact immutable rejected event;
- bound checkpoint coverage to persisted epoch scope contracts and temporal membership rather than mutable transport authorization;
- froze deterministic cross-sender mining order for equal-time financial windows;
- defined payload-only flow-control byte charging and remembered contract-binding presence rules;
- added Bitcoin direct-candidate self-consistency validation against exact serialized block/coinbase evidence;
- froze global privileged action numbers and canonical ADMIN TLV request encoding;
- hardened spec truncation detection and layer-boundary self-tests;
- expanded the wire baseline to every message, enum, oneof, RPC and reserved range;
- added state-machine vectors for reconnect/rollback/recovery gap, WAL crash ordering, idempotency, epoch floors, fencing, membership, quarantine and ordering;
- added valid Bitcoin direct-candidate and candidate-state vectors and consumed every declared semantic negative;
- expanded independent C# checks to semantic-contract, contract-binding, ADMIN and maximum-scope vectors;
- expanded TLA+ with crash, rollback, epoch, writer and fault transitions plus a deliberately unsafe mutation that CI requires TLC to reject.

## Draft 0.2 — adversarial hardening

- repaired and completely rewrote the corrupted/incomplete normative specification;
- defined sections for handshake, negotiation, WAL, ACK/replay, rollback, epochs, quarantine, clocks and mining completeness;
- bound relay event IDs into the event chain;
- made event/lane/sequence range rejection normative before hashing;
- made normal batch durability all-or-nothing;
- added immutable per-epoch contract binding and scope semantic contracts;
- made checkpoint scope lane-global/empty for Mining Profile v1 and added anti-backdating;
- split client/server heartbeat frames, bounded ChainProbe, and added graceful Goodbye;
- removed recursive paired-share schema;
- added exact monetary grammar, float validity, Bitcoin byte-order rules and candidate transition graph;
- added error dispositions and a normative registry;
- expanded CI to protect specification integrity, registries, layer boundaries, wire compatibility and profile semantics;
- expanded vectors for lane/type/sequence/scope boundaries, contract binding, ADMIN digest and .NET UUID byte order;
- added a small TLA+ safety model.

## Draft 0.1

Initial public CoreDRP/1 specification draft.
