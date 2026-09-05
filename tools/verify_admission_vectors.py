#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-admission-vectors.json').read_text())
u8=lambda n:bytes([n]);u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n);u64=lambda n:struct.pack('>Q',n);f64=lambda n:struct.pack('>d',n)
def lp32(b):return u32(len(b))+b
def opt_bytes(v):return u8(0) if v is None else u8(1)+lp32(bytes.fromhex(v))
def opt_text(v,ascii_only=False):
 if v is None:return u8(0)
 b=v.encode('ascii' if ascii_only else 'utf-8');return u8(1)+lp32(b)
def request(x):
 out=u16(1)+u64(x['block_height'])
 for k in ('miner','worker','user_agent'):out+=lp32(x[k].encode('utf-8'))
 for k in ('difficulty','achieved_share_difficulty','actual_difficulty','network_difficulty'):out+=f64(x[k])
 for k in ('source_ip','source','session_id'):out+=lp32(x[k].encode('utf-8'))
 out+=u8(1 if x['is_block_candidate'] else 0)
 out+=opt_bytes(x['candidate_hash_hex'])
 out+=opt_text(x['candidate_kind'])
 out+=opt_text(x['transaction_confirmation_data'])
 out+=opt_text(x['block_reward'],True)
 return out
r=D['mining_share_request_v1'];req=request(r);assert req.hex()==r['canonical_request_hex']
a=D['admission_digest'];scope=bytes.fromhex(a['scope_hex']);pre=b'CoreDRP1-ADMISSION'+u8(a['lane'])+u16(int(a['event_type'],16))+u16(len(scope))+scope+u32(len(req))+req
assert pre.hex()==a['preimage_hex'];assert hashlib.sha256(pre).hexdigest()==a['sha256']
# The identity must change if lane/scope/stable caller request changes.
base=hashlib.sha256(pre).digest()
for x in D['negative_cases']:
 if x['case_kind']=='scope_changes_digest':
  q=bytes.fromhex(x['scope_hex']);p=b'CoreDRP1-ADMISSION'+u8(a['lane'])+u16(int(a['event_type'],16))+u16(len(q))+q+u32(len(req))+req
 elif x['case_kind']=='lane_changes_digest':
  p=b'CoreDRP1-ADMISSION'+u8(x['lane'])+u16(int(a['event_type'],16))+u16(len(scope))+scope+u32(len(req))+req
 elif x['case_kind']=='candidate_presence_changes_request':
  m=dict(r);m['is_block_candidate']=x['is_block_candidate'];m['candidate_hash_hex']=x['candidate_hash_hex'];rq=request(m);p=b'CoreDRP1-ADMISSION'+u8(a['lane'])+u16(int(a['event_type'],16))+u16(len(scope))+scope+u32(len(rq))+rq
 else:raise AssertionError(x)
 assert hashlib.sha256(p).digest()!=base,x
print('CoreDRP Draft 0.6 current Mining admission vectors: OK')
