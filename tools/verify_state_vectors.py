#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Verify CoreDRP/1 Draft 0.3 state-machine decision vectors."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];D=json.loads((R/'docs/coredrp-v1-state-vectors.json').read_text(encoding='utf-8'))
def reconnect(x):
 C,Rm,T,E=x['C'],x['R'],x['T'],x['E']
 if not x['same_incarnation']:return 'RECEIVER_INCARNATION_CHANGED'
 if C>T:return 'SENDER_ROLLBACK'
 if not x['hash_match']:return 'SPLIT_LOG'
 if C<Rm:return 'RECEIVER_ROLLBACK'
 if C+1<E:return 'RECOVERY_GAP'
 if C>Rm:return 'ADOPT_ACK' if x['receiver_hash_verifiable'] else 'SPLIT_LOG'
 return 'RESUME'
for x in D['reconnect_cases']:
 assert reconnect(x)==x['expected'],x['name']
 if x['expected']=='RESUME':assert x['resume_sequence']==x['C']+1
 if x['expected']=='ADOPT_ACK':assert x['adopt_sequence']==x['C']
for x in D['wal_crash_cases']:
 if x.get('application_success_sent'):assert x['wal_durable'] and x['event_recoverable']
 if x.get('prune_allowed'):assert x['ack_anchor_durable'] and x['prune_through']<=x['remembered_ack_sequence']
 if not x.get('ack_anchor_durable',False):assert not x.get('prune_allowed',False)
 if x['name']=='wal_durable_before_response':assert x['retry_returns_same_event']
stored={}
for x in D['admission_idempotency']:
 if x['name']=='same_key_same_event':stored[x['key']]=(x['event_digest'],x['first_relay_event_id']);assert x['retry_relay_event_id']==x['first_relay_event_id'] and x['expected']=='RETURN_ORIGINAL'
 elif x['name']=='same_key_different_event':assert x['key'] in stored and x['stored_event_digest']==stored[x['key']][0] and x['event_digest']!=x['stored_event_digest'] and x['expected']=='IDEMPOTENCY_CONFLICT'
for x in D['epoch_transition_cases']:
 if x['name']=='inherit_floor':assert max(x['old_last_event_time'],x['old_last_trusted_checkpoint'],x['old_temporal_floor'])==x['expected_new_floor']
 else:assert ('ACCEPT' if x['new_event_time']>x['checkpoint_floor'] else 'CHECKPOINT_BACKDATED_EVENT')==x['expected'],x['name']
for x in D['writer_fencing']:
 if x['name']=='different_epochs_same_lane':assert x['expected_second_writer']=='DENY'
 else:assert x['writer_a_lane']!=x['writer_b_lane'] and x['expected_second_writer']=='ALLOW'
def payout_safe(x):
 mode=x['completeness_mode']
 if mode=='UNKNOWN':return False
 if mode=='NO_RELAY_REQUIRED':return True
 if mode!='RELAY_REQUIRED' or not x['members']:return False
 return all(m['checkpoint']>=x['required_boundary'] for m in x['members'])
for x in D['membership_cases']:assert payout_safe(x)==x['expected_payout_safe'],x['name']
for x in D['quarantine_cases']:
 if not x['resent_exact_bytes']:assert x['expected']=='CHAIN_OR_IDENTITY_MISMATCH'
 else:assert x['operator_approved_exact_hash'] and x['invalid_sequence'] in x['batch_sequences'] and x['expected_ack_through']==max(x['batch_sequences'])
o=D['ordering_case'];events=sorted(o['events'],key=lambda x:(x['event_time_unix_ms'],bytes.fromhex(x['sender_hex']),x['sequence'],bytes.fromhex(x['relay_event_id_hex'])));assert [e['id'] for e in events]==o['expected_order']
f=D['flow_control'];assert sum(x['payload_len'] for x in f['events'])==f['expected_payload_charge'];assert len(f['events'])==f['expected_window_events']
print('CoreDRP/1 Draft 0.3 state-machine vectors: OK')
