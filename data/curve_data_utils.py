"""
Utility functions for curve data manipulation in CurveEditor.

Provides interpolation and data manipulation functions that respect curve
segments and ENDFRAME boundaries for 3DEqualizer-style tracking.
"""

from core.point_types import get_point_status, safe_extract_point


def is_endframe_point(point: tuple[int, float, float] | tuple[int, float, float, str | bool]) -> bool:
    """Check if a point is an ENDFRAME point.

    Args:
        point: Point tuple to check

    Returns:
        True if the point is an ENDFRAME
    """
    status = get_point_status(point)
    return status == "endframe"


def find_interpolation_boundaries_with_segments(
    curve_data: list[tuple[int, float, float] | tuple[int, float, float, str | bool]],
    idx: int,
    selected_indices: set[int],
) -> tuple[tuple[int, float, float, str] | None, tuple[int, float, float, str] | None]:
    """Find valid interpolation boundaries respecting segment boundaries.

    This function ensures interpolation does not cross ENDFRAME points,
    maintaining curve segmentation for 3DEqualizer-style tracking.

    Args:
        curve_data: Complete curve data
        idx: Index of point to interpolate
        selected_indices: Set of indices being interpolated

    Returns:
        Tuple of (prev_point, next_point) for interpolation, or (None, None)
    """
    n_points = len(curve_data)

    # Find previous valid neighbor (not crossing ENDFRAME)
    prev_point = None
    for i in range(idx - 1, -1, -1):
        if i in selected_indices:
            continue

        p = curve_data[i]

        # Stop if we hit an ENDFRAME (segment boundary)
        if is_endframe_point(p):
            break

        # Check if point is not interpolated
        if get_point_status(p) != "interpolated":
            frame, x, y, status = safe_extract_point(p)
            prev_point = (frame, x, y, status)
            break

    # Find next valid neighbor (not crossing ENDFRAME)
    next_point = None

    # First check if current point itself is an ENDFRAME
    if idx < n_points and is_endframe_point(curve_data[idx]):
        # Can't interpolate an ENDFRAME point
        return (None, None)

    for i in range(idx + 1, n_points):
        if i in selected_indices:
            continue

        p = curve_data[i]

        # Check if point is not interpolated first
        if get_point_status(p) != "interpolated":
            # But stop if it's an ENDFRAME after checking
            if is_endframe_point(p):
                # Can use ENDFRAME as next point but don't cross it
                frame, x, y, status = safe_extract_point(p)
                next_point = (frame, x, y, status)
                break

            frame, x, y, status = safe_extract_point(p)
            next_point = (frame, x, y, status)
            break

    # Check if there's an ENDFRAME between prev and current
    if prev_point:
        prev_frame = prev_point[0]
        for i in range(idx - 1, -1, -1):
            if curve_data[i][0] == prev_frame:
                break
            if is_endframe_point(curve_data[i]):
                # ENDFRAME between prev and current - can't interpolate
                prev_point = None
                break

    return (prev_point, next_point)


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

    # For large datasets where O(n²) becomes problematic, use optimized approach
    # Based on benchmarking, the optimization overhead pays off at 100k operations
    if n_points * n_selected > 100000:  # 100k operations threshold (10x more aggressive)
        return _compute_interpolated_optimized(old_data, new_data, selected_indices)

    # For smaller datasets, use original algorithm with minor optimizations
    return _compute_interpolated_original(old_data, new_data, selected_indices)


def _compute_interpolated_original(
    old_data: list[tuple[int, float, float] | tuple[int, float, float, str | bool]],
    new_data: list[tuple[int, float, float, str]],
    selected_indices: list[int],
) -> list[tuple[int, float, float, str]]:
    """
    Enhanced original algorithm with segment-aware interpolation.

    Key improvements over the original:
    1. Set-based lookup for O(1) selected index checking
    2. Respects ENDFRAME boundaries (doesn't interpolate across segments)
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

        # Use segment-aware boundary finding
        prev_tuple, next_tuple = find_interpolation_boundaries_with_segments(old_data, idx, selected_set)

        # Convert tuples back to match existing logic
        prev_point = prev_tuple if prev_tuple else None
        next_point = next_tuple if next_tuple else None

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
    old_data: list[tuple[int, float, float] | tuple[int, float, float, str | bool]],
    new_data: list[tuple[int, float, float, str]],
    selected_indices: list[int],
) -> list[tuple[int, float, float, str]]:
    """
    O(n) optimized algorithm for large datasets with segment awareness.

    Pre-computes neighbor mappings while respecting ENDFRAME boundaries.
    Uses arrays instead of dictionaries for better performance.
    """
    n_points = len(old_data)
    selected_set = set(selected_indices)

    # Pre-compute neighbor mappings using arrays for performance
    prev_neighbors = [-1] * n_points
    next_neighbors = [-1] * n_points

    # Forward pass: build previous neighbor mappings (stop at ENDFRAME)
    last_valid_idx = -1
    last_was_endframe = False
    for i in range(n_points):
        if i in selected_set:
            # Check if we crossed an ENDFRAME boundary
            if last_was_endframe:
                prev_neighbors[i] = -1  # No valid prev across segment boundary
            else:
                prev_neighbors[i] = last_valid_idx
        else:
            p = old_data[i]
            status = get_point_status(p)
            if status != "interpolated":
                if is_endframe_point(p):
                    last_was_endframe = True
                    last_valid_idx = -1  # Reset after ENDFRAME
                else:
                    last_was_endframe = False
                    last_valid_idx = i

    # Backward pass: build next neighbor mappings (stop at ENDFRAME)
    last_valid_idx = -1
    for i in range(n_points - 1, -1, -1):
        if i in selected_set:
            # Check if point itself is ENDFRAME
            if is_endframe_point(old_data[i]):
                next_neighbors[i] = -1  # Can't interpolate ENDFRAME
            else:
                next_neighbors[i] = last_valid_idx
        else:
            p = old_data[i]
            status = get_point_status(p)
            if status != "interpolated":
                # Both branches assign to last_valid_idx, so just assign directly
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
