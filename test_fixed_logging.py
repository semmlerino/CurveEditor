#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the fixed LoggingService.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

from services.logging_service import LoggingService

def test_fixed_logging():
    """Test that the fixed LoggingService works correctly."""

    # Setup test log file
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"test_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    print(f"Testing fixed LoggingService...")
    print(f"Log file: {log_file}")
    print("-" * 60)

    # Initialize logging
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=log_file,
        console_output=True
    )

    # Test root logger
    logger.info("Root logger test message")

    # Test child loggers
    modules = ["ui_components", "timeline_components", "csv_export"]
    for module in modules:
        child_logger = LoggingService.get_logger(module)
        child_logger.info(f"Testing {module} logger")

    # Force close to flush everything
    LoggingService.close()

    # Check if log file was created and has content
    print(f"\nChecking log file...")
    if os.path.exists(log_file):
        size = os.path.getsize(log_file)
        with open(log_file, 'r') as f:
            lines = f.readlines()

        print(f"✓ Log file created successfully")
        print(f"✓ Size: {size} bytes")
        print(f"✓ Lines written: {len(lines)}")

        if lines:
            print(f"\nLog contents:")
            for line in lines:
                print(f"  {line.strip()}")

        return True
    else:
        print(f"✗ ERROR: Log file was not created!")
        return False

if __name__ == "__main__":
    success = test_fixed_logging()
    sys.exit(0 if success else 1)
