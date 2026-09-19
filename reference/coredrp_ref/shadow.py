# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Offline one-scope PPLNS shadow comparison using retained accepted fixtures.

No payout writes or daemon calls. This is the bridge for a later read-only
Miningcore export adapter, not a claim of live Mining profile support.
"""
import json,sys
from pathlib import Path
from fractions import Fraction
from .storage import connect
from .wire import require,H
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from audit_evidence import audit_retained
from financial_semantics import decimal,amount
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory

def accounting_class():
    from profiles.miningcore.coredrp_miningcore_v1_pb2 import MiningcoreAccountingShareEvent
    return MiningcoreAccountingShareEvent

def compare(dsn,case,baseline,evidence):
    # Evidence comes from the isolated scenario. No boolean/row in this harness
    # can authorize production payment; every result is explicitly shadow-only.
    safe=(evidence['mode']=='RELAY_REQUIRED' and evidence['membership_from']<=evidence['round_start']
          and evidence['policy_staged'] and evidence['clock']=='GOOD'
          and evidence['checkpoint']>=evidence['block_boundary']+2*evidence['skew']
          and not evidence['uncertainties'])
    expected={k:tuple(v) for k,v in case['expected'].items()}
    result,dust,digest=audit_retained(case['bundle'],case['sha256'],case['bundle']['summary_hash'],accounting_class(),'btc1',1,case['factor'],expected)
    totals={}
    for miner,value in result.values():totals[miner]=totals.get(miner,Fraction(0))+decimal(value)
    totals={k:amount(v) for k,v in totals.items()}
    differences=[dict(miner=k,baseline=baseline.get(k,'0'),reference=totals.get(k,'0'),reason='allocation differs; inspect accepted source, cutoff, adjustment and scale-24 rounding') for k in sorted(set(baseline)|set(totals)) if decimal(baseline.get(k,'0'))!=decimal(totals.get(k,'0'))]
    report=dict(shadow_only=True,scope='btc1',scheme='PPLNS',eligible=safe and not differences,blocked_reasons=([] if safe else ['incomplete policy/checkpoint/clock/uncertainty evidence'])+(['unexplained accounting differences'] if differences else []),differences=differences,totals=totals,dust=dust,bundle_digest=digest)
    with connect(dsn) as db:
        with db.transaction():
            db.execute('SET LOCAL synchronous_commit=on')
            db.execute('CREATE TABLE IF NOT EXISTS coredrp_ref.shadow_reports (digest bytea PRIMARY KEY, report jsonb NOT NULL)')
            raw=json.dumps(report,sort_keys=True)
            db.execute('INSERT INTO coredrp_ref.shadow_reports VALUES(%s,%s::jsonb) ON CONFLICT DO NOTHING',(H(raw.encode()),raw))
    return report

def fixture(dsn):
    case=json.loads((ROOT/'docs/coredrp-v1-review2-vectors.json').read_text())['audits'][0]
    # Baseline is explicit application-accounting export shape, never calculated
    # by the reference algorithm to make the comparison tautologically succeed.
    baseline={'miner2':'0.45','miner3':'0.45'}
    evidence=dict(mode='RELAY_REQUIRED',membership_from=0,round_start=0,policy_staged=True,clock='GOOD',checkpoint=5002,block_boundary=1002,skew=2000,uncertainties=[])
    return case,baseline,evidence

if __name__=='__main__':
    import os
    dsn=os.environ['COREDRP_REF_DSN'];print(json.dumps(compare(dsn,*fixture(dsn)),indent=2))
