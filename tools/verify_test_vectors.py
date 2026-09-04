#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# Originally designed and authored as part of CoreDRP by Rob Cooke.
# SPDX-License-Identifier: Apache-2.0
"""Verify all CoreDRP/1 Draft 0.2 cryptographic, range and digest vectors."""
from __future__ import annotations
import hashlib,json,struct,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'docs/coredrp-v1-test-vectors.json').read_text(encoding='utf-8'))
def H(b:bytes)->bytes:return hashlib.sha256(b).digest()
def u16(n:int)->bytes:return struct.pack('>H',n)
def u32(n:int)->bytes:return struct.pack('>I',n)
def u64(n:int)->bytes:return struct.pack('>Q',n)
def i64(n:int)->bytes:return struct.pack('>q',n)
t=D['domain_tags_ascii']; PAY=t['payload'].encode('ascii'); EVT=t['event'].encode('ascii'); GEN=t['genesis'].encode('ascii'); CON=t['contract'].encode('ascii'); ADM=t['admin'].encode('ascii')
def check_range(lane:int,seq:int,typ:int,scope:bytes)->None:
    if not 0<=lane<=255: raise ValueError('LANE_ID_OUT_OF_RANGE')
    if not 1<=seq<=(1<<63)-1: raise ValueError('SEQUENCE_OUT_OF_RANGE')
    if not 0<=typ<=0xffff: raise ValueError('EVENT_TYPE_OUT_OF_RANGE')
    if len(scope)>0xffff: raise ValueError('RESOURCE_LIMIT_EXCEEDED')
def chain_event(ch,s,e,l,n,typ,rid,q,tm,p):
    check_range(l,n,typ,q); ph=H(PAY+u32(len(p))+p); pre=EVT+ch+s+e+bytes([l])+u64(n)+u16(typ)+rid+u16(len(q))+q+i64(tm)+ph; return ph,pre,H(pre)
for c in D['chains']:
    s=uuid.UUID(c['sender_id']).bytes;e=uuid.UUID(c['log_epoch']).bytes;l=int(c['lane_id']);assert s.hex()==c['sender_id_bytes_hex'];assert e.hex()==c['log_epoch_bytes_hex']
    g=GEN+s+e+bytes([l]);assert g.hex()==c['genesis_preimage_hex'];ch=H(g);assert ch.hex()==c['genesis_chain_sha256']
    for x in c['events']:
        n=int(x['sequence']);typ=int(x['event_type'],16);rid=uuid.UUID(x['relay_event_id']).bytes;assert rid.hex()==x['relay_event_id_bytes_hex'];q=bytes.fromhex(x['scope_hex']);tm=int(x['event_time_unix_ms']);p=bytes.fromhex(x['payload_hex']);ph,pre,ch=chain_event(ch,s,e,l,n,typ,rid,q,tm,p);assert ph.hex()==x['payload_hash_sha256'];assert pre.hex()==x['event_preimage_hex'];assert ch.hex()==x['chain_hash_sha256']
    assert ch.hex()==c['terminal_chain_sha256']
# 65535-byte scope boundary
m=D['max_scope_case'];s=uuid.UUID(m['sender_id']).bytes;e=uuid.UUID(m['log_epoch']).bytes;l=m['lane_id'];q=bytes.fromhex(m['scope_pattern']['byte_hex'])*m['scope_pattern']['count'];rid=uuid.UUID(m['relay_event_id']).bytes;gch=H(GEN+s+e+bytes([l]));ph,pre,ch=chain_event(gch,s,e,l,m['sequence'],int(m['event_type'],16),rid,q,m['event_time_unix_ms'],bytes.fromhex(m['payload_hex']));assert ph.hex()==m['payload_hash_sha256'];assert H(pre).hex()==m['event_preimage_sha256'];assert ch.hex()==m['chain_hash_sha256']
# Contract binding
c=D['contract_binding']; profiles=sorted(c['profiles'],key=lambda x:(x['profile_id'],x['major'],x['minor'])); scopes=sorted(c['scope_contracts'],key=lambda x:(bytes.fromhex(x['scope_hex']),x['profile_id'])); ets=sorted(int(x,16) for x in c['event_types']);pb=b''
for p in profiles:
    i=p['profile_id'].encode('ascii');d=bytes.fromhex(p['digest_hex']);pb+=u16(len(i))+i+u16(p['major'])+u16(p['minor'])+bytes([1])+d
sb=b''
for x in scopes:
    q=bytes.fromhex(x['scope_hex']);i=x['profile_id'].encode('ascii');sb+=u16(len(q))+q+u16(len(i))+i+bytes.fromhex(x['digest_hex'])
pre=CON+u16(c['core_major'])+u16(c['core_minor'])+bytes([c['lane_id']])+u16(len(profiles))+pb+u16(len(scopes))+sb+u16(len(ets))+b''.join(u16(x) for x in ets);assert pre.hex()==c['preimage_hex'];assert H(pre).hex()==c['sha256']
# ADMIN digest
a=D['admin_digest'];body=bytes.fromhex(a['canonical_body_hex']);pre=ADM+u16(a['action_type'])+u32(len(body))+body;assert pre.hex()==a['preimage_hex'];assert H(pre).hex()==a['sha256']
# Negative/range vectors
for x in D['invalid_cases'][:4]:
    try:
        q=b'a'*x.get('scope_pattern',{}).get('count',0);check_range(x.get('lane_id',0),x.get('sequence',1),x.get('event_type',1),q)
    except ValueError as exc: assert str(exc)==x['expected_error'],x['name']
    else: raise AssertionError(x['name'])
print('CoreDRP/1 cryptographic, digest and boundary vectors: OK')
