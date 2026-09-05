#!/usr/bin/env python3
from pathlib import Path
import json,sys
from google.protobuf import descriptor_pb2
R=Path(__file__).resolve().parents[1];desc=R/'.build/coredrp.pb';base=R/'docs/coredrp-v1-wire-structure.json'
if not desc.exists():print('wire-structure prerequisite missing: build .build/coredrp.pb first',file=sys.stderr);raise SystemExit(2)
TARGETS={'protocol/coredrp-v1.proto','profiles/mining/coredrp-mining-v1.proto','profiles/miningcore/coredrp-miningcore-v1.proto'}
fds=descriptor_pb2.FileDescriptorSet();fds.ParseFromString(desc.read_bytes())
TYPE={1:'double',2:'float',3:'int64',4:'uint64',5:'int32',6:'fixed64',7:'fixed32',8:'bool',9:'string',10:'group',11:'message',12:'bytes',13:'uint32',14:'enum',15:'sfixed32',16:'sfixed64',17:'sint32',18:'sint64'}
LABEL={1:'optional',2:'required',3:'repeated'}
def enum_obj(e):return {'values':{v.name:v.number for v in e.value},'reserved_ranges':[[r.start,r.end] for r in e.reserved_range],'reserved_names':sorted(e.reserved_name)}
def field_obj(f,oneofs):
 typ=TYPE[f.type]
 if f.type in (11,14):typ=f.type_name.lstrip('.')
 return {'number':f.number,'type':typ,'label':LABEL[f.label],'proto3_optional':bool(f.proto3_optional),'oneof':oneofs[f.oneof_index] if f.HasField('oneof_index') else None}
def message_obj(m,prefix):
 oneofs=[x.name for x in m.oneof_decl]
 out={'fields':{f.name:field_obj(f,oneofs) for f in m.field},'oneofs':{name:sorted([f.name for f in m.field if f.HasField('oneof_index') and oneofs[f.oneof_index]==name]) for name in oneofs},'reserved_ranges':[[r.start,r.end] for r in m.reserved_range],'reserved_names':sorted(m.reserved_name),'messages':{},'enums':{}}
 for n in m.nested_type:out['messages'][n.name]=message_obj(n,prefix+'.'+n.name)
 for e in m.enum_type:out['enums'][e.name]=enum_obj(e)
 return out
def build():
 result={'format':'CoreDRP protobuf structural baseline v1','files':{}}
 byname={f.name:f for f in fds.file}
 for name in sorted(TARGETS):
  if name not in byname:raise SystemExit('descriptor missing '+name)
  f=byname[name];fo={'package':f.package,'syntax':f.syntax,'dependencies':list(f.dependency),'messages':{},'enums':{},'services':{}}
  for m in f.message_type:fo['messages'][m.name]=message_obj(m,f.package+'.'+m.name)
  for e in f.enum_type:fo['enums'][e.name]=enum_obj(e)
  for s in f.service:
   fo['services'][s.name]={'methods':{m.name:{'input':m.input_type.lstrip('.'),'output':m.output_type.lstrip('.'),'client_streaming':bool(m.client_streaming),'server_streaming':bool(m.server_streaming)} for m in s.method}}
  result['files'][name]=fo
 return result
actual=build()
if not base.exists():
 print(json.dumps(actual,sort_keys=True,separators=(',',':')),file=sys.stderr);raise SystemExit('wire structural baseline missing')
expected=json.loads(base.read_text())
if expected.get('PENDING') is True:
 print('WIRE_STRUCTURE_BASELINE='+json.dumps(actual,sort_keys=True,separators=(',',':')),file=sys.stderr);raise SystemExit(1)
if actual!=expected:
 import difflib
 a=json.dumps(expected,sort_keys=True,indent=2).splitlines();b=json.dumps(actual,sort_keys=True,indent=2).splitlines()
 print('wire structural compatibility failure:',file=sys.stderr)
 print('\n'.join(difflib.unified_diff(a,b,fromfile='baseline',tofile='current',lineterm='')),file=sys.stderr)
 raise SystemExit(1)
print('CoreDRP protobuf structural baseline: OK')
