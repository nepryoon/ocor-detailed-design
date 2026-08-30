from __future__ import annotations

from datetime import datetime, timezone

import pytest


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

