"""Automated check script for TV4 frontend: syntax compilation, fixture validation, and unit tests."""

from __future__ import annotations

import py_compile
import sys
import unittest
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from providers import MockDataProvider  # noqa: E402


def check_python_syntax() -> list[Path]:
    """Compile all Python files under src/frontend to catch syntax errors early."""
    py_files = sorted(FRONTEND_DIR.rglob("*.py"))
    for path in py_files:
        py_compile.compile(str(path), doraise=True)
    return py_files


def check_fixtures() -> dict[str, object]:
    """Verify sample CSV and JSON fixtures load cleanly and match schema."""
    provider = MockDataProvider()
    return provider.get_dataset_info()


def run_unit_tests() -> unittest.TestResult:
    """Discover and execute all unit tests under tests/."""
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(FRONTEND_DIR / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def main() -> int:
    compiled = check_python_syntax()
    print(f"[1/3] Syntax OK ({len(compiled)} Python files)")

    info = check_fixtures()
    print(f"[2/3] Fixtures OK (listings={info['listing_count']}, version={info['dataset_version']})")

    print("[3/3] Running unit tests...")
    result = run_unit_tests()
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
