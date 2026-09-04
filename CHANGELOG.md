# Changelog

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
