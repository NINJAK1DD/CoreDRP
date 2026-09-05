#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# Originally designed and authored as part of CoreDRP by Rob Cooke.
# SPDX-License-Identifier: Apache-2.0
"""Verify CoreDRP/1 Draft 0.4 cryptographic, contract, admission and ADMIN vectors."""
from __future__ import annotations
import hashlib,json,struct,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'docs/coredrp-v1-test-vectors.json').read_text(encoding='utf-8'))
def H(b:bytes)->bytes:return hashlib.sha256(b).digest()
def u8(n:int)->bytes:return bytes([n])
def u16(n:int)->bytes:return struct.pack('>H',n)
def u32(n:int)->bytes:return struct.pack('>I',n)
def u64(n:int)->bytes:return struct.pack('>Q',n)
def i64(n:int)->bytes:return struct.pack('>q',n)
t=D['domain_tags_ascii'];PAY=t['payload'].encode();EVT=t['event'].encode();GEN=t['genesis'].encode();CON=t['contract'].encode();ADM=t['admin'].encode();ADMISSION=t['admission'].encode()
def check_range(lane:int,seq:int,typ:int,scope:bytes)->None:
 if not 0<=lane<=255:raise ValueError('LANE_ID_OUT_OF_RANGE')
 if not 1<=seq<=(1<<63)-1:raise ValueError('SEQUENCE_OUT_OF_RANGE')
 if not 0<=typ<=0xffff:raise ValueError('EVENT_TYPE_OUT_OF_RANGE')
 if len(scope)>0xffff:raise ValueError('ATOMIC_RESOURCE_LIMIT_EXCEEDED')
def chain_event(ch,s,e,l,n,typ,rid,q,tm,p):
 check_range(l,n,typ,q);ph=H(PAY+u32(len(p))+p);pre=EVT+ch+s+e+u8(l)+u64(n)+u16(typ)+rid+u16(len(q))+q+i64(tm)+ph;return ph,pre,H(pre)
for c in D['chains']:
 s=uuid.UUID(c['sender_id']).bytes;e=uuid.UUID(c['log_epoch']).bytes;l=int(c['lane_id']);assert s.hex()==c['sender_id_bytes_hex'];assert e.hex()==c['log_epoch_bytes_hex'];g=GEN+s+e+u8(l);assert g.hex()==c['genesis_preimage_hex'];gen=H(g);assert gen.hex()==c['genesis_chain_sha256'];ch=bytes.fromhex(c['synthetic_previous_chain_sha256']) if c.get('kind')=='crypto_only' else gen
 for x in c['events']:
  rid=uuid.UUID(x['relay_event_id']).bytes;ph,pre,ch=chain_event(ch,s,e,l,int(x['sequence']),int(x['event_type'],16),rid,bytes.fromhex(x['scope_hex']),int(x['event_time_unix_ms']),bytes.fromhex(x['payload_hex']));assert rid.hex()==x['relay_event_id_bytes_hex'];assert ph.hex()==x['payload_hash_sha256'];assert pre.hex()==x['event_preimage_hex'];assert ch.hex()==x['chain_hash_sha256']
 assert ch.hex()==c['terminal_chain_sha256']
m=D['max_scope_case'];s=uuid.UUID(m['sender_id']).bytes;e=uuid.UUID(m['log_epoch']).bytes;q=bytes.fromhex(m['scope_pattern']['byte_hex'])*m['scope_pattern']['count'];ph,pre,ch=chain_event(H(GEN+s+e+u8(m['lane_id'])),s,e,m['lane_id'],m['sequence'],int(m['event_type'],16),uuid.UUID(m['relay_event_id']).bytes,q,m['event_time_unix_ms'],bytes.fromhex(m['payload_hex']));comp=m['event_preimage_components'];expected=bytes.fromhex(comp['prefix_hex'])+bytes.fromhex(comp['scope_repeat_byte_hex'])*comp['scope_repeat_count']+bytes.fromhex(comp['suffix_hex']);assert pre==expected and ph.hex()==m['payload_hash_sha256'] and ch.hex()==m['chain_hash_sha256']
def mining_source(c):
 pid=c['profile_id'].encode();q=c['scope'].encode();coin=c['coin_id'].encode();net=c['network_id'].encode();return u16(len(pid))+pid+u32(c['profile_major'])+u32(c['profile_minor'])+u16(len(q))+q+u8(c['payout_scheme'])+u16(len(coin))+coin+u16(len(net))+net+u16(c['completeness_policy_version'])+u16(c['retention_policy_version'])+u8(c['cross_sender_ordering_policy'])+u32(c['permitted_clock_skew_ms'])+u32(c['max_clock_step_ms'])+u32(c['probe_interval_ms'])+u32(c['probe_processing_max_ms'])+u32(c['evidence_expiry_ms'])+u32(c['unknown_grace_ms'])+u64(c['admission_idempotency_horizon_ms'])
