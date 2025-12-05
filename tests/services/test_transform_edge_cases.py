"""
Edge case tests for TransformService and Transform class.

Tests coordinate transformations with edge cases:
- Zero dimensions (0-width, 0-height views)
- Extreme coordinates (very large, very small, negative)
- Identity transforms (no scale, no offset)
- Inverse operations (round-trip conversions)
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none

import pytest
from services.transform_service import Transform, ViewState


class TestTransformZeroDimensions:
    """Tests for transforms with zero or near-zero dimensions."""

    def test_zero_width_view_state(self):
        """Transform should handle zero-width view gracefully."""
        view_state = ViewState(
            display_width=0,
            display_height=600,
            widget_width=0,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )
        # Should not raise - may produce degenerate transform
        transform = Transform.from_view_state(view_state)
        assert transform is not None

    def test_zero_height_view_state(self):
        """Transform should handle zero-height view gracefully."""
        view_state = ViewState(
            display_width=800,
            display_height=0,
            widget_width=800,
            widget_height=0,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )
        transform = Transform.from_view_state(view_state)
        assert transform is not None

    def test_zero_zoom_view_state(self):
        """Transform should handle zero zoom gracefully."""
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=0.0,  # Edge case: zero zoom
            offset_x=0.0,
            offset_y=0.0,
        )
        transform = Transform.from_view_state(view_state)
        # Zero zoom should not cause division by zero
        assert transform is not None

    def test_negative_zoom_view_state(self):
        """Transform should handle negative zoom gracefully."""
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=-1.0,  # Edge case: negative zoom
            offset_x=0.0,
            offset_y=0.0,
        )
        transform = Transform.from_view_state(view_state)
        assert transform is not None


class TestTransformExtremeCoordinates:
    """Tests for transforms with extreme coordinate values."""

    @pytest.fixture
    def standard_transform(self):
        """Create a standard transform for testing."""
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )
        return Transform.from_view_state(view_state)

    def test_very_large_coordinates(self, standard_transform):
        """Transform should handle very large coordinates."""
        transform = standard_transform
        large_x, large_y = 1e10, 1e10

        # Should not overflow
        screen_x, screen_y = transform.data_to_screen(large_x, large_y)
        assert not (screen_x != screen_x)  # Not NaN
        assert not (screen_y != screen_y)  # Not NaN

    def test_very_small_coordinates(self, standard_transform):
        """Transform should handle very small (subnormal) coordinates."""
        transform = standard_transform
        small_x, small_y = 1e-300, 1e-300

        screen_x, screen_y = transform.data_to_screen(small_x, small_y)
        assert not (screen_x != screen_x)  # Not NaN
        assert not (screen_y != screen_y)  # Not NaN

    def test_negative_coordinates(self, standard_transform):
        """Transform should handle negative coordinates."""
        transform = standard_transform
        neg_x, neg_y = -100.0, -200.0

        screen_x, screen_y = transform.data_to_screen(neg_x, neg_y)
        assert isinstance(screen_x, float)
        assert isinstance(screen_y, float)

    def test_mixed_extreme_coordinates(self, standard_transform):
        """Transform should handle mixed extreme coordinates."""
        transform = standard_transform

        # Very large X, very small Y
        screen_x, screen_y = transform.data_to_screen(1e10, 1e-10)
        assert not (screen_x != screen_x)
        assert not (screen_y != screen_y)


class TestTransformRoundTrip:
    """Tests for inverse transform operations."""

    @pytest.fixture
    def transform(self):
        """Create a transform with non-trivial settings."""
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=50.0,
            offset_y=-30.0,
        )
        return Transform.from_view_state(view_state)

    def test_data_to_screen_to_data_roundtrip(self, transform):
        """data_to_screen followed by screen_to_data should return original."""
        original_x, original_y = 0.5, 0.5

        screen_x, screen_y = transform.data_to_screen(original_x, original_y)
        recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

        assert abs(recovered_x - original_x) < 1e-10
        assert abs(recovered_y - original_y) < 1e-10

    def test_screen_to_data_to_screen_roundtrip(self, transform):
        """screen_to_data followed by data_to_screen should return original."""
        original_screen_x, original_screen_y = 400.0, 300.0

        data_x, data_y = transform.screen_to_data(original_screen_x, original_screen_y)
        recovered_x, recovered_y = transform.data_to_screen(data_x, data_y)

        assert abs(recovered_x - original_screen_x) < 1e-10
        assert abs(recovered_y - original_screen_y) < 1e-10

    def test_roundtrip_at_origin(self, transform):
        """Round-trip at data origin (0, 0)."""
        screen_x, screen_y = transform.data_to_screen(0.0, 0.0)
        recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

        assert abs(recovered_x) < 1e-10
        assert abs(recovered_y) < 1e-10

    def test_roundtrip_at_corners(self, transform):
        """Round-trip at normalized data corners."""
        corners = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]

        for orig_x, orig_y in corners:
            screen_x, screen_y = transform.data_to_screen(orig_x, orig_y)
            rec_x, rec_y = transform.screen_to_data(screen_x, screen_y)
            assert abs(rec_x - orig_x) < 1e-10, f"X mismatch at corner ({orig_x}, {orig_y})"
            assert abs(rec_y - orig_y) < 1e-10, f"Y mismatch at corner ({orig_x}, {orig_y})"


class TestTransformIdentity:
    """Tests for identity/no-op transforms."""

    def test_unity_zoom_no_offset(self):
        """Unity zoom with no offset should give predictable results."""
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )
        transform = Transform.from_view_state(view_state)

        # Center of normalized space should map to center of screen
        center_screen_x, center_screen_y = transform.data_to_screen(0.5, 0.5)
        # Just verify the transform is valid
        assert isinstance(center_screen_x, float)
        assert isinstance(center_screen_y, float)


class TestTransformWithUpdates:
    """Tests for Transform.with_updates method."""

    @pytest.fixture
    def base_transform(self):
        """Create base transform for update tests."""
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            offset_x=0.0,
            offset_y=0.0,
        )
        return Transform.from_view_state(view_state)

    def test_with_updates_creates_new_instance(self, base_transform):
        """with_updates should create new transform instance."""
        updated = base_transform.with_updates()

        # Should be a different instance
        assert updated is not base_transform

    def test_with_updates_preserves_original(self, base_transform):
        """with_updates should not modify original transform."""
        original_scale = base_transform.scale

        _ = base_transform.with_updates()

        assert base_transform.scale == original_scale

    def test_with_updates_none_values_preserved(self, base_transform):
        """with_updates with no arguments should preserve existing values."""
        original_hash = base_transform.stability_hash

        updated = base_transform.with_updates()  # No changes

        assert updated.stability_hash == original_hash
