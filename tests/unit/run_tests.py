#!/usr/bin/env python3
"""
Test runner for Job Application Tracker.

This script runs all test modules and provides a comprehensive test report.
"""

import sys
import os
import unittest
import argparse

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def discover_and_run_tests(test_dir="tests", pattern="test_*.py", verbosity=2):
    """
    Discover and run all tests in the test directory.

    Args:
        test_dir (str): Directory containing test files
        pattern (str): Pattern to match test files
        verbosity (int): Test output verbosity level

    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Discover tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern=pattern)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.splitlines()[-1]}")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.splitlines()[-1]}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    status = "PASSED" if success else "FAILED"
    print(f"\nOverall result: {status}")
    print("="*60)

    return success


def run_specific_test(test_module, verbosity=2):
    """
    Run a specific test module.

    Args:
        test_module (str): Name of the test module to run
        verbosity (int): Test output verbosity level

    Returns:
        bool: True if all tests passed, False otherwise
    """
    try:
        # Import the test module
        module = __import__(f"tests.{test_module}", fromlist=[test_module])

        # Create test suite from module
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)

        # Run tests
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        return len(result.failures) == 0 and len(result.errors) == 0

    except ImportError as e:
        print(f"Error importing test module '{test_module}': {e}")
        return False


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Run tests for Job Application Tracker")
    parser.add_argument("--module", "-m", type=str,
                       help="Run specific test module (e.g., test_parsing)")
    parser.add_argument("--verbose", "-v", action="count", default=1,
                       help="Increase verbosity (use -v, -vv, or -vvv)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Quiet mode (minimal output)")

    args = parser.parse_args()

    # Set verbosity level
    if args.quiet:
        verbosity = 0
    else:
        verbosity = min(args.verbose, 3)

    print("="*60)
    print("JOB APPLICATION TRACKER - TEST SUITE")
    print("="*60)

    if args.module:
        print(f"Running specific test module: {args.module}")
        success = run_specific_test(args.module, verbosity)
    else:
        print("Running all tests...")
        success = discover_and_run_tests(verbosity=verbosity)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
