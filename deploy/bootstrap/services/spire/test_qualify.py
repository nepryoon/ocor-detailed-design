#!/usr/bin/env python3
"""Unit tests for the fail-closed SPIRE provisioning qualifier."""

from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("qualify.py")
SPEC = importlib.util.spec_from_file_location("spire_qualify", MODULE_PATH)
assert SPEC and SPEC.loader
qualify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualify)


SERVER = "ghcr.io/spiffe/spire-server@sha256:" + "a" * 64
AGENT = "ghcr.io/spiffe/spire-agent@sha256:" + "b" * 64


class SpireQualifierTests(unittest.TestCase):
    def lock(self) -> dict:
        return {
            "services": [
                {"id": "spire-server", "image": SERVER, "version": "1.15.3", "source": "https://github.com/spiffe/spire/pkgs/container/spire-server", "license": "Apache-2.0", "official_source": True},
                {"id": "spire-agent", "image": AGENT, "version": "1.15.3", "source": "https://github.com/spiffe/spire/pkgs/container/spire-agent", "license": "Apache-2.0", "official_source": True},
            ]
        }

    def test_exact_pair_is_accepted(self) -> None:
        pair = qualify.validate_lock(self.lock())
        self.assertEqual({"spire-server", "spire-agent"}, set(pair))

    def test_mutable_image_is_rejected(self) -> None:
        lock = self.lock()
        lock["services"][1]["image"] = "ghcr.io/spiffe/spire-agent:latest"
        with self.assertRaises(qualify.QualificationError):
            qualify.validate_lock(lock)

    def test_duplicate_service_identity_is_rejected(self) -> None:
        lock = self.lock()
        lock["services"].append(dict(lock["services"][1]))
        with self.assertRaises(qualify.QualificationError):
            qualify.validate_lock(lock)

    def test_runtime_must_be_running_exact_and_unpublished(self) -> None:
        inspection = {
            "Config": {"Image": AGENT},
            "State": {"Running": True, "Paused": False},
            "HostConfig": {"SecurityOpt": ["no-new-privileges:true"]},
            "NetworkSettings": {"Ports": {}},
        }
        qualify.validate_inspection(inspection, AGENT, "spire-agent")
        inspection["NetworkSettings"]["Ports"] = {"8081/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8081"}]}
        with self.assertRaises(qualify.QualificationError):
            qualify.validate_inspection(inspection, AGENT, "spire-agent")

    def test_configs_are_closed_to_expected_trust_domain(self) -> None:
        qualify.validate_configs(
            'trust_domain = "ocor.test"\nsocket_path = "/run/spire/sockets/server.sock"\nbind_address = "0.0.0.0"\n',
            'trust_domain = "ocor.test"\nsocket_path = "/run/spire/sockets/agent.sock"\nserver_address = "spire-server"\n',
        )
        with self.assertRaises(qualify.QualificationError):
            qualify.validate_configs('trust_domain = "wrong"', 'trust_domain = "ocor.test"')
        with self.assertRaises(qualify.QualificationError):
            qualify.validate_configs(
                'trust_domain = "ocor.test"\ntrust_domain = "wrong"\nsocket_path = "/run/spire/sockets/server.sock"\nbind_address = "0.0.0.0"\n',
                'trust_domain = "ocor.test"\nsocket_path = "/run/spire/sockets/agent.sock"\nserver_address = "spire-server"\n',
            )

    def test_svid_identity_must_match_exactly(self) -> None:
        self.assertEqual(
            "spiffe://ocor.test/workload/ocor-dev-0077",
            qualify.validate_svid_output("SPIFFE ID: spiffe://ocor.test/workload/ocor-dev-0077"),
        )
        with self.assertRaises(qualify.QualificationError):
            qualify.validate_svid_output("SPIFFE ID: spiffe://other.test/workload/ocor-dev-0077")

    def test_every_mutation_requires_execute(self) -> None:
        for flag in ("recover_agent", "workload_svid", "fault", "invalid_token"):
            values = {name: False for name in ("recover_agent", "workload_svid", "fault", "invalid_token")}
            values[flag] = True
            with self.assertRaises(qualify.QualificationError):
                qualify.validate_mutation_flags(
                    SimpleNamespace(**values, execute=False, env_file=None)
                )
        qualify.validate_mutation_flags(
            SimpleNamespace(
                recover_agent=False,
                workload_svid=False,
                fault=False,
                invalid_token=False,
                execute=False,
                env_file=None,
            )
        )

    def test_cleanup_failure_is_fail_closed(self) -> None:
        failed = subprocess.CompletedProcess(["docker", "rm"], 1, "", "denied")
        present = subprocess.CompletedProcess(["docker", "inspect"], 0, "[]", "")
        with patch.object(qualify.subprocess, "run", side_effect=[failed, present]):
            with self.assertRaises(qualify.QualificationError):
                qualify.remove_container("test-container", allow_absent=False)

    def test_initial_cleanup_tolerates_only_confirmed_absence(self) -> None:
        failed = subprocess.CompletedProcess(["docker", "rm"], 1, "", "daemon unavailable")
        unknown = subprocess.CompletedProcess(["docker", "inspect"], 1, "", "daemon unavailable")
        with patch.object(qualify.subprocess, "run", side_effect=[failed, unknown]):
            with self.assertRaises(qualify.QualificationError):
                qualify.remove_container("test-container", allow_absent=True)


if __name__ == "__main__":
    unittest.main()
