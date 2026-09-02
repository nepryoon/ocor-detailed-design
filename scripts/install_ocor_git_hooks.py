#!/usr/bin/env python3
"""Install repository-local OCOR hooks as defence in depth."""

from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    hook = root / ".githooks/pre-push"
    if not hook.is_file():
        raise SystemExit("OCOR pre-push hook is missing")
    hook.chmod(0o755)
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)
    print("OCOR repository-local hooks installed; GitHub server-side protection is not implied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
