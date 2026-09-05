#!/usr/bin/env python3
from pathlib import Path
import json

R = Path(__file__).resolve().parents[1]
D = json.loads((R / 'docs/coredrp-v1-policy-clock-vectors.json').read_text())


def verify_bootstrap(x):
    if not x.get('prior_policy', False):
        valid = (
            x['generation'] == 1
            and x['action'] == 'COMPLETENESS_MODE_CHANGE'
            and x.get('old_mode') == 'NO_POLICY'
            and x.get('new_mode') == 'NO_RELAY_REQUIRED'
            and x['effective_unix_ms'] == x['origin_unix_ms']
            and x.get('required_staging_senders', []) == []
        )
        if not valid:
            return 'ADMIN_ACTION_CONFLICT'
        assert x['expected_frontier'] == x['origin_unix_ms'] - 1
        return 'ACCEPT_BOOTSTRAP'
    if x['generation'] < 2:
        return 'ADMIN_ACTION_CONFLICT'
    limit = x['payout_safe_through'] + x['clock_uncertainty_ms']
    return 'ACCEPT' if x['effective_unix_ms'] > limit else 'ADMIN_ACTION_CONFLICT'


def interval_class(x):
    lo, hi = x.get('lower'), x.get('upper')
    if lo is None or hi is None:
        return None
    s = x['bound_skew_ms']
    if -s <= lo <= hi <= s:
        return 'GOOD'
    if hi < -s or lo > s:
        return 'BAD'
    return 'UNKNOWN'


def verify_clock_update(x):
    generation = x['generation']
    last = 0 if x.get('new_stream') else x.get('last_generation', 0)
    if generation == 0:
        return ('MALFORMED_FRAME', None)
    if generation <= last:
        return ('IGNORE', None)

    valid_for = x['valid_for_ms']
    expiry = x['effective_expiry_ms']
    if not 1 <= valid_for <= expiry:
        return ('MALFORMED_FRAME', None)
    if x['reported_skew_ms'] != x['bound_skew_ms']:
        return ('CLOCK_CONTRACT_VIOLATION', None)

    lo, hi = x.get('lower'), x.get('upper')
    if (lo is None) != (hi is None):
        return ('MALFORMED_FRAME', None)
    if lo is not None and lo > hi:
        return ('MALFORMED_FRAME', None)
    if x.get('probe_present') and not x.get('probe_valid'):
        return ('MALFORMED_FRAME', None)

    state, reason = x['state'], x['reason']
    probe = x.get('probe_present', False)
    bounds = lo is not None
    cls = interval_class(x)

    # Deterministic processing-limit classification: verified overrun is BAD.
    if reason == 'SENDER_PROCESSING_LIMIT':
        if not probe:
            return ('MALFORMED_FRAME', None)
        if x.get('processing_exceeded') is not True:
            return ('CLOCK_CONTRACT_VIOLATION', None)
        if state != 'BAD':
            return ('CLOCK_CONTRACT_VIOLATION', None)
        if bounds and cls == 'GOOD':
            return ('CLOCK_CONTRACT_VIOLATION', None)
        return ('BAD', valid_for)

    if reason == 'RECEIVER_WALL_STEP':
        if probe:
            return ('MALFORMED_FRAME', None)
        if state != 'BAD':
            return ('CLOCK_CONTRACT_VIOLATION', None)
        if bounds and cls == 'GOOD':
            return ('CLOCK_CONTRACT_VIOLATION', None)
        return ('BAD', valid_for)

    if reason == 'EVIDENCE_EXPIRED':
        if state != 'UNKNOWN':
            return ('CLOCK_CONTRACT_VIOLATION', None)
        if probe or bounds:
            return ('MALFORMED_FRAME', None)
        return ('UNKNOWN', valid_for)

    if reason != 'PROBE_EVIDENCE':
        return ('MALFORMED_FRAME', None)
    if not probe or not bounds:
        return ('MALFORMED_FRAME', None)

    if state == 'GOOD' and cls != 'GOOD':
        return ('CLOCK_CONTRACT_VIOLATION', None)
    if state == 'BAD' and cls != 'BAD':
        return ('CLOCK_CONTRACT_VIOLATION', None)
    if state == 'UNKNOWN' and cls != 'UNKNOWN':
        return ('CLOCK_CONTRACT_VIOLATION', None)
    if state not in {'GOOD', 'BAD', 'UNKNOWN'}:
        return ('MALFORMED_FRAME', None)

    age = x.get('probe_age_ms', 0)
    if age >= expiry:
        return ('STALE_EVIDENCE', None)
    remaining = min(valid_for, expiry - age)
    assert age + remaining <= expiry
    return (state, remaining)


def verify_unknown_grace(x):
    prev_state = x['previous_state']
    prev_since = x['previous_unknown_since_mono']
    now = x['now_mono']
    grace = x['unknown_grace_ms']
    since = now if prev_state != 'UNKNOWN' or prev_since is None else prev_since
    remaining = max(0, grace - (now - since))
    return since, remaining


def verify_bad_recovery(x):
    if x['previous_state'] == 'BAD' and x.get('evidence_expired'):
        return 'RECOVERING'
    return 'GOOD' if (
        x['fresh_good_count'] >= 3
        and x['spans_probe_interval']
        and x['utc_not_behind']
    ) else 'RECOVERING'


def verify():
    assert 'current temporal bootstrap and ClockStateUpdate lifecycle vectors' in D['format']

    for x in D['bootstrap_cases']:
        assert verify_bootstrap(x) == x['expected'], x

    for x in D['clock_update_cases']:
        state, remaining = verify_clock_update(x)
        assert state == x['expected_state'], x
        if 'expected_remaining_ms' in x:
            assert remaining == x['expected_remaining_ms'], x

    for x in D['unknown_grace_cases']:
        since, remaining = verify_unknown_grace(x)
        assert since == x['expected_unknown_since_mono'], x
        assert remaining == x['expected_remaining_ms'], x

    for x in D['bad_recovery_cases']:
        assert verify_bad_recovery(x) == x['expected'], x

    for x in D['multi_scope_reducer_cases']:
        scopes = x['scopes']
        got = {key: min(s[key] for s in scopes) for key in ('skew','step','probe','processing','expiry','grace')}
        assert got == x['expected'], x

    print('CoreDRP Draft 0.6 temporal bootstrap and stateful clock lifecycle vectors: OK')


if __name__ == '__main__':
    verify()
