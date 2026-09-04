#!/usr/bin/env python3
import hashlib,json,struct,uuid
from pathlib import Path
R=Path(__file__).resolve().parents[1]; D=json.loads((R/'docs/coredrp-v1-test-vectors.json').read_text())
def H(b): return hashlib.sha256(b).digest()
def u16(n): return struct.pack('>H',n)
def u32(n): return struct.pack('>I',n)
def u64(n): return struct.pack('>Q',n)
def i64(n): return struct.pack('>q',n)
t=D['domain_tags_ascii']; PAY=t['payload'].encode(); EVT=t['event'].encode(); GEN=t['genesis'].encode(); CON=t['contract'].encode(); ADM=t['admin'].encode()
def rng(l,s,e,q):
 if not 0<=l<=255: raise ValueError('LANE_ID_OUT_OF_RANGE')
 if not 1<=s<=(1<<63)-1: raise ValueError('SEQUENCE_OUT_OF_RANGE')
 if not 0<=e<=65535: raise ValueError('EVENT_TYPE_OUT_OF_RANGE')
 if len(q)>65535: raise ValueError('RESOURCE_LIMIT_EXCEEDED')
for c in D['chains']:
 s=uuid.UUID(c['sender_id']).bytes; ep=uuid.UUID(c['log_epoch']).bytes; l=c['lane_id']; assert s.hex()==c['sender_id_bytes_hex']
 g=GEN+s+ep+bytes([l]); assert g.hex()==c['genesis_preimage_hex']; ch=H(g); assert ch.hex()==c['genesis_chain_sha256']
 for e in c['events']:
  n=e['sequence']; typ=int(e['event_type'],16); rid=bytes.fromhex(e['relay_event_id_bytes_hex']); q=bytes.fromhex(e['scope_hex']); tm=e['event_time_unix_ms']; p=bytes.fromhex(e['payload_hex']); rng(l,n,typ,q)
  ph=H(PAY+u32(len(p))+p); assert ph.hex()==e['payload_hash_sha256']; pre=EVT+ch+s+ep+bytes([l])+u64(n)+u16(typ)+rid+u16(len(q))+q+i64(tm)+ph; assert pre.hex()==e['event_preimage_hex']; ch=H(pre); assert ch.hex()==e['chain_hash_sha256']
 assert ch.hex()==c['terminal_chain_sha256']
for x in D['invalid_cases'][:4]:
 try: rng(x.get('lane_id',0),x.get('sequence',1),x.get('event_type',1),b'a'*x.get('scope_pattern',{}).get('count',0))
 except ValueError as z: assert str(z)==x['expected_error']
 else: raise AssertionError(x['name'])
print('CoreDRP/1 cryptographic and boundary vectors: OK')
