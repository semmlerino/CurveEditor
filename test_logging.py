#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify logging functionality."""

import os
import logging
from datetime import datetime
from services.logging_service import LoggingService

def test_logging():
    """Test the logging setup to ensure logs are written correctly."""
    # Setup logging
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    test_log_file = os.path.join(log_dir, f"test_logging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    print(f"Setting up logging to: {test_log_file}")

    # Initialize logging
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=test_log_file,
        console_output=True
    )

    # Test root logger
    logger.debug("DEBUG: This is a debug message from root logger")
    logger.info("INFO: This is an info message from root logger")
    logger.warning("WARNING: This is a warning message from root logger")
    logger.error("ERROR: This is an error message from root logger")

    # Test module loggers
    file_logger = LoggingService.get_logger("services.file_service")
    file_logger.info("INFO: Testing file service logger")

    curve_logger = LoggingService.get_logger("services.curve_service")
    curve_logger.debug("DEBUG: Testing curve service logger")

    # Test setting different levels
    LoggingService.set_module_level("services.file_service", logging.WARNING)
    file_logger.info("INFO: This should NOT appear (level set to WARNING)")
    file_logger.warning("WARNING: This should appear")

    # Check if log file was created and has content
    print(f"\nChecking log file...")
    if os.path.exists(test_log_file):
        size = os.path.getsize(test_log_file)
        print(f"✓ Log file exists: {test_log_file} ({size} bytes)")

        # Read and display content
        with open(test_log_file, 'r') as f:
            content = f.read()
            lines = content.splitlines()
            print(f"✓ Log file contains {len(lines)} lines")
            print("\nFirst few lines:")
            for line in lines[:5]:
                print(f"  {line}")
            print("\nLast few lines:")
            for line in lines[-5:]:
                print(f"  {line}")
    else:
        print(f"✗ Log file was not created at: {test_log_file}")

    # Clean up
    LoggingService.close()
    print("\nLogging test completed.")

if __name__ == "__main__":
    test_logging()
