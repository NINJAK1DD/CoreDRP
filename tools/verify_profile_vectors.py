#!/usr/bin/env python3
from pathlib import Path
import json,math
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory
R=Path(__file__).resolve().parents[1]; D=json.loads((R/'docs/coredrp-v1-test-vectors.json').read_text()); f=descriptor_pb2.FileDescriptorSet();f.ParseFromString((R/'.build/coredrp.pb').read_bytes());pool=descriptor_pool.DescriptorPool();q=list(f.file)
while q:
 progress=False
 for x in q[:]:
  try:pool.Add(x);q.remove(x);progress=True
  except Exception:pass
 if not progress:raise RuntimeError('descriptor dependency load')
def C(n):return message_factory.GetMessageClass(pool.FindMessageTypeByName(n))
S=C('coredrp.mining.v1.MiningShareEvent');CP=C('coredrp.v1.CompletenessCheckpoint');A=C('coredrp.miningcore.v1.MiningcoreAccountingShareEvent')
for e in D['chains'][0]['events']:
 et=int(e['event_type'],16);raw=bytes.fromhex(e['payload_hex']);tm=e['event_time_unix_ms'];scope=bytes.fromhex(e['scope_hex'])
 if et==0x0100:
  m=S();m.ParseFromString(raw);assert m.created_unix_ms==tm and m.miner;assert all(math.isfinite(x) and x>=0 for x in [m.difficulty,m.achieved_share_difficulty,m.actual_difficulty,m.network_difficulty])
 elif et==1:
  m=CP();m.ParseFromString(raw);assert m.complete_through_unix_ms==tm and scope==b''
 elif et==0x0200:
  m=A();m.ParseFromString(raw);assert m.HasField('primary') and not m.HasField('paired')
try:m=S();m.ParseFromString(b'\x00')
except Exception:pass
else:raise AssertionError('malformed payload parsed')
print('CoreDRP profile-aware vectors: OK')
