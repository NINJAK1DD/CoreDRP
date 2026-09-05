#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Execute financial v4 algorithms against boundary, mutation and stateful cases."""
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from financial_semantics import *
from verify_policy_clock_vectors import verify_bootstrap
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-financial-hardening-vectors.json').read_text())
def rejects(f,*args,**kw):
    try: f(*args,**kw)
    except ValueError: return
    raise AssertionError('invalid input accepted')

for x in D['division_cases']:
    if x['expected']=='REJECT': rejects(lambda: round_binary64(binary64(x['assigned'])/binary64(x['network'])))
    else: assert round_binary64(binary64(x['assigned'])/binary64(x['network']))==x['expected']
# Exact halfway ties, on either side of an even significand; independent rational oracle.
assert round_binary64(Fraction(1)+Fraction(1,2**53))=='3ff0000000000000'
assert round_binary64(Fraction(1)+Fraction(3,2**53))=='3ff0000000000002'
for x in D['windows']:
    for size in (1,2,3,100):
        got=select_window(x['rows'],x['factor'],size)
        assert [r[0] for r in got]==x['expected_ids']
        assert [r[1] for r in got]==list(map(Fraction,x['expected_contributions']))
        assert [r[2] for r in got]==list(map(Fraction,x['expected_fractions']))
# All four equal-time rows must survive pagination; timestamp-only pagination loses two.
rows=D['windows'][0]['rows']
assert len(select_window(rows,'2',2))==4
assert len([r for r in rows if r['time']<1000])==0
# Exercise remaining tie-break components independently of insertion order.
tied=copy.deepcopy(rows)
for r in tied:r['sender']='01'*16
for r in tied:r['sequence']=2 if r['accounting_id']=='1' else 1
assert [r[0] for r in select_window(tied,'2',1)]==['1','4','3','2']
rejects(select_window,rows+[rows[0]],'2')
rejects(select_window,rows,'2.0')
selected=select_window(rows,'1')
assert allocate(selected,'1')==({'4':'0.5','3':'0.5'},'0')
assert allocate(selected,'1','4','5')==({'4':'0.525','3':'0.475'},'0')
assert allocate(selected,'1','finder','5')==({'4':'0.475','3':'0.475','finder':'0.05'},'0')
thirds=[('a',Fraction(1),Fraction(1)),('b',Fraction(1),Fraction(1)),('c',Fraction(1),Fraction(1))]
assert allocate(thirds,'1')[1]=='0.000000000000000000000001'
assert sum(map(decimal,allocate(thirds,'1')[0].values()))+decimal(allocate(thirds,'1')[1])==1

adj=bytes.fromhex('512714e3717013d13566d57aef8ae1fee13b996cf4f0adf6e20eb05ff4d5edcf')
for p in D['pps_policies']:
    source=settlement_policy_source(p['scheme'],adj,p['parameters'])
    assert source.hex()==p['source_hex'] and hashlib.sha256(source).hexdigest()==p['sha256']
current=json.loads((R/'docs/coredrp-v1-draft06-vectors.json').read_text())
for name,p in current['settlement_policies'].items():
    params={'factor':'2'}
    if 'pplnsbf' in name:
        params['block_finder_percentage']='99.'+'9'*24 if 'max' in name else ('0' if 'blockfinder_0' in name else '5')
    assert settlement_policy_source(2 if 'pplnsbf' in name else 1,adj,params).hex()==p['source_hex']
assert D['pps_policies'][0]['sha256']!=D['pps_policies'][1]['sha256']
for params in ({},{'retained_reward_percentage':'0'},{'retained_reward_percentage':'101'},{'retained_reward_percentage':'98.0'}):
    rejects(settlement_policy_source,4,adj,params)
for x in D['pps_cases']:
    args={k:v for k,v in x.items() if k!='expected'}
    if x['expected']=='REJECT':rejects(pps_liability,**args)
    else:
        assert pps_liability(**args)==x['expected']
        validate_pps(4,x['expected'],**args)
        rejects(validate_pps,4,None,**args)
