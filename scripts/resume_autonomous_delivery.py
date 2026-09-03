#!/usr/bin/env python3
"""Preflight, optionally bootstrap, then resume the governed OCOR dispatcher."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from ocor_bootstrap_lib import root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repository = root()
    if args.execute:
        boot = subprocess.run([sys.executable, "scripts/bootstrap_development_environment.py", "--execute"], cwd=repository, check=False)
        if boot.returncode:
            return boot.returncode
    verify = subprocess.run([sys.executable, "scripts/verify_external_services.py", "--manifest-only"], cwd=repository, check=False)
    if verify.returncode:
        return verify.returncode
    command = [sys.executable, "scripts/ocor_autonomous_delivery.py", "--dry-run"]
    result = subprocess.run(command, cwd=repository, check=False)
    print(json.dumps({"status": "PASS" if result.returncode == 0 else "ERROR", "dispatcher": command}))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
