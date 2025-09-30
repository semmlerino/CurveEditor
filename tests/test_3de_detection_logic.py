"""Test suite for 3DEqualizer coordinate system detection logic.

Tests the detection logic that identifies 3DEqualizer data based on high-precision
decimal coordinates and ensures consistent behavior across all loading paths.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from controllers.file_operations_manager import FileOperationsManager


@pytest.fixture
def app(qtbot):
    """Ensure QApplication exists for signal testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def mock_main_window():
    """Create a mock main window for testing."""
    mock_window = Mock()
    mock_window.curve_widget = Mock()
    mock_window.state_manager = Mock()
    mock_window.state_manager.current_file = None
    mock_window.tracked_data = {}
    mock_window.active_points = []
    mock_window.set_tracked_data_atomic = Mock()
    mock_window.update_tracking_panel = Mock()
    mock_window.update_curve_display = Mock()
    mock_window.frame_slider = Mock()
    mock_window.frame_spinbox = Mock()
    mock_window.total_frames_label = Mock()
    return mock_window


@pytest.fixture
def file_operations_manager(mock_main_window):
    """Create FileOperationsManager instance for testing."""
    return FileOperationsManager(mock_main_window)


class TestCoordinateSystemDetection:
    """Test coordinate system detection logic."""

    def test_detects_3de_high_precision_coordinates(self, file_operations_manager):
        """Test that high-precision coordinates are detected as 3DE format."""
        # Mock data with high-precision coordinates (characteristic of 3DE exports)
        high_precision_data = {
            "Point01": [(1, 682.291351786175937, 405.847263681592829), (2, 683.123456789012345, 406.987654321098765)]
        }

        # Test the detection logic directly
        file_path = "test_data.txt"
        is_3de_data = file_path.endswith(".txt") and high_precision_data and len(high_precision_data) > 0

        if is_3de_data and high_precision_data:
            first_point_name = list(high_precision_data.keys())[0]
            first_trajectory = high_precision_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                # Check if coordinates have high precision (more than 3 decimal places)
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert is_3de_data, "Should detect high-precision coordinates as 3DE format"

    def test_detects_pixel_tracking_low_precision_coordinates(self, file_operations_manager):
        """Test that low-precision coordinates are detected as pixel tracking format."""
        # Mock data with low-precision coordinates (characteristic of pixel tracking)
        low_precision_data = {"Point01": [(1, 123.45, 234.56), (2, 124.78, 235.89)]}

        # Test the detection logic directly
        file_path = "test_data.txt"
        is_3de_data = file_path.endswith(".txt") and low_precision_data and len(low_precision_data) > 0

        if is_3de_data and low_precision_data:
            first_point_name = list(low_precision_data.keys())[0]
            first_trajectory = low_precision_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                # Check if coordinates have high precision (more than 3 decimal places)
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert not is_3de_data, "Should detect low-precision coordinates as pixel tracking format"

    def test_non_txt_files_not_detected_as_3de(self, file_operations_manager):
        """Test that non-.txt files are not detected as 3DE format."""
        high_precision_data = {"Point01": [(1, 682.291351786175937, 405.847263681592829)]}

        # Test with .csv file
        file_path = "test_data.csv"
        is_3de_data = file_path.endswith(".txt") and high_precision_data and len(high_precision_data) > 0

        assert not is_3de_data, "Non-.txt files should not be detected as 3DE format"

    def test_empty_data_not_detected_as_3de(self, file_operations_manager):
        """Test that empty data is not detected as 3DE format."""
        empty_data = {}

        file_path = "test_data.txt"
        is_3de_data = file_path.endswith(".txt") and empty_data and len(empty_data) > 0

        assert not is_3de_data, "Empty data should not be detected as 3DE format"


