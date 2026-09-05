#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify CoreDRP/1 Draft 0.4 state-machine decision vectors."""
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
 if not x['hash_match']:return 'SPLIT_LOG'
 if C+1<E:return 'RECOVERY_GAP'
 if C>Rm:return 'ADOPT_ACK' if x['receiver_hash_verifiable'] else 'SPLIT_LOG'
 return 'RESUME'
for x in D['reconnect_cases']:
 got=reconnect(x);assert got==x['expected'],(x['name'],got,x['expected'])
 if got=='RESUME':assert x['resume_sequence']==x['C']+1
 if got=='ADOPT_ACK':assert x['adopt_sequence']==x['C']
for x in D['wal_crash_cases']:
 if x.get('application_success_sent'):assert x['wal_durable'] and x['event_recoverable']
 if x.get('prune_allowed'):assert x['ack_anchor_durable'] and x['prune_through']<=x['remembered_ack_sequence']
 if not x.get('ack_anchor_durable',False):assert not x.get('prune_allowed',False)
 if x['name']=='wal_durable_before_response':assert x['retry_returns_same_event']
def admission(x):
 if x['age_ms']>x['horizon_ms']:return 'CALLER_RETRY_FORBIDDEN'
 if x['stored_digest']!=x['retry_digest']:return 'IDEMPOTENCY_KEY_CONFLICT'
 return 'RETURN_ORIGINAL'
for x in D['admission_idempotency']:
 assert admission(x)==x['expected'],x['name']
 if x['expected']=='RETURN_ORIGINAL':assert x['first_relay_event_id']==x['retry_relay_event_id']
def epoch(x):
 if x.get('initial'):
  return 'ALLOW_BOOTSTRAP' if x['approval_present'] and x['genesis_hash_match'] else 'EPOCH_NOT_APPROVED'
 if x['name'].startswith('normal_'):
  return 'ALLOW_NORMAL_TRANSITION' if x['C']==x['R']==x['T']==x['final_sequence'] and x['hashes_match'] else 'DENY_NORMAL_TRANSITION'
 if x['name'].startswith('exceptional_'):
  ok=x['gap_durable'] and x['gap_first']==x['C']+1 and x['gap_last']==x['T'] and x['R']==x['C']
  return 'ALLOW_EXCEPTIONAL_TRANSITION' if ok else 'DENY_EXCEPTIONAL_TRANSITION'
 if x['name']=='inherit_floor':return max(x['old_last_event_time'],x['old_last_trusted_checkpoint'],x['old_temporal_floor'])
 return 'ACCEPT' if x['new_event_time']>x['checkpoint_floor'] else 'CHECKPOINT_BACKDATED_EVENT'
for x in D['epoch_transition_cases']:
 expected=x.get('expected',x.get('expected_new_floor'));assert epoch(x)==expected,x['name']
for x in D['writer_fencing']:
 got='DENY' if x['same_sender'] and x['writer_a_lane']==x['writer_b_lane'] else 'ALLOW';assert got==x['expected_second_writer']
def payout_safe(x):
 mode=x['mode']
 if mode=='UNKNOWN':return False
 if mode=='NO_RELAY_REQUIRED':return True
 if mode!='RELAY_REQUIRED' or not x['members']:return False
 return all(m['checkpoint']>=x['required_boundary'] for m in x['members'])
for x in D['membership_cases']:assert payout_safe(x)==x['expected_payout_safe'],x['name']
def clock_state(x):
 if x.get('no_sample'):return 'UNKNOWN'
 L,U,S=x['L'],x['U'],x['S']
 if L>=-S and U<=S:return 'GOOD'
 if U < -S or L > S:return 'BAD'
 return 'UNKNOWN'
for x in D['clock_cases']:assert clock_state(x)==x['expected'],x['name']
a=D['clock_policy_aggregation'];got={k:min(s[k] for s in a['scopes']) for k in a['expected']};assert got==a['expected']
for x in D['quarantine_cases']:
 if not x.get('placement_valid',True):got=('INVALID_EVENT_PLACEMENT',False)
 elif not x.get('resent_exact_bytes',True):got=('CHAIN_OR_IDENTITY_MISMATCH',False)
 elif not x.get('payload_valid',True):got=('SEMANTIC_PAYLOAD_INVALID',True)
 else:got=('ACCEPT',False)
 assert got==(x['expected'],x['quarantinable']),x['name']
o=D['ordering_case'];events=sorted(o['events'],key=lambda x:(x['event_time_unix_ms'],bytes.fromhex(x['sender_hex']),x['sequence'],bytes.fromhex(x['relay_event_id_hex'])));assert [e['id'] for e in events]==o['expected_order']
for x in D['window_updates']:
 got='MALFORMED_FRAME' if x['new_events']>x['negotiated_events'] or x['new_bytes']>x['negotiated_bytes'] else ('ACCEPT_PAUSE' if x['new_events']==0 or x['new_bytes']==0 else 'ACCEPT')
 assert got==x['expected'],x['name']
f=D['flow_control'];assert sum(x['payload_len'] for x in f['events'])==f['expected_payload_charge'] and len(f['events'])==f['expected_window_events']
print('CoreDRP/1 Draft 0.4 state-machine vectors: OK')
