#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# Originally designed and authored as part of CoreDRP by Rob Cooke.
# SPDX-License-Identifier: Apache-2.0
"""Verify the CoreDRP/1 draft core hashing test vectors."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "docs" / "coredrp-v1-test-vectors.json"


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def u16(n: int) -> bytes:
    return struct.pack(">H", n)


def u32(n: int) -> bytes:
    return struct.pack(">I", n)


def u64(n: int) -> bytes:
    return struct.pack(">Q", n)


def i64(n: int) -> bytes:
    return struct.pack(">q", n)


def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    tags = data["domain_tags_ascii"]
    payload_domain = tags["payload"].encode("ascii")
    event_domain = tags["event"].encode("ascii")
    genesis_domain = tags["genesis"].encode("ascii")

    sender = uuid.UUID(data["sender_id"]).bytes
    epoch = uuid.UUID(data["log_epoch"]).bytes
    lane = int(data["lane_id"])
    if not 0 <= lane <= 255:
        raise ValueError("lane_id outside uint8 range")

    expected_sender = bytes.fromhex(data["sender_id_rfc4122_bytes_hex"])
    expected_epoch = bytes.fromhex(data["log_epoch_rfc4122_bytes_hex"])
    assert sender == expected_sender, "sender UUID byte-order vector mismatch"
    assert epoch == expected_epoch, "epoch UUID byte-order vector mismatch"

    chain = sha256(genesis_domain + sender + epoch + bytes([lane]))
    assert chain.hex() == data["genesis_chain_sha256"], "genesis chain mismatch"

    for event in data["events"]:
        sequence = int(event["sequence"])
        event_type = int(event["event_type"], 16)
        scope = bytes.fromhex(event["scope_hex"])
        event_time = int(event["event_time_unix_ms"])
        payload = bytes.fromhex(event["payload_hex"])

        payload_hash = sha256(payload_domain + u32(len(payload)) + payload)
        assert payload_hash.hex() == event["payload_hash_sha256"], (
            f"payload hash mismatch at sequence {sequence}"
        )

        chain = sha256(
            event_domain
            + chain
            + sender
            + epoch
            + bytes([lane])
            + u64(sequence)
            + u16(event_type)
            + u16(len(scope))
            + scope
            + i64(event_time)
            + payload_hash
        )
        assert chain.hex() == event["chain_hash_sha256"], (
            f"chain hash mismatch at sequence {sequence}"
        )

    assert chain.hex() == data["batch_terminal_chain_hash_sha256"], (
        "batch terminal chain mismatch"
    )
    print("CoreDRP/1 test vectors: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError, KeyError) as exc:
        print(f"CoreDRP/1 test-vector verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
