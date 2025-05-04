#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test runner for the CurveEditor application.

This script runs all unit tests, generates a coverage report,
and validates the service architecture.
"""

import unittest
import os
import sys
import subprocess
import argparse
from services.logging_service import LoggingService

logger = LoggingService.get_logger("test_runner")

def setup_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for CurveEditor")
    parser.add_argument("--coverage", action="store_true",
                        help="Generate coverage report")
    parser.add_argument("--validate", action="store_true",
                        help="Run architecture validation")
    parser.add_argument("--verbosity", type=int, default=2, choices=[0, 1, 2],
                        help="Verbosity level for test output")
    parser.add_argument("--tests", type=str, default=None,
                        help="Specific test module or class to run (e.g., 'test_curve_service' or 'test_curve_service.TestCurveService')")
    return parser.parse_args()

def run_tests(args):
    """Run all unit tests and optionally generate coverage report."""
    logger.info("Running tests...")

    if args.coverage:
        try:
            import coverage
        except ImportError:
            logger.error("Coverage package not found. Install with: pip install coverage")
            return False

        cov = coverage.Coverage(
            source=['services'],
            omit=['*/__init__.py', '*/test_*.py']
        )
        cov.start()

    # Discover and run tests
    loader = unittest.TestLoader()

    if args.tests:
        # Run specific test module or class
        if '.' in args.tests:
            # Format: module.class
            module_name, class_name = args.tests.split('.')
            module = __import__(f'tests.{module_name}', fromlist=[class_name])
            test_class = getattr(module, class_name)
            suite = loader.loadTestsFromTestCase(test_class)
        else:
            # Just a module name
            suite = loader.loadTestsFromName(f'tests.{args.tests}')
    else:
        # Run all tests
        suite = loader.discover('./tests', pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)

    if args.coverage:
        cov.stop()
        cov.save()

        # Print coverage report
        logger.info("\nCoverage Report:")
        cov.report()

        # Generate HTML report
        html_dir = os.path.join(os.getcwd(), 'coverage_html')
        cov.html_report(directory=html_dir)
        logger.info(f"HTML coverage report generated in: {html_dir}/index.html")

    return result.wasSuccessful()

def validate_architecture(args):
    """Run the architecture validation script."""
    if not args.validate:
        return True

    logger.info("\nValidating service architecture...")
    try:
        result = subprocess.run([sys.executable, 'refactoring_validation.py'],
                                capture_output=True, text=True)

        print(result.stdout)

        if result.returncode != 0:
            logger.error("Architecture validation failed!")
            return False

        return True
    except Exception as e:
        logger.error(f"Error running validation: {e}")
        return False

def main():
    """Main entry point for test runner."""
    # Initialize logging
    LoggingService.setup_logging(log_file="test_run.log")

    # Parse arguments
    args = setup_arguments()

    # Run tests
    tests_passed = run_tests(args)

    # Validate architecture if requested
    architecture_valid = validate_architecture(args)

    if tests_passed and (not args.validate or architecture_valid):
        logger.info("\n✅ All tests passed" +
                   (" and architecture validated successfully!" if args.validate else "!"))
        return 0
    else:
        logger.error("\n❌ Tests or validation failed. See output above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
