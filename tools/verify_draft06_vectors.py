#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/coredrp-v1-draft06-vectors.json').read_text())
H=lambda b:hashlib.sha256(b).digest();u16=lambda n:struct.pack('>H',n);u32=lambda n:struct.pack('>I',n)
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
# Contract binding exact preimage
c=D['contract_binding'];assert H(bytes.fromhex(c['preimage_hex'])).hex()==c['sha256']
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
# Clock state validity / BAD latch
for x in D['clock_state_cases']:
 k=x['case_kind']
 if k=='expired_bad_latched':got='RECOVERING'
 elif k.startswith('bad_recovery_'):
  got='GOOD' if x['fresh_good_count']>=3 and x['spans_probe_interval'] and x['utc_not_behind'] else 'RECOVERING'
 else:
  last=0 if x.get('new_stream') else x.get('last_generation',0)
  if x['generation']<=last:got='IGNORE'
  elif not 1<=x['valid_for_ms']<=x['effective_expiry_ms']:got='CLOCK_CONTRACT_VIOLATION'
  elif x['reported_skew_ms']!=x['bound_skew_ms']:got='CLOCK_CONTRACT_VIOLATION'
  elif x['state']=='GOOD' and not (-x['bound_skew_ms']<=x['lower']<=x['upper']<=x['bound_skew_ms']):got='CLOCK_CONTRACT_VIOLATION'
  elif x['state']=='BAD' and not (x['upper'] < -x['bound_skew_ms'] or x['lower'] > x['bound_skew_ms']):got='CLOCK_CONTRACT_VIOLATION'
  else:got=x['state']
 assert got==x['expected'],x
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
