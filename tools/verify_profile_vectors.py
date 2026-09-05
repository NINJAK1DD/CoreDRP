#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify Draft 0.4 profile semantics, negative cases, Bitcoin Merkle/witness evidence and accounting rules."""
from pathlib import Path
import hashlib,json,math,uuid,re,sys
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory
R=Path(__file__).resolve().parents[1]
desc=R/'.build/coredrp.pb'
if not desc.exists():print('profile-vector prerequisite missing: run protoc descriptor build before this verifier',file=sys.stderr);raise SystemExit(2)
D=json.loads((R/'docs/coredrp-v1-test-vectors.json').read_text());P=json.loads((R/'docs/coredrp-v1-profile-vectors.json').read_text())
fds=descriptor_pb2.FileDescriptorSet();fds.ParseFromString(desc.read_bytes());pool=descriptor_pool.DescriptorPool();pending=list(fds.file)
while pending:
 progress=False
 for fd in pending[:]:
  try:pool.Add(fd);pending.remove(fd);progress=True
  except Exception:pass
 if not progress:raise RuntimeError('descriptor dependency load failed')
def C(n):return message_factory.GetMessageClass(pool.FindMessageTypeByName(n))
S=C('coredrp.mining.v1.MiningShareEvent');CP=C('coredrp.v1.CompletenessCheckpoint');A=C('coredrp.miningcore.v1.MiningcoreAccountingShareEvent');BC=C('coredrp.miningcore.v1.BitcoinDirectCoinbaseCandidate');CS=C('coredrp.miningcore.v1.CandidateStateUpdate')
def valid_share(m,tm,lane=0,scope=b'btc1'):
 if lane!=0 or not scope or m.created_unix_ms!=tm or not m.miner:return False
 vals=[m.difficulty,m.achieved_share_difficulty,m.actual_difficulty,m.network_difficulty]
 if not all(math.isfinite(x) for x in vals):return False
 if not (m.difficulty>0 and m.actual_difficulty>0 and m.network_difficulty>0 and m.achieved_share_difficulty>=0):return False
 candidate_fields=m.HasField('candidate_hash') or m.HasField('candidate_kind') or m.HasField('transaction_confirmation_data') or m.HasField('block_reward')
 if not m.is_block_candidate and candidate_fields:return False
 if m.is_block_candidate and (not m.HasField('candidate_hash') or not m.candidate_hash):return False
 return True
def canonical_decimal(s):return bool(re.fullmatch(r'(?:0|[1-9][0-9]{0,13})(?:\.[0-9]{0,23}[1-9])?',s)) and len(s.replace('.',''))<=38
def valid_projection(p,tm,paired=False):
 if not p.HasField('share') or not valid_share(p.share,tm):return False
 if paired:
  if p.accounting_role!=3:return False
 else:
  if p.accounting_role not in (1,2):return False
 if not p.preserve_created:return False
 if p.HasField('reward_basis_satoshis') and p.reward_basis_satoshis<0:return False
 if p.HasField('pps_calculated_amount'):
  if not p.HasField('accounting_id') or not p.accounting_id or not canonical_decimal(p.pps_calculated_amount.canonical):return False
 if p.block_only and (not p.block_record_emitted or p.statistical_record_emitted):return False
 if p.statistical_record_emitted and p.block_only:return False
 return True
def valid_accounting(m,tm):
 if not m.HasField('primary') or not valid_projection(m.primary,tm,False):return False
 if m.primary.accounting_role==1 and m.HasField('paired'):return False
 if m.primary.accounting_role==2 and not m.HasField('paired'):return False
 if m.HasField('paired'):
  if not valid_projection(m.paired,tm,True):return False
  if (m.primary.share.miner,m.primary.share.worker,m.primary.share.session_id,m.primary.share.created_unix_ms)!=(m.paired.share.miner,m.paired.share.worker,m.paired.share.session_id,m.paired.share.created_unix_ms):return False
  if m.primary.HasField('accounting_id') and m.paired.HasField('accounting_id') and m.primary.accounting_id==m.paired.accounting_id:return False
 return True
for e in D['chains'][0]['events']:
 et=int(e['event_type'],16);raw=bytes.fromhex(e['payload_hex']);tm=int(e['event_time_unix_ms']);scope=bytes.fromhex(e['scope_hex'])
 if et==0x0100:
  m=S();m.ParseFromString(raw);assert valid_share(m,tm,0,scope)
 elif et==1:
  m=CP();m.ParseFromString(raw);assert m.complete_through_unix_ms==tm and scope==b''
 elif et==0x0200:
  m=A();m.ParseFromString(raw);assert valid_accounting(m,tm)
