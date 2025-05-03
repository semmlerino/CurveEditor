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
        "centering_zoom_operations.py",
        "curve_data_operations.py",
        "settings_operations.py",
        "history_operations.py",
        "file_operations.py",
        "curve_operations.py"
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
    # Core services with backward compatibility aliases
    ("from services.curve_service import CurveService as CurveViewOperations", "CurveViewOperations"),
    ("from services.image_service import ImageService as ImageOperations", "ImageOperations"),
    ("from services.visualization_service import VisualizationService as VisualizationOperations", "VisualizationOperations"),
    ("from services.centering_zoom_service import CenteringZoomService as ZoomOperations", "ZoomOperations"),
    ("from services.analysis_service import AnalysisService as CurveDataOperations", "CurveDataOperations"),
    ("from services.history_service import HistoryService as HistoryOperations", "HistoryOperations"),
    ("from services.file_service import FileService as FileOperations", "FileOperations"),
    ("from services.settings_service import SettingsService as SettingsOperations", "SettingsOperations"),

    # Direct service imports (without aliases)
    ("from services.curve_service import CurveService", "CurveService"),
    ("from services.image_service import ImageService", "ImageService"),
    ("from services.visualization_service import VisualizationService", "VisualizationService"),
    ("from services.centering_zoom_service import CenteringZoomService", "CenteringZoomService"),
    ("from services.analysis_service import AnalysisService", "AnalysisService"),
    ("from services.history_service import HistoryService", "HistoryService"),
    ("from services.file_service import FileService", "FileService"),
    ("from services.dialog_service import DialogService", "DialogService"),
    ("from services.settings_service import SettingsService", "SettingsService"),
    ("from services.input_service import InputService", "InputService")
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

# Validation recommendations
print("\n📝 RECOMMENDATIONS")
print("="*60)
if failed_imports > 0:
    print("⚠️ Fix failed imports to ensure proper service architecture")
    print("   Run the validation again after making changes")
else:
    print("✅ All imports are working correctly!")

print("\n🔍 NEXT STEPS")
print("="*60)
print("1. Run the application and test all functionality")
print("2. Consider removing .deprecated files if all imports are now using services")
print("3. Complete test coverage for all service methods")
print("4. Clean up debug print statements and improve error handling")

print("\nValidation complete.")
