# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
import asyncio,ssl,time,os
import psycopg
from grpclib.server import Server
from grpclib.client import Channel
from grpclib.encoding.proto import ProtoCodec
from grpclib.exceptions import GRPCError
from grpclib.const import Status
from protocol.coredrp_v1_grpc import DurableRelayBase,DurableRelayStub
from .wire import *
from .storage import Session

class LimitedCodec(ProtoCodec):
    def decode(self,data,message_type):
        if len(data)>256*1024:raise GRPCError(Status.RESOURCE_EXHAUSTED,'reference frame cap')
        return super().decode(data,message_type)

def tls(ca,cert,key,server=False):
    c=ssl.create_default_context(ssl.Purpose.CLIENT_AUTH if server else ssl.Purpose.SERVER_AUTH,cafile=str(ca))
    c.minimum_version=ssl.TLSVersion.TLSv1_3;c.maximum_version=ssl.TLSVersion.TLSv1_3
    c.verify_mode=ssl.CERT_REQUIRED;c.load_cert_chain(str(cert),str(key));c.set_alpn_protocols(['h2']);return c

def peer_id(peer,kind):
    cert=peer.cert() if peer else None
    require(cert is not None,'UNAUTHORIZED_SENDER')
    ids=[v for k,v in cert.get('subjectAltName',[]) if k=='URI' and v.startswith('urn:coredrp:')]
    require(len(ids)==1 and ids[0].startswith('urn:coredrp:'+kind+':'),'UNAUTHORIZED_SENDER')
    try:return uuid.UUID(ids[0].rsplit(':',1)[1]).bytes
    except ValueError:raise Failure('UNAUTHORIZED_SENDER') from None

# Use registry dispositions, not human exception text or database messages.
_OPERATOR={'SEQUENCE_GAP','CONTRACT_BINDING_CHANGED','ADMIN_ACTION_CONFLICT','SPLIT_LOG','SENDER_ROLLBACK','RECEIVER_ROLLBACK','RECOVERY_GAP','RECEIVER_INCARNATION_CHANGED','RECEIVER_ID_CHANGED','CHAIN_MISMATCH','CHECKPOINT_BACKDATED_EVENT','EVENT_IDENTITY_MISMATCH','INVALID_STATE_TRANSITION','EPOCH_NOT_APPROVED'}
def error(code):
    disposition=pb.ERROR_DISPOSITION_OPERATOR_INTERVENTION if code in _OPERATOR else pb.ERROR_DISPOSITION_PERMANENT_CONFIGURATION
    if code in ('RECEIVER_DURABILITY_UNAVAILABLE','RESOURCE_LIMIT_EXCEEDED','STREAM_ALREADY_ACTIVE','CLOCK_CONTRACT_VIOLATION'):disposition=pb.ERROR_DISPOSITION_STREAM_RETRYABLE
    if code=='SEMANTIC_PAYLOAD_INVALID':disposition=pb.ERROR_DISPOSITION_EVENT_QUARANTINABLE
    return pb.ServerFrame(error=pb.ProtocolError(code=pb.ErrorCode.Value(code),disposition=disposition,message=code))

class Receiver(DurableRelayBase):
    def __init__(self,dsn,paused=False):self.dsn=dsn;self.paused=paused;self.disconnected=False
    async def Stream(self,stream):
        session=None
        try:
            frame=await stream.recv_message()
            require(frame is not None and frame.WhichOneof('body')=='hello','MALFORMED_FRAME')
            require(peer_id(stream.peer,'sender')==frame.hello.sender_id,'UNAUTHORIZED_SENDER')
            session=Session(self.dsn,frame.hello)
            if self.paused:
                session.hello.window_events=session.hello.window_bytes=0
            await stream.send_message(pb.ServerFrame(hello=session.hello))
            window_events,window_bytes=MAX_BATCH,MAX_CHARGE
            if self.paused:
                window_events=window_bytes=0
                await stream.send_message(pb.ServerFrame(window_update=pb.WindowUpdate(window_events=0,window_bytes=0)))
            async for frame in stream:
                kind=frame.WhichOneof('body')
                if kind=='batch':
                    drop=os.environ.get('COREDRP_TEST_DISCONNECT') if not self.disconnected else None
                    if drop=='before_ingest':
                        self.disconnected=True;await stream.cancel();return
                    ack=session.ingest(frame.batch,window_events,window_bytes)
                    if drop=='after_ingest':
                        self.disconnected=True;await stream.cancel();return
                    ack.committed_at_unix_ms=int(time.time()*1000)
                    if self.paused:
                        window_events=window_bytes=0
                        await stream.send_message(pb.ServerFrame(window_update=pb.WindowUpdate(window_events=0,window_bytes=0)))
                    await stream.send_message(pb.ServerFrame(ack=ack))
                    if self.paused:
                        window_events,window_bytes=1+ack.committed_through_sequence%7,100
                        await stream.send_message(pb.ServerFrame(window_update=pb.WindowUpdate(window_events=window_events,window_bytes=window_bytes)))
                elif kind=='heartbeat':
                    await stream.send_message(pb.ServerFrame(heartbeat=pb.ServerHeartbeat(sent_at_unix_ms=int(time.time()*1000),committed_sequence=session.hello.committed_sequence)))
                    if self.paused:
                        window_events,window_bytes=MAX_BATCH,MAX_CHARGE
                        await stream.send_message(pb.ServerFrame(window_update=pb.WindowUpdate(window_events=window_events,window_bytes=window_bytes)))
                elif kind=='chain_probe_response':raise Failure('MALFORMED_FRAME')
                elif kind=='goodbye':
                    await stream.send_message(pb.ServerFrame(goodbye=pb.Goodbye(reason=pb.GOODBYE_REASON_GRACEFUL_SHUTDOWN)));return
                else:raise Failure('MALFORMED_FRAME')
        except Failure as e:await stream.send_message(error(e.code))
        except psycopg.Error:await stream.send_message(error('RECEIVER_DURABILITY_UNAVAILABLE'))
        finally:
            if session:session.close()