# Execute declared negative share/profile cases against validators.
base=S();base.ParseFromString(bytes.fromhex(D['chains'][0]['events'][0]['payload_hex']));tm=D['chains'][0]['events'][0]['event_time_unix_ms']
for x in D['invalid_cases']:
 name=x['name']
 if name=='checkpoint_time_mismatch':
  m=CP(complete_through_unix_ms=x['payload_complete_through_unix_ms']);assert m.complete_through_unix_ms!=x['event_time_unix_ms']
 elif name=='malformed_profile_payload':
  m=S()
  try:m.ParseFromString(bytes.fromhex(x['payload_hex']))
  except Exception:pass
  else:raise AssertionError(name)
 elif name=='wrong_lane_share':assert not valid_share(base,tm,x['lane_id'],bytes.fromhex(x['scope_hex'])) and x['expected_error']=='INVALID_EVENT_PLACEMENT'
 elif name=='candidate_fields_on_non_candidate':
  m=S();m.CopyFrom(base);m.is_block_candidate=False;m.candidate_hash=bytes.fromhex(x['candidate_hash_hex']);assert not valid_share(m,tm)
 elif name in {'lane_out_of_range','event_type_out_of_range','sequence_zero','scope_too_large'}:pass
 else:raise AssertionError(f'unconsumed invalid vector {name}')
for x in P['invalid_share_cases']:
 m=S();m.CopyFrom(base)
 if x['name']=='zero_accepted_difficulty':m.difficulty=0.0
 elif x['name']=='candidate_hash_on_non_candidate':m.is_block_candidate=False;m.candidate_hash=b'\x00'
 assert not valid_share(m,tm),x['name']
# Accounting validity matrix and executed negative mutations.
av=A();av.ParseFromString(bytes.fromhex(P['accounting_parent_aux']['payload_hex']));atm=P['accounting_parent_aux']['event_time_unix_ms'];assert valid_accounting(av,atm)
for x in P['invalid_accounting_cases']:
 m=A();m.CopyFrom(av);name=x['name']
 if name=='unspecified_primary_role':m.primary.accounting_role=0
 elif name=='single_with_paired':m.primary.accounting_role=1
 elif name=='parent_without_paired':m.ClearField('paired')
 elif name=='paired_not_auxiliary':m.paired.accounting_role=1
 elif name=='same_accounting_id':m.paired.accounting_id=m.primary.accounting_id
 elif name=='preserve_created_false':m.primary.preserve_created=False
 elif name=='block_only_statistical':m.primary.block_only=True;m.primary.block_record_emitted=True;m.primary.statistical_record_emitted=True
 else:raise AssertionError(name)
 assert not valid_accounting(m,atm),name
def read_varint(b,pos):
 n=0;shift=0
 while True:
  if pos>=len(b) or shift>63:raise ValueError('varint')
  x=b[pos];pos+=1;n|=(x&0x7f)<<shift
  if not x&0x80:return n,pos
  shift+=7
def enc_varint(n):
 out=bytearray()
 while True:
  x=n&0x7f;n>>=7;out.append(x|(0x80 if n else 0))
  if not n:return bytes(out)
def sha256d(b):return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def parse_tx(b,pos):
 start=pos
 if pos+4>len(b):raise ValueError('tx')
 version=b[pos:pos+4];pos+=4;segwit=False
 if pos+2<=len(b) and b[pos]==0 and b[pos+1]!=0:segwit=True;pos+=2
 nin,pos=read_varint(b,pos);inputs=[];in_ser=[]
 for _ in range(nin):
  p0=pos
  if pos+36>len(b):raise ValueError('input')
  prev=b[pos:pos+32];idx=int.from_bytes(b[pos+32:pos+36],'little');pos+=36;ln,pos=read_varint(b,pos)
  if pos+ln+4>len(b):raise ValueError('script')
  script=b[pos:pos+ln];pos+=ln;seq=b[pos:pos+4];pos+=4;inputs.append((prev,idx,script,seq));in_ser.append(b[p0:pos])
 nout,pos=read_varint(b,pos);outs=[];out_ser=[]
 for _ in range(nout):
  p0=pos
  if pos+8>len(b):raise ValueError('output')
  value=int.from_bytes(b[pos:pos+8],'little');pos+=8;ln,pos=read_varint(b,pos)
  if pos+ln>len(b):raise ValueError('pk')
  script=b[pos:pos+ln];pos+=ln;outs.append((value,script));out_ser.append(b[p0:pos])
 witnesses=[]
 if segwit:
  for _ in range(nin):
   nitems,pos=read_varint(b,pos);stack=[]
   for _ in range(nitems):ln,pos=read_varint(b,pos);stack.append(b[pos:pos+ln]);pos+=ln
   witnesses.append(stack)
 if pos+4>len(b):raise ValueError('locktime')
 lock=b[pos:pos+4];pos+=4
 nonwit=version+enc_varint(nin)+b''.join(in_ser)+enc_varint(nout)+b''.join(out_ser)+lock
 return {'full':b[start:pos],'nonwit':nonwit,'inputs':inputs,'outs':outs,'witnesses':witnesses,'segwit':segwit,'end':pos}
