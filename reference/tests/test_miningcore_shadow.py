# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from coredrp_ref.miningcore_shadow import snapshot,compare,digest,SOURCE_REVISION
from coredrp_ref.storage import connect
from coredrp_ref.wire import Failure

START='2026-09-19T00:00:00Z';END='2026-09-20T00:00:00Z'

def policy(scope):return dict(scope=scope,scheme='PPS',coin='bitcoin',retained_percent='100',**{'from':START,'until':END})

def example():
    key='10000000-0000-4000-8000-000000000001'
    share=dict(accountingid=key,miner='alice',difficulty_bits='3ff0000000000000',networkdifficulty_bits='4000000000000000',rewardbasissatoshis=50000000,created=START)
    credit=dict(share,address='alice',calculatedamount='0.25',creditedamount='0.25');credit.pop('miner')
    change=dict(id=1,address='alice',amount='0.25',usage='PPS share credit',tags=['pps','pps-share:'+key.replace('-','')],created=START)
    data=dict(version=1,scope='btc1',scheme='PPS',from_time=START,until_time=END,policy=policy('btc1'),shares=[share],credits=[credit],balance_changes=[change])
    return dict(data=data,sha256=digest(data))


def test_matching_arithmetic_cannot_authorize_payout():
    result=compare(example())
    assert result['accounting_matches'] and result['reference_totals']=={'alice':'0.25'}
    assert result['shadow_only'] and result['eligible'] is False and len(result['blocked_reasons'])==3

@pytest.mark.parametrize('target,field,value,reason',[
    ('credits','calculatedamount','0.2','calculated_liability_mismatch'),
    ('credits','creditedamount','0.3','credited_amount_outside_precision_carry_bounds'),
    ('credits','address','mallory','credit_source_mismatch'),
    ('credits','difficulty_bits','4000000000000000','credit_source_mismatch'),
    ('balance_changes','amount','0.2','balance_credit_mismatch'),
    ('balance_changes','tags',['pps','pps-share:x','pps-share:y'],'ambiguous_balance_credit_tags'),
    ('shares','difficulty_bits','7ff0000000000000','invalid_liability_input'),
])
def test_each_difference_has_identity_and_reason(target,field,value,reason):
    export=example();export['data'][target][0][field]=value;export['sha256']=digest(export['data'])
    report=compare(export)
    assert not report['eligible'] and not report['accounting_matches']
    assert reason in [row['reason'] for row in report['differences']]

@pytest.mark.parametrize('missing,reason',[('shares','credit_without_retained_share'),('credits','share_without_pps_credit'),('balance_changes','balance_credit_count_mismatch')])
def test_missing_evidence_never_matches(missing,reason):
    export=example();export['data'][missing]=[];export['sha256']=digest(export['data'])
    result=compare(export)
    assert not result['accounting_matches'] and not result['eligible']
    assert result['differences'][0]['reason']==reason


def test_digest_tamper_and_duplicate_identity_rejected():
    export=example();export['data']['credits'][0]['calculatedamount']='9'
    with pytest.raises(Failure,match='DIGEST'):compare(export)
    export=example();export['data']['shares']*=2;export['sha256']=digest(export['data'])
    with pytest.raises(Failure,match='DUPLICATE'):compare(export)


def test_precision_difference_is_explicitly_unverified():
    export=example();data=export['data'];data['shares'][0]['networkdifficulty_bits']='4008000000000000';data['credits'][0]['networkdifficulty_bits']='4008000000000000'
    data['credits'][0]['calculatedamount']='0.166666666666666666666666'
    data['credits'][0]['creditedamount']=data['balance_changes'][0]['amount']='0.166666666667'
    export['sha256']=digest(data);result=compare(export)
    assert result['accounting_matches'] and not result['eligible']
    assert result['precision_differences'][0]['verified'] is False


def test_cli_compares_retained_export_without_database(tmp_path):
    source=tmp_path/'snapshot.json';source.write_text(json.dumps(example()));output=tmp_path/'report.json'
    args=[sys.executable,'-m','coredrp_ref.miningcore_shadow','compare','--input',str(source),'--output',str(output)]
    result=subprocess.run(args,capture_output=True,env=dict(os.environ,PYTHONPATH='reference'))
    assert result.returncode==0,result.stderr.decode()
    assert json.loads(output.read_text())['eligible'] is False
    assert subprocess.run(args,capture_output=True,env=dict(os.environ,PYTHONPATH='reference')).returncode==2

@pytest.fixture(scope='module')
def source_schema():
    dsn=os.environ.get('COREDRP_REF_DSN');assert dsn,'real PostgreSQL is required for source export tests'
    raw=(Path(__file__).parent/'fixtures/miningcore-createdb.sql').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='b39bc84e790c61dfc4d6bfdeefeedc2287a5cd6fb47dfde5c0f09c02bcc035ec'
    with connect(dsn) as db:
        # Byte-exact upstream schema; omit only SET ROLE in the disposable lab.
        db.execute(raw.decode().replace('SET ROLE miningcore;','',1))
    return dsn

