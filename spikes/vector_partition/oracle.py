"""Policy-partitioned Qdrant oracle with pre-ANN authorization."""

from __future__ import annotations

import hashlib
import http.client
import json
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from typing import Any

QDRANT_IMAGE = (
    "qdrant/qdrant:v1.15.1@"
    "sha256:d122138f76868edba68d36cb0833139c1d1761f00f09e48e61f8314196e6a4c6"
)


class VectorPartitionError(RuntimeError):
    """Stable base error for partitioned-vector failures."""


class PartitionAccessDenied(VectorPartitionError):
    """Authorization is rejected without revealing partition existence."""

    reason_code = "PARTITION_ACCESS_DENIED"


class ScopeMismatch(VectorPartitionError):
    """An admitted vector claims a different physical policy partition."""

    reason_code = "VECTOR_SCOPE_MISMATCH"


@dataclass(frozen=True, slots=True)
class PartitionKey:
    tenant_id: str
    domain_id: str
    compartments: tuple[str, ...]
    marking_ref: str
    model_digest: str
    representation_version: int

    def digest(self) -> str:
        body = asdict(self)
        body["compartments"] = sorted(self.compartments)
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def collection_name(self) -> str:
        return f"ocor_{self.digest()[:32]}"


@dataclass(frozen=True, slots=True)
class SearchResult:
    item_ref: str
    version: int
    score: float
    marking_ref: str


@dataclass(frozen=True, slots=True)
class TimingEnvelope:
    baseline_median_seconds: float
    allowed_upper_seconds: float

    @classmethod
    def from_samples(cls, samples: list[float]) -> TimingEnvelope:
        median = statistics.median(samples)
        return cls(median, max(0.05, median * 10))

    def admits(self, samples: list[float]) -> bool:
        return statistics.median(samples) <= self.allowed_upper_seconds


def _command(*args: str, timeout: int = 60) -> str:
    result = subprocess.run(
        args,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise VectorPartitionError(
            f"command failed ({result.returncode}): {' '.join(args)}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


class QdrantHarness:
    """Lifecycle and JSON API for an isolated, pinned real Qdrant process."""

    def __init__(self, container: str, endpoint: str) -> None:
        self.container = container
        self.endpoint = endpoint.rstrip("/")

    @classmethod
    def provision(cls) -> QdrantHarness:
        container = f"ocor-spike-0023-{uuid.uuid4().hex[:12]}"
        _command(
            "docker",
            "run",
            "--detach",
            "--name",
            container,
            "--security-opt",
            "no-new-privileges:true",
            "--tmpfs",
            "/qdrant/storage:size=256m,mode=0750",
            "--publish",
            "127.0.0.1::6333",
            QDRANT_IMAGE,
        )
        try:
            binding = _command("docker", "port", container, "6333/tcp")
            port = binding.rsplit(":", 1)[1]
            harness = cls(container, f"http://127.0.0.1:{port}")
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                try:
                    info = harness.request("GET", "/")
                    if str(info.get("version", "")).startswith("1.15"):
                        return harness
                except VectorPartitionError:
                    time.sleep(0.2)
            raise VectorPartitionError("Qdrant did not expose its pinned version")
        except Exception:
            _command("docker", "rm", "--force", container)
            raise

    def destroy(self) -> None:
        if not self.container.startswith("ocor-spike-0023-"):
            raise VectorPartitionError("refusing to destroy a non-spike container")
        _command("docker", "rm", "--force", self.container)

    def request(self, method: str, path: str, body: Any | None = None) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.endpoint}{path}", data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read())
        except (
            urllib.error.URLError,
            http.client.RemoteDisconnected,
            ConnectionError,
            json.JSONDecodeError,
        ) as exc:
            raise VectorPartitionError(f"Qdrant request failed: {method} {path}") from exc


class PartitionedVectorIndex:
    """Routes each governed scope to a distinct Qdrant collection before ANN."""

    def __init__(self, qdrant: QdrantHarness, allowed: set[str]) -> None:
        self.qdrant = qdrant
        self.allowed = frozenset(allowed)
        self.backend_requests = 0

    def _authorize(self, partition: PartitionKey, authority_digest: str) -> None:
        digest = partition.digest()
        if digest not in self.allowed or authority_digest != digest:
            raise PartitionAccessDenied("PARTITION_ACCESS_DENIED")

    def create_partition(self, partition: PartitionKey) -> None:
        self._authorize(partition, partition.digest())
        self.backend_requests += 1
        self.qdrant.request(
            "PUT",
            f"/collections/{partition.collection_name()}",
            {"vectors": {"size": 4, "distance": "Cosine"}},
        )

    def upsert(
        self,
        partition: PartitionKey,
        *,
        authority_digest: str,
        points: list[dict[str, Any]],
    ) -> None:
        self._authorize(partition, authority_digest)
        for point in points:
            payload = point.get("payload", {})
            if payload.get("partition_digest") != partition.digest():
                raise ScopeMismatch("VECTOR_SCOPE_MISMATCH")
            if "vector" not in point or len(point["vector"]) != 4:
                raise VectorPartitionError("VECTOR_DIMENSION_MISMATCH")
        self.backend_requests += 1
        self.qdrant.request(
            "PUT",
            f"/collections/{partition.collection_name()}/points?wait=true",
            {"points": points},
        )

    def search(
        self,
        partition: PartitionKey,
        *,
        authority_digest: str,
        vector: list[float],
        limit: int = 3,
    ) -> tuple[SearchResult, ...]:
        self._authorize(partition, authority_digest)
        self.backend_requests += 1
        response = self.qdrant.request(
            "POST",
            f"/collections/{partition.collection_name()}/points/query",
            {"query": vector, "limit": limit, "with_payload": True, "with_vector": False},
        )
        points = response["result"]["points"]
        results = []
        for point in points:
            payload = point["payload"]
            if payload.get("partition_digest") != partition.digest():
                raise ScopeMismatch("VECTOR_SCOPE_MISMATCH")
            results.append(
                SearchResult(
                    item_ref=payload["item_ref"],
                    version=int(payload["version"]),
                    score=float(point["score"]),
                    marking_ref=payload["marking_ref"],
                )
            )
        return tuple(results)

    def count(self, partition: PartitionKey, *, authority_digest: str) -> int:
        self._authorize(partition, authority_digest)
        self.backend_requests += 1
        response = self.qdrant.request(
            "POST",
            f"/collections/{partition.collection_name()}/points/count",
            {"exact": True},
        )
        return int(response["result"]["count"])

    def timed_searches(
        self,
        partition: PartitionKey,
        *,
        authority_digest: str,
        vector: list[float],
        samples: int = 15,
    ) -> list[float]:
        durations = []
        for _ in range(samples):
            started = time.perf_counter()
            self.search(
                partition,
                authority_digest=authority_digest,
                vector=vector,
            )
            durations.append(time.perf_counter() - started)
        return durations
