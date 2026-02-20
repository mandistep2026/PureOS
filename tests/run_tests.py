#!/usr/bin/env python3
"""
tests/run_tests.py
==================
Test discovery and runner for the PureOS test suite.

This script uses only Python's standard library (``unittest``) and is the
canonical way to execute all tests.

Usage
-----
Run the full suite::

    python tests/run_tests.py

Run with increased verbosity (shows each test method name)::

    python tests/run_tests.py -v
    python tests/run_tests.py --verbose

Run only tests whose names match a pattern (substring match on
module.class.method)::

    python tests/run_tests.py --filter filesystem
    python tests/run_tests.py -f TestKernel

Run a specific test module directly (bypasses this script)::

    python -m unittest tests.unit.test_filesystem

Run a specific test class::

    python -m unittest tests.unit.test_filesystem.TestFileSystemBasics

Run a specific test method::

    python -m unittest tests.unit.test_filesystem.TestFileSystemBasics.test_mkdir

Exit codes
----------
* ``0`` — all tests passed (or the suite was empty).
* ``1`` — one or more tests failed or raised an error.
* ``2`` — invalid command-line arguments were supplied.

Compatibility with the existing ``--test`` flag in ``main.py``
--------------------------------------------------------------
The output format (summary line ``"X passed, Y failed"`` at the end) is
intentionally compatible with the prose printed by ``PureOS.run_tests()`` so
that CI scripts treating both outputs the same continue to work.
"""

import os
import sys
import argparse
import unittest
from typing import List, Optional

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so ``import core.*`` works whether
# this script is run from the project root or from inside tests/.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FilteringTestLoader(unittest.TestLoader):
    """TestLoader subclass that optionally restricts which tests are loaded.

    When *filter_pattern* is set only test methods whose fully-qualified name
    (``module.class.method``) contains *filter_pattern* as a case-insensitive
    substring are kept.
    """

    def __init__(self, filter_pattern: Optional[str] = None):
        super().__init__()
        self._filter = filter_pattern.lower() if filter_pattern else None

    def loadTestsFromModule(self, module, *args, **kwargs):
        suite = super().loadTestsFromModule(module, *args, **kwargs)
        if self._filter is None:
            return suite
        return self._apply_filter(suite)

    def _apply_filter(self, suite: unittest.TestSuite) -> unittest.TestSuite:
        """Recursively filter a test suite keeping only matching tests."""
        filtered = unittest.TestSuite()
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                child = self._apply_filter(item)
                if child.countTestCases() > 0:
                    filtered.addTest(child)
            else:
                # item is a TestCase instance
                full_name = f"{type(item).__module__}.{type(item).__qualname__}.{item._testMethodName}"
                if self._filter in full_name.lower():
                    filtered.addTest(item)
        return filtered


def _build_suite(
    start_dir: str,
    pattern: str = "test_*.py",
    filter_pattern: Optional[str] = None,
) -> unittest.TestSuite:
    """Discover and return a :class:`unittest.TestSuite`.

    Parameters
    ----------
    start_dir:
        Directory to begin recursive test discovery in.
    pattern:
        File-name glob for test module files.
    filter_pattern:
        Optional substring filter applied to fully-qualified test names.

    Returns
    -------
    unittest.TestSuite
        All discovered (and optionally filtered) tests.
    """
    loader = _FilteringTestLoader(filter_pattern)
    return loader.discover(start_dir=start_dir, pattern=pattern, top_level_dir=_PROJECT_ROOT)


def _run_suite(
    suite: unittest.TestSuite,
    verbosity: int = 1,
) -> unittest.TestResult:
    """Execute *suite* and return the result.

    Parameters
    ----------
    suite:
        The test suite to run.
    verbosity:
        ``1`` — dots only (default).  ``2`` — test-method names.

    Returns
    -------
    unittest.TestResult
        The result object; inspect ``.failures``, ``.errors``,
        ``.testsRun``, and ``.skipped`` for details.
    """
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        # Emit the timing/separator lines for readability.
        descriptions=True,
        failfast=False,
    )
    return runner.run(suite)


