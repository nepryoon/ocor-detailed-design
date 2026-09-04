"""Contract tests for the OCOR-DEV-0076 security-service qualifier."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("qualify_security_services.py")
SPEC = importlib.util.spec_from_file_location("qualify_security_services", MODULE_PATH)
assert SPEC and SPEC.loader
qualifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualifier)


def fixture():
    images = {
        "opa": "openpolicyagent/opa@sha256:" + "1" * 64,
        "keycloak": "quay.io/keycloak/keycloak@sha256:" + "2" * 64,
    }
    lock = {
        "services": [
            {"id": name, "image": image, "version": "1"}
            for name, image in images.items()
        ]
    }
    containers = {
        name: {
            "image": image,
            "running": True,
            "paused": False,
            "health": "healthy",
            "host_ips": ["127.0.0.1"],
        }
        for name, image in images.items()
    }
    api = {
        "opa": {"health": {}, "data": {"result": {}}},
        "keycloak": {
            "issuer": "http://127.0.0.1:8080/realms/master",
            "authorization_endpoint": "http://127.0.0.1:8080/realms/master/protocol/openid-connect/auth",
            "token_endpoint": "http://127.0.0.1:8080/realms/master/protocol/openid-connect/token",
        },
    }
    return lock, containers, api


class SecurityServiceContractTests(unittest.TestCase):
    def test_positive_real_service_contract_shape(self):
        lock, containers, api = fixture()
        self.assertEqual([], qualifier.validate_lock(lock))
        self.assertEqual(("opa", "keycloak"), qualifier.REQUIRED_SERVICES)
        self.assertEqual([], qualifier.evaluate(containers, api, lock))

    def test_mutable_or_missing_lock_entry_fails(self):
        lock, _, _ = fixture()
        lock["services"][0]["image"] = "openpolicyagent/opa:latest"
        lock["services"].pop()
        errors = qualifier.validate_lock(lock)
        self.assertTrue(any("missing" in error for error in errors))
        self.assertTrue(any("digest" in error for error in errors))

    def test_unhealthy_paused_or_externally_exposed_container_fails(self):
        lock, containers, api = fixture()
        containers["opa"]["health"] = "unhealthy"
        containers["keycloak"]["paused"] = True
        containers["opa"]["host_ips"] = ["0.0.0.0"]
        errors = qualifier.evaluate(containers, api, lock)
        self.assertTrue(any("opa" in error and "health" in error for error in errors))
        self.assertTrue(any("keycloak" in error and "paused" in error for error in errors))
        self.assertTrue(any("opa" in error and "exposure" in error for error in errors))

    def test_wrong_image_or_policy_api_fails(self):
        lock, containers, api = fixture()
        containers["opa"]["image"] = "openpolicyagent/opa@sha256:" + "9" * 64
        api["opa"]["data"] = {"unexpected": True}
        errors = qualifier.evaluate(containers, api, lock)
        self.assertTrue(any("image" in error for error in errors))
        self.assertTrue(any("OPA data API" in error for error in errors))

    def test_wrong_oidc_identity_fails(self):
        lock, containers, api = fixture()
        api["keycloak"]["issuer"] = "https://external.invalid/realms/master"
        errors = qualifier.evaluate(containers, api, lock)
        self.assertTrue(any("issuer" in error for error in errors))

    def test_each_security_service_fault_fails_closed(self):
        for service in qualifier.REQUIRED_SERVICES:
            with self.subTest(service=service):
                lock, containers, api = fixture()
                containers[service]["running"] = False
                self.assertTrue(qualifier.evaluate(containers, api, lock))


if __name__ == "__main__":
    unittest.main()
