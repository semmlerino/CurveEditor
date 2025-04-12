#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import copy

def apply_smoothing_filtering(curve_data, indices, method, **params):
    """
    Unified dispatcher for smoothing and filtering operations.
    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to operate on
        method: String identifier for the method (e.g., 'moving_average', 'gaussian', 'savitzky_golay', 'median', 'butterworth', 'average')
        params: Additional parameters for the method
    Returns:
        Modified curve_data with smoothing/filtering applied to the specified indices.
    """
    method = method.lower()
    if method in ("moving_average", "average"):
        window_size = params.get("window_size", 5)
        return smooth_moving_average(curve_data, indices, window_size)
    elif method == "gaussian":
        window_size = params.get("window_size", 5)
        sigma = params.get("sigma", 1.0)
        return smooth_gaussian(curve_data, indices, window_size, sigma)
    elif method == "savitzky_golay":
        window_size = params.get("window_size", 5)
        return smooth_savitzky_golay(curve_data, indices, window_size)
    elif method == "median":
        window_size = params.get("window_size", 5)
        return CurveOperations.filter_median(curve_data, indices, window_size)
    elif method == "butterworth":
        cutoff = params.get("cutoff", 0.2)
        order = params.get("order", 2)
        return filter_butterworth(curve_data, indices, cutoff, order)
    elif method == "filter_average":
        window_size = params.get("window_size", 5)
        return filter_average(curve_data, indices, window_size)
    elif method == "filter_gaussian":
        window_size = params.get("window_size", 5)
        sigma = params.get("sigma", 1.0)
        return filter_gaussian(curve_data, indices, window_size, sigma)
    else:
        raise ValueError(f"Unknown smoothing/filtering method: {method}")


def smooth_moving_average(curve_data, indices, window_size):
    """Apply moving average smoothing to the specified points."""
    if not indices or window_size < 3:
        return curve_data
        
    # Create a copy of the curve data for reading and writing
    result = copy.deepcopy(curve_data)
    original_data = copy.deepcopy(curve_data)
    
    # Calculate half window size
    half_window = window_size // 2
    
    # Apply smoothing
    for idx in indices:
        # Calculate window indices
        start_idx = max(0, idx - half_window)
        end_idx = min(len(original_data) - 1, idx + half_window)
        
        # Skip if we don't have enough points
        if end_idx - start_idx < 2:
            continue
            
        # Get frame
        frame = original_data[idx][0]
        
        # Calculate average
        sum_x = 0
        sum_y = 0
        count = 0
        
        for i in range(start_idx, end_idx + 1):
            _, x, y = original_data[i]
            sum_x += x
            sum_y += y
            count += 1
            
        avg_x = sum_x / count
        avg_y = sum_y / count
        
        # Update point
        result[idx] = (frame, avg_x, avg_y)
        
    return result

def smooth_gaussian(curve_data, indices, window_size, sigma):
    """Apply Gaussian smoothing to the specified points."""
    if not indices or window_size < 3:
        return curve_data
        
    # Create a copy of the curve data for reading and writing
    result = copy.deepcopy(curve_data)
    original_data = copy.deepcopy(curve_data)
    
    # Calculate half window size
    half_window = window_size // 2
    
    # Create Gaussian weights
    weights = []
    weight_sum = 0
    
    for i in range(-half_window, half_window + 1):
        weight = math.exp(-(i**2) / (2 * sigma**2))
        weights.append(weight)
        weight_sum += weight
        
    # Normalize weights
    weights = [w / weight_sum for w in weights]
    
    # Apply smoothing
    for idx in indices:
        # Calculate window indices
        start_idx = max(0, idx - half_window)
        end_idx = min(len(original_data) - 1, idx + half_window)
        
        # Skip if we don't have enough points
        if end_idx - start_idx < 2:
            continue
            
        # Get frame
        frame = original_data[idx][0]
        
        # Calculate weighted average
        weighted_x = 0
        weighted_y = 0
        actual_weight_sum = 0
        
        for i, w_idx in enumerate(range(start_idx, end_idx + 1)):
            # Get shifted weight index
            weight_idx = i + (start_idx - (idx - half_window))
            if weight_idx < 0 or weight_idx >= len(weights):
                continue
                
            # Apply weight
            _, x, y = original_data[w_idx]
            weight = weights[weight_idx]
            
            weighted_x += x * weight
            weighted_y += y * weight
            actual_weight_sum += weight
            
        # Normalize if needed
        if actual_weight_sum > 0:
            weighted_x /= actual_weight_sum
            weighted_y /= actual_weight_sum
            
        # Update point
        result[idx] = (frame, weighted_x, weighted_y)
        
    return result

