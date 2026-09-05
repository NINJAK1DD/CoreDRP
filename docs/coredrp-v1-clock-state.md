# CoreDRP/1 ClockStateUpdate Registry — Draft 0.6 Freeze Completion

**Status:** Draft 0.6 normative registry  
**Wire:** Core 1.1

This registry is incorporated through normative `coredrp-v1-draft06-contracts.md`, which is itself incorporated by Section 1 of `CoreDRP-1-SPEC-0.6.md`. It defines the complete accepted-state matrix, effective lane-policy reducer, freshness rules, UNKNOWN-grace semantics, BAD latching and recovery for `ClockStateUpdate`.

## 1. Effective multi-scope lane policy

For one authenticated sender/lane, let `A` be the set of Mining scopes that are currently active under the persisted epoch contracts and temporal policy. When `A` is non-empty, the effective lane clock policy is computed independently per parameter as the minimum across all active scopes:

- `effective_permitted_skew_ms = min(scope.permitted_clock_skew_ms)`;
- `effective_max_clock_step_ms = min(scope.max_clock_step_ms)`;
- `effective_probe_interval_ms = min(scope.probe_interval_ms)`;
- `effective_probe_processing_max_ms = min(scope.probe_processing_max_ms)`;
- `effective_evidence_expiry_ms = min(scope.evidence_expiry_ms)`;
- `effective_unknown_grace_ms = min(scope.unknown_grace_ms)`.

This element-wise minimum is the exact meaning of “strictest active clock policy”. Implementations MUST NOT use tuple ordering, first-scope wins, maximum, average, or scope-local clock states on a shared lane.

If no active Mining scope exists on a lane, the Mining clock gate is inactive for Mining admission/checkpoint purposes; Core control traffic remains subject to Core framing/authentication rules.

A change to the active scope set recomputes the effective policy immediately at its effective temporal boundary. A newly stricter policy can invalidate otherwise fresh evidence; evidence is reclassified against the new effective values before further covered admission or checkpoint advancement.

## 2. Common structural rules

For every accepted update:

- `observation_generation` MUST be non-zero and strictly greater than the last accepted generation in the current authenticated stream;
- generation state resets only after a successful new `ServerHello`; generations are never compared across streams;
- `state` MUST be GOOD, BAD, or UNKNOWN; UNSPECIFIED is `MALFORMED_FRAME`;
- `reason` MUST be PROBE_EVIDENCE, EVIDENCE_EXPIRED, RECEIVER_WALL_STEP, or SENDER_PROCESSING_LIMIT; UNSPECIFIED is `MALFORMED_FRAME`;
- `evidence_valid_for_ms` MUST be in `1..effective_evidence_expiry_ms`;
- `effective_permitted_skew_ms` MUST equal the value produced by Section 1 exactly;
- when both offset bounds are present, `lower_offset_ms <= upper_offset_ms`;
- a present `probe_id` MUST identify a valid current-stream observation and MUST NOT have been consumed, expired, or issued on a previous stream;
- integer/range/presence violations are `MALFORMED_FRAME`; semantically contradictory but structurally valid combinations are `CLOCK_CONTRACT_VIOLATION`.

Let `S = effective_permitted_skew_ms` and `I = [lower_offset_ms, upper_offset_ms]` when both bounds are present.

## 3. Exhaustive state/reason matrix

