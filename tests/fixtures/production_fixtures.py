"""
Production-realistic test fixtures.

Provides factory fixtures and helpers for testing real user workflows.
Follows pytest best practices:
- Factory as fixture pattern for multiple uses per test
- Explicit fixture dependencies for clarity
- Production-realistic state management
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from collections.abc import Callable
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from core.type_aliases import CurveDataList
from ui.curve_view_widget import CurveViewWidget


@pytest.fixture
def production_widget_factory(curve_view_widget: CurveViewWidget, qtbot) -> Callable[..., CurveViewWidget]:
    """Factory fixture for production-ready widget states.

    Returns function to create widget in various production configurations.
    Aligns with pytest "factory as fixture" pattern for multiple uses per test.

    Args:
        curve_view_widget: Base curve view widget fixture
        qtbot: pytest-qt bot for Qt operations

    Returns:
        Factory function that configures and returns production-ready widget

    Example:
        ```python
        def test_zoom(production_widget_factory, safe_test_data_factory):
            # Create widget with data, shown and rendered
            widget = production_widget_factory(
                curve_data=safe_test_data_factory(5)
            )

            # Create another configuration in same test
            widget = production_widget_factory(
                curve_data=safe_test_data_factory(10, spacing=50.0),
                wait_for_render=False
            )
        ```
    """

    def _create(
        curve_data: CurveDataList | None = None, show: bool = True, wait_for_render: bool = True
    ) -> CurveViewWidget:
        """Configure widget in production-ready state.

        Args:
            curve_data: Optional curve data to set
            show: Whether to show widget (triggers paint event)
            wait_for_render: Whether to wait for paint + cache rebuild

        Returns:
            Configured widget ready for production testing
        """
        if curve_data:
            from stores.application_state import get_application_state

            app_state = get_application_state()
            app_state.set_curve_data("test_curve", curve_data)
            app_state.set_active_curve("test_curve")
            curve_view_widget.set_curve_data(curve_data)

        if show:
            curve_view_widget.show()
            qtbot.waitExposed(curve_view_widget)
            if wait_for_render:
                qtbot.wait(50)  # Allow paint event + cache rebuild

        return curve_view_widget

    return _create


@pytest.fixture
def safe_test_data_factory() -> Callable[..., CurveDataList]:
    """Factory for creating test data avoiding (0,0) boundary issues.

    Returns function to generate test data with configurable spacing.
    Ensures all points are away from widget edges where QTest.mouseClick
    has boundary issues.

    Returns:
        Factory function that generates safe test data

    Example:
        ```python
        def test_selection(safe_test_data_factory):
            # 5 points starting at (50,50), spaced 100px apart
            data = safe_test_data_factory(5)

            # 10 points with tighter spacing
            dense_data = safe_test_data_factory(10, spacing=50.0)

            # Start further from edge
            margin_data = safe_test_data_factory(3, start_margin=100.0)
        ```
    """

    def _create(num_points: int, start_margin: float = 50.0, spacing: float = 100.0) -> CurveDataList:
        """Generate test data with safe coordinates.

        Args:
            num_points: Number of points to generate
            start_margin: Starting offset from (0,0) in pixels
            spacing: Distance between consecutive points

        Returns:
            List of (frame, x, y) tuples safe for QTest operations
        """
        return [(i + 1, start_margin + i * spacing, start_margin + i * spacing) for i in range(num_points)]

    return _create


@pytest.fixture
def user_interaction(qtbot) -> Any:
    """Fixture providing user interaction helpers.

    Returns object with methods simulating production user actions.
    Aligns with pytest-qt recommendation: prefer widget methods,
    but use simulation for mouse/keyboard when needed.

    Args:
        qtbot: pytest-qt bot for Qt operations

    Returns:
        Helper object with interaction methods

    Example:
        ```python
        def test_ctrl_click(production_widget_factory, safe_test_data_factory,
                           user_interaction):
            widget = production_widget_factory(safe_test_data_factory(5))

            # Select first point
            user_interaction.select_point(widget, 0)

            # Ctrl+click second point
            user_interaction.select_point(widget, 1, ctrl=True)

            assert len(widget.selected_indices) == 2
        ```
    """

    class UserInteraction:
        """Helper for simulating production user interactions."""

        def click(
            self,
            view: CurveViewWidget,
            data_x: float,
            data_y: float,
            modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
        ) -> None:
            """Simulate production-realistic click at data coordinates.

            Args:
                view: Curve view widget
                data_x: X coordinate in data space
                data_y: Y coordinate in data space
                modifier: Keyboard modifier (Ctrl, Shift, etc.)
            """
            from services import get_transform_service

            transform = get_transform_service().get_transform(view)
            screen_x, screen_y = transform.data_to_screen(data_x, data_y)

            QTest.mouseClick(view, Qt.MouseButton.LeftButton, modifier, QPointF(screen_x, screen_y).toPoint())
            qtbot.wait(10)

        def ctrl_click(self, view: CurveViewWidget, data_x: float, data_y: float) -> None:
            """Ctrl+click at data coordinates.

            Args:
                view: Curve view widget
                data_x: X coordinate in data space
                data_y: Y coordinate in data space
            """
            self.click(view, data_x, data_y, Qt.KeyboardModifier.ControlModifier)

        def select_point(self, view: CurveViewWidget, point_index: int, ctrl: bool = False) -> None:
            """Select point by index using production workflow.

            Args:
                view: Curve view widget
                point_index: Index of point to select
                ctrl: Whether to use Ctrl modifier for multi-selection

            Raises:
                pytest.Failed: If no active curve or index out of range
            """
            from stores.application_state import get_application_state

            app_state = get_application_state()
            if (cd := app_state.active_curve_data) is None:
                pytest.fail("No active curve for selection")

            _, curve_data = cd
            if point_index >= len(curve_data):
                pytest.fail(f"Point {point_index} out of range")

            point = curve_data[point_index]
            if len(point) < 3:
                pytest.fail(f"Invalid point data at index {point_index}")

            _, x, y = point[:3]
            modifier = Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier
            self.click(view, float(x), float(y), modifier)

    return UserInteraction()
