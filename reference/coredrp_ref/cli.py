# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
import argparse,asyncio,json,os,sys,uuid
from pathlib import Path
from .wire import Failure
from .wal import WAL
from .storage import bootstrap
from .transport import tls,serve
from .recovery import sync

def identifier(s):return uuid.UUID(s).bytes

def main():
    p=argparse.ArgumentParser(description='Experimental CoreDRP isolated reference lab')
    sub=p.add_subparsers(dest='action',required=True)
    init=sub.add_parser('bootstrap',help='idempotent privileged initial epoch approval; never replaces an existing epoch')
    for name in ('receiver','incarnation','sender','epoch'):init.add_argument('--'+name,required=True,type=identifier)
    init.add_argument('--admin-id',required=True,type=uuid.UUID)
    for action in ('serve','sync'):
        q=sub.add_parser(action)
        q.add_argument('--host',default='localhost');q.add_argument('--port',type=int,default=7443)
        for name in ('ca','cert','key'):q.add_argument('--'+name,required=True,type=Path)
        if action=='serve':q.add_argument('--ready',type=Path);q.add_argument('--test-paused',action='store_true')
        else:
            q.add_argument('--wal',required=True,type=Path);q.add_argument('--receiver',required=True,type=identifier)
            q.add_argument('--attempts',type=int,default=3);q.add_argument('--retry-delay',type=float,default=1);q.add_argument('--timeout',type=float,default=10)
    q=sub.add_parser('init-sender');q.add_argument('--wal',required=True,type=Path);q.add_argument('--sender',required=True,type=identifier);q.add_argument('--epoch',required=True,type=identifier);q.add_argument('--cap',type=int,default=1024*1024)
    q=sub.add_parser('admit-checkpoint');q.add_argument('--wal',required=True,type=Path);q.add_argument('--caller-key',required=True);q.add_argument('--time',required=True,type=int);q.add_argument('--through',required=True,type=int)
    q=sub.add_parser('inspect',help='verify sender WAL/anchor without repair or repinning');q.add_argument('--wal',required=True,type=Path)
    q=sub.add_parser('increase-cap',help='increase retained WAL capacity without deleting evidence');q.add_argument('--wal',required=True,type=Path);q.add_argument('--cap',required=True,type=int)
    a=p.parse_args()
    if a.action=='bootstrap':bootstrap(os.environ['COREDRP_REF_DSN'],a.receiver,a.incarnation,a.sender,a.epoch,a.admin_id)
    elif a.action=='serve':asyncio.run(serve(os.environ['COREDRP_REF_DSN'],a.host,a.port,tls(a.ca,a.cert,a.key,True),a.ready,a.test_paused))
    elif a.action=='init-sender':
        with WAL(a.wal,a.sender,a.epoch,a.cap):pass
    elif a.action=='admit-checkpoint':
        with WAL(a.wal) as w:print(json.dumps({'durable_sequence':w.admit_checkpoint(a.caller_key,a.time,a.through)}))
    elif a.action=='sync':
        ack=asyncio.run(sync(a.wal,a.host,a.port,tls(a.ca,a.cert,a.key),a.receiver,a.attempts,a.retry_delay,a.timeout))
        print(json.dumps({'remembered_ack':ack}))
    elif a.action=='increase-cap':
        with WAL(a.wal) as w:w.increase_cap(a.cap);print(json.dumps({'cap':w.state['cap']}))
    else:
        with WAL(a.wal) as w:print(json.dumps(w.state,sort_keys=True))

if __name__=='__main__':
    try:main()
    except Failure as e:print(e.code,file=sys.stderr);sys.exit(2)
    except OSError:print('LOCAL_IO_FAILURE',file=sys.stderr);sys.exit(2)
