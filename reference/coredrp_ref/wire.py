# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
import hashlib,struct,uuid
from google.protobuf.message import DecodeError
from protocol import coredrp_v1_pb2 as pb
MAX_TIME=253402300799999
MAX_PAYLOAD=4096
MAX_BATCH=32
MAX_CHARGE=131072
# Core 1.1, lane 0, no profiles/scope contracts, checkpoint only.
BINDING=hashlib.sha256(b'CoreDRP1-CONTRACT'+struct.pack('>IIBHHHH',1,1,0,0,0,1,1)).digest()
class Failure(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)
def require(ok,code):
    if not ok:raise Failure(code)
def uid(raw):require(len(raw)==16 and any(raw),'INVALID_HANDSHAKE');return raw
def H(b):return hashlib.sha256(b).digest()
def genesis(sender,epoch):return H(b'CoreDRP1-GENESIS'+uid(sender)+uid(epoch)+b'\0')
def payload_hash(p):return H(b'CoreDRP1-PAYLOAD'+struct.pack('>I',len(p))+p)
def validate(e):
    require(1<=e.sequence<=2**63-1,'SEQUENCE_OUT_OF_RANGE')
    require(e.event_type<=65535,'EVENT_TYPE_OUT_OF_RANGE')
    require(e.event_type==1,'UNADVERTISED_EVENT_TYPE')
    require(e.scope==b'','INVALID_EVENT_PLACEMENT')
    require(len(e.payload)<=MAX_PAYLOAD,'EVENT_TOO_LARGE')
    require(len(e.relay_event_id)==16 and any(e.relay_event_id),'MALFORMED_FRAME')
    require(0<=e.event_time_unix_ms<=MAX_TIME,'MALFORMED_FRAME')
    p=pb.CompletenessCheckpoint()
    try:p.ParseFromString(e.payload)
    except DecodeError:raise Failure('SEMANTIC_PAYLOAD_INVALID') from None
    require(0<=p.complete_through_unix_ms<=e.event_time_unix_ms,'SEMANTIC_PAYLOAD_INVALID')
    return p.complete_through_unix_ms

def chain(previous,sender,epoch,e):
    validate(e)
    return H(b'CoreDRP1-EVENT'+previous+sender+epoch+b'\0'+struct.pack('>QH',e.sequence,e.event_type)+e.relay_event_id+struct.pack('>H',len(e.scope))+e.scope+struct.pack('>q',e.event_time_unix_ms)+payload_hash(e.payload))
def charge(e):return 32+len(e.scope)+len(e.payload)
def checkpoint(sequence,event_time,boundary):
    return pb.Event(sequence=sequence,event_type=1,event_time_unix_ms=event_time,relay_event_id=uuid.uuid4().bytes,payload=pb.CompletenessCheckpoint(complete_through_unix_ms=boundary).SerializeToString())
