"""Exit abruptly at a selected durability boundary for the C3 spike."""

from __future__ import annotations

import json
import os
import sys

from oracle import AtomicCommitOracle, CrashStage


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: crash_worker.py CRASH_STAGE")
    dsn = os.environ.get("OCOR_LIVE_POSTGRES_DSN")
    if not dsn:
        raise SystemExit("OCOR_LIVE_POSTGRES_DSN is required")
    command = json.load(sys.stdin)
    AtomicCommitOracle(dsn).commit(command, crash_stage=CrashStage(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
