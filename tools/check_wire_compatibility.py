#!/usr/bin/env python3
# Copyright 2026 Rob Cooke
# Originally designed and authored as part of CoreDRP by Rob Cooke.
# SPDX-License-Identifier: Apache-2.0
"""Reject changes to fields already present in the Draft 0.2 wire baseline."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "docs/coredrp-v1-wire-baseline.json").read_text(encoding="utf-8"))["files"]

COMMENT_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
FIELD_RE = re.compile(
    r"(?<![\w.])(?:(optional|repeated)\s+)?([\w.]+)\s+(\w+)\s*=\s*(\d+)\s*;"
)


def message_body(path: str, message: str) -> str:
    text = COMMENT_RE.sub("", (ROOT / path).read_text(encoding="utf-8"))
    match = re.search(r"\bmessage\s+" + re.escape(message) + r"\s*\{", text)
    if not match:
        return ""

    depth = 1
    index = match.end()
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1

    if depth != 0:
        raise ValueError(f"unterminated message {message} in {path}")
    return text[match.end() : index - 1]


def fields(path: str, message: str) -> dict[str, str]:
    body = message_body(path, message)
    result: dict[str, str] = {}
    for qualifier, field_type, name, number in FIELD_RE.findall(body):
        signature = (f"{qualifier} " if qualifier else "") + field_type + " " + name
        if number in result:
            raise ValueError(f"duplicate field number {number} in {path}:{message}")
        result[number] = signature
    return result


def main() -> int:
    for path, messages in BASELINE.items():
        for message, expected_fields in messages.items():
            current = fields(path, message)
            for number, signature in expected_fields.items():
                if current.get(number) != signature:
                    print(
                        f"wire breaking change {path}:{message} field {number}: "
                        f"expected {signature!r}, got {current.get(number)!r}",
                        file=sys.stderr,
                    )
                    return 1
    print("CoreDRP wire compatibility baseline: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"wire compatibility check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
