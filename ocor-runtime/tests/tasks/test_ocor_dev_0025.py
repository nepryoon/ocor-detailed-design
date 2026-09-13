"""OCOR-DEV-0025: SPIKE distributed deletion saga.

Proves that a deletion request spanning real, independent backends
(PostgreSQL for metadata, TypeDB for content, Qdrant for cache/index)
reports DELETION_INCOMPLETE until every backend independently confirms
the item is gone -- and that a real backend outage during deletion is
correctly reflected, then resolved once the backend recovers and the
saga is retried. Every backend is real; no mocks. Reuses
spikes.vector_partition.oracle.QdrantHarness (OCOR-DEV-0023) and
scripts/fault_inject_test_environment.py's fault injection helpers
(OCOR-DEV-0083), both unmodified.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SCRIPTS_DIR = REPOSITORY_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from spikes.memory_deletion.saga import (  # noqa: E402 -- must follow sys.path.insert above
    DeletionStatus,
    PostgresMetadataTarget,
    QdrantCacheTarget,
    TypeDBContentTarget,
    run_deletion_saga,
)
from spikes.vector_partition.oracle import QdrantHarness  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "fault_inject_test_environment_0025", SCRIPTS_DIR / "fault_inject_test_environment.py"
)
assert _SPEC is not None and _SPEC.loader is not None
fault_inject = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fault_inject
_SPEC.loader.exec_module(fault_inject)

TYPEDB_HEALTH_URL = "http://127.0.0.1:8000/health"


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    dsn = os.environ.get("OCOR_LIVE_POSTGRES_DSN")
    if not dsn:
        pytest.fail("OCOR_LIVE_POSTGRES_DSN is mandatory qualifying evidence")
    return dsn


@pytest.fixture(scope="session")
def typedb_reachable() -> None:
    if not fault_inject.http_reachable(TYPEDB_HEALTH_URL, timeout=5.0):
        pytest.fail("a real, live TypeDB instance is mandatory qualifying evidence")


@pytest.fixture
def campaign(postgres_dsn: str, typedb_reachable: None):
    qdrant = QdrantHarness.provision()
    collection = f"ocor_deletion_{uuid.uuid4().hex[:12]}"
    metadata = PostgresMetadataTarget(postgres_dsn)
    content = TypeDBContentTarget()
    cache = QdrantCacheTarget(qdrant, collection)
    try:
        yield metadata, content, cache
    finally:
        qdrant.destroy()


def test_saga_deletes_across_all_real_backends_and_reports_deleted(campaign):
    metadata, content, cache = campaign
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    for target in (metadata, content, cache):
        target.put(item_id)
    assert all(target.contains(item_id) for target in (metadata, content, cache))

    receipt = run_deletion_saga(item_id, [metadata, content, cache])

    assert receipt.status is DeletionStatus.DELETED
    assert set(receipt.acknowledged) == {"metadata-postgres", "content-typedb", "cache-qdrant"}
    assert receipt.remaining == ()
    assert not any(target.contains(item_id) for target in (metadata, content, cache))


def test_saga_reports_deletion_incomplete_when_typedb_is_paused_then_recovers(campaign):
    metadata, content, cache = campaign
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    for target in (metadata, content, cache):
        target.put(item_id)

    pause = fault_inject.run(
        fault_inject.fault_command("typedb", "pause"), cwd=REPOSITORY_ROOT, timeout=30
    )
    assert pause.returncode == 0, pause.stderr
    try:
        paused = fault_inject._poll(lambda: not fault_inject.http_reachable(TYPEDB_HEALTH_URL, timeout=1.0), timeout=10.0)
        assert paused, "typedb was never observed unreachable after pause"

        receipt = run_deletion_saga(item_id, [metadata, content, cache])
    finally:
        unpause = fault_inject.run(
            fault_inject.fault_command("typedb", "unpause"), cwd=REPOSITORY_ROOT, timeout=30
        )
        assert unpause.returncode == 0, unpause.stderr
        recovered = fault_inject._poll(lambda: fault_inject.http_reachable(TYPEDB_HEALTH_URL, timeout=2.0), timeout=15.0)
        assert recovered, "typedb did not recover within the bounded window after unpause"

    assert receipt.status is DeletionStatus.DELETION_INCOMPLETE
    assert "content-typedb" in receipt.remaining
    assert set(receipt.acknowledged) == {"metadata-postgres", "cache-qdrant"}
    # content was never actually deleted while typedb was paused
    assert content.contains(item_id)

    retry = run_deletion_saga(item_id, [content])
    assert retry.status is DeletionStatus.DELETED
    assert not content.contains(item_id)


def test_a_success_receipt_is_structurally_impossible_while_any_target_still_contains_the_item(campaign):
    metadata, content, cache = campaign
    item_id = f"urn:ocor:item:{uuid.uuid4()}"
    metadata.put(item_id)

    class LyingTarget:
        """A target whose tombstone() call succeeds (no exception) but the
        item remains genuinely findable -- proves the saga never trusts a
        target's own success signal, only its own independent contains()
        re-check."""

        name = "lying-target"

        def tombstone(self, item_id: str) -> None:
            return None  # claims success by not raising, but deletes nothing

        def contains(self, item_id: str) -> bool:
            return True  # always still findable

    receipt = run_deletion_saga(item_id, [metadata, LyingTarget()])

    assert receipt.status is DeletionStatus.DELETION_INCOMPLETE
    assert "lying-target" in receipt.remaining
    assert "metadata-postgres" in receipt.acknowledged


def test_an_unreachable_target_fails_closed_as_remaining_not_acknowledged():
    class UnreachableTarget:
        name = "unreachable-target"

        def tombstone(self, item_id: str) -> None:
            raise ConnectionError("simulated real network failure")

        def contains(self, item_id: str) -> bool:
            raise ConnectionError("simulated real network failure")

    receipt = run_deletion_saga("urn:ocor:item:unreachable", [UnreachableTarget()])
    assert receipt.status is DeletionStatus.DELETION_INCOMPLETE
    assert receipt.remaining == ("unreachable-target",)
