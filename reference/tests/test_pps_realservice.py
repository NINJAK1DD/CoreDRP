# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Freeze the observed numeric incompatibility; never tolerate or rewrite it."""
import json
from pathlib import Path
from fractions import Fraction
from coredrp_ref.miningcore_shadow import compare,digest,pps_liability
from test_miningcore_shadow import example


def test_real_service_numeric_contract_is_exact_and_legacy_stays_a_mismatch():
    case=json.loads((Path(__file__).parent/'fixtures/pps-regtest-arithmetic.json').read_text())
    exact=pps_liability(case['reward_basis_satoshis'],case['assigned_binary64'],case['network_binary64'],case['retained_percent'])
    assert exact==case['pps_liability_v1_per_share']
    assert (Fraction(exact)-Fraction(case['legacy_decimal_per_share']))*case['share_count']==Fraction(case['aggregate_reference_minus_legacy'])
    export=example();data=export['data'];data['policy']['retained_percent']=case['retained_percent']
    for row in data['shares']+data['credits']:
        row.update(difficulty_bits=case['assigned_binary64'],networkdifficulty_bits=case['network_binary64'],rewardbasissatoshis=case['reward_basis_satoshis'])
    data['credits'][0]['calculatedamount']=case['legacy_decimal_per_share']
    data['credits'][0]['creditedamount']=data['balance_changes'][0]['amount']='10.645161290322'
    export['sha256']=digest(data);report=compare(export)
    assert not report['accounting_matches'] and not report['eligible']
    assert [r['reason'] for r in report['differences']]==['calculated_liability_mismatch']
    assert report['differences'][0]['reference']==exact
    # Separate synthetic version-1 scenario, never a rewrite of retained evidence.
    migrated=json.loads(json.dumps(export));migrated['data']['credits'][0]['calculatedamount']=exact
    migrated['sha256']=digest(migrated['data']);report=compare(migrated)
    assert report['accounting_matches'] and not report['eligible']
    assert export['data']['credits'][0]['calculatedamount']==case['legacy_decimal_per_share']