args={k:v for k,v in D['pps_cases'][1].items() if k!='expected'}
rejects(validate_pps,4,'0.5',**args)  # amount from old 0%-fee contract
rejects(validate_pps,1,'0.49',**args)
rejects(pps_liability,**args,coin='litecoin')
rejects(pps_liability,**args,eligible_network=False)

# Each failure leaves both WAL and caller idempotency state unchanged, then repair retries.
p=dict(activated=True,authorized=True,contract=True,mode='RELAY_REQUIRED',member=True,**{'from':1000,'until':2000})
for mutation in ({'activated':False},{'authorized':False},{'contract':False},{'member':False},{'mode':'NO_POLICY'},{'until':1000}):
    state={'policies':{'parent':p.copy(),'aux':dict(p,**mutation)},'wal':[],'outcomes':{}}
    before=copy.deepcopy(state)
    rejects(admit,state,'request-1',['parent','aux'],1000)
    assert state==before
    state['policies']['aux']=p.copy()
    assert admit(state,'request-1',['parent','aux'],1000)==1
    state['policies'].clear()
    assert admit(state,'request-1',['parent','aux'],1000)==1 and len(state['wal'])==1
state={'policies':{'parent':p.copy()},'wal':[],'outcomes':{}}
rejects(admit,state,'r',['parent','aux'],1000);assert not state['wal'] and not state['outcomes']
state['policies']['aux']=dict(p,mode='NO_RELAY_REQUIRED',member=False)
assert admit(state,'r',['parent','aux'],1000)==1
rejects(admit,state,'next',['aux'],2000)
for scope,pool in [(b'ltc','doge'),(b'btc','BTC'),(b'btc','btc '),(b'btc','\u0062\u0074\uff43')]:rejects(scope_pool,scope,pool)
scope_pool(b'btc1','btc1')
assert not no_live_dependencies({},['POLICY_RECONCILIATION_PENDING'])
assert not no_live_dependencies({},['RESOLVED_WAIVED'])
assert not no_live_dependencies({},['UNKNOWN'])
assert no_live_dependencies({},['RESOLVED_RECONCILED'])
assert not no_live_dependencies({'pps':True},[])
assert authority_allows(512) and not authority_allows(513) and not authority_allows(514)
boot=dict(generation=1,action='COMPLETENESS_MODE_CHANGE',old_mode='NO_POLICY',new_mode='RELAY_REQUIRED',effective_unix_ms=1000,origin_unix_ms=1000,required_staging_senders=[],expected_frontier=999)
assert verify_bootstrap(boot)=='ADMIN_ACTION_CONFLICT'
boot['new_mode']='NO_RELAY_REQUIRED';assert verify_bootstrap(boot)=='ACCEPT_BOOTSTRAP'
# A clean setup is no-relay at origin, staged members, then nonempty required mode.
frontier=1000;membership_start=6001;required_start=11002;uncertainty=4000
assert membership_start>frontier+uncertainty
assert activate_required(['sender'],required_start,membership_start,uncertainty,['sender'])['mode']=='RELAY_REQUIRED'
rejects(activate_required,[],required_start,membership_start,uncertainty,[])
rejects(activate_required,['sender'],required_start,membership_start,uncertainty,[])
rejects(activate_required,['sender'],membership_start+uncertainty,membership_start,uncertainty,['sender'])

s=D['effects']['summary_context'];sources=D['effects']['sources']
for i,x in enumerate(sources):
    assert effect_bytes(s,x).hex()==D['effects']['preimages'][i]
    assert participant_bytes(s,x).hex()==D['effects']['records'][i]
