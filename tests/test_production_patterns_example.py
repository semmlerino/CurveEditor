"""
Example tests demonstrating production workflow patterns.

This test file shows how to use the new production fixtures and patterns
for testing real user workflows. Use these examples as a reference when
writing new tests.

Key Patterns:
1. production_widget_factory: Create widget in production-ready state
2. safe_test_data_factory: Generate test data avoiding boundary issues
3. user_interaction: Simulate realistic user actions
4. @assert_production_realistic: Validate no anti-patterns used

Auto-Tagging:
Tests using production fixtures are automatically tagged with @pytest.mark.production
by conftest.py's pytest_collection_modifyitems hook.
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

from stores.application_state import get_application_state
from tests.test_utils import assert_production_realistic


class TestProductionWorkflowPatterns:
    """Examples of production-realistic testing patterns."""

    def test_basic_point_selection(self, production_widget_factory, safe_test_data_factory, user_interaction):
        """Example: Basic point selection using production patterns.

        Demonstrates:
        - Factory fixture for widget setup
        - Safe test data generation
        - User interaction helper
        - Automatic production marker tagging
        """
        # Create widget with test data in production-ready state
        widget = production_widget_factory(curve_data=safe_test_data_factory(5))

        # Simulate user selecting first point
        user_interaction.select_point(widget, 0)

        # Verify selection
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        curve_name, _ = cd
        selection = app_state.get_selection(curve_name)

        assert len(selection) == 1
        assert 0 in selection

    def test_multi_selection_with_ctrl(self, production_widget_factory, safe_test_data_factory, user_interaction):
        """Example: Multi-selection using Ctrl+click.

        Demonstrates:
        - Using ctrl parameter in select_point
        - Multiple interactions in same test
        - Selection state validation
        """
        widget = production_widget_factory(curve_data=safe_test_data_factory(5))

        # Select first point
        user_interaction.select_point(widget, 0)

        # Ctrl+click second point for multi-selection
        user_interaction.select_point(widget, 1, ctrl=True)

        # Verify both selected
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        curve_name, _ = cd
        selection = app_state.get_selection(curve_name)

        assert len(selection) == 2
        assert {0, 1}.issubset(selection)

    def test_custom_data_spacing(self, production_widget_factory, safe_test_data_factory, user_interaction):
        """Example: Using custom data spacing for different scenarios.

        Demonstrates:
        - Factory parameters for different configurations
        - Multiple widget configurations in one test
        """
        # Scenario 1: Dense data with tight spacing
        dense_data = safe_test_data_factory(num_points=10, spacing=50.0)
        widget = production_widget_factory(curve_data=dense_data)
        assert len(widget.curve_data) == 10

        # Scenario 2: Sparse data with wide spacing
        sparse_data = safe_test_data_factory(num_points=5, start_margin=100.0, spacing=200.0)
        widget = production_widget_factory(curve_data=sparse_data, wait_for_render=False)
        assert len(widget.curve_data) == 5

    def test_zoom_interaction(self, production_widget_factory, safe_test_data_factory, user_interaction):
        """Example: Testing interaction after zoom.

        Demonstrates:
        - Widget state modification
        - Interaction after view changes
        - Cache invalidation handling (automatic)
        """
        widget = production_widget_factory(curve_data=safe_test_data_factory(5))

        # Zoom in (triggers cache invalidation automatically)
        widget.zoom_factor = 2.0
        widget.update()

        # Interaction should still work (cache rebuilds automatically)
        user_interaction.select_point(widget, 0)

        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        curve_name, _ = cd
        selection = app_state.get_selection(curve_name)
        assert 0 in selection

    @assert_production_realistic
    def test_validation_decorator_usage(self, production_widget_factory, safe_test_data_factory):
        """Example: Using validation decorator to prevent anti-patterns.

        Demonstrates:
        - @assert_production_realistic decorator
        - Test will fail if it uses manual cache updates
        - Clear error messages guide developer to correct pattern

        Note: This test is intentionally correct. To see the validation in action,
        try uncommenting the line below (the test will fail with helpful message):
        # widget._update_screen_points_cache()  # This would fail validation!
        """
        widget = production_widget_factory(curve_data=safe_test_data_factory(5))

        # ✅ CORRECT: No manual cache updates
        # Cache is rebuilt automatically by production_widget_factory
        assert widget.curve_data is not None

        # ❌ WRONG (commented out - would cause validation failure):
        # widget._update_screen_points_cache()

    def test_direct_click_coordinates(self, production_widget_factory, safe_test_data_factory, user_interaction):
        """Example: Direct clicking at specific coordinates.

        Demonstrates:
        - Using user_interaction.click() with coordinates
        - Testing specific screen positions
        """
        data = safe_test_data_factory(3)
        widget = production_widget_factory(curve_data=data)

        # Click at exact data coordinates (50, 50) for first point
        user_interaction.click(widget, 50.0, 50.0)

        # Verify point was selected
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        curve_name, _ = cd
        selection = app_state.get_selection(curve_name)
        assert 0 in selection  # First point should be selected

    def test_without_show(self, production_widget_factory, safe_test_data_factory):
        """Example: Widget configuration without showing (unit test pattern).

        Demonstrates:
        - Using show=False for unit tests
        - Testing logic without full rendering
        """
        # Create widget but don't show it (faster for unit tests)
        widget = production_widget_factory(curve_data=safe_test_data_factory(5), show=False)

        # Can still verify data without full render cycle
        assert len(widget.curve_data) == 5

    def test_multiple_configurations_same_test(
        self, production_widget_factory, safe_test_data_factory, user_interaction
    ):
        """Example: Testing multiple configurations in one test.

        Demonstrates:
        - Factory pattern benefit: multiple widget states
        - Resetting widget between scenarios
        """
        # Configuration 1: Small dataset
        widget = production_widget_factory(curve_data=safe_test_data_factory(3))
        user_interaction.select_point(widget, 0)

        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            pytest.fail("No active curve")
        curve_name, _ = cd
        assert 0 in app_state.get_selection(curve_name)

        # Configuration 2: Larger dataset (reuses same widget fixture)
        widget = production_widget_factory(curve_data=safe_test_data_factory(10))
        assert len(widget.curve_data) == 10


# Run specific marker examples:
# pytest tests/test_production_patterns_example.py -m production -v
# pytest tests/test_production_patterns_example.py -k "ctrl" -v
# pytest tests/test_production_patterns_example.py::TestProductionWorkflowPatterns::test_basic_point_selection -v
