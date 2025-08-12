"""
Utility functions for curve data manipulation in CurveEditor.
"""

def compute_interpolated_curve_data(
    curve_data: list[tuple[int, float, float] | tuple[int, float, float, str | bool]], selected_indices: list[int]
) -> list[tuple[int, float, float, str]]:
    """
    Given a list of point tuples and indices to mark as interpolated,
    returns a new list with those points replaced by (frame, x, y, 'interpolated').

    Optimized to avoid O(n²) performance for large datasets by pre-computing neighbor mappings.
    """
    # Copy original data for reference and output
    old_data = list(curve_data)
    # Create new data list with the correct type (including status field)
    new_data: list[tuple[int, float, float, str]] = [(p[0], p[1], p[2], "") for p in curve_data]

    # Early exit for empty selection
    if not selected_indices:
        return new_data

    # Calculate complexity to decide algorithm
    n_points = len(curve_data)
    n_selected = len(selected_indices)

    # For extremely large datasets where O(n²) becomes truly problematic, use optimized approach
    # Based on benchmarking, the optimization overhead only pays off for very large datasets
    if n_points * n_selected > 1000000:  # 1M operations threshold
        return _compute_interpolated_optimized(old_data, new_data, selected_indices)

    # For smaller datasets, use original algorithm with minor optimizations
    return _compute_interpolated_original(old_data, new_data, selected_indices)

def _compute_interpolated_original(
    old_data: list, new_data: list[tuple[int, float, float, str]], selected_indices: list[int]
) -> list[tuple[int, float, float, str]]:
    """
    Enhanced original algorithm with optimizations for better practical performance.

    Key improvements over the original:
    1. Set-based lookup for O(1) selected index checking
    2. Early termination conditions in searches
    3. Reduced function call overhead
    4. Improved memory access patterns
    """
    selected_set = set(selected_indices)
    n_points = len(old_data)

    # Pre-check validity to avoid redundant bounds checking
    valid_indices = [idx for idx in sorted(selected_indices) if 0 <= idx < n_points]

    for idx in valid_indices:
        # Original point using type-safe extraction
        point = old_data[idx]
        frame, x, y, _ = safe_extract_point(point)

        # Find previous valid neighbor with optimized search
        prev_point = None
        for i in range(idx - 1, -1, -1):
            if i not in selected_set:
                p = old_data[i]
                # Fast path: check if point is not interpolated using type-safe method
                if get_point_status(p) != "interpolated":
                    prev_point = p
                    break

        # Find next valid neighbor with optimized search
        next_point = None
        for i in range(idx + 1, n_points):
            if i not in selected_set:
                p = old_data[i]
                # Fast path: check if point is not interpolated using type-safe method
                if get_point_status(p) != "interpolated":
                    next_point = p
                    break

        # Compute interpolation with optimized logic
        if prev_point and next_point:
            # Linear interpolation between two points using type-safe extraction
            f0, x0, y0, _ = safe_extract_point(prev_point)
            f1, x1, y1, _ = safe_extract_point(next_point)

            if f1 != f0:  # Normal case: different frame numbers
                t = (frame - f0) / (f1 - f0)
                interp_x = x0 + t * (x1 - x0)
                interp_y = y0 + t * (y1 - y0)
            else:  # Edge case: same frame number
                interp_x = (x0 + x1) * 0.5  # Slightly faster than division
                interp_y = (y0 + y1) * 0.5
        elif prev_point:
            # Use previous point values with type-safe extraction
            _, interp_x, interp_y, _ = safe_extract_point(prev_point)
        elif next_point:
            # Use next point values with type-safe extraction
            _, interp_x, interp_y, _ = safe_extract_point(next_point)
        else:
            # Fallback: use original point values
            interp_x, interp_y = x, y

        # Assign interpolated tuple
        new_data[idx] = (frame, interp_x, interp_y, "interpolated")

    return new_data

def _compute_interpolated_optimized(
    old_data: list, new_data: list[tuple[int, float, float, str]], selected_indices: list[int]
) -> list[tuple[int, float, float, str]]:
    """
    O(n) optimized algorithm for large datasets.

    Pre-computes neighbor mappings to avoid O(n²) searches.
    Uses arrays instead of dictionaries for better performance.
    """
    n_points = len(old_data)
    selected_set = set(selected_indices)

    # Pre-compute neighbor mappings using arrays for performance
    prev_neighbors = [-1] * n_points
    next_neighbors = [-1] * n_points

    # Forward pass: build previous neighbor mappings
    last_valid_idx = -1
    for i in range(n_points):
        if i in selected_set:
            prev_neighbors[i] = last_valid_idx
        else:
            p = old_data[i]
            if get_point_status(p) != "interpolated":
                last_valid_idx = i

    # Backward pass: build next neighbor mappings
    last_valid_idx = -1
    for i in range(n_points - 1, -1, -1):
        if i in selected_set:
            next_neighbors[i] = last_valid_idx
        else:
            p = old_data[i]
            if get_point_status(p) != "interpolated":
                last_valid_idx = i

    # Interpolate using pre-computed neighbors
    for idx in sorted(selected_indices):
        if idx < 0 or idx >= n_points:
            continue

        # Original point using type-safe extraction
        point = old_data[idx]
        frame, x, y, _ = safe_extract_point(point)

        # Get neighbors from pre-computed arrays (O(1) lookup)
        prev_idx = prev_neighbors[idx] if prev_neighbors[idx] != -1 else None
        next_idx = next_neighbors[idx] if next_neighbors[idx] != -1 else None

        prev_point = old_data[prev_idx] if prev_idx is not None else None
        next_point = old_data[next_idx] if next_idx is not None else None

        # Compute interpolation (same logic as original)
        if prev_point and next_point:
            # Linear interpolation using type-safe extraction
            f0, x0, y0, _ = safe_extract_point(prev_point)
            f1, x1, y1, _ = safe_extract_point(next_point)
            if f1 != f0:
                t = (frame - f0) / (f1 - f0)
                interp_x = x0 + t * (x1 - x0)
                interp_y = y0 + t * (y1 - y0)
            else:
                interp_x = (x0 + x1) / 2
                interp_y = (y0 + y1) / 2
        elif prev_point:
            _, interp_x, interp_y, _ = safe_extract_point(prev_point)
        elif next_point:
            _, interp_x, interp_y, _ = safe_extract_point(next_point)
        else:
            interp_x, interp_y = x, y

        # Assign interpolated tuple
        new_data[idx] = (frame, interp_x, interp_y, "interpolated")

    return new_data
