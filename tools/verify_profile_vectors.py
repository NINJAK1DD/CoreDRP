#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify current Mining 1.1 / Miningcore 1.1 accounting and Bitcoin semantics."""
from pathlib import Path
import hashlib,json,math,uuid,re,sys,copy
from financial_semantics import projection_pps
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory
R=Path(__file__).resolve().parents[1];desc=R/'.build/coredrp.pb'
if not desc.exists():print('profile-vector prerequisite missing: run protoc descriptor build before this verifier',file=sys.stderr);raise SystemExit(2)
D=json.loads((R/'docs/coredrp-v1-test-vectors.json').read_text())
A_VEC=json.loads((R/'docs/coredrp-v1-accounting-vectors.json').read_text())
B_VEC=json.loads((R/'docs/coredrp-v1-bitcoin-profile-vectors.json').read_text())
fds=descriptor_pb2.FileDescriptorSet();fds.ParseFromString(desc.read_bytes());pool=descriptor_pool.DescriptorPool();pending=list(fds.file)
while pending:
 progress=False
 for fd in pending[:]:
  try:pool.Add(fd);pending.remove(fd);progress=True
  except Exception:pass
 if not progress:raise RuntimeError('descriptor dependency load failed')
def C(n):return message_factory.GetMessageClass(pool.FindMessageTypeByName(n))
S=C('coredrp.mining.v1.MiningShareEvent');CP=C('coredrp.v1.CompletenessCheckpoint');A=C('coredrp.miningcore.v1.MiningcoreAccountingShareEvent');BC=C('coredrp.miningcore.v1.BitcoinDirectCoinbaseCandidate');CS=C('coredrp.miningcore.v1.CandidateStateUpdate')
SCOPE_RE=re.compile(rb'^[A-Za-z0-9._-]{1,64}$')
def valid_share(m,tm,lane=0,scope=b'btc1'):
 if lane!=0 or not SCOPE_RE.fullmatch(scope) or m.created_unix_ms!=tm or not m.miner:return False
 vals=[m.difficulty,m.achieved_share_difficulty,m.actual_difficulty,m.network_difficulty]
 if not all(math.isfinite(x) for x in vals):return False
 if not (m.difficulty>0 and m.actual_difficulty>0 and m.network_difficulty>0 and m.achieved_share_difficulty>=0):return False
 candidate_fields=m.HasField('candidate_hash') or m.HasField('candidate_kind') or m.HasField('transaction_confirmation_data') or m.HasField('block_reward')
 return (m.is_block_candidate and m.HasField('candidate_hash') and bool(m.candidate_hash)) or (not m.is_block_candidate and not candidate_fields)
def canonical_decimal(s):return bool(re.fullmatch(r'(?:0|[1-9][0-9]{0,13})(?:\.[0-9]{0,23}[1-9])?',s)) and len(s.replace('.',''))<=38
def valid_projection(p,tm,paired=False):
 scope=bytes(p.scope)
 if not SCOPE_RE.fullmatch(scope) or not p.HasField('share') or not valid_share(p.share,tm,0,scope):return False
 if paired and p.accounting_role!=3:return False
 if not paired and p.accounting_role not in (1,2):return False
 if not p.preserve_created:return False
 if p.HasField('accounting_id') and not p.accounting_id:return False
 if p.HasField('reward_basis_satoshis') and p.reward_basis_satoshis<=0:return False
 # All seeds in this corpus select PPLNS, not PPS.
 try:projection_pps(p,{'scheme':1})
 except ValueError:return False
 if p.block_only and (not p.block_record_emitted or p.statistical_record_emitted):return False
 if p.statistical_record_emitted and p.block_only:return False
 return True
def valid_accounting(m,tm,outer_scope):
 if not m.HasField('primary') or not valid_projection(m.primary,tm):return False
 if bytes(m.primary.scope)!=outer_scope:return False
 if m.primary.accounting_role==1 and m.HasField('paired'):return False
 if m.primary.accounting_role==2 and not m.HasField('paired'):return False
 if m.HasField('paired'):
  if not valid_projection(m.paired,tm,True):return False
  if bytes(m.paired.scope)==bytes(m.primary.scope):return False
  if not m.primary.HasField('accounting_id') or not m.paired.HasField('accounting_id') or not m.primary.accounting_id or m.primary.accounting_id!=m.paired.accounting_id:return False
  shared=lambda p:(p.share.worker,p.share.user_agent,p.share.source_ip,p.share.source,p.share.session_id,p.share.created_unix_ms,p.share.achieved_share_difficulty)
  if shared(m.primary)!=shared(m.paired):return False
 return True
