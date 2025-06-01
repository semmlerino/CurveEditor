#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thoroughly test the logging system to identify the issue.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

from services.logging_service import LoggingService

def test_direct_logging():
    """Test direct Python logging to see if it works."""
    print("\n=== TESTING DIRECT PYTHON LOGGING ===")

    # Create a simple logger with file handler
    test_logger = logging.getLogger('test_direct')
    test_logger.setLevel(logging.DEBUG)

    # Create file handler
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "test_direct.log")

    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)

    # Add handler to logger
    test_logger.addHandler(fh)

    # Test logging
    test_logger.info("Testing direct logging")

    # Force flush
    fh.flush()

    # Check if file exists
    if os.path.exists(log_file):
        print(f"✓ Direct logging works! File: {log_file}")
        with open(log_file, 'r') as f:
            print(f"  Content: {f.read().strip()}")
    else:
        print(f"✗ Direct logging failed - no file created")

    # Cleanup
    test_logger.removeHandler(fh)
    fh.close()

    return os.path.exists(log_file)

def test_logging_service():
    """Test LoggingService to see where it fails."""
    print("\n=== TESTING LOGGING SERVICE ===")

    # Close any existing logging
    LoggingService.close()
    LoggingService._initialized = False

    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "test_service.log")

    # Setup logging
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=log_file,
        console_output=True
    )

    print(f"Logger name: {logger.name}")
    print(f"Logger level: {logger.level}")
    print(f"Logger handlers: {logger.handlers}")
    print(f"LoggingService._log_file: {LoggingService._log_file}")
    print(f"LoggingService._file_handler: {LoggingService._file_handler}")

    # Test logging
    logger.info("Testing LoggingService")

    # Check all handlers
    for i, handler in enumerate(logger.handlers):
        print(f"\nHandler {i}: {handler}")
        print(f"  Type: {type(handler)}")
        if isinstance(handler, logging.FileHandler):
            print(f"  BaseFilename: {handler.baseFilename}")
            print(f"  Mode: {handler.mode}")
            print(f"  Encoding: {handler.encoding}")
            # Force flush
            handler.flush()

    # Check if file exists
    if os.path.exists(log_file):
        print(f"\n✓ LoggingService file created: {log_file}")
        with open(log_file, 'r') as f:
            content = f.read()
            print(f"  Size: {len(content)} bytes")
            print(f"  Content: {content[:200]}...")
    else:
        print(f"\n✗ LoggingService file NOT created: {log_file}")

    # Test a child logger
    child_logger = LoggingService.get_logger("test_module")
    print(f"\nChild logger name: {child_logger.name}")
    print(f"Child logger handlers: {child_logger.handlers}")
    print(f"Child logger propagate: {child_logger.propagate}")

    child_logger.info("Testing child logger")

    # Cleanup
    LoggingService.close()

    return os.path.exists(log_file)

def main():
    """Run all tests."""
    print("LOGGING DIAGNOSTIC TEST")
    print("=" * 60)

    # Test environment
    print("Environment:")
    print(f"  Python: {sys.version}")
    print(f"  Home: {os.path.expanduser('~')}")
    print(f"  CWD: {os.getcwd()}")

    # Run tests
    direct_ok = test_direct_logging()
    service_ok = test_logging_service()

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Direct logging: {'✓ PASS' if direct_ok else '✗ FAIL'}")
    print(f"  LoggingService: {'✓ PASS' if service_ok else '✗ FAIL'}")

    if not service_ok and direct_ok:
        print("\nDiagnosis: LoggingService has an issue, but Python logging works.")
        print("Check the LoggingService implementation for bugs.")

if __name__ == "__main__":
    main()
