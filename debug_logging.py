#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug logging configuration issue.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

# Import LoggingService
from services.logging_service import LoggingService

# Create a very simple test
log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
os.makedirs(log_dir, exist_ok=True)

test_log_file = os.path.join(log_dir, f"debug_logging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

print(f"Log directory: {log_dir}")
print(f"Log file: {test_log_file}")
print(f"Directory exists: {os.path.exists(log_dir)}")
print(f"Directory is writable: {os.access(log_dir, os.W_OK)}")

# Try to create the file directly
try:
    with open(test_log_file, 'w') as f:
        f.write("Test file creation\n")
    print(f"✓ Direct file creation succeeded")
    os.remove(test_log_file)
except Exception as e:
    print(f"✗ Direct file creation failed: {e}")

# Now try with logging
print("\nTrying with logging module...")
try:
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=test_log_file,
        console_output=True
    )

    logger.info("Test log entry")

    # Check if file was created
    if os.path.exists(test_log_file):
        print(f"✓ Log file created: {test_log_file}")
        print(f"  Size: {os.path.getsize(test_log_file)} bytes")
    else:
        print(f"✗ Log file NOT created")

    # Force a flush
    for handler in logger.handlers:
        handler.flush()

    # Check again
    if os.path.exists(test_log_file):
        print(f"✓ After flush - log file exists")
        with open(test_log_file, 'r') as f:
            content = f.read()
            print(f"  Content: {repr(content)}")
    else:
        print(f"✗ After flush - log file still does not exist")

except Exception as e:
    print(f"✗ Logging setup failed: {e}")
    import traceback
    traceback.print_exc()

# Clean up
LoggingService.close()