| State | Reason | `probe_id` | lower/upper bounds | Required semantic relation | Result |
|---|---|---|---|---|---|
| GOOD | PROBE_EVIDENCE | REQUIRED | BOTH REQUIRED | `-S <= lower <= upper <= S` | ACCEPT |
| GOOD | EVIDENCE_EXPIRED | any | any | expired evidence cannot assert GOOD | `CLOCK_CONTRACT_VIOLATION` |
| GOOD | RECEIVER_WALL_STEP | any | any | wall-step evidence cannot assert GOOD | `CLOCK_CONTRACT_VIOLATION` |
| GOOD | SENDER_PROCESSING_LIMIT | any | any | processing-limit evidence cannot prove GOOD | `CLOCK_CONTRACT_VIOLATION` |
| BAD | PROBE_EVIDENCE | REQUIRED | BOTH REQUIRED | `upper < -S` OR `lower > S` | ACCEPT |
| BAD | RECEIVER_WALL_STEP | MUST BE ABSENT | BOTH OPTIONAL, but either both or neither | if present, interval MUST NOT be wholly GOOD; wall-step detection itself is authoritative BAD evidence | ACCEPT |
| BAD | SENDER_PROCESSING_LIMIT | REQUIRED | BOTH OPTIONAL, but either both or neither | sender processing exceeded bound for the referenced probe; any present interval MUST NOT be wholly GOOD | ACCEPT |
| BAD | EVIDENCE_EXPIRED | any | any | expiry alone is UNKNOWN/RECOVERING, never new BAD evidence | `CLOCK_CONTRACT_VIOLATION` |
| UNKNOWN | EVIDENCE_EXPIRED | MUST BE ABSENT | MUST BE ABSENT | no fresh bound evidence remains | ACCEPT |
| UNKNOWN | PROBE_EVIDENCE | REQUIRED | BOTH REQUIRED | interval overlaps the policy boundary: NOT wholly GOOD and NOT wholly BAD | ACCEPT |
| UNKNOWN | SENDER_PROCESSING_LIMIT | REQUIRED | BOTH OPTIONAL, but either both or neither | insufficient trustworthy bound; any present interval MUST NOT be wholly GOOD | ACCEPT |
| UNKNOWN | RECEIVER_WALL_STEP | any | any | receiver wall-step is definitive BAD, not UNKNOWN | `CLOCK_CONTRACT_VIOLATION` |

`any` above means the row is contradictory regardless of optional-field presence; implementations MUST NOT reinterpret it into another state.

## 4. Presence and interval rules

- Lower and upper bounds are a pair. Exactly one present is `MALFORMED_FRAME`.
- GOOD always carries both bounds and a current-stream `probe_id`.
- BAD/PROBE_EVIDENCE always carries both bounds and a current-stream `probe_id`.
- UNKNOWN/PROBE_EVIDENCE always carries both bounds and a current-stream `probe_id`.
- UNKNOWN/EVIDENCE_EXPIRED carries neither bounds nor `probe_id`.
- RECEIVER_WALL_STEP MUST NOT carry `probe_id`; bounds are diagnostic only and, if used, MUST be a complete pair.
- SENDER_PROCESSING_LIMIT requires the referenced `probe_id`; bounds are optional diagnostics but, if used, MUST be a complete pair.

For a complete interval `I`:

- `GOOD_INTERVAL` iff `-S <= lower <= upper <= S`;
- `BAD_INTERVAL` iff `upper < -S OR lower > S`;
- `UNKNOWN_INTERVAL` otherwise.

PROBE_EVIDENCE rows MUST use the state corresponding exactly to that classification.

## 5. Probe-backed freshness and delayed delivery

For each outstanding probe ID, the sender durably/in-memory associates a local monotonic timestamp `probe_response_sent_mono` captured immediately after the corresponding `ClockProbeResponse` is emitted. This local monotonic age is authoritative for how old probe-backed evidence is when a later `ClockStateUpdate` arrives.

For a probe-backed update received at monotonic time `now_mono`:

`probe_age_ms = now_mono - probe_response_sent_mono` using checked monotonic arithmetic.

The sender computes:

`remaining_from_policy_ms = effective_evidence_expiry_ms - probe_age_ms`.

If `probe_age_ms >= effective_evidence_expiry_ms`, the probe-backed update is already expired and MUST NOT establish GOOD/BAD/UNKNOWN evidence. It is discarded as stale evidence and local state transitions as if no fresh observation had arrived (including BAD-latch rules below).

Otherwise:

`accepted_remaining_lifetime_ms = min(evidence_valid_for_ms, remaining_from_policy_ms)`.