def smooth_savitzky_golay(curve_data, indices, window_size):
    """Apply Savitzky-Golay smoothing to the specified points."""
    if not indices or window_size < 5:  # Need at least 5 points for quadratic fitting
        return curve_data
        
    # Create a copy of the curve data for reading and writing
    result = copy.deepcopy(curve_data)
    original_data = copy.deepcopy(curve_data)
    
    # Calculate half window size
    half_window = window_size // 2
    
    # Apply smoothing
    for idx in indices:
        # Calculate window indices
        start_idx = max(0, idx - half_window)
        end_idx = min(len(original_data) - 1, idx + half_window)
        
        # Skip if we don't have enough points
        if end_idx - start_idx < 4:  # Need at least 5 points for quadratic
            continue
            
        # Get frame
        frame = original_data[idx][0]
        
        # Get points in window
        x_points = []
        y_points = []
        for i in range(start_idx, end_idx + 1):
            _, x, y = original_data[i]
            x_points.append(x)
            y_points.append(y)
            
        # Calculate relative position in window
        rel_pos = idx - start_idx
        
        # Apply a simplified Savitzky-Golay by fitting quadratic polynomials
        x_new = savitzky_golay_fit(range(len(x_points)), x_points, rel_pos)
        y_new = savitzky_golay_fit(range(len(y_points)), y_points, rel_pos)
        
        # Update point
        result[idx] = (frame, x_new, y_new)
            
    return result

def savitzky_golay_fit(x_indices, values, target_idx):
    """Fit a quadratic polynomial to the data and evaluate at target index."""
    n = len(values)
    if n < 3:
        return values[target_idx] if 0 <= target_idx < n else 0
        
    # Calculate sums for least squares fitting
    sum_x = sum(x_indices)
    sum_x2 = sum(x*x for x in x_indices)
    sum_x3 = sum(x*x*x for x in x_indices)
    sum_x4 = sum(x*x*x*x for x in x_indices)
    
    sum_y = sum(values)
    sum_xy = sum(x*y for x, y in zip(x_indices, values))
    sum_x2y = sum(x*x*y for x, y in zip(x_indices, values))
    
    # Set up matrix for quadratic fit: y = a + bx + cx^2
    determinant = n*sum_x2*sum_x4 + sum_x*sum_x3*sum_x2 + sum_x2*sum_x*sum_x3 - \
                 sum_x2*sum_x2*sum_x2 - sum_x*sum_x*sum_x4 - n*sum_x3*sum_x3
    
    if abs(determinant) < 1e-10:  # Nearly singular matrix, use simpler approach
        return values[target_idx] if 0 <= target_idx < n else 0
    
    # Calculate coefficients
    a = (sum_y*sum_x2*sum_x4 + sum_x*sum_x3*sum_xy + sum_x2*sum_xy*sum_x3 - \
         sum_x2*sum_x2*sum_xy - sum_x*sum_xy*sum_x4 - sum_y*sum_x3*sum_x3) / determinant
         
    b = (n*sum_xy*sum_x4 + sum_y*sum_x3*sum_x2 + sum_x2*sum_x*sum_x2y - \
         sum_x2*sum_xy*sum_x2 - sum_y*sum_x*sum_x4 - n*sum_x3*sum_x2y) / determinant
         
    c = (n*sum_x2*sum_x2y + sum_x*sum_xy*sum_x2 + sum_y*sum_x*sum_x3 - \
         sum_y*sum_x2*sum_x2 - sum_x*sum_x*sum_x2y - n*sum_xy*sum_x3) / determinant
    
    # Evaluate polynomial at target index
    target_x = x_indices[target_idx] if 0 <= target_idx < n else 0
    return a + b*target_x + c*target_x*target_x

# (Moved filter_median into CurveOperations as a static method)

def filter_average(curve_data, indices, window_size):
    """Apply simple moving average filter to the specified points."""
    # This is essentially the same as smooth_moving_average
    return smooth_moving_average(curve_data, indices, window_size)

def filter_gaussian(curve_data, indices, window_size, sigma):
    """Apply Gaussian filter to the specified points."""
    # This is essentially the same as smooth_gaussian
    return smooth_gaussian(curve_data, indices, window_size, sigma)

def filter_butterworth(curve_data, indices, cutoff, order):
    """Apply Butterworth low-pass filter to the specified points."""
    if not indices or len(indices) < 3:
        return curve_data
        
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Get indices range
    min_idx = min(indices)
    max_idx = max(indices)
    
    # We need to work on the whole range to ensure proper filtering
    # Extract x and y sequences
    frames = []
    x_values = []
    y_values = []
    
    for i in range(min_idx, max_idx + 1):
        frame, x, y = curve_data[i]
        frames.append(frame)
        x_values.append(x)
        y_values.append(y)
    
    # Apply the filter to x and y sequences separately
    filtered_x = butterworth_filter(x_values, cutoff, order)
    filtered_y = butterworth_filter(y_values, cutoff, order)
    
    # Update only the requested indices
    for idx_pos, idx in enumerate(range(min_idx, max_idx + 1)):
        if idx in indices:
            frame = frames[idx_pos]
            result[idx] = (frame, filtered_x[idx_pos], filtered_y[idx_pos])
            
    return result

