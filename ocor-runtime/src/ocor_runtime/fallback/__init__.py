"""ARA-approved persistence fallbacks."""

from .postgres_outbox import (
    POSTGRESQL_DDL,
    OutboxReconciler,
    PostgreSQLTransactionalOutbox,
    select_atomic_backend,
)

__all__ = [
    "POSTGRESQL_DDL",
    "OutboxReconciler",
    "PostgreSQLTransactionalOutbox",
    "select_atomic_backend",
]

