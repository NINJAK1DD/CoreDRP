# CoreDRP/1 ClockStateUpdate Registry — Draft 0.6 Profile Freeze

**Status:** Draft 0.6 normative registry  
**Wire:** Core 1.1

This registry is incorporated through `coredrp-v1-draft06-contracts.md` and defines the complete accepted-state matrix, effective multi-scope reducer, freshness rules, UNKNOWN grace, BAD latching and recovery.

## 1. Effective multi-scope lane policy

For one authenticated sender/lane, let `A` be active Mining scopes. When non-empty, compute each effective parameter independently as the minimum across `A`:

- permitted skew;
- max wall-clock step;
- probe interval;
- sender processing maximum;
- evidence expiry;
- UNKNOWN grace.

No tuple ordering, maximum, average, first-scope rule, or per-scope lane state is conforming. Scope-set changes reclassify existing evidence immediately against the new effective policy.

## 2. Common structural rules

Every accepted update requires non-zero strictly increasing stream-local generation, a non-UNSPECIFIED state/reason, valid lifetime, exact effective skew, paired offset bounds, and valid current-stream probe identity where required. Structural violations are `MALFORMED_FRAME`; semantically contradictory combinations are `CLOCK_CONTRACT_VIOLATION`.

Let `S = effective_permitted_skew_ms` and `I=[lower,upper]`.

- GOOD interval: `-S <= lower <= upper <= S`;
- BAD interval: `upper < -S OR lower > S`;
- UNKNOWN interval: otherwise.

## 3. Exhaustive state/reason matrix

| State | Reason | probe | bounds | Required relation | Result |
|---|---|---|---|---|---|
| GOOD | PROBE_EVIDENCE | required | both | GOOD interval | ACCEPT |
| GOOD | any other reason | any | any | cannot prove GOOD | `CLOCK_CONTRACT_VIOLATION` |
| BAD | PROBE_EVIDENCE | required | both | BAD interval | ACCEPT |
| BAD | RECEIVER_WALL_STEP | absent | both or neither | wall step itself is authoritative BAD; present interval not wholly GOOD | ACCEPT |
| BAD | SENDER_PROCESSING_LIMIT | required | both or neither | referenced sender processing duration exceeded effective processing maximum; present interval not wholly GOOD | ACCEPT |
| BAD | EVIDENCE_EXPIRED | any | any | expiry alone is not new BAD evidence | `CLOCK_CONTRACT_VIOLATION` |
| UNKNOWN | EVIDENCE_EXPIRED | absent | absent | no fresh bound evidence | ACCEPT |
| UNKNOWN | PROBE_EVIDENCE | required | both | UNKNOWN interval | ACCEPT |
| UNKNOWN | RECEIVER_WALL_STEP | any | any | wall step is BAD | `CLOCK_CONTRACT_VIOLATION` |
| UNKNOWN | SENDER_PROCESSING_LIMIT | any | any | processing-limit classification is deterministically BAD | `CLOCK_CONTRACT_VIOLATION` |

**Deterministic processing-limit rule:** when the receiver can verify that sender processing duration for a referenced probe exceeded `effective_probe_processing_max_ms`, the wire state MUST be BAD with reason `SENDER_PROCESSING_LIMIT`. UNKNOWN is not conforming for that same observation. If processing duration cannot be established, the receiver MUST NOT use `SENDER_PROCESSING_LIMIT`; unusable/ambiguous offset evidence is classified by PROBE_EVIDENCE/UNKNOWN or by expiry as applicable.

Thus two conforming receivers observing the same processing-limit fact cannot choose different BAD/UNKNOWN safety consequences.

## 4. Freshness and delayed delivery

The sender records monotonic `probe_response_sent_mono` for each probe. On a probe-backed update:

`probe_age_ms = now_mono - probe_response_sent_mono`.

If `probe_age_ms >= effective_evidence_expiry_ms`, the evidence is stale and establishes no fresh state. Otherwise:

`accepted_remaining_lifetime_ms = min(evidence_valid_for_ms, effective_evidence_expiry_ms - probe_age_ms)`.

Receiver-advertised lifetime may shorten but never extend freshness beyond sender-observed probe age.

## 5. Replay and UNKNOWN grace

Generation is stream-local and strictly increasing. Replayed/stale generation is ignored without changing state or timers.

UNKNOWN uses one monotonic `unknown_since_mono` per episode. Repeated UNKNOWN updates, reconnects, delayed expiry, or stale generations MUST NOT move it forward. Grace ends only on genuine GOOD or BAD/RECOVERING transition.

## 6. BAD latch and recovery

Expiry of BAD yields local RECOVERING, not ordinary UNKNOWN grace. BAD/RECOVERING -> GOOD requires trusted UTC not behind durable event time, three fresh GOOD probe observations, first/last spanning at least one effective probe interval, and no intervening BAD. Reconnect does not clear the latch.

## 7. Admission/checkpoint gate

BAD and RECOVERING always block covered Mining admission/checkpoint advancement. UNKNOWN may admit only during its one non-extending grace episode where Mining policy allows, but UNKNOWN never advances trusted completeness checkpoints.

Local wall-clock step greater than effective max step is BAD. Verified sender processing duration greater than effective processing maximum is BAD as specified above.

## 8. Conformance requirements

The corpus MUST exercise GOOD, delayed/expired GOOD, BAD probe, UNKNOWN overlap, wall step, deterministic BAD processing-limit classification, rejection of UNKNOWN/SENDER_PROCESSING_LIMIT, malformed bound presence, stale generation, UNKNOWN non-extension, BAD latch/recovery, and multi-scope reduction.
