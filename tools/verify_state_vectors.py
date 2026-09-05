#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify CoreDRP/1 Draft 0.5 state-machine decision vectors."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];D=json.loads((R/'docs/coredrp-v1-state-vectors.json').read_text(encoding='utf-8'))
def reconnect(x):
 C,Rm,T,E=x['C'],x['R'],x['T'],x['E']
 if not x['same_receiver_id']:return 'RECEIVER_ID_CHANGED'
 if not x['same_incarnation']:return 'RECEIVER_INCARNATION_CHANGED'
 if not x['approved_epoch']:return 'EPOCH_NOT_APPROVED'
 if C>T:return 'SENDER_ROLLBACK'
 if C<Rm:return 'RECEIVER_ROLLBACK'
 if C==0 and Rm==0 and not x.get('genesis_hash_match',True):return 'SPLIT_LOG'
 if C>0 and not x['hash_match']:return 'SPLIT_LOG'
 if C+1<E:return 'RECOVERY_GAP'
 if C>Rm:return 'ADOPT_ACK' if x['receiver_hash_verifiable'] else 'SPLIT_LOG'
 return 'RESUME'
for x in D['reconnect_cases']:assert reconnect(x)==x['expected'],x
def repin(x):
 if not x['approved']:return 'DENY'
 if not x['hash_match']:return 'SPLIT_LOG'
 if x['C']>x['T']:return 'SENDER_ROLLBACK'
 if x['C']<x['R']:return 'REPLAY_AND_REPIN' if x.get('lost_acked_history_retained') else 'RECOVERY_GAP'
 if x['C']>x['R']:return 'ADOPT_AND_REPIN' if x['hash_verifiable'] else 'SPLIT_LOG'
 return 'REPIN'
for x in D['receiver_replacement_cases']:assert repin(x)==x['expected'],x
for x in D['admission_idempotency']:
 if x['case_kind']=='same_key_same_digest':
  assert x['stored_digest']==x['retry_digest'] and x['first_relay_event_id']==x['retry_relay_event_id'] and x['expected']=='RETURN_ORIGINAL'
 elif x['case_kind']=='same_key_different_digest':assert x['stored_digest']!=x['retry_digest'] and x['expected']=='IDEMPOTENCY_KEY_CONFLICT'
 elif x['case_kind']=='same_key_different_lane':assert x['lane']!=x['stored_lane'] and x['expected']=='DISTINCT_NAMESPACE'
 else:raise AssertionError(x)
for x in D['epoch_cases']:
 k=x['case_kind']
 if k=='normal':got='ALLOW_NORMAL_TRANSITION' if x['C']==x['R']==x['T']==x['final_sequence'] and x['hashes_match'] else 'DENY_NORMAL_TRANSITION'
 elif k in {'exceptional_exact','exceptional_wildcard'}:
  ok=x['R']==x['C'] and x['gap_first']==x['C']+1 and x['gap_last']==x['T'] and ((k=='exceptional_exact' and x['scope_attribution_complete'] and x['gap_scope']!='*') or (k=='exceptional_wildcard' and not x['scope_attribution_complete'] and x['gap_scope']=='*'))
  got='ALLOW_EXCEPTIONAL_TRANSITION' if ok else 'DENY_EXCEPTIONAL_TRANSITION'
 elif k=='retired_import':got='RESOLVED_RECONCILED' if x['retired_epoch'] and x['chain_verified'] and x['range_verified'] and x['effects_idempotent'] else 'DENY'
 else:raise AssertionError(x)
 assert got==x['expected'],x
for x in D['membership_event_cases']:
 got='ACCEPT' if x['transport_authorized'] and (x['mode']!='RELAY_REQUIRED' or x['membership_covers_event']) else 'TEMPORAL_MEMBERSHIP_REQUIRED'
 assert got==x['expected'],x
for x in D['checkpoint_authorization_cases']:
 got='ACCEPT' if all(s['authorized'] for s in x['covered_scopes']) else 'UNAUTHORIZED_SCOPE';assert got==x['expected'],x
for x in D['gap_relevance_cases']:
 got=x['gap_scope']=='*' or x['gap_scope']==x['query_scope'];assert got==x['expected_relevant'],x
def clock(x):
 if x.get('no_sample'):return 'UNKNOWN'
 L,U,S=x['L'],x['U'],x['S']
 if L>=-S and U<=S:return 'GOOD'
 if U < -S or L > S:return 'BAD'
 return 'UNKNOWN'
for x in D['clock_cases']:assert clock(x)==x['expected'],x
for x in D['clock_state_updates']:
 if x['generation']<=x['last_generation']:got='IGNORE'
 elif x['age_ms']>x['valid_for_ms']:got='UNKNOWN'
 else:got=x['state']
 assert got==x['expected'],x
MAX_T=253402300799999
for x in D['time_cases']:
 if x['case_kind']=='overflow_b_plus_2s':
  got='REJECT_OVERFLOW' if x['B'] > (2**63-1) - 2*x['S'] else 'ACCEPT'
 else:got='ACCEPT' if 0<=x['event_time']<=MAX_T else 'REJECT'
 assert got==x['expected'],x
for x in D['scope_contract_ownership']:
 typ=int(x['event_type'],16);need_mc=typ in {0x0200,0x0201,0x0202};got='ACCEPT' if x['has_mining'] and (x['has_miningcore'] or not need_mc) else 'SEMANTIC_CONTRACT_MISMATCH';assert got==x['expected'],x
f=D['flow_control'];charge=sum(f['fixed_event_charge']+e['scope_len']+e['payload_len'] for e in f['events']);assert charge==f['expected_charge'];assert f['window_bytes_zero_pauses'] and f['window_events_zero_pauses']
for x in D['membership_interval_cases']:
 if x['case_kind']=='deactivation_final_required':got=x['final_checkpoint']>=x['until']-1
 else:got=x['from']<=x['T']<x['until']
 assert got==x['expected'],x
print('CoreDRP/1 Draft 0.5 state-machine vectors: OK')
