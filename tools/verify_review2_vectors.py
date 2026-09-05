#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Regression corpus for the reviews of ffacfa1. No network or mutable settings."""
import copy,hashlib,json,struct
from pathlib import Path
from fractions import Fraction
from request_encodings import encode,admission,admin_body,admin_preimage,validate_admin_body,accept_group,group_digest
from financial_semantics import *
from verify_policy_clock_vectors import verify_clock_update
from verify_accounting_schema3_safety import A,strict_accounting
from audit_evidence import audit,audit_retained,event_hash
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-review2-vectors.json').read_text())
H=lambda b:hashlib.sha256(b).hexdigest()
def rejects(f,*a,**kw):
    try:f(*a,**kw)
    except ValueError:return
    raise AssertionError('invalid input accepted')
for c in D['requests']:
    r=encode(c['kind'],c['request']);p=admission(c['lane'],c['event_type'],c['scope'],c['kind'],c['request'])
    assert r.hex()==c['request_hex'] and p.hex()==c['preimage_hex'] and H(p)==c['sha256']
    rejects(encode,c['kind'],dict(c['request'],created_unix_ms=1234))
    # Every caller field binds identity, including absent/present-empty metadata.
    if c['event_type']==512:
        for key,v in [('reward_basis_satoshis',1001),('scope',b'other'.hex()),('accounting_id','ff'*16),('pps_calculated_amount','0.1')]:
            x=copy.deepcopy(c['request']);x['primary'][key]=v
            assert encode(c['kind'],x)!=r
    elif c['event_type']==513:
        # Codec-only array/presence mutations; consensus validity is a separate gate.
        x=copy.deepcopy(c['request']);x['recipients']=[dict(address=None,script_pub_key='51',amount_satoshis=1),dict(address='recipient',script_pub_key='52',amount_satoshis=2)]
        arr=encode(c['kind'],x);x['recipients'].reverse();assert encode(c['kind'],x)==arr
        x['recipients'][1]['address']='';assert encode(c['kind'],x)!=arr
        x=copy.deepcopy(c['request']);x['consensus_commitments']*=2;rejects(encode,c['kind'],x)
    else:
        x=dict(c['request'],last_attempt_unix_ms=1001);assert encode(c['kind'],x)!=r
pair=D['requests'][1]['request'];swapped=dict(primary=pair['paired'],paired=pair['primary'])
assert encode('MiningcoreAccountingShareRequestV1',pair)!=encode('MiningcoreAccountingShareRequestV1',swapped)
for c in D['admin']:
    action=c['action'];fields=c['fields'];b=admin_body(action,fields);p=admin_preimage(action,fields)
    assert b.hex()==c['canonical_body_hex'] and p.hex()==c['preimage_hex'] and H(p)==c['sha256']
    assert validate_admin_body(action,b)==b
    for ids in ([1,1]+list(range(3,len(fields)+1)),[2,1]+list(range(3,len(fields)+1))):
        x=copy.deepcopy(fields)
        for f,i in zip(x,ids):f['id']=i
        rejects(admin_body,action,x)
    # Field 2 TLV: 8-byte uint64 replaced by 4-byte value, framing remains consistent.
    wrong=b[:28]+(4).to_bytes(4,'big')+b[36:40]+b[40:]
    rejects(validate_admin_body,action,wrong)
    # Duplicate/descending IDs in incoming raw TLV are rejected without sorting.
    rejects(validate_admin_body,action,b[:26]+b'\0\1'+b[28:])
    rejects(validate_admin_body,action,b[:4]+b'\0\2'+b[6:26]+b'\0\1'+b[28:])
policy=D['activated_policy'];assert encode(policy['kind'],policy['record']).hex()==policy['record_hex']
assert H(encode(policy['kind'],policy['record']))==policy['sha256']
for k,v in [('receiver','09'*16),('incarnation','09'*16),('sender','09'*16),('scope','62'),('generation',4),('valid_from',1001),('valid_until',None),('mode',2),('mining_contract','33'*32),('miningcore_contract',None),('admin_id','09'*16),('admin_digest','33'*32),('state_version',1)]:
    assert H(encode(policy['kind'],dict(policy['record'],**{k:v})))!=policy['sha256']
# All-history admission guard, including after ACK pruning and restart. This reference
# deliberately uses the conservative rule even for continuing members.
p=dict(activated=True,authorized=True,contract=True,mode='NO_RELAY_REQUIRED',member=False,generation=1,**{'from':0,'until':3000})
for mode in ('NO_RELAY_REQUIRED','RELAY_REQUIRED'):
 for event_time in (999,1000,1001):
  sender={'policies':{'aux':dict(p,mode=mode,member=True)},'wal':[],'outcomes':{},'admission_history_known':True}
  admit(sender,'old',['aux'],event_time);sender['wal'].clear();sender=copy.deepcopy(sender)
  pending={'generation':2,'effective':1000,'digest':'d'}
  if event_time<1000:assert stage_withdrawal(sender,'aux',pending)==(2,'d')
  else:rejects(stage_withdrawal,sender,'aux',pending)
  assert (2,1000) in sender['admission_caps']['aux']
  rejects(admit,sender,'new',['aux'],1000)
  # A later cutoff works; draining history alone never changed the recorded max.
  assert stage_withdrawal(sender,'aux',dict(pending,generation=3,effective=1002))==(3,'d')
