"""
Unit tests for the AnalysisService class.
"""

import unittest
import numpy as np
from unittest.mock import Mock, patch
from services.analysis_service import AnalysisService


class TestAnalysisService(unittest.TestCase):
    """Test cases for the AnalysisService class."""

    def setUp(self):
        """Set up test fixtures for each test."""
        # Sample curve data for testing
        self.curve_data = [
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
        self.analysis_service = AnalysisService(self.curve_data)

    def test_smooth_moving_average(self):
        """Test smoothing with moving average."""
        # Arrange
        indices_to_smooth = [1, 2, 3]  # Smooth the middle points
        window_size = 3

        # Act
        self.analysis_service.smooth_moving_average(indices_to_smooth, window_size)
        smoothed_data = self.analysis_service.get_data()

        # Assert
        # For point at index 2 (frame 3), the smoothed coordinates should be the average
        # of points at indices 1, 2, and 3
        expected_x = np.mean([105.0, 110.0, 115.0])
        expected_y = np.mean([203.0, 205.0, 208.0])

        self.assertAlmostEqual(smoothed_data[2][1], expected_x, places=4)
        self.assertAlmostEqual(smoothed_data[2][2], expected_y, places=4)

    def test_smooth_gaussian(self):
        """Test smoothing with Gaussian filter."""
        # Arrange
        indices_to_smooth = list(range(5))  # Smooth the first 5 points
        window_size = 3
        sigma = 1.0

        # Act
        self.analysis_service.smooth_gaussian(indices_to_smooth, window_size, sigma)
        smoothed_data = self.analysis_service.get_data()

        # Assert
        # Since we're using a Gaussian filter, results will depend on the implementation
        # Just ensure that smoothing occurred without errors and data structure is preserved
        for i in range(5):
            # Check that each point has frame, x, y
            self.assertEqual(len(smoothed_data[i]), 3)
            # Check that frame numbers are preserved
            self.assertEqual(smoothed_data[i][0], i + 1)

    def test_smooth_savitzky_golay(self):
        """Test smoothing with Savitzky-Golay filter."""
        # Arrange
        indices_to_smooth = list(range(5))  # Smooth the first 5 points
        window_size = 3  # Must be odd

        # Act
        self.analysis_service.smooth_savitzky_golay(indices_to_smooth, window_size)
        smoothed_data = self.analysis_service.get_data()

        # Assert
        # Ensure smoothing occurred without errors and data structure is preserved
        for i in range(5):
            # Check that each point has frame, x, y
            self.assertEqual(len(smoothed_data[i]), 3)
            # Check that frame numbers are preserved
            self.assertEqual(smoothed_data[i][0], i + 1)

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
        problem_data = [
            (1, 100.0, 200.0),
            (2, 100.1, 200.1),  # Very small movement (jitter)
            (3, 150.0, 250.0),  # Sudden jump
            (4, 155.0, 255.0),
            # Gap
            (10, 200.0, 300.0),
            (11, 100.0, 100.0)  # Another sudden jump
        ]

        analysis = AnalysisService(problem_data)

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
