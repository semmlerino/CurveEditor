#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check the home directory path and log file location.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

# Get the home directory
home_dir = os.path.expanduser("~")
print(f"Home directory: {home_dir}")

# Check various log directory paths
log_paths = [
    os.path.join(home_dir, ".curve_editor", "logs"),
    os.path.join(home_dir, ".curve_editor"),
    os.path.join("C:\\Users\\gabri\\.curve_editor\\logs"),
    os.path.join("C:\\Users\\gabri\\.curve_editor"),
]

for path in log_paths:
    exists = os.path.exists(path)
    is_dir = os.path.isdir(path) if exists else False
    print(f"\n{path}:")
    print(f"  Exists: {exists}")
    print(f"  Is directory: {is_dir}")

    if exists and is_dir:
        try:
            files = os.listdir(path)
            print(f"  Files: {files[:5] if len(files) > 5 else files}")
        except Exception as e:
            print(f"  Error listing files: {e}")

# Check if we can create a test file
test_file = os.path.join(home_dir, ".curve_editor_test.txt")
try:
    with open(test_file, 'w') as f:
        f.write("test")
    print(f"\n✓ Can write to home directory: {home_dir}")
    os.remove(test_file)
except Exception as e:
    print(f"\n✗ Cannot write to home directory: {e}")
