#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
def die(s): print('document-structure failure:',s,file=sys.stderr); raise SystemExit(1)
for p in R.rglob('*'):
 if p.is_file() and p.suffix in {'.md','.proto','.py','.yml','.yaml','.json','.tla','.cfg'}:
  b=p.read_bytes()
  try:t=b.decode('utf-8')
  except UnicodeDecodeError as e: die(f'{p}: invalid UTF-8 {e}')
  if '\x00' in t: die(f'{p}: NUL')
  if any(ord(c)<32 and c not in '\n\r\t' for c in t): die(f'{p}: control byte')
p=R/'docs/CoreDRP-1-SPEC-0.5.md'; b=p.read_bytes(); s=b.decode('utf-8')
if len(b)<18000: die(f'normative Draft 0.5 spec unexpectedly small: {len(b)} bytes')
nums=[int(x) for x in re.findall(r'^## (\d+)\.',s,re.M)]
if nums!=list(range(1,51)): die(f'expected exactly sections 1..50, got {nums}')
for n in map(int,re.findall(r'\bSection (\d+)\b',s)):
 if n not in set(nums): die(f'unresolved Section {n}')
if '## 50. Authorship' not in s: die('missing terminal Authorship section')
if '<!-- COREDRP-SPEC-END:50 -->' not in s: die('missing terminal specification sentinel')
if 'https://github.com/NINJAK1DD/CoreDRP' not in s or 'https://coredrp.org' not in s: die('missing canonical project/source sentinel')
if 'Draft 0.5' not in s: die('canonical spec is not Draft 0.5')
print('CoreDRP Draft 0.5 document structure: OK')
