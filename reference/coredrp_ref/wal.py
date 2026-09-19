# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Checksummed append-only WAL, fsynced anchor, and POSIX sender fencing.

No pruning or repair is automatic. Every uncertain/corrupt record fails closed.
"""
import fcntl,json,os,struct
from pathlib import Path
from .wire import pb,require,Failure,H,genesis,chain,validate,checkpoint,BINDING
from .faults import hit,io_fault

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def atomic(path,obj):
    raw=canonical(obj);data=canonical({'data':obj,'sha256':H(raw).hex()})
    temp=path.with_suffix('.new')
    with open(temp,'wb') as f:
        io_fault('anchor_write');require(f.write(data)==len(data),'WAL_IO_FAILURE');f.flush()
        io_fault('anchor_fsync');os.fsync(f.fileno())
    io_fault('anchor_replace');os.replace(temp,path)
    io_fault('anchor_directory_fsync');syncdir(path.parent)
def read_anchor(path):
    try:
        x=json.loads(path.read_bytes());require(H(canonical(x['data'])).hex()==x['sha256'],'WAL_CORRUPTION');return x['data']
    except (ValueError,KeyError):raise Failure('WAL_CORRUPTION') from None

class WAL:
    def __init__(self,path,sender=None,epoch=None,cap=1024*1024):
        self.healthy=True
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True);syncdir(self.path.parent)
        self.lock=open(self.path/'writer.lock','a+b')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:self.lock.close();raise Failure('STREAM_ALREADY_ACTIVE') from None
        self.file=None
        try:
            anchor=self.path/'anchor.json'
            if not anchor.exists():
                require(sender is not None and epoch is not None and not (self.path/'events.wal').exists(),'RECOVERY_GAP')
                genesis(sender,epoch)
                self.state=dict(sender=sender.hex(),epoch=epoch.hex(),tail=0,tail_hash=genesis(sender,epoch).hex(),ack=0,ack_hash=genesis(sender,epoch).hex(),receiver=None,incarnation=None,bound=False,cap=cap,last_time=0,checkpoint=-1)
                atomic(anchor,self.state)
            self.state=read_anchor(anchor)
            require(sender is None or self.state['sender']==sender.hex(),'INVALID_HANDSHAKE')
            require(epoch is None or self.state['epoch']==epoch.hex(),'EPOCH_NOT_APPROVED')
            self.sender=bytes.fromhex(self.state['sender']);self.epoch=bytes.fromhex(self.state['epoch'])
            # Common parent is the provisioned local durability domain. Cloned paths
            # must stay under it; copying identities across hosts is not supported.
            fences=self.path.parent/'sender-fences';fences.mkdir(exist_ok=True);syncdir(fences.parent)
            self.identity_lock=open(fences/(self.state['sender']+'.lane0.lock'),'a+b')
            try:fcntl.flock(self.identity_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Failure('STREAM_ALREADY_ACTIVE') from None
            if not (self.path/'events.wal').exists():
                require(self.state['tail']==0,'WAL_CORRUPTION')
                with open(self.path/'events.wal','xb') as f:f.flush();os.fsync(f.fileno())
                syncdir(self.path)
            self.file=open(self.path/'events.wal','r+b',buffering=0)
            self.recover()
        except BaseException:self.close();raise
    def close(self):
        self.healthy=False
        if self.file:self.file.close()
        if hasattr(self,'identity_lock'):self.identity_lock.close()
        self.lock.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def check(self):require(self.healthy,'WAL_REOPEN_REQUIRED')
    def save(self):
        self.check()
        try:atomic(self.path/'anchor.json',self.state)
        except (OSError,Failure):
            self.close();raise Failure('WAL_IO_FAILURE') from None
    def increase_cap(self,cap):
        self.check()
        require(type(cap) is int and cap>self.state['cap'],'INVALID_CAP_INCREASE')
        self.state['cap']=cap;self.save()
    def recover(self):
        self.events=[];self.keys={};self.hashes=[genesis(self.sender,self.epoch)]
        self.file.seek(0);last_time=0;floor=-1
        try:
            while header:=self.file.read(8):
                require(len(header)==8 and header[:4]==b'DRP1','WAL_CORRUPTION')
                n=struct.unpack('>I',header[4:])[0];require(0<n<=16384,'WAL_CORRUPTION')
                raw=self.file.read(n);digest=self.file.read(32)
                require(len(raw)==n and H(header+raw)==digest,'WAL_CORRUPTION')
                x=json.loads(raw);e=pb.Event.FromString(bytes.fromhex(x['event']))
                require(e.sequence==len(self.events)+1 and x['key'] not in self.keys,'WAL_CORRUPTION')
                boundary=validate(e);require(e.event_time_unix_ms>=last_time and e.event_time_unix_ms>floor and boundary>=floor,'WAL_CORRUPTION')
                ch=chain(self.hashes[-1],self.sender,self.epoch,e);require(ch.hex()==x['chain'],'WAL_CORRUPTION')
                self.events.append(e);self.hashes.append(ch);self.keys[x['key']]=(x['request'],e.sequence)
                last_time=e.event_time_unix_ms;floor=boundary
            t=self.state['tail'];require(0<=t<=len(self.events) and self.hashes[t].hex()==self.state['tail_hash'],'WAL_CORRUPTION')
            a=self.state['ack'];require(0<=a<=t and self.hashes[a].hex()==self.state['ack_hash'],'WAL_CORRUPTION')
        except (ValueError,KeyError,IndexError):raise Failure('WAL_CORRUPTION') from None
        # A complete suffix may have survived a failed fsync without being durable.
        # Sync it before advancing the durable anchor or returning caller success.
        io_fault('recovery_fsync');os.fsync(self.file.fileno())
        # Complete fsynced suffix beyond a lagging anchor is retained, never discarded.
        self.state.update(tail=len(self.events),tail_hash=self.hashes[-1].hex(),last_time=last_time,checkpoint=floor);self.save()
    def admit_checkpoint(self,key,event_time,boundary):
        self.check()
        require(isinstance(key,str) and 0<len(key.encode())<=128,'INVALID_HANDSHAKE')
        request=H(canonical([event_time,boundary])).hex()
        if key in self.keys:
            old,seq=self.keys[key];require(old==request,'IDEMPOTENCY_KEY_CONFLICT');return seq
        require(self.state['bound'],'EPOCH_NOT_APPROVED')
        e=checkpoint(self.state['tail']+1,event_time,boundary);validate(e)
        require(event_time>=self.state['last_time'] and event_time>self.state['checkpoint'] and boundary>=self.state['checkpoint'],'CHECKPOINT_BACKDATED_EVENT')
        ch=chain(self.hashes[-1],self.sender,self.epoch,e)
        raw=canonical(dict(key=key,request=request,event=e.SerializeToString().hex(),chain=ch.hex()));header=b'DRP1'+struct.pack('>I',len(raw));record=header+raw+H(header+raw)
        self.file.seek(0,2);require(self.file.tell()+len(record)<=self.state['cap'],'RESOURCE_LIMIT_EXCEEDED')
        hit('before_wal_write')
        try:
            io_fault('wal_write')
            require(self.file.write(record)==len(record),'WAL_IO_FAILURE')
            io_fault('wal_fsync');os.fsync(self.file.fileno());hit('after_wal_fsync')
            self.state.update(tail=e.sequence,tail_hash=ch.hex(),last_time=event_time,checkpoint=boundary);self.save();hit('after_anchor_fsync')
        except OSError:
            self.close();raise Failure('WAL_IO_FAILURE') from None
        except BaseException:
            # Caller must reopen/recover before further work following an IO failure.
            self.close();raise
        self.events.append(e);self.hashes.append(ch);self.keys[key]=(request,e.sequence);return e.sequence
    def acknowledge(self,seq,digest):
        self.check()
        require(self.state['ack']<=seq<=self.state['tail'],'SENDER_ROLLBACK')
        require(self.hashes[seq]==digest,'SPLIT_LOG')
        if seq==self.state['ack']:return
        hit('before_ack_persist')
        self.state.update(ack=seq,ack_hash=digest.hex());self.save();hit('after_ack_persist')
    def bind(self,h):
        self.check()
        require(len(h.receiver_id)==16 and len(h.receiver_database_epoch)==16,'INVALID_HANDSHAKE')
        if self.state['receiver'] is not None:
            require(self.state['receiver']==h.receiver_id.hex(),'RECEIVER_ID_CHANGED')
            require(self.state['incarnation']==h.receiver_database_epoch.hex(),'RECEIVER_INCARNATION_CHANGED')
        require(h.protocol_major==h.protocol_minor==1 and h.contract_binding_digest==BINDING,'CONTRACT_BINDING_CHANGED')
        require(not h.profiles and not h.scope_contracts and list(h.accepted_event_types)==[1],'SEMANTIC_CONTRACT_MISMATCH')
        require(h.committed_sequence<=self.state['tail'],'SENDER_ROLLBACK')
        require(h.committed_sequence>=self.state['ack'],'RECEIVER_ROLLBACK')
        require(self.hashes[h.committed_sequence]==h.committed_chain_hash,'SPLIT_LOG')
        self.state.update(receiver=h.receiver_id.hex(),incarnation=h.receiver_database_epoch.hex(),bound=True);self.save()
        self.acknowledge(h.committed_sequence,h.committed_chain_hash)
    def hello(self):
        self.check()
        h=pb.ClientHello(protocol_major=1,protocol_minor=1,sender_id=self.sender,lane_id=0,log_epoch=self.epoch,earliest_retained_sequence=1,durable_tail_sequence=self.state['tail'],remembered_ack_sequence=self.state['ack'],remembered_ack_chain_hash=bytes.fromhex(self.state['ack_hash']),supported_event_types=[1],implementation_name='coredrp-reference',implementation_version='0.1')
        if self.state['bound']:h.remembered_contract_binding_digest=BINDING
        return h
