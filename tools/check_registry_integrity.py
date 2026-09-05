#!/usr/bin/env python3
from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[1]
required={
 'docs/coredrp-mining-v1-semantics.md':['Draft 0.6','completeness_policy_version','B + 2*S','(sender_id, lane_id, scope, producer_id)','1024 registered producer IDs','PayoutSafeThrough(scope)'],
 'docs/coredrp-miningcore-v1-semantics.md':['Draft 0.6','accounting_schema_version','bytes','paired.scope != primary.scope','accounting_id','settlement_scheme_policy_digest32','Payout-significant quarantine'],
 'docs/coredrp-v1-clock-state.md':['Draft 0.6','effective multi-scope lane policy','SENDER_PROCESSING_LIMIT','deterministically BAD','RECOVERING'],
 'docs/coredrp-v1-temporal-policy.md':['Draft 0.6','RequiredStagingSender','applicable_clock_uncertainty_ms','scope_safety_origin_unix_ms','PolicyEvidenceV1','CORRECT_MEMBERSHIP_END'],
 'docs/coredrp-v1-settlement-safety.md':['Draft 0.6','SettlementSafe','SettlementPruneSafe','scope_safety_origin_unix_ms','RESOLVED_WAIVED','PayoutSafeThrough'],
 'docs/coredrp-v1-settlement-scheme-policies.md':['Draft 0.6','settlement_scheme_policy_digest32','PPLNSBF','block_finder_percentage'],
 'docs/coredrp-v1-producer-lifecycle.md':['Draft 0.6','producer tombstone','MUST NEVER be registered again','semantic-contract digest'],
 'docs/coredrp-v1-profile-transitions.md':['Draft 0.6','FINANCIALLY_INCOMPATIBLE','Financial migration barrier','active producer generation'],
 'docs/coredrp-v1-quarantine-safety.md':['Draft 0.6','UNRESOLVED','RESOLVED_RECONCILED','RESOLVED_WAIVED','QUARANTINE_AND_ADVANCE'],
 'docs/coredrp-v1-draft06-contracts.md':['Draft 0.6','coredrp-v1-settlement-scheme-policies.md','coredrp-v1-producer-lifecycle.md','coredrp-v1-profile-transitions.md','coredrp-v1-quarantine-safety.md','accounting_schema_version = 2','settlement_policy_version = 2'],
 'docs/coredrp-v1-bitcoin-network-policies.md':['Draft 0.6','MUST NOT be selected by any production Mining scope','bitcoin_network_policy_digest'],
 'docs/coredrp-v1-admin-actions.md':['Draft 0.6','TEMPORAL_POLICY_RECONCILIATION','prior_policy_evidence','new_policy_evidence','policy_generation','staged_policy_digest'],
 'docs/coredrp-v1-errors.md':['Draft 0.6','SEMANTIC_RETRY_LIMIT','ProtocolError.disposition'],
 'docs/coredrp-v1-error-emission.md':['Draft 0.6','SEMANTIC_RETRY_LIMIT','TEMPORAL_MEMBERSHIP_REQUIRED'],
}
failed=False
for rel,needles in required.items():
 p=R/rel
 if not p.exists():print('missing normative registry:',rel,file=sys.stderr);failed=True;continue
 b=p.read_bytes()
 try:t=b.decode('utf-8')
 except UnicodeDecodeError:print('registry is not UTF-8:',rel,file=sys.stderr);failed=True;continue
 if len(b)<500:print('normative registry unexpectedly small:',rel,len(b),file=sys.stderr);failed=True
 for n in needles:
  if n not in t:print('registry missing required sentinel:',rel,repr(n),file=sys.stderr);failed=True
# Current conformance artefacts must exist and self-identify as current/profile-freeze.
vector_required={
 'docs/coredrp-v1-core-hash-vectors.json':'current Core 1.1',
 'docs/coredrp-v1-admission-vectors.json':'current Mining admission',
 'docs/coredrp-v1-accounting-vectors.json':'accounting-schema-v2',
 'docs/coredrp-v1-bitcoin-profile-vectors.json':'Miningcore 1.1 Bitcoin candidate',
 'docs/coredrp-v1-draft06-vectors.json':'profile-freeze',
 'docs/coredrp-v1-wire-structure.json':None,
}
for rel,sentinel in vector_required.items():
 p=R/rel
 if not p.exists():print('missing current conformance artifact:',rel,file=sys.stderr);failed=True;continue
 if sentinel and sentinel not in p.read_text(encoding='utf-8'):print('current conformance artifact missing sentinel:',rel,sentinel,file=sys.stderr);failed=True
# Structural baseline may never be committed in PENDING state.
wp=R/'docs/coredrp-v1-wire-structure.json'
if wp.exists():
 try:w=json.loads(wp.read_text())
 except Exception as e:print('invalid structural wire baseline:',e,file=sys.stderr);failed=True
 else:
  if w.get('PENDING') is True:print('structural wire baseline is still PENDING',file=sys.stderr);failed=True
  elif w.get('format')!='CoreDRP protobuf structural baseline v1':print('unexpected structural wire baseline format',file=sys.stderr);failed=True
# Unversioned spec must remain pointer only.
p=R/'docs/CoreDRP-1-SPEC.md';t=p.read_text(encoding='utf-8')
if 'CoreDRP-1-SPEC-0.6.md' not in t or len(t.encode())>4096 or '## 33. PayoutSafe' in t:
 print('unversioned spec must remain a small pointer to canonical versioned spec',file=sys.stderr);failed=True
# Historical corpus is archival only.
h=R/'docs/historical/coredrp-v1-draft04-vectors.json'
if not h.exists():print('historical Draft 0.4 corpus missing archival copy',file=sys.stderr);failed=True
for forbidden in ['docs/coredrp-v1-draft05-vectors.json','docs/coredrp-v1-profile-vectors.json','tools/verify_draft05_vectors.py','tools/verify_historical_draft04_vectors.py','model/CoreDRP-unsafe.cfg','docs/coredrp-v1-draft05-contracts.md','docs/coredrp-v1-wire-baseline.json','docs/coredrp-v1-package-baseline.json']:
 if (R/forbidden).exists():print('superseded/orphaned freeze artifact still present:',forbidden,file=sys.stderr);failed=True
if failed:raise SystemExit(1)
print('CoreDRP Draft 0.6 profile-freeze registry and authority integrity: OK')
