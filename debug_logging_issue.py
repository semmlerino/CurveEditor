#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug logging to find out why log files aren't being created."""

import os
import sys
import logging
from datetime import datetime
import traceback

# Test 1: Basic Python logging
print("TEST 1: Basic Python logging")
print("-" * 40)

log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
print(f"Log directory: {log_dir}")
print(f"Directory exists: {os.path.exists(log_dir)}")

# Create directory
os.makedirs(log_dir, exist_ok=True)
print(f"Directory exists after makedirs: {os.path.exists(log_dir)}")

# Create a basic log file
basic_log = os.path.join(log_dir, "basic_test.log")
print(f"\nTrying to create basic log file: {basic_log}")

try:
    # Test basic file writing
    with open(basic_log, 'w') as f:
        f.write("Test write\n")
    print(f"✓ Basic file write successful")
except Exception as e:
    print(f"✗ Basic file write failed: {e}")
    traceback.print_exc()

# Test Python logging module
try:
    # Configure basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(basic_log),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger("test_logger")
    logger.info("Test log message from basic logging")

    # Check file content
    if os.path.exists(basic_log):
        with open(basic_log, 'r') as f:
            content = f.read()
        print(f"✓ Log file exists, size: {len(content)} bytes")
        print(f"Content preview: {content[:100]}...")
    else:
        print(f"✗ Log file not created")

except Exception as e:
    print(f"✗ Basic logging failed: {e}")
    traceback.print_exc()

# Test 2: Test LoggingService
print("\n\nTEST 2: LoggingService")
print("-" * 40)

try:
    from services.logging_service import LoggingService

    test_log = os.path.join(log_dir, f"service_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    print(f"Testing LoggingService with: {test_log}")

    # Setup logging
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=test_log,
        console_output=True
    )

    logger.info("Test message from LoggingService")

    # Force flush
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
            print(f"✓ Flushed FileHandler: {handler.baseFilename}")

    # Check if file exists
    if os.path.exists(test_log):
        size = os.path.getsize(test_log)
        print(f"✓ LoggingService log file created: {test_log} ({size} bytes)")
        with open(test_log, 'r') as f:
            content = f.read()
        print(f"Content: {content[:200]}...")
    else:
        print(f"✗ LoggingService log file NOT created")

    # Check handlers
    print(f"\nLogger handlers: {logger.handlers}")
    for handler in logger.handlers:
        print(f"  - {handler.__class__.__name__}: {getattr(handler, 'baseFilename', 'N/A')}")

except Exception as e:
    print(f"✗ LoggingService test failed: {e}")
    traceback.print_exc()

# Test 3: Check permissions
print("\n\nTEST 3: Directory permissions")
print("-" * 40)

# Check directory permissions
try:
    test_file = os.path.join(log_dir, "permission_test.txt")
    with open(test_file, 'w') as f:
        f.write("Permission test")
    os.remove(test_file)
    print(f"✓ Write permissions OK for {log_dir}")
except Exception as e:
    print(f"✗ Permission issue: {e}")

# List existing log files
print(f"\nExisting log files in {log_dir}:")
if os.path.exists(log_dir):
    files = os.listdir(log_dir)
    for f in sorted(files)[:10]:  # Show first 10
        filepath = os.path.join(log_dir, f)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            print(f"  - {f} ({size} bytes)")
else:
    print("  Directory does not exist!")

print("\nDiagnostic complete.")
