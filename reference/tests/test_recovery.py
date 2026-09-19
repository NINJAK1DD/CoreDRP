# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
import asyncio
import errno
import os
import subprocess
import sys
import pytest
from coredrp_ref import recovery
from coredrp_ref.wal import WAL
from coredrp_ref.wire import Failure
from test_wal import create

@pytest.mark.parametrize('point',['wal_write','wal_fsync','anchor_write','anchor_fsync','anchor_replace','anchor_directory_fsync'])
@pytest.mark.parametrize('code',['EIO','ENOSPC'])
def test_admission_io_failure_requires_recovery(tmp_path,monkeypatch,point,code):
    path=tmp_path/'wal';create(path)
    with WAL(path) as w:
        monkeypatch.setenv('COREDRP_TEST_IO',point);monkeypatch.setenv('COREDRP_TEST_ERRNO',code)
        with pytest.raises(Failure,match='WAL_IO_FAILURE'):w.admit_checkpoint('key',100,99)
        with pytest.raises(Failure,match='WAL_REOPEN_REQUIRED'):w.admit_checkpoint('key',100,99)
    monkeypatch.delenv('COREDRP_TEST_IO')
    with WAL(path) as w:
        assert w.admit_checkpoint('key',100,99)==1
        assert len(w.events)==1

@pytest.mark.parametrize('point',['anchor_write','anchor_fsync','anchor_replace','anchor_directory_fsync'])
def test_failed_ack_cannot_be_acknowledged_from_memory(tmp_path,monkeypatch,point):
    path=tmp_path/'wal';create(path)
    with WAL(path) as w:
        w.admit_checkpoint('key',100,99)
        monkeypatch.setenv('COREDRP_TEST_IO',point)
        with pytest.raises(Failure,match='WAL_IO_FAILURE'):w.acknowledge(1,w.hashes[1])
        with pytest.raises(Failure,match='WAL_REOPEN_REQUIRED'):w.acknowledge(1,w.hashes[1])
        with pytest.raises(Failure,match='WAL_REOPEN_REQUIRED'):w.hello()
    monkeypatch.delenv('COREDRP_TEST_IO')
    with WAL(path) as w:
        assert w.state['ack'] in (0,1)
        w.acknowledge(1,w.hashes[1])
    with WAL(path) as w:assert w.state['ack']==1


def test_recovered_suffix_is_synced_before_anchor(tmp_path,monkeypatch):
    path=tmp_path/'wal';create(path)
    anchor=(path/'anchor.json').read_bytes()
    with WAL(path) as w:
        monkeypatch.setenv('COREDRP_TEST_IO','wal_fsync')
        with pytest.raises(Failure):w.admit_checkpoint('key',100,99)
    monkeypatch.setenv('COREDRP_TEST_IO','recovery_fsync')
    with pytest.raises(OSError):WAL(path)
    assert (path/'anchor.json').read_bytes()==anchor
    monkeypatch.delenv('COREDRP_TEST_IO')
    with WAL(path) as w:assert w.admit_checkpoint('key',100,99)==1


def test_short_write_preserves_corrupt_evidence(tmp_path):
    path=tmp_path/'wal';create(path)
    with WAL(path) as w:
        original=w.file
        class Short:
            def __getattr__(self,key):return getattr(original,key)
            def write(self,data):return original.write(data[:len(data)//2])
        w.file=Short()
        with pytest.raises(Failure,match='WAL_IO_FAILURE'):w.admit_checkpoint('key',100,99)
    raw=(path/'events.wal').read_bytes()
    with pytest.raises(Failure,match='WAL_CORRUPTION'):WAL(path)
    assert (path/'events.wal').read_bytes()==raw


def test_operator_capacity_increase_retains_all_evidence(tmp_path):
    path=tmp_path/'wal';create(path,cap=1)
    with WAL(path) as w:
        with pytest.raises(Failure,match='RESOURCE_LIMIT'):w.admit_checkpoint('key',100,99)
    out=subprocess.run([sys.executable,'-m','coredrp_ref.cli','increase-cap','--wal',str(path),'--cap','10000'],capture_output=True,env=dict(os.environ,PYTHONPATH='reference'))
    assert out.returncode==0,out.stderr.decode()
    with WAL(path) as w:
        assert w.state['cap']==10000 and w.admit_checkpoint('key',100,99)==1
        with pytest.raises(Failure,match='INVALID_CAP'):w.increase_cap(9999)


@pytest.mark.parametrize('code',['WAL_IO_FAILURE','RECEIVER_ID_CHANGED','RECEIVER_INCARNATION_CHANGED','SPLIT_LOG','WAL_CORRUPTION'])
def test_permanent_failure_is_not_retried(tmp_path,monkeypatch,code):
    path=tmp_path/'wal';create(path);calls=[]
    async def fail(*args):calls.append(1);raise Failure(code)
    monkeypatch.setattr(recovery,'drain',fail)
    with pytest.raises(Failure,match=code):asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,3,0))
    assert len(calls)==1


