"""
Comprehensive tests for RenderState visibility computation.

This test suite verifies that RenderState.compute() correctly implements the same
visibility logic as CurveViewWidget.should_render_curve() but pre-computes the
results for better performance.

Test Coverage:
- All three display modes (ALL_VISIBLE, SELECTED, ACTIVE_ONLY)
- Metadata visibility filtering (visible=True/False)
- Interaction between display mode and metadata
- Edge cases (no curves, no active curve, empty selection)
- Convenience methods (should_render, __contains__, __len__, __bool__)
- Immutability and thread safety
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

import pytest

from core.display_mode import DisplayMode
from rendering.render_state import RenderState
from stores.application_state import get_application_state
from ui.curve_view_widget import CurveViewWidget


@pytest.fixture
def curve_widget(qapp):
    """Provide fresh CurveViewWidget for each test."""
    widget = CurveViewWidget()
    yield widget
    widget.deleteLater()


@pytest.fixture
def sample_curves():
    """Provide sample curve data for testing."""
    return {
        "Track1": [
            (1, 10.0, 20.0),
            (2, 15.0, 25.0),
            (3, 20.0, 30.0),
        ],
        "Track2": [
            (1, 30.0, 40.0),
            (2, 35.0, 45.0),
            (3, 40.0, 50.0),
        ],
        "Track3": [
            (1, 50.0, 60.0),
            (2, 55.0, 65.0),
            (3, 60.0, 70.0),
        ],
    }


class TestRenderStateAllVisibleMode:
    """Test RenderState.compute() in ALL_VISIBLE display mode."""

    def test_all_visible_includes_all_curves(self, curve_widget, sample_curves):
        """In ALL_VISIBLE mode, all metadata-visible curves should be included."""
        # Setup: Load curves and set ALL_VISIBLE mode via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_show_all_curves(True)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: All curves are visible
        assert state.display_mode == DisplayMode.ALL_VISIBLE
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 3
        assert state.visible_curves is not None
        assert "Track1" in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" in state.visible_curves
        assert state.visible_curves is not None
        assert "Track3" in state.visible_curves
        assert state.active_curve == "Track1"

    def test_all_visible_ignores_selection(self, curve_widget, sample_curves):
        """In ALL_VISIBLE mode, selection doesn't affect visibility."""
        # Setup: Load curves, set selection, set ALL_VISIBLE mode via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track1"})  # Select only Track1
        app_state.set_show_all_curves(True)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: All curves visible despite selection
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 3
        assert state.visible_curves is not None
        assert "Track1" in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" in state.visible_curves  # Not selected but still visible
        assert state.visible_curves is not None
        assert "Track3" in state.visible_curves  # Not selected but still visible

    def test_all_visible_respects_metadata_visibility(self, curve_widget, sample_curves):
        """In ALL_VISIBLE mode, metadata.visible=False hides curves."""
        # Setup: Load curves and hide Track2 via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_curve_visibility("Track2", False)
        app_state.set_show_all_curves(True)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: Track2 hidden by metadata
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 2
        assert state.visible_curves is not None
        assert "Track1" in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" not in state.visible_curves  # Hidden by metadata
        assert state.visible_curves is not None
        assert "Track3" in state.visible_curves


class TestRenderStateSelectedMode:
    """Test RenderState.compute() in SELECTED display mode."""

    def test_selected_includes_only_selected_curves(self, curve_widget, sample_curves):
        """In SELECTED mode, only selected curves should be included."""
        # Setup: Load curves, select Track1 and Track3 via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track1", "Track3"})
        app_state.set_show_all_curves(False)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: Only selected curves visible
        assert state.display_mode == DisplayMode.SELECTED
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 2
        assert state.visible_curves is not None
        assert "Track1" in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" not in state.visible_curves  # Not selected
        assert state.visible_curves is not None
        assert "Track3" in state.visible_curves

    def test_selected_respects_metadata_visibility(self, curve_widget, sample_curves):
        """In SELECTED mode, hidden curves don't render even if selected."""
        # Setup: Load curves, hide Track2, select Track1 and Track2 via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_curve_visibility("Track2", False)
        app_state.set_selected_curves({"Track1", "Track2"})
        app_state.set_show_all_curves(False)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: Track2 hidden despite being selected
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 1
        assert state.visible_curves is not None
        assert "Track1" in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" not in state.visible_curves  # Hidden by metadata

    def test_selected_empty_selection(self, curve_widget, sample_curves):
        """Clearing selection in SELECTED mode transitions to ACTIVE_ONLY mode."""
        # Setup: Load curves, set SELECTED mode, then clear selection via ApplicationState
        # Note: When selection is cleared, display_mode automatically becomes ACTIVE_ONLY
        # because DisplayMode.from_legacy() sees has_selection=False
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1"})  # First select
        app_state.set_selected_curves(set())  # Then clear selection

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: Mode automatically transitioned to ACTIVE_ONLY (empty selection)
        # So only the active curve is visible
        assert state.display_mode == DisplayMode.ACTIVE_ONLY
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 1
        assert state.visible_curves is not None
        assert "Track1" in state.visible_curves  # Active curve visible
        assert state.visible_curves is not None
        assert "Track2" not in state.visible_curves
        assert state.visible_curves is not None
        assert "Track3" not in state.visible_curves
        assert state.active_curve == "Track1"


