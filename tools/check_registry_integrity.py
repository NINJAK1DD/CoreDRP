#!/usr/bin/env python3
from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[1]
required={
 'docs/coredrp-v1-miningcore-requests.md':['Draft 0.6','MiningcoreAccountingShareRequestV1','BitcoinDirectCoinbaseCandidateRequestV1','CandidateStateUpdateRequestV1','CoreDRP1-ADMISSION','created_unix_ms'],
 'docs/coredrp-mining-v1-semantics.md':['Draft 0.6','PayoutEffectScopes(E)','TEMPORAL_MEMBERSHIP_REQUIRED','(sender_id, lane_id, scope, producer_id)','1024 registered producer IDs','PayoutSafeThrough(scope)'],
 'docs/coredrp-miningcore-v1-semantics.md':['Draft 0.6','accounting_schema_version','accounting_schema_version` | 3','settlement_policy_version` | 5','transport-authorized for `P.scope`','share.achieved_share_difficulty > 0','block_only = false','Guid.ToString("N")','QUARANTINE_RECONCILIATION'],
 'docs/coredrp-v1-clock-state.md':['Draft 0.6','Effective multi-scope lane policy','SENDER_PROCESSING_LIMIT','deterministically BAD','RECOVERING'],
 'docs/coredrp-v1-temporal-policy.md':['Draft 0.6','RequiredStagingSender','AdmissionPolicyHolders(Q)','issuance-ledger lock','SkewTransition','last active clock-governed scope','applicable_clock_uncertainty_ms','NO_POLICY','PolicyEvidenceV1'],
 'docs/coredrp-v1-settlement-safety.md':['Draft 0.6','SettlementSafe','SettlementPruneSafe','SettlementEvidenceSummaryV1','ParticipantEffectV1','EffectIdentityV1','CheckpointEvidenceV1','UncertaintyRecordV1','share_difficulty_adjustment_policy_digest32','RESOLVED_WAIVED','PayoutSafeThrough'],
 'docs/coredrp-v1-settlement-scheme-policies.md':['Draft 0.6','uint16_be(3)','resolved effective','share_difficulty_adjustment_policy_digest32','PPLNSBF','block_finder_percentage','PPLNSScoreV1','PPSLiabilityV1','retained_reward_percentage','Full-tuple pagination'],
 'docs/coredrp-v1-share-difficulty-adjustment-policies.md':['Draft 0.6','share_difficulty_adjustment_policy_digest32','identity','constant_multiplier','round-to-nearest, ties-to-even','P_exact'],
 'docs/coredrp-v1-producer-lifecycle.md':['Draft 0.6','producer tombstone','MUST NEVER be registered again','semantic-contract digest'],
 'docs/coredrp-v1-profile-transitions.md':['Draft 0.6','FINANCIALLY_INCOMPATIBLE','NoLiveDependencies','POLICY_RECONCILIATION_PENDING','active producer generation','SettlementEvidenceSummaryV1'],
 'docs/coredrp-v1-quarantine-safety.md':['Draft 0.6','UNRESOLVED','RESOLVED_RECONCILED','RESOLVED_WAIVED','ReconciledEffectEvidenceV1','QUARANTINE_RECONCILIATION','QUARANTINE_WAIVER','coredrp-v1-validator-authorities.md'],
 'docs/coredrp-v1-validator-authorities.md':['Draft 0.6','validator_profile_digest32','coredrp.profile11.exact-revalidation','22a09b0066b1b1e7fdd6258fc435ea4e4c7ad7aff8b0440915fec452abb88e04'],
 'docs/coredrp-v1-draft06-contracts.md':['Draft 0.6','coredrp-v1-share-difficulty-adjustment-policies.md','coredrp-v1-validator-authorities.md','accounting_schema_version = 3','settlement_policy_version = 5','6ecd5753448cc09f2ecda289a9b77b31b83dbc0391f83d402620f309f6b83979'],
 'docs/coredrp-v1-bitcoin-network-policies.md':['Draft 0.6','MUST NOT be selected by any production Mining scope','bitcoin_network_policy_digest'],
 'docs/coredrp-v1-admin-actions.md':['Draft 0.6','QUARANTINE_RECONCILIATION','QUARANTINE_WAIVER','corrected effect digest','TEMPORAL_POLICY_RECONCILIATION','staged_policy_digest'],
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
vector_required={
 'docs/coredrp-v1-core-hash-vectors.json':'current Core 1.1',
 'docs/coredrp-v1-admission-vectors.json':'current Mining admission',
 'docs/coredrp-v1-accounting-vectors.json':'accounting-schema-v3',
 'docs/coredrp-v1-accounting-schema3-safety-vectors.json':'accounting-schema-v3 strict safety vectors',
 'docs/coredrp-v1-bitcoin-profile-vectors.json':'Miningcore 1.1 Bitcoin candidate',
 'docs/coredrp-v1-draft06-vectors.json':'final Profile 1.1 freeze conformance vectors',
 'docs/coredrp-v1-policy-clock-vectors.json':'current temporal bootstrap and ClockStateUpdate lifecycle vectors',
 'docs/coredrp-v1-review-blocker-vectors.json':'review-blocker vectors',
 'docs/coredrp-v1-financial-hardening-vectors.json':'settlement-policy-v5 financial hardening vectors',
 'docs/coredrp-v1-review2-vectors.json':'admission/history/audit hardening vectors',
 'docs/coredrp-v1-request-schemas.json':'ActivatedPolicyEvidenceV1',
 'docs/coredrp-v1-wire-structure.json':None,
}
for rel,sentinel in vector_required.items():
 p=R/rel
 if not p.exists():print('missing current conformance artifact:',rel,file=sys.stderr);failed=True;continue
 if sentinel and sentinel not in p.read_text(encoding='utf-8'):print('current conformance artifact missing sentinel:',rel,sentinel,file=sys.stderr);failed=True
for tool in ['tools/verify_policy_clock_vectors.py','tools/verify_accounting_schema3_safety.py','tools/verify_review_blocker_vectors.py','tools/verify_financial_hardening.py','tools/financial_semantics.py','tools/request_encodings.py','tools/audit_evidence.py','tools/verify_review2_vectors.py','tools/csharp-vector-check/EncodingChecks.cs']:
 if not (R/tool).exists():print('required conformance verifier missing:',tool,file=sys.stderr);failed=True
wp=R/'docs/coredrp-v1-wire-structure.json'
if wp.exists():
 try:w=json.loads(wp.read_text())
 except Exception as e:print('invalid structural wire baseline:',e,file=sys.stderr);failed=True
 else:
  if w.get('PENDING') is True:print('structural wire baseline must never remain PENDING',file=sys.stderr);failed=True
  elif w.get('format')!='CoreDRP protobuf structural baseline v1':print('unexpected structural wire baseline format',file=sys.stderr);failed=True
p=R/'docs/CoreDRP-1-SPEC.md';t=p.read_text(encoding='utf-8')
if 'CoreDRP-1-SPEC-0.6.md' not in t or len(t.encode())>4096 or '## 33. PayoutSafe' in t:
 print('unversioned spec must remain a small pointer to canonical versioned spec',file=sys.stderr);failed=True
h=R/'docs/historical/coredrp-v1-draft04-vectors.json'
if not h.exists():print('historical Draft 0.4 corpus missing archival copy',file=sys.stderr);failed=True
for forbidden in ['docs/coredrp-v1-draft05-vectors.json','docs/coredrp-v1-profile-vectors.json','tools/verify_draft05_vectors.py','tools/verify_historical_draft04_vectors.py','model/CoreDRP-unsafe.cfg','docs/coredrp-v1-draft05-contracts.md','docs/coredrp-v1-wire-baseline.json','docs/coredrp-v1-package-baseline.json']:
 if (R/forbidden).exists():print('superseded/orphaned freeze artifact still present:',forbidden,file=sys.stderr);failed=True
if failed:raise SystemExit(1)
print('CoreDRP Draft 0.6 final Profile 1.1 registry and authority integrity: OK')
