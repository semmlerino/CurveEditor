#!/usr/bin/env python3
"""
Validation script for transformation system migration.
Run this after completing the migration to ensure everything works.
"""

import sys
import traceback
from unittest.mock import Mock

def test_no_legacy_references():
    """Test that no legacy transformation references exist."""
    print("Testing for legacy transformation references...")

    # Try to import legacy modules - these should fail
    legacy_modules = [
        'services.transform_stabilizer',
        'services.transformation_shim',
        'services.transformation_integration',
        'services.main_window_unified_patch'
    ]

    for module_name in legacy_modules:
        try:
            __import__(module_name)
            print(f"❌ FAILED: Legacy module {module_name} still exists!")
            return False
        except ImportError:
            print(f"✅ OK: Legacy module {module_name} not found (expected)")

    return True

def test_services_init_cleanup():
    """Test that services/__init__.py has been cleaned of legacy imports."""
    print("Testing services/__init__.py for legacy imports...")

    try:
        # Read the services/__init__.py file
        with open('services/__init__.py', 'r') as f:
            content = f.read()

        # Check for legacy import patterns
        legacy_patterns = [
            'transformation_integration',
            'transformation_shim',
            'transform_stabilizer',
            'TransformationShim',
            'TransformStabilizer',
            'get_transform',
            'stable_transform_operation'
        ]

        for pattern in legacy_patterns:
            if pattern in content:
                print(f"❌ FAILED: Found legacy reference '{pattern}' in services/__init__.py")
                return False

        print("✅ OK: services/__init__.py cleaned of legacy imports")
        return True

    except FileNotFoundError:
        print("❌ FAILED: services/__init__.py not found")
        return False
    except Exception as e:
        print(f"❌ FAILED: Error checking services/__init__.py: {e}")
        return False

def test_unified_transformation_functionality():
    """Test basic unified transformation functionality."""
    print("Testing unified transformation functionality...")

    try:
        from services.unified_transformation_service import UnifiedTransformationService

        # Create a mock curve view
        mock_curve_view = Mock()
        mock_curve_view.width.return_value = 800
        mock_curve_view.height.return_value = 600
        mock_curve_view.zoom_factor = 1.0
        mock_curve_view.offset_x = 0.0
        mock_curve_view.offset_y = 0.0
        mock_curve_view.flip_y_axis = True
        mock_curve_view.scale_to_image = True
        mock_curve_view.image_width = 1920
        mock_curve_view.image_height = 1080

        # Test transform creation
        transform = UnifiedTransformationService.from_curve_view(mock_curve_view)
        assert transform is not None
        print("✅ OK: Transform creation works")

        # Test point transformation
        result = UnifiedTransformationService.transform_point(transform, 100.0, 200.0)
        assert len(result) == 2
        print("✅ OK: Point transformation works")

        # Test batch transformation
        points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        results = UnifiedTransformationService.transform_points(transform, points)
        assert len(results) == 2
        print("✅ OK: Batch transformation works")

        # Test stable transformation context
        with UnifiedTransformationService.stable_transformation_context(mock_curve_view) as stable_transform:
            assert stable_transform is not None
        print("✅ OK: Stable transformation context works")

        return True

    except Exception as e:
        print(f"❌ FAILED: Unified transformation test failed: {e}")
        traceback.print_exc()
        return False

def test_main_window_initialization():
    """Test that main window initializes without legacy references."""
    print("Testing main window initialization...")

    try:
        # This is a basic import test
        import main_window

        # Check that legacy imports are not present
        source_lines = open('main_window.py', 'r').readlines()
        legacy_imports = [
            'from services.transform_stabilizer import TransformStabilizer',
            'from services.transformation_shim import',
            'from services.transformation_integration import'
        ]

        for line in source_lines:
            for legacy_import in legacy_imports:
                if legacy_import in line and not line.strip().startswith('#'):
                    print(f"❌ FAILED: Found legacy import: {line.strip()}")
                    return False

        print("✅ OK: No legacy imports found in main_window.py")
        return True

    except Exception as e:
        print(f"❌ FAILED: Main window test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("TRANSFORMATION SYSTEM MIGRATION VALIDATION")
    print("=" * 60)

    tests = [
        test_no_legacy_references,
        test_services_init_cleanup,
        test_unified_transformation_functionality,
        test_main_window_initialization
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: Test {test.__name__} crashed: {e}")
            failed += 1
        print("-" * 40)

    print(f"\nRESULTS: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 ALL TESTS PASSED! Migration completed successfully.")
        return 0
    else:
        print(f"💥 {failed} TESTS FAILED! Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