def miningcore_source(c):
 pid=c['profile_id'].encode();q=c['scope'].encode();return u16(len(pid))+pid+u32(c['profile_major'])+u32(c['profile_minor'])+u16(len(q))+q+u32(c['accounting_schema_version'])+u32(c['persistence_schema_version'])+u16(c['direct_candidate_validation_version'])+u16(c['settlement_policy_version'])
for name,builder in [('mining',mining_source),('miningcore',miningcore_source)]:
 obj=D['semantic_contracts'][name];src=builder(obj['configuration']);assert src.hex()==obj['source_bytes_hex'] and H(src).hex()==obj['sha256']
def contract_preimage(c):
 profiles=[]
 for p in c['profiles']:
  ident=p['profile_id'].encode();d=p.get('digest_hex');entry=u16(len(ident))+ident+u32(p['major'])+u32(p['minor'])+u8(1 if d else 0)+(bytes.fromhex(d) if d else b'');profiles.append((p['profile_id'],p['major'],p['minor'],entry))
 profiles.sort(key=lambda x:x[:3]);scopes=[];seen=set()
 for x in c['scope_contracts']:
  q=bytes.fromhex(x['scope_hex']);key=(q,x['profile_id'],x['major'],x['minor']);assert key not in seen;seen.add(key);ident=x['profile_id'].encode();entry=u16(len(q))+q+u16(len(ident))+ident+u32(x['major'])+u32(x['minor'])+bytes.fromhex(x['digest_hex']);scopes.append((key,entry))
 scopes.sort(key=lambda x:x[0]);ets=[]
 for raw in c['event_types']:
  n=int(raw,16);assert 0<=n<=0xffff;ets.append(n)
 assert len(ets)==len(set(ets));ets.sort();return CON+u32(c['core_major'])+u32(c['core_minor'])+u8(c['lane_id'])+u16(len(profiles))+b''.join(x[3] for x in profiles)+u16(len(scopes))+b''.join(x[1] for x in scopes)+u16(len(ets))+b''.join(u16(x) for x in ets)
c=D['contract_binding'];pre=contract_preimage(c);assert pre.hex()==c['preimage_hex'] and H(pre).hex()==c['sha256']
n=D['contract_binding_without_digest'];pre=CON+u32(n['core_major'])+u32(n['core_minor'])+u8(n['lane_id']);p=n['profile'];ident=p['profile_id'].encode();pre+=u16(1)+u16(len(ident))+ident+u32(p['major'])+u32(p['minor'])+u8(0)+u16(0)+u16(1)+u16(int(n['event_types'][0],16));assert pre.hex()==n['preimage_hex'] and H(pre).hex()==n['sha256']
a=D['admission_digest'];q=bytes.fromhex(a['scope_hex']);payload=bytes.fromhex(a['payload_hex']);meta=bytes.fromhex(a['profile_metadata_hex']);pre=ADMISSION+u16(int(a['event_type'],16))+u16(len(q))+q+u32(len(payload))+payload+u32(len(meta))+meta;assert pre.hex()==a['preimage_hex'] and H(pre).hex()==a['sha256']
a=D['admin_digest'];fields=[]
for f in a['fields']:
 v=uuid.UUID(f['value']).bytes if f['type']=='uuid' else u64(int(f['value'])) if f['type']=='uint64' else f['value'].encode();fields.append((f['field_id'],v))
body=u16(1)+u16(len(fields))+b''.join(u16(fid)+u32(len(v))+v for fid,v in fields);pre=ADM+u16(a['action_type'])+u32(len(body))+body;assert body.hex()==a['canonical_body_hex'] and pre.hex()==a['preimage_hex'] and H(pre).hex()==a['sha256']
for x in D['invalid_cases']:
 if x['name'] not in {'lane_out_of_range','event_type_out_of_range','sequence_zero','scope_too_large'}:continue
 q=b'a'*x.get('scope_pattern',{}).get('count',0)
 try:check_range(x.get('lane_id',0),x.get('sequence',1),x.get('event_type',1),q)
 except ValueError as exc:assert str(exc)==x['expected_error'],x['name']
 else:raise AssertionError(x['name'])
print('CoreDRP/1 Draft 0.4 cryptographic, contract, admission and ADMIN vectors: OK')
