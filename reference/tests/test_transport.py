# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Scripted peer exercises sender negotiation; live TLS/DB tests are separate."""
import asyncio
import uuid
from types import SimpleNamespace

import pytest
from coredrp_ref import transport
from coredrp_ref.wal import WAL
from coredrp_ref.wire import BINDING, MAX_BATCH, MAX_CHARGE, MAX_PAYLOAD, Failure, charge, pb


def exchange(monkeypatch, wal, hello, updates=()):
    batches=[]
    class Stream:
        peer=None
        def __init__(self):self.queue=[pb.ServerFrame(hello=hello)]
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def send_request(self):pass
        async def send_message(self,frame,**kwargs):
            kind=frame.WhichOneof('body')
            if kind=='heartbeat':
                self.queue.append(pb.ServerFrame(heartbeat=pb.ServerHeartbeat()))
                self.queue.extend(pb.ServerFrame(window_update=u) for u in updates)
            elif kind=='batch':
                batches.append(frame.batch)
                self.queue.append(pb.ServerFrame(ack=pb.Ack(committed_through_sequence=frame.batch.events[-1].sequence,committed_chain_hash=frame.batch.terminal_chain_hash)))
        async def recv_message(self):
            assert self.queue,'sender stalled with no peer response pending'
            return self.queue.pop(0)
        def __aiter__(self):return self
        async def __anext__(self):
            if self.queue:return self.queue.pop(0)
            raise StopAsyncIteration
    stream=Stream()
    class Channel:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    monkeypatch.setattr(transport,'Channel',Channel)
    monkeypatch.setattr(transport,'DurableRelayStub',lambda channel:SimpleNamespace(Stream=SimpleNamespace(open=lambda **kw:stream)))
    monkeypatch.setattr(transport,'peer_id',lambda *args:b'r'*16)
    asyncio.run(transport.drain(wal,'localhost',1,None,b'r'*16))
    return batches


@pytest.fixture
def sender(tmp_path):
    with WAL(tmp_path/'wal',uuid.uuid4().bytes,uuid.uuid4().bytes) as wal:
        hello=pb.ServerHello(protocol_major=1,protocol_minor=1,receiver_id=b'r'*16,receiver_database_epoch=b'd'*16,accepted_event_types=[1],contract_binding_digest=BINDING,committed_chain_hash=wal.hashes[0],max_event_payload_bytes=MAX_PAYLOAD,max_batch_events=MAX_BATCH,max_batch_payload_bytes=MAX_CHARGE,window_events=MAX_BATCH,window_bytes=MAX_CHARGE)
        wal.bind(hello)
        for i in range(70):wal.admit_checkpoint(str(i),100+i,99+i)
        yield wal,hello


@pytest.mark.parametrize('peer_events,peer_bytes',[(1000,16*1024*1024),(3,100),(1000,100)])
def test_peer_caps_bound_outgoing_batches(monkeypatch,sender,peer_events,peer_bytes):
    wal,hello=sender
    hello.max_event_payload_bytes=16*1024*1024
    hello.max_batch_events=hello.window_events=peer_events
    hello.max_batch_payload_bytes=hello.window_bytes=peer_bytes
    batches=exchange(monkeypatch,wal,hello)
    assert wal.state['ack']==70
    assert [e.sequence for b in batches for e in b.events]==list(range(1,71))
    assert all(len(b.events)<=min(peer_events,MAX_BATCH) for b in batches)
    assert all(sum(map(charge,b.events))<=min(peer_bytes,MAX_CHARGE) for b in batches)


@pytest.mark.parametrize('initial',[0,1])
def test_credit_can_grow_after_hello(monkeypatch,sender,initial):
    wal,hello=sender
    hello.window_events=initial
    hello.window_bytes=initial*100
    batches=exchange(monkeypatch,wal,hello,[pb.WindowUpdate(window_events=MAX_BATCH,window_bytes=MAX_CHARGE)])
    assert wal.state['ack']==70
    assert any(len(b.events)>initial for b in batches)


@pytest.mark.parametrize('field',['window_events','window_bytes'])
def test_credit_above_peer_maximum_rejected(monkeypatch,sender,field):
    wal,hello=sender
    hello.window_events=hello.window_bytes=0
    update=pb.WindowUpdate(window_events=MAX_BATCH,window_bytes=MAX_CHARGE)
    setattr(update,field,getattr(update,field)+1)
    with pytest.raises(Failure,match='RESOURCE_LIMIT_EXCEEDED'):exchange(monkeypatch,wal,hello,[update])
    assert wal.state['ack']==0


@pytest.mark.parametrize('field',['max_event_payload_bytes','max_batch_events','max_batch_payload_bytes'])
def test_zero_peer_maximum_rejected(monkeypatch,sender,field):
    wal,hello=sender
    setattr(hello,field,0)
    with pytest.raises(Failure,match='INVALID_HANDSHAKE'):exchange(monkeypatch,wal,hello)


def test_local_byte_cap_still_applies_to_large_peer_credit(monkeypatch,sender):
    wal,hello=sender
    monkeypatch.setattr(transport,'MAX_CHARGE',100)
    hello.max_batch_events=1000
    hello.max_batch_payload_bytes=16*1024*1024
    hello.window_events=hello.window_bytes=0
    batches=exchange(monkeypatch,wal,hello,[pb.WindowUpdate(window_events=1000,window_bytes=16*1024*1024)])
    assert wal.state['ack']==70
    assert all(sum(map(charge,b.events))<=100 for b in batches)


def test_payload_above_peer_cap_stops_before_send(monkeypatch,sender):
    wal,hello=sender
    hello.max_event_payload_bytes=1
    with pytest.raises(Failure,match='EVENT_TOO_LARGE'):exchange(monkeypatch,wal,hello)
    assert wal.state['ack']==0


def test_insufficient_temporary_byte_credit_waits_for_update(monkeypatch,sender):
    wal,hello=sender
    hello.window_bytes=1
    batches=exchange(monkeypatch,wal,hello,[pb.WindowUpdate(window_events=MAX_BATCH,window_bytes=MAX_CHARGE)])
    assert wal.state['ack']==70 and batches


def test_repeated_pause_resume_changing_credit(monkeypatch,sender):
    wal,hello=sender
    hello.window_events=hello.window_bytes=0
    # Updates can arrive while a batch is in flight; only the next batch uses
    # the replacement credit. Include insufficient positive credit and pauses.
    updates=[pb.WindowUpdate(window_events=n,window_bytes=b) for n,b in [(1,100),(0,0),(3,1),(0,100),(2,100),(0,0),(4,200)]]
    batches=exchange(monkeypatch,wal,hello,updates)
    assert wal.state['ack']==70
    assert len(batches[0].events)==1 and all(len(b.events)<=4 for b in batches)
