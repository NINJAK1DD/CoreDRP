#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1];D=json.loads((R/'docs/coredrp-v1-draft05-vectors.json').read_text())
u8=lambda n:bytes([n]);u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n);u64=lambda n:struct.pack('>Q',n);f64=lambda n:struct.pack('>d',n)
def lp32(b):return u32(len(b))+b
def utf8(s):return s.encode('utf-8')
def opt_bytes(v):return u8(0) if v is None else u8(1)+lp32(bytes.fromhex(v))
def opt_text(v,ascii_only=False):
 if v is None:return u8(0)
 b=v.encode('ascii' if ascii_only else 'utf-8');return u8(1)+lp32(b)
def mining_share_request_v1(x):
 out=u16(1)+u64(x['block_height'])
 out+=lp32(utf8(x['miner']))+lp32(utf8(x['worker']))+lp32(utf8(x['user_agent']))
 out+=f64(x['difficulty'])+f64(x['achieved_share_difficulty'])+f64(x['actual_difficulty'])+f64(x['network_difficulty'])
 out+=lp32(utf8(x['source_ip']))+lp32(utf8(x['source']))+lp32(utf8(x['session_id']))
 out+=u8(1 if x['is_block_candidate'] else 0)
 out+=opt_bytes(x['candidate_hash_hex'])+opt_text(x['candidate_kind'])+opt_text(x['transaction_confirmation_data'])+opt_text(x['block_reward'],True)
 return out
r=D['mining_share_request_v1'];req=mining_share_request_v1(r);assert req.hex()==r['canonical_request_hex']
a=D['admission_digest'];assert req.hex()==a['canonical_request_hex'];scope=bytes.fromhex(a['scope_hex']);pre=b'CoreDRP1-ADMISSION'+u8(a['lane'])+u16(int(a['event_type'],16))+u16(len(scope))+scope+u32(len(req))+req;assert pre.hex()==a['preimage_hex'];assert hashlib.sha256(pre).hexdigest()==a['sha256']
for obj in D['semantic_contracts'].values():
 src=bytes.fromhex(obj['source_hex']);assert hashlib.sha256(src).hexdigest()==obj['sha256']
def negotiate(x):
 common=set(tuple(r) for r in x['sender']) & set(tuple(r) for r in x['receiver']);eligible=[r for r in common if (r[2],r[3]) <= (x['core_major'],x['core_minor'])]
 if not eligible:return None
 maj=max(r[0] for r in eligible);minor=max(r[1] for r in eligible if r[0]==maj);return [maj,minor]
for x in D['profile_negotiation_cases']:assert negotiate(x)==x['expected'],x
for x in D['admin_order_cases']:
 strictly=all(a<b for a,b in zip(x['field_ids'],x['field_ids'][1:]));width_ok=not x.get('uint64_field_id') or x['widths'][x['field_ids'].index(x['uint64_field_id'])]==8;got='ACCEPT' if strictly and width_ok else 'REJECT';assert got==x['expected'],x
seen_actions=set()
for x in D['admin_action_cases']:
 assert x['action_type'] not in seen_actions;seen_actions.add(x['action_type']);assert all(a<b for a,b in zip(x['field_ids'],x['field_ids'][1:]));assert x['expected']=='ACCEPT'
assert {4,5,6,7}.issubset(seen_actions)
for x in D['scope_digest_cases']:
 try:x['profile_id'].encode('ascii');ascii_ok=True
 except UnicodeEncodeError:ascii_ok=False
 got='ACCEPT' if ascii_ok and x['digest_len']==32 else 'INVALID_HANDSHAKE';assert got==x['expected'],x
for x in D['candidate_state_cases']:
 got='ACCEPT' if x['candidate_exists'] and x['same_scope'] and x['monotonic'] else 'INVALID_STATE_TRANSITION';assert got==x['expected'],x
print('CoreDRP Draft 0.5 supplemental conformance vectors: OK')
