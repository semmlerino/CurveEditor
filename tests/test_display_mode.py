#!/usr/bin/env python3
"""
Tests for DisplayMode enum.

Validates the DisplayMode enum's conversion logic, properties, and
migration helpers for replacing the confusing show_all_curves boolean.
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

from core.display_mode import DisplayMode


class TestDisplayModeFromLegacy:
    """Test conversion from legacy boolean state to DisplayMode."""

    def test_from_legacy_all_visible(self):
        """Test conversion when show_all_curves=True."""
        mode = DisplayMode.from_legacy(show_all_curves=True, has_selection=False)
        assert mode == DisplayMode.ALL_VISIBLE

    def test_from_legacy_all_visible_ignores_selection(self):
        """Test that ALL_VISIBLE is returned regardless of selection state."""
        mode = DisplayMode.from_legacy(show_all_curves=True, has_selection=True)
        assert mode == DisplayMode.ALL_VISIBLE

    def test_from_legacy_selected(self):
        """Test conversion when show_all_curves=False and has selection."""
        mode = DisplayMode.from_legacy(show_all_curves=False, has_selection=True)
        assert mode == DisplayMode.SELECTED

    def test_from_legacy_active_only(self):
        """Test conversion when show_all_curves=False and no selection."""
        mode = DisplayMode.from_legacy(show_all_curves=False, has_selection=False)
        assert mode == DisplayMode.ACTIVE_ONLY


class TestDisplayModeToLegacy:
    """Test conversion from DisplayMode to legacy boolean state."""

    def test_to_legacy_all_visible(self):
        """Test ALL_VISIBLE converts to (True, False)."""
        show_all, should_select = DisplayMode.ALL_VISIBLE.to_legacy()
        assert show_all is True
        assert should_select is False

    def test_to_legacy_selected(self):
        """Test SELECTED converts to (False, True)."""
        show_all, should_select = DisplayMode.SELECTED.to_legacy()
        assert show_all is False
        assert should_select is True

    def test_to_legacy_active_only(self):
        """Test ACTIVE_ONLY converts to (False, False)."""
        show_all, should_select = DisplayMode.ACTIVE_ONLY.to_legacy()
        assert show_all is False
        assert should_select is False


class TestDisplayModeRoundTrip:
    """Test round-trip conversion between DisplayMode and legacy state."""

    def test_roundtrip_all_visible(self):
        """Test ALL_VISIBLE survives round-trip conversion."""
        original = DisplayMode.ALL_VISIBLE
        show_all, should_select = original.to_legacy()
        converted = DisplayMode.from_legacy(show_all, should_select)
        assert converted == original

    def test_roundtrip_selected(self):
        """Test SELECTED survives round-trip conversion."""
        original = DisplayMode.SELECTED
        show_all, should_select = original.to_legacy()
        converted = DisplayMode.from_legacy(show_all, should_select)
        assert converted == original

    def test_roundtrip_active_only(self):
        """Test ACTIVE_ONLY survives round-trip conversion."""
        original = DisplayMode.ACTIVE_ONLY
        show_all, should_select = original.to_legacy()
        converted = DisplayMode.from_legacy(show_all, should_select)
        assert converted == original


class TestDisplayModeProperties:
    """Test DisplayMode properties for UI display."""

    def test_display_name_all_visible(self):
        """Test display name for ALL_VISIBLE mode."""
        assert DisplayMode.ALL_VISIBLE.display_name == "All Visible Curves"

    def test_display_name_selected(self):
        """Test display name for SELECTED mode."""
        assert DisplayMode.SELECTED.display_name == "Selected Curves"

    def test_display_name_active_only(self):
        """Test display name for ACTIVE_ONLY mode."""
        assert DisplayMode.ACTIVE_ONLY.display_name == "Active Curve Only"

    def test_description_all_visible(self):
        """Test description for ALL_VISIBLE mode."""
        desc = DisplayMode.ALL_VISIBLE.description
        assert "all curves" in desc.lower()
        assert "visible" in desc.lower()

    def test_description_selected(self):
        """Test description for SELECTED mode."""
        desc = DisplayMode.SELECTED.description
        assert "selected" in desc.lower()

    def test_description_active_only(self):
        """Test description for ACTIVE_ONLY mode."""
        desc = DisplayMode.ACTIVE_ONLY.description
        assert "active" in desc.lower()


class TestDisplayModeComparison:
    """Test DisplayMode enum comparison and identity."""

    def test_enum_equality(self):
        """Test enum values are equal to themselves."""
        assert DisplayMode.ALL_VISIBLE == DisplayMode.ALL_VISIBLE
        assert DisplayMode.SELECTED == DisplayMode.SELECTED
        assert DisplayMode.ACTIVE_ONLY == DisplayMode.ACTIVE_ONLY

    def test_enum_inequality(self):
        """Test enum values are not equal to each other."""
        assert DisplayMode.ALL_VISIBLE != DisplayMode.SELECTED
        assert DisplayMode.ALL_VISIBLE != DisplayMode.ACTIVE_ONLY
        assert DisplayMode.SELECTED != DisplayMode.ACTIVE_ONLY

    def test_enum_identity(self):
        """Test enum values are singletons."""
        assert DisplayMode.ALL_VISIBLE is DisplayMode.ALL_VISIBLE
        assert DisplayMode.SELECTED is DisplayMode.SELECTED
        assert DisplayMode.ACTIVE_ONLY is DisplayMode.ACTIVE_ONLY


class TestDisplayModeUsagePatterns:
    """Test common usage patterns with DisplayMode."""

    def test_pattern_matching(self):
        """Test DisplayMode works with pattern matching (Python 3.10+)."""

        def get_action(mode: DisplayMode) -> str:
            match mode:
                case DisplayMode.ALL_VISIBLE:
                    return "show_all"
                case DisplayMode.SELECTED:
                    return "show_selected"
                case DisplayMode.ACTIVE_ONLY:
                    return "show_active"

        assert get_action(DisplayMode.ALL_VISIBLE) == "show_all"
        assert get_action(DisplayMode.SELECTED) == "show_selected"
        assert get_action(DisplayMode.ACTIVE_ONLY) == "show_active"

    def test_if_elif_pattern(self):
        """Test DisplayMode works with traditional if/elif."""

        def get_action(mode: DisplayMode) -> str:
            if mode == DisplayMode.ALL_VISIBLE:
                return "show_all"
            elif mode == DisplayMode.SELECTED:
                return "show_selected"
            else:  # ACTIVE_ONLY
                return "show_active"

        assert get_action(DisplayMode.ALL_VISIBLE) == "show_all"
        assert get_action(DisplayMode.SELECTED) == "show_selected"
        assert get_action(DisplayMode.ACTIVE_ONLY) == "show_active"

    def test_migration_example(self):
        """Test migration from legacy to new code."""
        # Old code state
        show_all_curves = False
        selected_curve_names = {"curve1", "curve2"}

        # Convert to DisplayMode
        mode = DisplayMode.from_legacy(
            show_all_curves=show_all_curves,
            has_selection=len(selected_curve_names) > 0,
        )

        # Verify correct mode detected
        assert mode == DisplayMode.SELECTED

        # Use in new code
        curves_to_display = selected_curve_names if mode == DisplayMode.SELECTED else set()

        assert curves_to_display == {"curve1", "curve2"}
