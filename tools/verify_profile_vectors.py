#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify Draft 0.5 profile/accounting/Bitcoin evidence semantics."""
from pathlib import Path
import hashlib,json,math,uuid,re,sys,copy
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory
R=Path(__file__).resolve().parents[1];desc=R/'.build/coredrp.pb'
if not desc.exists():print('profile-vector prerequisite missing: run protoc descriptor build',file=sys.stderr);raise SystemExit(2)
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
 return (m.is_block_candidate and m.HasField('candidate_hash') and bool(m.candidate_hash)) or (not m.is_block_candidate and not candidate_fields)
def canonical_decimal(s):return bool(re.fullmatch(r'(?:0|[1-9][0-9]{0,13})(?:\.[0-9]{0,23}[1-9])?',s)) and len(s.replace('.',''))<=38
def valid_projection(p,tm,paired=False):
 if not p.HasField('share') or not valid_share(p.share,tm):return False
 if paired and p.accounting_role!=3:return False
 if not paired and p.accounting_role not in (1,2):return False
 if not p.preserve_created:return False
 if p.HasField('accounting_id') and not p.accounting_id:return False
 if p.HasField('reward_basis_satoshis') and p.reward_basis_satoshis<0:return False
 if p.HasField('pps_calculated_amount') and (not p.HasField('accounting_id') or not canonical_decimal(p.pps_calculated_amount.canonical)):return False
 if p.block_only and (not p.block_record_emitted or p.statistical_record_emitted):return False
 if p.statistical_record_emitted and p.block_only:return False
 return True
def valid_accounting(m,tm):
 if not m.HasField('primary') or not valid_projection(m.primary,tm):return False
 if m.primary.accounting_role==1 and m.HasField('paired'):return False
 if m.primary.accounting_role==2 and not m.HasField('paired'):return False
 if m.HasField('paired'):
  if not valid_projection(m.paired,tm,True):return False
  if (m.primary.share.miner,m.primary.share.worker,m.primary.share.session_id,m.primary.share.created_unix_ms)!=(m.paired.share.miner,m.paired.share.worker,m.paired.share.session_id,m.paired.share.created_unix_ms):return False
  if m.primary.HasField('accounting_id') and m.paired.HasField('accounting_id') and m.primary.accounting_id==m.paired.accounting_id:return False
 return True
for e in D['chains'][0]['events']:
 et=int(e['event_type'],16);raw=bytes.fromhex(e['payload_hex']);tm=int(e['event_time_unix_ms']);scope=bytes.fromhex(e['scope_hex'])
 if et==0x0100:m=S();m.ParseFromString(raw);assert valid_share(m,tm,0,scope)
 elif et==1:m=CP();m.ParseFromString(raw);assert m.complete_through_unix_ms==tm and scope==b''
 elif et==0x0200:m=A();m.ParseFromString(raw);assert valid_accounting(m,tm)
base=S();base.ParseFromString(bytes.fromhex(D['chains'][0]['events'][0]['payload_hex']));tm=D['chains'][0]['events'][0]['event_time_unix_ms']
for x in P['invalid_share_cases']:
 m=S();m.CopyFrom(base)
 if x['name']=='zero_accepted_difficulty':m.difficulty=0.0
 elif x['name']=='candidate_hash_on_non_candidate':m.is_block_candidate=False;m.candidate_hash=b'\x00'
 assert not valid_share(m,tm),x['name']
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
empty_id=A();empty_id.CopyFrom(av);empty_id.primary.accounting_id=b'';empty_id.primary.ClearField('pps_calculated_amount');assert not valid_accounting(empty_id,atm)
def rv(b,pos):
 n=0;shift=0
 while True:
  if pos>=len(b) or shift>63:raise ValueError('varint')
  x=b[pos];pos+=1;n|=(x&0x7f)<<shift
  if not x&0x80:return n,pos
  shift+=7
def ev(n):
 out=bytearray()
 while True:
  x=n&0x7f;n>>=7;out.append(x|(0x80 if n else 0))
  if not n:return bytes(out)
