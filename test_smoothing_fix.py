#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that the smoothing operation no longer shifts the entire curve.
This test creates sample data, applies smoothing, and checks for curve displacement.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.analysis_service import AnalysisService
import math

def test_smoothing_no_displacement():
    """Test that smoothing operation doesn't shift the curve."""

    # Create test data - a simple sine wave with some noise
    test_data = []
    for i in range(100):
        x = i * 0.1
        y = math.sin(x) * 100 + 500  # Sine wave centered at y=500

        # Add some noise to simulate real data
        if i % 5 == 0:
            y += (i % 10 - 5) * 2  # Small noise

        test_data.append((i, x * 100, y))  # frame, x, y

    # Calculate the centroid before smoothing
    centroid_x_before = sum(p[1] for p in test_data) / len(test_data)
    centroid_y_before = sum(p[2] for p in test_data) / len(test_data)

    print(f"Centroid before smoothing: ({centroid_x_before:.2f}, {centroid_y_before:.2f})")

    # Apply smoothing to all points
    analysis = AnalysisService(test_data)
    indices = list(range(len(test_data)))
    window_size = 7

    # Apply the smoothing
    analysis.smooth_moving_average(indices, window_size)
    smoothed_data = analysis.get_data()

    # Calculate the centroid after smoothing
    centroid_x_after = sum(p[1] for p in smoothed_data) / len(smoothed_data)
    centroid_y_after = sum(p[2] for p in smoothed_data) / len(smoothed_data)

    print(f"Centroid after smoothing: ({centroid_x_after:.2f}, {centroid_y_after:.2f})")

    # Calculate the shift
    shift_x = abs(centroid_x_after - centroid_x_before)
    shift_y = abs(centroid_y_after - centroid_y_before)

    print(f"Centroid shift: ({shift_x:.2f}, {shift_y:.2f})")

    # Check individual points
    print("\nSample point comparisons:")
    for i in [0, 25, 50, 75, 99]:
        before = test_data[i]
        after = smoothed_data[i]
        print(f"Point {i}: ({before[1]:.2f}, {before[2]:.2f}) -> ({after[1]:.2f}, {after[2]:.2f})")

    # Test passes if the centroid shift is minimal (less than 1% of the range)
    x_range = max(p[1] for p in test_data) - min(p[1] for p in test_data)
    y_range = max(p[2] for p in test_data) - min(p[2] for p in test_data)

    max_allowed_shift_x = x_range * 0.01  # 1% of range
    max_allowed_shift_y = y_range * 0.01  # 1% of range

    if shift_x < max_allowed_shift_x and shift_y < max_allowed_shift_y:
        print("\n✓ TEST PASSED: Centroid shift is within acceptable range")
        print(f"  X shift: {shift_x:.2f} < {max_allowed_shift_x:.2f}")
        print(f"  Y shift: {shift_y:.2f} < {max_allowed_shift_y:.2f}")
        return True
    else:
        print("\n✗ TEST FAILED: Centroid shift is too large")
        print(f"  X shift: {shift_x:.2f} > {max_allowed_shift_x:.2f}")
        print(f"  Y shift: {shift_y:.2f} > {max_allowed_shift_y:.2f}")
        return False

if __name__ == "__main__":
    success = test_smoothing_no_displacement()
    sys.exit(0 if success else 1)
