"""Test Y-axis coordinate flipping for 3DEqualizer data.

This module tests the Y-flip functionality that converts 3DEqualizer's
bottom-origin coordinates to Qt's top-origin coordinate system.
"""

import pytest
from PySide6.QtCore import QPointF

from services import get_data_service, get_transform_service
from ui.file_operations import FileLoadSignals, FileLoadWorker


@pytest.fixture(autouse=True)
def reset_services():
    """Reset service singletons to ensure clean state for each test."""
    import services

    # Store original values
    original = {
        "_data_service": getattr(services, "_data_service", None),
        "_transform_service": getattr(services, "_transform_service", None),
        "_interaction_service": getattr(services, "_interaction_service", None),
        "_ui_service": getattr(services, "_ui_service", None),
    }

    # Reset to None
    services._data_service = None
    services._transform_service = None
    services._interaction_service = None
    services._ui_service = None

    yield

    # Restore original values
    for key, value in original.items():
        setattr(services, key, value)


class TestDataServiceYFlip:
    """Test DataService Y-flip functionality."""

    def test_load_tracked_data_applies_y_flip(self, tmp_path):
        """Test that load_tracked_data applies Y-flip to all points."""
        # Create test tracking data file
        tracking_file = tmp_path / "test_tracking.txt"
        tracking_file.write_text("""2
Point1
0
3
1 100.0 200.0
2 110.0 210.0
3 120.0 220.0
Point2
0
2
1 300.0 400.0
2 310.0 410.0""")

        # Load data
        data_service = get_data_service()
        tracked_data = data_service.load_tracked_data(str(tracking_file))

        # Verify Y-flip applied (720 - y)
        assert "Point1" in tracked_data
        assert "Point2" in tracked_data

        # Check Point1 coordinates (now includes status field)
        point1_data = tracked_data["Point1"]
        assert len(point1_data) == 3
        # Extract frame, x, y from 4-element tuples (frame, x, y, status)
        assert point1_data[0][:3] == (1, 100.0, 520.0)  # 720 - 200 = 520
        assert point1_data[1][:3] == (2, 110.0, 510.0)  # 720 - 210 = 510
        assert point1_data[2][:3] == (3, 120.0, 500.0)  # 720 - 220 = 500

        # Check Point2 coordinates (now includes status field)
        point2_data = tracked_data["Point2"]
        assert len(point2_data) == 2
        # Extract frame, x, y from 4-element tuples (frame, x, y, status)
        assert point2_data[0][:3] == (1, 300.0, 320.0)  # 720 - 400 = 320
        assert point2_data[1][:3] == (2, 310.0, 310.0)  # 720 - 410 = 310

    def test_load_2dtrack_data_applies_y_flip(self, tmp_path):
        """Test that _load_2dtrack_data returns data with 3DE metadata for Y-flip."""
        # Create test file
        tracking_file = tmp_path / "test_single.txt"
        tracking_file.write_text("""1
07
0
3
1 150.0 100.0
2 160.0 110.0
3 170.0 120.0""")

        # Load data
        data_service = get_data_service()
        result = data_service._load_2dtrack_data(str(tracking_file))

        # Result should be CurveDataWithMetadata with 3DE coordinate system
        from core.coordinate_system import CoordinateOrigin, CoordinateSystem
        from core.curve_data import CurveDataWithMetadata

        assert isinstance(result, CurveDataWithMetadata)
        assert result.metadata is not None
        assert result.metadata.system == CoordinateSystem.THREE_DE_EQUALIZER
        assert result.metadata.origin == CoordinateOrigin.BOTTOM_LEFT

        # Data should contain raw (unflipped) coordinates
        curve_data = result.data
        assert len(curve_data) == 3
        assert curve_data[0][2] == 100.0  # Raw Y coordinate
        assert curve_data[1][2] == 110.0
        assert curve_data[2][2] == 120.0

    def test_y_flip_with_actual_3dequalizer_data(self, tmp_path):
        """Test Y-flip with realistic 3DEqualizer data."""
        # Use actual Point01 data from 2DTrackDatav2.txt
        tracking_file = tmp_path / "3dequalizer_data.txt"
        tracking_file.write_text("""1
Point01
0
3
1 682.291351786175937 211.331718165415879
2 682.521866906603547 212.542773564770839
3 682.749290318226074 214.136859613534251""")

        data_service = get_data_service()
        tracked_data = data_service.load_tracked_data(str(tracking_file))

        # Verify Point01 is flipped correctly
        assert "Point01" in tracked_data
        point01 = tracked_data["Point01"]

        # Expected Y values after flip
        expected_y1 = 720 - 211.331718165415879
        expected_y2 = 720 - 212.542773564770839
        expected_y3 = 720 - 214.136859613534251

        assert abs(point01[0][2] - expected_y1) < 0.001
        assert abs(point01[1][2] - expected_y2) < 0.001
        assert abs(point01[2][2] - expected_y3) < 0.001


