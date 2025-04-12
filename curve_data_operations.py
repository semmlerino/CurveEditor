"""
curve_data_operations.py

Canonical implementation of all curve data operations for the Curve Editor.
This module centralizes smoothing, filtering, filling, extrapolation, and related operations.
All UI, batch, and preset logic should call this API.

Refactoring Plan: See CONSOLIDATE_SMOOTHING_FILTERING.md
"""

class CurveDataOperations:
    """
    Canonical class for all curve data operations.
    """

    @staticmethod
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
            return CurveDataOperations.smooth_moving_average(curve_data, indices, window_size)
        elif method == "gaussian":
            window_size = params.get("window_size", 5)
            sigma = params.get("sigma", 1.0)
            return CurveDataOperations.smooth_gaussian(curve_data, indices, window_size, sigma)
        elif method == "savitzky_golay":
            window_size = params.get("window_size", 5)
            return CurveDataOperations.smooth_savitzky_golay(curve_data, indices, window_size)
        # TODO: Add median, butterworth, filter_average, filter_gaussian as methods
        else:
            raise ValueError(f"Unknown smoothing/filtering method: {method}")

    @staticmethod
    def smooth_moving_average(curve_data, indices, window_size):
        """Apply moving average smoothing to the specified points."""
        import copy
        if not indices or window_size < 3:
            return curve_data
        result = copy.deepcopy(curve_data)
        original_data = copy.deepcopy(curve_data)
        half_window = window_size // 2
        for idx in indices:
            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)
            if end_idx - start_idx < 2:
                continue
            frame = original_data[idx][0]
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
            result[idx] = (frame, avg_x, avg_y)
        return result

    @staticmethod
    def smooth_gaussian(curve_data, indices, window_size, sigma):
        """Apply Gaussian smoothing to the specified points."""
        import math
        import copy
        if not indices or window_size < 3:
            return curve_data
        result = copy.deepcopy(curve_data)
        original_data = copy.deepcopy(curve_data)
        half_window = window_size // 2
        weights = []
        weight_sum = 0
        for i in range(-half_window, half_window + 1):
            weight = math.exp(-(i**2) / (2 * sigma**2))
            weights.append(weight)
            weight_sum += weight
        weights = [w / weight_sum for w in weights]
        for idx in indices:
            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)
            if end_idx - start_idx < 2:
                continue
            frame = original_data[idx][0]
            weighted_x = 0
            weighted_y = 0
            actual_weight_sum = 0
            for i, w_idx in enumerate(range(start_idx, end_idx + 1)):
                weight_idx = i + (start_idx - (idx - half_window))
                if weight_idx < 0 or weight_idx >= len(weights):
                    continue
                _, x, y = original_data[w_idx]
                weight = weights[weight_idx]
                weighted_x += x * weight
                weighted_y += y * weight
                actual_weight_sum += weight
            if actual_weight_sum > 0:
                weighted_x /= actual_weight_sum
                weighted_y /= actual_weight_sum
            result[idx] = (frame, weighted_x, weighted_y)
        return result

    @staticmethod
    def smooth_savitzky_golay(curve_data, indices, window_size):
        """Apply Savitzky-Golay smoothing to the specified points."""
        import copy
        if not indices or window_size < 5:
            return curve_data
        result = copy.deepcopy(curve_data)
        original_data = copy.deepcopy(curve_data)
        half_window = window_size // 2
        for idx in indices:
            start_idx = max(0, idx - half_window)
            end_idx = min(len(original_data) - 1, idx + half_window)
            if end_idx - start_idx < 4:
                continue
            frame = original_data[idx][0]
            x_points = []
            y_points = []
            for i in range(start_idx, end_idx + 1):
                _, x, y = original_data[i]
                x_points.append(x)
                y_points.append(y)
            rel_pos = idx - start_idx
            x_new = CurveDataOperations.savitzky_golay_fit(range(len(x_points)), x_points, rel_pos)
            y_new = CurveDataOperations.savitzky_golay_fit(range(len(y_points)), y_points, rel_pos)
            result[idx] = (frame, x_new, y_new)
        return result

    @staticmethod
    def savitzky_golay_fit(x_indices, values, target_idx):
        """Fit a quadratic polynomial to the given data points and return the value at target_idx."""
        # Placeholder for actual implementation
        # TODO: Move implementation from curve_operations.py
        raise NotImplementedError