def merkle(leaves):
 if not leaves:return b'\x00'*32
 level=list(leaves)
 while len(level)>1:
  if len(level)%2:level.append(level[-1])
  level=[sha256d(level[i]+level[i+1]) for i in range(0,len(level),2)]
 return level[0]
def scriptnum_first(script):
 if not script:return None
 ln=script[0]
 if ln==0 or 1+ln>len(script):return None
 raw=script[1:1+ln];v=int.from_bytes(raw,'little');return v & ~(1<<(8*len(raw)-1)) if raw[-1]&0x80 else v
def validate_candidate(v):
 m=BC();m.ParseFromString(bytes.fromhex(v['payload_hex']));block=bytes(m.serialized_block)
 if len(block)<81 or len(block)>4_000_000:return False
 if sha256d(block[:80])[::-1]!=bytes(m.block_hash):return False
 count,pos=read_varint(block,80);txs=[]
 for _ in range(count):tx=parse_tx(block,pos);txs.append(tx);pos=tx['end']
 if pos!=len(block) or not txs:return False
 coin=txs[0]
 if len(coin['inputs'])!=1 or coin['inputs'][0][0]!=b'\x00'*32 or coin['inputs'][0][1]!=0xffffffff:return False
 if sha256d(coin['nonwit'])[::-1]!=bytes(m.coinbase_txid):return False
 txids=[sha256d(t['nonwit']) for t in txs]
 if merkle(txids)!=block[36:68]:return False
 if m.block_height and scriptnum_first(coin['inputs'][0][2])!=m.block_height:return False
 commitment_indices=[i for i,(value,script) in enumerate(coin['outs']) if len(script)>=38 and script[:6]==bytes.fromhex('6a24aa21a9ed')]
 if commitment_indices:
  idx=max(commitment_indices)
  if not coin['segwit'] or not coin['witnesses'] or not coin['witnesses'][0] or len(coin['witnesses'][0][0])!=32:return False
  reserved=coin['witnesses'][0][0];wleaves=[b'\x00'*32]+[sha256d(t['full']) for t in txs[1:]];expected=sha256d(merkle(wleaves)+reserved)
  if coin['outs'][idx][1][6:38]!=expected:return False
 if sum(v for v,_ in coin['outs'])!=m.gross_reward_satoshis:return False
 miner=(m.miner_reward_satoshis,bytes(m.miner_script_pub_key));rec=[(r.amount_satoshis,bytes(r.script_pub_key)) for r in m.recipients]
 direct=[miner]+rec;consensus=[o for i,o in enumerate(coin['outs']) if i in commitment_indices and o[0]==0]
 remaining=list(coin['outs'])
 for o in direct+consensus:
  if o not in remaining:return False
  remaining.remove(o)
 if remaining:return False
 return bytes(m.candidate_id)==uuid.UUID(v['candidate_id']).bytes and m.submission_state==1
assert validate_candidate(P['bitcoin_direct_candidate_legacy'])
assert validate_candidate(P['bitcoin_direct_candidate_segwit'])
u=P['candidate_state_update'];m=CS();m.ParseFromString(bytes.fromhex(u['payload_hex']));assert bytes(m.candidate_id)==uuid.UUID(u['candidate_id']).bytes and m.state==2 and m.submission_attempts==1 and m.definitive_misses==0 and m.last_attempt_unix_ms==u['last_attempt_unix_ms']
print('CoreDRP Draft 0.4 profile, accounting, Merkle and SegWit vectors: OK')
