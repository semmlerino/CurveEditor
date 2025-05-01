#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validation script for the CurveService refactoring.
This script ensures that the standardized import pattern for CurveService works correctly.
"""

import os
import sys

# Try importing using the standard pattern
try:
    from services.curve_service import CurveService as CurveViewOperations
    print("✅ Successfully imported CurveService as CurveViewOperations")
except Exception as e:
    print(f"❌ Failed to import CurveService as CurveViewOperations: {e}")
    sys.exit(1)

# Check if curve_view_operations.py exists (should not exist)
if os.path.exists("curve_view_operations.py"):
    print("❌ Legacy file curve_view_operations.py still exists and should be removed")
else:
    print("✅ Legacy file curve_view_operations.py has been removed")

# Check if we can access methods in CurveViewOperations
try:
    print(f"✅ CurveViewOperations has these methods:")
    for method_name in dir(CurveViewOperations):
        if not method_name.startswith("_"):
            print(f"  - {method_name}")
except Exception as e:
    print(f"❌ Failed to inspect CurveViewOperations methods: {e}")

print("\nValidation complete.")
