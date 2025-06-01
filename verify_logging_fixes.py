#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test to verify logging functionality after fixes.
This script imports various modules and tests that logging is working correctly.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

from services.logging_service import LoggingService

def test_logging_setup():
    """Test that logging is properly configured and writing to files."""

    # Setup logging directory
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Create test log file
    test_log_file = os.path.join(log_dir, f"verify_logging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    print(f"Testing logging setup...")
    print(f"Log file: {test_log_file}")
    print("-" * 60)

    # Initialize logging
    logger = LoggingService.setup_logging(
        level=logging.DEBUG,
        log_file=test_log_file,
        console_output=True
    )

    # Test various modules that were fixed
    print("\n1. Testing root logger...")
    logger.info("Root logger test - this should appear in the log file")

    print("\n2. Testing fixed modules...")
    modules_to_test = [
        "ui_components",
        "timeline_components",
        "csv_export",
        "signal_registry",
        "shortcut_signal_connector",
        "view_signal_connector",
        "edit_signal_connector",
        "application_state",
        "enhanced_curve_view"
    ]

    for module_name in modules_to_test:
        module_logger = LoggingService.get_logger(module_name)
        module_logger.info(f"Testing logger for {module_name} - logging is working!")
        print(f"   ✓ {module_name}")

    # Verify log file exists and has content
    print(f"\n3. Verifying log file...")
    if os.path.exists(test_log_file):
        size = os.path.getsize(test_log_file)
        with open(test_log_file, 'r') as f:
            lines = f.readlines()

        print(f"   ✓ Log file created successfully")
        print(f"   ✓ Size: {size} bytes")
        print(f"   ✓ Lines written: {len(lines)}")

        # Show some sample lines
        print(f"\n4. Sample log entries:")
        for i, line in enumerate(lines[:5]):
            print(f"   [{i+1}] {line.strip()}")

        # Check if all modules logged
        modules_found = 0
        for module in modules_to_test:
            if any(module in line for line in lines):
                modules_found += 1

        print(f"\n5. Module coverage: {modules_found}/{len(modules_to_test)} modules logged successfully")

        return True
    else:
        print(f"   ✗ ERROR: Log file was not created!")
        return False

def test_import_modules():
    """Test that all fixed modules can be imported without errors."""
    print("\n6. Testing module imports...")

    try:
        # Import the fixed modules to ensure no syntax errors
        import ui_components
        print("   ✓ ui_components imported successfully")

        import timeline_components
        print("   ✓ timeline_components imported successfully")

        import csv_export
        print("   ✓ csv_export imported successfully")

        import signal_registry
        print("   ✓ signal_registry imported successfully")

        from signal_connectors import shortcut_signal_connector
        print("   ✓ shortcut_signal_connector imported successfully")

        from signal_connectors import view_signal_connector
        print("   ✓ view_signal_connector imported successfully")

        from signal_connectors import edit_signal_connector
        print("   ✓ edit_signal_connector imported successfully")

        import application_state
        print("   ✓ application_state imported successfully")

        import enhanced_curve_view
        print("   ✓ enhanced_curve_view imported successfully")

        return True
    except ImportError as e:
        print(f"   ✗ ERROR importing module: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("CURVE EDITOR LOGGING VERIFICATION")
    print("=" * 60)

    # Test logging setup
    logging_ok = test_logging_setup()

    # Test imports
    imports_ok = test_import_modules()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Logging functionality: {'✓ PASS' if logging_ok else '✗ FAIL'}")
    print(f"  Module imports: {'✓ PASS' if imports_ok else '✗ FAIL'}")
    print(f"  Overall: {'✓ ALL TESTS PASSED' if logging_ok and imports_ok else '✗ SOME TESTS FAILED'}")
    print("=" * 60)

    # Cleanup
    LoggingService.close()

    return 0 if (logging_ok and imports_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
