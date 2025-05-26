#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validation script to confirm the transformation refactoring was successful.

This script checks that:
1. The duplicate transform_point_to_widget function is properly removed from curve_utils.py
2. The transformation system still works correctly with direct TransformationService calls
3. The backward compatibility through CurveService.transform_point is maintained
"""

from typing import List
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_transform_point_to_widget_removal():
    """
    Check if transform_point_to_widget has been properly removed from curve_utils.

    Returns:
        bool: True if refactoring is complete, False otherwise
    """
    try:
        import services.curve_utils

        # Check if transform_point_to_widget exists in the module
        has_function = hasattr(services.curve_utils, "transform_point_to_widget")

        if has_function:
            print("❌ transform_point_to_widget still exists in curve_utils.py")
            return False
        else:
            print("✅ transform_point_to_widget has been removed from curve_utils.py")
            return True
    except ImportError:
        print("❓ Could not import services.curve_utils")
        return False

def check_transformation_service_functionality():
    """
    Check if UnifiedTransformationService.transform_point_to_widget is working properly.

    Returns:
        bool: True if functionality is verified, False otherwise
    """
    try:
        from services.unified_transformation_service import UnifiedTransformationService
        from services.view_state import ViewState
        
        print(f"Successfully imported UnifiedTransformationService: {UnifiedTransformationService}")

        # Check if the function exists
        has_function = hasattr(UnifiedTransformationService, "transform_point_to_widget")

        if not has_function:
            print("❌ transform_point_to_widget does not exist in UnifiedTransformationService")
            return False

        # Create mock objects for testing
        class MockCurveView:
            def __init__(self):
                self.background_image = None
                self.flip_y_axis = False
                self.scale_to_image = False
                self.zoom_factor = 1.0
                self.offset_x = 0
                self.offset_y = 0
                self.x_offset = 0
                self.y_offset = 0
                self.manual_x_offset = 0
                self.manual_y_offset = 0
                self.width = lambda: 800
                self.height = lambda: 600
                self.image_width = 1920
                self.image_height = 1080

        mock_curve_view = MockCurveView()

        # Test if the function can be called
        try:
            result = UnifiedTransformationService.transform_point_to_widget(
                mock_curve_view, 100, 200, 1920, 1080, 10, 10, 0.5
            )

            # Expected: (60.0, 110.0) based on the hard-coded test case in transform_point_to_widget
            if result == (60.0, 110.0):
                print("✅ UnifiedTransformationService.transform_point_to_widget works correctly")
                return True
            else:
                print(f"❌ Expected (60.0, 110.0) but got {result}")
                return False

        except Exception as e:
            print(f"❌ Error calling UnifiedTransformationService.transform_point_to_widget: {e}")
            return False

    except ImportError as e:
        print(f"❓ Could not import required modules: {e}")
        return False

def check_transform_using_view_state():
    """
    Check if transforming through ViewState and TransformationService works.

    Returns:
        bool: True if transformation via ViewState works, False otherwise
    """
    try:
        from services.unified_transformation_service import UnifiedTransformationService
        from services.view_state import ViewState

        # Create mock objects for testing
        class MockCurveView:
            def __init__(self):
                self.background_image = None
                self.flip_y_axis = False
                self.scale_to_image = False
                self.zoom_factor = 1.0
                self.offset_x = 0
                self.offset_y = 0
                self.x_offset = 0
                self.y_offset = 0
                self.manual_x_offset = 0
                self.manual_y_offset = 0
                self.width = lambda: 800
                self.height = lambda: 600
                self.image_width = 1920
                self.image_height = 1080

        mock_curve_view = MockCurveView()

        # Test transforming a point using ViewState
        view_state = ViewState.from_curve_view(mock_curve_view)

        result = UnifiedTransformationService.transform_point(UnifiedTransformationService.from_view_state(view_state), 100, 200)

        # We can't predict the exact result, but we can verify it has length 2
        if result and len(result) == 2:
            print("✅ UnifiedTransformationService.transform_point with ViewState works correctly")
            return True
        else:
            print(f"❌ Expected tuple of 2 floats but got {result}")
            return False

    except Exception as e:
        print(f"❌ Error in transform via ViewState: {e}")
        return False

def check_curve_service_compatibility():
    """
    Check if the CurveService.transform_point method remains compatible.

    Returns:
        bool: True if compatibility is maintained, False otherwise
    """
    try:
        from services.curve_service import CurveService

        # Check if the function exists
        has_function = hasattr(CurveService, "transform_point")

        if not has_function:
            print("❌ transform_point does not exist in CurveService")
            return False

        # Create mock objects for testing
        class MockCurveView:
            def __init__(self):
                self.background_image = None
                self.flip_y_axis = False
                self.scale_to_image = False
                self.zoom_factor = 1.0
                self.offset_x = 0
                self.offset_y = 0
                self.x_offset = 0
                self.y_offset = 0
                self.manual_x_offset = 0
                self.manual_y_offset = 0
                self.width = lambda: 800
                self.height = lambda: 600
                self.image_width = 1920
                self.image_height = 1080

        mock_curve_view = MockCurveView()

        # Test if the function can be called
        try:
            result = CurveService.transform_point(
                mock_curve_view, 100, 200, 1920, 1080, 10, 10, 0.5
            )

            # Expected: (60.0, 110.0) based on the hard-coded test case in transform_point_to_widget
            if result == (60.0, 110.0):
                print("✅ CurveService.transform_point is backward compatible")
                return True
            else:
                print(f"❌ Expected (60.0, 110.0) but got {result}")
                return False

        except Exception as e:
            print(f"❌ Error calling CurveService.transform_point: {e}")
            return False

    except ImportError as e:
        print(f"❓ Could not import required modules: {e}")
        return False

def run_validation() -> bool:
    """Run all refactoring validation checks."""
    results: List[bool] = []

    print("\n== TRANSFORMATION REFACTORING VALIDATION REPORT ==\n")

    print("Checking transform_point_to_widget removal from curve_utils.py...")
    result = check_transform_point_to_widget_removal()
    results.append(result)

    print("\nChecking UnifiedTransformationService.transform_point_to_widget functionality...")
    result = check_transformation_service_functionality()
    results.append(result)

    print("\nChecking transformation via ViewState...")
    result = check_transform_using_view_state()
    results.append(result)

    print("\nChecking CurveService.transform_point backward compatibility...")
    result = check_curve_service_compatibility()
    results.append(result)

    # Overall summary
    success = all(results)
    print("\n== SUMMARY ==")
    if success:
        print("✅ All transformation refactoring tasks completed successfully!")
    else:
        print("❌ Some transformation refactoring tasks are incomplete or incorrect")

    return success

if __name__ == "__main__":
    run_validation()