assert participant_digest(s,sources)==D['effects']['participant_digest']
assert participant_digest(s,list(reversed(sources)))==D['effects']['participant_digest']
totals={}
for x in sources:totals[x['miner']]=totals.get(x['miner'],Fraction(0))+decimal(x['amount'])
assert {k:amount(v) for k,v in totals.items()}==D['effects']['miner_totals']
for key,value in [('amount','12.6'),('miner','other'),('sequence',43),('payload_hash','dd'*32),('identity','0191b00100007000800000000000e006')]:
    mutated=copy.deepcopy(sources);mutated[0][key]=value
    assert participant_digest(s,mutated)!=D['effects']['participant_digest']
rejects(participant_digest,s,sources+[dict(sources[0],amount='1')])
for key,value in [('lane',1),('event_type',513),('sequence',0),('identity','00'*16),('amount','1.0')]:
    rejects(effect_bytes,s,dict(sources[0],**{key:value}))
# Mixed-case spellings decode to the same UUID and must not double count.
upper=dict(sources[0],identity=sources[0]['identity'].upper())
assert upper['identity']!=sources[0]['identity']
assert effect_bytes(s,upper)==effect_bytes(s,sources[0])
assert participant_digest(s,[upper])==participant_digest(s,[sources[0]])
rejects(participant_digest,s,[sources[0],upper])
rejects(participant_digest,s,[sources[0],dict(upper,amount='1')])

# Offline no-relay nonmember: issuance before preparation makes it a required holder.
receiver={'mode':'NO_RELAY_REQUIRED','holders':set(),'holder_skews':{},'pending':None}
issue_no_relay(receiver,'offline',3000)
prepare_required(receiver,['member'],11002,3,'digest3')
assert receiver['pending']['required']=={'offline','member'}
assert 2*max(receiver['holder_skews'].values())==6000
rejects(issue_no_relay,receiver,'late',2000)
assert 'late' not in receiver['holders']
acknowledge_required(receiver,'member',(3,'digest3'))
rejects(commit_required,receiver)
assert receiver['mode']=='NO_RELAY_REQUIRED'
rejects(acknowledge_required,receiver,'offline',(2,'old-digest'))
# Sender reconnects, persists cap, acknowledges, then loses activation notice.
offline={'policies':{'aux':dict(p,mode='NO_RELAY_REQUIRED',member=False,until=20000)},'wal':[],'outcomes':{}}
ack=stage_withdrawal(offline,'aux',receiver['pending'])
acknowledge_required(receiver,'offline',ack)
commit_required(receiver)
offline=copy.deepcopy(offline)  # restart restores the persisted cap
assert admit(offline,'before',['aux'],11001)==1
before=copy.deepcopy(offline)
rejects(admit,offline,'at-boundary',['aux'],11002)
assert offline==before
# Replaying a prior success remains idempotent, without a second WAL admission.
assert admit(offline,'before',['aux'],11002)==1 and len(offline['wal'])==1
# Aborted activation / older staging cannot reopen the capped evidence.
stage_withdrawal(offline,'aux',{'effective':12000,'generation':4,'digest':'later'})
assert (3,11002) in offline['admission_caps']['aux']
rejects(admit,offline,'after-abort',['aux'],12000)
# Activated generation 3 permits members up to generation 4's later cap.
offline['policies']['aux'].update(generation=3,mode='RELAY_REQUIRED',member=True)
assert admit(offline,'new-member',['aux'],11002)==2
rejects(admit,offline,'later-cap',['aux'],12000)
# Final holder-set recheck catches a concurrent/inconsistent issuance ledger.
r={'mode':'NO_RELAY_REQUIRED','holders':set(),'holder_skews':{},'pending':None}
prepare_required(r,['member'],11002,3,'digest3');acknowledge_required(r,'member',(3,'digest3'))
r['holders'].add('unexpected')
rejects(commit_required,r)
rejects(activate_required,['member'],11002,1000,6000,['member'],['offline'])
assert activate_required(['member'],11002,1000,6000,['member','offline'],['offline'])['mode']=='RELAY_REQUIRED'
print('CoreDRP settlement-policy-v4 financial hardening: OK')