def _print_summary(result: unittest.TestResult, suite_count: int) -> None:
    """Print a human-readable summary compatible with ``PureOS.run_tests()``.

    Parameters
    ----------
    result:
        The :class:`unittest.TestResult` returned by the runner.
    suite_count:
        Total number of tests in the suite (may differ from
        ``result.testsRun`` if ``failfast`` is active).
    """
    passed  = result.testsRun - len(result.failures) - len(result.errors)
    failed  = len(result.failures) + len(result.errors)
    skipped = len(result.skipped) if hasattr(result, "skipped") else 0

    print()
    print("=" * 60)
    print("PureOS Test Suite Summary")
    print("=" * 60)
    print(f"  Total discovered : {suite_count}")
    print(f"  Run              : {result.testsRun}")
    print(f"  Passed           : {passed}")
    print(f"  Failed           : {failed}")
    print(f"  Skipped          : {skipped}")
    print("=" * 60)

    # Short-form compatible with the existing --test flag output format:
    #   "X passed, Y failed"
    print(f"\nTest Results: {passed} passed, {failed} failed")

    if failed == 0 and result.testsRun > 0:
        print("\nAll tests passed ✓")
    elif result.testsRun == 0:
        print("\nNo tests were found or matched the filter.")
    else:
        print(f"\n{failed} test(s) failed ✗")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    argv:
        Argument list to parse.  Defaults to ``sys.argv[1:]``.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with attributes:

        * ``verbose`` (bool) — increase runner verbosity.
        * ``filter``  (str | None) — substring filter on test names.
        * ``start_dir`` (str) — root directory for test discovery.
        * ``pattern`` (str) — filename glob for test modules.
    """
    parser = argparse.ArgumentParser(
        prog="python tests/run_tests.py",
        description="PureOS test runner — discovers and runs all unittest tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Show each test method name as it runs (verbosity=2).",
    )
    parser.add_argument(
        "-f", "--filter",
        metavar="PATTERN",
        default=None,
        help=(
            "Only run tests whose fully-qualified name contains PATTERN "
            "(case-insensitive substring match on 'module.class.method')."
        ),
    )
    parser.add_argument(
        "--start-dir",
        metavar="DIR",
        default=_HERE,
        help=(
            f"Directory to begin test discovery in.  "
            f"Defaults to '{_HERE}'."
        ),
    )
    parser.add_argument(
        "--pattern",
        metavar="GLOB",
        default="test_*.py",
        help="Filename pattern for test modules.  Defaults to 'test_*.py'.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Discover, run, and summarise the PureOS test suite.

    Parameters
    ----------
    argv:
        Argument list passed to the argument parser.  Uses ``sys.argv[1:]``
        when *None*.

    Returns
    -------
    int
        Exit code: ``0`` for success, ``1`` for test failures/errors,
        ``2`` for argument errors.
    """
    args = _parse_args(argv)

    verbosity = 2 if args.verbose else 1

    print(f"PureOS Test Runner")
    print(f"  Discovering tests in : {args.start_dir}")
    print(f"  File pattern         : {args.pattern}")
    if args.filter:
        print(f"  Filter               : {args.filter!r}")
    print()

    suite = _build_suite(
        start_dir=args.start_dir,
        pattern=args.pattern,
        filter_pattern=args.filter,
    )

    suite_count = suite.countTestCases()

    if suite_count == 0:
        print("No tests discovered.")
        if args.filter:
            print(f"(No tests matched filter {args.filter!r}.)")
        # Return 0 — an empty suite is not an error; the suite may simply not
        # exist yet.
        return 0

    result = _run_suite(suite, verbosity=verbosity)
    _print_summary(result, suite_count)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
