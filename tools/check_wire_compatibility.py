#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Reject any protobuf edit not explicitly reviewed into the Draft 0.5 fingerprint set."""
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parents[1]
B=json.loads((R/'docs/coredrp-v1-wire-fingerprints.json').read_text(encoding='utf-8'))
def git_blob_sha(b:bytes)->str:
 return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
for path,expected in B.items():
 if path=='note':continue
 p=R/path
 if not p.exists():print('wire compatibility failure: missing',path,file=sys.stderr);raise SystemExit(1)
 got=git_blob_sha(p.read_bytes())
 if got!=expected:
  print(f'wire compatibility failure: {path} changed: expected reviewed blob {expected}, got {got}',file=sys.stderr);raise SystemExit(1)
print('CoreDRP Draft 0.5 exact protobuf wire fingerprints: OK')
