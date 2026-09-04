#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# Originally designed and authored as part of CoreDRP by Rob Cooke.
# SPDX-License-Identifier: Apache-2.0
"""Fail CI if the CoreDRP protobuf dependency direction is violated."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "protocol" / "coredrp-v1.proto"
MINING = ROOT / "profiles" / "mining" / "coredrp-mining-v1.proto"
MININGCORE = ROOT / "profiles" / "miningcore" / "coredrp-miningcore-v1.proto"

IMPORT_RE = re.compile(r'^\s*import\s+"([^"]+)"\s*;', re.MULTILINE)


def imports(path: Path) -> set[str]:
    return set(IMPORT_RE.findall(path.read_text(encoding="utf-8")))


def fail(message: str) -> None:
    print(f"layer-boundary failure: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    core_imports = imports(CORE)
    mining_imports = imports(MINING)
    miningcore_imports = imports(MININGCORE)

    if any(x.startswith("profiles/") for x in core_imports):
        fail(f"Core imports a profile: {sorted(core_imports)}")

    if any(x.startswith("profiles/miningcore/") for x in mining_imports):
        fail(f"Mining profile imports Miningcore: {sorted(mining_imports)}")

    allowed_mining = {"protocol/coredrp-v1.proto"}
    unexpected = mining_imports - allowed_mining
    if unexpected:
        fail(f"Mining profile has unexpected imports: {sorted(unexpected)}")

    allowed_miningcore = {
        "protocol/coredrp-v1.proto",
        "profiles/mining/coredrp-mining-v1.proto",
    }
    unexpected = miningcore_imports - allowed_miningcore
    if unexpected:
        fail(f"Miningcore profile has unexpected imports: {sorted(unexpected)}")

    core_text = CORE.read_text(encoding="utf-8")
    # Check schema identifiers only (comments are deliberately excluded).
    stripped = re.sub(r"//.*?$|/\*.*?\*/", "", core_text, flags=re.MULTILINE | re.DOTALL)
    pairs = re.findall(r"\b(?:message|enum|service|rpc)\s+(\w+)|\b(\w+)\s*=\s*\d+\s*;", stripped)
    identifiers = [value for pair in pairs for value in pair if value]

    def words(identifier: str) -> set[str]:
        # Split snake_case first, then CamelCase/acronym boundaries. Exact word
        # matching avoids false positives such as "spool" containing "pool".
        parts = []
        for chunk in identifier.replace("-", "_").split("_"):
            parts.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", chunk))
        return {part.lower() for part in parts}

    forbidden = {"pool", "miner", "share", "payout", "bitcoin", "coinbase", "hashrate", "postgres", "miningcore", "stratum"}
    hits = sorted({word for identifier in identifiers for word in words(identifier) if word in forbidden})
    if hits:
        fail(f"Core schema identifiers contain profile-specific terms: {hits}")

    print("CoreDRP layer boundaries: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