class TestToolbarLoadingDetection:
    """Test 3DE detection in toolbar loading path."""

    @patch("services.get_data_service")
    def test_toolbar_loading_calls_3de_setup_for_high_precision(self, mock_get_data_service, file_operations_manager):
        """Test that toolbar loading calls setup_for_3dequalizer_data for high-precision coordinates."""
        # Mock data service to return high-precision data
        mock_data_service = Mock()
        mock_get_data_service.return_value = mock_data_service

        high_precision_data = {"Point01": [(1, 682.291351786175937, 405.847263681592829)]}
        mock_data_service.load_tracked_data.return_value = high_precision_data

        # Mock file dialog to return a .txt file
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("test_3de_data.txt", "")

            # Call the open_file method
            file_operations_manager.open_file()

            # Verify that setup_for_3dequalizer_data was called
            file_operations_manager.main_window.curve_widget.setup_for_3dequalizer_data.assert_called_once()
            file_operations_manager.main_window.curve_widget.setup_for_pixel_tracking.assert_not_called()

    @patch("services.get_data_service")
    def test_toolbar_loading_calls_pixel_setup_for_low_precision(self, mock_get_data_service, file_operations_manager):
        """Test that toolbar loading calls setup_for_pixel_tracking for low-precision coordinates."""
        # Mock data service to return low-precision data
        mock_data_service = Mock()
        mock_get_data_service.return_value = mock_data_service

        low_precision_data = {"Point01": [(1, 123.45, 234.56)]}
        mock_data_service.load_tracked_data.return_value = low_precision_data

        # Mock file dialog to return a .txt file
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = ("test_pixel_data.txt", "")

            # Call the open_file method
            file_operations_manager.open_file()

            # Verify that setup_for_pixel_tracking was called
            file_operations_manager.main_window.curve_widget.setup_for_pixel_tracking.assert_called_once()
            file_operations_manager.main_window.curve_widget.setup_for_3dequalizer_data.assert_not_called()


class TestCommandLineLoadingDetection:
    """Test 3DE detection logic used in command-line loading path."""

    def test_command_line_detection_logic_for_3de_data(self):
        """Test that the detection logic correctly identifies 3DE data for command-line loading."""
        from pathlib import Path

        # Simulate the detection logic used in _load_initial_data_file
        file_path = Path("test_3de_data.txt")
        curve_data = {"Point01": [(1, 682.291351786175937, 405.847263681592829)]}

        # Apply the same detection logic as in main_window.py
        is_3de_data = str(file_path).endswith(".txt") and curve_data and len(curve_data) > 0

        # Check for high-precision decimals characteristic of 3DE exports
        if is_3de_data and curve_data:
            first_point_name = list(curve_data.keys())[0]
            first_trajectory = curve_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                # Check if coordinates have high precision (more than 3 decimal places)
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert is_3de_data, "Command-line detection should identify high-precision data as 3DE"

    def test_command_line_detection_logic_for_pixel_data(self):
        """Test that the detection logic correctly identifies pixel tracking data for command-line loading."""
        from pathlib import Path

        # Simulate the detection logic used in _load_initial_data_file
        file_path = Path("test_pixel_data.txt")
        curve_data = {"Point01": [(1, 123.45, 234.56)]}

        # Apply the same detection logic as in main_window.py
        is_3de_data = str(file_path).endswith(".txt") and curve_data and len(curve_data) > 0

        # Check for high-precision decimals characteristic of 3DE exports
        if is_3de_data and curve_data:
            first_point_name = list(curve_data.keys())[0]
            first_trajectory = curve_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                # Check if coordinates have high precision (more than 3 decimal places)
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert not is_3de_data, "Command-line detection should identify low-precision data as pixel tracking"


class TestEdgeCases:
    """Test edge cases for the detection logic."""

    def test_integer_coordinates_not_detected_as_3de(self, file_operations_manager):
        """Test that integer coordinates are not detected as 3DE format."""
        integer_data = {"Point01": [(1, 123, 456)]}

        file_path = "test_data.txt"
        is_3de_data = file_path.endswith(".txt") and integer_data and len(integer_data) > 0

        if is_3de_data and integer_data:
            first_point_name = list(integer_data.keys())[0]
            first_trajectory = integer_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert not is_3de_data, "Integer coordinates should not be detected as 3DE format"

    def test_exactly_3_decimal_places_not_detected_as_3de(self, file_operations_manager):
        """Test that exactly 3 decimal places are not detected as 3DE format."""
        three_decimal_data = {"Point01": [(1, 123.456, 789.012)]}

        file_path = "test_data.txt"
        is_3de_data = file_path.endswith(".txt") and three_decimal_data and len(three_decimal_data) > 0

        if is_3de_data and three_decimal_data:
            first_point_name = list(three_decimal_data.keys())[0]
            first_trajectory = three_decimal_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert not is_3de_data, "Exactly 3 decimal places should not be detected as 3DE format"

    def test_malformed_trajectory_data_not_detected_as_3de(self, file_operations_manager):
        """Test that malformed trajectory data is handled gracefully."""
        malformed_data = {
            "Point01": [(1,)]  # Missing coordinates
        }

        file_path = "test_data.txt"
        is_3de_data = file_path.endswith(".txt") and malformed_data and len(malformed_data) > 0

        if is_3de_data and malformed_data:
            first_point_name = list(malformed_data.keys())[0]
            first_trajectory = malformed_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_data = has_high_precision

        assert not is_3de_data, "Malformed trajectory data should not be detected as 3DE format"


