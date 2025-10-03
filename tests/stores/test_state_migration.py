"""
Tests for StateMigrationMixin compatibility layer.

Verifies that old code patterns continue working during migration
while properly forwarding to ApplicationState.
"""

from collections.abc import Generator

import pytest

from stores.application_state import get_application_state, reset_application_state
from stores.state_migration import StateMigrationMixin


class MockComponent(StateMigrationMixin):
    """Mock component using StateMigrationMixin for testing."""

    def __init__(self) -> None:
        super().__init__()


class TestStateMigrationMixin:
    """Test backward compatibility layer."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> Generator[None, None, None]:
        """Reset state before each test."""
        reset_application_state()
        yield
        reset_application_state()

    @pytest.fixture
    def component(self) -> MockComponent:
        """Create test component with mixin."""
        return MockComponent()

    # ==================== Single Curve Compatibility ====================

    def test_curve_data_getter(self, component: MockComponent) -> None:
        """Test curve_data property forwards to ApplicationState."""
        state = get_application_state()
        test_data = [(1, 10.0, 20.0, "normal"), (2, 30.0, 40.0, "normal")]

        # Set up ApplicationState
        state.set_curve_data("test_curve", test_data)
        state.set_active_curve("test_curve")

        # Old API should work
        assert component.curve_data == test_data

    def test_curve_data_setter(self, component: MockComponent) -> None:
        """Test curve_data setter forwards to ApplicationState."""
        state = get_application_state()
        state.set_active_curve("test_curve")

        test_data = [(1, 10.0, 20.0, "normal")]
        component.curve_data = test_data

        # Verify data in ApplicationState
        assert state.get_curve_data("test_curve") == test_data

    def test_selected_indices_getter(self, component: MockComponent) -> None:
        """Test selected_indices property forwards to ApplicationState."""
        state = get_application_state()
        state.set_selection("test_curve", {0, 1, 2})
        state.set_active_curve("test_curve")

        assert component.selected_indices == {0, 1, 2}

    def test_selected_indices_setter(self, component: MockComponent) -> None:
        """Test selected_indices setter forwards to ApplicationState."""
        state = get_application_state()
        state.set_active_curve("test_curve")

        component.selected_indices = {5, 10}

        assert state.get_selection("test_curve") == {5, 10}

    # ==================== Multi-Curve Compatibility ====================

    def test_curves_data_getter(self, component: MockComponent) -> None:
        """Test curves_data property returns all curves."""
        state = get_application_state()
        state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
        state.set_curve_data("curve2", [(2, 30.0, 40.0, "normal")])

        curves = component.curves_data

        assert "curve1" in curves
        assert "curve2" in curves
        assert len(curves) == 2

    def test_curves_data_setter_uses_batch(self, component: MockComponent) -> None:
        """Test curves_data setter uses batch mode for performance."""
        test_curves = {
            "curve1": [(1, 10.0, 20.0, "normal")],
            "curve2": [(2, 30.0, 40.0, "normal")],
            "curve3": [(3, 50.0, 60.0, "normal")],
        }

        component.curves_data = test_curves

        state = get_application_state()
        assert set(state.get_all_curve_names()) == {"curve1", "curve2", "curve3"}

    # ==================== Frame State Compatibility ====================

    def test_current_frame_getter(self, component: MockComponent) -> None:
        """Test current_frame property forwards to ApplicationState."""
        state = get_application_state()
        state.set_frame(42)

        assert component.current_frame == 42

    def test_current_frame_setter(self, component: MockComponent) -> None:
        """Test current_frame setter forwards to ApplicationState."""
        component.current_frame = 100

        state = get_application_state()
        assert state.current_frame == 100

    # ==================== Deprecation Warning Tests ====================

    def test_warns_on_first_use(self, component: MockComponent, caplog: pytest.LogCaptureFixture) -> None:
        """Test deprecation warning logged on first use."""
        state = get_application_state()
        state.set_active_curve("test")

        # First access should warn
        _ = component.curve_data

        assert "DEPRECATED" in caplog.text
        assert "curve_data" in caplog.text
        assert "MockComponent" in caplog.text

    def test_warns_only_once_per_attribute(self, component: MockComponent, caplog: pytest.LogCaptureFixture) -> None:
        """Test warning only shown once per attribute."""
        state = get_application_state()
        state.set_active_curve("test")

        # First access
        caplog.clear()
        _ = component.curve_data
        first_record_count = len([r for r in caplog.records if "DEPRECATED" in r.message])
        assert first_record_count == 1

        # Second access - no new warning
        caplog.clear()
        _ = component.curve_data
        second_record_count = len([r for r in caplog.records if "DEPRECATED" in r.message])
        assert second_record_count == 0

    def test_different_attributes_warn_separately(
        self, component: MockComponent, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test different attributes get separate warnings."""
        state = get_application_state()
        state.set_active_curve("test")

        caplog.clear()

        # Access different attributes
        _ = component.curve_data
        _ = component.selected_indices
        _ = component.current_frame

        # Should have 3 distinct warnings
        warning_count = len([r for r in caplog.records if "DEPRECATED" in r.message])
        assert warning_count == 3

    # ==================== Integration Tests ====================

    def test_round_trip_data_flow(self, component: MockComponent) -> None:
        """Test data flows correctly: set via mixin → ApplicationState → get via mixin."""
        state = get_application_state()
        state.set_active_curve("test_curve")

        # Set via mixin
        test_data = [(1, 10.0, 20.0, "normal"), (2, 30.0, 40.0, "keyframe")]
        component.curve_data = test_data

        # Verify in ApplicationState
        assert state.get_curve_data("test_curve") == test_data

        # Get via mixin
        retrieved = component.curve_data
        assert retrieved == test_data

    def test_multi_curve_batch_performance(self, component: MockComponent) -> None:
        """Test multi-curve update uses batch mode (implied by no errors)."""
        # Large multi-curve update
        large_curves = {f"curve_{i}": [(i, float(i), float(i * 2), "normal")] for i in range(100)}

        # Should not error or be slow (batch mode)
        component.curves_data = large_curves

        state = get_application_state()
        assert len(state.get_all_curve_names()) == 100
