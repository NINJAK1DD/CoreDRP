# CoreDRP/1 ClockStateUpdate Registry — Draft 0.6

**Status:** Draft 0.6 normative registry  
**Wire:** Core 1.1

This registry is incorporated through the normative `coredrp-v1-draft06-contracts.md` registry, which is itself incorporated by Section 1 of `CoreDRP-1-SPEC-0.6.md`. It defines the complete accepted-state matrix for `ClockStateUpdate`. Values not permitted below are rejected before they can influence admission, checkpoints, or payout safety.

## 1. Common structural rules

For every accepted update:

- `observation_generation` MUST be non-zero and strictly greater than the last accepted generation in the current authenticated stream;
- generation state is reset only by a successful new `ServerHello`; generations are never compared across streams;
- `state` MUST be one of GOOD, BAD, UNKNOWN; UNSPECIFIED is `MALFORMED_FRAME`;
- `reason` MUST be one of PROBE_EVIDENCE, EVIDENCE_EXPIRED, RECEIVER_WALL_STEP, SENDER_PROCESSING_LIMIT; UNSPECIFIED is `MALFORMED_FRAME`;
- `evidence_valid_for_ms` MUST be in `1..effective_evidence_expiry_ms`;
- `effective_permitted_skew_ms` MUST equal the strictest currently bound lane skew policy exactly;
- when both offset bounds are present, `lower_offset_ms <= upper_offset_ms`;
- a present `probe_id` MUST identify a valid receiver-owned observation from the current stream and MUST NOT have been consumed, expired, or issued on a previous stream;
- integer/range/presence violations are `MALFORMED_FRAME`; semantically contradictory but structurally valid combinations are `CLOCK_CONTRACT_VIOLATION`.

Let `S = effective_permitted_skew_ms` and `I = [lower_offset_ms, upper_offset_ms]` when both bounds are present.

## 2. Exhaustive state/reason matrix

| State | Reason | `probe_id` | lower/upper bounds | Required semantic relation | Result |
|---|---|---|---|---|---|
| GOOD | PROBE_EVIDENCE | REQUIRED | BOTH REQUIRED | `-S <= lower <= upper <= S` | ACCEPT |
| GOOD | EVIDENCE_EXPIRED | any | any | contradictory: expired evidence cannot assert GOOD | `CLOCK_CONTRACT_VIOLATION` |
| GOOD | RECEIVER_WALL_STEP | any | any | contradictory: wall-step evidence cannot assert GOOD | `CLOCK_CONTRACT_VIOLATION` |
| GOOD | SENDER_PROCESSING_LIMIT | any | any | processing-limit evidence cannot prove GOOD | `CLOCK_CONTRACT_VIOLATION` |
| BAD | PROBE_EVIDENCE | REQUIRED | BOTH REQUIRED | `upper < -S` OR `lower > S` | ACCEPT |
| BAD | RECEIVER_WALL_STEP | MUST BE ABSENT | BOTH OPTIONAL, but either both or neither | if present, interval MUST NOT be wholly GOOD; wall-step detection itself is authoritative BAD evidence | ACCEPT |
| BAD | SENDER_PROCESSING_LIMIT | REQUIRED | BOTH OPTIONAL, but either both or neither | sender processing exceeded bound for the referenced probe; any present interval MUST NOT be wholly GOOD | ACCEPT |
| BAD | EVIDENCE_EXPIRED | any | any | expiry alone is UNKNOWN/RECOVERING, never new BAD evidence | `CLOCK_CONTRACT_VIOLATION` |
| UNKNOWN | EVIDENCE_EXPIRED | MUST BE ABSENT | MUST BE ABSENT | no fresh bound evidence remains | ACCEPT |
| UNKNOWN | PROBE_EVIDENCE | REQUIRED | BOTH REQUIRED | interval overlaps the policy boundary: NOT wholly GOOD and NOT wholly BAD | ACCEPT |
| UNKNOWN | SENDER_PROCESSING_LIMIT | REQUIRED | BOTH OPTIONAL, but either both or neither | insufficient trustworthy bound; any present interval MUST NOT be wholly GOOD | ACCEPT |
| UNKNOWN | RECEIVER_WALL_STEP | any | any | receiver wall-step is definitive BAD, not UNKNOWN | `CLOCK_CONTRACT_VIOLATION` |

`any` above means the row is already contradictory regardless of optional-field presence; implementations MUST NOT reinterpret it into another state.

## 3. Presence rules

- Lower and upper bounds are a pair. Exactly one present is `MALFORMED_FRAME`.
- GOOD always carries both bounds and a current-stream `probe_id`.
- BAD/PROBE_EVIDENCE always carries both bounds and a current-stream `probe_id`.
- UNKNOWN/PROBE_EVIDENCE always carries both bounds and a current-stream `probe_id`.
- UNKNOWN/EVIDENCE_EXPIRED carries neither bounds nor `probe_id`.
- RECEIVER_WALL_STEP MUST NOT carry `probe_id`; bounds are diagnostic only and, if used, MUST be a complete pair.
- SENDER_PROCESSING_LIMIT references the probe whose sender-side processing duration violated policy and therefore requires `probe_id`; bounds are optional diagnostics but, if used, MUST be a complete pair.

## 4. Derived interval classes

For a complete interval `I`:

- `GOOD_INTERVAL` iff `-S <= lower <= upper <= S`;
- `BAD_INTERVAL` iff `upper < -S OR lower > S`;
- `UNKNOWN_INTERVAL` otherwise.

PROBE_EVIDENCE rows MUST use the state corresponding exactly to that classification. A receiver MUST NOT label one interval with a different state.

## 5. Stream processing and replay

An update with generation less than or equal to the last accepted generation in the same stream is stale/replayed and MUST be ignored without changing clock state. It is not an error response condition.

A successfully negotiated replacement stream starts a fresh generation namespace at 1. The first update in the new stream is compared only against generation zero, not against the previous stream's terminal generation.

## 6. Expiry and BAD latch

Local monotonic expiry of a previously accepted GOOD or ordinary UNKNOWN observation produces local UNKNOWN when there is no newer state.

Expiry of an accepted BAD does **not** produce ordinary UNKNOWN grace. It produces RECOVERING, a local derived state that continues to block covered admission and checkpoint advancement until Core Draft 0.6 Section 30 recovery conditions are met.

RECOVERING is not a wire `ClockBoundState` enum value. It is sender/receiver local protocol state derived from prior BAD evidence plus recovery observations.

## 7. Recovery observations

BAD/RECOVERING -> GOOD requires all of:

- trusted UTC is not behind durable last event time;
- at least three fresh accepted GOOD/PROBE_EVIDENCE updates;
- the first and last qualifying observations span at least one effective probe interval;
- no intervening accepted BAD occurs.

A new BAD resets the qualifying-GOOD count and span.

## 8. Conformance

The Draft 0.6 vector corpus MUST contain at least one accepted and one rejected case for every non-trivial matrix family: GOOD probe, BAD probe, UNKNOWN overlap, evidence expiry, receiver wall step, sender processing limit, malformed one-bound presence, invalid probe presence, stale generation, new-stream generation reset, BAD expiry latch, and BAD recovery.