class TestRenderStateActiveOnlyMode:
    """Test RenderState.compute() in ACTIVE_ONLY display mode."""

    def test_active_only_includes_only_active_curve(self, curve_widget, sample_curves):
        """In ACTIVE_ONLY mode, only the active curve should be included."""
        # Setup: Load curves with Track2 active via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track2")
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: Only active curve visible
        assert state.display_mode == DisplayMode.ACTIVE_ONLY
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 1
        assert state.visible_curves is not None
        assert "Track1" not in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" in state.visible_curves  # Active
        assert state.visible_curves is not None
        assert "Track3" not in state.visible_curves
        assert state.active_curve == "Track2"

    def test_active_only_respects_metadata_visibility(self, curve_widget, sample_curves):
        """In ACTIVE_ONLY mode, hidden active curve doesn't render."""
        # Setup: Load curves, make Track2 active, hide Track2 via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track2")
        app_state.set_curve_visibility("Track2", False)
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: No curves visible (active curve is hidden)
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 0
        assert state.visible_curves is not None
        assert "Track2" not in state.visible_curves  # Hidden by metadata

    def test_active_only_no_active_curve(self, curve_widget, sample_curves):
        """In ACTIVE_ONLY mode with no active curve, nothing visible."""
        # Setup: Load curves, then clear active curve via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_active_curve(None)
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: No curves visible (no active curve)
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 0
        assert state.active_curve is None


class TestRenderStateEdgeCases:
    """Test RenderState.compute() edge cases."""

    def test_no_curves(self, curve_widget):
        """With no curves, visible_curves should be empty."""
        # Setup: Widget with no curves via ApplicationState
        app_state = get_application_state()
        app_state.set_show_all_curves(True)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: Empty visible set
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 0
        assert bool(state) is False

    def test_all_curves_hidden_by_metadata(self, curve_widget, sample_curves):
        """When all curves hidden by metadata, visible_curves should be empty."""
        # Setup: Load curves and hide all via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        for curve_name in sample_curves:
            app_state.set_curve_visibility(curve_name, False)
        app_state.set_show_all_curves(True)

        # Act: Compute render state
        state = RenderState.compute(curve_widget)

        # Assert: No curves visible (all hidden)
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 0
        assert state.visible_curves is not None
        assert "Track1" not in state.visible_curves
        assert state.visible_curves is not None
        assert "Track2" not in state.visible_curves
        assert state.visible_curves is not None
        assert "Track3" not in state.visible_curves


