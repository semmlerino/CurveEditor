#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify and fix the logging issue."""

import os
import sys
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.logging_service import LoggingService

def test_current_logging():
    """Test the current logging setup to reproduce the issue."""
    print("=" * 60)
    print("TEST 1: Current Logging Setup (Expected to fail)")
    print("=" * 60)

    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    test_log = os.path.join(log_dir, f"test_current_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    # Setup logging as currently implemented
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=test_log,
        console_output=True
    )

    # Test logging
    logger.info("Test message from root logger")

    # Test child logger
    child_logger = LoggingService.get_logger("test_module")
    child_logger.info("Test message from child logger")

    # Check if file was created
    if os.path.exists(test_log):
        size = os.path.getsize(test_log)
        print(f"✓ Log file created: {test_log} ({size} bytes)")
    else:
        print(f"✗ Log file NOT created: {test_log}")

    LoggingService.close()
    return os.path.exists(test_log)

def test_fixed_logging():
    """Test a potential fix for the logging issue."""
    print("\n" + "=" * 60)
    print("TEST 2: Fixed Logging Setup")
    print("=" * 60)

    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    test_log = os.path.join(log_dir, f"test_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    # Create logger directly to test the fix
    logger = logging.getLogger('curve_editor')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    # Create file handler
    try:
        file_handler = logging.FileHandler(test_log, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Test logging immediately
        logger.info("Test message - should appear in log file")

        # Force flush
        file_handler.flush()

        # Test child logger
        child_logger = logging.getLogger('curve_editor.test_module')
        child_logger.info("Child logger message - should also appear")

        # Force flush again
        file_handler.flush()

        # Close handler to ensure write
        file_handler.close()

        # Check if file was created and has content
        if os.path.exists(test_log):
            size = os.path.getsize(test_log)
            print(f"✓ Log file created: {test_log} ({size} bytes)")

            with open(test_log, 'r') as f:
                content = f.read()
                lines = content.strip().split('\n')
                print(f"✓ Log contains {len(lines)} lines")
                print("\nLog content:")
                for line in lines:
                    print(f"  {line}")
        else:
            print(f"✗ Log file NOT created: {test_log}")

    except Exception as e:
        print(f"✗ Error setting up logging: {e}")
        import traceback
        traceback.print_exc()

    return os.path.exists(test_log)

def main():
    """Run the tests."""
    # Test current implementation
    current_works = test_current_logging()

    # Test potential fix
    fixed_works = test_fixed_logging()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Current implementation: {'✓ WORKS' if current_works else '✗ FAILS'}")
    print(f"Fixed implementation: {'✓ WORKS' if fixed_works else '✗ FAILS'}")

    if not current_works and fixed_works:
        print("\nThe issue is confirmed! The logging setup needs to be fixed.")
        print("The problem appears to be with how the logger and handlers are configured.")

if __name__ == "__main__":
    main()
