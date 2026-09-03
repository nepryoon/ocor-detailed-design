#!/usr/bin/env python3
"""Negative conformance tests for DEC-211 bootstrap lock validation."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from ocor_bootstrap_lib import canonical_json, validate_locks  # noqa: E402
from preflight_environment import validate_tool  # noqa: E402


def load(name: str) -> dict:
    return json.loads((ROOT / f"infra/{name}.lock.json").read_text(encoding="utf-8"))


def schema(name: str) -> Draft202012Validator:
    value = json.loads((ROOT / f"infra/{name}.lock.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return Draft202012Validator(value, format_checker=FormatChecker())


class BootstrapLockValidationTests(unittest.TestCase):
    def test_current_locks_are_schema_valid_and_canonical(self) -> None:
        for name in ("toolchain", "services"):
            value = load(name)
            self.assertEqual([], list(schema(name).iter_errors(value)))
            self.assertEqual(canonical_json(value), (ROOT / f"infra/{name}.lock.json").read_text(encoding="utf-8"))
        self.assertEqual([], validate_locks(ROOT))

    def test_tool_without_integrity_is_rejected(self) -> None:
        value = load("toolchain")
        del value["tools"][0]["integrity"]
        self.assertTrue(list(schema("toolchain").iter_errors(value)))

    def test_non_official_or_non_https_tool_source_is_rejected(self) -> None:
        for mutation in ({"official_source": False}, {"source": "file:///tmp/tool"}):
            with self.subTest(mutation=mutation):
                value = load("toolchain")
                value["tools"][0].update(mutation)
                self.assertTrue(list(schema("toolchain").iter_errors(value)))

    def test_service_requires_exactly_one_pinned_acquisition_mode(self) -> None:
        value = load("services")
        service = value["services"][1]
        del service["image"]
        self.assertTrue(list(schema("services").iter_errors(value)))
        value = load("services")
        value["services"][1]["build"] = copy.deepcopy(value["services"][0]["build"])
        self.assertTrue(list(schema("services").iter_errors(value)))

    def test_malformed_build_and_mutable_image_are_rejected(self) -> None:
        value = load("services")
        value["services"][0]["build"]["source_sha512"] = "0" * 127
        self.assertTrue(list(schema("services").iter_errors(value)))
        value = load("services")
        value["services"][1]["image"] = "example/service:latest"
        self.assertTrue(list(schema("services").iter_errors(value)))

    def test_duplicate_ids_are_rejected_semantically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            (repository / "infra/fuseki").mkdir(parents=True)
            (repository / "infra/fuseki/Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
            tools = load("toolchain")
            services = load("services")
            tools["tools"].append(copy.deepcopy(tools["tools"][0]))
            services["services"].append(copy.deepcopy(services["services"][0]))
            (repository / "infra/toolchain.lock.json").write_text(canonical_json(tools), encoding="utf-8")
            (repository / "infra/services.lock.json").write_text(canonical_json(services), encoding="utf-8")
            errors = validate_locks(repository)
            self.assertIn("duplicate tool id", errors)
            self.assertIn("duplicate service id", errors)

    def test_container_integrity_must_equal_image_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            (repository / "infra/fuseki").mkdir(parents=True)
            (repository / "infra/fuseki/Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
            tools = load("toolchain")
            tools["tools"][3]["integrity"] = "0" * 64
            (repository / "infra/toolchain.lock.json").write_text(canonical_json(tools), encoding="utf-8")
            (repository / "infra/services.lock.json").write_text(canonical_json(load("services")), encoding="utf-8")
            self.assertTrue(any("image/integrity mismatch" in item for item in validate_locks(repository)))

    def test_preflight_rejects_missing_and_wrong_integrity_host_tool(self) -> None:
        item = load("toolchain")["tools"][0]
        with mock.patch("preflight_environment.shutil.which", return_value=None):
            self.assertEqual((None, "command unavailable"), validate_tool(ROOT, item))
        with tempfile.NamedTemporaryFile() as executable:
            with mock.patch("preflight_environment.shutil.which", return_value=executable.name):
                _, error = validate_tool(ROOT, item)
        self.assertEqual("executable integrity mismatch", error)

    def test_preflight_rejects_wrong_host_version(self) -> None:
        item = copy.deepcopy(load("toolchain")["tools"][0])
        with tempfile.NamedTemporaryFile() as executable:
            executable.write(b"pinned executable")
            executable.flush()
            item["integrity"] = hashlib.sha256(b"pinned executable").hexdigest()
            result = subprocess.CompletedProcess([executable.name], 0, stdout="Docker version 0.0.0", stderr="")
            with (
                mock.patch("preflight_environment.shutil.which", return_value=executable.name),
                mock.patch("preflight_environment.run", return_value=result),
            ):
                _, error = validate_tool(ROOT, item)
        self.assertEqual("version mismatch", error)

    def test_preflight_rejects_wrong_container_version(self) -> None:
        item = load("toolchain")["tools"][3]
        metadata = [{"Id": f"sha256:{item['integrity']}", "Config": {"Env": ["JAVA_VERSION=jdk-0.0.0"]}}]
        result = subprocess.CompletedProcess(["docker"], 0, stdout=json.dumps(metadata), stderr="")
        with mock.patch("preflight_environment.run", return_value=result):
            _, error = validate_tool(ROOT, item)
        self.assertEqual("container version mismatch: 0.0.0", error)


if __name__ == "__main__":
    unittest.main()
