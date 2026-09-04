#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify CoreDRP/1 Draft 0.3 cryptographic, contract and ADMIN vectors."""
from __future__ import annotations
import hashlib, json, struct, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'docs/coredrp-v1-test-vectors.json').read_text(encoding='utf-8'))
def H(b:bytes)->bytes:return hashlib.sha256(b).digest()
def u8(n:int)->bytes:return bytes([n])
def u16(n:int)->bytes:return struct.pack('>H',n)
def u32(n:int)->bytes:return struct.pack('>I',n)
def u64(n:int)->bytes:return struct.pack('>Q',n)
def i64(n:int)->bytes:return struct.pack('>q',n)
tags=D['domain_tags_ascii']; PAY=tags['payload'].encode('ascii'); EVT=tags['event'].encode('ascii'); GEN=tags['genesis'].encode('ascii'); CON=tags['contract'].encode('ascii'); ADM=tags['admin'].encode('ascii')
def check_range(lane:int,seq:int,typ:int,scope:bytes)->None:
 if not 0<=lane<=255:raise ValueError('LANE_ID_OUT_OF_RANGE')
 if not 1<=seq<=(1<<63)-1:raise ValueError('SEQUENCE_OUT_OF_RANGE')
 if not 0<=typ<=0xffff:raise ValueError('EVENT_TYPE_OUT_OF_RANGE')
 if len(scope)>0xffff:raise ValueError('RESOURCE_LIMIT_EXCEEDED')
def chain_event(ch,s,e,l,n,typ,rid,q,tm,p):
 check_range(l,n,typ,q);ph=H(PAY+u32(len(p))+p);pre=EVT+ch+s+e+u8(l)+u64(n)+u16(typ)+rid+u16(len(q))+q+i64(tm)+ph;return ph,pre,H(pre)
for c in D['chains']:
 s=uuid.UUID(c['sender_id']).bytes;ep=uuid.UUID(c['log_epoch']).bytes;lane=int(c['lane_id']);assert s.hex()==c['sender_id_bytes_hex'];assert ep.hex()==c['log_epoch_bytes_hex'];g=GEN+s+ep+u8(lane);assert g.hex()==c['genesis_preimage_hex'];genesis=H(g);assert genesis.hex()==c['genesis_chain_sha256'];ch=bytes.fromhex(c['synthetic_previous_chain_sha256']) if c.get('kind')=='crypto_only' else genesis
 for x in c['events']:
  rid=uuid.UUID(x['relay_event_id']).bytes;assert rid.hex()==x['relay_event_id_bytes_hex'];ph,pre,ch=chain_event(ch,s,ep,lane,int(x['sequence']),int(x['event_type'],16),rid,bytes.fromhex(x['scope_hex']),int(x['event_time_unix_ms']),bytes.fromhex(x['payload_hex']));assert ph.hex()==x['payload_hash_sha256'];assert pre.hex()==x['event_preimage_hex'];assert ch.hex()==x['chain_hash_sha256']
 assert ch.hex()==c['terminal_chain_sha256']
m=D['max_scope_case'];s=uuid.UUID(m['sender_id']).bytes;ep=uuid.UUID(m['log_epoch']).bytes;lane=int(m['lane_id']);q=bytes.fromhex(m['scope_pattern']['byte_hex'])*int(m['scope_pattern']['count']);rid=uuid.UUID(m['relay_event_id']).bytes;gch=H(GEN+s+ep+u8(lane));ph,pre,ch=chain_event(gch,s,ep,lane,int(m['sequence']),int(m['event_type'],16),rid,q,int(m['event_time_unix_ms']),bytes.fromhex(m['payload_hex']));comp=m['event_preimage_components'];expected=bytes.fromhex(comp['prefix_hex'])+bytes.fromhex(comp['scope_repeat_byte_hex'])*int(comp['scope_repeat_count'])+bytes.fromhex(comp['suffix_hex']);assert pre==expected;assert ph.hex()==m['payload_hash_sha256'] and ch.hex()==m['chain_hash_sha256']
def mining_source(c):
 pid=c['profile_id'].encode('ascii');scope=c['scope'].encode('ascii');coin=c['coin_id'].encode('ascii');net=c['network_id'].encode('ascii');return u16(len(pid))+pid+u32(c['profile_major'])+u32(c['profile_minor'])+u16(len(scope))+scope+u8(c['payout_scheme'])+u16(len(coin))+coin+u16(len(net))+net+u16(c['completeness_policy_version'])+u16(c['retention_policy_version'])+u8(c['cross_sender_ordering_policy'])+u8(c['completeness_mode'])+u32(c['permitted_clock_skew_ms'])+u32(c['max_clock_step_ms'])+u32(c['probe_interval_ms'])+u32(c['probe_processing_max_ms'])+u32(c['evidence_expiry_ms'])+u32(c['unknown_grace_ms'])