class TestRenderStateConvenienceMethods:
    """Test RenderState convenience methods."""

    def test_should_render_method(self, curve_widget, sample_curves):
        """should_render() should return True for visible curves."""
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track1", "Track3"})
        app_state.set_show_all_curves(False)

        # Act
        state = RenderState.compute(curve_widget)

        # Assert
        assert state.should_render("Track1") is True
        assert state.should_render("Track2") is False
        assert state.should_render("Track3") is True

    def test_contains_operator(self, curve_widget, sample_curves):
        """'in' operator should work for curve name checking."""
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Act
        state = RenderState.compute(curve_widget)

        # Assert: 'in' operator works
        assert "Track1" in state
        assert "Track2" not in state
        assert "Track3" not in state

    def test_len_operator(self, curve_widget, sample_curves):
        """len() should return number of visible curves."""
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track1", "Track2"})
        app_state.set_show_all_curves(False)

        # Act
        state = RenderState.compute(curve_widget)

        # Assert
        assert len(state) == 2
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 2

    def test_bool_operator_true(self, curve_widget, sample_curves):
        """bool() should return True when curves are visible."""
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_show_all_curves(True)

        # Act
        state = RenderState.compute(curve_widget)

        # Assert
        assert bool(state) is True
        assert state  # Truthy

    def test_bool_operator_false(self, curve_widget):
        """bool() should return False when no curves are visible."""
        # Setup: No curves via ApplicationState
        app_state = get_application_state()
        app_state.set_show_all_curves(True)

        # Act
        state = RenderState.compute(curve_widget)

        # Assert
        assert bool(state) is False
        assert not state  # Falsy

    def test_repr_method(self, curve_widget, sample_curves):
        """repr() should return useful debug string."""
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_show_all_curves(True)

        # Act
        state = RenderState.compute(curve_widget)
        repr_str = repr(state)

        # Assert: Contains key information
        assert "RenderState" in repr_str
        assert "ALL_VISIBLE" in repr_str
        assert "curves=3" in repr_str
        assert "Track1" in repr_str


class TestRenderStateImmutability:
    """Test that RenderState is truly immutable."""

    def test_frozen_dataclass(self, curve_widget, sample_curves):
        """RenderState should be frozen (immutable)."""
        # Setup
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        state = RenderState.compute(curve_widget)

        # Assert: Cannot modify attributes (dataclass frozen=True)
        with pytest.raises(Exception, match="frozen|cannot assign"):
            state.display_mode = DisplayMode.ACTIVE_ONLY  # pyright: ignore[reportAttributeAccessIssue]

        with pytest.raises(Exception, match="frozen|cannot assign"):
            state.visible_curves = frozenset({"NewCurve"})  # pyright: ignore[reportAttributeAccessIssue]

        with pytest.raises(Exception, match="frozen|cannot assign"):
            state.active_curve = "Track2"  # pyright: ignore[reportAttributeAccessIssue]

    def test_visible_curves_is_frozenset(self, curve_widget, sample_curves):
        """visible_curves should be frozenset (immutable)."""
        # Setup
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        state = RenderState.compute(curve_widget)

        # Assert: Is frozenset
        assert isinstance(state.visible_curves, frozenset)

        # Assert: Cannot modify frozenset (no 'add' method)
        with pytest.raises(AttributeError, match="'frozenset' object has no attribute 'add'"):
            state.visible_curves.add("NewCurve")  # pyright: ignore[reportAttributeAccessIssue]


# NOTE: TestRenderStateMatchesShouldRenderCurve class removed (obsolete migration tests)
# The widget method should_render_curve() was removed and logic moved to RenderState.
# Behavior is verified in test_display_mode_integration.py instead.


class TestRenderStatePerformance:
    """Test RenderState performance characteristics."""

    def test_compute_is_efficient(self, curve_widget):
        """Compute should be fast even with many curves."""
        # Setup: Create 100 curves via ApplicationState
        app_state = get_application_state()
        many_curves = {f"Track{i}": [(j, float(j), float(j)) for j in range(1, 4)] for i in range(100)}
        curve_widget.set_curves_data(many_curves, active_curve="Track0")
        app_state.set_show_all_curves(True)

        # Act: Compute should be fast (this is just a smoke test)
        import time

        start = time.perf_counter()
        state = RenderState.compute(curve_widget)
        elapsed = time.perf_counter() - start

        # Assert: Should complete quickly (< 100ms is very generous)
        assert elapsed < 0.1, f"Compute took {elapsed*1000:.2f}ms for 100 curves"
        assert state.visible_curves is not None
        assert len(state.visible_curves) == 100

    def test_membership_check_is_fast(self, curve_widget, sample_curves):
        """Membership check should be O(1)."""
        # Setup
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        state = RenderState.compute(curve_widget)

        # Act: Many membership checks should be fast
        import time

        start = time.perf_counter()
        for _ in range(10000):
            _ = "Track1" in state
            _ = "Track2" in state
            _ = "Track3" in state
        elapsed = time.perf_counter() - start

        # Assert: 30k checks should complete very quickly (< 10ms)
        assert elapsed < 0.01, f"30k membership checks took {elapsed*1000:.2f}ms"
