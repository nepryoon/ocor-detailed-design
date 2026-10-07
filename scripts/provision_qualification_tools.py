#!/usr/bin/env python3
"""Acquire official checksum-pinned qualification tools in the worktree (DEC-211)."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def checked_digest(data: bytes, expected: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("official qualification tool checksum mismatch")


def fetch(url: str) -> bytes:
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                data: bytes = response.read(100_000_000)
                return data
        except (OSError, urllib.error.URLError):
            if attempt == 1:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")


def acquire(repository: Path) -> list[dict[str, str]]:
    lock = json.loads((repository / "infra/qualification_tools.lock.json").read_text())
    directory = repository / ".ocor/tools/bin"
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for item in lock["tools"]:
        official = fetch(item["checksum_source"]).decode().split()[0]
        if official != item["source_sha256"]:
            raise ValueError(f"official checksum differs from lock: {item['id']}")
        data = fetch(item["source"])
        checked_digest(data, official)
        if item["archive_member"]:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
                member = archive.getmember(item["archive_member"])
                if not member.isfile():
                    raise ValueError("qualification archive member is not a regular file")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("qualification archive member absent")
                data = stream.read()
        checked_digest(data, item["binary_sha256"])
        target = directory / item["id"]
        if target.is_symlink():
            raise ValueError("qualification tool target is a symlink")
        target.write_bytes(data)
        target.chmod(0o755)
        records.append({"id": item["id"], "version": item["version"], "binary_sha256": item["binary_sha256"], "source": item["source"]})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    if not args.execute:
        print(json.dumps({"status": "PASS", "mode": "CHECK_ONLY", "destination": ".ocor/tools/bin"}))
        return 0
    try:
        print(json.dumps({"status": "PASS", "tools": acquire(repository)}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