def butterworth_filter(data, cutoff, order):
    """Apply Butterworth low-pass filter to a 1D sequence."""
    if not data:
        return []
        
    # Use a simplified implementation since we don't have scipy
    # This is a naive implementation to demonstrate the concept
    n = len(data)
    output = [0] * n
    
    # Compute filter coefficients (simplified)
    # In a real implementation, we would use scipy's butter and filtfilt functions
    
    # For now, just use a simplified approach with weighted averaging
    # where weights are based on a butterworth response curve
    
    # First compute the alpha parameter (0 to 1, where 1 is no filtering)
    alpha = 1.0 / (1.0 + (1.0 / cutoff)**(2*order))
    
    # Apply a simple first-order filter (this is not a true Butterworth filter)
    output[0] = data[0]
    for i in range(1, n):
        output[i] = alpha * data[i] + (1 - alpha) * output[i-1]
        
    # Apply the filter in reverse for zero-phase effect (similar to filtfilt)
    for i in range(n-2, -1, -1):
        output[i] = alpha * output[i] + (1 - alpha) * output[i+1]
        
    return output

def fill_linear(curve_data, start_frame, end_frame, preserve_endpoints=True):
    """Fill a gap using linear interpolation."""
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Create a frame map of existing points
    frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(result)}
    
    # Get the points at the gap boundaries
    before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f < start_frame]
    after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f > end_frame]
    
    if not before_points or not after_points:
        return result  # Cannot interpolate without points on both sides
        
    # Get the closest points to the gap
    before_points.sort(key=lambda p: start_frame - p[1])
    after_points.sort(key=lambda p: p[1] - end_frame)
    
    # Get points at the gap boundaries
    _, b_frame, b_x, b_y = before_points[0]
    _, a_frame, a_x, a_y = after_points[0]
    
    # Generate new points
    new_points = []
    frame_diff = a_frame - b_frame
    
    for frame in range(start_frame, end_frame + 1):
        # Skip if the frame already exists and we're preserving endpoints
        if frame in frame_map and preserve_endpoints:
            continue
            
        # Calculate interpolation parameter (0.0 to 1.0)
        t = (frame - b_frame) / frame_diff
        
        # Linear interpolation
        x = b_x + (a_x - b_x) * t
        y = b_y + (a_y - b_y) * t
        
        # Add to new points
        new_points.append((frame, x, y))
    
    # Add new points to the curve data
    add_points_to_curve(result, new_points)
    return result

def fill_cubic_spline(curve_data, start_frame, end_frame, tension, preserve_endpoints=True):
    """Fill a gap using cubic spline interpolation."""
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Create a frame map of existing points
    frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(result)}
    
    # Get points before and after the gap
    before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f < start_frame]
    after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f > end_frame]
    
    # We need at least 2 points on each side for cubic interpolation
    # If we don't have enough, fall back to linear
    if len(before_points) < 2 or len(after_points) < 2:
        return fill_linear(curve_data, start_frame, end_frame, preserve_endpoints)
        
    # Get 2 points on each side
    before_points.sort(key=lambda p: start_frame - p[1])
    after_points.sort(key=lambda p: p[1] - end_frame)
    
    b_points = before_points[:2]
    a_points = after_points[:2]
    
    # Set up control points for the spline
    p0 = (b_points[0][2], b_points[0][3])  # x, y of first before point
    p1 = (b_points[1][2], b_points[1][3])  # x, y of second before point
    p2 = (a_points[1][2], a_points[1][3])  # x, y of second after point
    p3 = (a_points[0][2], a_points[0][3])  # x, y of first after point
    
    # Generate new points
    new_points = []
    total_frames = end_frame - start_frame + 1
    
    for i, frame in enumerate(range(start_frame, end_frame + 1)):
        # Skip if the frame already exists and we're preserving endpoints
        if frame in frame_map and preserve_endpoints:
            continue
            
        # Normalize parameter (0.0 to 1.0)
        u = i / total_frames
        
        # Apply tension
        t = 1.0 - tension
        
        # Calculate the four basis functions for the cubic spline
        u2 = u * u
        u3 = u2 * u
        
        # Hermite basis functions with tension
        h1 = 2*u3 - 3*u2 + 1
        h2 = -2*u3 + 3*u2
        h3 = (u3 - 2*u2 + u) * t
        h4 = (u3 - u2) * t
        
        # Calculate interpolated point
        x = h1 * p1[0] + h2 * p2[0] + h3 * (p2[0] - p0[0]) + h4 * (p3[0] - p1[0])
        y = h1 * p1[1] + h2 * p2[1] + h3 * (p2[1] - p0[1]) + h4 * (p3[1] - p1[1])
        
        new_points.append((frame, x, y))
    
    # Add new points to the curve data
    add_points_to_curve(result, new_points)
    return result

