# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Bounded reconnects; each attempt reopens and verifies durable sender state."""
import asyncio
import ssl
from grpclib.const import Status
from grpclib.exceptions import GRPCError, StreamTerminatedError
from .wire import Failure, require
from .wal import WAL
from .transport import drain

async def sync(path,host,port,context,receiver,attempts=3,delay=1,timeout=10):
    require(type(attempts) is int and 1<=attempts<=100,'INVALID_RETRY_POLICY')
    require(0<=delay<=60 and 0<timeout<=300,'INVALID_RETRY_POLICY')
    for attempt in range(attempts):
        # Storage/corruption/fencing failures are outside the network retry block.
        with WAL(path) as wal:
            try:
                await drain(wal,host,port,context,receiver,timeout)
                return wal.state['ack']
            except Failure as error:
                if error.code not in {'RECEIVER_DURABILITY_UNAVAILABLE','STREAM_ALREADY_ACTIVE'}:raise
            except ssl.SSLError:
                raise Failure('TLS_AUTHENTICATION_FAILED') from None
            except GRPCError as error:
                if error.status not in {Status.UNAVAILABLE,Status.DEADLINE_EXCEEDED}:raise Failure('REMOTE_PROTOCOL_FAILURE') from None
            except (ConnectionError,TimeoutError,StreamTerminatedError):pass
        if attempt+1<attempts:await asyncio.sleep(delay)
    raise Failure('RECOVERY_RETRY_EXHAUSTED')
