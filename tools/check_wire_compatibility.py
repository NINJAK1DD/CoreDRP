#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Reject unreviewed changes to the complete Draft 0.3 protobuf wire surface."""
from pathlib import Path
import json,re,sys
R=Path(__file__).resolve().parents[1]
B=json.loads((R/'docs/coredrp-v1-wire-baseline.json').read_text(encoding='utf-8'))
PKG=json.loads((R/'docs/coredrp-v1-package-baseline.json').read_text(encoding='utf-8'))
COMMENT_RE=re.compile(r'//.*?$|/\*.*?\*/',re.M|re.S)
FIELD_RE=re.compile(r'(?<![\w.])(?:(optional|repeated)\s+)?([\w.]+)\s+(\w+)\s*=\s*(\d+)\s*;')
def die(s):print('wire compatibility failure:',s,file=sys.stderr);raise SystemExit(1)
def text(path):return COMMENT_RE.sub('',(R/path).read_text(encoding='utf-8'))
def package(path):
 t=text(path);m=re.search(r'\bpackage\s+([\w.]+)\s*;',t)
 if not m:die(f'{path}: missing package declaration')
 return m.group(1)
def named_block(t,kind,name):
 m=re.search(r'\b'+re.escape(kind)+r'\s+'+re.escape(name)+r'\s*\{',t)
 if not m:return None
 depth=1;i=m.end()
 while i<len(t) and depth:
  depth+=(t[i]=='{')-(t[i]=='}');i+=1
 if depth:die(f'unterminated {kind} {name}')
 return t[m.end():i-1]
def fields(path,msg):
 body=named_block(text(path),'message',msg)
 if body is None:return None
 out={}
 for q,ty,n,num in FIELD_RE.findall(body):
  sig=(f'{q} ' if q else '')+ty+' '+n
  if num in out:die(f'duplicate field {path}:{msg}:{num}')
  out[num]=sig
 return out
def enum_values(path,name):
 body=named_block(text(path),'enum',name)
 if body is None:return None
 return {n:int(v) for n,v in re.findall(r'\b([A-Z][A-Z0-9_]*)\s*=\s*(-?\d+)\s*;',body)}
def oneofs(path,msg):
 body=named_block(text(path),'message',msg)
 if body is None:return None
 out={}
 for m in re.finditer(r'\boneof\s+(\w+)\s*\{',body):
  name=m.group(1);depth=1;i=m.end()
  while i<len(body) and depth:
   depth+=(body[i]=='{')-(body[i]=='}');i+=1
  if depth:die(f'unterminated oneof {path}:{msg}:{name}')
  ob=body[m.end():i-1];vals={}
  for q,ty,n,num in FIELD_RE.findall(ob):vals[num]=(f'{q} ' if q else '')+ty+' '+n
  out[name]=vals
 return out
def services(path):
 t=text(path);pkg=package(path);out={}
 for name in re.findall(r'\bservice\s+(\w+)\s*\{',t):
  body=named_block(t,'service',name);rpcs={}
  for rn,cs,inp,ss,outp in re.findall(r'\brpc\s+(\w+)\s*\(\s*(stream\s+)?([\w.]+)\s*\)\s*returns\s*\(\s*(stream\s+)?([\w.]+)\s*\)\s*;',body):rpcs[rn]=(('stream ' if cs else '')+inp+' -> '+('stream ' if ss else '')+outp)
  out[f'{pkg}.{name}']=rpcs
 return out
def reserved(path,kind,name):
 body=named_block(text(path),kind,name)
 if body is None:return None
 vals=[]
 for x in re.findall(r'\breserved\s+([^;]+);',body):
  vals += [re.sub(r'\s+',' ',p.strip()) for p in x.split(',')]
 return vals
# Package identities are part of the wire contract because they define fully qualified type/service names.
for path,expected in PKG.items():
 got=package(path)
 if got!=expected:die(f'{path} package changed: expected {expected!r}, got {got!r}')
# Exact baseline equality: additions as well as mutations require explicit baseline review.
for path,msgs in B['messages'].items():
 current_names=set(re.findall(r'\bmessage\s+(\w+)\s*\{',text(path)))
 if current_names!=set(msgs):die(f'{path} message set changed: expected {sorted(msgs)}, got {sorted(current_names)}')
 for msg,expected in msgs.items():
  got=fields(path,msg)
  if got!=expected:die(f'{path}:{msg} fields changed: expected {expected}, got {got}')
for path,enums in B['enums'].items():
 current_names=set(re.findall(r'\benum\s+(\w+)\s*\{',text(path)))
 if current_names!=set(enums):die(f'{path} enum set changed: expected {sorted(enums)}, got {sorted(current_names)}')
 for name,expected in enums.items():
  got=enum_values(path,name)
  if got!=expected:die(f'{path}:{name} enum values changed: expected {expected}, got {got}')
# Compare oneof layout for every message, including messages that are expected to have no oneofs.
for path,msgs in B['messages'].items():
 expected_by_message=B.get('oneofs',{}).get(path,{})
 for msg in msgs:
  expected=expected_by_message.get(msg,{})
  got=oneofs(path,msg)
  if got!=expected:die(f'{path}:{msg} oneofs changed: expected {expected}, got {got}')
for path,expected in B.get('services',{}).items():
 expected_fq={f'{PKG[path]}.{name}':rpcs for name,rpcs in expected.items()}
 got=services(path)
 if got!=expected_fq:die(f'{path} services changed: expected {expected_fq}, got {got}')
for path,items in B.get('reserved',{}).items():
 enum_names=set(B.get('enums',{}).get(path,{}))
 for name,expected in items.items():
  kind='enum' if name in enum_names else 'message';got=reserved(path,kind,name)
  if got!=expected:die(f'{path}:{name} reserved declarations changed: expected {expected}, got {got}')
print('CoreDRP full protobuf wire surface: OK')