def test_bounded_retry_reopens_wal(tmp_path,monkeypatch):
    path=tmp_path/'wal';create(path);handles=[]
    async def attempt(w,*args):
        handles.append(w)
        if len(handles)<3:raise ConnectionResetError()
    monkeypatch.setattr(recovery,'drain',attempt)
    assert asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,3,0))==0
    assert len({id(w) for w in handles})==3 and all(not w.healthy for w in handles)
    async def unavailable(*args):raise ConnectionRefusedError()
    monkeypatch.setattr(recovery,'drain',unavailable)
    with pytest.raises(Failure,match='RECOVERY_RETRY_EXHAUSTED'):asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,2,0))


def registry_retryable_codes():
    from pathlib import Path
    rows=(Path(__file__).resolve().parents[2]/'docs/coredrp-v1-errors.md').read_text().splitlines()
    return {line.split('|')[2].strip() for line in rows if '| STREAM_RETRYABLE |' in line}


@pytest.mark.parametrize('code',sorted(registry_retryable_codes()))
def test_every_registry_retryable_code_recovers_and_is_bounded(tmp_path,monkeypatch,code):
    from coredrp_ref.transport import error,RETRYABLE_CODES
    from coredrp_ref.wire import pb
    assert RETRYABLE_CODES==registry_retryable_codes()
    assert error(code).error.disposition==pb.ERROR_DISPOSITION_STREAM_RETRYABLE
    path=tmp_path/'wal';create(path);calls=[]
    async def transient(*args):
        calls.append(1)
        if len(calls)<3:raise Failure(code)
    monkeypatch.setattr(recovery,'drain',transient)
    assert asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,3,0))==0
    assert len(calls)==3
    calls.clear()
    with pytest.raises(Failure,match='RECOVERY_RETRY_EXHAUSTED'):asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,2,0))
    assert len(calls)==2


@pytest.mark.parametrize('err',[errno.ENETUNREACH,errno.EHOSTUNREACH,errno.ENETDOWN,errno.EHOSTDOWN,errno.ETIMEDOUT,'dns'])
def test_network_os_errors_retry_then_recover(tmp_path,monkeypatch,err):
    import socket
    path=tmp_path/'wal';create(path);calls=[]
    async def transient(*args):
        calls.append(1)
        if len(calls)<3:
            if err=='dns':raise socket.gaierror(socket.EAI_AGAIN,'temporary DNS failure')
            raise OSError(err,'network unavailable')
    monkeypatch.setattr(recovery,'drain',transient)
    assert asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,3,0))==0
    assert len(calls)==3
    calls.clear()
    with pytest.raises(Failure,match='RECOVERY_RETRY_EXHAUSTED'):asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,2,0))
    assert len(calls)==2


@pytest.mark.parametrize('kind',['tls','permanent_dns','disk_full','disk_io'])
def test_non_network_os_errors_do_not_retry(tmp_path,monkeypatch,kind):
    import socket,ssl
    path=tmp_path/'wal';create(path);calls=[]
    async def fail(*args):
        calls.append(1)
        if kind=='tls':raise ssl.SSLError('certificate rejected')
        if kind=='permanent_dns':raise socket.gaierror(socket.EAI_NONAME,'unknown hostname')
        raise OSError(errno.ENOSPC if kind=='disk_full' else errno.EIO,'storage failure')
    monkeypatch.setattr(recovery,'drain',fail)
    with pytest.raises(Failure if kind=='tls' else OSError):asyncio.run(recovery.sync(path,'localhost',1,None,b'r'*16,3,0))
    assert len(calls)==1


def test_wal_open_io_failure_stays_outside_network_retry(tmp_path,monkeypatch):
    calls=[]
    def fail(*args):calls.append(1);raise OSError(errno.EIO,'storage failure')
    monkeypatch.setattr(recovery,'WAL',fail)
    with pytest.raises(OSError):asyncio.run(recovery.sync(tmp_path/'wal','localhost',1,None,b'r'*16,3,0))
    assert len(calls)==1
