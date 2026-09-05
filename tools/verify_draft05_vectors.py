#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1];D=json.loads((R/'docs/coredrp-v1-draft05-vectors.json').read_text())
u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n)
a=D['admission_digest'];scope=bytes.fromhex(a['scope_hex']);req=bytes.fromhex(a['canonical_request_hex']);pre=b'CoreDRP1-ADMISSION'+bytes([a['lane']])+u16(int(a['event_type'],16))+u16(len(scope))+scope+u32(len(req))+req;assert pre.hex()==a['preimage_hex'];assert hashlib.sha256(pre).hexdigest()==a['sha256']
def negotiate(x):
 common=set(tuple(r) for r in x['sender']) & set(tuple(r) for r in x['receiver']);eligible=[r for r in common if (r[2],r[3]) <= (x['core_major'],x['core_minor'])]
 if not eligible:return None
 maj=max(r[0] for r in eligible);minor=max(r[1] for r in eligible if r[0]==maj);return [maj,minor]
for x in D['profile_negotiation_cases']:assert negotiate(x)==x['expected'],x
for x in D['admin_order_cases']:
 strictly=all(a<b for a,b in zip(x['field_ids'],x['field_ids'][1:]));width_ok=not x.get('uint64_field_id') or x['widths'][x['field_ids'].index(x['uint64_field_id'])]==8;got='ACCEPT' if strictly and width_ok else 'REJECT';assert got==x['expected'],x
for x in D['scope_digest_cases']:
 try:x['profile_id'].encode('ascii');ascii_ok=True
 except UnicodeEncodeError:ascii_ok=False
 got='ACCEPT' if ascii_ok and x['digest_len']==32 else 'INVALID_HANDSHAKE';assert got==x['expected'],x
for x in D['candidate_state_cases']:
 got='ACCEPT' if x['candidate_exists'] and x['same_scope'] and x['monotonic'] else 'INVALID_STATE_TRANSITION';assert got==x['expected'],x
print('CoreDRP Draft 0.5 supplemental conformance vectors: OK')
