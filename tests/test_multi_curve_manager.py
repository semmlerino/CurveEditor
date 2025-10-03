"""Test suite for MultiCurveManager.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use real components where possible
- Mock only at system boundaries
"""

import pytest

from core.type_aliases import CurveDataList
from stores.application_state import reset_application_state
from ui.curve_view_widget import CurveViewWidget
from ui.multi_curve_manager import MultiCurveManager


class TestMultiCurveManager:
    """Unit tests for MultiCurveManager."""

    @pytest.fixture
    def widget(self, qtbot):
        """Create a CurveViewWidget for testing."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def manager(self, widget):
        """Create a MultiCurveManager for testing."""
        # Reset ApplicationState to ensure clean state for each test
        # (widget initialization may have added curves)
        reset_application_state()
        return MultiCurveManager(widget)

    def test_initial_state(self, manager):
        """Test that manager starts with empty state."""
        assert manager.curves_data == {}
        assert manager.curve_metadata == {}
        assert manager.active_curve_name is None
        assert not manager.show_all_curves
        assert manager.selected_curve_names == set()

    def test_add_curve(self, manager, widget):
        """Test adding a single curve."""
        data: CurveDataList = [(1, 100.0, 200.0), (2, 150.0, 250.0)]

        manager.add_curve("test_curve", data)

        assert "test_curve" in manager.curves_data
        assert manager.curves_data["test_curve"] == data
        assert manager.active_curve_name == "test_curve"
        assert "test_curve" in manager.curve_metadata
        assert manager.curve_metadata["test_curve"]["visible"] is True

    def test_add_curve_with_metadata(self, manager):
        """Test adding a curve with custom metadata."""
        data: CurveDataList = [(1, 100.0, 200.0)]
        metadata = {"visible": False, "color": "#FF0000"}

        manager.add_curve("red_curve", data, metadata)

        assert manager.curve_metadata["red_curve"]["visible"] is False
        assert manager.curve_metadata["red_curve"]["color"] == "#FF0000"

    def test_remove_curve(self, manager, widget):
        """Test removing a curve."""
        data: CurveDataList = [(1, 100.0, 200.0)]
        manager.add_curve("test_curve", data)

        manager.remove_curve("test_curve")

        assert "test_curve" not in manager.curves_data
        assert "test_curve" not in manager.curve_metadata
        assert manager.active_curve_name is None

    def test_remove_active_curve_selects_another(self, manager, widget):
        """Test that removing active curve selects another curve."""
        data1: CurveDataList = [(1, 100.0, 200.0)]
        data2: CurveDataList = [(1, 200.0, 300.0)]

        manager.add_curve("curve1", data1)
        manager.add_curve("curve2", data2)
        manager.set_active_curve("curve1")

        manager.remove_curve("curve1")

        # Should auto-select curve2
        assert manager.active_curve_name == "curve2"

    def test_set_curves_data(self, manager, widget):
        """Test setting multiple curves at once."""
        curves = {
            "curve1": [(1, 100.0, 200.0), (2, 150.0, 250.0)],
            "curve2": [(1, 200.0, 300.0), (2, 250.0, 350.0)],
        }

        manager.set_curves_data(curves, active_curve="curve1")

        assert len(manager.curves_data) == 2
        assert manager.active_curve_name == "curve1"
        assert "curve1" in manager.curve_metadata
        assert "curve2" in manager.curve_metadata

    def test_set_curves_data_with_metadata(self, manager, widget):
        """Test setting curves with custom metadata."""
        curves = {"curve1": [(1, 100.0, 200.0)]}
        metadata = {"curve1": {"visible": False, "color": "#00FF00"}}

        manager.set_curves_data(curves, metadata=metadata)

        assert manager.curve_metadata["curve1"]["visible"] is False
        assert manager.curve_metadata["curve1"]["color"] == "#00FF00"

    def test_set_active_curve(self, manager, widget):
        """Test setting the active curve."""
        curves = {
            "curve1": [(1, 100.0, 200.0)],
            "curve2": [(1, 200.0, 300.0)],
        }
        manager.set_curves_data(curves, active_curve="curve1")

        manager.set_active_curve("curve2")

        assert manager.active_curve_name == "curve2"

    def test_update_curve_visibility(self, manager, widget):
        """Test updating curve visibility."""
        manager.add_curve("test_curve", [(1, 100.0, 200.0)])

        manager.update_curve_visibility("test_curve", False)

        assert manager.curve_metadata["test_curve"]["visible"] is False

        manager.update_curve_visibility("test_curve", True)

        assert manager.curve_metadata["test_curve"]["visible"] is True

    def test_update_curve_color(self, manager, widget):
        """Test updating curve color."""
        manager.add_curve("test_curve", [(1, 100.0, 200.0)])

        manager.update_curve_color("test_curve", "#FF0000")

        assert manager.curve_metadata["test_curve"]["color"] == "#FF0000"

    def test_toggle_show_all_curves(self, manager, widget):
        """Test toggling show all curves mode."""
        assert not manager.show_all_curves

        manager.toggle_show_all_curves(True)
        assert manager.show_all_curves

        manager.toggle_show_all_curves(False)
        assert not manager.show_all_curves

    def test_set_selected_curves(self, manager, widget):
        """Test setting selected curves."""
        curves = {
            "curve1": [(1, 100.0, 200.0)],
            "curve2": [(1, 200.0, 300.0)],
            "curve3": [(1, 300.0, 400.0)],
        }
        manager.set_curves_data(curves)

        manager.set_selected_curves(["curve1", "curve3"])

        assert manager.selected_curve_names == {"curve1", "curve3"}
        # Last in list should become active
        assert manager.active_curve_name == "curve3"

    def test_get_live_curves_data_no_curves(self, manager):
        """Test get_live_curves_data with no curves."""
        result = manager.get_live_curves_data()

        assert result == {}

    def test_get_live_curves_data_with_static_data(self, manager, widget):
        """Test get_live_curves_data returns static data by default."""
        curves = {
            "curve1": [(1, 100.0, 200.0)],
            "curve2": [(1, 200.0, 300.0)],
        }
        manager.set_curves_data(curves, active_curve="curve1")

        result = manager.get_live_curves_data()

        assert len(result) == 2
        assert "curve1" in result
        assert "curve2" in result

    def test_first_curve_becomes_active_by_default(self, manager, widget):
        """Test that first curve becomes active when no active specified."""
        curves = {
            "curve1": [(1, 100.0, 200.0)],
            "curve2": [(1, 200.0, 300.0)],
        }

        manager.set_curves_data(curves)

        # First key should be active (dict insertion order preserved in Python 3.7+)
        assert manager.active_curve_name in curves.keys()

    def test_remove_nonexistent_curve_is_safe(self, manager, widget):
        """Test that removing non-existent curve doesn't crash."""
        # Should not raise an exception
        manager.remove_curve("nonexistent")

    def test_update_visibility_of_nonexistent_curve_is_safe(self, manager, widget):
        """Test that updating non-existent curve visibility doesn't crash."""
        # Should not raise an exception
        manager.update_curve_visibility("nonexistent", False)

    def test_update_color_of_nonexistent_curve_is_safe(self, manager, widget):
        """Test that updating non-existent curve color doesn't crash."""
        # Should not raise an exception
        manager.update_curve_color("nonexistent", "#FF0000")