def fill_constant_velocity(curve_data, start_frame, end_frame, window_size, preserve_endpoints=True):
    """Fill a gap assuming constant velocity based on surrounding frames."""
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Create a frame map of existing points
    frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(result)}
    
    # Get points before and after the gap
    before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f < start_frame]
    after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f > end_frame]
    
    # We need at least window_size points on each side
    if len(before_points) < window_size or len(after_points) < window_size:
        # Fall back to linear if not enough points
        return fill_linear(curve_data, start_frame, end_frame, preserve_endpoints)
        
    # Sort points by proximity to gap
    before_points.sort(key=lambda p: start_frame - p[1])
    after_points.sort(key=lambda p: p[1] - end_frame)
    
    # Calculate velocity from before points
    b_velocity_x = 0
    b_velocity_y = 0
    
    for i in range(1, window_size):
        frame_diff = before_points[i-1][1] - before_points[i][1]
        if frame_diff == 0:
            continue
            
        b_velocity_x += (before_points[i-1][2] - before_points[i][2]) / frame_diff
        b_velocity_y += (before_points[i-1][3] - before_points[i][3]) / frame_diff
        
    b_velocity_x /= window_size - 1
    b_velocity_y /= window_size - 1
    
    # Calculate velocity from after points
    a_velocity_x = 0
    a_velocity_y = 0
    
    for i in range(1, window_size):
        frame_diff = after_points[i][1] - after_points[i-1][1]
        if frame_diff == 0:
            continue
            
        a_velocity_x += (after_points[i][2] - after_points[i-1][2]) / frame_diff
        a_velocity_y += (after_points[i][3] - after_points[i-1][3]) / frame_diff
        
    a_velocity_x /= window_size - 1
    a_velocity_y /= window_size - 1
    
    # Average the velocities
    velocity_x = (b_velocity_x + a_velocity_x) / 2
    velocity_y = (b_velocity_y + a_velocity_y) / 2
    
    # Get the points at the gap boundaries
    _, b_frame, b_x, b_y = before_points[0]
    
    # Generate new points
    new_points = []
    for frame in range(start_frame, end_frame + 1):
        # Skip if the frame already exists and we're preserving endpoints
        if frame in frame_map and preserve_endpoints:
            continue
            
        # Calculate steps from boundary
        steps = frame - b_frame
        
        # Apply constant velocity
        x = b_x + velocity_x * steps
        y = b_y + velocity_y * steps
        
        new_points.append((frame, x, y))
    
    # Add new points to the curve data
    add_points_to_curve(result, new_points)
    return result

def add_points_to_curve(curve_data, new_points):
    """Add new points to the curve data and sort by frame."""
    # Create frame map for easy reference
    points_map = {frame: (frame, x, y) for frame, x, y in curve_data}
    
    # Add new points
    for frame, x, y in new_points:
        points_map[frame] = (frame, x, y)
        
    # Convert back to sorted list
    sorted_data = [points_map[frame] for frame in sorted(points_map.keys())]
    
    # Update curve_data in-place
    curve_data.clear()
    curve_data.extend(sorted_data)

def extrapolate_forward(curve_data, num_frames, method, fit_points=5):
    """Extrapolate curve forward by num_frames using the specified method."""
    if not curve_data or num_frames <= 0:
        return curve_data
        
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Get the last few frames for extrapolation
    sorted_data = sorted(result, key=lambda x: x[0])
    last_frame = sorted_data[-1][0]
    
    # Get points to use for extrapolation
    points_to_use = sorted_data[-min(fit_points, len(sorted_data)):]
    
    extrapolated = []
    
    # Linear extrapolation
    if method == 0:  # Linear
        if len(points_to_use) < 2:
            return result
            
        # Use last two points to determine direction
        frame1, x1, y1 = points_to_use[-2]
        frame2, x2, y2 = points_to_use[-1]
        
        # Calculate velocity (change per frame)
        frame_diff = frame2 - frame1
        if frame_diff == 0:
            return result
            
        dx = (x2 - x1) / frame_diff
        dy = (y2 - y1) / frame_diff
        
        # Extrapolate
        for i in range(1, num_frames + 1):
            new_frame = last_frame + i
            new_x = x2 + dx * i
            new_y = y2 + dy * i
            extrapolated.append((new_frame, new_x, new_y))
            
    # Last velocity extrapolation (continue with last velocity)
    elif method == 1:  # Last Velocity
        if len(points_to_use) < 2:
            return result
            
        # Calculate average velocity over the last few points
        velocities_x = []
        velocities_y = []
        
        for i in range(1, len(points_to_use)):
            prev_frame, prev_x, prev_y = points_to_use[i-1]
            curr_frame, curr_x, curr_y = points_to_use[i]
            
            frame_diff = curr_frame - prev_frame
            if frame_diff > 0:
                velocities_x.append((curr_x - prev_x) / frame_diff)
                velocities_y.append((curr_y - prev_y) / frame_diff)
        
        if not velocities_x or not velocities_y:
            return result
            
        # Calculate average velocity
        avg_dx = sum(velocities_x) / len(velocities_x)
        avg_dy = sum(velocities_y) / len(velocities_y)
        
        # Extrapolate
        frame, x, y = points_to_use[-1]
        
        for i in range(1, num_frames + 1):
            new_frame = last_frame + i
            new_x = x + avg_dx * i
            new_y = y + avg_dy * i
            extrapolated.append((new_frame, new_x, new_y))
            
    # Quadratic extrapolation (fit a quadratic curve)
    elif method == 2:  # Quadratic
        if len(points_to_use) < 3:
            return result
            
        # Extract data for curve fitting
        frames = [p[0] for p in points_to_use]
        xs = [p[1] for p in points_to_use]
        ys = [p[2] for p in points_to_use]
        
        # Normalize frames for better numerical stability
        min_frame = min(frames)
        normalized_frames = [f - min_frame for f in frames]
        
        # Fit quadratic polynomials for x and y
        x_coeffs = fit_quadratic(normalized_frames, xs)
        y_coeffs = fit_quadratic(normalized_frames, ys)
        
        if not x_coeffs or not y_coeffs:
            return result
            
        # Extrapolate
        for i in range(1, num_frames + 1):
            new_frame = last_frame + i
            normalized_new_frame = new_frame - min_frame
            
            # Evaluate polynomials
            new_x = x_coeffs[0] + x_coeffs[1] * normalized_new_frame + x_coeffs[2] * normalized_new_frame**2
            new_y = y_coeffs[0] + y_coeffs[1] * normalized_new_frame + y_coeffs[2] * normalized_new_frame**2
            
            extrapolated.append((new_frame, new_x, new_y))
    
    # Add extrapolated points to the curve data
    add_points_to_curve(result, extrapolated)
    return result

