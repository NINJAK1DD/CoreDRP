#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
def die(s): print('document-structure failure:',s,file=sys.stderr); raise SystemExit(1)
for p in R.rglob('*'):
 if p.is_file() and p.suffix in {'.md','.proto','.py','.yml','.yaml','.json','.tla','.cfg','.cs'}:
  b=p.read_bytes()
  try:t=b.decode('utf-8')
  except UnicodeDecodeError as e: die(f'{p}: invalid UTF-8 {e}')
  if '\x00' in t: die(f'{p}: NUL')
  if any(ord(c)<32 and c not in '\n\r\t' for c in t): die(f'{p}: control byte')
p=R/'docs/CoreDRP-1-SPEC-0.6.md'; b=p.read_bytes(); s=b.decode('utf-8')
if len(b)<18000: die(f'normative Draft 0.6 spec unexpectedly small: {len(b)} bytes')
nums=[int(x) for x in re.findall(r'^## (\d+)\.',s,re.M)]
if nums!=list(range(1,51)): die(f'expected exactly sections 1..50, got {nums}')
for n in map(int,re.findall(r'\bSection (\d+)\b',s)):
 if n not in set(nums): die(f'unresolved Section {n}')
for required in ['## 50. Authorship','<!-- COREDRP-SPEC-END:50 -->','https://github.com/NINJAK1DD/CoreDRP','https://coredrp.org','Draft 0.6','PayoutEffectScopes(E)','accounting schema 3','QUARANTINE_RECONCILIATION','SettlementEvidenceSummaryV1','NoLiveDependencies']:
 if required not in s:die(f'missing sentinel {required}')
registries=[
 'coredrp-mining-v1-semantics.md','coredrp-miningcore-v1-semantics.md','coredrp-v1-draft06-contracts.md',
 'coredrp-v1-bitcoin-network-policies.md','coredrp-v1-settlement-scheme-policies.md','coredrp-v1-share-difficulty-adjustment-policies.md',
 'coredrp-v1-settlement-safety.md','coredrp-v1-temporal-policy.md','coredrp-v1-quarantine-safety.md','coredrp-v1-profile-transitions.md',
 'coredrp-v1-admin-actions.md','coredrp-v1-errors.md','coredrp-v1-error-emission.md','coredrp-v1-metrics.md'
]
for reg in registries:
 if reg not in s:die(f'canonical spec does not incorporate {reg}')
 if not (R/'docs'/reg).exists():die(f'incorporated registry missing: {reg}')
if 'compatibility registry is normative' not in s.lower():die('canonical spec does not bind compatibility registry')
if not (R/'docs/coredrp-v1-compatibility.md').exists():die('compatibility registry missing')
print('CoreDRP Draft 0.6 final Profile 1.1 document structure: OK')
