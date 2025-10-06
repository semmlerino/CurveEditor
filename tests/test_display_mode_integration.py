"""
Comprehensive integration tests for DisplayMode property and should_render_curve().

This test suite verifies the DisplayMode property getter/setter integration with
CurveViewWidget's visibility logic, ensuring proper state transitions and rendering
behavior across all display modes.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use real components (CurveViewWidget, ApplicationState)
- Clear test names that describe expected behavior
- Comprehensive edge case coverage
"""

import pytest

from core.display_mode import DisplayMode
from core.type_aliases import CurveDataList
from rendering.render_state import RenderState
from stores.application_state import get_application_state, reset_application_state
from ui.curve_view_widget import CurveViewWidget


@pytest.fixture
def curve_widget(qtbot) -> CurveViewWidget:
    """Create a fresh CurveViewWidget with clean ApplicationState."""
    reset_application_state()
    widget = CurveViewWidget()
    qtbot.addWidget(widget)  # Auto cleanup
    widget.resize(800, 600)
    return widget


@pytest.fixture
def sample_curves() -> dict[str, CurveDataList]:
    """Create sample curve data for testing."""
    return {
        "Track1": [(0, 100.0, 100.0), (10, 110.0, 105.0), (20, 120.0, 110.0)],
        "Track2": [(0, 200.0, 150.0), (10, 210.0, 155.0), (20, 220.0, 160.0)],
        "Track3": [(0, 300.0, 200.0), (10, 310.0, 205.0), (20, 320.0, 210.0)],
    }


# =============================================================================
# 1. Property Getter Tests (3 tests)
# =============================================================================