unknown={'wal':[]};rejects(stage_withdrawal,unknown,'aux',pending)
for tm in (999,1000,1001):
 receiver={'mode':'NO_RELAY_REQUIRED','holders':{'holder'},'pending':None,'committed_history_known':True,'committed_through':{('holder','aux'):tm}}
 prepare_required(receiver,['member'],1000,2,'d')
 for who in ('holder','member'):acknowledge_required(receiver,who,(2,'d'))
 if tm<1000:commit_required(receiver)
 else:rejects(commit_required,receiver);assert receiver['mode']=='NO_RELAY_REQUIRED'
# Original identity replays only once; distinct event, sender, epoch, lane, sequence,
# relay UUID or group digest cannot re-use a global accounting UUID after pruning.
req=D['requests'][1]['request'];aid=req['primary']['accounting_id'];digest=group_digest(aid,req,1000,b'payload')
ledger={};identity=('sender','epoch',0,1,'relay')
assert accept_group(ledger,aid,identity,digest)=='COMMIT_EFFECTS'
assert accept_group(ledger,aid.upper(),identity,digest)=='REPLAY_NO_EFFECT'
for i,v in enumerate(('other','new-epoch',1,2,'new-relay')):
 x=list(identity);x[i]=v;before=copy.deepcopy(ledger);rejects(accept_group,ledger,aid,tuple(x),digest);assert ledger==before
rejects(accept_group,ledger,aid,identity,b'x'*32)
assert accept_group(ledger,'ee'*16,identity,digest)=='COMMIT_EFFECTS' # uniqueness of Core identity is separately enforced by Core
# Recompute settlement amounts from retained original protobuf, not payout hashes.
for c in D['audits']:
 b=c['bundle'];expected={k:tuple(v) for k,v in c['expected'].items()}
 for e in b['events']:
  m=A();m.ParseFromString(bytes.fromhex(e['payload']));assert strict_accounting(m,e['event_time'],bytes.fromhex(e['scope']))
 def check(x):return audit(x,A,'btc1',c['scheme'],c['factor'],expected,finder_percentage=b['inputs']['finder_percentage'])
 assert audit_retained(b,c['sha256'],b['summary_hash'],A,'btc1',c['scheme'],c['factor'],expected,finder_percentage=b['inputs']['finder_percentage'])==check(b)
 x=copy.deepcopy(b);x['events'].pop(0) # even a noncontributing boundary row is retained
 rejects(audit_retained,x,c['sha256'],b['summary_hash'],A,'btc1',c['scheme'],c['factor'],expected)
 x=copy.deepcopy(b);x['summary_hash']='55'*32
 rejects(audit_retained,x,c['sha256'],b['summary_hash'],A,'btc1',c['scheme'],c['factor'],expected)
 got,dust,digest=check(b);assert dust==c['dust'] and digest==c['sha256'] and encode('SettlementAuditBundleV1',b).hex()==c['bundle_hex']
 # Losing a contributing payload or changing deduction/reward fails recomputation.
 x=copy.deepcopy(b);x['events'].pop();rejects(check,x)
 x=copy.deepcopy(b);x['inputs']['deductions'][0]['amount']='0.2';rejects(check,x)
 x=copy.deepcopy(b);x['events'][-1]['payload']='00';rejects(check,x)
 x=copy.deepcopy(b);m=A();m.ParseFromString(bytes.fromhex(x['events'][-1]['payload']));m.primary.share.difficulty=0.75
 x['events'][-1]['payload']=m.SerializeToString().hex();x['events'][-1]['chain_hash']=event_hash(x['events'][-1]);rejects(check,x)
 if c['scheme']==2:
  x=copy.deepcopy(b);x['inputs']['finder_accounting_id']='02'*16;rejects(check,x)
  x=copy.deepcopy(b);x['inputs']['block_height']+=1;rejects(check,x)
# Small review hardening regressions.
rejects(allocate,[('x',Fraction(1),Fraction(1)),('x',Fraction(1),Fraction(1))],'1')
f=json.loads((R/'docs/coredrp-v1-financial-hardening-vectors.json').read_text())['effects']
for n in (257,65536):rejects(participant_bytes,f['summary_context'],dict(f['sources'][0],miner='x'*n))
assert no_live_dependencies({},[]) and not no_live_dependencies({'unsettled':True},[])
for lo,hi,state in [(-3000,-2000,'UNKNOWN'),(-3000,-2001,'BAD'),(2000,3000,'UNKNOWN'),(2001,3000,'BAD')]:
 x=dict(generation=1,last_generation=0,valid_for_ms=1000,effective_expiry_ms=1000,reported_skew_ms=2000,bound_skew_ms=2000,lower=lo,upper=hi,state=state,reason='PROBE_EVIDENCE',probe_present=True,probe_valid=True)
 assert verify_clock_update(x)==(state,1000)
 x['state']='BAD' if state=='UNKNOWN' else 'UNKNOWN';assert verify_clock_update(x)[0]=='CLOCK_CONTRACT_VIOLATION'
 x.update(lower=hi,upper=lo);assert verify_clock_update(x)[0]=='MALFORMED_FRAME'
print('CoreDRP admission history, request/ADMIN encodings, global identity and retained-source settlement audit: OK')
