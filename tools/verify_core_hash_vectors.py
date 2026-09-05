#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct,uuid
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-core-hash-vectors.json').read_text())
H=lambda b:hashlib.sha256(b).digest();u8=lambda n:bytes([n]);u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n);u64=lambda n:struct.pack('>Q',n);i64=lambda n:struct.pack('>q',n)
PAY=D['domain_tags_ascii']['payload'].encode();EVT=D['domain_tags_ascii']['event'].encode();GEN=D['domain_tags_ascii']['genesis'].encode()
def event(ch,s,e,l,n,t,rid,q,tm,p):
 assert 0<=l<=255 and 1<=n<=(1<<63)-1 and 0<=t<=0xffff and len(q)<=0xffff
 ph=H(PAY+u32(len(p))+p)
 pre=EVT+ch+s+e+u8(l)+u64(n)+u16(t)+rid+u16(len(q))+q+i64(tm)+ph
 return ph,pre,H(pre)
for c in D['chains']:
 s=uuid.UUID(c['sender_id']).bytes;e=uuid.UUID(c['log_epoch']).bytes;l=c['lane_id']
 assert s.hex()==c['sender_id_bytes_hex'] and e.hex()==c['log_epoch_bytes_hex']
 gp=GEN+s+e+u8(l);assert gp.hex()==c['genesis_preimage_hex'];g=H(gp);assert g.hex()==c['genesis_chain_sha256']
 ch=bytes.fromhex(c['synthetic_previous_chain_sha256']) if c['kind']=='crypto_only' else g
 for x in c['events']:
  rid=uuid.UUID(x['relay_event_id']).bytes;ph,pre,ch=event(ch,s,e,l,x['sequence'],int(x['event_type'],16),rid,bytes.fromhex(x['scope_hex']),x['event_time_unix_ms'],bytes.fromhex(x['payload_hex']))
  assert rid.hex()==x['relay_event_id_bytes_hex'];assert ph.hex()==x['payload_hash_sha256'];assert pre.hex()==x['event_preimage_hex'];assert ch.hex()==x['chain_hash_sha256']
 assert ch.hex()==c['terminal_chain_sha256']
m=D['max_scope_case'];s=uuid.UUID(m['sender_id']).bytes;e=uuid.UUID(m['log_epoch']).bytes;q=bytes.fromhex(m['scope_pattern']['byte_hex'])*m['scope_pattern']['count']
ph,pre,ch=event(H(GEN+s+e+u8(m['lane_id'])),s,e,m['lane_id'],m['sequence'],int(m['event_type'],16),uuid.UUID(m['relay_event_id']).bytes,q,m['event_time_unix_ms'],bytes.fromhex(m['payload_hex']))
comp=m['event_preimage_components'];expected=bytes.fromhex(comp['prefix_hex'])+bytes.fromhex(comp['scope_repeat_byte_hex'])*comp['scope_repeat_count']+bytes.fromhex(comp['suffix_hex'])
assert pre==expected and ph.hex()==m['payload_hash_sha256'] and ch.hex()==m['chain_hash_sha256']
print('CoreDRP Core 1.1 current hash-chain vectors: OK')
