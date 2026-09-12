"""PHASE2-4-BACKLOG-GENERATOR-DRIFT: scripts/build_ocor_development_plan.py
must reproduce the committed backlog/DAG/context-manifest bit-for-bit.

RED (reports/tests/evidence/rem_backlog_generator_drift/red.log, fingerprint
below): before this fix, `scripts/build_ocor_development_plan.py`'s
`TASK_SPECS` only ever described 69 tasks. Tasks OCOR-DEV-0070..0084 (the
WS-12 infrastructure-bootstrap-repair chain, adopted into
docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json out of band, without
ever updating the generator that is this repository's sanctioned way of
producing that file) were silently dropped by any real regeneration -- the
generator would overwrite the committed 84-task backlog with a 69-task one,
destroying 15 already-accepted tasks and every dependency edge that gates on
them (OCOR-DEV-0016/0017/0018/0021 each depend on OCOR-DEV-0084). This was
caught by actually invoking the generator during Phase 2.1 and diffing its
output against the committed file -- never by a test, because no test
exercised the generator's output against reality at all.

GREEN: this test drives the real generator functions (`build_tasks`,
`dag_text`, `context_manifest`) against the same pinned IRB/ADD/LLD matrix
input the CLI uses, and asserts field-for-field, and then object-for-object,
identity against the currently committed
docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json,
docs/development_plan/OCOR_DEPENDENCY_DAG.mmd and
docs/development_plan/OCOR_AGENT_CONTEXT_MANIFEST.json. It does not invoke
`build_trace` / OCOR_TRACEABILITY_PLAN.csv generation: that output has its
own separate, already-known staleness (e.g. a hard-coded
`baseline_status["WS-12"] = "ABSENT"` and a `by_ws[rid]` "last task with this
requirement wins" resolution that a duplicated cross-cutting requirement ID
such as BR-003 makes order-sensitive) that predates and is independent of
this drift, and is intentionally out of scope for this remediation.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "scripts/build_ocor_development_plan.py"
RED_LOG = ROOT / "reports/tests/evidence/rem_backlog_generator_drift/red.log"

SPEC = importlib.util.spec_from_file_location("build_ocor_development_plan_rem", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
gen = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gen
SPEC.loader.exec_module(gen)


def _rows() -> list[dict[str, object]]:
    matrix = json.loads((ROOT / "reports/traceability/OCOR_IRB_ADD_LLD_v1.1_Matrix.json").read_text(encoding="utf-8"))
    return matrix["rows"]


def _real_backlog() -> list[dict[str, object]]:
    data = json.loads((ROOT / "docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json").read_text(encoding="utf-8"))
    return data["tasks"] if isinstance(data, dict) and "tasks" in data else data


def test_red_log_is_sealed_and_fingerprinted():
    assert RED_LOG.is_file(), "RED evidence for PHASE2-4-BACKLOG-GENERATOR-DRIFT is missing"
    digest = hashlib.sha256(RED_LOG.read_bytes()).hexdigest()
    assert digest == "94c2781e8c0072dd4e7c1b84c9772aeedd7159fa78e00f521efb946bc7748841"
    assert "tasks silently dropped by regeneration" in RED_LOG.read_text(encoding="utf-8")
    assert "OCOR-DEV-0084" in RED_LOG.read_text(encoding="utf-8")


def test_generated_task_count_matches_reality():
    tasks = gen.build_tasks(_rows())
    real_tasks = _real_backlog()
    gen_ids = {t["id"] for t in tasks}
    real_ids = {t["id"] for t in real_tasks}
    assert gen_ids == real_ids
    assert len(tasks) == len(real_tasks) == 84


def test_every_generated_task_is_byte_identical_to_the_committed_backlog():
    tasks = gen.build_tasks(_rows())
    real_by_id = {t["id"]: t for t in _real_backlog()}
    gen_by_id = {t["id"]: t for t in tasks}
    mismatches = {tid: (gen_by_id[tid], real_by_id[tid]) for tid in real_by_id if gen_by_id[tid] != real_by_id[tid]}
    assert not mismatches, f"generator/reality task mismatches: {sorted(mismatches)}"


def test_generated_dag_is_byte_identical_to_the_committed_dag():
    tasks = gen.build_tasks(_rows())
    _order, _waves, critical, _duration = gen.topological(tasks)
    generated = gen.dag_text(tasks, critical)
    real = (ROOT / "docs/development_plan/OCOR_DEPENDENCY_DAG.mmd").read_text(encoding="utf-8")
    # write_text() (the sanctioned writer) appends the file's trailing
    # newline; dag_text() itself is only required to match its content.
    assert generated == real.rstrip("\n")


def test_generated_context_manifest_is_identical_to_the_committed_manifest():
    tasks = gen.build_tasks(_rows())
    generated = gen.context_manifest(tasks)
    real = json.loads((ROOT / "docs/development_plan/OCOR_AGENT_CONTEXT_MANIFEST.json").read_text(encoding="utf-8"))
    assert generated == real
