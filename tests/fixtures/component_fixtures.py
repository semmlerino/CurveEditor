"""
Component fixtures for testing.

Contains fixtures that provide real component instances instead of mocks.
These should be preferred over mock objects when possible.
"""

import pytest

from tests.test_utilities import (
    TestCurveView,
    TestDataBuilder,
    TestMainWindow,
)


@pytest.fixture
def test_curve_view() -> TestCurveView:
    """Create a real test curve view instance.

    PREFER THIS over mock curve view fixtures.

    Returns:
        TestCurveView: A lightweight test curve view
    """
    return TestCurveView()


@pytest.fixture
def test_curve_view_with_data() -> TestCurveView:
    """Create a test curve view with sample data.

    Returns:
        TestCurveView: Curve view populated with test data
    """
    return TestDataBuilder.curve_view_with_data()


@pytest.fixture
def test_main_window() -> TestMainWindow:
    """Create a real test main window instance.

    PREFER THIS over mock main window fixtures.

    Returns:
        TestMainWindow: A lightweight test main window
    """
    return TestMainWindow()


# Factory Fixtures (Following Testing Guide Best Practices)


@pytest.fixture
def make_test_curve_view():
    """Factory for creating TestCurveView instances with custom data.

    Usage:
        def test_something(make_test_curve_view):
            view = make_test_curve_view()  # Default
            view_with_data = make_test_curve_view(
                curve_data=[(1, 100, 200), (2, 300, 400)]
            )

    Returns:
        Factory function that creates TestCurveView instances
    """

    def _make_test_curve_view(**kwargs):
        return TestCurveView(**kwargs)

    return _make_test_curve_view


@pytest.fixture
def make_point():
    """Factory for creating Point4 tuples.

    Usage:
        def test_points(make_point):
            point1 = make_point(1, 100, 200)  # frame, x, y
            point2 = make_point(2, 300, 400, "keyframe")  # with status

    Returns:
        Factory function that creates Point4 tuples
    """

    def _make_point(frame: int, x: float, y: float, status: str = "normal"):
        return (frame, x, y, status)

    return _make_point


@pytest.fixture
def make_curve_data():
    """Factory for creating curve data lists.

    Usage:
        def test_curves(make_curve_data):
            simple_curve = make_curve_data(3)  # 3 points
            complex_curve = make_curve_data(
                10,
                start_frame=5,
                x_multiplier=2.0
            )

    Returns:
        Factory function that creates curve data lists
    """

    def _make_curve_data(
        num_points: int = 5,
        start_frame: int = 1,
        x_multiplier: float = 100.0,
        y_multiplier: float = 200.0,
        status: str = "normal",
    ):
        return [(start_frame + i, i * x_multiplier, i * y_multiplier, status) for i in range(num_points)]

    return _make_curve_data


@pytest.fixture
def make_test_main_window():
    """Factory for creating TestMainWindow instances with custom settings.

    Usage:
        def test_windows(make_test_main_window):
            window = make_test_main_window()  # Default
            custom_window = make_test_main_window(
                default_directory="/custom/path"
            )

    Returns:
        Factory function that creates TestMainWindow instances
    """

    def _make_test_main_window(**kwargs):
        return TestMainWindow(**kwargs)

    return _make_test_main_window


@pytest.fixture
def test_main_window_with_data() -> TestMainWindow:
    """Create a test main window with sample data.

    Returns:
        TestMainWindow: Main window populated with test data
    """
    return TestDataBuilder.main_window_with_data()


@pytest.fixture
def test_curve_renderer():
    """Create a test curve renderer component.

    Returns:
        CurveRenderer: A renderer component for testing
    """
    from rendering import CurveRenderer

    return CurveRenderer()


@pytest.fixture
def test_selection_manager():
    """Create a test selection manager component.

    Returns:
        SelectionManager: A selection manager for testing
    """
    from ui.components import SelectionManager

    return SelectionManager()


@pytest.fixture
def test_data_manager():
    """Create a test data manager component.

    Returns:
        CurveDataManager: A data manager for testing
    """
    from ui.components import CurveDataManager

    return CurveDataManager()


@pytest.fixture
def test_transform_manager():
    """Create a test transform manager component.

    Returns:
        TransformManager: A transform manager for testing
    """
    from ui.components import TransformManager

    return TransformManager()


@pytest.fixture
def test_interaction_handler():
    """Create a test interaction handler component.

    Returns:
        InteractionHandler: An interaction handler for testing
    """
    from ui.components import InteractionHandler

    return InteractionHandler()


@pytest.fixture
def test_file_controller(test_main_window):
    """Create a test file controller.

    Args:
        test_main_window: Test main window fixture

    Returns:
        FileController: A file controller for testing
    """
    from ui.controllers import FileController

    return FileController(test_main_window)


@pytest.fixture
def test_edit_controller(test_main_window):
    """Create a test edit controller.

    Args:
        test_main_window: Test main window fixture

    Returns:
        EditController: An edit controller for testing
    """
    from ui.controllers import EditController

    return EditController(test_main_window)


@pytest.fixture
def test_view_controller(test_main_window):
    """Create a test view controller.

    Args:
        test_main_window: Test main window fixture

    Returns:
        ViewController: A view controller for testing
    """
    from ui.controllers import ViewController

    return ViewController(test_main_window)


@pytest.fixture
def test_timeline_controller(test_main_window):
    """Create a test timeline controller.

    Args:
        test_main_window: Test main window fixture

    Returns:
        TimelineController: A timeline controller for testing
    """
    from ui.controllers import TimelineController

    return TimelineController(test_main_window)


@pytest.fixture
def test_curve_controller(test_main_window):
    """Create a test curve controller.

    Args:
        test_main_window: Test main window fixture

    Returns:
        CurveController: A curve controller for testing
    """
    from ui.controllers import CurveController

    return CurveController(test_main_window)


@pytest.fixture
def integrated_curve_view(qapp):
    """Create a fully integrated curve view widget with all components.

    Args:
        qapp: Qt application fixture

    Returns:
        CurveViewWidget: Fully configured curve view widget
    """
    from ui.curve_view_widget_refactored import CurveViewWidget

    widget = CurveViewWidget()
    widget.resize(800, 600)

    # Initialize with test data
    widget.set_curve_data(
        [
            (1, 100.0, 200.0),
            (2, 150.0, 250.0),
            (3, 200.0, 300.0),
            (4, 250.0, 350.0),
            (5, 300.0, 400.0),
        ]
    )

    return widget


@pytest.fixture
def integrated_main_window(qapp):
    """Create a fully integrated main window with all controllers.

    Args:
        qapp: Qt application fixture

    Returns:
        MainWindow: Fully configured main window
    """
    from ui.main_window_refactored import MainWindow

    window = MainWindow()
    window.resize(1200, 800)

    # Initialize with test data
    if window.curve_widget:
        window.curve_widget.set_curve_data(
            [
                (1, 100.0, 200.0),
                (2, 150.0, 250.0),
                (3, 200.0, 300.0),
            ]
        )

    return window
