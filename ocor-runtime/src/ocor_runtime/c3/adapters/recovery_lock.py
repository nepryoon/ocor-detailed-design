"""Real PostgreSQL advisory-lock adapter for single-writer recovery.

Confines its own ``psycopg`` reference to this module (AFF-002/AFF-006,
``OCOR_LANGUAGE_POLICY.md`` row 8), kept as a NEW file separate from
the sealed, content-hash-pinned ``c3/adapters/postgres.py``
(OCOR-DEV-0029) so that file's own sealed evidence digest stays
untouched. Exposes only a plain, psycopg-free context manager to its
caller (``ocor_runtime.c3.recovery``), which never imports ``psycopg``
itself.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg


class PostgresAdvisoryLock:
    """A real, session-scoped PostgreSQL advisory lock (blocking):
    concurrent callers -- even in separate processes -- serialize on
    the same real, external, durable lock rather than an in-process
    one, so it enforces single-writer discipline across processes, and
    a fresh instance created after a real restart reacquires the
    identical lock and converges the same way."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("a PostgreSQL DSN is required")
        self._dsn = dsn

    @contextmanager
    def held(self, key: str) -> Iterator[None]:
        with psycopg.connect(self._dsn) as connection:
            connection.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (key,))
            try:
                yield
            finally:
                connection.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (key,))
