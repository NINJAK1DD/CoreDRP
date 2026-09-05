# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Canonical caller request bytes; typed schemas are normative registry data."""
import json,struct,hashlib,math
from pathlib import Path
SCHEMAS=json.loads((Path(__file__).resolve().parents[1]/'docs/coredrp-v1-request-schemas.json').read_text())
def integer(v,fmt):
    if type(v) is not int:raise ValueError('integer type')
    try:return struct.pack('>'+fmt,v)
    except struct.error as e:raise ValueError('integer range') from e
u16=lambda n:integer(n,'H')
u32=lambda n:integer(n,'I')
def lp(b):return u32(len(b))+b

def encode(kind,x):
    fields=SCHEMAS[kind]
    if set(x)!=set(f['name'] for f in fields):raise ValueError('missing/unknown request fields')
    return u16(1)+b''.join(value(f['type'],x[f['name']]) for f in fields)

def value(kind,x):
    if kind.startswith('?'):return b'\0' if x is None else b'\1'+value(kind[1:],x)
    if kind.startswith('array:'):
        child=kind[6:];records=[encode(child,r) for r in x]
        if child=='CommitmentRequestV1':
            indices=[r['output_index'] for r in x]
            if len(set(indices))!=len(indices):raise ValueError('duplicate commitment index')
            records=[b for _,b in sorted(zip(indices,records))]
        else:records.sort()
        return u32(len(records))+b''.join(lp(b) for b in records)
    if kind in SCHEMAS:return lp(encode(kind,x))
    if kind in ('u8','u16','u32','u64','i64'):return integer(x,dict(u8='B',u16='H',u32='I',u64='Q',i64='q')[kind])
    if kind=='bool':
        if type(x) is not bool:raise ValueError('boolean')
        return bytes([x])
    if kind=='f64':
        if type(x) is not float or not math.isfinite(x) or x<=0:raise ValueError('difficulty must be a positive finite double')
        return struct.pack('>d',x)
    if kind in ('uuid16','hash32','bytes'):
        b=bytes.fromhex(x)
        if kind!='bytes' and (len(b)!=(16 if kind=='uuid16' else 32) or kind=='uuid16' and not any(b)):raise ValueError('fixed bytes')
        return lp(b) if kind=='bytes' else b
    if kind in ('utf8','ascii'):return lp(x.encode('utf-8' if kind=='utf8' else 'ascii'))
    raise ValueError('unknown type')

def admission(lane,typ,scope,kind,x):
    if (typ,lane,kind) not in [(512,0,'MiningcoreAccountingShareRequestV1'),(513,1,'BitcoinDirectCoinbaseCandidateRequestV1'),(514,1,'CandidateStateUpdateRequestV1')]:raise ValueError('placement')
    q=scope.encode('ascii');r=encode(kind,x)
    return b'CoreDRP1-ADMISSION'+bytes([lane])+u16(typ)+u16(len(q))+q+lp(r)

def group_digest(accounting_id,request,event_time,payload):
    ph=hashlib.sha256(b'CoreDRP1-PAYLOAD'+lp(payload)).digest()
    return hashlib.sha256(u16(1)+value('uuid16',accounting_id)+lp(encode('MiningcoreAccountingShareRequestV1',request))+integer(event_time,'q')+ph).digest()

def accept_group(ledger,accounting_id,identity,digest):
    key=value('uuid16',accounting_id)
    if len(digest)!=32:raise ValueError('group digest width')
    if key in ledger:
        if ledger[key]!=(identity,digest):raise ValueError('INVALID_STATE_TRANSITION')
        return 'REPLAY_NO_EFFECT'
    ledger[key]=(identity,digest)
    return 'COMMIT_EFFECTS'

# ADMIN inputs preserve wire order; never repair invalid TLV ordering.
ADMIN_TYPES={
 4:['uuid16','u64','uuid16','u8','uuid16','u64','hash32','uuid16','i64','i64','utf8'],
 5:['uuid16','u64','uuid16','u8','uuid16','hash32','i64','i64','utf8'],
 6:['uuid16','u64','uuid16','u8','uuid16','u64','hash32','u64','u64','u64','uuid16','u8','utf8']}
def admin_body(action,fields):
    types=ADMIN_TYPES[action]
    if [f['id'] for f in fields]!=list(range(1,len(types)+1)):raise ValueError('ADMIN field order/set')
    out=u16(1)+u16(len(fields))
    for f,t in zip(fields,types):
        b=value(t,f['value'])
        if t=='utf8':b=b[4:]  # ADMIN TLV supplies the sole text length.
        out+=u16(f['id'])+lp(b)
    return out

def validate_admin_body(action,b):
    def take(n):
        nonlocal offset
        if offset+n>len(b):raise ValueError('ADMIN truncated')
        out=b[offset:offset+n];offset+=n;return out
    offset=0
    if take(2)!=u16(1) or take(2)!=u16(len(ADMIN_TYPES[action])):raise ValueError('ADMIN version/count')
    for i,t in enumerate(ADMIN_TYPES[action],1):
        if take(2)!=u16(i):raise ValueError('ADMIN field order')
        n=int.from_bytes(take(4),'big');v=take(n)
        size={'uuid16':16,'u64':8,'i64':8,'u8':1,'hash32':32}.get(t)
        if size is not None and n!=size:raise ValueError('ADMIN field width')
        if t=='uuid16' and not any(v):raise ValueError('ADMIN zero UUID')
        if t=='utf8':v.decode('utf-8',errors='strict')
    if offset!=len(b):raise ValueError('ADMIN trailing bytes')
    return b

def admin_preimage(action,fields):
    b=admin_body(action,fields);validate_admin_body(action,b)
    return b'CoreDRP1-ADMIN'+u16(action)+lp(b)
