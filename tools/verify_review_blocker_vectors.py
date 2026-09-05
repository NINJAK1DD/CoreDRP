#!/usr/bin/env python3
from pathlib import Path
from fractions import Fraction
import hashlib,json,struct
from financial_semantics import effect_bytes, participant_bytes
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-review-blocker-vectors.json').read_text())
H=lambda b:hashlib.sha256(b).digest()
u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n);u64=lambda n:struct.pack('>Q',n);i64=lambda n:struct.pack('>q',n)

# Exact binary64 * canonical decimal rational, then one roundTiesToEven to binary64.
def bits_float(h): return struct.unpack('>d',bytes.fromhex(h))[0]
def float_hex(x): return struct.pack('>d',x).hex()
def decimal_fraction(s):
    if '.' in s:
        a,b=s.split('.',1); return Fraction(int(a+b),10**len(b))
    return Fraction(int(s),1)
x=D['difficulty_adjustment']; d=bits_float(x['input_binary64_bits_hex'])
exact=Fraction.from_float(d)*decimal_fraction(x['multiplier_decimal'])
required=float(exact)
assert float_hex(required)==x['required_output_binary64_bits_hex']
naive=d*float(x['multiplier_decimal'])
assert float_hex(naive)==x['forbidden_double_rounded_output_bits_hex']
assert float_hex(required)!=float_hex(naive)

# Registered validator authority digest.
a=D['validator_authority']; aid=a['authority_id'].encode('ascii'); ets=sorted(a['event_types'])
assert ets==sorted(set(ets)) and all(0<=e<=0xffff for e in ets)
asrc=u16(1)+u16(len(aid))+aid+u32(a['major'])+u32(a['minor'])+u16(len(ets))+b''.join(u16(e) for e in ets)
assert asrc.hex()==a['source_hex']; assert H(asrc).hex()==a['sha256']

# SettlementEvidenceSummaryV1 exact byte reconstruction.
s=D['settlement_summary']
source=effect_bytes(s,s['effect_source'])
assert source.hex()==s['effect_identity_preimage_hex']
assert H(source).hex()==s['effect_identity_digest32']
participant=participant_bytes(s,s['effect_source'])
assert participant.hex()==s['participant_record_hex']
pdsrc=u16(1)+u32(1)+u32(len(participant))+participant
assert H(pdsrc).hex()==s['participant_effects_digest32']
sender=bytes.fromhex(s['required_sender_uuid_hex']); assert len(sender)==16
rssrc=u16(1)+u32(1)+sender
assert H(rssrc).hex()==s['required_sender_set_digest32']
checkpoint=bytes.fromhex(s['checkpoint_record_hex'])
cpsrc=u16(1)+u32(1)+u32(len(checkpoint))+checkpoint
assert H(cpsrc).hex()==s['checkpoint_evidence_digest32']
assert s['uncertainty_record_count']==0
usrc=u16(1)+u32(0)
assert H(usrc).hex()==s['uncertainty_snapshot_digest32']
scope=s['scope'].encode('ascii'); sid=bytes.fromhex(s['settlement_id_hex'])
summary=(u16(1)+u16(len(scope))+scope+u16(len(sid))+sid+bytes([s['payout_scheme']])+
 bytes.fromhex(s['settlement_scheme_policy_digest32'])+bytes.fromhex(s['share_difficulty_adjustment_policy_digest32'])+
 bytes.fromhex(s['mining_scope_contract_digest32'])+bytes.fromhex(s['miningcore_scope_contract_digest32'])+
 i64(s['evidence_from_unix_ms'])+i64(s['evidence_through_unix_ms'])+
 u32(1)+bytes.fromhex(s['participant_effects_digest32'])+u32(1)+bytes.fromhex(s['required_sender_set_digest32'])+
 u32(1)+bytes.fromhex(s['checkpoint_evidence_digest32'])+u32(0)+bytes.fromhex(s['uncertainty_snapshot_digest32'])+
 u64(s['receiver_state_version'])+i64(s['proved_at_unix_ms']))
assert summary.hex()==s['summary_hex']; assert H(summary).hex()==s['summary_sha256']
print('CoreDRP Draft 0.6 review-blocker vectors: OK')