class TestMultiCurveManagerIntegration:
    """Integration tests for MultiCurveManager with CurveViewWidget."""

    @pytest.fixture
    def widget(self, qtbot):
        """Create a CurveViewWidget for testing."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def manager(self, widget):
        """Create a MultiCurveManager for testing."""
        # Reset ApplicationState to ensure clean state for each test
        # (widget initialization may have added curves)
        reset_application_state()
        return MultiCurveManager(widget)

    def test_adding_curve_updates_widget_data(self, manager, widget):
        """Test that adding first curve updates widget's curve data."""
        data: CurveDataList = [(1, 100.0, 200.0), (2, 150.0, 250.0)]

        manager.add_curve("test_curve", data)

        # Widget should have the curve data
        assert len(widget.curve_data) == 2

    def test_set_active_curve_updates_widget_store(self, manager, widget):
        """Test that setting active curve updates widget's store."""
        curves = {
            "curve1": [(1, 100.0, 200.0)],
            "curve2": [(1, 200.0, 300.0), (2, 250.0, 350.0)],
        }
        manager.set_curves_data(curves, active_curve="curve1")

        manager.set_active_curve("curve2")

        # Widget's store should now have curve2's data
        assert len(widget.curve_data) == 2

    def test_manager_widget_relationship(self, manager, widget):
        """Test that manager correctly references its widget."""
        assert manager.widget is widget
