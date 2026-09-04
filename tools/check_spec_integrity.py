#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
def die(s): print('spec-integrity failure:',s,file=sys.stderr); raise SystemExit(1)
for p in R.rglob('*'):
 if p.is_file() and p.suffix in {'.md','.proto','.py','.yml','.yaml','.json','.tla','.cfg'}:
  b=p.read_bytes()
  try:t=b.decode('utf-8')
  except UnicodeDecodeError as e: die(f'{p}: invalid UTF-8 {e}')
  if '\x00' in t: die(f'{p}: NUL')
  if any(ord(c)<32 and c not in '\n\r\t' for c in t): die(f'{p}: control byte')
s=(R/'docs/CoreDRP-1-SPEC.md').read_text(); nums=[int(x) for x in re.findall(r'^## (\d+)\.',s,re.M)]
if nums!=list(range(1,max(nums)+1)): die(f'non-contiguous sections {nums}')
for n in map(int,re.findall(r'\bSection (\d+)\b',s)):
 if n not in set(nums): die(f'unresolved Section {n}')
print('CoreDRP specification integrity: OK')
