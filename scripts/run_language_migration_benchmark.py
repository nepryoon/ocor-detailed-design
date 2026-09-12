"""Phase 3 (CC-OCOR-DELIVERY-COMPLETION mandate) language-migration benchmark.

Measures the 4 candidate components named in
docs/development_methodology/OCOR_LANGUAGE_POLICY.md §3 against the
migration thresholds fixed there *before* any measurement was taken, and
reports, per component, either a real measured outcome or an honest
NOT_YET_MEASURABLE status with the concrete reason (never a fabricated
number and never a skip reported as a pass).

Component 1 (RFC 8785 canonicalization kernel + digest) is the only one
with a real implementation on both sides of the comparison today: the
Python kernel (ocor_runtime.canonical) and the compiled TypeScript SDK
(ocor-runtime/sdk/typescript, built in Phase 2.3), driven the same way
Node.js already serves as the REM-0007 cross-language oracle. It is
measured for real by this script.

Components 2 (C3 commit path), 3 (C5 event backbone) and 4 (C4 projection)
have no qualifying real backend/implementation to measure yet:
- Component 2 needs a live PostgreSQL backend, exactly like the live suite
  in ocor-runtime/tests/tasks/test_ocor_dev_0015.py, which is NOT_EXECUTED
  in this sandbox for the identical, already-documented reason (no local
  Postgres). It becomes measurable once wired into a CI job with the
  Postgres service already used by the `integration-postgresql` workflow
  step.
- Components 3 and 4 have no implementation at all yet:
  ocor_runtime.c5_actions is the obsolete 32-transition FSM (not the real
  Kafka-backed event backbone, OCOR-DEV-0040/0041) and ocor_runtime.c4_marking
  implements only the marking lattice (not a TypeDB/Jena projection adapter,
  OCOR-DEV-0037/0038), both per docs/planning/OCOR_CURRENT_STATE_BASELINE.json.
  They become measurable once those backlog tasks land.

Reporting these as NOT_YET_MEASURABLE, with the precise reason, is a
complete and honest partial outcome for this iteration -- not a stand-in
for NO_MIGRATION_JUSTIFIED, which requires an actual measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = ROOT / "ocor-runtime/sdk/typescript"
BENCHMARK_CLI = SDK_ROOT / "dist/cli/benchmark_canonicalize.js"
CORPUS_PATH = ROOT / "reports/benchmarks/fixtures/phase3_canonical_corpus.json"

sys.path.insert(0, str(ROOT / "ocor-runtime/src"))

# Thresholds transcribed verbatim from docs/development_methodology/
# OCOR_LANGUAGE_POLICY.md §3, fixed before any measurement. A permanent
# regression test (reports/tests/test_language_migration_benchmark_harness.py)
# asserts these stay byte-identical to the policy document's own numbers.
COMPONENT_1_MEDIAN_RATIO_THRESHOLD = 3.0
COMPONENT_1_P95_MS_THRESHOLD = 2.0
COMPONENT_2_P95_MS_THRESHOLD = 15.0
COMPONENT_3_THROUGHPUT_FLOOR_MSG_S = 5000
COMPONENT_3_P95_MS_THRESHOLD = 20.0
COMPONENT_4_PROJECTION_LAG_P95_MS_THRESHOLD = 200.0

CORPUS_SEED = 20260912
CORPUS_DOC_COUNT = 200
CORPUS_TARGET_BYTES = 10_000
REPEATS_PER_DOCUMENT = 25


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_corpus(seed: int, count: int, target_bytes: int) -> list[dict[str, Any]]:
    """Deterministically generate `count` documents near `target_bytes` serialized.

    A tiny linear-congruential generator (not `random.Random`) is used
    deliberately: its output is defined by this file's own arithmetic, not
    by a CPython/PyPy PRNG implementation detail that could drift across
    interpreter versions and silently change the sealed corpus hash below.
    """
    state = seed

    def next_u32() -> int:
        nonlocal state
        state = (state * 1103515245 + 12345) & 0xFFFFFFFF
        return state

    def word(n: int) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyzÀÉ€😀"
        return "".join(alphabet[next_u32() % len(alphabet)] for _ in range(n))

    documents: list[dict[str, Any]] = []
    for doc_index in range(count):
        doc: dict[str, Any] = {
            "document_id": f"phase3-corpus-{doc_index:04d}",
            "kind": "reference_payload",
            "tags": [word(6) for _ in range(4)],
            "fields": {},
        }
        # Keep padding with small records until the canonical-JSON-shaped
        # document is within +/-5% of the target serialized size.
        while True:
            serialized = len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
            if serialized >= target_bytes:
                break
            key = f"f{len(doc['fields']):04d}"
            doc["fields"][key] = {
                "label": word(10),
                "value": (next_u32() % 2_000_000_000) / 1000.0,
                "flag": next_u32() % 2 == 0,
                "note": word(24),
            }
        documents.append(doc)
    return documents


def load_or_build_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.is_file():
        raise SystemExit(
            f"missing sealed corpus fixture at {CORPUS_PATH}; "
            "run with --regenerate-corpus once, inspect the diff, then commit it"
        )
    result: list[dict[str, Any]] = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return result


def _python_timings_ns(corpus: list[dict[str, Any]], repeats: int) -> list[float]:
    from ocor_runtime.canonical import canonical_sha256, canonicalize_json  # noqa: PLC0415

    per_document_medians: list[float] = []
    for document in corpus:
        samples: list[int] = []
        for _ in range(repeats):
            start = time.perf_counter_ns()
            canonicalize_json(document)
            canonical_sha256(document)
            end = time.perf_counter_ns()
            samples.append(end - start)
        per_document_medians.append(statistics.median(samples))
    return per_document_medians


def _node_timings_ns(corpus: list[dict[str, Any]], repeats: int) -> list[float]:
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node.js is mandatory for the component-1 cross-language oracle")
    if not BENCHMARK_CLI.is_file():
        raise SystemExit(
            f"missing compiled oracle at {BENCHMARK_CLI}; run "
            "`npm install && npm run build` in ocor-runtime/sdk/typescript first"
        )
    version = subprocess.run([node, "--version"], check=False, capture_output=True, text=True, timeout=10)
    if version.returncode != 0 or version.stdout.strip() != "v20.20.2":
        raise SystemExit(f"expected Node v20.20.2, got {version.stdout.strip()!r} (rc={version.returncode})")
    stdin_text = "\n".join(json.dumps(doc, ensure_ascii=False) for doc in corpus) + "\n"
    result = subprocess.run(
        [node, str(BENCHMARK_CLI), str(repeats)],
        input=stdin_text,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise SystemExit(f"node benchmark oracle failed: {result.stderr}")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != len(corpus):
        raise SystemExit(f"expected {len(corpus)} oracle results, got {len(lines)}")
    return [float(json.loads(line)["median_ns"]) for line in lines]


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def measure_component_1() -> dict[str, Any]:
    corpus = load_or_build_corpus()
    corpus_bytes = CORPUS_PATH.read_bytes()
    python_ns = _python_timings_ns(corpus, REPEATS_PER_DOCUMENT)
    node_ns = _node_timings_ns(corpus, REPEATS_PER_DOCUMENT)

    python_median_ns = statistics.median(python_ns)
    node_median_ns = statistics.median(node_ns)
    python_p95_ms = _p95(python_ns) / 1_000_000
    ratio = python_median_ns / node_median_ns if node_median_ns > 0 else float("inf")

    threshold_exceeded = ratio > COMPONENT_1_MEDIAN_RATIO_THRESHOLD or python_p95_ms > COMPONENT_1_P95_MS_THRESHOLD
    return {
        "component": "rfc8785_canonicalization_kernel",
        "status": "MEASURED",
        "outcome": "MIGRATION_THRESHOLD_EXCEEDED" if threshold_exceeded else "NO_MIGRATION_JUSTIFIED",
        "measurements": {
            "corpus_documents": len(corpus),
            "corpus_sha256": _sha256_bytes(corpus_bytes),
            "repeats_per_document": REPEATS_PER_DOCUMENT,
            "python_median_ns": python_median_ns,
            "node_median_ns": node_median_ns,
            "median_ratio_python_over_node": ratio,
            "python_p95_ms": python_p95_ms,
        },
        "thresholds": {
            "median_ratio_gt": COMPONENT_1_MEDIAN_RATIO_THRESHOLD,
            "python_p95_ms_gt": COMPONENT_1_P95_MS_THRESHOLD,
        },
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": __import__("os").cpu_count(),
        },
    }


def measure_component_2() -> dict[str, Any]:
    return {
        "component": "c3_commit_path",
        "status": "NOT_YET_MEASURABLE",
        "reason": (
            "Requires a live PostgreSQL backend, exactly like "
            "ocor-runtime/tests/tasks/test_ocor_dev_0015.py's live suite, which is "
            "NOT_EXECUTED in this sandbox for the same, already-documented reason "
            "(no local PostgreSQL). Real measurement requires wiring this component "
            "into a CI job with the same Postgres service the integration-postgresql "
            "workflow step already provisions; not fabricated here."
        ),
        "thresholds": {"p95_ms_gt": COMPONENT_2_P95_MS_THRESHOLD},
    }


def measure_component_3() -> dict[str, Any]:
    return {
        "component": "c5_event_backbone",
        "status": "NOT_YET_MEASURABLE",
        "reason": (
            "No real C5 event-backbone implementation exists yet: "
            "ocor_runtime.c5_actions is the obsolete 32-transition action FSM, not "
            "the approved Kafka-backed event backbone (OCOR-DEV-0040/0041, WS-06, "
            "not yet executed), per docs/planning/OCOR_CURRENT_STATE_BASELINE.json. "
            "There is nothing to benchmark until that backlog task lands."
        ),
        "thresholds": {
            "throughput_floor_msg_s": COMPONENT_3_THROUGHPUT_FLOOR_MSG_S,
            "p95_ms_gt": COMPONENT_3_P95_MS_THRESHOLD,
        },
    }


def measure_component_4() -> dict[str, Any]:
    return {
        "component": "c4_projection",
        "status": "NOT_YET_MEASURABLE",
        "reason": (
            "No real C4 projection adapter exists yet: ocor_runtime.c4_marking "
            "implements only the marking lattice, not a TypeDB/Jena projection "
            "adapter (OCOR-DEV-0037/0038, WS-05, not yet executed), per "
            "docs/planning/OCOR_CURRENT_STATE_BASELINE.json. There is nothing to "
            "benchmark until those backlog tasks land."
        ),
        "thresholds": {"projection_lag_p95_ms_gt": COMPONENT_4_PROJECTION_LAG_P95_MS_THRESHOLD},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--regenerate-corpus",
        action="store_true",
        help="Regenerate and overwrite the sealed component-1 corpus fixture, then exit.",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write the full JSON result here.")
    args = parser.parse_args()

    if args.regenerate_corpus:
        corpus = generate_corpus(CORPUS_SEED, CORPUS_DOC_COUNT, CORPUS_TARGET_BYTES)
        CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CORPUS_PATH.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {len(corpus)} documents to {CORPUS_PATH} (sha256={_sha256_file(CORPUS_PATH)})")
        return 0

    result = {
        "schema_version": "1.0",
        "policy_reference": "docs/development_methodology/OCOR_LANGUAGE_POLICY.md#3-soglie-di-migrazione",
        "components": [
            measure_component_1(),
            measure_component_2(),
            measure_component_3(),
            measure_component_4(),
        ],
    }
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
