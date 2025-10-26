"""Tests for VisualSettings dataclass.

Validates:
    - Default values match current_defaults.txt
    - All 6 numeric field validations work correctly
    - QColor default factories create independent instances
    - Mutability (can modify fields after creation)
    - 100% coverage of VisualSettings class
"""

import pytest
from PySide6.QtGui import QColor

from rendering.visual_settings import VisualSettings


class TestVisualSettingsDefaults:
    """Test default values match current behavior (current_defaults.txt)."""

    def test_display_toggles_defaults(self) -> None:
        """Verify all 6 display toggle defaults."""
        visual = VisualSettings()
        assert visual.show_grid is False
        assert visual.show_points is True
        assert visual.show_lines is True
        assert visual.show_labels is False
        assert visual.show_velocity_vectors is False
        assert visual.show_all_frame_numbers is False

    def test_grid_settings_defaults(self) -> None:
        """Verify all 3 grid setting defaults."""
        visual = VisualSettings()
        assert visual.grid_size == 50
        assert visual.grid_color == QColor(100, 100, 100, 50)
        assert visual.grid_line_width == 1

    def test_point_rendering_defaults(self) -> None:
        """Verify all 2 point rendering defaults."""
        visual = VisualSettings()
        assert visual.point_radius == 5
        assert visual.selected_point_radius == 7

    def test_line_rendering_defaults(self) -> None:
        """Verify all 4 line rendering defaults."""
        visual = VisualSettings()
        assert visual.line_color == QColor(200, 200, 200)
        assert visual.line_width == 2
        assert visual.selected_line_color == QColor(255, 255, 100)
        assert visual.selected_line_width == 3


class TestVisualSettingsValidation:
    """Test __post_init__ validation for all 6 numeric fields."""

    def test_point_radius_validation(self) -> None:
        """point_radius must be > 0."""
        with pytest.raises(ValueError, match="point_radius must be > 0"):
            VisualSettings(point_radius=0)
        with pytest.raises(ValueError, match="point_radius must be > 0"):
            VisualSettings(point_radius=-5)

    def test_selected_point_radius_validation(self) -> None:
        """selected_point_radius must be > 0."""
        with pytest.raises(ValueError, match="selected_point_radius must be > 0"):
            VisualSettings(selected_point_radius=0)
        with pytest.raises(ValueError, match="selected_point_radius must be > 0"):
            VisualSettings(selected_point_radius=-3)

    def test_line_width_validation(self) -> None:
        """line_width must be > 0."""
        with pytest.raises(ValueError, match="line_width must be > 0"):
            VisualSettings(line_width=0)
        with pytest.raises(ValueError, match="line_width must be > 0"):
            VisualSettings(line_width=-1)

    def test_selected_line_width_validation(self) -> None:
        """selected_line_width must be > 0."""
        with pytest.raises(ValueError, match="selected_line_width must be > 0"):
            VisualSettings(selected_line_width=0)
        with pytest.raises(ValueError, match="selected_line_width must be > 0"):
            VisualSettings(selected_line_width=-2)

    def test_grid_size_validation(self) -> None:
        """grid_size must be > 0."""
        with pytest.raises(ValueError, match="grid_size must be > 0"):
            VisualSettings(grid_size=0)
        with pytest.raises(ValueError, match="grid_size must be > 0"):
            VisualSettings(grid_size=-10)

    def test_grid_line_width_validation(self) -> None:
        """grid_line_width must be > 0."""
        with pytest.raises(ValueError, match="grid_line_width must be > 0"):
            VisualSettings(grid_line_width=0)
        with pytest.raises(ValueError, match="grid_line_width must be > 0"):
            VisualSettings(grid_line_width=-1)

    def test_valid_positive_values(self) -> None:
        """Valid positive values should not raise errors."""
        # Should not raise
        visual = VisualSettings(
            point_radius=10,
            selected_point_radius=15,
            line_width=5,
            selected_line_width=7,
            grid_size=100,
            grid_line_width=2,
        )
        assert visual.point_radius == 10
        assert visual.selected_point_radius == 15
        assert visual.line_width == 5
        assert visual.selected_line_width == 7
        assert visual.grid_size == 100
        assert visual.grid_line_width == 2


class TestVisualSettingsQColorFactories:
    """Test QColor default factories create independent instances."""

    def test_grid_color_factory(self) -> None:
        """Each instance gets independent grid_color."""
        visual1 = VisualSettings()
        visual2 = VisualSettings()

        # Same initial value
        assert visual1.grid_color == QColor(100, 100, 100, 50)
        assert visual2.grid_color == QColor(100, 100, 100, 50)

        # Independent instances
        visual1.grid_color.setRed(255)
        assert visual1.grid_color.red() == 255
        assert visual2.grid_color.red() == 100  # Unchanged

    def test_line_color_factory(self) -> None:
        """Each instance gets independent line_color."""
        visual1 = VisualSettings()
        visual2 = VisualSettings()

        # Same initial value
        assert visual1.line_color == QColor(200, 200, 200)
        assert visual2.line_color == QColor(200, 200, 200)

        # Independent instances
        visual1.line_color.setBlue(100)
        assert visual1.line_color.blue() == 100
        assert visual2.line_color.blue() == 200  # Unchanged

    def test_selected_line_color_factory(self) -> None:
        """Each instance gets independent selected_line_color."""
        visual1 = VisualSettings()
        visual2 = VisualSettings()

        # Same initial value
        assert visual1.selected_line_color == QColor(255, 255, 100)
        assert visual2.selected_line_color == QColor(255, 255, 100)

        # Independent instances
        visual1.selected_line_color.setGreen(50)
        assert visual1.selected_line_color.green() == 50
        assert visual2.selected_line_color.green() == 255  # Unchanged


class TestVisualSettingsMutability:
    """Test VisualSettings is mutable (can modify fields)."""

    def test_can_modify_display_toggles(self) -> None:
        """Display toggles can be changed after creation."""
        visual = VisualSettings()
        visual.show_grid = True
        visual.show_points = False
        assert visual.show_grid is True
        assert visual.show_points is False

    def test_can_modify_numeric_fields(self) -> None:
        """Numeric fields can be changed after creation."""
        visual = VisualSettings()
        visual.point_radius = 10
        visual.line_width = 5
        visual.grid_size = 100
        assert visual.point_radius == 10
        assert visual.line_width == 5
        assert visual.grid_size == 100

    def test_can_modify_color_fields(self) -> None:
        """Color fields can be reassigned after creation."""
        visual = VisualSettings()
        new_color = QColor(255, 0, 0)
        visual.line_color = new_color
        assert visual.line_color == new_color

    def test_mutability_allows_runtime_changes(self) -> None:
        """Verify mutability supports UI-driven changes."""
        visual = VisualSettings()

        # Simulate UI slider changes
        visual.point_radius = 8
        visual.selected_point_radius = 12
        visual.line_width = 4
        visual.selected_line_width = 6

        # Simulate UI toggle changes
        visual.show_grid = True
        visual.show_labels = True

        # Verify all changes persisted
        assert visual.point_radius == 8
        assert visual.selected_point_radius == 12
        assert visual.line_width == 4
        assert visual.selected_line_width == 6
        assert visual.show_grid is True
        assert visual.show_labels is True
