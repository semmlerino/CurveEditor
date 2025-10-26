#!/usr/bin/env python
"""
Tests for TransformService.get_transform() helper method.

This test suite validates the convenience method that simplifies the 3-step
transform pattern into a single method call.
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

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from services.transform_service import Transform, TransformService

if TYPE_CHECKING:
    from ui.service_facade import ServiceFacade


class MockCurveView:
    """Mock CurveView for testing.

    This is a minimal mock that only implements the attributes actually used
    by TransformService. The protocol requires many more attributes, but they
    are accessed via getattr() with defaults in the implementation.
    """

    def __init__(
        self,
        zoom_factor: float = 1.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        width: int = 1920,
        height: int = 1080,
        flip_y_axis: bool = True,
    ):
        self.zoom_factor: float = zoom_factor
        self.offset_x: float = offset_x
        self.offset_y: float = offset_y
        self.width_value: int = width
        self.height_value: int = height
        self.flip_y_axis: bool = flip_y_axis
        self.manual_offset_x: float = 0.0
        self.manual_offset_y: float = 0.0

    def width(self) -> int:
        """Return widget width."""
        return self.width_value

    def height(self) -> int:
        """Return widget height."""
        return self.height_value


class TestGetTransformHelper:
    """Test suite for TransformService.get_transform() convenience method."""

    @pytest.fixture
    def transform_service(self) -> TransformService:
        """Create a TransformService instance."""
        return TransformService()

    @pytest.fixture
    def mock_view(self) -> MockCurveView:
        """Create a mock CurveView."""
        return MockCurveView()

    def test_get_transform_returns_transform_object(
        self, transform_service: TransformService, mock_view: MockCurveView
    ) -> None:
        """Test that get_transform returns a Transform instance."""
        transform = transform_service.get_transform(mock_view)

        assert isinstance(transform, Transform)
        assert transform is not None

    def test_get_transform_equivalent_to_two_step_pattern(
        self, transform_service: TransformService, mock_view: MockCurveView
    ) -> None:
        """Test that get_transform produces same result as 2-step pattern."""
        # Old pattern (2 steps)
        view_state = transform_service.create_view_state(mock_view)
        transform_old = transform_service.create_transform_from_view_state(view_state)

        # New pattern (1 step)
        transform_new = transform_service.get_transform(mock_view)

        # Should produce identical transforms
        assert transform_old.scale == transform_new.scale
        assert transform_old.center_offset == transform_new.center_offset
        assert transform_old.pan_offset == transform_new.pan_offset
        assert transform_old.flip_y == transform_new.flip_y
        assert transform_old.display_height == transform_new.display_height

    def test_get_transform_with_different_zoom_levels(self, transform_service: TransformService) -> None:
        """Test get_transform with various zoom levels."""
        zoom_levels = [0.5, 1.0, 2.0, 5.0, 10.0]

        for zoom in zoom_levels:
            view = MockCurveView(zoom_factor=zoom)
            transform = transform_service.get_transform(view)

            assert transform.scale == zoom
            assert isinstance(transform, Transform)

    def test_get_transform_with_pan_offsets(self, transform_service: TransformService) -> None:
        """Test get_transform with different pan offsets."""
        view = MockCurveView(offset_x=100.0, offset_y=-50.0)
        transform = transform_service.get_transform(view)

        assert transform.pan_offset == (100.0, -50.0)

    def test_get_transform_with_different_display_sizes(self, transform_service: TransformService) -> None:
        """Test get_transform with various widget sizes."""
        sizes = [(1920, 1080), (1280, 720), (3840, 2160)]

        for width, height in sizes:
            view = MockCurveView(width=width, height=height)
            transform = transform_service.get_transform(view)

            # Transform is created successfully (display_height comes from image, not widget)
            assert isinstance(transform, Transform)

    def test_get_transform_with_y_flip(self, transform_service: TransformService) -> None:
        """Test get_transform respects Y-axis flip setting."""
        # With Y flip (default)
        view_flipped = MockCurveView(flip_y_axis=True)
        transform_flipped = transform_service.get_transform(view_flipped)
        assert transform_flipped.flip_y is True

        # Without Y flip
        view_normal = MockCurveView(flip_y_axis=False)
        transform_normal = transform_service.get_transform(view_normal)
        assert transform_normal.flip_y is False

    def test_get_transform_coordinate_conversion(self, transform_service: TransformService) -> None:
        """Test that transform from get_transform can convert coordinates."""
        view = MockCurveView(zoom_factor=2.0, offset_x=50.0, offset_y=25.0)
        transform = transform_service.get_transform(view)

        # Test data to screen conversion
        screen_x, screen_y = transform.data_to_screen(100.0, 200.0)
        assert isinstance(screen_x, int | float)
        assert isinstance(screen_y, int | float)

        # Test screen to data conversion (round trip)
        data_x, data_y = transform.screen_to_data(screen_x, screen_y)
        assert isinstance(data_x, int | float)
        assert isinstance(data_y, int | float)
        assert abs(data_x - 100.0) < 0.01
        assert abs(data_y - 200.0) < 0.01

    def test_get_transform_with_complex_view_state(self, transform_service: TransformService) -> None:
        """Test get_transform with complex view configuration."""
        view = MockCurveView(zoom_factor=3.5, offset_x=150.0, offset_y=-75.0, width=2560, height=1440, flip_y_axis=True)

        transform = transform_service.get_transform(view)

        assert transform.scale == 3.5
        assert transform.pan_offset == (150.0, -75.0)
        # display_height comes from image dimensions, not widget height
        assert isinstance(transform.display_height, int)
        assert transform.flip_y is True

    def test_get_transform_multiple_calls_independent(self, transform_service: TransformService) -> None:
        """Test that multiple get_transform calls are independent."""
        view1 = MockCurveView(zoom_factor=1.0)
        view2 = MockCurveView(zoom_factor=2.0)

        transform1 = transform_service.get_transform(view1)
        transform2 = transform_service.get_transform(view2)

        # Should be different objects
        assert transform1 is not transform2
        # With different scales
        assert transform1.scale == 1.0
        assert transform2.scale == 2.0

    def test_get_transform_thread_safety(self, transform_service: TransformService) -> None:
        """Test that get_transform is thread-safe (basic smoke test)."""
        import threading

        view = MockCurveView()
        results: list[Transform | None] = [None] * 10

        def create_transform(index: int) -> None:
            results[index] = transform_service.get_transform(view)

        threads = [threading.Thread(target=create_transform, args=(i,)) for i in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                import warnings

                warnings.warn(f"Thread {thread.name} did not stop within timeout", stacklevel=2)

        # All should have succeeded
        assert all(isinstance(r, Transform) for r in results)
        # All should have same scale
        assert all(r.scale == view.zoom_factor for r in results if r is not None)


class TestServiceFacadeGetTransform:
    """Test ServiceFacade.get_transform() method."""

    @pytest.fixture
    def service_facade(self) -> ServiceFacade:
        """Create ServiceFacade instance."""
        from ui.service_facade import ServiceFacade

        return ServiceFacade()

    @pytest.fixture
    def mock_view(self) -> MockCurveView:
        """Create a mock CurveView."""
        return MockCurveView()

    def test_service_facade_get_transform_available(self, service_facade, mock_view: MockCurveView) -> None:  # type: ignore[no-untyped-def]
        """Test that ServiceFacade.get_transform is available."""
        transform = service_facade.get_transform(mock_view)

        # Should return Transform or None (depends on service availability)
        assert transform is None or isinstance(transform, Transform)

    def test_service_facade_get_transform_with_service_available(
        self,
        service_facade,
        mock_view: MockCurveView,  # type: ignore[no-untyped-def]
    ) -> None:
        """Test ServiceFacade.get_transform when transform service is available."""
        # Ensure transform service is available
        if service_facade.is_service_available("transform"):
            transform = service_facade.get_transform(mock_view)
            assert isinstance(transform, Transform)


class TestGetTransformDocumentation:
    """Test that documentation is clear and helpful."""

    def test_get_transform_has_docstring(self) -> None:
        """Test that get_transform has comprehensive docstring."""
        from services.transform_service import TransformService

        assert TransformService.get_transform.__doc__ is not None
        docstring = TransformService.get_transform.__doc__

        # Should mention the convenience nature
        assert "convenience" in docstring.lower() or "combines" in docstring.lower()

        # Should show the pattern comparison
        assert "old" in docstring.lower() or "new" in docstring.lower()

    def test_service_facade_get_transform_has_docstring(self) -> None:
        """Test that ServiceFacade.get_transform has docstring."""
        from ui.service_facade import ServiceFacade

        assert ServiceFacade.get_transform.__doc__ is not None
        docstring = ServiceFacade.get_transform.__doc__

        # Should mention the convenience nature
        assert "convenience" in docstring.lower() or "combines" in docstring.lower()
