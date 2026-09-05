#!/usr/bin/env python3
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[1]
p=R/'docs/coredrp-v1-metrics.md';t=p.read_text(encoding='utf-8');spec=(R/'docs/CoreDRP-1-SPEC-0.6.md').read_text(encoding='utf-8')
def die(s):print('metrics-registry failure:',s,file=sys.stderr);raise SystemExit(1)
if 'Draft 0.6' not in t:die('registry version is not Draft 0.6')
rows=re.findall(r'^\| `([^`]+)` \| (gauge|counter|histogram) \| `([^`]*)` \|',t,re.M)
if len(rows)<25:die(f'too few metric rows: {len(rows)}')
names=[x[0] for x in rows]
if len(names)!=len(set(names)):die('duplicate metric name')
for name,typ,labels in rows:
 if not name.startswith('miningcore_coredrp_'):die(f'bad prefix: {name}')
 if name.endswith('_total') and typ!='counter':die(f'_total metric must be counter: {name}')
 if typ=='counter' and not name.endswith('_total'):die(f'counter must end _total: {name}')
 forbidden={'miner','worker','ip','relay_event_id','epoch','chain_hash','error_text','caller_admission_key'}
 got={x for x in labels.split(',') if x}
 if got & forbidden:die(f'unbounded/sensitive label on {name}: {sorted(got&forbidden)}')
required={'miningcore_coredrp_connected','miningcore_coredrp_spool_events','miningcore_coredrp_acked_sequence','miningcore_coredrp_clock_bound_state','miningcore_coredrp_payout_safe_through_unix_seconds','miningcore_coredrp_safe_prune_through_unix_seconds','miningcore_coredrp_unresolved_completeness_gaps','miningcore_coredrp_admission_generation_records','miningcore_coredrp_admission_generation_bytes','miningcore_coredrp_admission_retired_generation_high_water','miningcore_coredrp_waived_completeness_ranges'}
if not required.issubset(set(names)):die(f'missing required metrics: {sorted(required-set(names))}')
if 'coredrp-v1-metrics.md' not in spec:die('canonical spec does not incorporate metric registry')
print('CoreDRP Draft 0.6 metrics registry: OK')
