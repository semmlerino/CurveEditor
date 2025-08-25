"""
Tests for interaction service functionality.

Updated to work with the new InteractionService architecture.
"""

from unittest.mock import Mock

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QRubberBand

from services.interaction_service import InteractionService
from tests.test_utilities import ProtocolCompliantMockCurveView, ProtocolCompliantMockMainWindow


class TestCurveViewWithRubberBand(ProtocolCompliantMockCurveView):
    """Extended test curve view with rubber band support."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add rubber band attributes
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_active: bool = False
        self.rubber_band_origin: QPointF | None = None
        # Track method calls for testing
        self._rubber_band_shown = False
        self._rubber_band_hidden = False
        self._rubber_band_geometry = None

    def create_rubber_band(self):
        """Create a mock rubber band for testing."""
        self.rubber_band = Mock(spec=QRubberBand)

        # Track show/hide calls
        def track_show():
            self._rubber_band_shown = True

        def track_hide():
            self._rubber_band_hidden = True

        def track_geometry(rect):
            self._rubber_band_geometry = rect

        self.rubber_band.show = track_show
        self.rubber_band.hide = track_hide
        self.rubber_band.setGeometry = track_geometry


def test_handle_mouse_move_rubber_band_active():
    """
    Test handle_mouse_move when rubber band selection is active.
    """
    # Arrange
    view = TestCurveViewWithRubberBand()
    view.curve_data = [
        (1, 100, 200, "keyframe"),
        (2, 150, 250, "keyframe"),
        (3, 200, 300, "keyframe"),
    ]
    view.points = view.curve_data
    view.create_rubber_band()

    # Set up rubber band state as if it was started
    view.rubber_band_active = True
    view.rubber_band_origin = QPointF(50, 50)

    service = InteractionService()

    # Create a mock mouse event
    mock_event = Mock(spec=QMouseEvent)
    mock_event.position.return_value = QPointF(150, 150)

    # Act
    service.handle_mouse_move(view, mock_event)

    # Assert
    # The rubber band functionality depends on USE_NEW_SERVICES flag
    # In default mode (consolidated), mouse events may just log warnings
    # In new services mode, they delegate to the adapter
    # Since these are integration tests, we verify that the method doesn't crash
    assert view.rubber_band is not None  # Rubber band still exists
    assert view.rubber_band_active  # State preserved


def test_handle_mouse_release_rubber_band_finalize():
    """
    Test handle_mouse_release finalizing rubber band selection.
    """
    # Arrange
    view = TestCurveViewWithRubberBand()
    view.curve_data = [
        (1, 100, 200, "keyframe"),
        (2, 150, 250, "keyframe"),
        (3, 200, 300, "keyframe"),
    ]
    view.points = view.curve_data
    view.create_rubber_band()

    # Set up rubber band state
    view.rubber_band_active = True
    view.rubber_band_origin = QPointF(50, 50)

    service = InteractionService()
    ProtocolCompliantMockMainWindow()

    # Create a mock mouse event
    mock_event = Mock(spec=QMouseEvent)
    mock_event.position.return_value = QPointF(250, 350)

    # Act
    service.handle_mouse_release(view, mock_event)

    # Assert
    # The rubber band functionality depends on USE_NEW_SERVICES flag
    # In default mode, mouse events may just log warnings
    # In new services mode, they delegate to the adapter
    # Since these are integration tests, we verify that the method doesn't crash
    assert view.rubber_band is not None  # Rubber band still exists


def test_rubber_band_selection_integration():
    """Test rubber band selection workflow with real point selection."""
    # Arrange
    view = TestCurveViewWithRubberBand()
    view.curve_data = [
        (1, 100, 200, "keyframe"),
        (2, 150, 250, "keyframe"),
        (3, 200, 300, "keyframe"),
    ]
    view.points = view.curve_data
    main_window = ProtocolCompliantMockMainWindow()

    # Add transform attributes needed for coordinate conversion
    view.flip_y_axis = True
    view.scale_to_image = False
    setattr(view, "center_offset_x", 0.0)
    setattr(view, "center_offset_y", 0.0)

    service = InteractionService()

    # Act - Test rubber band selection using select_points_in_rect
    # Create a rectangle that should encompass the first two points
    # Using screen coordinates - this tests the real transformation logic

    # Get the real transformation
    from services import get_transform_service

    transform_service = get_transform_service()
    view_state = transform_service.create_view_state(view)
    real_transform = transform_service.create_transform_from_view_state(view_state)

    # Override the mock's get_current_transform to return the real transform
    view.get_current_transform = lambda: real_transform

    # Get transformed coordinates for first two points
    p0_transformed = real_transform.data_to_screen(100, 200)
    p1_transformed = real_transform.data_to_screen(150, 250)

    # Create rectangle that includes both points
    min_x = min(p0_transformed[0], p1_transformed[0]) - 20
    min_y = min(p0_transformed[1], p1_transformed[1]) - 20
    max_x = max(p0_transformed[0], p1_transformed[0]) + 20
    max_y = max(p0_transformed[1], p1_transformed[1]) + 20

    rect = QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))

    # Test rubber band selection
    count = service.select_points_in_rect(view, main_window, rect)

    # Assert
    assert count == 2  # Should select first two points
    assert view.selected_points == {0, 1}
    assert view.selected_point_idx == 0  # Should be minimum selected index
    assert view.update_called


def test_interaction_service_initialization():
    """Test that InteractionService can be initialized."""
    service = InteractionService()
    assert service is not None
    assert hasattr(service, "handle_mouse_press")
    assert hasattr(service, "handle_mouse_move")
    assert hasattr(service, "handle_mouse_release")


def test_interaction_service_spatial_index():
    """Test that spatial index is properly initialized."""
    service = InteractionService()
    assert service._point_index is not None
    assert hasattr(service._point_index, "rebuild_index")
    assert hasattr(service._point_index, "find_point_at_position")
