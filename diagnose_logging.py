#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnostic script to identify logging issues
"""

import os
import sys
import logging
import platform
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

from services.logging_service import LoggingService

def diagnose_logging():
    """Diagnose logging issues"""
    print("=" * 80)
    print("LOGGING DIAGNOSTICS")
    print("=" * 80)
    print(f"Platform: {platform.system()}")
    print(f"Python version: {sys.version}")
    print()

    # Test 1: Basic file handler test
    print("TEST 1: Basic Python logging FileHandler")
    test_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(test_dir, exist_ok=True)
    print(f"Test directory: {test_dir}")
    print(f"Directory exists: {os.path.exists(test_dir)}")
    print(f"Directory writable: {os.access(test_dir, os.W_OK)}")

    test_file = os.path.join(test_dir, f"basic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    print(f"Test file: {test_file}")

    try:
        # Create basic logger
        basic_logger = logging.getLogger('basic_test')
        basic_logger.setLevel(logging.DEBUG)
        basic_logger.handlers.clear()

        # Create file handler directly
        handler = logging.FileHandler(test_file, mode='a', encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        basic_logger.addHandler(handler)

        # Write test message
        basic_logger.info("This is a test message")
        handler.flush()  # Force flush

        # Check if file exists
        if os.path.exists(test_file):
            size = os.path.getsize(test_file)
            print(f"✓ Basic test file created successfully (size: {size} bytes)")
            with open(test_file, 'r') as f:
                content = f.read()
            print(f"✓ Content: {content.strip()}")
        else:
            print(f"✗ Basic test file NOT created!")

        # Clean up
        handler.close()
        basic_logger.removeHandler(handler)
    except Exception as e:
        print(f"✗ ERROR in basic test: {e}")
        import traceback
        traceback.print_exc()

    print()

    # Test 2: LoggingService test
    print("TEST 2: LoggingService")
    service_test_file = os.path.join(test_dir, f"service_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    print(f"Service test file: {service_test_file}")

    try:
        # Reset LoggingService
        LoggingService.close()
        LoggingService._initialized = False

        # Setup logging with service
        logger = LoggingService.setup_logging(
            level=logging.DEBUG,
            log_file=service_test_file,
            console_output=True
        )

        # Write test messages
        logger.info("Service test message 1")
        child_logger = LoggingService.get_logger("test_module")
        child_logger.info("Child logger test message")

        # Force flush
        if LoggingService._file_handler:
            LoggingService._file_handler.flush()
            print("✓ Flushed file handler")
        else:
            print("✗ No file handler found in LoggingService!")

        # Check if file exists
        if os.path.exists(service_test_file):
            size = os.path.getsize(service_test_file)
            print(f"✓ Service test file created (size: {size} bytes)")
            with open(service_test_file, 'r') as f:
                lines = f.readlines()
            print(f"✓ Lines written: {len(lines)}")
            for i, line in enumerate(lines[:3]):
                print(f"  Line {i+1}: {line.strip()}")
        else:
            print(f"✗ Service test file NOT created!")

    except Exception as e:
        print(f"✗ ERROR in service test: {e}")
        import traceback
        traceback.print_exc()

    print()

    # Test 3: Check logging configuration
    print("TEST 3: Logging configuration")
    print(f"Root logger level: {logging.getLogger().level}")
    print(f"Root logger handlers: {logging.getLogger().handlers}")
    print(f"curve_editor logger: {logging.getLogger('curve_editor')}")
    print(f"curve_editor handlers: {logging.getLogger('curve_editor').handlers}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    diagnose_logging()
