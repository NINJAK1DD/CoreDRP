# Changelog

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
