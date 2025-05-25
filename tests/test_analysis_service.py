"""
Unit tests for the AnalysisService class.
"""

import unittest
import numpy as np
from typing import List, Tuple, cast
from services.analysis_service import AnalysisService, PointsList


class TestAnalysisService(unittest.TestCase):
    """Test cases for the AnalysisService class."""

    def setUp(self):
        """Set up test fixtures for each test."""
        # Sample curve data for testing
        self.curve_data: List[Tuple[int, float, float]] = [
            (1, 100.0, 200.0),
            (2, 105.0, 203.0),
            (3, 110.0, 205.0),
            (4, 115.0, 208.0),
            (5, 120.0, 210.0),
            # Gap
            (10, 145.0, 230.0),
            (11, 150.0, 235.0),
            (12, 155.0, 240.0)
        ]

        # Create an AnalysisService instance with the sample data
        # Cast the data to ensure type compatibility
        points_list: PointsList = cast(PointsList, self.curve_data)
        self.analysis_service = AnalysisService(points_list)

    def test_smooth_moving_average(self):
        """Test smoothing with moving average."""
        # Arrange
        indices_to_smooth = [1, 2, 3]  # Smooth the middle points
        window_size = 3

        # Make a copy of the original data for reference
        original_data = [(frame, x, y) for frame, x, y in self.curve_data]

        # Calculate original centroid before smoothing
        original_x_sum = 0.0
        original_y_sum = 0.0
        for idx in indices_to_smooth:
            original_x_sum += self.curve_data[idx][1]
            original_y_sum += self.curve_data[idx][2]
        original_centroid_x = original_x_sum / len(indices_to_smooth)
        original_centroid_y = original_y_sum / len(indices_to_smooth)

        # Act
        self.analysis_service.smooth_moving_average(indices_to_smooth, window_size)
        smoothed_data = self.analysis_service.get_data()

        # Assert
        # Testing for index 2 (frame 3), the smoothed coordinates should be influenced by
        # points at indices 1, 2, and 3 based on the algorithm's blend factor
        
        # Calculate the expected values manually using the same algorithm as in the implementation
        # This accounts for the blend factor used in the actual implementation
        idx = 2  # Testing the middle point
        half_window = window_size // 2
        
        # Collect window values
        window_x_values = [original_data[i][1] for i in range(max(0, idx - half_window), min(len(original_data), idx + half_window + 1))]
        window_y_values = [original_data[i][2] for i in range(max(0, idx - half_window), min(len(original_data), idx + half_window + 1))]
        
        # Calculate average values
        avg_x = sum(window_x_values) / len(window_x_values)
        avg_y = sum(window_y_values) / len(window_y_values)
        
        # Apply same blend factor as in implementation
        blend_factor = min(0.8, window_size / 20.0)  # Must match the formula in implementation
        expected_x = original_data[idx][1] * (1 - blend_factor) + avg_x * blend_factor
        expected_y = original_data[idx][2] * (1 - blend_factor) + avg_y * blend_factor

        # Test with a reasonable delta to account for floating point differences
        self.assertAlmostEqual(float(smoothed_data[idx][1]), float(expected_x), delta=0.0001)
        self.assertAlmostEqual(float(smoothed_data[idx][2]), float(expected_y), delta=0.0001)

        # Calculate new centroid after smoothing
        smoothed_x_sum = 0.0
        smoothed_y_sum = 0.0
        for idx in indices_to_smooth:
            smoothed_x_sum += smoothed_data[idx][1]
            smoothed_y_sum += smoothed_data[idx][2]
        smoothed_centroid_x = smoothed_x_sum / len(indices_to_smooth)
        smoothed_centroid_y = smoothed_y_sum / len(indices_to_smooth)

        # Check that the centroid position is maintained (within a small tolerance)
        # This ensures that the curve isn't being displaced during smoothing
        self.assertAlmostEqual(original_centroid_x, smoothed_centroid_x, delta=0.01)
        self.assertAlmostEqual(original_centroid_y, smoothed_centroid_y, delta=0.01)

    # Removed test_smooth_gaussian as that functionality is no longer supported

    # Removed test_smooth_savitzky_golay as that functionality is no longer supported

    def test_fill_gap_linear(self):
        """Test filling a gap with linear interpolation."""
        # Arrange
        start_frame = 5
        end_frame = 10

        # Act
        self.analysis_service.fill_gap_linear(start_frame, end_frame)
        filled_data = self.analysis_service.get_data()

        # Assert
        # Check that we have filled points for frames 6-9
        frames = [pt[0] for pt in filled_data]
        for frame in range(6, 10):
            self.assertIn(frame, frames)

        # Check that the interpolated values follow a linear progression
        idx_frame_6 = frames.index(6)
        point_6 = filled_data[idx_frame_6]

        # Linear interpolation: frame 6 should be 1/5 of the way from frame 5 to frame 10
        expected_x = 120.0 + (145.0 - 120.0) * 0.2
        expected_y = 210.0 + (230.0 - 210.0) * 0.2

        self.assertAlmostEqual(point_6[1], expected_x, places=4)
        self.assertAlmostEqual(point_6[2], expected_y, places=4)

    def test_fill_gap_spline(self):
        """Test filling a gap with spline interpolation."""
        # Arrange
        start_frame = 5
        end_frame = 10

        # Act
        self.analysis_service.fill_gap_spline(start_frame, end_frame)
        filled_data = self.analysis_service.get_data()

        # Assert
        # Check that we have filled points for frames 6-9
        frames = [pt[0] for pt in filled_data]
        for frame in range(6, 10):
            self.assertIn(frame, frames)

        # Ensure all points have the correct structure
        for point in filled_data:
            self.assertEqual(len(point), 3)
            self.assertIsInstance(point[0], int)  # frame
            self.assertIsInstance(point[1], float)  # x
            self.assertIsInstance(point[2], float)  # y

    def test_normalize_velocity(self):
        """Test normalizing point velocities."""
        # Arrange
        target_velocity = 5.0

        # Act
        self.analysis_service.normalize_velocity(target_velocity)
        normalized_data = self.analysis_service.get_data()

        # Assert
        # Check data structure is preserved
        self.assertEqual(len(normalized_data), len(self.curve_data))

        # Calculate velocities between consecutive points
        for i in range(len(normalized_data) - 1):
            if normalized_data[i+1][0] - normalized_data[i][0] == 1:  # consecutive frames
                dx = normalized_data[i+1][1] - normalized_data[i][1]
                dy = normalized_data[i+1][2] - normalized_data[i][2]
                velocity = np.sqrt(dx**2 + dy**2)

                # Velocity should be close to target (allowing for rounding errors)
                self.assertAlmostEqual(velocity, target_velocity, delta=0.1)

    def test_detect_problems(self):
        """Test detecting problems in tracking data."""
        # Create data with intentional problems
        problem_data: List[Tuple[int, float, float]] = [
            (1, 100.0, 200.0),
            (2, 100.1, 200.1),  # Very small movement (jitter)
            (3, 150.0, 250.0),  # Sudden jump
            (4, 155.0, 255.0),
            # Gap
            (10, 200.0, 300.0),
            (11, 100.0, 100.0)  # Another sudden jump
        ]

        # Cast the data to ensure type compatibility
        points_list: PointsList = cast(PointsList, problem_data)
        analysis = AnalysisService(points_list)

        # Act
        problems = analysis.detect_problems()

        # Assert
        # Should detect at least:
        # 1. Jitter at frame 2
        # 2. Sudden jump at frames 3 and 11
        # 3. Gap between frames 4 and 10
        self.assertGreaterEqual(len(problems), 3)

        # Check that the problems dictionary has the right structure
        for frame, issue_data in problems.items():
            self.assertIsInstance(frame, int)
            self.assertIn('type', issue_data)
            self.assertIn('description', issue_data)


if __name__ == '__main__':
    unittest.main()