async def serve(dsn,host,port,ssl_context,ready=None,paused=False):
    server=Server([Receiver(dsn,paused)],codec=LimitedCodec())
    await server.start(host,port,ssl=ssl_context)
    if ready:ready.write_text('ready')
    try:await asyncio.Future()
    finally:server.close();await server.wait_closed()

async def drain(wal,host,port,ssl_context,receiver_id,timeout=10):
    # Stop-and-wait bounded batches; sender lock is held by caller for whole stream.
    async with Channel(host,port,ssl=ssl_context,codec=LimitedCodec()) as channel:
        async with DurableRelayStub(channel).Stream.open(timeout=timeout) as stream:
            await stream.send_request()
            require(peer_id(stream.peer,'receiver')==receiver_id,'RECEIVER_ID_CHANGED')
            await stream.send_message(pb.ClientFrame(hello=wal.hello()))
            frame=await stream.recv_message()
            require(frame is not None,'INVALID_HANDSHAKE')
            if frame.WhichOneof('body')=='error':raise Failure(pb.ErrorCode.Name(frame.error.code))
            require(frame.WhichOneof('body')=='hello','INVALID_HANDSHAKE')
            h=frame.hello
            require(h.receiver_id==receiver_id,'RECEIVER_ID_CHANGED')
            require(h.max_event_payload_bytes>0 and h.max_batch_events>0 and h.max_batch_payload_bytes>0,'INVALID_HANDSHAKE')
            payload_limit=min(h.max_event_payload_bytes,MAX_PAYLOAD)
            batch_events=min(h.max_batch_events,MAX_BATCH)
            batch_bytes=min(h.max_batch_payload_bytes,MAX_CHARGE)
            require(h.window_events<=h.max_batch_events and h.window_bytes<=h.max_batch_payload_bytes,'INVALID_HANDSHAKE')
            wal.bind(h);we,wb=h.window_events,h.window_bytes
            # Control exchange before data also consumes an initial WindowUpdate.
            await stream.send_message(pb.ClientFrame(heartbeat=pb.ClientHeartbeat(durable_tail_sequence=wal.state['tail'],oldest_retained_sequence=1)))
            waiting_heartbeat=True;inflight=None
            while waiting_heartbeat or wal.state['ack']<wal.state['tail']:
                if not waiting_heartbeat and inflight is None and we and wb:
                    batch=[];size=0
                    for e in wal.events[wal.state['ack']:]:
                        require(len(e.payload)<=payload_limit,'EVENT_TOO_LARGE')
                        require(charge(e)<=batch_bytes,'EVENT_TOO_LARGE')
                        if len(batch)>=min(we,batch_events) or size+charge(e)>min(wb,batch_bytes):break
                        batch.append(e);size+=charge(e)
                    if batch:
                        inflight=batch[-1].sequence
                        await stream.send_message(pb.ClientFrame(batch=pb.EventBatch(first_sequence=batch[0].sequence,events=batch,terminal_chain_hash=wal.hashes[batch[-1].sequence])))
                frame=await stream.recv_message();require(frame is not None,'RECEIVER_DURABILITY_UNAVAILABLE')
                kind=frame.WhichOneof('body')
                if kind=='error':raise Failure(pb.ErrorCode.Name(frame.error.code))
                if kind=='ack':
                    require(inflight is not None and frame.ack.committed_through_sequence==inflight,'MALFORMED_FRAME')
                    wal.acknowledge(frame.ack.committed_through_sequence,frame.ack.committed_chain_hash);inflight=None
                elif kind=='window_update':
                    require(frame.window_update.window_events<=h.max_batch_events and frame.window_update.window_bytes<=h.max_batch_payload_bytes,'RESOURCE_LIMIT_EXCEEDED')
                    we,wb=frame.window_update.window_events,frame.window_update.window_bytes
                elif kind=='heartbeat':waiting_heartbeat=False
                else:raise Failure('MALFORMED_FRAME')
            await stream.send_message(pb.ClientFrame(goodbye=pb.Goodbye(reason=pb.GOODBYE_REASON_GRACEFUL_SHUTDOWN)),end=True)
            # Drain remaining control frames before trailing metadata.
            async for frame in stream:
                if frame.WhichOneof('body')=='error':raise Failure(pb.ErrorCode.Name(frame.error.code))
