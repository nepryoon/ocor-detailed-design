#!/usr/bin/env python3
"""Reset only the disposable ocor-bootstrap Compose environment."""

from __future__ import annotations

import argparse
import json
import sys

from ocor_bootstrap_lib import root, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="confirm removal of project containers and volumes")
    args = parser.parse_args()
    repository = root()
    env_file = repository / ".ocor" / "bootstrap.env"
    command = ["docker", "compose"]
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(["-p", "ocor-bootstrap", "-f", "deploy/bootstrap/compose.yaml", "down", "--volumes", "--remove-orphans"])
    if not args.execute:
        print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "command": command}, indent=2))
        return 0
    result = run(command, cwd=repository, timeout=180)
    print(json.dumps({"status": "PASS" if result.returncode == 0 else "ERROR", "stderr": result.stderr[-1000:]}, indent=2))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
