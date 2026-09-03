#!/usr/bin/env python3
"""Apply a bounded reversible fault to an ocor-bootstrap service."""

from __future__ import annotations

import argparse
import json
import sys

from ocor_bootstrap_lib import root, run


ALLOWED = {"terminusdb", "typedb", "fuseki", "opa", "keycloak", "openbao", "spire-server", "spire-agent"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=sorted(ALLOWED))
    parser.add_argument("fault", choices=("pause", "unpause", "restart", "disconnect", "reconnect"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repository = root()
    container = f"ocor-bootstrap-{args.service}-1"
    commands = {
        "pause": ["docker", "pause", container],
        "unpause": ["docker", "unpause", container],
        "restart": ["docker", "restart", "--time", "10", container],
        "disconnect": ["docker", "network", "disconnect", "ocor-bootstrap_ocor-bootstrap", container],
        "reconnect": ["docker", "network", "connect", "ocor-bootstrap_ocor-bootstrap", container],
    }
    if not args.execute:
        print(json.dumps({"status": "PASS", "mode": "DRY_RUN", "command": commands[args.fault]}, indent=2))
        return 0
    result = run(commands[args.fault], cwd=repository, timeout=30)
    print(json.dumps({"status": "PASS" if result.returncode == 0 else "ERROR", "stderr": result.stderr[-500:]}, indent=2))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
