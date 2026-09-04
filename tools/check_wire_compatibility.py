#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
R=Path(__file__).resolve().parents[1]; B=json.loads((R/'docs/coredrp-v1-wire-baseline.json').read_text())['files']
def fields(path,msg):
 t=re.sub(r'//.*?$|/\*.*?\*/','',(R/path).read_text(),flags=re.M|re.S); m=re.search(r'\bmessage\s+'+re.escape(msg)+r'\s*\{',t)
 if not m:return {}
 d=1;i=m.end()
 while i<len(t) and d:
  d += (t[i]=='{')-(t[i]=='}'); i+=1
 body=t[m.end():i-1]; out={}
 for q,ty,n,num in re.findall(r'^\s*(?:(optional|repeated)\s+)?([\w.]+)\s+(\w+)\s*=\s*(\d+)\s*;',body,re.M):out[num]=((q+' ') if q else '')+ty+' '+n
 return out
for path,msgs in B.items():
 for msg,base in msgs.items():
  cur=fields(path,msg)
  for num,sig in base.items():
   if cur.get(num)!=sig:print(f'wire breaking change {path}:{msg} field {num}: expected {sig!r}, got {cur.get(num)!r}',file=sys.stderr);raise SystemExit(1)
print('CoreDRP wire compatibility baseline: OK')