def miningcore_source(c):
 pid=c['profile_id'].encode('ascii');scope=c['scope'].encode('ascii');return u16(len(pid))+pid+u32(c['profile_major'])+u32(c['profile_minor'])+u16(len(scope))+scope+u32(c['accounting_schema_version'])+u32(c['persistence_schema_version'])+u16(c['direct_candidate_validation_version'])+u16(c['settlement_policy_version'])
sc=D['semantic_contracts']
for name,builder in [('mining',mining_source),('miningcore',miningcore_source)]:
 src=builder(sc[name]['configuration']);assert src.hex()==sc[name]['source_bytes_hex'];assert H(src).hex()==sc[name]['sha256']
def contract_preimage(core_major,core_minor,lane,profiles,scopes,event_types):
 if not 0<=lane<=255:raise ValueError('LANE_ID_OUT_OF_RANGE')
 for n in (core_major,core_minor):
  if not 0<=n<=0xffffffff:raise ValueError('INVALID_HANDSHAKE')
 ps=[];seen=set()
 for p in profiles:
  key=(p['profile_id'],p['major']);
  if key in seen:raise ValueError('INVALID_HANDSHAKE')
  seen.add(key);ident=p['profile_id'].encode('ascii');digest=p.get('digest_hex');entry=u16(len(ident))+ident+u32(p['major'])+u32(p['minor'])+u8(1 if digest is not None else 0)
  if digest is not None:
   d=bytes.fromhex(digest);assert len(d)==32;entry+=d
  ps.append((p['profile_id'],p['major'],p['minor'],entry))
 ps.sort(key=lambda x:x[:3]);ss=[];seen_sc=set()
 for x in scopes:
  q=bytes.fromhex(x['scope_hex']);ident=x['profile_id'].encode('ascii');key=(q,x['profile_id'])
  if key in seen_sc:raise ValueError('INVALID_HANDSHAKE')
  seen_sc.add(key);d=bytes.fromhex(x['digest_hex']);assert len(d)==32;ss.append((q,x['profile_id'],u16(len(q))+q+u16(len(ident))+ident+d))
 ss.sort(key=lambda x:(x[0],x[1]));ets=[]
 for raw in event_types:
  n=int(raw,16) if isinstance(raw,str) else int(raw)
  if not 0<=n<=0xffff:raise ValueError('EVENT_TYPE_OUT_OF_RANGE')
  ets.append(n)
 if len(set(ets))!=len(ets):raise ValueError('INVALID_HANDSHAKE')
 ets.sort();return CON+u32(core_major)+u32(core_minor)+u8(lane)+u16(len(ps))+b''.join(x[3] for x in ps)+u16(len(ss))+b''.join(x[2] for x in ss)+u16(len(ets))+b''.join(u16(x) for x in ets)
c=D['contract_binding'];pre=contract_preimage(c['core_major'],c['core_minor'],c['lane_id'],c['profiles'],c['scope_contracts'],c['event_types']);assert pre.hex()==c['preimage_hex'] and H(pre).hex()==c['sha256'];n=D['contract_binding_without_digest'];p=n['profile'];pre=contract_preimage(n['core_major'],n['core_minor'],n['lane_id'],[{'profile_id':p['profile_id'],'major':p['major'],'minor':p['minor']}],n['scope_contracts'],n['event_types']);assert pre.hex()==n['preimage_hex'] and H(pre).hex()==n['sha256']
a=D['admin_digest'];fields=[]
for f in a['fields']:
 value=uuid.UUID(f['value']).bytes if f['type']=='uuid' else u64(int(f['value'])) if f['type']=='uint64' else f['value'].encode('utf-8') if f['type']=='utf8' else (_ for _ in ()).throw(AssertionError('unknown admin field type'));fields.append((int(f['field_id']),value))
assert [x[0] for x in fields]==sorted(x[0] for x in fields) and len({x[0] for x in fields})==len(fields);body=u16(1)+u16(len(fields))+b''.join(u16(fid)+u32(len(v))+v for fid,v in fields);assert body.hex()==a['canonical_body_hex'];pre=ADM+u16(a['action_type'])+u32(len(body))+body;assert pre.hex()==a['preimage_hex'] and H(pre).hex()==a['sha256']
for x in D['invalid_cases']:
 if x['name'] not in {'lane_out_of_range','event_type_out_of_range','sequence_zero','scope_too_large'}:continue
 q=b'a'*int(x.get('scope_pattern',{}).get('count',0))
 try:check_range(int(x.get('lane_id',0)),int(x.get('sequence',1)),int(x.get('event_type',1)),q)
 except ValueError as exc:assert str(exc)==x['expected_error'],x['name']
 else:raise AssertionError(x['name'])
print('CoreDRP/1 Draft 0.3 cryptographic, contract and ADMIN vectors: OK')
