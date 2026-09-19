# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Dedicated PostgreSQL database only. Ingest/effect/head share one transaction."""
import hashlib,uuid
import psycopg
from .wire import *
from .faults import hit
SCHEMA='''
CREATE SCHEMA IF NOT EXISTS coredrp_ref;
CREATE TABLE IF NOT EXISTS coredrp_ref.identity (
 singleton boolean PRIMARY KEY CHECK(singleton), receiver bytea NOT NULL, incarnation bytea NOT NULL);
CREATE TABLE IF NOT EXISTS coredrp_ref.streams (
 sender bytea PRIMARY KEY, epoch bytea NOT NULL, head bigint NOT NULL,
 chain bytea NOT NULL, owner bigint NOT NULL DEFAULT 0, checkpoint bigint NOT NULL DEFAULT -1,
 last_time bigint NOT NULL DEFAULT 0, binding bytea NOT NULL);
CREATE TABLE IF NOT EXISTS coredrp_ref.events (
 sender bytea NOT NULL, epoch bytea NOT NULL, sequence bigint NOT NULL,
 relay bytea NOT NULL UNIQUE, event bytea NOT NULL, payload bytea NOT NULL,
 chain bytea NOT NULL, PRIMARY KEY(sender,epoch,sequence));
CREATE TABLE IF NOT EXISTS coredrp_ref.effects (
 sender bytea NOT NULL, epoch bytea NOT NULL, sequence bigint NOT NULL,
 complete_through bigint NOT NULL, PRIMARY KEY(sender,epoch,sequence),
 FOREIGN KEY(sender,epoch,sequence) REFERENCES coredrp_ref.events);
CREATE TABLE IF NOT EXISTS coredrp_ref.admin (
 id uuid PRIMARY KEY, request bytea NOT NULL, action text NOT NULL);
'''

def connect(dsn):
    db=psycopg.connect(dsn,autocommit=True)
    try:
        require(db.execute('SELECT current_database()').fetchone()[0].startswith('coredrp_ref_'),'ISOLATED_DATABASE_REQUIRED')
        for name in ('fsync','full_page_writes'):
            require(db.execute('SHOW '+name).fetchone()[0]=='on','RECEIVER_DURABILITY_UNAVAILABLE')
        return db
    except BaseException:db.close();raise

def bootstrap(dsn,receiver,incarnation,sender,epoch,admin_id):
    uid(receiver);uid(incarnation);uid(sender);uid(epoch)
    request=H(receiver+incarnation+sender+epoch+BINDING)
    with connect(dsn) as db:
        with db.transaction():
            db.execute('SET LOCAL synchronous_commit=on')
            db.execute('SELECT pg_advisory_xact_lock(731994010)')
            db.execute(SCHEMA)
            old=db.execute('SELECT request FROM coredrp_ref.admin WHERE id=%s',(admin_id,)).fetchone()
            if old:require(bytes(old[0])==request,'IDEMPOTENCY_KEY_CONFLICT');return
            ident=db.execute('SELECT receiver,incarnation FROM coredrp_ref.identity').fetchone()
            if ident:require(tuple(map(bytes,ident))==(receiver,incarnation),'ADMIN_ACTION_CONFLICT')
            else:db.execute('INSERT INTO coredrp_ref.identity VALUES(true,%s,%s)',(receiver,incarnation))
            require(db.execute('SELECT 1 FROM coredrp_ref.streams WHERE sender=%s',(sender,)).fetchone() is None,'ADMIN_ACTION_CONFLICT')
            db.execute('INSERT INTO coredrp_ref.streams(sender,epoch,head,chain,binding) VALUES(%s,%s,0,%s,%s)',(sender,epoch,genesis(sender,epoch),BINDING))
            db.execute('INSERT INTO coredrp_ref.admin VALUES(%s,%s,%s)',(admin_id,request,'INITIAL_EPOCH_APPROVAL'))

