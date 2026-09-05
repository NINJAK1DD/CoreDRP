#!/usr/bin/env python3
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];D=json.loads((R/'docs/coredrp-v1-freeze-completion-vectors.json').read_text())
PROD_MAX=253402300799999
# Cross-sender B+2S completeness.
for x in D['completeness_boundary_cases']:
 try:
  req=x['boundary']+2*x['skew']
  valid=0<=req<=x.get('production_max',PROD_MAX)
 except OverflowError:valid=False;req=None
 got=bool(valid and x['checkpoint_complete_through']>=req)
 assert got==x['expected'],x
# Probe freshness and UNKNOWN grace.
for x in D['clock_freshness_cases']:
 k=x['case_kind']
 if k.startswith('delayed_good'):
  rem=max(0,x['effective_expiry_ms']-x['probe_age_ms']);accepted=min(x['advertised_valid_for_ms'],rem) if rem>0 else 0
  got='EXPIRED' if accepted<=0 else 'GOOD_SHORTENED' if accepted<x['advertised_valid_for_ms'] else 'GOOD'
  assert accepted==x['expected_remaining_ms'] and got==x['expected'],x
 else:
  since=x['unknown_since_ms'] if x['already_unknown'] else x['now_ms'];remaining=max(0,x['effective_unknown_grace_ms']-(x['now_ms']-since))
  assert since==x['expected_unknown_since_ms'] and remaining==x['expected_remaining_ms'],x
# Element-wise strictest clock reducer.
for x in D['multi_scope_clock_cases']:
 keys=('skew','max_step','probe_interval','processing_max','evidence_expiry','unknown_grace');got={k:min(s[k] for s in x['scopes']) for k in keys};assert got==x['expected'],x
# Scope-qualified bounded producer state.
for x in D['producer_idempotency_cases']:
 k=x['case_kind']
 if k=='same_uuid_different_scope_is_distinct':got='DISTINCT_NAMESPACES' if x['scope_a']!=x['scope_b'] else 'SAME_NAMESPACE'
 elif k=='unregistered_producer':got='REJECT_BEFORE_WAL' if not x['registered'] else 'ADMIT'
 elif k=='producer_registry_bound':got='REJECT_REGISTRATION' if x['new_registration'] and x['registered_count']>=x['max_registered'] else 'ACCEPT_REGISTRATION'
 elif k=='sequence_max_seals':got='SEAL_NO_INCREMENT' if x['admission_sequence']==(1<<64)-1 else 'INCREMENT'
 elif k=='generation_max_exhausts_producer':got='PRODUCER_EXHAUSTED' if x['sealed'] and x['producer_generation']==(1<<64)-1 else 'NEXT_GENERATION'
 else:raise AssertionError(x)
 assert got==x['expected'],x
# Frozen semantic allocations.
for x in D['semantic_allocation_cases']:
 valid=(x['payout_scheme'] in {1,2,3,4,5,6} and x['completeness_policy_version']==2 and x['retention_policy_version']==1 and x['cross_sender_ordering_policy']==1 and x['admission_policy_version']==3)
 got='ACCEPT' if valid else 'SEMANTIC_CONTRACT_MISMATCH';assert got==x['expected'],x
# Sender policy staging.
for x in D['policy_staging_cases']:
 staged=all(x['staged'].get(s)==x['policy_digest'] for s in x['required']);got='ACCEPT' if staged and x['generation_next'] and x['effective_safe'] else 'ADMIN_ACTION_CONFLICT';assert got==x['expected'],x
# Temporal reconciliation kind/presence matrix.
for x in D['reconciliation_cases']:
 k=x['correction_kind'];valid=k in {1,2,3,4,5,6}
 if k in {1,2,3,5}:valid=valid and x['has_sender']
 if k in {4,6}:valid=valid and not x['has_sender']
 if k==1:valid=valid and not x['prior_present'] and x['new_present']
 if k in {2,3,4}:valid=valid and x['prior_present'] and x['new_present']
 if k in {5,6}:valid=valid and x['prior_present'] and not x['new_present']
 got='ACCEPT' if valid else 'MALFORMED_FRAME';assert got==x['expected'],x
# Contiguous scalar vs settlement-specific evidence interval.
def intersects(a,b,c,d):return not (b<c or d<a)
for x in D['settlement_hole_cases']:
 k=x['case_kind']
 if k=='waived_hole_caps_scalar':
  got=x['current_contiguous_safe'] if x['hole_status']=='RESOLVED_WAIVED' and x['candidate_scalar']>=x['hole_from'] else x['candidate_scalar'];assert got==x['expected_scalar'],x
 else:
  relevant=intersects(x['evidence_from'],x['evidence_through'],x['hole_from'],x['hole_until']);safe=bool(x['other_gates'] and not (relevant and x['hole_status']=='RESOLVED_WAIVED'))
  assert safe==x['expected_settlement_safe'],x
  if 'expected_operational_settlement' in x:assert bool(safe or x.get('override'))==x['expected_operational_settlement'],x
print('CoreDRP Draft 0.6 freeze-completion vectors: OK')
