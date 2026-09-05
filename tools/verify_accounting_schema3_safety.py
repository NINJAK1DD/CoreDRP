#!/usr/bin/env python3
from pathlib import Path
import json,math,re,sys,uuid
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory
R=Path(__file__).resolve().parents[1];desc=R/'.build/coredrp.pb'
if not desc.exists():
 print('accounting-schema3 prerequisite missing: run protoc descriptor build before this verifier',file=sys.stderr);raise SystemExit(2)
fds=descriptor_pb2.FileDescriptorSet();fds.ParseFromString(desc.read_bytes());pool=descriptor_pool.DescriptorPool();pending=list(fds.file)
while pending:
 progress=False
 for fd in pending[:]:
  try:pool.Add(fd);pending.remove(fd);progress=True
  except Exception:pass
 if not progress:raise RuntimeError('descriptor dependency load failed')
def C(n):return message_factory.GetMessageClass(pool.FindMessageTypeByName(n))
A=C('coredrp.miningcore.v1.MiningcoreAccountingShareEvent')
BASE=json.loads((R/'docs/coredrp-v1-accounting-vectors.json').read_text())
V=json.loads((R/'docs/coredrp-v1-accounting-schema3-safety-vectors.json').read_text())
SCOPE_RE=re.compile(rb'^[A-Za-z0-9._-]{1,64}$')

def uuid16_ok(b):
 if len(b)!=16 or b==b'\x00'*16:return False
 try:uuid.UUID(bytes=bytes(b));return True
 except Exception:return False

def strict_projection(p,tm):
 if not SCOPE_RE.fullmatch(bytes(p.scope)) or not p.HasField('share') or not p.preserve_created:return False
 s=p.share
 vals=[s.difficulty,s.achieved_share_difficulty,s.actual_difficulty,s.network_difficulty]
 if not all(math.isfinite(x) for x in vals):return False
 if not (s.miner and s.session_id and s.source_ip and s.difficulty>0 and s.achieved_share_difficulty>0 and s.actual_difficulty>0 and s.network_difficulty>0 and s.created_unix_ms==tm):return False
 if not p.HasField('accounting_id') or not uuid16_ok(p.accounting_id):return False
 if not p.HasField('reward_basis_satoshis') or p.reward_basis_satoshis<=0:return False
 if p.block_only:return False
 return True

def strict_accounting(m,tm,outer):
 if not m.HasField('primary') or not strict_projection(m.primary,tm):return False
 if bytes(m.primary.scope)!=outer or m.primary.accounting_role not in (1,2):return False
 if m.primary.accounting_role==1 and m.HasField('paired'):return False
 if m.primary.accounting_role==2 and not m.HasField('paired'):return False
 if m.HasField('paired'):
  p=m.paired
  if p.accounting_role!=3 or not strict_projection(p,tm):return False
  if bytes(p.scope)==bytes(m.primary.scope) or p.accounting_id!=m.primary.accounting_id:return False
  shared=lambda q:(q.share.worker,q.share.user_agent,q.share.source_ip,q.share.source,q.share.session_id,q.share.created_unix_ms,q.share.achieved_share_difficulty)
  if shared(p)!=shared(m.primary):return False
 return True

base=A();base.ParseFromString(bytes.fromhex(BASE['parent_aux']['payload_hex']));tm=BASE['parent_aux']['event_time_unix_ms'];outer=BASE['parent_aux']['outer_scope'].encode()
assert strict_accounting(base,tm,outer)
for x in V['cases']:
 m=A();m.CopyFrom(base);k=x['case_kind']
 if k=='base_parent_aux':pass
 elif k=='missing_primary_accounting_id':m.primary.ClearField('accounting_id')
 elif k=='zero_accounting_id':m.primary.accounting_id=b'\x00'*16;m.paired.accounting_id=b'\x00'*16
 elif k=='short_accounting_id':m.primary.accounting_id=b'\x01'*15
 elif k=='missing_reward_basis':m.primary.ClearField('reward_basis_satoshis')
 elif k=='zero_reward_basis':m.primary.reward_basis_satoshis=0
 elif k=='empty_session_id':m.primary.share.session_id='';m.paired.share.session_id=''
 elif k=='empty_source_ip':m.primary.share.source_ip='';m.paired.share.source_ip=''
 elif k=='zero_achieved_share_difficulty':m.primary.share.achieved_share_difficulty=0;m.paired.share.achieved_share_difficulty=0
 elif k=='block_only':m.primary.block_only=True;m.primary.block_record_emitted=True;m.primary.statistical_record_emitted=False
 elif k=='paired_missing_accounting_id':m.paired.ClearField('accounting_id')
 elif k=='paired_missing_reward_basis':m.paired.ClearField('reward_basis_satoshis')
 else:raise AssertionError(k)
 got='VALID' if strict_accounting(m,tm,outer) else 'SEMANTIC_PAYLOAD_INVALID'
 assert got==x['expected'],(x,got)
# Pin RFC 9562 UUID bytes -> canonical Miningcore Guid N representation.
b=bytes.fromhex(BASE['parent_aux']['accounting_id_hex']);assert uuid.UUID(bytes=b).hex==BASE['parent_aux']['accounting_id_hex'].lower()
print('CoreDRP Miningcore accounting schema 3 strict safety vectors: OK')
