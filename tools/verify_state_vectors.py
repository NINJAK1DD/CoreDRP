#!/usr/bin/env python3
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];D=json.loads((R/'docs/coredrp-v1-state-vectors.json').read_text())
def reconnect(x):
 C,R,T,E=x['C'],x['R'],x['T'],x['E']
 if not x['same_receiver_id']:return 'RECEIVER_ID_CHANGED'
 if not x['same_incarnation']:return 'RECEIVER_INCARNATION_CHANGED'
 if not x['approved_epoch']:return 'EPOCH_NOT_APPROVED'
 if C>T:return 'SENDER_ROLLBACK'
 if C<R:return 'RECEIVER_ROLLBACK'
 if C==0 and R==0 and not x.get('genesis_hash_match',True):return 'SPLIT_LOG'
 if C>0 and not x['hash_match']:return 'SPLIT_LOG'
 if C+1<E:return 'RECOVERY_GAP'
 if C>R:return 'ADOPT_ACK' if x['receiver_hash_verifiable'] else 'SPLIT_LOG'
 return 'RESUME'
for x in D['reconnect_cases']:assert reconnect(x)==x['expected'],x
for x in D['receiver_replacement_cases']:
 if not x['approved']:got='DENY'
 elif not x['hash_match']:got='SPLIT_LOG'
 elif x['C']>x['T']:got='SENDER_ROLLBACK'
 elif x['C']<x['R']:got='REPLAY_AND_REPIN' if x.get('lost_acked_history_retained') else 'RECOVERY_GAP'
 elif x['C']>x['R']:got='ADOPT_AND_REPIN' if x['hash_verifiable'] else 'SPLIT_LOG'
 else:got='REPIN'
 assert got==x['expected'],x
for x in D['epoch_cases']:
 k=x['case_kind']
 if k=='normal':got='ALLOW_NORMAL_TRANSITION' if x['C']==x['R']==x['T']==x['final_sequence'] and x['hashes_match'] else 'DENY_NORMAL_TRANSITION'
 elif k in {'exceptional_exact','exceptional_wildcard','exceptional_missing_atomic_gap'}:
  scope_ok=(k=='exceptional_exact' and x['scope_attribution_complete'] and x['gap_scope']!='*') or (k=='exceptional_wildcard' and not x['scope_attribution_complete'] and x['gap_scope']=='*') or k=='exceptional_missing_atomic_gap'
  ok=x['R']==x['C'] and x['gap_first']==x['C']+1 and x['gap_last']==x['T'] and scope_ok and x['atomic_gap_and_retire']
  got='ALLOW_EXCEPTIONAL_TRANSITION' if ok else 'DENY_EXCEPTIONAL_TRANSITION'
 elif k=='retired_import':got='RESOLVED_RECONCILED' if x['retired_epoch'] and x['chain_verified'] and x['range_verified'] and x['effects_idempotent'] else 'DENY'
 else:raise AssertionError(x)
 assert got==x['expected'],x
for x in D['membership_event_cases']:
 got='ACCEPT' if x['transport_authorized'] and (x['mode']!='RELAY_REQUIRED' or x['membership_covers_event']) else 'TEMPORAL_MEMBERSHIP_REQUIRED';assert got==x['expected'],x
for x in D['checkpoint_authorization_cases']:
 got='ACCEPT' if all(s['authorized'] for s in x['covered_scopes']) else 'UNAUTHORIZED_SCOPE';assert got==x['expected'],x
for x in D['gap_payout_cases']:
 blocks=x['status'] in {'UNRESOLVED','RESOLVED_WAIVED'};assert blocks==x['expected_blocks_payout'];assert (not blocks)==x['can_advance_frontier']
for x in D['clock_state_updates']:
 k=x['case_kind']
 if k=='bad_expiry_latched':got='RECOVERING'
 elif k=='bad_recovery_three_good':got='GOOD' if x['fresh_good_count']>=3 and x['spans_probe_interval'] and x['utc_not_behind'] else 'RECOVERING'
 else:
  last=0 if x.get('new_stream') else x.get('last_generation',0)
  if x['generation']<=last:got='IGNORE'
  elif x.get('age_ms',0)>x['valid_for_ms']:got='UNKNOWN'
  elif not 1<=x['valid_for_ms']<=x['effective_expiry_ms']:got='CLOCK_CONTRACT_VIOLATION'
  elif x['reported_skew_ms']!=x['bound_skew_ms']:got='CLOCK_CONTRACT_VIOLATION'
  elif (x.get('lower') is None)!=(x.get('upper') is None):got='MALFORMED_FRAME'
  elif x.get('lower') is not None and x['lower']>x['upper']:got='MALFORMED_FRAME'
  elif x['state'] in ('BAD','UNKNOWN') and x.get('lower') is not None:
   from verify_policy_clock_vectors import interval_class
   got=x['state'] if interval_class(x)==x['state'] else 'CLOCK_CONTRACT_VIOLATION'
  elif x['state']=='GOOD' and not (-x['bound_skew_ms']<=x['lower']<=x['upper']<=x['bound_skew_ms']):got='CLOCK_CONTRACT_VIOLATION'
  else:got=x['state']
 assert got==x['expected'],x
MAX_T=253402300799999
for x in D['time_cases']:
 if x['case_kind']=='overflow_b_plus_2s':got='REJECT_OVERFLOW' if not (0<=x['B']<=253402300799999 and 0<=x['S']<=2**32-1 and x['B']<=253402300799999-2*x['S']) else 'ACCEPT'
 else:got='ACCEPT' if 0<=x['event_time']<=MAX_T else 'REJECT'
 assert got==x['expected'],x
for x in D['scope_contract_ownership']:
 typ=int(x['event_type'],16);need_mc=typ in {0x0200,0x0201,0x0202};got='ACCEPT' if x['has_mining'] and (x['has_miningcore'] or not need_mc) else 'SEMANTIC_CONTRACT_MISMATCH';assert got==x['expected'],x
f=D['flow_control'];assert sum(f['fixed_event_charge']+e['scope_len']+e['payload_len'] for e in f['events'])==f['expected_charge'];assert f['window_bytes_zero_pauses'] and f['window_events_zero_pauses']
for x in D['temporal_policy_cases']:
 if x.get('reconciliation'):got='RECORD_UNCERTAINTY_AND_BLOCK_ADVANCE'
 elif x['effective']<=x['payout_safe_through']+x['clock_uncertainty']:got='ADMIN_ACTION_CONFLICT'
 else:got='ACCEPT'
 assert got==x['expected'],x
for x in D['payout_evidence_cases']:
 got=bool(x['receiver_checkpoint_committed'] and x['membership'] and x['clock'] and x['gap_status']=='NONE');assert got==x['expected'],x
print('CoreDRP/1 Draft 0.6 state-machine vectors: OK')