def extrapolate_backward(curve_data, num_frames, method, fit_points=5):
    """Extrapolate curve backward by num_frames using the specified method."""
    if not curve_data or num_frames <= 0:
        return curve_data
        
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Get the first few frames for extrapolation
    sorted_data = sorted(result, key=lambda x: x[0])
    first_frame = sorted_data[0][0]
    
    # Get points to use for extrapolation
    points_to_use = sorted_data[:min(fit_points, len(sorted_data))]
    
    extrapolated = []
    
    # Linear extrapolation
    if method == 0:  # Linear
        if len(points_to_use) < 2:
            return result
            
        # Use first two points to determine direction
        frame1, x1, y1 = points_to_use[0]
        frame2, x2, y2 = points_to_use[1]
        
        # Calculate velocity (change per frame)
        frame_diff = frame2 - frame1
        if frame_diff == 0:
            return result
            
        dx = (x2 - x1) / frame_diff
        dy = (y2 - y1) / frame_diff
        
        # Extrapolate backward
        for i in range(1, num_frames + 1):
            new_frame = first_frame - i
            new_x = x1 - dx * i
            new_y = y1 - dy * i
            extrapolated.append((new_frame, new_x, new_y))
            
    # First velocity extrapolation (continue with first velocity)
    elif method == 1:  # First Velocity
        if len(points_to_use) < 2:
            return result
            
        # Calculate average velocity over the first few points
        velocities_x = []
        velocities_y = []
        
        for i in range(len(points_to_use) - 1):
            curr_frame, curr_x, curr_y = points_to_use[i]
            next_frame, next_x, next_y = points_to_use[i+1]
            
            frame_diff = next_frame - curr_frame
            if frame_diff > 0:
                velocities_x.append((next_x - curr_x) / frame_diff)
                velocities_y.append((next_y - curr_y) / frame_diff)
        
        if not velocities_x or not velocities_y:
            return result
            
        # Calculate average velocity
        avg_dx = sum(velocities_x) / len(velocities_x)
        avg_dy = sum(velocities_y) / len(velocities_y)
        
        # Extrapolate backward
        frame, x, y = points_to_use[0]
        
        for i in range(1, num_frames + 1):
            new_frame = first_frame - i
            new_x = x - avg_dx * i
            new_y = y - avg_dy * i
            extrapolated.append((new_frame, new_x, new_y))
            
    # Quadratic extrapolation (fit a quadratic curve)
    elif method == 2:  # Quadratic
        if len(points_to_use) < 3:
            return result
            
        # Extract data for curve fitting
        frames = [p[0] for p in points_to_use]
        xs = [p[1] for p in points_to_use]
        ys = [p[2] for p in points_to_use]
        
        # Normalize frames for better numerical stability
        min_frame = min(frames)
        normalized_frames = [f - min_frame for f in frames]
        
        # Fit quadratic polynomials for x and y
        x_coeffs = fit_quadratic(normalized_frames, xs)
        y_coeffs = fit_quadratic(normalized_frames, ys)
        
        if not x_coeffs or not y_coeffs:
            return result
            
        # Extrapolate backward
        for i in range(1, num_frames + 1):
            new_frame = first_frame - i
            normalized_new_frame = new_frame - min_frame
            
            # Evaluate polynomials
            new_x = x_coeffs[0] + x_coeffs[1] * normalized_new_frame + x_coeffs[2] * normalized_new_frame**2
            new_y = y_coeffs[0] + y_coeffs[1] * normalized_new_frame + y_coeffs[2] * normalized_new_frame**2
            
            extrapolated.append((new_frame, new_x, new_y))
    
    # Add extrapolated points to the curve data
    add_points_to_curve(result, extrapolated)
    return result