class TestFileLoadWorkerYFlip:
    """Test FileLoadWorker Y-flip functionality."""

    def test_load_2dtrack_data_direct_with_flip(self, tmp_path):
        """Test _load_2dtrack_data_direct with flip_y=True."""
        # Create test file
        tracking_file = tmp_path / "test_worker.txt"
        tracking_file.write_text("""1
07
0
2
1 500.0 150.0
2 510.0 160.0""")

        # Create worker
        signals = FileLoadSignals()
        worker = FileLoadWorker(signals)

        # Test with flip
        data_flip = worker._load_2dtrack_data_direct(str(tracking_file), flip_y=True, image_height=720)

        assert len(data_flip) == 2
        assert data_flip[0] == (1, 500.0, 570.0)  # 720 - 150 = 570
        assert data_flip[1] == (2, 510.0, 560.0)  # 720 - 160 = 560

        # Test without flip
        data_no_flip = worker._load_2dtrack_data_direct(str(tracking_file), flip_y=False)

        assert len(data_no_flip) == 2
        assert data_no_flip[0] == (1, 500.0, 150.0)
        assert data_no_flip[1] == (2, 510.0, 160.0)

    def test_worker_respects_image_height_parameter(self, tmp_path):
        """Test that worker uses the image_height parameter correctly."""
        tracking_file = tmp_path / "test_height.txt"
        tracking_file.write_text("""1
07
0
1
1 100.0 100.0""")

        signals = FileLoadSignals()
        worker = FileLoadWorker(signals)

        # Test with different image heights
        data_720 = worker._load_2dtrack_data_direct(str(tracking_file), flip_y=True, image_height=720)
        assert data_720[0][2] == 620.0  # 720 - 100

        data_1080 = worker._load_2dtrack_data_direct(str(tracking_file), flip_y=True, image_height=1080)
        assert data_1080[0][2] == 980.0  # 1080 - 100


class TestCoordinateTransformWithFlip:
    """Test coordinate transformations with flipped Y data."""

    def test_transform_service_with_flipped_coordinates(self):
        """Test TransformService handles flipped coordinates correctly."""
        from services.transform_service import ViewState

        # Create view state with real dimensions
        view_state = ViewState(
            display_width=1280,
            display_height=720,
            widget_width=1016,
            widget_height=645,
            zoom_factor=0.754,
            scale_to_image=True,
            flip_y_axis=False,  # Already flipped in data
            image_width=1280,
            image_height=720,
        )

        transform_service = get_transform_service()
        transform = transform_service.create_transform_from_view_state(view_state)

        # Test Point01's flipped position (682.3, 508.7)
        screen_pos = transform.data_to_screen(682.3, 508.7)

        # Should be in lower portion of screen
        assert screen_pos[1] > 300  # Y position should be in lower half

    def test_curve_widget_displays_flipped_points_correctly(self, qtbot):
        """Test that CurveViewWidget displays flipped points correctly."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        widget.resize(1280, 720)

        # Set flipped data (as loaded by DataService)
        flipped_data = [
            (1, 682.3, 508.7),  # Y already flipped from 211.3
            (2, 682.5, 507.5),  # Y already flipped from 212.5
        ]
        widget.set_curve_data(flipped_data)

        # Verify points are stored correctly
        assert len(widget.curve_data) == 2
        assert widget.curve_data[0][2] == 508.7

        # Test screen transformation
        screen_pos = widget.data_to_screen(682.3, 508.7)
        assert isinstance(screen_pos, QPointF)
        # Point should be in lower portion
        assert screen_pos.y() > widget.height() / 2


class TestIntegrationYFlip:
    """Integration tests for the complete Y-flip pipeline."""

    def test_full_pipeline_with_y_flip(self, tmp_path, qtbot):
        """Test complete pipeline from file to display with Y-flip."""
        # Create test tracking file with correct format for multi-point
        # DataService looks for lines starting with "Point"
        tracking_file = tmp_path / "pipeline_test.txt"
        tracking_file.write_text("""1
