#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]; C=R/'protocol/coredrp-v1.proto'; M=R/'profiles/mining/coredrp-mining-v1.proto'; MC=R/'profiles/miningcore/coredrp-miningcore-v1.proto'; IMP=re.compile(r'^\s*import\s+"([^"]+)"',re.M)
def im(p):return set(IMP.findall(p.read_text()))
def die(x):print('layer-boundary failure:',x,file=sys.stderr);raise SystemExit(1)
if any(x.startswith('profiles/') for x in im(C)):die('Core imports profile')
if im(M)-{'protocol/coredrp-v1.proto'}:die('Mining forbidden import')
if im(MC)-{'protocol/coredrp-v1.proto','profiles/mining/coredrp-mining-v1.proto'}:die('Miningcore forbidden import')
def ids_text(t):
 t=re.sub(r'//.*?$|/\*.*?\*/','',t,flags=re.M|re.S);return [x for pair in re.findall(r'\b(?:message|enum|service|rpc)\s+(\w+)|\b(\w+)\s*=\s*\d+\s*;',t) for x in pair if x]
def words(s):
 out=[]
 for c in s.replace('-','_').split('_'):out+=re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+',c)
 return [x.lower() for x in out]
core_stems=('pool','miner','mining','share','payout','bitcoin','coinbase','hashrate','postgres','stratum','pplns','prop','wallet','satoshi','difficult','block','reward','coin','nonce','merkle','txid','wtxid','utxo','mempool','fee','ledger','segwit','witness')
mining_stems=('postgres','sql','miningcore','npgsql')
def hits_for(text,stems):return sorted({w for i in ids_text(text) for w in words(i) if any(w.startswith(s) for s in stems)})
for p,stems in [(C,core_stems),(M,mining_stems)]:
 hits=hits_for(p.read_text(),stems)
 if hits:die(f'{p.relative_to(R)} contains forbidden profile terms: {hits}')
bad='''message MiningState { string difficulties = 1; string blockchain = 2; string pplnsbf = 3; string txid = 4; string utxo = 5; string mempool = 6; string fees = 7; string ledger = 8; string wtxid = 9; string segwit = 10; }'''
expected={'mining','difficulties','blockchain','pplnsbf','txid','utxo','mempool','fees','ledger','wtxid','segwit'}
seen=set(hits_for(bad,core_stems))
if not expected.issubset(seen):die(f'boundary self-test failed, missed {sorted(expected-seen)}')
if hits_for('message Version { uint32 minimum_core_major = 1; }',core_stems):die('boundary self-test false-positive on minimum_core_major')
print('CoreDRP layer boundaries: OK')
