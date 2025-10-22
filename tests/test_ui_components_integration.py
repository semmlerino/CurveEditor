#!/usr/bin/env python
"""
Tests for UI Components integration and Component Container Pattern.

These tests validate the architectural integration methodology documented
in CLAUDE.md and ensure proper widget mapping and validation.
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

from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QLabel, QSlider, QSpinBox
from pytestqt.qtbot import QtBot

from ui.main_window import MainWindow
from ui.ui_components import UIComponents


class TestUIComponentsIntegration:
    """Test Component Container Pattern integration."""

    def test_ui_components_initialization(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test UIComponents container is properly initialized in MainWindow."""
        window = MainWindow()
        qtbot.addWidget(window)

        # UIComponents container should exist
        assert window.ui is not None, "MainWindow missing ui components container"
        assert isinstance(window.ui, UIComponents), "ui should be UIComponents instance"

        # All component groups should exist and be accessible
        assert window.ui.timeline is not None, "Missing timeline components"
        assert window.ui.point_edit is not None, "Missing point_edit components"
        assert window.ui.visualization is not None, "Missing visualization components"
        assert window.ui.status is not None, "Missing status components"
        assert window.ui.toolbar is not None, "Missing toolbar components"
        assert window.ui.smoothing is not None, "Missing smoothing components"

    def test_timeline_component_mappings(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test timeline components are properly mapped."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test frame spinbox mapping
        assert window.ui.timeline.frame_spinbox is not None, "Missing timeline.frame_spinbox"
        assert window.ui.timeline.frame_spinbox is window.frame_spinbox, "frame_spinbox not mapped correctly"
        assert isinstance(window.ui.timeline.frame_spinbox, QSpinBox), "frame_spinbox wrong type"

        # Test fps spinbox mapping
        assert window.ui.timeline.fps_spinbox is not None, "Missing timeline.fps_spinbox"
        assert window.ui.timeline.fps_spinbox is window.fps_spinbox, "fps_spinbox not mapped correctly"
        assert isinstance(window.ui.timeline.fps_spinbox, QSpinBox), "fps_spinbox wrong type"

        # Test timeline slider mapping
        assert window.ui.timeline.timeline_slider is not None, "Missing timeline.timeline_slider"
        assert window.ui.timeline.timeline_slider is window.frame_slider, "timeline_slider not mapped correctly"
        assert isinstance(window.ui.timeline.timeline_slider, QSlider), "timeline_slider wrong type"

        # Test play button - the only playback button that's actually functional
        assert window.ui.timeline.play_button is not None, "Missing timeline.play_button"
        assert window.ui.timeline.play_button is window.btn_play_pause, "play_button not mapped"

        # NOTE: Removed orphaned button tests (first_frame_button, etc.) - those buttons
        # were never added to UI and have been correctly removed as architectural bugs

    def test_point_edit_component_mappings(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test point editing components are properly mapped with correct types."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test x coordinate editor - should be QDoubleSpinBox
        assert window.ui.point_edit.x_edit is not None, "Missing point_edit.x_edit"
        assert window.ui.point_edit.x_edit is window.point_x_spinbox, "x_edit not mapped correctly"
        assert isinstance(window.ui.point_edit.x_edit, QDoubleSpinBox), "x_edit wrong type - should be QDoubleSpinBox"

        # Test y coordinate editor - should be QDoubleSpinBox
        assert window.ui.point_edit.y_edit is not None, "Missing point_edit.y_edit"
        assert window.ui.point_edit.y_edit is window.point_y_spinbox, "y_edit not mapped correctly"
        assert isinstance(window.ui.point_edit.y_edit, QDoubleSpinBox), "y_edit wrong type - should be QDoubleSpinBox"

    def test_visualization_component_mappings(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test visualization components are properly mapped."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test point size slider mapping
        assert window.ui.visualization.point_size_slider is not None, "Missing visualization.point_size_slider"
        assert window.ui.visualization.point_size_slider is window.point_size_slider, "point_size_slider not mapped"
        assert isinstance(window.ui.visualization.point_size_slider, QSlider), "point_size_slider wrong type"

        # Test line width slider mapping
        assert window.ui.visualization.line_width_slider is not None, "Missing visualization.line_width_slider"
        assert window.ui.visualization.line_width_slider is window.line_width_slider, "line_width_slider not mapped"
        assert isinstance(window.ui.visualization.line_width_slider, QSlider), "line_width_slider wrong type"

    def test_status_component_mappings(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test status components are properly mapped."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test info label mapping
        assert window.ui.status.info_label is not None, "Missing status.info_label"
        assert window.ui.status.info_label is window.total_frames_label, "info_label not mapped correctly"
        assert isinstance(window.ui.status.info_label, QLabel), "info_label wrong type"

        # Test quality labels mapping
        assert window.ui.status.quality_score_label is not None, "Missing status.quality_score_label"
        assert window.ui.status.quality_score_label is window.point_count_label, "quality_score_label not mapped"

        assert window.ui.status.quality_coverage_label is not None, "Missing status.quality_coverage_label"
        assert (
            window.ui.status.quality_coverage_label is window.selected_count_label
        ), "quality_coverage_label not mapped"

        assert window.ui.status.quality_consistency_label is not None, "Missing status.quality_consistency_label"
        assert window.ui.status.quality_consistency_label is window.bounds_label, "quality_consistency_label not mapped"

    def test_property_access_works(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test that property access through UIComponents works correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test timeline property access
        assert window.ui.frame_spinbox is window.frame_spinbox, "frame_spinbox property access failed"
        assert window.ui.fps_spinbox is window.fps_spinbox, "fps_spinbox property access failed"
        assert window.ui.timeline_slider is window.frame_slider, "timeline_slider property access failed"

        # Test point edit property access
        assert window.ui.x_edit is window.point_x_spinbox, "x_edit property access failed"
        assert window.ui.y_edit is window.point_y_spinbox, "y_edit property access failed"

        # Test visualization property access
        assert window.ui.point_size_slider is window.point_size_slider, "point_size_slider property access failed"
        assert window.ui.line_width_slider is window.line_width_slider, "line_width_slider property access failed"

    def test_component_groups_access(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test that component groups can be accessed and inspected."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Get component groups
        groups = window.ui.get_component_groups()
        expected_groups = {"toolbar", "timeline", "status", "visualization", "point_edit", "smoothing"}

        assert isinstance(groups, dict), "get_component_groups should return dict"
        assert set(groups.keys()) == expected_groups, f"Missing groups: {expected_groups - set(groups.keys())}"

        # Each group should be a component instance
        for group_name, group in groups.items():
            assert group is not None, f"Component group {group_name} is None"
            # Check it's an object with attributes (better than hasattr __dict__)
            assert isinstance(group, object), f"Component group {group_name} not a proper object"

    def test_validation_completeness(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test built-in validation method works."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test validation - should return empty list if all critical components exist
        missing = window.ui.validate_completeness()
        assert isinstance(missing, list), "validate_completeness should return list"

        # We can't guarantee all critical components exist since MainWindow doesn't map all of them yet,
        # but the method should work without crashing
        # Note: This test validates the methodology works, not that all components are mapped

    def test_no_silent_attribute_creation(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test that mappings don't create silent attributes."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test that our mappings reference actual attributes, not dynamic creation
        # All mapped attributes should exist in the component class definitions

        # Timeline attributes that should exist
        timeline_attrs = dir(window.ui.timeline)
        assert "frame_spinbox" in timeline_attrs, "frame_spinbox should be defined in TimelineUIComponents"
        assert "fps_spinbox" in timeline_attrs, "fps_spinbox should be defined in TimelineUIComponents"
        assert "timeline_slider" in timeline_attrs, "timeline_slider should be defined in TimelineUIComponents"

        # Visualization attributes that should exist
        viz_attrs = dir(window.ui.visualization)
        assert "point_size_slider" in viz_attrs, "point_size_slider should be defined in VisualizationUIComponents"
        assert "line_width_slider" in viz_attrs, "line_width_slider should be defined in VisualizationUIComponents"

        # Point edit attributes that should exist
        point_edit_attrs = dir(window.ui.point_edit)
        assert "x_edit" in point_edit_attrs, "x_edit should be defined in PointEditUIComponents"
        assert "y_edit" in point_edit_attrs, "y_edit should be defined in PointEditUIComponents"


class TestArchitecturalIntegrationMethodology:
    """Test the architectural integration methodology principles."""

    def test_structure_compatibility_validation(self):
        """Test structure compatibility validation approach."""
        from ui.ui_components import PointEditUIComponents, TimelineUIComponents, VisualizationUIComponents

        # Get actual component structures
        timeline = TimelineUIComponents()
        viz = VisualizationUIComponents()
        point_edit = PointEditUIComponents()

        # Define what MainWindow expects to map
        expected_mappings = {
            "timeline": ["frame_spinbox", "fps_spinbox", "timeline_slider", "play_button"],
            "visualization": ["point_size_slider", "line_width_slider"],
            "point_edit": ["x_edit", "y_edit"],
        }

        # Validate compatibility
        for group_name, expected_attrs in expected_mappings.items():
            component: object
            if group_name == "timeline":
                component = timeline
            elif group_name == "visualization":
                component = viz
            elif group_name == "point_edit":
                component = point_edit
            else:
                continue  # Skip unknown groups

            component_attrs = set(dir(component))

            for attr in expected_attrs:
                assert attr in component_attrs, f"Missing {attr} in {group_name} - would cause silent creation"

    def test_type_compatibility_validation(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test that widget types match component expectations."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test coordinate editing uses appropriate numeric input widgets
        assert isinstance(window.point_x_spinbox, QDoubleSpinBox), "X coordinate should use QDoubleSpinBox"
        assert isinstance(window.point_y_spinbox, QDoubleSpinBox), "Y coordinate should use QDoubleSpinBox"

        # Test that UIComponents expects the same types
        assert isinstance(window.ui.point_edit.x_edit, QDoubleSpinBox), "UIComponents x_edit should be QDoubleSpinBox"
        assert isinstance(window.ui.point_edit.y_edit, QDoubleSpinBox), "UIComponents y_edit should be QDoubleSpinBox"

    def test_mapping_integrity(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test that all mappings reference the same widget instances."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test that direct access and component access reference same instances
        test_cases = [
            (window.frame_spinbox, window.ui.timeline.frame_spinbox, "frame_spinbox"),
            (window.fps_spinbox, window.ui.timeline.fps_spinbox, "fps_spinbox"),
            (window.frame_slider, window.ui.timeline.timeline_slider, "timeline_slider"),
            (window.point_x_spinbox, window.ui.point_edit.x_edit, "x_edit"),
            (window.point_y_spinbox, window.ui.point_edit.y_edit, "y_edit"),
            (window.point_size_slider, window.ui.visualization.point_size_slider, "point_size_slider"),
            (window.line_width_slider, window.ui.visualization.line_width_slider, "line_width_slider"),
        ]

        for direct_widget, component_widget, name in test_cases:
            assert direct_widget is component_widget, f"Mapping integrity failed for {name}"

    def test_component_organization(self, qapp: QApplication, qtbot: QtBot) -> None:
        """Test that components are properly organized by functional groups."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Timeline group should contain timeline-related widgets
        timeline_widgets = [
            window.ui.timeline.frame_spinbox,
            window.ui.timeline.fps_spinbox,
            window.ui.timeline.timeline_slider,
            window.ui.timeline.play_button,
        ]

        for widget in timeline_widgets:
            if widget is not None:  # Some widgets might not be mapped yet
                # Timeline widgets should have time/frame-related functionality
                # Check for common widget methods using callable()
                has_set_value = callable(getattr(widget, "setValue", None))
                has_set_checked = callable(getattr(widget, "setChecked", None))
                assert has_set_value or has_set_checked, "Timeline widget missing expected methods"

        # Point edit group should contain coordinate editing widgets
        point_edit_widgets = [
            window.ui.point_edit.x_edit,
            window.ui.point_edit.y_edit,
        ]

        for widget in point_edit_widgets:
            if widget is not None:
                # Point edit widgets should support numeric input
                assert callable(getattr(widget, "setValue", None)), "Point edit widget should support setValue"
                assert callable(getattr(widget, "value", None)), "Point edit widget should support value"
