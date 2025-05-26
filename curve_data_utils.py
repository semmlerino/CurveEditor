"""
Utility functions for curve data manipulation in CurveEditor.
"""

def compute_interpolated_curve_data(curve_data, selected_indices):
    """
    Given a list of point tuples and indices to mark as interpolated,
    returns a new list with those points replaced by (frame, x, y, 'interpolated').
    """
    # Copy original data for reference and output
    old_data = list(curve_data)
    new_data = list(curve_data)
    # Create set for quick lookup of removed indices
    sel_set = set(selected_indices)
    # Interpolate each selected index based on original points
    for idx in sorted(selected_indices):
        if idx < 0 or idx >= len(old_data):
            continue
        # Original point
        point = old_data[idx]
        frame, x, y = point[:3]
        # Find previous non-interpolated and non-selected neighbor
        prev_point = None
        for i in range(idx - 1, -1, -1):
            if i in sel_set:
                continue
            p = old_data[i]
            if len(p) == 3 or (len(p) > 3 and p[3] != 'interpolated'):
                prev_point = p
                break
        # Find next non-interpolated and non-selected neighbor
        next_point = None
        for i in range(idx + 1, len(old_data)):
            if i in sel_set:
                continue
            p = old_data[i]
            if len(p) == 3 or (len(p) > 3 and p[3] != 'interpolated'):
                next_point = p
                break
        # Compute interpolation
        if prev_point and next_point:
            _, x0, y0 = prev_point[:3]
            _, x1, y1 = next_point[:3]
            f0, f1 = prev_point[0], next_point[0]
            if f1 != f0:
                t = (frame - f0) / (f1 - f0)
                interp_x = x0 + t * (x1 - x0)
                interp_y = y0 + t * (y1 - y0)
            else:
                interp_x = (x0 + x1) / 2
                interp_y = (y0 + y1) / 2
        elif prev_point:
            interp_x, interp_y = prev_point[1], prev_point[2]
        elif next_point:
            interp_x, interp_y = next_point[1], next_point[2]
        else:
            interp_x, interp_y = x, y
        # Assign interpolated tuple
        new_data[idx] = (frame, interp_x, interp_y, 'interpolated')
    return new_data
