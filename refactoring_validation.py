#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Refactoring Validation for CurveEditor.

This utility module verifies that the refactoring operations have been
successfully applied to the codebase. It checks that duplicated code
has been properly consolidated.
"""

import inspect
import os
import sys

import importlib.util

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_view_state_refactoring():
    """
    Check if ViewState class has been properly consolidated.

    Returns:
        bool: True if refactoring is complete, False otherwise
    """
    # Import both modules to check for duplicate definitions

    # Try to import ViewState from models to see if it still exists
    try:
        spec = importlib.util.find_spec("services.models")
        if spec is None:
            return False

        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)

        # Check if ViewState exists in models module
        if hasattr(models_module, "ViewState"):
            print("❌ ViewState still exists in models.py")
            return False
        else:
            print("✅ ViewState only exists in view_state.py")
            return True
    except ImportError:
        print("❓ Could not import services.models")
        return False

def check_pan_view_refactoring():
    """
    Check if pan_view method has been properly consolidated.

    Returns:
        bool: True if refactoring is complete, False otherwise
    """
    # Import both services
    from services.centering_zoom_service import CenteringZoomService
    from services.visualization_service import VisualizationService

    # Check if pan_view exists in CenteringZoomService
    centering_has_pan_view = hasattr(CenteringZoomService, "pan_view")

    # Check if pan_view exists in VisualizationService
    visualization_has_pan_view = hasattr(VisualizationService, "pan_view")

    if centering_has_pan_view and not visualization_has_pan_view:
        print("✅ pan_view only exists in CenteringZoomService")
        return True
    elif not centering_has_pan_view and visualization_has_pan_view:
        print("❌ pan_view only exists in VisualizationService instead of CenteringZoomService")
        return False
    elif centering_has_pan_view and visualization_has_pan_view:
        print("❌ pan_view still exists in both services")
        return False
    else:
        print("❓ pan_view doesn't exist in either service")
        return False

def check_extract_frame_number_refactoring():
    """
    Check if extract_frame_number function has been properly consolidated.

    Returns:
        bool: True if refactoring is complete, False otherwise
    """
    # Import both modules
    import utils
    from services.curve_service import CurveService

    # Get the source code of both implementations
    utils_src = inspect.getsource(utils.extract_frame_number)
    curve_service_src = inspect.getsource(CurveService.extract_frame_number)

    # Check if CurveService's implementation now uses the utils version
    if "from utils import extract_frame_number" in curve_service_src:
        print("✅ CurveService now uses utils.extract_frame_number")
        return True
    else:
        print("❌ CurveService does not use utils.extract_frame_number")
        return False

def run_validation():
    """Run all refactoring validation checks."""
    results = []

    print("\n== REFACTORING VALIDATION REPORT ==\n")

    print("Checking ViewState refactoring...")
    results.append(check_view_state_refactoring())

    print("\nChecking pan_view refactoring...")
    results.append(check_pan_view_refactoring())

    print("\nChecking extract_frame_number refactoring...")
    results.append(check_extract_frame_number_refactoring())

    # Overall summary
    success = all(results)
    print("\n== SUMMARY ==")
    if success:
        print("✅ All refactoring tasks completed successfully!")
    else:
        print("❌ Some refactoring tasks are incomplete or incorrect")

    return success

if __name__ == "__main__":
    run_validation()