def fit_quadratic(x, y):
    """Fit a quadratic polynomial to the given data points."""
    if len(x) != len(y) or len(x) < 3:
        return None
        
    n = len(x)
    
    # Calculate sums for the system of equations
    sum_x = sum(x)
    sum_x2 = sum(xi**2 for xi in x)
    sum_x3 = sum(xi**3 for xi in x)
    sum_x4 = sum(xi**4 for xi in x)
    
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2y = sum(xi**2 * yi for xi, yi in zip(x, y))
    
    # Set up the system of linear equations
    A = [
        [n, sum_x, sum_x2],
        [sum_x, sum_x2, sum_x3],
        [sum_x2, sum_x3, sum_x4]
    ]
    
    b = [sum_y, sum_xy, sum_x2y]
    A = [[float(value) for value in row] for row in A]
    b = [float(value) for value in b]
    
    # Solve using a simple Gaussian elimination
    for i in range(3):
        # Find the maximum element in the current column
        max_row = i
        for j in range(i + 1, 3):
            if abs(A[j][i]) > abs(A[max_row][i]):
                max_row = j
                
        # Swap rows if needed
        if max_row != i:
            A[i], A[max_row] = A[max_row], A[i]
            b[i], b[max_row] = b[max_row], b[i]
            
        # Make sure pivot is non-zero
        if abs(A[i][i]) < 1e-10:
            return None
            
        # Eliminate
        for j in range(i + 1, 3):
            factor = A[j][i] / A[i][i]
            for k in range(i, 3):
                A[j][k] -= factor * A[i][k]
            b[j] -= factor * b[i]
            
    # Back substitution
    x = [0.0, 0.0, 0.0]
    for i in range(2, -1, -1):
        x[i] = b[i]
        for j in range(i + 1, 3):
            x[i] -= A[i][j] * x[j]
        x[i] /= A[i][i]
        
    return x

