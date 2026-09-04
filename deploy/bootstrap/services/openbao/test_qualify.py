#!/usr/bin/env python3
"""Unit contracts for the OpenBao-only provisioning qualifier."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("qualify.py")
SPEC = importlib.util.spec_from_file_location("openbao_qualify", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
qualify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualify)


def locked_service() -> dict[str, object]:
    return {
        "id": "openbao",
        "image": "quay.io/openbao/openbao@sha256:" + "a" * 64,
        "license": "MPL-2.0",
        "official_source": True,
        "source": "https://quay.io/repository/openbao/openbao",
        "version": "2.6.2",
    }


class OpenBaoQualificationContractTests(unittest.TestCase):
    def test_scope_is_exclusively_openbao(self) -> None:
        self.assertEqual("openbao", qualify.SERVICE)

    def test_exact_lock_is_accepted(self) -> None:
        self.assertEqual("2.6.2", qualify.validate_lock({"services": [locked_service()]})["version"])

    def test_mutable_or_unofficial_lock_is_rejected(self) -> None:
        service = locked_service()
        service["image"] = "quay.io/openbao/openbao:latest"
        with self.assertRaisesRegex(qualify.QualificationError, "digest-pinned"):
            qualify.validate_lock({"services": [service]})
        service = locked_service()
        service["official_source"] = False
        with self.assertRaisesRegex(qualify.QualificationError, "official"):
            qualify.validate_lock({"services": [service]})

    def test_external_binding_or_wrong_image_is_rejected(self) -> None:
        inspection = {
            "Config": {"Image": locked_service()["image"]},
            "HostConfig": {"SecurityOpt": ["no-new-privileges:true"]},
            "State": {"Running": True, "Paused": False, "Health": {"Status": "healthy"}},
            "NetworkSettings": {
                "Ports": {"8200/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8200"}]}
            },
        }
        with self.assertRaisesRegex(qualify.QualificationError, "loopback"):
            qualify.validate_inspection(inspection, str(locked_service()["image"]))
        inspection["NetworkSettings"]["Ports"]["8200/tcp"][0]["HostIp"] = "127.0.0.1"
        with self.assertRaisesRegex(qualify.QualificationError, "image"):
            qualify.validate_inspection(inspection, "quay.io/openbao/openbao@sha256:" + "b" * 64)

    def test_health_contract_is_exact_and_unsealed(self) -> None:
        result = qualify.validate_health(
            200,
            json.dumps(
                {
                    "initialized": True,
                    "sealed": False,
                    "standby": False,
                    "version": "2.6.2",
                }
            ),
            "2.6.2",
        )
        self.assertEqual("UNSEALED", result["seal_state"])

    def test_sealed_or_wrong_version_fails_closed(self) -> None:
        with self.assertRaisesRegex(qualify.QualificationError, "sealed"):
            qualify.validate_health(
                503,
                json.dumps({"initialized": True, "sealed": True, "version": "2.6.2"}),
                "2.6.2",
            )
        with self.assertRaisesRegex(qualify.QualificationError, "version"):
            qualify.validate_health(
                200,
                json.dumps(
                    {
                        "initialized": True,
                        "sealed": False,
                        "standby": False,
                        "version": "2.6.1",
                    }
                ),
                "2.6.2",
            )

    def test_auth_contract_requires_denial_and_authorized_success(self) -> None:
        result = qualify.validate_auth(
            invalid_status=403,
            invalid_body=json.dumps({"errors": ["permission denied"]}),
            authorized_status=200,
            authorized_body=json.dumps({"data": {"secret/": {"type": "kv"}}}),
        )
        self.assertEqual("FAIL_CLOSED", result["invalid_token"])
        with self.assertRaisesRegex(qualify.QualificationError, "invalid token"):
            qualify.validate_auth(
                invalid_status=200,
                invalid_body=json.dumps({"data": {}}),
                authorized_status=200,
                authorized_body=json.dumps({"data": {}}),
            )


if __name__ == "__main__":
    unittest.main()
