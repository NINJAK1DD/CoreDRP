# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Arithmetic audit of accepted inputs. Authentication/completeness are separate proofs.

This is not a SettlementPruneSafe evaluator or a production protobuf validator.
"""
from fractions import Fraction
from financial_semantics import decimal,amount,binary64,round_binary64,select_window,allocate
from request_encodings import encode,integer,lp
import hashlib,struct
H=lambda b:hashlib.sha256(b).digest()
def event_hash(e):
    payload=bytes.fromhex(e['payload']);scope=bytes.fromhex(e['scope'])
    return H(b'CoreDRP1-EVENT'+bytes.fromhex(e['previous_chain_hash'])+bytes.fromhex(e['sender'])+bytes.fromhex(e['epoch'])+integer(e['lane'],'B')+integer(e['sequence'],'Q')+integer(e['event_type'],'H')+bytes.fromhex(e['relay'])+integer(len(scope),'H')+scope+integer(e['event_time'],'q')+H(b'CoreDRP1-PAYLOAD'+lp(payload))).hex()

def audit(bundle,A,scope,scheme,factor,expected,adjustment='1',finder_percentage='0'):
    inputs=bundle['inputs'];gross=decimal(inputs['gross_reward']);reward=decimal(inputs['distributable_reward'])
    deductions=inputs['deductions']
    identities=[bytes.fromhex(x['destination']) for x in deductions]
    if any(not x for x in identities) or len(set(identities))!=len(identities):raise ValueError('deduction identity')
    if gross!=reward+sum((decimal(x['amount']) for x in deductions),Fraction(0)):raise ValueError('reward conservation')
    if inputs['finder_percentage']!=(finder_percentage if scheme==2 else '0'):raise ValueError('finder percentage binding')
    rows=[];miners={};finder_matches=[];seen=set()
    for e in bundle['events']:
        if e['event_type']!=512 or e['lane']!=0 or event_hash(e)!=e['chain_hash']:raise ValueError('source integrity')
        key=(e['event_time'],bytes.fromhex(e['sender']),e['sequence'],bytes.fromhex(e['relay']))
        if key in seen:raise ValueError('source duplicate')
        seen.add(key)
        m=A();m.ParseFromString(bytes.fromhex(e['payload']))
        projections=[m.primary]+([m.paired] if m.HasField('paired') else [])
        for p in projections:
            if p.share.created_unix_ms!=e['event_time']:raise ValueError('assigned time')
            if p.scope!=scope.encode():continue
            identity=p.accounting_id.hex()
            if identity in miners:raise ValueError('accounting duplicate')
            miners[identity]=p.share.miner
            assigned=struct.pack('>d',p.share.difficulty).hex()
            adjusted=round_binary64(binary64(assigned)*decimal(adjustment))
            rows.append(dict(accounting_id=identity,time=e['event_time'],sender=e['sender'],sequence=e['sequence'],relay=e['relay'],difficulty=adjusted,network=struct.pack('>d',p.share.network_difficulty).hex()))
            if p.share.is_block_candidate and p.share.candidate_hash.hex()==inputs['block_hash'] and p.share.block_height==inputs['block_height']:
                finder_matches.append(identity)
    if scheme==3:
        selected=[(r['accounting_id'],binary64(round_binary64(binary64(r['difficulty'])/binary64(r['network']))),Fraction(1)) for r in rows]
    else:selected=select_window(rows,factor)
    finder=inputs['finder_accounting_id']
    if scheme==2:
        if finder_matches!=[finder]:raise ValueError('finder linkage')
    elif finder is not None:raise ValueError('unexpected finder')
    amounts,dust=allocate(selected,inputs['distributable_reward'],finder,finder_percentage if scheme==2 else '0')
    result={k:(miners[k],v) for k,v in amounts.items()}
    if result!=expected:raise ValueError('allocation mismatch')
    return result,dust,H(encode('SettlementAuditBundleV1',bundle)).hex()


def audit_retained(bundle,trusted_bundle_digest,trusted_summary_digest,*args,**kwargs):
    # Anchors come from the immutable final settlement record, not from the bundle.
    if H(encode('SettlementAuditBundleV1',bundle)).hex()!=trusted_bundle_digest or bundle['summary_hash']!=trusted_summary_digest:
        raise ValueError('immutable settlement anchor mismatch')
    return audit(bundle,*args,**kwargs)
