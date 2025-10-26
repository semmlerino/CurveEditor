"""Simple filter implementations to replace scipy dependency."""

from typing import cast

from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData


def simple_lowpass_filter(data: CurveDataInput, window_size: int = 5) -> CurveDataList:
    """
    Simple moving average filter as scipy alternative.

    Args:
        data: List of (frame, x, y) tuples
        window_size: Size of the moving window (default 5)

    Returns:
        Filtered curve data
    """
    if len(data) < window_size:
        return list(data)  # Convert to list for return type compatibility

    # Sort by frame
    sorted_data = sorted(data, key=lambda p: p[0])

    # Extract values
    frames = [p[0] for p in sorted_data]
    x_values = [p[1] for p in sorted_data]
    y_values = [p[2] for p in sorted_data]

    # Apply simple moving average to x and y values
    filtered_x: list[float] = []
    filtered_y: list[float] = []
    half_window = window_size // 2

    for i in range(len(x_values)):
        start = max(0, i - half_window)
        end = min(len(x_values), i + half_window + 1)
        filtered_x.append(sum(x_values[start:end]) / (end - start))
        filtered_y.append(sum(y_values[start:end]) / (end - start))

    # Reconstruct data, preserving any additional elements
    result: CurveDataList = []
    for i in range(len(frames)):
        if len(sorted_data[i]) > 3:
            # Preserve extra elements like status
            combined = (frames[i], filtered_x[i], filtered_y[i]) + tuple(sorted_data[i][3:])  # noqa: RUF005
            result.append(cast(LegacyPointData, combined))
        else:
            result.append((frames[i], filtered_x[i], filtered_y[i]))

    return result
