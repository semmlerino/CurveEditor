#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validation script for the service-based architecture refactoring.
This script ensures that the standardized import patterns for all services work correctly.
"""

import os
import sys

def validate_import(import_statement, expected_class_name):
    """Validate a specific import and print the results"""
    print(f"\n📋 Testing import: {import_statement}")
    try:
        exec(import_statement)
        service_class = eval(expected_class_name)
        print(f"✅ Successfully imported {expected_class_name}")

        # Check methods in the service
        print(f"✅ {expected_class_name} has these methods:")
        methods = [m for m in dir(service_class) if not m.startswith("_") and callable(getattr(service_class, m))]
        for method_name in methods[:5]:  # Show only first 5 methods to avoid clutter
            print(f"  - {method_name}")
        if len(methods) > 5:
            print(f"  - ... and {len(methods) - 5} more methods")

        return True
    except Exception as e:
        print(f"❌ Failed to import {expected_class_name}: {e}")
        return False

def check_deprecated_files():
    """Check status of deprecated files"""
    print("\n📋 Checking deprecated files:")
    deprecated_files = [
        "curve_view_operations.py",
        "image_operations.py",
        "visualization_operations.py",
        "centering_zoom_operations.py"
    ]

    for file in deprecated_files:
        if not os.path.exists(file):
            print(f"✅ {file} has been removed (good)")
        elif os.path.exists(f"{file}.deprecated"):
            print(f"✅ {file} has been marked as deprecated")
        else:
            # The file exists but isn't marked as deprecated, check if it contains a warning
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    if "DEPRECATED" in content and "warning" in content.lower():
                        print(f"✅ {file} contains proper deprecation warning")
                    else:
                        print(f"⚠️ {file} exists but may not have proper deprecation warning")
            except Exception:
                print(f"⚠️ {file} exists but could not check for deprecation warning")

# Validate all service imports
print("🔍 VALIDATING SERVICE ARCHITECTURE REFACTORING")
print("="*60)

# Define imports to test
imports_to_test = [
    ("from services.curve_service import CurveService as CurveViewOperations", "CurveViewOperations"),
    ("from services.image_service import ImageService as ImageOperations", "ImageOperations"),
    ("from services.visualization_service import VisualizationService", "VisualizationService"),
    ("from services.centering_zoom_service import CenteringZoomService as ZoomOperations", "ZoomOperations"),
    ("from services.analysis_service import AnalysisService", "AnalysisService"),
    ("from services.history_service import HistoryService", "HistoryService"),
    ("from services.file_service import FileService", "FileService"),
    ("from services.dialog_service import DialogService", "DialogService")
]

# Track success/failure
successful_imports = 0
failed_imports = 0

for import_stmt, class_name in imports_to_test:
    if validate_import(import_stmt, class_name):
        successful_imports += 1
    else:
        failed_imports += 1

# Check deprecated files
check_deprecated_files()

# Print summary
print("\n📊 VALIDATION SUMMARY")
print("="*60)
print(f"✅ Successful imports: {successful_imports}")
print(f"❌ Failed imports: {failed_imports}")
total_services = len(imports_to_test)
success_percentage = (successful_imports / total_services) * 100
print(f"📈 Service architecture migration: {success_percentage:.1f}% complete")

print("\nValidation complete.")
