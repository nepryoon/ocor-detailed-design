#!/usr/bin/env python3
"""Validate task evidence without converting absent or skipped work into PASS."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

NON_QUALIFYING = {"SKIPPED", "UNAVAILABLE", "NOT_EXECUTED", "XFAIL"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_zero_int(value: object, path: str) -> None:
    """Fail closed on a missing, non-integer or non-zero outcome field."""
    if type(value) is not int or value != 0:
        raise ValueError(f"{path} is not a valid zero: {value!r}")


def _validate_command(command: dict[str, object]) -> None:
    """Fail closed unless a command carries concrete numeric success evidence.

    The `status` label and the top-level `result` string are not trusted on their
    own: a command must back its PASS claim with either an exit_code of 0 or a
    result/counters object whose failure counters are all 0.
    """
    exit_code = command.get("exit_code")
    result = command.get("result")
    if result is not None and not isinstance(result, dict):
        raise ValueError(f"command result is not an object: {result!r}")
    has_numeric_evidence = exit_code is not None or isinstance(result, dict) or any(
        key in command for key in ("failed", "skipped", "not_executed", "xfailed")
    )
    if not has_numeric_evidence:
        raise ValueError("command has no numeric outcome evidence (exit_code or result)")
    if exit_code is not None:
        _require_zero_int(exit_code, "command exit_code")
    if isinstance(result, dict):
        for key in ("failed", "skipped", "not_executed"):
            if key in result:
                _require_zero_int(result[key], f"command result.{key}")
    for key in ("failed", "skipped", "not_executed", "xfailed"):
        if key in command:
            _require_zero_int(command[key], f"command {key}")


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
        for command in commands:
            if not isinstance(command, dict):
                raise ValueError(f"command entry is not an object: {command!r}")
            _validate_command(command)
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