class TestDisplayModePropertyGetter:
    """Test display_mode property getter logic."""

    def test_display_mode_getter_all_visible(self, curve_widget: CurveViewWidget) -> None:
        """
        Test that show_all_curves=True maps to DisplayMode.ALL_VISIBLE.

        Verifies: When display_mode is set to ALL_VISIBLE, it correctly returns ALL_VISIBLE.
        """
        # Setup: Set ALL_VISIBLE mode via ApplicationState
        app_state = get_application_state()
        app_state.set_show_all_curves(True)
        app_state.set_selected_curves(set())  # No selection

        # Verify: ALL_VISIBLE mode
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE

        # Verify: Mode persists even with selection
        app_state.set_selected_curves({"Track1", "Track2"})
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE

    def test_display_mode_getter_selected(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that show_all_curves=False + selection maps to DisplayMode.SELECTED.

        Verifies: When show_all_curves is disabled and curves are selected,
        the display_mode property returns SELECTED.
        """
        # Setup: Load curves and set selection via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1", "Track2"})

        # Verify: SELECTED mode
        assert curve_widget.display_mode == DisplayMode.SELECTED

    def test_display_mode_getter_active_only(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that show_all_curves=False + no selection maps to DisplayMode.ACTIVE_ONLY.

        Verifies: When show_all_curves is disabled and no curves are selected,
        the display_mode property returns ACTIVE_ONLY.
        """
        # Setup: Load curves, disable show_all, clear selection via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Verify: ACTIVE_ONLY mode
        assert curve_widget.display_mode == DisplayMode.ACTIVE_ONLY


# =============================================================================
# 2. Property Setter Tests (3 tests)
# =============================================================================


class TestDisplayModePropertySetter:
    """Test display_mode property setter behavior."""

    def test_display_mode_setter_all_visible(self, curve_widget: CurveViewWidget) -> None:
        """
        Test that setting show_all_curves=True results in ALL_VISIBLE display mode.

        Verifies: ApplicationState API correctly computes display_mode
        and leaves selection unchanged.
        """
        # Setup: Start with different mode via ApplicationState
        app_state = get_application_state()
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1"})

        # Action: Set show_all_curves=True via ApplicationState
        app_state.set_show_all_curves(True)

        # Verify: display_mode computed as ALL_VISIBLE, selection preserved
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE
        assert "Track1" in app_state.get_selected_curves()  # Preserved

    def test_display_mode_setter_selected_auto_select(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that selecting a curve with show_all=False results in SELECTED mode.

        Verifies: ApplicationState API correctly computes display_mode
        when curves are selected with show_all_curves disabled.
        """
        # Setup: Load curves via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_show_all_curves(True)

        # Action: Select curve and disable show_all via ApplicationState
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1"})

        # Verify: display_mode computed as SELECTED
        assert curve_widget.display_mode == DisplayMode.SELECTED
        assert app_state.display_mode == DisplayMode.SELECTED
        assert "Track1" in app_state.get_selected_curves()
        assert len(app_state.get_selected_curves()) == 1

    def test_display_mode_setter_active_only_clears(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that clearing selection with show_all=False results in ACTIVE_ONLY mode.

        Verifies: ApplicationState API correctly computes display_mode
        when selection is empty and show_all_curves is disabled.
        """
        # Setup: Load curves with selection via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)
        app_state.set_selected_curves({"Track1", "Track2", "Track3"})
        app_state.set_show_all_curves(False)

        # Action: Clear selection via ApplicationState
        app_state.set_selected_curves(set())

        # Verify: display_mode computed as ACTIVE_ONLY
        assert curve_widget.display_mode == DisplayMode.ACTIVE_ONLY
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY
        assert len(app_state.get_selected_curves()) == 0


# =============================================================================
# 3. Edge Cases (3 tests)
# =============================================================================


class TestDisplayModeEdgeCases:
    """Test edge cases and error conditions."""

    def test_display_mode_selected_no_active_curve(self, curve_widget: CurveViewWidget) -> None:
        """
        Test that setting SELECTED mode with no active curve results in empty selection.

        Verifies: When no active curve exists, setting SELECTED mode doesn't crash
        and leaves selection empty (nothing to auto-select).
        """
        # Setup: No curves loaded (no active curve) via ApplicationState
        app_state = get_application_state()
        app_state.set_show_all_curves(True)
        assert app_state.active_curve is None

        # Action: Disable show_all with empty selection via ApplicationState
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Verify: No crash, display_mode is ACTIVE_ONLY (no selection possible)
        assert curve_widget.display_mode == DisplayMode.ACTIVE_ONLY
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY
        assert len(app_state.get_selected_curves()) == 0

    def test_display_mode_active_only_no_active_curve(self, curve_widget: CurveViewWidget) -> None:
        """
        Test that ACTIVE_ONLY mode with no active curve is safe.

        Verifies: When no active curve exists, ACTIVE_ONLY mode clears
        selection without errors.
        """
        # Setup: No curves loaded, some selection exists via ApplicationState
        app_state = get_application_state()
        app_state.set_selected_curves({"NonexistentCurve"})
        assert app_state.active_curve is None

        # Action: Clear selection via ApplicationState
        app_state.set_selected_curves(set())
        app_state.set_show_all_curves(False)

        # Verify: Selection cleared, display_mode is ACTIVE_ONLY, no crashes
        assert len(app_state.get_selected_curves()) == 0
        assert curve_widget.display_mode == DisplayMode.ACTIVE_ONLY
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

    def test_display_mode_preserves_existing_selection(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that SELECTED mode preserves existing selection.

        Verifies: When switching to SELECTED mode with existing selection,
        the selection is preserved (not replaced with active curve).
        """
        # Setup: Load curves with existing selection via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track2", "Track3"})
        app_state.set_show_all_curves(True)

        # Action: Disable show_all (keeps selection) via ApplicationState
        app_state.set_show_all_curves(False)

        # Verify: Existing selection preserved, display_mode is SELECTED
        assert curve_widget.display_mode == DisplayMode.SELECTED
        assert app_state.display_mode == DisplayMode.SELECTED
        selected = app_state.get_selected_curves()
        assert "Track2" in selected
        assert "Track3" in selected
        assert "Track1" not in selected  # Not auto-added


# =============================================================================
# 4. should_render_curve() Integration (3 tests)
# =============================================================================


class TestShouldRenderCurveIntegration:
    """Test should_render_curve() behavior with DisplayMode."""

    def test_should_render_all_visible_mode(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that ALL_VISIBLE mode renders all visible curves.

        Verifies: In ALL_VISIBLE mode, RenderState.visible_curves contains
        all curves with metadata.visible=True, regardless of selection.
        """
        # Setup: Load curves, set ALL_VISIBLE mode via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)
        app_state.set_show_all_curves(True)

        # Verify: All curves should render
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert "Track3" in render_state.visible_curves

        # Verify: Selection doesn't affect rendering in ALL_VISIBLE mode
        app_state.set_selected_curves({"Track1"})  # Select only Track1
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves  # Still renders
        assert "Track3" in render_state.visible_curves  # Still renders

    def test_should_render_selected_mode(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that SELECTED mode renders only selected curves.

        Verifies: In SELECTED mode, RenderState.visible_curves contains
        only curves in the selected_curve_names set.
        """
        # Setup: Load curves, set SELECTED mode with specific selection via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track1", "Track2"})
        app_state.set_show_all_curves(False)

        # Verify: Only selected curves render
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert "Track3" not in render_state.visible_curves  # Not selected

    def test_should_render_active_only_mode(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that ACTIVE_ONLY mode renders only the active curve (BUG FIX TEST).

        This test verifies the critical bug fix: In ACTIVE_ONLY mode
        (show_all_curves=False, empty selection), only the active curve
        should render. Previously, the else branch would render the active
        curve even in SELECTED mode, causing incorrect behavior.

        Verifies: In ACTIVE_ONLY mode, RenderState.visible_curves contains
        only the active curve, and no other curves.
        """
        # Setup: Load curves, set ACTIVE_ONLY mode via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track2")
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves(set())

        # Verify: Only active curve renders (this is the bug fix!)
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" not in render_state.visible_curves
        assert "Track2" in render_state.visible_curves  # Active
        assert "Track3" not in render_state.visible_curves

        # Verify: Changing active curve changes rendering
        curve_widget.set_active_curve("Track3")
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" not in render_state.visible_curves
        assert "Track2" not in render_state.visible_curves
        assert "Track3" in render_state.visible_curves  # New active


# =============================================================================
# 5. State Transitions (3 tests)
# =============================================================================


class TestDisplayModeStateTransitions:
    """Test state transitions and consistency across display modes."""

    def test_display_mode_multiple_transitions(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test multiple display mode transitions maintain consistency.

        Verifies: Transitioning through all display modes (ALL_VISIBLE →
        SELECTED → ACTIVE_ONLY → ALL_VISIBLE) maintains correct state
        and rendering behavior at each step.
        """
        # Setup: Load curves
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")

        # Transition 1: ALL_VISIBLE
        app_state.set_show_all_curves(True)
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert "Track3" in render_state.visible_curves

        # Transition 2: SELECTED
        app_state.set_selected_curves({"Track1", "Track3"})
        app_state.set_show_all_curves(False)
        assert curve_widget.display_mode == DisplayMode.SELECTED
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" not in render_state.visible_curves  # Not selected
        assert "Track3" in render_state.visible_curves

        # Transition 3: ACTIVE_ONLY
        app_state.set_selected_curves(set())
        assert curve_widget.display_mode == DisplayMode.ACTIVE_ONLY
        assert len(app_state.get_selected_curves()) == 0  # Cleared
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves  # Active
        assert "Track2" not in render_state.visible_curves
        assert "Track3" not in render_state.visible_curves

        # Transition 4: Back to ALL_VISIBLE
        app_state.set_show_all_curves(True)
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert "Track3" in render_state.visible_curves

    def test_display_mode_setter_idempotent(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that setting the same mode twice is safe and idempotent.

        Verifies: Setting display_mode to the same value multiple times
        doesn't cause side effects or state corruption.
        """
        # Setup: Load curves via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_selected_curves({"Track1", "Track2"})
        app_state.set_show_all_curves(False)

        # Capture original state
        original_selection = app_state.get_selected_curves().copy()
        original_mode = curve_widget.display_mode

        # Action: Set same state multiple times via ApplicationState (idempotency test)
        app_state.set_show_all_curves(False)  # Again
        app_state.set_selected_curves({"Track1", "Track2"})  # Again

        # Verify: State unchanged (idempotent)
        assert app_state.get_selected_curves() == original_selection
        assert curve_widget.display_mode == original_mode
        assert curve_widget.display_mode == DisplayMode.SELECTED

    def test_display_mode_respects_metadata_visibility(
        self, curve_widget: CurveViewWidget, sample_curves: dict[str, CurveDataList]
    ) -> None:
        """
        Test that all display modes respect metadata.visible=False.

        Verifies: Curves with metadata.visible=False are never in RenderState.visible_curves,
        regardless of display mode (ALL_VISIBLE, SELECTED, or ACTIVE_ONLY).
        This ensures metadata visibility is the highest priority filter.
        """
        # Setup: Load curves, hide Track2 via metadata
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves, active_curve="Track1")
        app_state.set_curve_visibility("Track2", False)

        # Test 1: ALL_VISIBLE mode respects metadata.visible
        app_state.set_show_all_curves(True)
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" not in render_state.visible_curves  # Hidden by metadata
        assert "Track3" in render_state.visible_curves

        # Test 2: SELECTED mode respects metadata.visible
        app_state.set_selected_curves({"Track1", "Track2"})  # Try to select hidden
        app_state.set_show_all_curves(False)
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track1" in render_state.visible_curves
        assert "Track2" not in render_state.visible_curves  # Still hidden!

        # Test 3: ACTIVE_ONLY mode respects metadata.visible
        curve_widget.set_active_curve("Track2")  # Make hidden curve active
        app_state.set_selected_curves(set())
        render_state = RenderState.compute(curve_widget)
        assert render_state.visible_curves is not None
        assert "Track2" not in render_state.visible_curves  # Hidden even when active!
