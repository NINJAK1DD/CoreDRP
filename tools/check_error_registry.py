#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
p=(R/'protocol/coredrp-v1.proto').read_text();d=(R/'docs/coredrp-v1-errors.md').read_text();e=(R/'docs/coredrp-v1-error-emission.md').read_text()
b=re.search(r'enum ErrorCode\s*\{(.*?)\}',p,re.S).group(1)
a={(n,int(v)) for n,v in re.findall(r'([A-Z][A-Z0-9_]*)\s*=\s*(\d+)',b)}
z={(n,int(v)) for v,n in re.findall(r'^\|\s*(\d+)\s*\|\s*([A-Z][A-Z0-9_]*)\s*\|',d,re.M)}
if a!=z:print('error registry mismatch',a-z,z-a,file=sys.stderr);raise SystemExit(1)
missing=[]
for name,value in sorted(a,key=lambda x:x[1]):
 if value==0:continue
 if not re.search(r'^\|\s*'+re.escape(name)+r'\s*\|',e,re.M):missing.append(name)
if missing:print('missing normative error emission rules:',missing,file=sys.stderr);raise SystemExit(1)
print('CoreDRP error registry parity and emission coverage: OK')
