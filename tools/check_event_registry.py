#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
exp={'CORE_EVENT_TYPE_COMPLETENESS_CHECKPOINT':1,'MINING_EVENT_TYPE_SHARE':256,'MININGCORE_EVENT_TYPE_ACCOUNTING_SHARE':512,'MININGCORE_EVENT_TYPE_BITCOIN_DIRECT_COINBASE_CANDIDATE':513,'MININGCORE_EVENT_TYPE_CANDIDATE_STATE_UPDATE':514}
t='\n'.join((R/p).read_text() for p in ['protocol/coredrp-v1.proto','profiles/mining/coredrp-mining-v1.proto','profiles/miningcore/coredrp-miningcore-v1.proto'])
s=(R/'docs/CoreDRP-1-SPEC-0.6.md').read_text()
for n,v in exp.items():
 if not re.search(rf'\b{n}\s*=\s*{v}\b',t):print('event registry failure',n,file=sys.stderr);raise SystemExit(1)
for h in ['0x0001','0x0100','0x0200','0x0201','0x0202']:
 if h not in s:raise SystemExit('spec missing '+h)
# 0xFFFF is a Core hash-boundary conformance case, not an application event allocation.
core=(R/'docs/coredrp-v1-core-hash-vectors.json').read_text()
if '"event_type":"0xFFFF"' not in core:raise SystemExit('boundary-test event type 0xFFFF missing from current Core hash corpus')
print('CoreDRP Draft 0.6 event registry: OK')
