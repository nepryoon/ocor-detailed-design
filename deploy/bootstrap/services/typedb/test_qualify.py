#!/usr/bin/env python3
"""Unit contract tests for the TypeDB provisioning qualification harness."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("qualify.py")
SPEC = importlib.util.spec_from_file_location("typedb_qualify", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
qualify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualify)


class TypeDBQualificationContractTests(unittest.TestCase):
    def test_lock_contract_accepts_exact_digest_and_version(self) -> None:
        lock = {
            "services": [
                {
                    "id": "typedb",
                    "image": "typedb/typedb@sha256:" + "a" * 64,
                    "version": "3.12.3",
                    "official_source": True,
                    "source": "https://hub.docker.com/r/typedb/typedb",
                    "license": "MPL-2.0",
                }
            ]
        }
        entry = qualify.validate_lock(lock)
        self.assertEqual(entry["version"], "3.12.3")

    def test_lock_contract_rejects_mutable_image(self) -> None:
        lock = {
            "services": [
                {
                    "id": "typedb",
                    "image": "typedb/typedb:3.12.3",
                    "version": "3.12.3",
                    "official_source": True,
                    "source": "https://hub.docker.com/r/typedb/typedb",
                    "license": "MPL-2.0",
                }
            ]
        }
        with self.assertRaisesRegex(qualify.QualificationError, "digest-pinned"):
            qualify.validate_lock(lock)

    def test_runtime_contract_rejects_external_binding(self) -> None:
        inspection = {
            "Config": {"Image": "typedb/typedb@sha256:" + "a" * 64},
            "State": {"Running": True, "Health": {"Status": "healthy"}},
            "NetworkSettings": {
                "Ports": {"1729/tcp": [{"HostIp": "0.0.0.0", "HostPort": "1729"}]}
            },
        }
        with self.assertRaisesRegex(qualify.QualificationError, "loopback"):
            qualify.validate_inspection(inspection, inspection["Config"]["Image"])

    def test_http_contract_requires_exact_version_and_auth_failure(self) -> None:
        observed = qualify.validate_http_observations(
            health_status=204,
            version_status=200,
            version_body=json.dumps({"distribution": "TypeDB CE", "version": "3.12.3"}),
            unauth_status=401,
            unauth_body=json.dumps({"code": "AUT2", "message": "Missing token"}),
            expected_version="3.12.3",
        )
        self.assertEqual(observed["unauthenticated_database_access"], "FAIL_CLOSED")

    def test_http_contract_rejects_wrong_version(self) -> None:
        with self.assertRaisesRegex(qualify.QualificationError, "version"):
            qualify.validate_http_observations(
                health_status=204,
                version_status=200,
                version_body=json.dumps({"distribution": "TypeDB CE", "version": "3.12.2"}),
                unauth_status=401,
                unauth_body=json.dumps({"code": "AUT2"}),
                expected_version="3.12.3",
            )


if __name__ == "__main__":
    unittest.main()