@pytest.fixture
def source(source_schema):
    dsn=source_schema;scope='shadow'+uuid.uuid4().hex[:12];key=uuid.uuid4()
    with connect(dsn) as db:
        with db.transaction():
            db.execute('INSERT INTO public.share_accounting_groups VALUES(%s,1,%s,%s)',(key,'A'*64,START))
            db.execute('INSERT INTO public.shares(poolid,blockheight,difficulty,networkdifficulty,miner,ipaddress,accountingid,accountingrole,rewardbasissatoshis,created) VALUES(%s,100,1,2,\'alice\',\'private-address-not-exported\',%s,1,50000000,%s)',(scope,key,START))
            db.execute('INSERT INTO public.pps_share_credits VALUES(%s,%s,\'alice\',0.25,0.25,1,2,50000000,%s)',(scope,key,START))
            db.execute('INSERT INTO public.balance_changes(poolid,address,amount,usage,tags,created) VALUES(%s,\'alice\',0.25,\'PPS share credit\',%s,%s)',(scope,['pps','pps-share:'+key.hex],START))
    return dsn,scope,key


def test_real_schema_export_is_read_only_exact_and_scope_bound(source):
    dsn,scope,key=source
    export=snapshot(dsn,scope,START,END,policy(scope));data=export['data']
    assert data['source']['read_only']=='on' and data['source_schema_reviewed_at']==SOURCE_REVISION
    assert len(data['shares'])==len(data['credits'])==len(data['balance_changes'])==1
    assert data['shares'][0]['difficulty_bits']=='3ff0000000000000'
    assert 'private-address-not-exported' not in json.dumps(export)
    assert compare(export)['accounting_matches'] and not compare(export)['eligible']
    other=snapshot(dsn,'missing-scope',START,END,policy('missing-scope'))
    assert not compare(other)['accounting_matches']
    # A second capture does not mutate source data.
    second=snapshot(dsn,scope,START,END,policy(scope))
    for table in ('shares','credits','balance_changes'):assert data[table]==second['data'][table]


def test_real_ledger_difference_and_deleted_share_are_explained(source):
    dsn,scope,key=source
    with connect(dsn) as db:db.execute('UPDATE public.pps_share_credits SET calculatedamount=0.2 WHERE poolid=%s',(scope,))
    result=compare(snapshot(dsn,scope,START,END,policy(scope)))
    assert 'calculated_liability_mismatch' in [d['reason'] for d in result['differences']]
    with connect(dsn) as db:db.execute('DELETE FROM public.shares WHERE poolid=%s',(scope,))
    result=compare(snapshot(dsn,scope,START,END,policy(scope)))
    assert result['differences'][0]['reason']=='credit_without_retained_share'


def test_export_limit_rejects_instead_of_truncating(source,monkeypatch):
    import coredrp_ref.miningcore_shadow as adapter
    dsn,scope,key=source;monkeypatch.setattr(adapter,'MAX_ROWS',0)
    with pytest.raises(Failure,match='SHADOW_EXPORT_LIMIT'):snapshot(dsn,scope,START,END,policy(scope))


def test_snapshot_does_not_mix_concurrent_accounting_versions(source,monkeypatch):
    import psycopg
    dsn,scope,key=source;original=psycopg.Connection.execute;changed=False
    def execute(db,query,params=None,**kwargs):
        nonlocal changed
        if str(query).startswith('SELECT accountingid,address') and not changed:
            changed=True
            with connect(dsn) as writer:
                with writer.transaction():
                    original(writer,'UPDATE public.shares SET difficulty=2 WHERE poolid=%s',(scope,))
                    original(writer,'UPDATE public.pps_share_credits SET difficulty=2,calculatedamount=0.5,creditedamount=0.5 WHERE poolid=%s',(scope,))
                    original(writer,'UPDATE public.balance_changes SET amount=0.5 WHERE poolid=%s',(scope,))
        return original(db,query,params,**kwargs)
    monkeypatch.setattr(psycopg.Connection,'execute',execute)
    export=snapshot(dsn,scope,START,END,policy(scope))
    assert changed and compare(export)['reference_totals']=={'alice':'0.25'}
    assert compare(export)['accounting_matches']
    fresh=snapshot(dsn,scope,START,END,policy(scope))
    assert compare(fresh)['reference_totals']=={'alice':'0.5'} and compare(fresh)['accounting_matches']


def test_export_transaction_rejects_source_writes(source,monkeypatch):
    import psycopg
    dsn,scope,key=source;original=psycopg.Connection.execute;checked=False
    def execute(db,query,params=None,**kwargs):
        nonlocal checked
        if str(query).startswith('SELECT accountingid,miner') and not checked:
            checked=True
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                with db.transaction():original(db,'UPDATE public.shares SET difficulty=9 WHERE poolid=%s',(scope,))
        return original(db,query,params,**kwargs)
    monkeypatch.setattr(psycopg.Connection,'execute',execute)
    assert compare(snapshot(dsn,scope,START,END,policy(scope)))['accounting_matches'] and checked
