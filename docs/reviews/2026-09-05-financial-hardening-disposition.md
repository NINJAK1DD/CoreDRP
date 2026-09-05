# Financial hardening review disposition — 5 September 2026

Copyright © 2026 Rob Cooke · SPDX-License-Identifier: CC-BY-4.0

Baseline: `3c1eed1a2f4218966bb66038e5f88830598b4778` (merged PR #10).
Inputs: the current-head six-P1 review and the cumulative adversarial review through Round 8 and its AB2 correction.

## Current findings

| Finding | Disposition and evidence |
|---|---|
| P1-1 PPLNS/PPLNSBF cutoff arithmetic | Settlement-scheme §5 allocates PPLNSScoreV1/PPLNSBFScoreV1: one binary64 quotient, lossless exact rational score/accumulation, exact comparison, partial boundary and fail-closed overflow/underflow. Python and independent C# execute one-ULP cutoff, ties, subnormal, overflow, underfilled and equal-time examples. |
| P1-2 PPS unbound local configuration | Settlement-scheme §2/§6 bind resolved retained_reward_percentage and PPSLiabilityV1; exact input rationals and one truncation to scale 24. Parsed protobuf checks require PPS presence, reject non-PPS presence, wrong fee amount and ineligible coin/network. The allocated coin is bitcoin; additional Bitcoin-family coins need explicit future eligibility allocation. |
| P1-3 / AB2 opaque effect identity and aggregated-share ambiguity | Settlement-safety §6.1 defines EffectIdentityV1, one contribution per accounting UUID, exact destination/amount/source/contract binding, retained preimages, duplicate identity rejection and per-miner sum reconciliation. Two same-miner shares reconstruct in Python and C#. The AB2 addendum correctly says existing retained record bytes already permitted rehashing; this change additionally makes effect semantics independently checkable. |
| P1-4 pending temporal reconciliation absent from migration barrier | NoLiveDependencies explicitly blocks POLICY_RECONCILIATION_PENDING ranges/effects. SettlementSafe and SettlementPruneSafe also name it. Negative closure vector and executable status handling reject pending and unknown status. |
| P1-5 RELAY_REQUIRED bootstrap gap | Bootstrap allows NO_RELAY_REQUIRED only. Initial memberships must be staged before a later nonempty RELAY_REQUIRED activation; empty or unstaged activation is rejected. Bootstrap, clean setup and timing-boundary cases execute. |
| P1-6 scope / PoolId mapping | Miningcore §1.1 mandates exact UTF8(PoolConfig.Id) equality per projection/candidate namespace. Tests reject wrong pool, case, whitespace and Unicode aliasing. |
| AB1 sender admission can wedge immutable stream | Mining §8 requires durable activated authorization/contract/policy/membership evidence for every payout-effect scope before WAL or producer-sequence mutation. Missing/unknown/staged-only state fails locally. Stateful tests verify no partial primary admission, retry after repair, and idempotent replay after policy change. |
| P2 critical candidate reconciliation scope | Explicitly waiver-only in Profile 1.1 for 0x0201/0x0202; the share authority cannot reconcile them. Waiver preserves uncertainty, retention and migration blocks. No new authority is allocated. |
| Full-tuple settlement query/pagination | Settlement-scheme §5.1 freezes descending full-tuple exclusive cursor with immutable snapshot and RFC UUID ordering. Equal-time multi-page tests produce identical results for page sizes 1, 2, 3 and 100; timestamp-only pagination is an explicit negative control. |
| Authority incorporation hygiene | Top-level specification now explicitly incorporates the validator-authority registry. |

## Historical findings

The cumulative attachment is a history, not a list of simultaneously open blockers. Its later rounds expressly close earlier issues. The current tree retains those fixes and their regression gates:

| Historical group | Current coverage retained |
|---|---|
| C1–C4 document integrity | Canonical UTF-8 versioned spec, pointer-only unversioned file, complete numbered sections and integrity gates |
| W1–W14 wire/identity/negotiation | Validated integer widths, fixed UUID/hash lengths, empty-frame rejection, reserved fields, core event registry, split heartbeat types, bounded admin diagnostics, immutable epoch contracts, Goodbye, structurally nonrecursive projections and explicit relay/candidate identities |
| X1–X5 cryptography | Current independent Core hash corpus, parsed profile fixtures, boundary vectors, canonical UUID bytes and ADMIN construction |
| Y1–Y3 / Z1–Z2 / V1–V3 original state/clock/failure review | Normative reconnect precedence, whole-batch integrity/transaction semantics, certificate identity equality, lane-global checkpoints, durable WAL/idempotency and database-failure rules |
| T1–T5 / P1–P11 / Q1–Q8 | Layer stem self-tests, spec/registry integrity, full structural wire baseline, executable parsed payload/state failures, .NET target, error disposition consistency, Bitcoin SegWit and metrics gates |
| S1–S3 / U1–U6 / later V1–V2 | Realistic TLA+ mutation controls, current domain allocations, input-driven state cases, archived conflicting corpus, removed orphans, ordinary Buf breaking on both paths, structural/fingerprint checks and current labels |
| AA1–AA4 and PR #10's four threads | Multi-scope receiver checks, effective parameters, sorted multi-key policy vectors, removed Buf exception, explicit summary sentinel, exact multiplier, canonical component bytes and registered validator authority remain in place |
| Formal-model coverage observation (later V3) | Existing bounded model is retained; financial arithmetic is exercised in executable Python/.NET conformance, not claimed to be proven by that model. |

## Compatibility and implementation boundary

Core 1.1 protobuf files, field numbers, hash domains and Core cryptographic corpus do not change. Mining/Miningcore profile versions remain 1.1; pre-freeze completeness policy advances 2 → 3, Miningcore settlement policy 3 → 4, and settlement-scheme source grammar 2 → 3. New reference semantic and epoch-binding digests prevent silent negotiation with the prior financial behavior. Nonidentical financial contracts require NoLiveDependencies or a distinct scope; there is no implicit upgrade of old evidence or liabilities.

This repository is a specification and conformance suite, not a production Miningcore relay implementation. The normative integration changes and runnable algorithm/reference validators are implemented here. Production Miningcore SQL/payout handler changes belong to its integration work: do not reuse ReadSharesBeforeAsync, host-decimal cutoff calculation, live-config PPS validation or aliasing PoolId lookups unchanged. No production service or Miningcore repository is modified by this PR.

The reference suite covers the listed boundary and mutation cases. CI also runs the existing parsed protobuf, structural wire/Buf, independent .NET, TLA+ safety and realistic mutation gates. Passing conformance is not a claim that a deployed crash-safe relay or payout implementation has been tested.

## PR #11 follow-up review

- P1 stale no-relay policy: RequiredStagingSender now includes the durable lifetime AdmissionPolicyHolders set. Issuance is logged before delivery and serialized with transition preparation/activation. Offline holders block activation until exact staging acknowledgement; sender-side caps precede ACK and survive lost activation notices, restart and abort. Recorded scope skew covers nonmember holders without post-transition active clock scopes. Stateful conformance exercises stale/offline evidence, concurrent issuance, exact boundary, wrong ACK, restart, new activated member evidence and holder-set recheck.
- P2 duplicate effect UUID casing: participant duplicate keys use decoded UUID bytes. Regressions reject upper/lowercase duplicates, including different amounts, while a single uppercase spelling reconstructs the same bytes/digest.
