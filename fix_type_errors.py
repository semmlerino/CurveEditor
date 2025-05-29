#!/usr/bin/env python
"""Fix type checking errors in the CurveEditor project."""

import os
import sys
from pathlib import Path

def fix_test_centering_zoom():
    """Fix type errors in test_centering_zoom.py"""
    print("Fixing test_centering_zoom.py...")

    file_path = "/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_centering_zoom.py"

    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Fix 1: Remove the duplicate __init__ and misplaced docstring
    # The issue is that there's a docstring on line 431 and a duplicate __init__ around line 437
    # This appears to be remnants of a bad merge or refactoring

    # Find and remove the problematic lines
    # Line 431 has a misplaced docstring
    # Lines 433-444 seem to be duplicate/misplaced code

    # Remove lines 431-444 (0-indexed: 430-443)
    if len(lines) > 444:
        # Check if line 431 contains the misplaced docstring
        if '"""Mock main window for testing."""' in lines[430]:
            print("Removing misplaced docstring and duplicate code...")
            del lines[430:444]  # Remove lines 431-444

    # Write back the fixed file
    with open(file_path, 'w') as f:
        f.writelines(lines)

    print("Fixed test_centering_zoom.py")

def fix_main_window_protocol():
    """Fix the protocol compatibility issue in main_window.py"""
    print("Fixing main_window.py protocol issue...")

    file_path = "/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/main_window.py"

    # The issue is that DialogService.fill_gap expects MainWindowProtocol
    # but MainWindow might not implement it properly
    # The current workaround with cast() is not satisfying mypy

    # For now, we'll keep the cast but ensure MainWindow properly implements the protocol
    # This requires checking that MainWindow has all required attributes and methods

    print("main_window.py protocol issue requires architectural review")

def main():
    """Run all type checking fixes."""
    print("=== Fixing Type Checking Errors ===\n")

    # Fix test_centering_zoom.py first as it has clear structural issues
    fix_test_centering_zoom()

    # Fix other issues
    fix_main_window_protocol()

    print("\n=== Type Checking Fixes Complete ===")
    print("Run mypy to verify remaining issues")

if __name__ == "__main__":
    main()
