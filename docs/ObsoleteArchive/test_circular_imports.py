#!/usr/bin/env python
"""Test for circular imports in CurveEditor modules."""

import sys
import traceback


def test_imports():
    """Test importing all major modules to check for circular imports."""
    modules_to_test = [
        "main",
        "main_window",
        "curve_view",
        "services.unified_transformation_service",
        "services.unified_transform",
        "services.transformation_integration",
        "services.curve_service",
        "services.file_service",
        "services.history_service",
        "services.settings_service",
        "services.analysis_service",
        "services.centering_zoom_service",
        "services.visualization_service",
        "services.models",
        "services.protocols",
        "toolbar_components",
        "point_edit_components",
        "smoothing_components",
        "timeline_components",
        "status_components",
        "visualization_components",
        "ui_components",
        "menu_bar",
        "dialogs",
        "error_handling",
        "batch_edit",
        "batch_edit_protocols",
        "enhanced_curve_view",
        "keyboard_shortcuts",
    ]

    failed_imports = []
    circular_imports = []

    for module_name in modules_to_test:
        try:
            # Clear the module from sys.modules to ensure fresh import
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Try to import the module
            __import__(module_name)
            print(f"✓ Successfully imported: {module_name}")

        except ImportError as e:
            if "circular import" in str(e).lower():
                circular_imports.append((module_name, str(e)))
                print(f"✗ Circular import detected in: {module_name}")
            else:
                failed_imports.append((module_name, str(e)))
                print(f"✗ Failed to import: {module_name} - {e}")
        except Exception as e:
            failed_imports.append((module_name, traceback.format_exc()))
            print(f"✗ Error importing: {module_name} - {e}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if circular_imports:
        print(f"\nCircular imports detected: {len(circular_imports)}")
        for module, error in circular_imports:
            print(f"  - {module}: {error}")
    else:
        print("\n✓ No circular imports detected!")

    if failed_imports:
        print(f"\nFailed imports: {len(failed_imports)}")
        for module, error in failed_imports:
            print(f"  - {module}: {error}")
    else:
        print("\n✓ All modules imported successfully!")

    return len(circular_imports) == 0 and len(failed_imports) == 0


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
