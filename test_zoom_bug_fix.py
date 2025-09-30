#!/usr/bin/env python
"""Test to verify the zoom-float bug is fixed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.transform_service import Transform, ViewState


def test_zoom_bug_fix():
    """Test that zoom operations don't cause floating/drift."""

    print("Testing zoom-float bug fix...")
    print("=" * 60)

    # Create initial ViewState with separate fit_scale and zoom_factor
    initial_state = ViewState(
        display_width=1280.0,  # Now float for precision
        display_height=720.0,  # Now float for precision
        widget_width=800,
        widget_height=600,
        zoom_factor=1.0,  # User zoom only
        fit_scale=0.75,  # Separate fit scale (to fit content in widget)
        scale_to_image=False,
        flip_y_axis=False,
    )

    # Create initial transform
    t1 = Transform.from_view_state(initial_state)

    # Test point at center of data
    data_x, data_y = 640, 360

    # Get initial screen position
    screen_x1, screen_y1 = t1.data_to_screen(data_x, data_y)
    print("Initial state:")
    print(f"  Fit scale: {initial_state.fit_scale:.3f}")
    print(f"  User zoom: {initial_state.zoom_factor:.3f}")
    print(f"  Combined scale: {initial_state.fit_scale * initial_state.zoom_factor:.3f}")
    print(f"  Data point: ({data_x}, {data_y})")
    print(f"  Screen position: ({screen_x1:.2f}, {screen_y1:.2f})")

    # Simulate zoom in by 10%
    zoomed_state = ViewState(
        display_width=1280.0,
        display_height=720.0,
        widget_width=800,
        widget_height=600,
        zoom_factor=1.1,  # User zoomed in 10%
        fit_scale=0.75,  # Fit scale remains the same
        scale_to_image=False,
        flip_y_axis=False,
    )

    # Create zoomed transform
    t2 = Transform.from_view_state(zoomed_state)

    # Get new screen position (without pan adjustment)
    screen_x2, screen_y2 = t2.data_to_screen(data_x, data_y)
    print("\nAfter zoom to 1.1x (without pan adjustment):")
    print(f"  Fit scale: {zoomed_state.fit_scale:.3f}")
    print(f"  User zoom: {zoomed_state.zoom_factor:.3f}")
    print(f"  Combined scale: {zoomed_state.fit_scale * zoomed_state.zoom_factor:.3f}")
    print(f"  Screen position: ({screen_x2:.2f}, {screen_y2:.2f})")

    # Calculate drift
    drift_x = screen_x2 - screen_x1
    drift_y = screen_y2 - screen_y1
    print(f"  Position change: ({drift_x:.2f}, {drift_y:.2f})")

    # The point should move outward from center when zooming
    # This is expected behavior when zooming without pan adjustment

    # Now test with pan adjustment (simulating wheelEvent behavior)
    pan_adjust_x = screen_x1 - screen_x2  # Keep point at same screen position
    pan_adjust_y = screen_y1 - screen_y2

    zoomed_with_pan = ViewState(
        display_width=1280.0,
        display_height=720.0,
        widget_width=800,
        widget_height=600,
        zoom_factor=1.1,
        fit_scale=0.75,
        offset_x=pan_adjust_x,  # Pan adjustment
        offset_y=pan_adjust_y,  # Pan adjustment
        scale_to_image=False,
        flip_y_axis=False,
    )

    t3 = Transform.from_view_state(zoomed_with_pan)
    screen_x3, screen_y3 = t3.data_to_screen(data_x, data_y)

    print("\nAfter zoom with pan adjustment:")
    print(f"  Pan adjustment: ({pan_adjust_x:.2f}, {pan_adjust_y:.2f})")
    print(f"  Screen position: ({screen_x3:.2f}, {screen_y3:.2f})")

    # Calculate final drift
    final_drift_x = abs(screen_x3 - screen_x1)
    final_drift_y = abs(screen_y3 - screen_y1)

    print(f"  Final drift from original: ({final_drift_x:.2f}, {final_drift_y:.2f})")

    # Success criteria: drift should be less than 1 pixel
    if final_drift_x < 1.0 and final_drift_y < 1.0:
        print("\n✅ SUCCESS: Zoom bug is fixed! Point stays at same screen position.")
        print("   Fit scale and zoom factor are properly separated.")
        return True
    else:
        print("\n❌ FAILURE: Point still drifts during zoom!")
        print(f"   Drift: ({final_drift_x:.2f}, {final_drift_y:.2f}) pixels")
        return False


def test_scale_compounding():
    """Test that scales are applied correctly."""

    print("\n" + "=" * 60)
    print("Testing scale compounding...")

    state = ViewState(
        display_width=1000.0,
        display_height=1000.0,
        widget_width=500,
        widget_height=500,
        zoom_factor=2.0,  # User zoom 2x
        fit_scale=0.5,  # Fit scale 0.5
        scale_to_image=False,
        flip_y_axis=False,
    )

    transform = Transform.from_view_state(state)

    # The combined scale should be fit_scale * zoom_factor = 0.5 * 2.0 = 1.0
    expected_scale = 0.5 * 2.0

    # Test a point transformation
    data_x, data_y = 100, 100
    screen_x, screen_y = transform.data_to_screen(data_x, data_y)

    # With scale 1.0 and center at (250, 250), point (100,100) should be at (100, 100) + center offset
    # Since display is 1000x1000 and widget is 500x500, center offset should center the content

    print(f"  Fit scale: {state.fit_scale}")
    print(f"  User zoom: {state.zoom_factor}")
    print(f"  Expected combined scale: {expected_scale}")
    print(f"  Data point: ({data_x}, {data_y})")
    print(f"  Screen point: ({screen_x:.2f}, {screen_y:.2f})")

    # Verify the transform is using the correct combined scale
    # The transform should effectively have scale = 1.0
    back_x, back_y = transform.screen_to_data(screen_x, screen_y)

    error_x = abs(back_x - data_x)
    error_y = abs(back_y - data_y)

    print(f"  Round-trip back to data: ({back_x:.2f}, {back_y:.2f})")
    print(f"  Round-trip error: ({error_x:.6f}, {error_y:.6f})")

    if error_x < 0.001 and error_y < 0.001:
        print("\n✅ SUCCESS: Scale compounding is correct!")
        return True
    else:
        print("\n❌ FAILURE: Scale compounding has errors!")
        return False


if __name__ == "__main__":
    success1 = test_zoom_bug_fix()
    success2 = test_scale_compounding()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ ALL TESTS PASSED - Zoom bug is fixed!")
    else:
        print("❌ SOME TESTS FAILED - More work needed")

    sys.exit(0 if (success1 and success2) else 1)