# Current profile seed events.
for e in D['chains'][0]['events']:
 et=int(e['event_type'],16);raw=bytes.fromhex(e['payload_hex']);tm=int(e['event_time_unix_ms']);scope=bytes.fromhex(e['scope_hex'])
 if et==0x0100:
  m=S();m.ParseFromString(raw);assert valid_share(m,tm,0,scope)
 elif et==1:
  m=CP();m.ParseFromString(raw);assert m.complete_through_unix_ms==tm and scope==b''
 elif et==0x0200:
  m=A();m.ParseFromString(raw);assert valid_accounting(m,tm,scope)
# Executed accounting-v2 positive/negative cases.
av=A();av.ParseFromString(bytes.fromhex(A_VEC['parent_aux']['payload_hex']));atm=A_VEC['parent_aux']['event_time_unix_ms'];outer=A_VEC['parent_aux']['outer_scope'].encode();assert valid_accounting(av,atm,outer)
assert av.primary.accounting_id==av.paired.accounting_id and av.primary.share.miner!=av.paired.share.miner
for x in A_VEC['invalid_cases']:
 m=A();m.CopyFrom(av);k=x['case_kind']
 if k=='different_accounting_id':m.paired.accounting_id=b'\x01'*16
 elif k=='same_scope':m.paired.scope=m.primary.scope
 elif k=='primary_scope_not_outer':m.primary.scope=b'btc'
 elif k=='paired_same_miner_allowed':m.paired.share.miner=m.primary.share.miner
 elif k=='different_worker':m.paired.share.worker='other'
 elif k=='different_user_agent':m.paired.share.user_agent='other'
 elif k=='different_source_ip':m.paired.share.source_ip='198.51.100.1'
 elif k=='different_source':m.paired.share.source='other'
 elif k=='different_session':m.paired.share.session_id='other'
 elif k=='different_created':m.paired.share.created_unix_ms+=1
 elif k=='different_achieved_share_difficulty':m.paired.share.achieved_share_difficulty+=1
 else:raise AssertionError(k)
 got='VALID' if valid_accounting(m,atm,outer) else 'SEMANTIC_PAYLOAD_INVALID';assert got==x['expected'],x
# Mining share negative regressions.
base=S();base.ParseFromString(bytes.fromhex(D['chains'][0]['events'][0]['payload_hex']));tm=D['chains'][0]['events'][0]['event_time_unix_ms']
m=S();m.CopyFrom(base);m.difficulty=0.0;assert not valid_share(m,tm)
m=S();m.CopyFrom(base);m.is_block_candidate=False;m.candidate_hash=b'\x00';assert not valid_share(m,tm)
# Bitcoin evidence helpers.
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
def commitment_class(script):return 'BIP141' if len(script)>=38 and script[:6]==bytes.fromhex('6a24aa21a9ed') else None
def validate_candidate(v):
 m=BC();m.ParseFromString(bytes.fromhex(v['payload_hex']));block=bytes(m.serialized_block);params=v.get('network_parameters')
 if not isinstance(params,dict) or params.get('direct_candidate_validation_version')!=2:return False
 activation=params.get('bip34_activation_height');allowed=set(params.get('allowed_consensus_commitment_classes',[]))
 if not isinstance(activation,int) or activation<0 or len(block)<81 or len(block)>4_000_000:return False
 if h2(block[:80])[::-1]!=bytes(m.block_hash):return False
 count,pos=rv(block,80);txs=[]
 for _ in range(count):t=parse_tx(block,pos);txs.append(t);pos=t['end']
 if pos!=len(block) or not txs:return False
 coin=txs[0]
 if len(coin['inputs'])!=1 or coin['inputs'][0][0]!=b'\x00'*32 or coin['inputs'][0][1]!=0xffffffff:return False
 txids=[h2(t['nonwit']) for t in txs]
 if len(set(txids))!=len(txids) or txids[0][::-1]!=bytes(m.coinbase_txid) or merkle(txids)!=block[36:68]:return False
 if m.block_height>=activation and scriptnum_minimal(coin['inputs'][0][2])!=m.block_height:return False
 magic=bytes.fromhex('6a24aa21a9ed');commitment_indices=[i for i,(_,script) in enumerate(coin['outs']) if len(script)>=38 and script[:6]==magic]
 witness=any(t['segwit'] for t in txs)
 if witness and not commitment_indices:return False
 if commitment_indices:
  idx=max(commitment_indices)
  if not coin['segwit'] or not coin['witnesses'] or not coin['witnesses'][0] or len(coin['witnesses'][0][0])!=32:return False
  expected=h2(merkle([b'\x00'*32]+[h2(t['full']) for t in txs[1:]])+coin['witnesses'][0][0])
  if coin['outs'][idx][1][6:38]!=expected:return False
 if sum(v for v,_ in coin['outs'])!=m.gross_reward_satoshis:return False
 direct=[(m.miner_reward_satoshis,bytes(m.miner_script_pub_key))]+[(r.amount_satoshis,bytes(r.script_pub_key)) for r in m.recipients]
 declared={}
 for c in m.consensus_commitments:
  idx=c.output_index
  if idx in declared or idx>=len(coin['outs']):return False
  out=coin['outs'][idx]
  if out[1]!=bytes(c.script_pub_key) or out[0]!=0:return False
  cls=commitment_class(out[1])
  if cls is None or cls not in allowed:return False
  declared[idx]=out
 if any(i not in declared for i in commitment_indices):return False
 remaining=list(coin['outs'])
 for o in direct+list(declared.values()):
  if o not in remaining:return False
  remaining.remove(o)
 return not remaining and bytes(m.candidate_id)==uuid.UUID(v['candidate_id']).bytes and m.submission_state==1
