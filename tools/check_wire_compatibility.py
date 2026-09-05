#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parents[1]
B=json.loads((R/'docs/coredrp-v1-wire-fingerprints.json').read_text())
def git_blob_sha(b:bytes)->str:return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
failed=False
for path,expected in B.items():
 if path=='note':continue
 p=R/path
 if not p.exists():print('wire compatibility failure: missing',path,file=sys.stderr);failed=True;continue
 b=p.read_bytes();g=git_blob_sha(b);s=hashlib.sha256(b).hexdigest()
 if g!=expected['git_blob_sha1']:
  print(f'wire compatibility failure: {path} Git blob changed: expected {expected["git_blob_sha1"]}, got {g}',file=sys.stderr);failed=True
 if expected['sha256']=='PENDING':
  print(f'wire fingerprint pending: {path} sha256={s}',file=sys.stderr);failed=True
 elif s!=expected['sha256']:
  print(f'wire compatibility failure: {path} SHA-256 changed: expected {expected["sha256"]}, got {s}',file=sys.stderr);failed=True
if failed:raise SystemExit(1)
print('CoreDRP Draft 0.6 exact protobuf Git/SHA-256 fingerprints: OK')
