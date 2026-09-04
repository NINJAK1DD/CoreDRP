#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]; C=R/'protocol/coredrp-v1.proto'; M=R/'profiles/mining/coredrp-mining-v1.proto'; MC=R/'profiles/miningcore/coredrp-miningcore-v1.proto'; IMP=re.compile(r'^\s*import\s+"([^"]+)"',re.M)
def im(p):return set(IMP.findall(p.read_text()))
def die(x):print('layer-boundary failure:',x,file=sys.stderr);raise SystemExit(1)
if any(x.startswith('profiles/') for x in im(C)):die('Core imports profile')
if im(M)-{'protocol/coredrp-v1.proto'}:die('Mining forbidden import')
if im(MC)-{'protocol/coredrp-v1.proto','profiles/mining/coredrp-mining-v1.proto'}:die('Miningcore forbidden import')
def ids(p):
 t=re.sub(r'//.*?$|/\*.*?\*/','',p.read_text(),flags=re.M|re.S);return [x for pair in re.findall(r'\b(?:message|enum|service|rpc)\s+(\w+)|\b(\w+)\s*=\s*\d+\s*;',t) for x in pair if x]
def words(s):
 out=[]
 for c in s.replace('-','_').split('_'):out+=re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+',c)
 return [x.lower() for x in out]
cf=('pool','miner','share','payout','bitcoin','coinbase','hashrate','postgres','miningcore','stratum','pplns','prop','wallet','satoshi','difficulty','block','reward','coin','nonce','merkle'); mf=('postgres','sql','miningcore','pplnsbf','npgsql')
for p,fs in [(C,cf),(M,mf)]:
 hits=[w for i in ids(p) for w in words(i) if any(w==f or w.startswith(f+'s') for f in fs)]
 if hits:die(str(sorted(set(hits))))
print('CoreDRP layer boundaries: OK')