def h2(b):return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def parse_tx(b,pos):
 start=pos
 if pos+4>len(b):raise ValueError('tx')
 ver=b[pos:pos+4];pos+=4;segwit=False
 if pos+2<=len(b) and b[pos]==0 and b[pos+1]!=0:segwit=True;pos+=2
 nin,pos=rv(b,pos);inputs=[];iser=[]
 for _ in range(nin):
  p0=pos
  if pos+36>len(b):raise ValueError('input')
  prev=b[pos:pos+32];idx=int.from_bytes(b[pos+32:pos+36],'little');pos+=36;ln,pos=rv(b,pos)
  if pos+ln+4>len(b):raise ValueError('script')
  script=b[pos:pos+ln];pos+=ln;seq=b[pos:pos+4];pos+=4;inputs.append((prev,idx,script,seq));iser.append(b[p0:pos])
 nout,pos=rv(b,pos);outs=[];oser=[]
 for _ in range(nout):
  p0=pos
  if pos+8>len(b):raise ValueError('output')
  value=int.from_bytes(b[pos:pos+8],'little');pos+=8;ln,pos=rv(b,pos)
  if pos+ln>len(b):raise ValueError('pk')
  script=b[pos:pos+ln];pos+=ln;outs.append((value,script));oser.append(b[p0:pos])
 wit=[]
 if segwit:
  for _ in range(nin):
   cnt,pos=rv(b,pos);stack=[]
   for _ in range(cnt):
    ln,pos=rv(b,pos)
    if pos+ln>len(b):raise ValueError('witness')
    stack.append(b[pos:pos+ln]);pos+=ln
   wit.append(stack)
 if pos+4>len(b):raise ValueError('locktime')
 lock=b[pos:pos+4];pos+=4;nonwit=ver+ev(nin)+b''.join(iser)+ev(nout)+b''.join(oser)+lock
 return {'full':b[start:pos],'nonwit':nonwit,'inputs':inputs,'outs':outs,'witnesses':wit,'segwit':segwit,'end':pos}
def merkle(leaves):
 if not leaves:return b'\x00'*32
 level=list(leaves)
 while len(level)>1:
  if len(level)%2:level.append(level[-1])
  level=[h2(level[i]+level[i+1]) for i in range(0,len(level),2)]
 return level[0]
def scriptnum_minimal(script):
 if not script:return None
 ln=script[0]
 if ln==0 or ln>5 or 1+ln>len(script):return None
 raw=script[1:1+ln]
 if len(raw)>1 and (raw[-1]&0x7f)==0 and not (raw[-2]&0x80):return None
 neg=raw[-1]&0x80;v=int.from_bytes(raw,'little') & ~(1<<(8*len(raw)-1));return -v if neg else v
def commitment_class(script):
 return 'BIP141' if len(script)>=38 and script[:6]==bytes.fromhex('6a24aa21a9ed') else None
def validate_candidate(v):
 m=BC();m.ParseFromString(bytes.fromhex(v['payload_hex']));block=bytes(m.serialized_block)
 params=v.get('network_parameters')
 if not isinstance(params,dict) or params.get('direct_candidate_validation_version',0)<2:return False
 activation=params.get('bip34_activation_height');allowed=set(params.get('allowed_consensus_commitment_classes',[]))
 if not isinstance(activation,int) or activation<0:return False
 if len(block)<81 or len(block)>4_000_000:return False
 if h2(block[:80])[::-1]!=bytes(m.block_hash):return False
 count,pos=rv(block,80);txs=[]
 for _ in range(count):t=parse_tx(block,pos);txs.append(t);pos=t['end']
 if pos!=len(block) or not txs:return False
 coin=txs[0]
 if len(coin['inputs'])!=1 or coin['inputs'][0][0]!=b'\x00'*32 or coin['inputs'][0][1]!=0xffffffff:return False
 txids=[h2(t['nonwit']) for t in txs]
 if len(set(txids))!=len(txids):return False
 if txids[0][::-1]!=bytes(m.coinbase_txid):return False
 if merkle(txids)!=block[36:68]:return False
 if m.block_height>=activation and scriptnum_minimal(coin['inputs'][0][2])!=m.block_height:return False
 magic=bytes.fromhex('6a24aa21a9ed');commitment_indices=[i for i,(value,script) in enumerate(coin['outs']) if len(script)>=38 and script[:6]==magic]
 witness=any(t['segwit'] for t in txs)
 if witness and not commitment_indices:return False
 if commitment_indices:
  idx=max(commitment_indices)
  if not coin['segwit'] or not coin['witnesses'] or not coin['witnesses'][0] or len(coin['witnesses'][0][0])!=32:return False
  expected=h2(merkle([b'\x00'*32]+[h2(t['full']) for t in txs[1:]])+coin['witnesses'][0][0])
  if coin['outs'][idx][1][6:38]!=expected:return False
 if sum(value for value,_ in coin['outs'])!=m.gross_reward_satoshis:return False
 direct=[(m.miner_reward_satoshis,bytes(m.miner_script_pub_key))]+[(r.amount_satoshis,bytes(r.script_pub_key)) for r in m.recipients]
 declared_by_index={}
 for c in m.consensus_commitments:
  idx=c.output_index
  if idx in declared_by_index or idx>=len(coin['outs']):return False
  out=coin['outs'][idx]
  if out[1]!=bytes(c.script_pub_key) or out[0]!=0:return False
  cls=commitment_class(out[1])
  if cls is None or cls not in allowed:return False
  declared_by_index[idx]=out
 # Every BIP141-pattern output is an explicitly declared consensus output; there is no implicit fallback path.
 if any(i not in declared_by_index for i in commitment_indices):return False
 remaining=list(coin['outs'])
 for o in direct+list(declared_by_index.values()):
  if o not in remaining:return False
  remaining.remove(o)
 if remaining:return False
 return bytes(m.candidate_id)==uuid.UUID(v['candidate_id']).bytes and m.submission_state==1
