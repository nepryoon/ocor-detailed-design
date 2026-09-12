"""Phase 3 (CC-OCOR-DELIVERY-COMPLETION mandate) benchmark harness guards.

These tests do not re-verify the sealed Phase 3 decision numbers (that
evidence is a point-in-time measurement, sealed in
reports/benchmarks/phase3_language_migration_benchmark_20260912.json). They
guard the two things that would otherwise let the harness silently drift
away from what was actually decided:

1. The thresholds hard-coded in scripts/run_language_migration_benchmark.py
   must stay byte-identical to the numbers fixed, before any measurement,
   in docs/development_methodology/OCOR_LANGUAGE_POLICY.md §3. A silent
   edit to either side without the other would invalidate every future
   Phase 3 rerun without anyone noticing.
2. The sealed corpus fixture must stay exactly what it was when component 1
   was measured (same seed, same generator, same bytes) so a future rerun
   is actually comparable to the sealed decision, not a different corpus
   wearing the same file name.

A fast, low-repeat end-to-end run of component 1 is included (skipped, with
a registered exception, when Node.js or the compiled SDK oracle is
unavailable) to prove the comparison logic itself is correct -- not to
reproduce the exact sealed ratio, which depends on host hardware.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "scripts/run_language_migration_benchmark.py"
POLICY_PATH = ROOT / "docs/development_methodology/OCOR_LANGUAGE_POLICY.md"
CORPUS_PATH = ROOT / "reports/benchmarks/fixtures/phase3_canonical_corpus.json"

SPEC = importlib.util.spec_from_file_location("run_language_migration_benchmark_test", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness
SPEC.loader.exec_module(harness)


def _policy_text() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def test_component_1_thresholds_match_the_policy_document():
    text = _policy_text()
    assert "supera **3×**" in text
    assert harness.COMPONENT_1_MEDIAN_RATIO_THRESHOLD == 3.0
    assert "supera **2 ms**" in text
    assert harness.COMPONENT_1_P95_MS_THRESHOLD == 2.0


def test_component_2_threshold_matches_the_policy_document():
    text = _policy_text()
    assert "supera **15 ms**" in text
    assert harness.COMPONENT_2_P95_MS_THRESHOLD == 15.0


def test_component_3_thresholds_match_the_policy_document():
    text = _policy_text()
    assert "sotto **5.000 messaggi/s**" in text
    assert harness.COMPONENT_3_THROUGHPUT_FLOOR_MSG_S == 5000
    assert "supera **20 ms**" in text
    assert harness.COMPONENT_3_P95_MS_THRESHOLD == 20.0


def test_component_4_threshold_matches_the_policy_document():
    text = _policy_text()
    assert "supera **200 ms**" in text
    assert harness.COMPONENT_4_PROJECTION_LAG_P95_MS_THRESHOLD == 200.0


def test_reference_payload_size_matches_the_policy_document():
    text = _policy_text()
    assert "payload di riferimento (10 KB)" in text
    assert harness.CORPUS_TARGET_BYTES == 10_000


def test_sealed_corpus_fixture_is_unchanged():
    assert CORPUS_PATH.is_file(), "sealed Phase 3 corpus fixture is missing"
    digest = hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()
    assert digest == "2ce8879bc8e5697a4f51e37a3ae1262da4995c2fdba7f2ba23e6e3e775da80b7"


def test_corpus_generator_is_deterministic_and_reproduces_the_sealed_fixture():
    corpus = harness.generate_corpus(harness.CORPUS_SEED, harness.CORPUS_DOC_COUNT, harness.CORPUS_TARGET_BYTES)
    regenerated = json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert hashlib.sha256(regenerated.encode("utf-8")).hexdigest() == "2ce8879bc8e5697a4f51e37a3ae1262da4995c2fdba7f2ba23e6e3e775da80b7"


def test_corpus_documents_are_near_the_10kb_reference_payload():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    sizes = [len(json.dumps(doc, ensure_ascii=False).encode("utf-8")) for doc in corpus]
    assert len(sizes) == 200
    assert all(9_000 <= size <= 11_000 for size in sizes)


def test_components_2_3_4_are_reported_not_yet_measurable_never_fabricated():
    for measure in (harness.measure_component_2, harness.measure_component_3, harness.measure_component_4):
        result = measure()
        assert result["status"] == "NOT_YET_MEASURABLE"
        assert "reason" in result and len(result["reason"]) > 20
        assert "outcome" not in result, "a component with no real measurement must never carry an outcome verdict"


def _node_and_compiled_oracle_available() -> bool:
    node = shutil.which("node")
    if node is None:
        return False
    version = subprocess.run([node, "--version"], check=False, capture_output=True, text=True, timeout=10)
    if version.returncode != 0 or version.stdout.strip() != "v20.20.2":
        return False
    return harness.BENCHMARK_CLI.is_file()


@pytest.mark.skipif(
    not _node_and_compiled_oracle_available(),
    reason="TEST-INFRA-004: Node.js v20.20.2 with the compiled SDK oracle is required for the cross-language benchmark",
)
def test_component_1_measurement_end_to_end_smoke():
    original_repeats = harness.REPEATS_PER_DOCUMENT
    original_corpus_path = harness.CORPUS_PATH
    small_corpus = harness.generate_corpus(harness.CORPUS_SEED, count=5, target_bytes=1_000)
    scratch = ROOT / "reports/tests/evidence/phase3_smoke_corpus.json"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text(json.dumps(small_corpus, ensure_ascii=False), encoding="utf-8")
    try:
        harness.CORPUS_PATH = scratch
        harness.REPEATS_PER_DOCUMENT = 3
        result = harness.measure_component_1()
    finally:
        harness.CORPUS_PATH = original_corpus_path
        harness.REPEATS_PER_DOCUMENT = original_repeats
        scratch.unlink(missing_ok=True)
    assert result["status"] == "MEASURED"
    assert result["outcome"] in {"NO_MIGRATION_JUSTIFIED", "MIGRATION_THRESHOLD_EXCEEDED"}
    assert result["measurements"]["python_median_ns"] > 0
    assert result["measurements"]["node_median_ns"] > 0


def test_no_prohibited_claim_appears_in_the_sealed_benchmark_evidence():
    evidence_path = ROOT / "reports/benchmarks/phase3_language_migration_benchmark_20260912.json"
    text = evidence_path.read_text(encoding="utf-8")
    prohibited = [r"E1\s*=\s*1", r"E2\s*=\s*1", r"Production readiness\s*=\s*(GO|PASS)", r"runtime conformance\s*=\s*PASS"]
    assert not [pattern for pattern in prohibited if re.search(pattern, text, flags=re.IGNORECASE)]