class CurveOperations:
    """Static utility methods for curve operations in the curve editor."""
    
    @staticmethod
    def detect_problems(main_window):
        """Detect potential problems in the tracking data.
        
        Args:
            main_window: The main window containing the curve data
            
        Returns:
            A list of detected problems with format [(frame, severity, description), ...]
        """
        if not main_window.curve_data:
            return []
            
        # Sort by frame
        sorted_data = sorted(main_window.curve_data, key=lambda x: x[0])
        
        problems = []
    @staticmethod
    def smooth_moving_average(curve_data, indices, window_size):
        """Apply moving average smoothing to the specified points via CurveOperations interface."""
        return smooth_moving_average(curve_data, indices, window_size)

        
        # 1. Check for sudden jumps in position
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            frame, x, y = sorted_data[i]
            
            # Calculate distance between consecutive points
            distance = math.sqrt((x - prev_x)**2 + (y - prev_y)**2)
            
            # Also check if frames are consecutive
            frame_gap = frame - prev_frame
            
            # Normalize by frame gap (for non-consecutive frames)
            if frame_gap > 1:
                normalized_distance = distance / frame_gap
            else:
                normalized_distance = distance
                
            # Define thresholds for jumps
            medium_threshold = 10.0  # Adjust based on typical movement
            high_threshold = 30.0
            
            if normalized_distance > high_threshold:
                severity = min(1.0, normalized_distance / (high_threshold * 2))
                problems.append((frame, "Sudden Jump", severity, 
                                f"Distance of {distance:.2f} pixels from previous frame ({normalized_distance:.2f}/frame)"))
            elif normalized_distance > medium_threshold:
                severity = min(0.7, normalized_distance / high_threshold)
                problems.append((frame, "Large Movement", severity,
                                f"Distance of {distance:.2f} pixels from previous frame ({normalized_distance:.2f}/frame)"))
        
        # 2. Check for acceleration (changes in velocity)
        for i in range(2, len(sorted_data)):
            frame_2, x_2, y_2 = sorted_data[i-2]
            frame_1, x_1, y_1 = sorted_data[i-1]
            frame_0, x_0, y_0 = sorted_data[i]
            
            # Calculate velocities (distance per frame)
            time_1 = frame_1 - frame_2
            time_0 = frame_0 - frame_1
            
            if time_1 == 0 or time_0 == 0:
                continue
                
            dx_1 = (x_1 - x_2) / time_1
            dy_1 = (y_1 - y_2) / time_1
            
            dx_0 = (x_0 - x_1) / time_0
            dy_0 = (y_0 - y_1) / time_0
            
            # Calculate change in velocity (acceleration)
            accel_x = abs(dx_0 - dx_1)
            accel_y = abs(dy_0 - dy_1)
            
            # Calculate magnitude of acceleration
            accel_mag = math.sqrt(accel_x**2 + accel_y**2)
            
            # Define thresholds for acceleration
            medium_threshold = 0.8  # Adjust based on typical acceleration
            high_threshold = 2.0
            
            if accel_mag > high_threshold:
                severity = min(0.9, accel_mag / (high_threshold * 2))
                problems.append((frame_0, "High Acceleration", severity,
                                f"Acceleration of {accel_mag:.2f} pixels/frame²"))
            elif accel_mag > medium_threshold:
                severity = min(0.6, accel_mag / high_threshold)
                problems.append((frame_0, "Medium Acceleration", severity,
                                f"Acceleration of {accel_mag:.2f} pixels/frame²"))
        
        # 3. Check for gaps in tracking
        for i in range(1, len(sorted_data)):
            prev_frame, _, _ = sorted_data[i-1]
            frame, _, _ = sorted_data[i]
            
            frame_gap = frame - prev_frame
            
            if frame_gap > 10:
                severity = min(1.0, frame_gap / 30.0)
                problems.append((prev_frame, "Large Gap", severity,
                                f"Gap of {frame_gap} frames after this point"))
            elif frame_gap > 3:
                severity = min(0.5, frame_gap / 10.0)
                problems.append((prev_frame, "Small Gap", severity,
                                f"Gap of {frame_gap} frames after this point"))
        
        # 4. Check for excessive jitter
        if len(sorted_data) >= 5:
            window_size = 5
            
            for i in range(window_size, len(sorted_data)):
                window = sorted_data[i-window_size:i]
                
                # Calculate the average position
                avg_x = sum(p[1] for p in window) / window_size
                avg_y = sum(p[2] for p in window) / window_size
                
                # Calculate the variance in position
                var_x = sum((p[1] - avg_x)**2 for p in window) / window_size
                var_y = sum((p[2] - avg_y)**2 for p in window) / window_size
                
                # Calculate the total variance (jitter)
                jitter = math.sqrt(var_x + var_y)
                
                # Define thresholds for jitter
                medium_threshold = 2.0  # Adjust based on typical jitter
                high_threshold = 5.0
                
                if jitter > high_threshold:
                    frame, _, _ = sorted_data[i-1]
                    severity = min(0.8, jitter / (high_threshold * 2))
                    problems.append((frame, "High Jitter", severity,
                                    f"Jitter of {jitter:.2f} pixels in a {window_size}-frame window"))
                elif jitter > medium_threshold:
                    frame, _, _ = sorted_data[i-1]
                    severity = min(0.5, jitter / high_threshold)
                    problems.append((frame, "Medium Jitter", severity,
                                    f"Jitter of {jitter:.2f} pixels in a {window_size}-frame window"))
        
        # Sort problems by frame for easier navigation
        problems.sort(key=lambda x: x[0])
        
        return problems

    @staticmethod
    def filter_median(curve_data, indices, window_size):
        """Apply median filter to the specified points."""
        if not indices or window_size < 3:
            return curve_data

        # Create a copy of the curve data for reading and writing
        result = copy.deepcopy(curve_data)
        original_data = copy.deepcopy(curve_data)

        # Calculate half window size
        half_window = window_size // 2

        # Apply filter
        for idx in indices:
            # Calculate window indices
            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)

            # Skip if window is too small
            if end_idx - start_idx < 2:
                continue

            # Get frame
            frame = original_data[idx][0]

            # Collect x and y values in the window
            x_values = [original_data[i][1] for i in range(start_idx, end_idx + 1)]
            y_values = [original_data[i][2] for i in range(start_idx, end_idx + 1)]

            # Sort and get median
            x_values.sort()
            y_values.sort()

            median_x = x_values[len(x_values) // 2]
            median_y = y_values[len(y_values) // 2]

            # Update point
            result[idx] = (frame, median_x, median_y)

        return result

    @staticmethod
    def fill_accelerated_motion(curve_data, start_frame, end_frame, window_size, accel_weight, preserve_endpoints=True):
        """Fill a gap using accelerated motion based on surrounding frames."""
        # Create a copy of the curve data
        result = copy.deepcopy(curve_data)
        
        # Create a frame map of existing points
        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(result)}
        
        # Get points before and after the gap
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f > end_frame]
        
        # We need at least window_size points on each side
        if len(before_points) < window_size or len(after_points) < window_size:
            # Fall back to constant velocity if not enough points
            return fill_constant_velocity(curve_data, start_frame, end_frame, window_size, preserve_endpoints)
            
        # Sort points by proximity to gap
        before_points.sort(key=lambda p: start_frame - p[1])
        after_points.sort(key=lambda p: p[1] - end_frame)
        
        # Calculate velocity from before points
        b_velocity_x = 0
        b_velocity_y = 0
        
        for i in range(1, window_size):
            frame_diff = before_points[i-1][1] - before_points[i][1]
            if frame_diff == 0:
                continue
                
            b_velocity_x += (before_points[i-1][2] - before_points[i][2]) / frame_diff
            b_velocity_y += (before_points[i-1][3] - before_points[i][3]) / frame_diff
            
        b_velocity_x /= max(1, window_size - 1)
        b_velocity_y /= max(1, window_size - 1)
        
        # Calculate velocity from after points
        a_velocity_x = 0
        a_velocity_y = 0
        
        for i in range(1, window_size):
            frame_diff = after_points[i][1] - after_points[i-1][1]
            if frame_diff == 0:
                continue
                
            a_velocity_x += (after_points[i][2] - after_points[i-1][2]) / frame_diff
            a_velocity_y += (after_points[i][3] - after_points[i-1][3]) / frame_diff
            
        a_velocity_x /= max(1, window_size - 1)
        a_velocity_y /= max(1, window_size - 1)
        
        # Calculate acceleration (difference in velocities)
        total_gap = end_frame - start_frame + 1
        if total_gap > 0:
            accel_x = (a_velocity_x - b_velocity_x) / total_gap
            accel_y = (a_velocity_y - b_velocity_y) / total_gap
        else:
            accel_x = 0
            accel_y = 0
        
        # Apply accel_weight to control how much acceleration to use
        accel_x *= accel_weight
        accel_y *= accel_weight
        
        # Get the points at the gap boundaries
        _, b_frame, b_x, b_y = before_points[0]
        
        # Generate new points
        new_points = []
        for frame in range(start_frame, end_frame + 1):
            # Skip if the frame already exists and we're preserving endpoints
            if frame in frame_map and preserve_endpoints:
                continue
                
            # Calculate steps from boundary
            steps = frame - b_frame
            
            # Apply constant velocity with acceleration
            # Using the kinematic equation: position = initial_position + initial_velocity * time + 0.5 * acceleration * time^2
            x = b_x + b_velocity_x * steps + 0.5 * accel_x * steps * steps
            y = b_y + b_velocity_y * steps + 0.5 * accel_y * steps * steps
            
            new_points.append((frame, x, y))
        
        # Add new points to the curve data
        add_points_to_curve(result, new_points)
        return result

    @staticmethod
    def fill_average(curve_data, start_frame, end_frame, window_size, preserve_endpoints=True):
        """Fill a gap by averaging neighboring frames."""
        # Create a copy of the curve data
        result = copy.deepcopy(curve_data)
        
        # Create a frame map of existing points
        frame_map = {frame: (idx, frame, x, y) for idx, (frame, x, y) in enumerate(result)}
        
        # Get points before and after the gap
        before_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f < start_frame]
        after_points = [(idx, f, x, y) for idx, (f, x, y) in enumerate(result) if f > end_frame]
        
        # We need at least some points on each side
        if not before_points or not after_points:
            # Fall back to linear if not enough points
            return fill_linear(curve_data, start_frame, end_frame, preserve_endpoints)
            
        # Sort points by proximity to gap
        before_points.sort(key=lambda p: start_frame - p[1])
        after_points.sort(key=lambda p: p[1] - end_frame)
        
        # Get points to use for averaging (up to window_size on each side)
        before_window = before_points[:min(window_size, len(before_points))]
        after_window = after_points[:min(window_size, len(after_points))]
        
        # Calculate average positions
        avg_before_x = sum(p[2] for p in before_window) / len(before_window)
        avg_before_y = sum(p[3] for p in before_window) / len(before_window)
        
        avg_after_x = sum(p[2] for p in after_window) / len(after_window)
        avg_after_y = sum(p[3] for p in after_window) / len(after_window)
        
        # Generate new points with a weighted average based on proximity to each side
        new_points = []
        total_frames = end_frame - start_frame + 1
        
        for frame in range(start_frame, end_frame + 1):
            # Skip if the frame already exists and we're preserving endpoints
            if frame in frame_map and preserve_endpoints:
                continue
                
            # Calculate weight based on position in the gap (0 at start, 1 at end)
            t = (frame - start_frame) / total_frames if total_frames > 0 else 0.5
            
            # Weighted average
            x = avg_before_x * (1 - t) + avg_after_x * t
            y = avg_before_y * (1 - t) + avg_after_y * t
            
            new_points.append((frame, x, y))
        
        # Add new points to the curve data
        add_points_to_curve(result, new_points)

    @staticmethod
    def undo(main_window):
        """Undo the last operation. (Placeholder)"""
        # TODO: Implement undo functionality
        print("Undo operation triggered (not implemented).")

    @staticmethod
    def redo(main_window):
        """Redo the last undone operation. (Placeholder)"""
        # TODO: Implement redo functionality
        print("Redo operation triggered (not implemented).")
