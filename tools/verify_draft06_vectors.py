#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-draft06-vectors.json').read_text())
H=lambda b:hashlib.sha256(b).digest();u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n)
def lp16(b):return u16(len(b))+b

# Normative registries must be incorporated.
contracts=(R/'docs/coredrp-v1-draft06-contracts.md').read_text()
for reg in ('coredrp-v1-clock-state.md','coredrp-v1-temporal-policy.md','coredrp-v1-settlement-safety.md','coredrp-v1-settlement-scheme-policies.md','coredrp-v1-producer-lifecycle.md','coredrp-v1-profile-transitions.md','coredrp-v1-quarantine-safety.md'):
 assert reg in contracts,reg

# Compatibility.
for x in D['compatibility_cases']:
 k=x['case_kind']
 if k=='core_1_1':got='CORE_1_1' if x['peer_core_minor']==1 else 'PROTOCOL_VERSION_MISMATCH'
 elif k=='core_1_0_peer':got='PROTOCOL_VERSION_MISMATCH'
 elif k=='mining_1_1':got='ACCEPT' if tuple(x['core'])>=tuple(x['minimum_core']) else 'REJECT'
 elif k=='miningcore_requires_mining':got='ACCEPT' if x['mining_selected'] else 'REJECT'
 else:raise AssertionError(x)
 assert got==x['expected'],x

# Published digests.
for group in ('semantic_contracts','network_policies','settlement_policies'):
 for name,obj in D[group].items():
  assert H(bytes.fromhex(obj['source_hex'])).hex()==obj['sha256'],(group,name)

# Structured epoch binding reconstruction.
c=D['contract_binding'];profiles=[]
for p in sorted(c['profile_entries'],key=lambda x:(x['profile_id'].encode('ascii'),x['major'],x['minor'])):
 pid=p['profile_id'].encode('ascii');entry=lp16(pid)+u32(p['major'])+u32(p['minor'])+bytes([1 if p['has_digest'] else 0])
 if p['has_digest']:
  dg=bytes.fromhex(p['digest_hex']);assert len(dg)==32;entry+=dg
 profiles.append(entry)
scopes=[]
for s in sorted(c['scope_contracts'],key=lambda x:(bytes.fromhex(x['scope_hex']),x['profile_id'].encode('ascii'),x['major'],x['minor'])):
 scope=bytes.fromhex(s['scope_hex']);pid=s['profile_id'].encode('ascii');dg=bytes.fromhex(s['digest_hex']);assert len(dg)==32
 scopes.append(lp16(scope)+lp16(pid)+u32(s['major'])+u32(s['minor'])+dg)
events=sorted(c['event_types']);assert events==sorted(set(events)) and all(0<=e<=0xffff for e in events)
pre=b'CoreDRP1-CONTRACT'+u32(c['core_major'])+u32(c['core_minor'])+bytes([c['lane']])+u16(len(profiles))+b''.join(profiles)+u16(len(scopes))+b''.join(scopes)+u16(len(events))+b''.join(u16(e) for e in events)
assert pre.hex()==c['preimage_hex'];assert H(pre).hex()==c['sha256']

# Producer/idempotency lifecycle.
for x in D['idempotency_generation_cases']:
 k=x['case_kind']
 if k=='new_next_sequence':got='ADMIT_NEW' if x['request_generation']==x['active_generation'] and x['request_sequence']==x['last_new_sequence']+1 else 'REJECT'
 elif k=='retired_generation':got='CALLER_ADMISSION_GENERATION_RETIRED' if x['request_generation']<=x['retired_high_water'] else 'REJECT'
 elif k=='retired_producer_reregister':got='PRODUCER_UUID_RETIRED' if x['producer_tombstoned'] else 'REGISTER'
 elif k=='contract_change_active_generation':got='SEAL_BEFORE_CONTRACT_TRANSITION' if x['old_contract']!=x['new_contract'] and x['active_generation_open'] else 'CONTINUE'
 elif k=='contract_same_active_generation':got='CONTINUE' if x['old_contract']==x['new_contract'] else 'REJECT'
 else:raise AssertionError(x)
 assert got==x['expected'],x

# Deterministic clock classification families.
for x in D['clock_state_cases']:
 state,reason=x['state'],x['reason']
 if reason=='SENDER_PROCESSING_LIMIT' and x.get('processing_exceeded'):
  got='BAD' if state=='BAD' and x.get('probe') else 'CLOCK_CONTRACT_VIOLATION'
 elif reason=='PROBE_EVIDENCE':
  got=state if x.get('probe') and x.get('bounds')==state else 'CLOCK_CONTRACT_VIOLATION'
 elif reason=='RECEIVER_WALL_STEP':got='BAD' if state=='BAD' and not x.get('probe') else 'CLOCK_CONTRACT_VIOLATION'
 else:got='CLOCK_CONTRACT_VIOLATION'
 assert got==x['expected'],x

# Deterministic RequiredStagingSender.
for x in D['staging_sender_cases']:
 k=x['case_kind']
 if k in ('membership_start','membership_end'):got=[x['sender']]
 elif k=='mode_required_to_none':got=sorted(x['members_t_minus_1'])
 elif k=='mode_none_to_required':got=sorted(x['members_t'])
 else:raise AssertionError(x)
 assert got==x['expected'],x

# applicable_clock_uncertainty = 2*max effective skew.
for x in D['clock_uncertainty_cases']:
 got=0 if not x['effective_skews_ms'] else 2*max(x['effective_skews_ms'])
 assert got==x['expected_ms'],x

# Settlement-specific pruning.
for x in D['settlement_prune_cases']:
 got=bool(x['all_settlements_final'] and not x['intersects_unsafe_audit'] and not x['live_dependencies'] and x['proof_summarized'] and x['scheme_allows'])
 assert got==x['expected'],x

# Financial quarantine lifecycle.
for x in D['quarantine_cases']:
 payout_significant=x['event_type'] in (0x0100,0x0200)
 got=bool(payout_significant and x['state']=='RESOLVED_RECONCILED')
 assert got==x['expected_settlement_safe'],x

# Financial semantic-contract transition barrier.
for x in D['profile_transition_cases']:
 changed=x['old_mining']!=x['new_mining'] or x['old_mc']!=x['new_mc']
 got='ALLOW' if not changed or x['old_state_closed'] else 'ADMIN_ACTION_CONFLICT'
 assert got==x['expected'],x

# Temporal reconciliation cross-field constraints.
for x in D['temporal_reconciliation_cases']:
 valid=x['same_scope'] and x['new_generation_matches_admin'] and x['non_overlapping']
 if x['correction_kind']==3:valid=valid and x['same_sender'] and x['same_valid_from']
 got='ACCEPT' if valid else 'ADMIN_ACTION_CONFLICT'
 assert got==x['expected'],x

print('CoreDRP Draft 0.6 profile-freeze vectors: OK')