The update expires locally after that remaining lifetime. The receiver-advertised `evidence_valid_for_ms` may shorten freshness but can never extend it beyond the sender-observed age of the probe.

Equivalent invariant:

`probe_age_ms + accepted_remaining_lifetime_ms <= effective_evidence_expiry_ms`.

This prevents a delayed GOOD from receiving a fresh full lifetime after network/stream stall.

Non-probe reasons are not allowed to manufacture probe freshness. Their lifetime still cannot exceed the effective evidence-expiry policy and is governed by their state/reason row.

## 6. Stream replay and generation

An update with generation less than or equal to the last accepted generation in the same stream is stale/replayed and MUST be ignored without changing clock state or grace timers.

A replacement stream starts a fresh generation namespace at 1. The first update in the new stream is compared only against generation zero, not the prior stream's terminal generation.

Changing streams does not itself create GOOD evidence or reset a latched BAD/RECOVERING condition unless the recovery rules are satisfied.

## 7. UNKNOWN grace non-extension

The implementation maintains local monotonic `unknown_since_mono` for the current UNKNOWN episode.

- On transition from non-UNKNOWN into ordinary UNKNOWN, set `unknown_since_mono = now_mono` once.
- While already UNKNOWN, subsequent UNKNOWN updates, delayed EVIDENCE_EXPIRED messages, stale generations, reconnects, or equivalent no-fresh-evidence indications MUST NOT move `unknown_since_mono` forward.
- UNKNOWN grace remaining is `max(0, effective_unknown_grace_ms - (now_mono - unknown_since_mono))`.
- The UNKNOWN episode ends only on a genuine accepted GOOD recovery or transition to BAD/RECOVERING.
- Entering GOOD clears `unknown_since_mono`.
- Entering BAD clears ordinary UNKNOWN grace and establishes the BAD latch.

Thus repeated/delayed UNKNOWN frames cannot restart the grace budget.

## 8. Expiry, BAD latch and recovery

Local monotonic expiry of previously accepted GOOD produces ordinary UNKNOWN and starts one UNKNOWN episode if no newer state exists.

Expiry of accepted BAD does **not** produce ordinary UNKNOWN grace. It produces RECOVERING, a local derived state that continues to block covered admission and checkpoint advancement.

RECOVERING is not a wire enum value. It is local protocol state derived from prior BAD evidence plus recovery observations.

BAD/RECOVERING -> GOOD requires all of:

- trusted UTC is not behind durable last event time;
- at least three fresh accepted GOOD/PROBE_EVIDENCE observations;
- every qualifying observation passes the delayed-delivery freshness rule in Section 5;
- first and last qualifying observations span at least one `effective_probe_interval_ms`;
- no intervening accepted BAD occurs.

A new BAD resets qualifying GOOD count/span. Reconnect does not clear the BAD latch.

## 9. Admission and checkpoint gate

Covered Mining admission/checkpoint advancement requires the effective lane clock state permitted by Mining policy. BAD and RECOVERING always block. UNKNOWN may admit during the one non-extending configured grace episode if the bound Mining completeness policy allows it, but UNKNOWN never advances trusted completeness checkpoints.

Any local wall-clock step greater than `effective_max_clock_step_ms` is BAD. Sender processing duration greater than `effective_probe_processing_max_ms` is classified per the matrix and can never prove GOOD.

## 10. Conformance corpus

The current conformance corpus MUST exercise at least:

- accepted GOOD probe;
- rejected GOOD with stale probe age;
- accepted BAD probe;
- UNKNOWN overlap;
- ordinary evidence expiry;
- delayed GOOD whose `probe_age + advertised_lifetime` exceeds policy and is shortened/rejected appropriately;
- UNKNOWN update that does not restart grace;
- receiver wall step;
- sender processing limit;
- malformed one-bound presence;
- invalid probe presence;
- stale generation;
- new-stream generation reset without clearing BAD latch;
- BAD expiry latch;
- BAD recovery with insufficient and sufficient GOOD observations;
- multi-scope reducer where different scopes are strictest for different parameters.
