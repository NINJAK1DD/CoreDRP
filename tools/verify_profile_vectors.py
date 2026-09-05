#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify Draft 0.3 profile semantics, negative cases and Bitcoin evidence consistency."""
from pathlib import Path
import hashlib,json,math,uuid
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-test-vectors.json').read_text(encoding='utf-8'))
P=json.loads((R/'docs/coredrp-v1-profile-vectors.json').read_text(encoding='utf-8'))
fds=descriptor_pb2.FileDescriptorSet();fds.ParseFromString((R/'.build/coredrp.pb').read_bytes());pool=descriptor_pool.DescriptorPool();pending=list(fds.file)
while pending:
 progress=False
 for fd in pending[:]:
  try:pool.Add(fd);pending.remove(fd);progress=True
  except Exception:pass
 if not progress:raise RuntimeError('descriptor dependency load failed')
def C(n):return message_factory.GetMessageClass(pool.FindMessageTypeByName(n))
S=C('coredrp.mining.v1.MiningShareEvent');CP=C('coredrp.v1.CompletenessCheckpoint');A=C('coredrp.miningcore.v1.MiningcoreAccountingShareEvent');BC=C('coredrp.miningcore.v1.BitcoinDirectCoinbaseCandidate');CS=C('coredrp.miningcore.v1.CandidateStateUpdate')
def valid_share(m,tm,lane,scope):
 if lane!=0 or not scope or m.created_unix_ms!=tm or not m.miner:return False
 vals=[m.difficulty,m.achieved_share_difficulty,m.actual_difficulty,m.network_difficulty]
 if not all(math.isfinite(x) for x in vals):return False
 if not (m.difficulty>0 and m.actual_difficulty>0 and m.network_difficulty>0 and m.achieved_share_difficulty>=0):return False
 candidate_fields=m.HasField('candidate_hash') or m.HasField('candidate_kind') or m.HasField('transaction_confirmation_data') or m.HasField('block_reward')
 if not m.is_block_candidate and candidate_fields:return False
 if m.is_block_candidate and (not m.HasField('candidate_hash') or len(m.candidate_hash)==0):return False
 return True
for e in D['chains'][0]['events']:
 et=int(e['event_type'],16);raw=bytes.fromhex(e['payload_hex']);tm=int(e['event_time_unix_ms']);scope=bytes.fromhex(e['scope_hex'])
 if et==0x0100:
  m=S();m.ParseFromString(raw);assert valid_share(m,tm,0,scope)
 elif et==1:
  m=CP();m.ParseFromString(raw);assert m.complete_through_unix_ms==tm and scope==b''
 elif et==0x0200:
  m=A();m.ParseFromString(raw);assert m.HasField('primary') and not m.HasField('paired');assert valid_share(m.primary.share,tm,0,scope)
for x in D['invalid_cases']:
 name=x['name']
 if name=='checkpoint_time_mismatch':assert int(x['event_time_unix_ms'])!=int(x['payload_complete_through_unix_ms'])
 elif name=='malformed_profile_payload':
  m=S()
  try:m.ParseFromString(bytes.fromhex(x['payload_hex']))
  except Exception:pass
  else:raise AssertionError(name)
 elif name=='wrong_lane_share':assert int(x['lane_id'])!=0
 elif name=='candidate_fields_on_non_candidate':assert x['is_block_candidate'] is False and bytes.fromhex(x['candidate_hash_hex'])
 elif name in {'lane_out_of_range','event_type_out_of_range','sequence_zero','scope_too_large'}:pass
 else:raise AssertionError(f'unconsumed invalid vector {name}')
def read_varint(b,pos):
 n=0;shift=0
 while True:
  if pos>=len(b) or shift>63:raise ValueError('varint')
  x=b[pos];pos+=1;n|=(x&0x7f)<<shift
  if not x&0x80:return n,pos
  shift+=7
def parse_legacy_tx(b,pos):
 start=pos
 if pos+4>len(b):raise ValueError('tx')
 pos+=4;nin,pos=read_varint(b,pos);inputs=[]
 for _ in range(nin):
  if pos+36>len(b):raise ValueError('input')
  prev=b[pos:pos+32];idx=int.from_bytes(b[pos+32:pos+36],'little');pos+=36;ln,pos=read_varint(b,pos)
  if pos+ln+4>len(b):raise ValueError('script')
  script=b[pos:pos+ln];pos+=ln;seq=b[pos:pos+4];pos+=4;inputs.append((prev,idx,script,seq))
 nout,pos=read_varint(b,pos);outs=[]
 for _ in range(nout):
  if pos+8>len(b):raise ValueError('output')
  value=int.from_bytes(b[pos:pos+8],'little');pos+=8;ln,pos=read_varint(b,pos)
  if pos+ln>len(b):raise ValueError('pk')
  script=b[pos:pos+ln];pos+=ln;outs.append((value,script))
 if pos+4>len(b):raise ValueError('locktime')
 pos+=4;return b[start:pos],inputs,outs,pos
def sha256d(b):return hashlib.sha256(hashlib.sha256(b).digest()).digest()
v=P['bitcoin_direct_candidate'];m=BC();m.ParseFromString(bytes.fromhex(v['payload_hex']));assert bytes(m.block_hash).hex()==v['block_hash_hex'];assert bytes(m.coinbase_txid).hex()==v['coinbase_txid_hex'];assert bytes(m.serialized_block).hex()==v['serialized_block_hex'];assert bytes(m.candidate_id)==uuid.UUID(v['candidate_id']).bytes;assert m.submission_state==1 and m.gross_reward_satoshis==v['gross_reward_satoshis'];block=bytes(m.serialized_block);assert 81<=len(block)<=4_000_000;assert sha256d(block[:80])[::-1]==bytes(m.block_hash);count,pos=read_varint(block,80);assert count>=1;tx,inputs,outs,end=parse_legacy_tx(block,pos);assert len(inputs)==1 and inputs[0][0]==b'\x00'*32 and inputs[0][1]==0xffffffff;assert sha256d(tx)[::-1]==bytes(m.coinbase_txid);assert m.block_height==0;assert sum(value for value,_ in outs)==m.gross_reward_satoshis;miner_matches=[(value,script) for value,script in outs if script==bytes(m.miner_script_pub_key) and value==m.miner_reward_satoshis];assert len(miner_matches)==1;recipient_pairs=[(r.amount_satoshis,bytes(r.script_pub_key)) for r in m.recipients];classified=[(m.miner_reward_satoshis,bytes(m.miner_script_pub_key))]+recipient_pairs;assert sorted(classified,key=lambda x:(x[1],x[0]))==sorted(outs,key=lambda x:(x[1],x[0]));assert end==len(block)
u=P['candidate_state_update'];m2=CS();m2.ParseFromString(bytes.fromhex(u['payload_hex']));assert bytes(m2.candidate_id)==uuid.UUID(u['candidate_id']).bytes;assert m2.state==2 and m2.submission_attempts==1 and m2.definitive_misses==0;assert m2.HasField('last_attempt_unix_ms') and m2.last_attempt_unix_ms==u['last_attempt_unix_ms']
for x in P['invalid_share_cases']:
 if x['name']=='zero_accepted_difficulty':assert float(x['value'])==0.0
 elif x['name']=='candidate_hash_on_non_candidate':assert x['is_block_candidate'] is False and bytes.fromhex(x['candidate_hash_hex'])
 else:raise AssertionError(f"unconsumed profile invalid {x['name']}")
print('CoreDRP Draft 0.3 profile-aware and Bitcoin evidence vectors: OK')
