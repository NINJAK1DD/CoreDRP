# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Real PostgreSQL + separate TLS/gRPC receiver/sender processes. Never mocked.

Required env COREDRP_REF_DSN points to a disposable coredrp_ref_* database.
No skip fallback: collecting this suite without the lab fails explicitly.
"""
import asyncio,datetime,os,socket,ssl,subprocess,sys,time,uuid
from pathlib import Path
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from coredrp_ref.wal import WAL
from coredrp_ref.wire import *
from coredrp_ref.storage import bootstrap,connect,Session
from coredrp_ref.transport import tls,drain,peer_id
R=b'r'*16;I=b'i'*16

@pytest.fixture
def lab(tmp_path):
    dsn=os.environ.get('COREDRP_REF_DSN')
    assert dsn,'COREDRP_REF_DSN is required; use the isolated PostgreSQL CI service'
    sender=uuid.uuid4().bytes;epoch=uuid.uuid4().bytes
    bootstrap(dsn,R,I,sender,epoch,uuid.uuid4())
    ca_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    now=datetime.datetime.now(datetime.timezone.utc)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'CoreDRP test CA')])
    ca=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True,path_length=0),True).sign(ca_key,hashes.SHA256())
    (tmp_path/'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    for who,identity in [('receiver',R),('sender',sender)]:
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cert=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,who)])).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.UniformResourceIdentifier('urn:coredrp:'+who+':'+str(uuid.UUID(bytes=identity)))]),False).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if who=='receiver' else ExtendedKeyUsageOID.CLIENT_AUTH]),False).sign(ca_key,hashes.SHA256())
        (tmp_path/(who+'.pem')).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        path=tmp_path/(who+'.key');path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));path.chmod(0o600)
    with WAL(tmp_path/'wal',sender,epoch):pass
    processes=[]
    def cmd(*args,crash=None):
        env=dict(os.environ,PYTHONPATH='reference')
        env.pop('COREDRP_TEST_CRASH',None)
        if crash:env['COREDRP_TEST_CRASH']=crash
        return subprocess.run([sys.executable,'-m','coredrp_ref.cli',*map(str,args)],env=env,capture_output=True,timeout=15)
    def certargs(who):return ['--ca',tmp_path/'ca.pem','--cert',tmp_path/(who+'.pem'),'--key',tmp_path/(who+'.key')]
    def start(crash=None,paused=False):
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        ready=tmp_path/('ready-'+str(port));env=dict(os.environ,PYTHONPATH='reference')
        env.pop('COREDRP_TEST_CRASH',None)
        if crash:env['COREDRP_TEST_CRASH']=crash
        log=open(tmp_path/('receiver-'+str(port)+'.log'),'wb')
        p=subprocess.Popen([sys.executable,'-m','coredrp_ref.cli','serve','--port',str(port),'--ready',str(ready),*map(str,certargs('receiver')),*(['--test-paused'] if paused else [])],env=env,stdout=log,stderr=log)
        log.close();processes.append(p)
        deadline=time.monotonic()+10
        while not ready.exists():
            assert p.poll() is None,(tmp_path/('receiver-'+str(port)+'.log')).read_text()
            assert time.monotonic()<deadline,'receiver startup timed out'
            time.sleep(.02)
        return p,port
    def sync(port,crash=None):return cmd('sync','--wal',tmp_path/'wal','--receiver',str(uuid.UUID(bytes=R)),'--port',port,*certargs('sender'),crash=crash)
    def counts():
        with connect(dsn) as db:
            return tuple(db.execute('SELECT count(*) FROM coredrp_ref.'+t+' WHERE sender=%s',(sender,)).fetchone()[0] for t in ('events','effects'))
    # Negotiate and persist approval/binding before any local admission.
    p,port=start();out=sync(port);assert out.returncode==0,out.stderr.decode();p.kill();p.wait()
    yield dict(path=tmp_path,dsn=dsn,sender=sender,epoch=epoch,start=start,sync=sync,counts=counts,cmd=cmd,certargs=certargs)
    for p in processes:
        if p.poll() is None:p.kill()
        p.wait(timeout=5)

@pytest.mark.parametrize('point,side,committed,acked',[
 ('before_receiver_commit','receiver',0,0),
 ('after_receiver_commit','receiver',1,0),
 ('before_ack_persist','sender',1,0),
 ('after_ack_persist','sender',1,1)])
def test_kill_boundary_then_restart_both(lab,point,side,committed,acked):
    path=lab['path']/'wal'
    with WAL(path) as w:w.admit_checkpoint('event-1',100,99);original=w.events[0].SerializeToString()
    p,port=lab['start'](crash=point if side=='receiver' else None)
    out=lab['sync'](port,crash=point if side=='sender' else None)
    assert out.returncode!=0
    if side=='receiver':assert p.wait(timeout=5)==-9
    else:assert out.returncode==-9;p.kill();p.wait()
    assert lab['counts']()==(committed,committed)
    with WAL(path) as w:assert w.state['ack']==acked
    p,port=lab['start']();out=lab['sync'](port);assert out.returncode==0,out.stderr.decode()
    assert lab['counts']()==(1,1)
    with WAL(path) as w:
        assert w.state['ack']==w.state['tail']==1
        assert w.events[0].SerializeToString()==original
    # Repeated reconnect/recovery has no additional application effect.
    assert lab['sync'](port).returncode==0;assert lab['counts']()==(1,1)

def test_atomic_batch_replay_fencing_and_zero_window(lab):
    with WAL(lab['path']/'wal') as w:
        for i in range(3):w.admit_checkpoint(str(i),100+i,99+i)
        s=Session(lab['dsn'],w.hello())
        try:
            with pytest.raises(Failure,match='STREAM_ALREADY_ACTIVE'):Session(lab['dsn'],w.hello())
            b=pb.EventBatch(first_sequence=1,events=w.events,terminal_chain_hash=w.hashes[-1])
            with pytest.raises(Failure,match='RESOURCE'):s.ingest(b,0,0)
            assert lab['counts']()==(0,0)
            bad=pb.EventBatch();bad.CopyFrom(b);bad.terminal_chain_hash=b'x'*32
            with pytest.raises(Failure,match='CHAIN_MISMATCH'):s.ingest(bad)
            assert lab['counts']()==(0,0)
            bad.CopyFrom(b);bad.events[1].event_time_unix_ms=50
            bad.events[1].payload=pb.CompletenessCheckpoint(complete_through_unix_ms=49).SerializeToString()
            previous=w.hashes[0]
            for e in bad.events:previous=chain(previous,w.sender,w.epoch,e)
            bad.terminal_chain_hash=previous
            with pytest.raises(Failure,match='CHECKPOINT_BACKDATED'):s.ingest(bad)
            assert lab['counts']()==(0,0) # first effect in the failed transaction rolled back
            s.ingest(b);s.ingest(b);assert lab['counts']()==(3,3)
            # Rehashed altered replay cannot substitute an original immutable event.
            bad.CopyFrom(b);bad.events[0].relay_event_id=b'z'*16
            previous=w.hashes[0]
            for e in bad.events:previous=chain(previous,w.sender,w.epoch,e)
            bad.terminal_chain_hash=previous
            with pytest.raises(Failure,match='EVENT_IDENTITY_MISMATCH'):s.ingest(bad)
            assert lab['counts']()==(3,3)
        finally:s.close()

def test_zero_window_control_exchange_then_drain(lab):
    with WAL(lab['path']/'wal') as w:
        for i in range(40):w.admit_checkpoint(str(i),100+i,99+i)
    p,port=lab['start'](paused=True)
    out=lab['sync'](port);assert out.returncode==0,out.stderr.decode()
    assert lab['counts']()==(40,40)

def test_tls12_and_missing_client_certificate_rejected(lab):
    p,port=lab['start']()
    for version,client_cert in [(ssl.TLSVersion.TLSv1_2,True),(ssl.TLSVersion.TLSv1_3,False)]:
        context=ssl.create_default_context(cafile=str(lab['path']/'ca.pem'))
        context.minimum_version=context.maximum_version=version
        if client_cert:context.load_cert_chain(lab['path']/'sender.pem',lab['path']/'sender.key')
        with pytest.raises((ssl.SSLError,ConnectionError,OSError)):
            with socket.create_connection(('localhost',port),timeout=2) as sock:
                with context.wrap_socket(sock,server_hostname='localhost') as wrapped:
                    # TLS1.3 may surface the mandatory client-certificate alert on read.
                    wrapped.sendall(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n');wrapped.recv(1024)
    assert lab['counts']()==(0,0)

def test_wrong_receiver_identity_stops_before_admission(lab):
    p,port=lab['start']()
    out=lab['cmd']('sync','--wal',lab['path']/'wal','--receiver',str(uuid.uuid4()),'--port',port,*lab['certargs']('sender'))
    assert out.returncode==2 and b'RECEIVER_ID_CHANGED' in out.stderr
    assert lab['counts']()==(0,0)

def test_admin_bootstrap_is_idempotent_and_cannot_replace(lab):
    admin=uuid.uuid4();sender=uuid.uuid4().bytes;epoch=uuid.uuid4().bytes
    bootstrap(lab['dsn'],R,I,sender,epoch,admin);bootstrap(lab['dsn'],R,I,sender,epoch,admin)
    with pytest.raises(Failure,match='IDEMPOTENCY_KEY_CONFLICT'):bootstrap(lab['dsn'],R,I,sender,uuid.uuid4().bytes,admin)
    with pytest.raises(Failure,match='ADMIN_ACTION_CONFLICT'):bootstrap(lab['dsn'],R,I,sender,uuid.uuid4().bytes,uuid.uuid4())


def test_isolated_shadow_comparison_and_missing_evidence(lab):
    from coredrp_ref.shadow import compare,fixture
    case,baseline,evidence=fixture(lab['dsn'])
    report=compare(lab['dsn'],case,baseline,evidence)
    assert report['eligible'] and report['shadow_only'] and not report['differences']
    for key,value in [('policy_staged',False),('membership_from',1),('clock','UNKNOWN'),('checkpoint',5001),('uncertainties',['RESOLVED_WAIVED'])]:
        result=compare(lab['dsn'],case,baseline,dict(evidence,**{key:value}))
        assert not result['eligible'] and result['blocked_reasons']
    result=compare(lab['dsn'],case,dict(baseline,miner2='0.44'),evidence)
    assert not result['eligible'] and result['differences'][0]['miner']=='miner2'


def test_wrong_authenticated_sender_identity(lab):
    from grpclib.client import Channel
    from protocol.coredrp_v1_grpc import DurableRelayStub
    p,port=lab['start']()
    async def attempt():
        context=tls(lab['path']/'ca.pem',lab['path']/'sender.pem',lab['path']/'sender.key')
        with WAL(lab['path']/'wal') as w:h=w.hello()
        h.sender_id=uuid.uuid4().bytes
        async with Channel('localhost',port,ssl=context) as channel:
            async with DurableRelayStub(channel).Stream.open(timeout=3) as stream:
                await stream.send_message(pb.ClientFrame(hello=h),end=True)
                frame=await stream.recv_message()
                assert frame.WhichOneof('body')=='error' and frame.error.code==pb.UNAUTHORIZED_SENDER
    asyncio.run(attempt());assert lab['counts']()==(0,0)
