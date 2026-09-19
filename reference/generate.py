# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Generate into ignored build output; never alter the frozen protobuf sources."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1]
out=root/'.build/reference';out.mkdir(parents=True,exist_ok=True)
plugin=Path(sys.executable).parent/'protoc-gen-grpclib_python'
subprocess.run([sys.executable,'-m','grpc_tools.protoc','-I',str(root),f'--python_out={out}',f'--grpclib_python_out={out}',f'--plugin=protoc-gen-grpclib_python={plugin}',*[str(root/f) for f in ('protocol/coredrp-v1.proto','profiles/mining/coredrp-mining-v1.proto','profiles/miningcore/coredrp-miningcore-v1.proto')]],check=True)