assert validate_candidate(P['bitcoin_direct_candidate_legacy'])
assert validate_candidate(P['bitcoin_direct_candidate_segwit'])
# Executed negative evidence mutations and policy regressions.
def with_mutation(v,mut):
 x=copy.deepcopy(v);m=BC();m.ParseFromString(bytes.fromhex(x['payload_hex']));mut(m);x['payload_hex']=m.SerializeToString().hex();return x
assert not validate_candidate(with_mutation(P['bitcoin_direct_candidate_legacy'],lambda m:setattr(m,'gross_reward_satoshis',m.gross_reward_satoshis+1)))
assert not validate_candidate(with_mutation(P['bitcoin_direct_candidate_legacy'],lambda m:setattr(m,'block_hash',bytes([m.block_hash[0]^1])+m.block_hash[1:])))
assert not validate_candidate(with_mutation(P['bitcoin_direct_candidate_segwit'],lambda m:m.ClearField('consensus_commitments')))
assert not validate_candidate(with_mutation(P['bitcoin_direct_candidate_segwit'],lambda m:setattr(m,'block_height',m.block_height+1)))
disallowed=copy.deepcopy(P['bitcoin_direct_candidate_segwit']);disallowed['network_parameters']['allowed_consensus_commitment_classes']=[];assert not validate_candidate(disallowed)
dupe_decl=with_mutation(P['bitcoin_direct_candidate_segwit'],lambda m:m.consensus_commitments.add().CopyFrom(m.consensus_commitments[0]));assert not validate_candidate(dupe_decl)
# Construct CVE-2012-2459 pair: [A,B,C] and [A,B,C,C] have same Merkle root, but duplicate txids MUST reject mutant.
def simple_tx(tag):
 prev=bytes([tag])*32;return b'\x01\x00\x00\x00'+b'\x01'+prev+b'\x00\x00\x00\x00'+b'\x00'+b'\xff\xff\xff\xff'+b'\x01'+(1).to_bytes(8,'little')+b'\x01\x51'+b'\x00\x00\x00\x00'
def cve_candidate(duplicate):
 basev=copy.deepcopy(P['bitcoin_direct_candidate_legacy']);m=BC();m.ParseFromString(bytes.fromhex(basev['payload_hex']));old=bytes(m.serialized_block);_,p=rv(old,80);coin=parse_tx(old,p);b=simple_tx(1);c=simple_tx(2);txraw=[coin['full'],b,c]+([c] if duplicate else []);txids=[h2(parse_tx(t,0)['nonwit']) for t in txraw];header=bytearray(old[:80]);header[36:68]=merkle(txids);block=bytes(header)+ev(len(txraw))+b''.join(txraw);m.serialized_block=block;m.block_hash=h2(bytes(header))[::-1];basev['payload_hex']=m.SerializeToString().hex();return basev
honest=cve_candidate(False);mutant=cve_candidate(True);mh=BC();mh.ParseFromString(bytes.fromhex(honest['payload_hex']));mm=BC();mm.ParseFromString(bytes.fromhex(mutant['payload_hex']));assert mh.block_hash==mm.block_hash and mh.serialized_block!=mm.serialized_block;assert validate_candidate(honest);assert not validate_candidate(mutant)
u=P['candidate_state_update'];m=CS();m.ParseFromString(bytes.fromhex(u['payload_hex']));assert bytes(m.candidate_id)==uuid.UUID(u['candidate_id']).bytes and m.state==2 and m.submission_attempts==1
print('CoreDRP Draft 0.5 profile/accounting/Bitcoin positive and negative vectors: OK')
