#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pyright: reportUnusedVariable=false

"""
Canonical module for all core curve data operations.

This module consolidates logic for smoothing, filtering, filling gaps,
extrapolation, and potentially other data manipulations to ensure
consistency and maintainability.
"""

from typing import List, Tuple, Optional, Sequence
import math
import copy
# Potential future imports: numpy, scipy if added

class CurveDataOperations:
    """Provides methods for manipulating curve data."""

    def __init__(self, curve_data: Sequence[Tuple[int, float, float]]):
        """
        Initialize with the curve data to operate on.

        Args:
            curve_data: List of (frame, x, y) tuples.
                        Operations will modify a copy unless otherwise specified.
        """
        # Store a working copy to avoid modifying the original list directly
        # unless an in-place modification method is explicitly called.
        self._curve_data: List[Tuple[int, float, float]] = list(curve_data)
        self._original_data: Sequence[Tuple[int, float, float]] = curve_data # Keep a reference if needed for comparison

    def get_data(self) -> List[Tuple[int, float, float]]:
        """Returns the current state of the curve data being operated on."""
        return copy.deepcopy(self._curve_data) # Return a copy

    # --- Smoothing Methods ---
    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """Apply moving average smoothing to the specified points."""
        if not indices or window_size < 3:
            return # No change if invalid input

        # Operate on the internal copy
        original_data = copy.deepcopy(self._curve_data) # Need original for calculations
        result_data = self._curve_data # Modify internal state directly

        half_window = window_size // 2

        for idx in indices:
            if not (0 <= idx < len(original_data)):
                continue # Skip invalid indices

            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)

            if end_idx - start_idx < 2: # Need at least 3 points in window
                continue

            _, x, y = original_data[idx]
            sum_x: float = 0.0
            sum_y: float = 0.0
            count = 0

            for i in range(start_idx, end_idx + 1):
                _, x, y = original_data[i]
                sum_x += x
                sum_y += y
                count += 1

            if count > 0:
                avg_x = sum_x / count
                avg_y = sum_y / count
                result_data[idx] = (_, avg_x, avg_y)
        # self._curve_data is modified in place

    def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
        """Apply Gaussian smoothing to the specified points."""
        if not indices or window_size < 3 or sigma <= 0:
            return # No change if invalid input

        original_data = copy.deepcopy(self._curve_data)
        result_data = self._curve_data

        half_window = window_size // 2

        # Create Gaussian weights
        weights: List[float] = []
        weight_sum: float = 0.0
        for i in range(-half_window, half_window + 1):
            weight = math.exp(-(i**2) / (2 * sigma**2))
            weights.append(weight)
            weight_sum += weight

        if weight_sum <= 1e-10: # Avoid division by zero
             return # Cannot normalize weights

        weights = [w / weight_sum for w in weights]

        for idx in indices:
            if not (0 <= idx < len(original_data)):
                continue

            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)

            if end_idx - start_idx < 2:
                continue

            _, x, y = original_data[idx]
            weighted_x: float = 0.0
            weighted_y: float = 0.0
            actual_weight_sum: float = 0.0

            for i, w_idx in enumerate(range(start_idx, end_idx + 1)):
                weight_idx = i + (start_idx - (idx - half_window))
                if 0 <= weight_idx < len(weights):
                    _, x, y = original_data[w_idx]
                    weight = weights[weight_idx]
                    weighted_x += x * weight
                    weighted_y += y * weight
                    actual_weight_sum += weight

            if actual_weight_sum > 1e-10:
                weighted_x /= actual_weight_sum
                weighted_y /= actual_weight_sum
                result_data[idx] = (_, weighted_x, weighted_y)
        # self._curve_data is modified in place

    def smooth_savitzky_golay(self, indices: List[int], window_size: int) -> None:
        """Apply Savitzky-Golay smoothing to the specified points."""
        if not indices or window_size < 5 or window_size % 2 == 0: # Need odd window >= 5
            return # No change if invalid input

        original_data = copy.deepcopy(self._curve_data)
        result_data = self._curve_data

        half_window = window_size // 2

        for idx in indices:
            if not (0 <= idx < len(original_data)):
                continue

            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)

            # Need at least window_size points for the fit
            if end_idx - start_idx + 1 < window_size:
                continue

            _, x, y = original_data[idx]

            # Get points in window
            x_points: List[float] = []
            y_points: List[float] = []
            window_indices = list(range(start_idx, end_idx + 1)) # Indices within original_data
            relative_indices = list(range(len(window_indices))) # 0-based indices for fitting

            for i in window_indices:
                _, x, y = original_data[i]
                x_points.append(x)
                y_points.append(y)

            # Calculate relative position in window (0-based)
            rel_pos = idx - start_idx

            # Apply fit
            x_new = self._savitzky_golay_fit(relative_indices, x_points, rel_pos)
            y_new = self._savitzky_golay_fit(relative_indices, y_points, rel_pos)

            if x_new is not None and y_new is not None:
                result_data[idx] = (_, x_new, y_new)
        # self._curve_data is modified in place

    # --- Filtering Methods ---
    def filter_median(self, indices: List[int], window_size: int) -> None:
        """Apply median filter to the specified points."""
        if not indices or window_size < 3 or window_size % 2 == 0: # Need odd window >= 3
             return # No change if invalid input

        original_data = copy.deepcopy(self._curve_data)
        result_data = self._curve_data

        half_window = window_size // 2

        for idx in indices:
            if not (0 <= idx < len(original_data)):
                continue

            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)

            # Ensure the window has at least the minimum size centered around idx
            actual_window_size = end_idx - start_idx + 1
            if actual_window_size < 3:
                continue

            _, x, y = original_data[idx]

            # Collect x and y values in the window
            x_values = [original_data[i][1] for i in range(start_idx, end_idx + 1)]
            y_values = [original_data[i][2] for i in range(start_idx, end_idx + 1)]

            # Sort and get median
            x_values.sort()
            y_values.sort()

            median_x = x_values[len(x_values) // 2]
            median_y = y_values[len(y_values) // 2]

            # Update point
            result_data[idx] = (_, median_x, median_y)
        # self._curve_data is modified in place

    def filter_butterworth(self, indices: List[int], cutoff: float, order: int) -> None:
        """Apply Butterworth low-pass filter to the specified points."""
        if not indices or len(indices) < 3 or not (0 < cutoff < 1) or order < 1:
             return # No change if invalid input

        # Need a copy as Butterworth modifies based on the whole sequence range
        original_data = copy.deepcopy(self._curve_data)
        result_data = self._curve_data # We'll update this in place for the specified indices

        # Get indices range to operate on the continuous segment containing the indices
        # Ensure indices are valid before proceeding
        if not all(0 <= i < len(original_data) for i in indices):
             print("Warning: Some indices for Butterworth filter are out of bounds.")
             return # Cannot proceed safely

        min_idx = min(indices)
        max_idx = max(indices)

        # Extract x and y sequences for the relevant range
        frames_in_range: List[int] = []
        x_values_in_range: List[float] = []
        y_values_in_range: List[float] = []

        # Iterate through the valid range based on min/max of provided indices
        for i in range(min_idx, max_idx + 1):
             # We already checked indices are valid, so direct access should be safe
             # but double-check length just in case curve_data was modified externally
             if i < len(original_data):
                 _, x, y = original_data[i]
                 frames_in_range.append(_)
                 x_values_in_range.append(x)
                 y_values_in_range.append(y)
             else:
                 print(f"Warning: Index {i} out of bounds during Butterworth data extraction.")
                 return # Cannot proceed safely

        if len(x_values_in_range) < 3: # Need enough points for filtering
             return

        # Apply the filter to x and y sequences separately
        filtered_x = self._butterworth_filter(x_values_in_range, cutoff, order)
        filtered_y = self._butterworth_filter(y_values_in_range, cutoff, order)

        # Update only the requested indices within the result_data
        indices_set = set(indices) # Faster lookup
        for i, original_idx in enumerate(range(min_idx, max_idx + 1)):
             if original_idx in indices_set:
                 # Ensure we have corresponding filtered data and original_idx is valid
                 if i < len(filtered_x) and i < len(filtered_y) and original_idx < len(result_data):
                     _, x, y = original_data[original_idx]
                     result_data[original_idx] = (_, filtered_x[i], filtered_y[i])
                 else:
                      print(f"Warning: Mismatch or invalid index during Butterworth update at index {original_idx}.")
                      # Decide how to handle: skip, error, etc. Skipping for now.
                      continue
        # self._curve_data is modified in place for the specified indices

    # --- Gap Filling Methods ---
    def fill_linear(self, start_frame: int, end_frame: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap using linear interpolation."""
        # Use internal data copy
        current_data = self._curve_data
        if not current_data: return

        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(current_data)}
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f > end_frame]

        if not before_points or not after_points:
            print("Warning: Cannot interpolate without points on both sides of the gap.")
            return # Cannot interpolate

        before_points.sort(key=lambda p: p[1], reverse=True) # Closest frame before start_frame
        after_points.sort(key=lambda p: p[1]) # Closest frame after end_frame

        _, b_frame, b_x, b_y = before_points[0]
        _, a_frame, a_x, a_y = after_points[0]

        new_points: List[Tuple[int, float, float]] = []
        frame_diff = a_frame - b_frame
        if frame_diff <= 0:
             print("Warning: Invalid frame boundaries for linear fill.")
             return # Avoid division by zero or invalid range

        for frame in range(start_frame, end_frame + 1):
            if frame in frame_map and preserve_endpoints:
                continue

            t = (frame - b_frame) / frame_diff
            x = b_x + (a_x - b_x) * t
            y = b_y + (a_y - b_y) * t
            new_points.append((frame, x, y))

        self._add_points_and_sort(new_points)
        # self._curve_data is modified in place by _add_points_and_sort

    def fill_cubic_spline(self, start_frame: int, end_frame: int, tension: float, preserve_endpoints: bool = True) -> None:
        """Fill a gap using cubic spline interpolation (Catmull-Rom like)."""
        current_data = self._curve_data
        if not current_data: return

        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(current_data)}
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f > end_frame]

        # Need at least 2 points on each side for cubic interpolation control points
        if len(before_points) < 2 or len(after_points) < 2:
            print("Warning: Not enough points for cubic spline, falling back to linear.")
            self.fill_linear(start_frame, end_frame, preserve_endpoints) # Call self method
            return

        before_points.sort(key=lambda p: p[1], reverse=True)
        after_points.sort(key=lambda p: p[1])

        # Control points: p0 (before[1]), p1 (before[0]), p2 (after[0]), p3 (after[1])
        p0 = (before_points[1][2], before_points[1][3])
        p1 = (before_points[0][2], before_points[0][3])
        p2 = (after_points[0][2], after_points[0][3])
        p3 = (after_points[1][2], after_points[1][3])

        # Frames corresponding to p1 and p2
        f1 = before_points[0][1]
        f2 = after_points[0][1]
        frame_diff_segment = f2 - f1
        if frame_diff_segment <= 0:
             print("Warning: Invalid frame boundaries for cubic spline segment.")
             return

        new_points: List[Tuple[int, float, float]] = []
        for frame in range(start_frame, end_frame + 1):
            if frame in frame_map and preserve_endpoints:
                continue

            # Normalize parameter t within the segment [f1, f2]
            t = (frame - f1) / frame_diff_segment

            # Catmull-Rom spline calculation (simplified, adjust tension if needed)
            t2 = t * t
            t3 = t2 * t

            # Basis functions (adjust based on desired spline type if not Catmull-Rom)
            h1 = -0.5*t3 + t2 - 0.5*t
            h2 = 1.5*t3 - 2.5*t2 + 1.0
            h3 = -1.5*t3 + 2.0*t2 + 0.5*t
            h4 = 0.5*t3 - 0.5*t2

            # Calculate interpolated point
            x = h1*p0[0] + h2*p1[0] + h3*p2[0] + h4*p3[0]
            y = h1*p0[1] + h2*p1[1] + h3*p2[1] + h4*p3[1]

            new_points.append((frame, x, y))

        self._add_points_and_sort(new_points)

    def fill_constant_velocity(self, start_frame: int, end_frame: int, window_size: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap assuming constant velocity based on surrounding frames."""
        current_data = self._curve_data
        if not current_data: return

        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(current_data)}
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f > end_frame]

        # Need at least window_size points on each side to calculate average velocity
        if len(before_points) < window_size or len(after_points) < window_size:
            print(f"Warning: Not enough points ({len(before_points)} before, {len(after_points)} after) for constant velocity (need {window_size}), falling back to linear.")
            self.fill_linear(start_frame, end_frame, preserve_endpoints)
            return

        before_points.sort(key=lambda p: p[1], reverse=True)
        after_points.sort(key=lambda p: p[1])

        # Calculate average velocity from before points
        b_velocities_x: List[float] = []
        b_velocities_y: List[float] = []
        for i in range(window_size - 1):
            _, f, x, y = before_points[i]
            _, f_next, x_next, y_next = before_points[i+1]
            frame_diff = f - f_next
            if frame_diff > 0:
                b_velocities_x.append((x - x_next) / frame_diff)
                b_velocities_y.append((y - y_next) / frame_diff)
        b_velocity_x = sum(b_velocities_x) / len(b_velocities_x) if b_velocities_x else 0
        b_velocity_y = sum(b_velocities_y) / len(b_velocities_y) if b_velocities_y else 0


        # Calculate average velocity from after points
        a_velocities_x: List[float] = []
        a_velocities_y: List[float] = []
        for i in range(window_size - 1):
            _, f, x, y = after_points[i]
            _, f_next, x_next, y_next = after_points[i+1]
            frame_diff = f_next - f
            if frame_diff > 0:
                a_velocities_x.append((x_next - x) / frame_diff)
                a_velocities_y.append((y_next - y) / frame_diff)
        a_velocity_x = sum(a_velocities_x) / len(a_velocities_x) if a_velocities_x else 0
        a_velocity_y = sum(a_velocities_y) / len(a_velocities_y) if a_velocities_y else 0

        # Average the before and after velocities
        velocity_x = (b_velocity_x + a_velocity_x) / 2
        velocity_y = (b_velocity_y + a_velocity_y) / 2

        # Get the point just before the gap
        _, b_frame, b_x, b_y = before_points[0]

        new_points: List[Tuple[int, float, float]] = []
        for frame in range(start_frame, end_frame + 1):
            if frame in frame_map and preserve_endpoints:
                continue

            steps = frame - b_frame
            x = b_x + velocity_x * steps
            y = b_y + velocity_y * steps
            new_points.append((frame, x, y))

        self._add_points_and_sort(new_points)

    def fill_accelerated_motion(self, start_frame: int, end_frame: int, window_size: int, accel_weight: float, preserve_endpoints: bool = True) -> None:
        """Fill a gap using accelerated motion based on surrounding frames."""
        current_data = self._curve_data
        if not current_data: return

        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(current_data)}
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f > end_frame]

        # Need at least window_size points on each side
        if len(before_points) < window_size or len(after_points) < window_size:
            print(f"Warning: Not enough points for accelerated motion (need {window_size}), falling back to constant velocity.")
            # Fallback requires calling the method on self
            self.fill_constant_velocity(start_frame, end_frame, window_size, preserve_endpoints)
            return

        before_points.sort(key=lambda p: p[1], reverse=True)
        after_points.sort(key=lambda p: p[1])

        # Calculate average velocity from before points (same as constant velocity)
        b_velocities_x: List[float] = []
        b_velocities_y: List[float] = []
        for i in range(window_size - 1):
            _, f, x, y = before_points[i]
            _, f_next, x_next, y_next = before_points[i+1]
            frame_diff = f - f_next
            if frame_diff > 0:
                b_velocities_x.append((x - x_next) / frame_diff)
                b_velocities_y.append((y - y_next) / frame_diff)
        b_velocity_x = sum(b_velocities_x) / len(b_velocities_x) if b_velocities_x else 0
        b_velocity_y = sum(b_velocities_y) / len(b_velocities_y) if b_velocities_y else 0

        # Calculate average velocity from after points (same as constant velocity)
        a_velocities_x: List[float] = []
        a_velocities_y: List[float] = []
        for i in range(window_size - 1):
            _, f, x, y = after_points[i]
            _, f_next, x_next, y_next = after_points[i+1]
            frame_diff = f_next - f
            if frame_diff > 0:
                a_velocities_x.append((x_next - x) / frame_diff)
                a_velocities_y.append((y_next - y) / frame_diff)
        a_velocity_x = sum(a_velocities_x) / len(a_velocities_x) if a_velocities_x else 0
        a_velocity_y = sum(a_velocities_y) / len(a_velocities_y) if a_velocities_y else 0

        # Calculate acceleration (difference in velocities over the gap duration)
        # Use frames closest to the gap for duration calculation
        b_frame_edge = before_points[0][1]
        a_frame_edge = after_points[0][1]
        duration = a_frame_edge - b_frame_edge # Duration over which velocity changes
        if duration <= 0:
             accel_x, accel_y = 0.0, 0.0 # Avoid division by zero, assume no acceleration
        else:
             accel_x = (a_velocity_x - b_velocity_x) / duration
             accel_y = (a_velocity_y - b_velocity_y) / duration

        # Apply accel_weight
        accel_x *= accel_weight
        accel_y *= accel_weight

        # Get the point just before the gap
        _, b_frame, b_x, b_y = before_points[0]

        new_points: List[Tuple[int, float, float]] = []
        for frame in range(start_frame, end_frame + 1):
            if frame in frame_map and preserve_endpoints:
                continue

            steps = frame - b_frame # Time elapsed since the start of the gap fill (relative to b_frame)
            # Kinematic equation: pos = initial_pos + initial_vel * time + 0.5 * accel * time^2
            x = b_x + b_velocity_x * steps + 0.5 * accel_x * steps * steps
            y = b_y + b_velocity_y * steps + 0.5 * accel_y * steps * steps
            new_points.append((frame, x, y))

        self._add_points_and_sort(new_points)

    def fill_average(self, start_frame: int, end_frame: int, window_size: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap by averaging neighboring frames."""
        current_data = self._curve_data
        if not current_data: return

        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(current_data)}
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(current_data) if f > end_frame]

        if not before_points or not after_points:
            print("Warning: Not enough points for average fill, falling back to linear.")
            self.fill_linear(start_frame, end_frame, preserve_endpoints)
            return

        before_points.sort(key=lambda p: p[1], reverse=True)
        after_points.sort(key=lambda p: p[1])

        # Get points to use for averaging
        before_window = before_points[:min(window_size, len(before_points))]
        after_window = after_points[:min(window_size, len(after_points))]

        # Calculate average positions
        avg_before_x = sum(p[2] for p in before_window) / len(before_window)
        avg_before_y = sum(p[3] for p in before_window) / len(before_window)
        avg_after_x = sum(p[2] for p in after_window) / len(after_window)
        avg_after_y = sum(p[3] for p in after_window) / len(after_window)

        new_points: List[Tuple[int, float, float]] = []
        # Use frames closest to the gap for weighting calculation
        b_frame_edge = before_points[0][1]
        a_frame_edge = after_points[0][1]
        total_gap_frames = a_frame_edge - b_frame_edge # Use edge frames for weight span
        if total_gap_frames <= 0: total_gap_frames = 1 # Avoid division by zero

        for frame in range(start_frame, end_frame + 1):
            if frame in frame_map and preserve_endpoints:
                continue

            # Calculate weight based on relative position between edge frames
            t = (frame - b_frame_edge) / total_gap_frames
            t = max(0.0, min(1.0, t)) # Clamp weight between 0 and 1

            # Weighted average
            x = avg_before_x * (1 - t) + avg_after_x * t
            y = avg_before_y * (1 - t) + avg_after_y * t
            new_points.append((frame, x, y))

        self._add_points_and_sort(new_points)

    # --- Extrapolation Methods ---
    def extrapolate_forward(self, num_frames: int, method: int, fit_points: int = 5) -> None:
        """Extrapolate curve forward by num_frames using the specified method."""
        current_data = self._curve_data
        if not current_data or num_frames <= 0:
            return # No change

        # Assume data is sorted (maintained by _add_points_and_sort)
        sorted_data = current_data

        if not sorted_data: return # Should not happen if check above passed, but safety check

        last_frame = sorted_data[-1][0]
        points_to_use = sorted_data[-min(fit_points, len(sorted_data)):]

        extrapolated: List[Tuple[int, float, float]] = []

        if method == 0:  # Linear
            if len(points_to_use) < 2: return
            _, x1, y1 = points_to_use[-2]
            _, x2, y2 = points_to_use[-1]
            frame_diff = _ - _
            if frame_diff <= 0: return # Avoid division by zero or invalid direction

            dx = (x2 - x1) / frame_diff
            dy = (y2 - y1) / frame_diff

            for i in range(1, num_frames + 1):
                new_frame = last_frame + i
                new_x = x2 + dx * i
                new_y = y2 + dy * i
                extrapolated.append((new_frame, new_x, new_y))

        elif method == 1:  # Last Velocity
            if len(points_to_use) < 2: return
            velocities_x: List[float] = []
            velocities_y: List[float] = []
            for i in range(1, len(points_to_use)):
                _, x1, y1 = points_to_use[i-1]
                _, x2, y2 = points_to_use[i]
                frame_diff = _ - _
                if frame_diff > 0:
                    velocities_x.append((x2 - x1) / frame_diff)
                    velocities_y.append((y2 - y1) / frame_diff)

            if not velocities_x: return # Cannot calculate velocity
            avg_dx = sum(velocities_x) / len(velocities_x)
            avg_dy = sum(velocities_y) / len(velocities_y)

            _, x, y = points_to_use[-1]
            for i in range(1, num_frames + 1):
                new_frame = last_frame + i
                new_x = x + avg_dx * i
                new_y = y + avg_dy * i
                extrapolated.append((new_frame, new_x, new_y))

        elif method == 2:  # Quadratic
            if len(points_to_use) < 3: return
            frames = [p[0] for p in points_to_use]
            xs = [p[1] for p in points_to_use]
            ys = [p[2] for p in points_to_use]
            min_frame = min(frames)
            normalized_frames = [f - min_frame for f in frames]

            # Use the internal helper method
            x_coeffs = self._fit_quadratic(normalized_frames, xs)
            y_coeffs = self._fit_quadratic(normalized_frames, ys)

            if not x_coeffs or not y_coeffs: return # Fit failed

            for i in range(1, num_frames + 1):
                new_frame = last_frame + i
                normalized_new_frame = new_frame - min_frame
                # Ensure coeffs has 3 elements before accessing index 2
                if len(x_coeffs) == 3 and len(y_coeffs) == 3:
                     new_x = x_coeffs[0] + x_coeffs[1] * normalized_new_frame + x_coeffs[2] * normalized_new_frame**2
                     new_y = y_coeffs[0] + y_coeffs[1] * normalized_new_frame + y_coeffs[2] * normalized_new_frame**2
                     extrapolated.append((new_frame, new_x, new_y))
                else:
                     print("Warning: Quadratic fit returned unexpected number of coefficients.")
                     return # Fit failed

        # Add extrapolated points using the internal helper
        self._add_points_and_sort(extrapolated)
        # self._curve_data is modified in place

    def extrapolate_backward(self, num_frames: int, method: int, fit_points: int = 5) -> None:
        """Extrapolate curve backward by num_frames using the specified method."""
        current_data = self._curve_data
        if not current_data or num_frames <= 0:
            return # No change

        # Assume data is sorted
        sorted_data = current_data
        if not sorted_data: return

        first_frame = sorted_data[0][0]
        points_to_use = sorted_data[:min(fit_points, len(sorted_data))]

        extrapolated: List[Tuple[int, float, float]] = []

        if method == 0:  # Linear
            if len(points_to_use) < 2: return
            _, x1, y1 = points_to_use[0]
            _, x2, y2 = points_to_use[1]
            frame_diff = _ - _
            if frame_diff <= 0: return

            dx = (x2 - x1) / frame_diff
            dy = (y2 - y1) / frame_diff

            for i in range(1, num_frames + 1):
                new_frame = first_frame - i
                new_x = x1 - dx * i
                new_y = y1 - dy * i
                extrapolated.append((new_frame, new_x, new_y))

        elif method == 1:  # First Velocity
            if len(points_to_use) < 2: return
            velocities_x: List[float] = []
            velocities_y: List[float] = []
            for i in range(len(points_to_use) - 1):
                _, x1, y1 = points_to_use[i]
                _, x2, y2 = points_to_use[i+1]
                frame_diff = _ - _
                if frame_diff > 0:
                    velocities_x.append((x2 - x1) / frame_diff)
                    velocities_y.append((y2 - y1) / frame_diff)

            if not velocities_x: return
            avg_dx = sum(velocities_x) / len(velocities_x)
            avg_dy = sum(velocities_y) / len(velocities_y)

            _, x, y = points_to_use[0]
            for i in range(1, num_frames + 1):
                new_frame = first_frame - i
                new_x = x - avg_dx * i
                new_y = y - avg_dy * i
                extrapolated.append((new_frame, new_x, new_y))

        elif method == 2:  # Quadratic
            if len(points_to_use) < 3: return
            frames = [p[0] for p in points_to_use]
            xs = [p[1] for p in points_to_use]
            ys = [p[2] for p in points_to_use]
            min_frame = min(frames)
            normalized_frames = [f - min_frame for f in frames]

            x_coeffs = self._fit_quadratic(normalized_frames, xs)
            y_coeffs = self._fit_quadratic(normalized_frames, ys)

            if not x_coeffs or not y_coeffs: return

            for i in range(1, num_frames + 1):
                new_frame = first_frame - i
                normalized_new_frame = new_frame - min_frame
                if len(x_coeffs) == 3 and len(y_coeffs) == 3:
                     new_x = x_coeffs[0] + x_coeffs[1] * normalized_new_frame + x_coeffs[2] * normalized_new_frame**2
                     new_y = y_coeffs[0] + y_coeffs[1] * normalized_new_frame + y_coeffs[2] * normalized_new_frame**2
                     extrapolated.append((new_frame, new_x, new_y))
                else:
                     print("Warning: Quadratic fit returned unexpected number of coefficients.")
                     return # Fit failed


        self._add_points_and_sort(extrapolated)
        # self._curve_data is modified in place

    # --- Batch Transformation Methods (Consider moving from batch_edit.py) ---
    def scale_points(self, indices: List[int], scale_x: float, scale_y: float, center_x: Optional[float] = None, center_y: Optional[float] = None) -> None:
        """Scale multiple points."""
        # TODO: Consider moving logic from batch_edit.py
        pass

    def offset_points(self, indices: List[int], offset_x: float, offset_y: float) -> None:
        """Offset multiple points."""
        # TODO: Consider moving logic from batch_edit.py
        pass

    def rotate_points(self, indices: List[int], angle_degrees: float, center_x: Optional[float] = None, center_y: Optional[float] = None) -> None:
        """Rotate multiple points."""
        # TODO: Consider moving logic from batch_edit.py
        pass

    # --- Helper/Utility Methods ---
    def _add_points_and_sort(self, new_points: List[Tuple[int, float, float]]) -> None:
        """Internal helper to add points and maintain sorted order."""
        # Create frame map for easy reference of existing points in self._curve_data
        # Ensure we handle potential duplicate frames in the initial data if any exist
        # Taking the last occurrence in case of duplicates during enumeration
        points_map = {frame: (frame, x, y) for _, (frame, x, y) in enumerate(self._curve_data)}

        # Add or update points from new_points, overwriting existing frames
        for frame, x, y in new_points:
            points_map[frame] = (frame, x, y)

        # Convert back to sorted list based on frame numbers
        sorted_data = [points_map[frame] for frame in sorted(points_map.keys())]

        # Update internal curve_data in-place
        self._curve_data.clear()
        self._curve_data.extend(sorted_data)

    def _savitzky_golay_fit(self, x_indices: List[int], values: List[float], target_idx: int) -> Optional[float]:
        """Fit a quadratic polynomial to the data and evaluate at target index."""
        n = len(values)
        if n < 3:
            return values[target_idx] if 0 <= target_idx < n else None # Indicate failure

        # Calculate sums for least squares fitting
        sum_x = sum(x_indices)
        sum_x2 = sum(x*x for x in x_indices)
        sum_x3 = sum(x*x*x for x in x_indices)
        sum_x4 = sum(x*x*x*x for x in x_indices)

        sum_y = sum(values)
        sum_xy = sum(x*y for x, y in zip(x_indices, values))
        sum_x2y = sum(x*x*y for x, y in zip(x_indices, values))

        # Set up matrix for quadratic fit: y = a + bx + cx^2
        # Using formula for determinant of 3x3 matrix for Vandermonde-like system
        # omega_c = tan(pi * cutoff) # Bilinear transform adjustment (approx)
        # alpha = (1 - sin(omega_c)) / cos(omega_c) # Simplified 1st order relation
        # Let's try a simpler heuristic based on exponential decay:
        determinant = n*sum_x2*sum_x4 + sum_x*sum_x3*sum_x2 + sum_x2*sum_x*sum_x3 - \
                     sum_x2*sum_x2*sum_x2 - sum_x*sum_x*sum_x4 - n*sum_x3*sum_x3

        if abs(determinant) < 1e-10:  # Nearly singular matrix
            return values[target_idx] if 0 <= target_idx < n else None # Fallback or indicate failure

        # Calculate coefficients using Cramer's rule (or matrix inversion formulas)
        a = (sum_y*(sum_x2*sum_x4 - sum_x3*sum_x3) - sum_xy*(sum_x*sum_x4 - sum_x2*sum_x3) + sum_x2y*(sum_x*sum_x3 - sum_x2*sum_x2)) / determinant
        b = (n*(sum_xy*sum_x4 - sum_x2y*sum_x3) - sum_x*(sum_y*sum_x4 - sum_x2y*sum_x2) + sum_x2*(sum_y*sum_x3 - sum_xy*sum_x2)) / determinant
        c = (n*(sum_x2*sum_x2y - sum_x3*sum_xy) - sum_x*(sum_x*sum_x2y - sum_x2*sum_xy) + sum_x2*(sum_x*sum_xy - sum_x2*sum_y)) / determinant

        # Evaluate polynomial at target index
        target_x = x_indices[target_idx] if 0 <= target_idx < n else 0 # Use 0 if index out of bounds? Or handle error?
        if not (0 <= target_idx < n):
             return None # Indicate failure if target index is invalid

        return a + b*target_x + c*target_x*target_x

    def _butterworth_filter(self, data: List[float], cutoff: float, order: int) -> List[float]:
        """Apply Butterworth low-pass filter to a 1D sequence (simplified)."""
        if not data or len(data) < 2:
            return data # Return original if not enough data

        # Simplified implementation (not a true multi-pole Butterworth)
        # This uses exponential moving average forward and backward pass (like filtfilt)
        n = len(data)
        output = [0.0] * n # Use floats for calculations

        # Calculate alpha based on cutoff frequency (approximate)
        # A lower cutoff means more smoothing (smaller alpha)
        # Higher order makes the transition sharper (alpha closer to 0 or 1)
        # This formula is a simplification. Real Butterworth requires filter design.
        try:
            # Avoid potential math domain errors with cutoff near 0 or 1
            if cutoff <= 1e-6: # Use a small epsilon
                 alpha = 0.0 # Max filtering
            elif cutoff >= 1.0 - 1e-6:
                 alpha = 1.0 # No filtering
            else:
                 # Simple approximation, adjust exponent as needed for desired response
                 # Using a formula related to EMA time constant and cutoff frequency
                 # omega_c = tan(pi * cutoff) # Bilinear transform adjustment (approx)
                 # alpha = (1 - sin(omega_c)) / cos(omega_c) # Simplified 1st order relation
                 # Let's try a simpler heuristic based on exponential decay:
                 decay = math.exp(-math.pi * cutoff * math.sqrt(2)) # Approx decay for Butterworth-like response
                 alpha = 1.0 - decay
                 alpha = max(0.0, min(1.0, alpha)) # Clamp between 0 and 1

        except (OverflowError, ValueError):
             alpha = 0.0 # Max filtering if calculation fails

        if abs(alpha - 1.0) < 1e-10: # Almost no filtering
             return [float(d) for d in data] # Ensure float output

        # Forward pass (EMA)
        output[0] = float(data[0])
        for i in range(1, n):
            output[i] = alpha * float(data[i]) + (1.0 - alpha) * output[i-1]

        # Backward pass (EMA) - modifies 'output' in place
        # Initialize last element for backward pass
        # output[n-1] remains as is from the forward pass for the first step
        # Need to be careful with the backward pass initialization if data length is 1
        if n > 1:
             # The last value from forward pass is the starting point for backward
             # output[n-1] = output[n-1] # No change needed for the last element itself in backward pass start
             for i in range(n-2, -1, -1):
                 output[i] = alpha * output[i] + (1.0 - alpha) * output[i+1]
        # else: output[0] is already set

        return output

    def _fit_quadratic(self, x: Sequence[float], y: Sequence[float]) -> Optional[List[float]]:
        """Fit a quadratic polynomial (ax^2 + bx + c) to the given data points."""
        # This is the implementation moved from curve_operations.fit_quadratic
        if len(x) != len(y) or len(x) < 3:
            return None # Cannot fit with less than 3 points

        n = len(x)

        # Calculate sums needed for the normal equations of least squares
        sum_x = sum(x)
        sum_x2 = sum(xi**2 for xi in x)
        sum_x3 = sum(xi**3 for xi in x)
        sum_x4 = sum(xi**4 for xi in x)

        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2y = sum(xi**2 * yi for xi, yi in zip(x, y))

        # Set up the system matrix (A) and vector (b) for Ax = b
        # Where x = [c, b, a] for y = c + bx + ax^2
        A = [
            [float(n), float(sum_x), float(sum_x2)],
            [float(sum_x), float(sum_x2), float(sum_x3)],
            [float(sum_x2), float(sum_x3), float(sum_x4)]
        ]
        b_vec = [float(sum_y), float(sum_xy), float(sum_x2y)]

        # Solve using Gaussian elimination (simple implementation)
        # Forward elimination
        for i in range(3):
            # Find pivot
            max_row = i
            for k in range(i + 1, 3):
                if abs(A[k][i]) > abs(A[max_row][i]):
                    max_row = k
            # Swap rows
            A[i], A[max_row] = A[max_row], A[i]
            b_vec[i], b_vec[max_row] = b_vec[max_row], b_vec[i]

            # Check for singular matrix
            if abs(A[i][i]) < 1e-10:
                print("Warning: Singular matrix encountered during quadratic fit.")
                return None

            # Eliminate column i
            for k in range(i + 1, 3):
                # Check for division by zero before calculating factor
                if abs(A[i][i]) < 1e-10:
                     print("Warning: Near-zero pivot encountered during elimination.")
                     return None # Avoid division by zero
                factor = A[k][i] / A[i][i]
                b_vec[k] -= factor * b_vec[i]
                for j in range(i, 3):
                    A[k][j] -= factor * A[i][j]

        # Back substitution
        coeffs = [0.0, 0.0, 0.0] # c, b, a
        for i in range(2, -1, -1):
            sum_ax = 0.0
            for j in range(i + 1, 3):
                sum_ax += A[i][j] * coeffs[j]
            # Check for division by zero again
            if abs(A[i][i]) < 1e-10:
                 print("Warning: Division by zero during back substitution in quadratic fit.")
                 return None
            coeffs[i] = (b_vec[i] - sum_ax) / A[i][i]

        # Return coefficients in order [c, b, a] corresponding to y = c + bx + ax^2
        return coeffs

    # ... other potential private helpers ...

# Example Usage (for testing/demonstration)
if __name__ == '__main__':
    sample_data = [(i, float(i * 2), float(i * i)) for i in range(10)]
    sample_data.extend([(i, float(i * 2), float(i * i)) for i in range(15, 25)]) # Add a gap

    ops = CurveDataOperations(sample_data)

    # Example: Smooth a range
    ops.smooth_gaussian(indices=list(range(5, 9)), window_size=5, sigma=1.0)
    smoothed_data = ops.get_data()
    print("Smoothed Data:", smoothed_data)

    # Example: Fill a gap
    ops_fill = CurveDataOperations(sample_data) # Use fresh instance for fill
    ops_fill.fill_linear(start_frame=10, end_frame=14)
    filled_data = ops_fill.get_data()
    print("\nFilled Data:", filled_data)