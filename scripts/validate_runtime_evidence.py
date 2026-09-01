#!/usr/bin/env python3
"""Validate task evidence without converting absent or skipped work into PASS."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence


NON_QUALIFYING = {"SKIPPED", "UNAVAILABLE", "NOT_EXECUTED", "XFAIL"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--non-skipped", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        entries = manifest.get("artifacts", [])
        evidence = next((item for item in entries if item.get("task_id") == args.task), None)
        if evidence is None:
            raise ValueError(f"manifest has no evidence entry for {args.task}")
        evidence_path = args.manifest.parent / evidence["path"]
        record = json.loads(evidence_path.read_text(encoding="utf-8"))
        if record.get("task_id") != args.task:
            raise ValueError("task identifier mismatch")
        if evidence.get("sha256") != digest(evidence_path):
            raise ValueError("evidence digest mismatch")
        raw_entry = next(
            (
                item
                for item in entries
                if item.get("task_id") == f"{args.task}-RAW"
            ),
            None,
        )
        if raw_entry is None:
            raise ValueError("manifest has no raw evidence entry")
        raw_path = args.manifest.parent / raw_entry["path"]
        raw_digest = digest(raw_path)
        if raw_entry.get("sha256") != raw_digest:
            raise ValueError("raw manifest digest mismatch")
        commands = record.get("commands", [])
        if not commands:
            raise ValueError("evidence has no executed command")
        statuses = {str(item.get("status", "")).upper() for item in commands}
        if args.non_skipped and statuses & NON_QUALIFYING:
            raise ValueError(f"non-qualifying result present: {sorted(statuses & NON_QUALIFYING)}")
        if statuses != {"PASS"} or record.get("result") != "PASS":
            raise ValueError(f"mandatory evidence is not all PASS: {sorted(statuses)}")
        if record.get("raw_output_sha256") != raw_digest:
            raise ValueError("record raw-output digest mismatch")
        required = {"commit", "environment", "raw_output_sha256", "created_at"}
        missing = sorted(required - record.keys())
        if missing:
            raise ValueError(f"evidence fields missing: {', '.join(missing)}")
        print(f"PASS: qualifying task evidence for {args.task}")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
