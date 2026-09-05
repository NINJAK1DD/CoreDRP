#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-draft06-vectors.json').read_text())
H=lambda b:hashlib.sha256(b).digest();u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n)
def lp16(b):return u16(len(b))+b

# Compatibility
for x in D['compatibility_cases']:
 if x['case_kind']=='core_1_1':got='CORE_1_1' if x['peer_core_minor']==1 else 'PROTOCOL_VERSION_MISMATCH'
 elif x['case_kind']=='core_1_0_peer':got='PROTOCOL_VERSION_MISMATCH'
 elif x['case_kind']=='mining_1_1':got='ACCEPT' if tuple(x['core'])>=tuple(x['minimum_core']) else 'REJECT'
 elif x['case_kind']=='miningcore_requires_mining':got='ACCEPT' if x['mining_selected'] else 'REJECT'
 else:raise AssertionError(x)
 assert got==x['expected'],x

# Semantic/network digests
for group in ('semantic_contracts','network_policies'):
 for name,obj in D[group].items():assert H(bytes.fromhex(obj['source_hex'])).hex()==obj['sha256'],(group,name)

# Reconstruct the complete epoch contract binding from structured fields.
c=D['contract_binding']
profiles=[]
for p in sorted(c['profile_entries'],key=lambda x:(x['profile_id'].encode('ascii'),x['major'],x['minor'])):
 pid=p['profile_id'].encode('ascii');entry=lp16(pid)+u32(p['major'])+u32(p['minor'])+bytes([1 if p['has_digest'] else 0])
 if p['has_digest']:
  dg=bytes.fromhex(p['digest_hex']);assert len(dg)==32;entry+=dg
 profiles.append(entry)
scopes=[]
for s in sorted(c['scope_contracts'],key=lambda x:(bytes.fromhex(x['scope_hex']),x['profile_id'].encode('ascii'),x['major'],x['minor'])):
 scope=bytes.fromhex(s['scope_hex']);pid=s['profile_id'].encode('ascii');dg=bytes.fromhex(s['digest_hex']);assert len(dg)==32
 scopes.append(lp16(scope)+lp16(pid)+u32(s['major'])+u32(s['minor'])+dg)
events=sorted(c['event_types']);assert len(events)==len(set(events)) and all(0<=e<=0xffff for e in events)
reconstructed=(b'CoreDRP1-CONTRACT'+u32(c['core_major'])+u32(c['core_minor'])+bytes([c['lane']])+u16(len(profiles))+b''.join(profiles)+u16(len(scopes))+b''.join(scopes)+u16(len(events))+b''.join(u16(e) for e in events))
assert reconstructed.hex()==c['preimage_hex'],'contract binding structured reconstruction mismatch'
assert H(reconstructed).hex()==c['sha256'],'contract binding digest mismatch'

# Bounded generation idempotency
for x in D['idempotency_generation_cases']:
 k=x['case_kind']
 if k=='new_next_sequence':got='ADMIT_NEW' if x['request_generation']==x['active_generation'] and x['request_sequence']==x['last_new_sequence']+1 else 'REJECT'
 elif k=='active_retry_same':got='RETURN_ORIGINAL' if x['stored_digest']==x['retry_digest'] else 'IDEMPOTENCY_KEY_CONFLICT'
 elif k=='active_retry_conflict':got='IDEMPOTENCY_KEY_CONFLICT' if x['stored_digest']!=x['retry_digest'] else 'RETURN_ORIGINAL'
 elif k=='retired_generation':got='CALLER_ADMISSION_GENERATION_RETIRED' if x['request_generation']<=x['retired_high_water'] else 'REJECT'
 elif k=='generation_capacity':got='SEAL_BEFORE_NEW_ADMISSION' if x['record_count']>=x['max_records'] else 'ADMIT_NEW'
 elif k=='seal':assert x['all_outcomes_durable'];assert x['expected_new_retired_high_water']==x['active_generation'] and x['expected_new_generation']==x['active_generation']+1;continue
 else:raise AssertionError(x)
 assert got==x['expected'],x

# Exhaustive ClockStateUpdate matrix families plus BAD recovery latch.
def interval_class(x):
 if x.get('lower') is None or x.get('upper') is None:return None
 L,U,S=x['lower'],x['upper'],x['bound_skew_ms']
 if -S<=L<=U<=S:return 'GOOD'
 if U < -S or L > S:return 'BAD'
 return 'UNKNOWN'
