# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
import json,os,subprocess,sys,uuid
import pytest
from coredrp_ref.wal import WAL
from coredrp_ref.wire import *

def bind(w):
    w.bind(pb.ServerHello(protocol_major=1,protocol_minor=1,receiver_id=b'r'*16,receiver_database_epoch=b'd'*16,accepted_event_types=[1],contract_binding_digest=BINDING,committed_sequence=0,committed_chain_hash=w.hashes[0]))
def create(path,cap=100000):
    with WAL(path,uuid.uuid4().bytes,uuid.uuid4().bytes,cap) as w:bind(w)
def run_admit(path,point,key='k',tm=100):
    env=dict(os.environ,COREDRP_TEST_CRASH=point,PYTHONPATH='reference')
    return subprocess.run([sys.executable,'-m','coredrp_ref.cli','admit-checkpoint','--wal',str(path),'--caller-key',key,'--time',str(tm),'--through',str(tm-1)],env=env,capture_output=True)

@pytest.mark.parametrize('point,tail',[('before_wal_write',0),('after_wal_fsync',1),('after_anchor_fsync',1)])
def test_process_death_admission(tmp_path,point,tail):
    path=tmp_path/'wal';create(path)
    assert run_admit(path,point).returncode==-9
    with WAL(path) as w:
        assert w.state['tail']==tail
        assert w.admit_checkpoint('k',100,99)==1
        assert len(w.events)==1
        with pytest.raises(Failure,match='IDEMPOTENCY'):w.admit_checkpoint('k',101,99)

def test_spool_fence_and_no_backdating(tmp_path):
    path=tmp_path/'wal';create(path,cap=1)
    with WAL(path) as w:
        with pytest.raises(Failure,match='RESOURCE'):w.admit_checkpoint('a',100,99)
        with pytest.raises(Failure,match='STREAM_ALREADY_ACTIVE'):WAL(path)
        assert not w.events
    assert (path/'events.wal').stat().st_size==0

@pytest.mark.parametrize('where',['wal','anchor','tail'])
def test_corruption_fails_closed(tmp_path,where):
    path=tmp_path/'wal';create(path)
    with WAL(path) as w:w.admit_checkpoint('k',100,99)
    target=path/('anchor.json' if where=='anchor' else 'events.wal')
    b=target.read_bytes()
    if where=='tail':b=b[:-1]
    else:b=b[:20]+bytes([b[20]^1])+b[21:]
    target.write_bytes(b)
    with pytest.raises(Failure,match='WAL_CORRUPTION'):WAL(path)
    assert target.read_bytes()==b

def test_reconnect_guards(tmp_path):
    path=tmp_path/'wal';create(path)
    with WAL(path) as w:
        w.admit_checkpoint('k',100,99)
        h=pb.ServerHello(protocol_major=1,protocol_minor=1,receiver_id=b'r'*16,receiver_database_epoch=b'd'*16,accepted_event_types=[1],contract_binding_digest=BINDING,committed_sequence=1,committed_chain_hash=w.hashes[1])
        w.bind(h);assert w.state['ack']==1
        h.committed_sequence=0;h.committed_chain_hash=w.hashes[0]
        with pytest.raises(Failure,match='RECEIVER_ROLLBACK'):w.bind(h)
        h.receiver_id=b'x'*16
        with pytest.raises(Failure,match='RECEIVER_ID_CHANGED'):w.bind(h)
        with pytest.raises(Failure,match='CHECKPOINT_BACKDATED'):w.admit_checkpoint('late',99,98)

def test_identity_fence_across_cloned_paths(tmp_path):
    import shutil
    path=tmp_path/'wal';create(path);shutil.copytree(path,tmp_path/'clone')
    with WAL(path):
        with pytest.raises(Failure,match='STREAM_ALREADY_ACTIVE'):WAL(tmp_path/'clone')

def test_core_hash_matches_frozen_vectors():
    # Independently reconstruct a real checkpoint from the existing normative corpus.
    from pathlib import Path
    d=json.loads((Path(__file__).resolve().parents[2]/'docs/coredrp-v1-core-hash-vectors.json').read_text())
    checked=0
    for c in d['chains']:
        if c['lane_id']!=0:continue
        sender=uuid.UUID(c['sender_id']).bytes;epoch=uuid.UUID(c['log_epoch']).bytes
        prev=bytes.fromhex(c.get('synthetic_previous_chain_sha256',c['genesis_chain_sha256']))
        assert genesis(sender,epoch).hex()==c['genesis_chain_sha256']
        for x in c['events']:
            if int(x['event_type'],16)==1 and not x['scope_hex']:
                e=pb.Event(sequence=x['sequence'],event_type=1,event_time_unix_ms=x['event_time_unix_ms'],relay_event_id=uuid.UUID(x['relay_event_id']).bytes,payload=bytes.fromhex(x['payload_hex']))
                assert chain(prev,sender,epoch,e).hex()==x['chain_hash_sha256'];checked+=1
            prev=bytes.fromhex(x['chain_hash_sha256'])
    assert checked