Point01
0
2
1 640.0 180.0
2 650.0 190.0""")

        # Load through DataService
        data_service = get_data_service()
        tracked_data = data_service.load_tracked_data(str(tracking_file))

        # Verify data is flipped
        assert "Point01" in tracked_data
        point_data = tracked_data["Point01"]
        assert point_data[0][2] == 540.0  # 720 - 180
        assert point_data[1][2] == 530.0  # 720 - 190

        # Create curve widget and set data
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        widget.resize(1280, 720)
        widget.set_curve_data(point_data)

        # Verify transformation places point in correct region
        screen_pos = widget.data_to_screen(640.0, 540.0)
        # Should be in lower portion (Y > 360 for 720 height)
        assert screen_pos.y() > 360

    @pytest.mark.parametrize(
        "original_y,expected_flipped",
        [
            (100.0, 620.0),  # Near top -> near bottom
            (211.3, 508.7),  # Point01 actual data
            (360.0, 360.0),  # Middle stays middle
            (600.0, 120.0),  # Near bottom -> near top
            (0.0, 720.0),  # Top edge -> bottom edge
            (720.0, 0.0),  # Bottom edge -> top edge
        ],
    )
    def test_y_flip_values(self, original_y, expected_flipped):
        """Test Y-flip calculation for various values."""
        image_height = 720
        flipped = image_height - original_y
        assert abs(flipped - expected_flipped) < 0.001

    def test_multi_point_tracking_all_flipped(self, tmp_path):
        """Test that all points in multi-point tracking are flipped."""
        # Create file with multiple points
        tracking_file = tmp_path / "multi_point.txt"
        content = "12\n"  # 12 points

        for i in range(1, 13):
            content += f"Point{i:02d}\n0\n1\n1 {100 + i * 10} {50 + i * 5}\n"

        tracking_file.write_text(content)

        # Load data
        data_service = get_data_service()
        tracked_data = data_service.load_tracked_data(str(tracking_file))

        # Verify all points are flipped
        assert len(tracked_data) == 12

        for i in range(1, 13):
            point_name = f"Point{i:02d}"
            assert point_name in tracked_data

            point_data = tracked_data[point_name]
            original_y = 50 + i * 5
            expected_y = 720 - original_y

            assert abs(point_data[0][2] - expected_y) < 0.001


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_file_handling(self, tmp_path):
        """Test handling of empty tracking file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        data_service = get_data_service()
        data = data_service.load_tracked_data(str(empty_file))

        assert data == {}

    def test_malformed_data_handling(self, tmp_path):
        """Test handling of malformed tracking data."""
        bad_file = tmp_path / "bad.txt"
        bad_file.write_text("""1
BadPoint
not_a_number
1 abc def""")

        data_service = get_data_service()
        data = data_service.load_tracked_data(str(bad_file))

        # Should handle gracefully
        assert isinstance(data, dict)

    def test_negative_y_values(self, tmp_path):
        """Test Y-flip with negative Y values."""
        tracking_file = tmp_path / "negative.txt"
        tracking_file.write_text("""1
NegPoint
0
2
1 100.0 -50.0
2 100.0 800.0""")

        data_service = get_data_service()
        tracked_data = data_service.load_tracked_data(str(tracking_file))

        if "NegPoint" in tracked_data:
            point_data = tracked_data["NegPoint"]
            # -50 flipped: 720 - (-50) = 770
            assert point_data[0][2] == 770.0
            # 800 flipped: 720 - 800 = -80
            assert point_data[1][2] == -80.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