def clock_update(x):
 k=x['case_kind']
 if k=='expired_bad_latched':return 'RECOVERING'
 if k.startswith('bad_recovery_'):
  return 'GOOD' if x['fresh_good_count']>=3 and x['spans_probe_interval'] and x['utc_not_behind'] else 'RECOVERING'
 gen=x['generation'];last=0 if x.get('new_stream') else x.get('last_generation',0)
 if gen==0:return 'MALFORMED_FRAME'
 if gen<=last:return 'IGNORE'
 if not 1<=x['valid_for_ms']<=x['effective_expiry_ms']:return 'MALFORMED_FRAME'
 if x['reported_skew_ms']!=x['bound_skew_ms']:return 'CLOCK_CONTRACT_VIOLATION'
 lo,hi=x.get('lower'),x.get('upper')
 if (lo is None)!=(hi is None):return 'MALFORMED_FRAME'
 if lo is not None and lo>hi:return 'MALFORMED_FRAME'
 if x.get('probe_present') and not x.get('probe_valid'):return 'MALFORMED_FRAME'
 state,reason=x['state'],x['reason'];cls=interval_class(x);probe=x.get('probe_present',False);bounds=lo is not None
 if state=='GOOD':
  if reason!='PROBE_EVIDENCE':return 'CLOCK_CONTRACT_VIOLATION'
  if not probe or not bounds:return 'MALFORMED_FRAME'
  return 'GOOD' if cls=='GOOD' else 'CLOCK_CONTRACT_VIOLATION'
 if state=='BAD':
  if reason=='EVIDENCE_EXPIRED':return 'CLOCK_CONTRACT_VIOLATION'
  if reason=='PROBE_EVIDENCE':
   if not probe or not bounds:return 'MALFORMED_FRAME'
   return 'BAD' if cls=='BAD' else 'CLOCK_CONTRACT_VIOLATION'
  if reason=='RECEIVER_WALL_STEP':
   if probe:return 'MALFORMED_FRAME'
   return 'CLOCK_CONTRACT_VIOLATION' if bounds and cls=='GOOD' else 'BAD'
  if reason=='SENDER_PROCESSING_LIMIT':
   if not probe:return 'MALFORMED_FRAME'
   return 'CLOCK_CONTRACT_VIOLATION' if bounds and cls=='GOOD' else 'BAD'
  return 'MALFORMED_FRAME'
 if state=='UNKNOWN':
  if reason=='RECEIVER_WALL_STEP':return 'CLOCK_CONTRACT_VIOLATION'
  if reason=='EVIDENCE_EXPIRED':
   if probe or bounds:return 'MALFORMED_FRAME'
   return 'UNKNOWN'
  if reason=='PROBE_EVIDENCE':
   if not probe or not bounds:return 'MALFORMED_FRAME'
   return 'UNKNOWN' if cls=='UNKNOWN' else 'CLOCK_CONTRACT_VIOLATION'
  if reason=='SENDER_PROCESSING_LIMIT':
   if not probe:return 'MALFORMED_FRAME'
   return 'CLOCK_CONTRACT_VIOLATION' if bounds and cls=='GOOD' else 'UNKNOWN'
  return 'MALFORMED_FRAME'
 return 'MALFORMED_FRAME'
for x in D['clock_state_cases']:assert clock_update(x)==x['expected'],x

# Receiver-observable payout safety and gap status
for x in D['payout_cases']:
 gap_ok=x['gap_status'] in {'NONE','RESOLVED_RECONCILED'}
 got=bool(x['receiver_checkpoint_committed'] and x['membership_complete'] and x['clock_valid'] and gap_ok and x['quarantine_clear'])
 assert got==x['expected'],x

# Policy retroactivity
for x in D['temporal_policy_cases']:
 if x.get('reconciliation'):got='RECORD_UNCERTAINTY_AND_BLOCK_ADVANCE'
 elif x['effective']<=x['payout_safe_through']+x['clock_uncertainty']:got='ADMIN_ACTION_CONFLICT'
 else:got='ACCEPT'
 assert got==x['expected'],x

# ADMIN atomic idempotency ordering
for x in D['admin_idempotency_cases']:
 if x['stored_digest'] is not None:
  got='RETURN_ORIGINAL' if x['stored_digest']==x['retry_digest'] else 'IDEMPOTENCY_KEY_CONFLICT'
 else:got='APPLY_ATOMICALLY' if x['state_version_matches'] else 'ADMIN_ACTION_CONFLICT'
 assert got==x['expected'],x
print('CoreDRP Draft 0.6 freeze vectors: OK')
