"""DEC-212 Phase 2.2: fail closed if the running interpreter diverges from the pin.

The authoritative pin is `.python-version`, mirrored in `pyproject.toml`'s
`requires-python` and in every CI workflow's `actions/setup-python` step. This
test reads the pin from disk rather than hard-coding it, so a future patch
bump only needs to update `.python-version`.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

PIN_PATH = Path(__file__).resolve().parents[1] / ".python-version"


def test_python_version_file_is_an_exact_patch_pin() -> None:
    pin = PIN_PATH.read_text(encoding="utf-8").strip()
    assert pin.count(".") == 2, f".python-version must pin major.minor.patch, got {pin!r}"


def test_running_interpreter_matches_the_pin() -> None:
    pin = PIN_PATH.read_text(encoding="utf-8").strip()
    actual = platform.python_version()
    assert actual == pin, (
        f"running interpreter {actual} diverges from the pinned {pin} in "
        f"{PIN_PATH}; the environment is not the governed one"
    )


def test_running_interpreter_is_cpython() -> None:
    assert sys.implementation.name == "cpython"