assert validate_candidate(B_VEC['bitcoin_direct_candidate_legacy']);assert validate_candidate(B_VEC['bitcoin_direct_candidate_segwit'])
def with_mutation(v,mut):
 x=copy.deepcopy(v);m=BC();m.ParseFromString(bytes.fromhex(x['payload_hex']));mut(m);x['payload_hex']=m.SerializeToString().hex();return x
assert not validate_candidate(with_mutation(B_VEC['bitcoin_direct_candidate_legacy'],lambda m:setattr(m,'gross_reward_satoshis',m.gross_reward_satoshis+1)))
assert not validate_candidate(with_mutation(B_VEC['bitcoin_direct_candidate_legacy'],lambda m:setattr(m,'block_hash',bytes([m.block_hash[0]^1])+m.block_hash[1:])))
assert not validate_candidate(with_mutation(B_VEC['bitcoin_direct_candidate_segwit'],lambda m:m.ClearField('consensus_commitments')))
assert not validate_candidate(with_mutation(B_VEC['bitcoin_direct_candidate_segwit'],lambda m:setattr(m,'block_height',m.block_height+1)))
disallowed=copy.deepcopy(B_VEC['bitcoin_direct_candidate_segwit']);disallowed['network_parameters']['allowed_consensus_commitment_classes']=[];assert not validate_candidate(disallowed)
# CVE-2012-2459 class duplicate txid pair.
def simple_tx(tag):
 prev=bytes([tag])*32;return b'\x01\x00\x00\x00'+b'\x01'+prev+b'\x00\x00\x00\x00'+b'\x00'+b'\xff\xff\xff\xff'+b'\x01'+(1).to_bytes(8,'little')+b'\x01\x51'+b'\x00\x00\x00\x00'
def cve_candidate(duplicate):
 x=copy.deepcopy(B_VEC['bitcoin_direct_candidate_legacy']);m=BC();m.ParseFromString(bytes.fromhex(x['payload_hex']));old=bytes(m.serialized_block);_,p=rv(old,80);coin=parse_tx(old,p);b=simple_tx(1);c=simple_tx(2);raw=[coin['full'],b,c]+([c] if duplicate else []);ids=[h2(parse_tx(t,0)['nonwit']) for t in raw];header=bytearray(old[:80]);header[36:68]=merkle(ids);block=bytes(header)+ev(len(raw))+b''.join(raw);m.serialized_block=block;m.block_hash=h2(bytes(header))[::-1];x['payload_hex']=m.SerializeToString().hex();return x
honest=cve_candidate(False);mutant=cve_candidate(True);mh=BC();mh.ParseFromString(bytes.fromhex(honest['payload_hex']));mm=BC();mm.ParseFromString(bytes.fromhex(mutant['payload_hex']));assert mh.block_hash==mm.block_hash and validate_candidate(honest) and not validate_candidate(mutant)
u=B_VEC['candidate_state_update'];m=CS();m.ParseFromString(bytes.fromhex(u['payload_hex']));assert bytes(m.candidate_id)==uuid.UUID(u['candidate_id']).bytes and m.state==2 and m.submission_attempts==1
print('CoreDRP Mining 1.1 / Miningcore 1.1 accounting and Bitcoin vectors: OK')
