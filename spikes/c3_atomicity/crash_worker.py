"""Exit abruptly at a selected durability boundary for the C3 spike."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from oracle import AtomicCommitOracle, CrashStage


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: crash_worker.py DATABASE CRASH_STAGE")
    command = json.load(sys.stdin)
    AtomicCommitOracle(Path(sys.argv[1])).commit(
        command, crash_stage=CrashStage(sys.argv[2])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
