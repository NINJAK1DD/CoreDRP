#!/usr/bin/env python3
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
required={
 'docs/coredrp-mining-v1-semantics.md':[
  'Draft 0.6','completeness_policy_version','B + 2*S','(sender_id, lane_id, scope, producer_id)','1024 registered producer IDs','PayoutSafeThrough(scope)'],
 'docs/coredrp-miningcore-v1-semantics.md':[
  'Draft 0.6','accounting_schema_version','settlement_policy_version','PPLNS','PPS','DIRECT_SOLO','synthetic-regtest'],
 'docs/coredrp-v1-clock-state.md':[
  'Draft 0.6','effective_permitted_skew_ms = min','probe_age_ms','unknown_since_mono','RECOVERING'],
 'docs/coredrp-v1-temporal-policy.md':[
  'Draft 0.6','policy_generation','Sender staging requirement','PolicyEvidenceV1','INSERT_MISSING_MEMBERSHIP_INTERVAL'],
 'docs/coredrp-v1-settlement-safety.md':[
  'Draft 0.6','SettlementSafe','B + 2*S','RESOLVED_WAIVED','PayoutSafeThrough'],
 'docs/coredrp-v1-draft06-contracts.md':[
  'Draft 0.6','coredrp-v1-temporal-policy.md','coredrp-v1-settlement-safety.md','completeness_policy_version = 2','settlement_policy_version = 1'],
 'docs/coredrp-v1-bitcoin-network-policies.md':[
  'Draft 0.6','MUST NOT be selected by any production Mining scope','bitcoin_network_policy_digest'],
 'docs/coredrp-v1-admin-actions.md':[
  'TEMPORAL_POLICY_RECONCILIATION','prior_policy_evidence','new_policy_evidence','policy_generation','staged_policy_digest'],
}
failed=False
for rel,needles in required.items():
 p=R/rel
 if not p.exists():print('missing normative registry:',rel,file=sys.stderr);failed=True;continue
 b=p.read_bytes()
 try:t=b.decode('utf-8')
 except UnicodeDecodeError:print('registry is not UTF-8:',rel,file=sys.stderr);failed=True;continue
 if len(b)<800:
  print('normative registry unexpectedly small:',rel,len(b),file=sys.stderr);failed=True
 for n in needles:
  if n not in t:print('registry missing required sentinel:',rel,repr(n),file=sys.stderr);failed=True
# Unversioned spec must remain a pointer, never a second normative copy.
p=R/'docs/CoreDRP-1-SPEC.md';t=p.read_text(encoding='utf-8')
if 'CoreDRP-1-SPEC-0.6.md' not in t or len(t.encode())>4096 or '## 33. PayoutSafe' in t:
 print('unversioned spec must remain a small pointer to canonical versioned spec',file=sys.stderr);failed=True
# Historical protocol-semantic vectors are allowed only below docs/historical and are never current CI inputs.
h=R/'docs/historical/coredrp-v1-draft04-vectors.json'
if not h.exists():print('historical Draft 0.4 corpus missing archival copy',file=sys.stderr);failed=True
for forbidden in ['docs/coredrp-v1-draft05-vectors.json','tools/verify_draft05_vectors.py','tools/verify_historical_draft04_vectors.py','model/CoreDRP-unsafe.cfg','docs/coredrp-v1-draft05-contracts.md']:
 if (R/forbidden).exists():print('superseded/orphaned freeze artifact still present:',forbidden,file=sys.stderr);failed=True
if failed:raise SystemExit(1)
print('CoreDRP Draft 0.6 normative registry and authority integrity: OK')