class Session:
    def __init__(self,dsn,h):
        require(h.protocol_major==h.protocol_minor==1,'PROTOCOL_VERSION_MISMATCH')
        uid(h.sender_id);uid(h.log_epoch)
        require(h.lane_id==0,'LANE_ID_OUT_OF_RANGE')
        require(not h.profiles and not h.scope_contracts and list(h.supported_event_types)==[1],'SEMANTIC_CONTRACT_MISMATCH')
        require(h.earliest_retained_sequence==1 and h.durable_tail_sequence<=2**63-1,'INVALID_HANDSHAKE')
        require(h.HasField('remembered_ack_sequence')==h.HasField('remembered_ack_chain_hash'),'INVALID_HANDSHAKE')
        if h.HasField('remembered_ack_sequence'):
            require(h.remembered_ack_sequence<=h.durable_tail_sequence and len(h.remembered_ack_chain_hash)==32,'INVALID_HANDSHAKE')
        if h.HasField('remembered_contract_binding_digest'):require(h.remembered_contract_binding_digest==BINDING,'CONTRACT_BINDING_CHANGED')
        self.db=connect(dsn);self.sender=h.sender_id;self.epoch=h.log_epoch
        try:
            lock=int.from_bytes(H(b'lane0'+h.sender_id)[:8],'big',signed=True)
            require(self.db.execute('SELECT pg_try_advisory_lock(%s)',(lock,)).fetchone()[0],'STREAM_ALREADY_ACTIVE')
            with self.db.transaction():
                self.db.execute('SET LOCAL synchronous_commit=on')
                row=self.db.execute('SELECT epoch,head,chain,owner,binding FROM coredrp_ref.streams WHERE sender=%s FOR UPDATE',(self.sender,)).fetchone()
                require(row is not None and bytes(row[0])==self.epoch,'EPOCH_NOT_APPROVED')
                require(bytes(row[4])==BINDING,'CONTRACT_BINDING_CHANGED')
                require(row[1]<=h.durable_tail_sequence,'SENDER_ROLLBACK')
                if h.HasField('remembered_ack_sequence'):
                    require(row[1]>=h.remembered_ack_sequence,'RECEIVER_ROLLBACK')
                    remembered=genesis(self.sender,self.epoch) if h.remembered_ack_sequence==0 else bytes(self.db.execute('SELECT chain FROM coredrp_ref.events WHERE sender=%s AND epoch=%s AND sequence=%s',(self.sender,self.epoch,h.remembered_ack_sequence)).fetchone()[0])
                    require(remembered==h.remembered_ack_chain_hash,'SPLIT_LOG')
                self.owner=row[3]+1
                self.db.execute('UPDATE coredrp_ref.streams SET owner=%s WHERE sender=%s',(self.owner,self.sender))
                ident=self.db.execute('SELECT receiver,incarnation FROM coredrp_ref.identity').fetchone()
                self.hello=pb.ServerHello(protocol_major=1,protocol_minor=1,receiver_id=bytes(ident[0]),receiver_database_epoch=bytes(ident[1]),committed_sequence=row[1],committed_chain_hash=bytes(row[2]),accepted_event_types=[1],max_event_payload_bytes=MAX_PAYLOAD,max_batch_payload_bytes=MAX_CHARGE,max_batch_events=MAX_BATCH,window_events=MAX_BATCH,window_bytes=MAX_CHARGE,contract_binding_digest=BINDING)
        except BaseException:self.close();raise
    def close(self):self.db.close()
    def ingest(self,batch,window_events=MAX_BATCH,window_bytes=MAX_CHARGE):
        es=batch.events
        require(0<len(es)<=MAX_BATCH and len(es)<=window_events,'RESOURCE_LIMIT_EXCEEDED')
        require(sum(map(charge,es))<=min(MAX_CHARGE,window_bytes),'RESOURCE_LIMIT_EXCEEDED')
        require(batch.first_sequence==es[0].sequence,'SEQUENCE_GAP')
        for e in es:validate(e)
        with self.db.transaction():
            self.db.execute('SET LOCAL synchronous_commit=on')
            row=self.db.execute('SELECT epoch,head,chain,owner,checkpoint,last_time FROM coredrp_ref.streams WHERE sender=%s FOR UPDATE',(self.sender,)).fetchone()
            require(bytes(row[0])==self.epoch and row[3]==self.owner,'STREAM_ALREADY_ACTIVE')
            head,old_hash,floor,last=row[1],bytes(row[2]),row[4],row[5]
            first=es[0].sequence;require(first<=head+1,'SEQUENCE_GAP')
            if first==1:prev=genesis(self.sender,self.epoch)
            else:
                ancestor=self.db.execute('SELECT chain FROM coredrp_ref.events WHERE sender=%s AND epoch=%s AND sequence=%s',(self.sender,self.epoch,first-1)).fetchone()
                require(ancestor is not None,'RECOVERY_GAP');prev=bytes(ancestor[0])
            prepared=[]
            for i,e in enumerate(es):
                require(e.sequence==first+i,'SEQUENCE_GAP');prev=chain(prev,self.sender,self.epoch,e);prepared.append((e,prev))
            require(prev==batch.terminal_chain_hash,'CHAIN_MISMATCH')
            for e,ch in prepared:
                if e.sequence<=head:
                    stored=self.db.execute('SELECT event,chain FROM coredrp_ref.events WHERE sender=%s AND epoch=%s AND sequence=%s',(self.sender,self.epoch,e.sequence)).fetchone()
                    require(stored is not None and bytes(stored[0])==e.SerializeToString() and bytes(stored[1])==ch,'EVENT_IDENTITY_MISMATCH');continue
                boundary=validate(e)
                require(e.sequence==head+1,'SEQUENCE_GAP')
                require(e.event_time_unix_ms>=last and e.event_time_unix_ms>floor and boundary>=floor,'CHECKPOINT_BACKDATED_EVENT')
                require(self.db.execute('SELECT 1 FROM coredrp_ref.events WHERE relay=%s',(e.relay_event_id,)).fetchone() is None,'EVENT_IDENTITY_MISMATCH')
                self.db.execute('INSERT INTO coredrp_ref.events VALUES(%s,%s,%s,%s,%s,%s,%s)',(self.sender,self.epoch,e.sequence,e.relay_event_id,e.SerializeToString(),e.payload,ch))
                self.db.execute('INSERT INTO coredrp_ref.effects VALUES(%s,%s,%s,%s)',(self.sender,self.epoch,e.sequence,boundary))
                head,old_hash,last,floor=e.sequence,ch,e.event_time_unix_ms,boundary
            self.db.execute('UPDATE coredrp_ref.streams SET head=%s,chain=%s,last_time=%s,checkpoint=%s WHERE sender=%s AND owner=%s',(head,old_hash,last,floor,self.sender,self.owner))
            hit('before_receiver_commit')
        hit('after_receiver_commit')
        return pb.Ack(committed_through_sequence=head,committed_chain_hash=old_hash)