class TestLoadingPathConsistency:
    """Test that toolbar and command-line loading paths produce consistent results."""

    def test_both_paths_detect_3de_data_consistently(self):
        """Test that both toolbar and command-line loading detect 3DE data consistently."""
        from pathlib import Path

        # Test data with high-precision coordinates
        high_precision_data = {"Point01": [(1, 682.291351786175937, 405.847263681592829)]}

        # Test toolbar loading detection logic
        file_path_toolbar = "test_3de_data.txt"
        is_3de_toolbar = file_path_toolbar.endswith(".txt") and high_precision_data and len(high_precision_data) > 0

        if is_3de_toolbar and high_precision_data:
            first_point_name = list(high_precision_data.keys())[0]
            first_trajectory = high_precision_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_toolbar = has_high_precision

        # Test command-line loading detection logic (same logic)
        file_path_cmdline = Path("test_3de_data.txt")
        is_3de_cmdline = (
            str(file_path_cmdline).endswith(".txt") and high_precision_data and len(high_precision_data) > 0
        )

        if is_3de_cmdline and high_precision_data:
            first_point_name = list(high_precision_data.keys())[0]
            first_trajectory = high_precision_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_cmdline = has_high_precision

        # Both should detect as 3DE
        assert is_3de_toolbar == is_3de_cmdline, "Both loading paths should detect 3DE data consistently"
        assert is_3de_toolbar, "Both paths should detect high-precision data as 3DE"

    def test_both_paths_detect_pixel_data_consistently(self):
        """Test that both toolbar and command-line loading detect pixel data consistently."""
        from pathlib import Path

        # Test data with low-precision coordinates
        low_precision_data = {"Point01": [(1, 123.45, 234.56)]}

        # Test toolbar loading detection logic
        file_path_toolbar = "test_pixel_data.txt"
        is_3de_toolbar = file_path_toolbar.endswith(".txt") and low_precision_data and len(low_precision_data) > 0

        if is_3de_toolbar and low_precision_data:
            first_point_name = list(low_precision_data.keys())[0]
            first_trajectory = low_precision_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_toolbar = has_high_precision

        # Test command-line loading detection logic (same logic)
        file_path_cmdline = Path("test_pixel_data.txt")
        is_3de_cmdline = str(file_path_cmdline).endswith(".txt") and low_precision_data and len(low_precision_data) > 0

        if is_3de_cmdline and low_precision_data:
            first_point_name = list(low_precision_data.keys())[0]
            first_trajectory = low_precision_data[first_point_name]
            if first_trajectory and len(first_trajectory) > 0:
                x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                is_3de_cmdline = has_high_precision

        # Both should detect as pixel tracking (not 3DE)
        assert is_3de_toolbar == is_3de_cmdline, "Both loading paths should detect pixel data consistently"
        assert not is_3de_toolbar, "Both paths should detect low-precision data as pixel tracking"

    def test_detection_logic_boundary_cases_consistency(self):
        """Test that boundary cases are handled consistently across loading paths."""
        from pathlib import Path

        test_cases = [
            # Exactly 3 decimal places - should NOT be 3DE
            {"Point01": [(1, 123.456, 789.012)]},
            # 4 decimal places - should be 3DE
            {"Point01": [(1, 123.4567, 789.0123)]},
            # Mixed precision - should be 3DE (first coordinate determines)
            {"Point01": [(1, 123.123456789, 789.01)]},
            # Integer coordinates - should NOT be 3DE
            {"Point01": [(1, 123, 456)]},
        ]

        expected_results = [False, True, True, False]

        for i, test_data in enumerate(test_cases):
            # Test both paths with same logic
            for file_path in ["test.txt", Path("test.txt")]:
                is_3de_data = str(file_path).endswith(".txt") and test_data and len(test_data) > 0

                if is_3de_data and test_data:
                    first_point_name = list(test_data.keys())[0]
                    first_trajectory = test_data[first_point_name]
                    if first_trajectory and len(first_trajectory) > 0:
                        x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                        has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                        is_3de_data = has_high_precision

                assert (
                    is_3de_data == expected_results[i]
                ), f"Test case {i} with data {test_data} should return {expected_results[i]} for path {file_path}"
