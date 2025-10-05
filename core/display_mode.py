#!/usr/bin/env python3
"""
Display mode enumeration for curve visibility control.

This module defines the DisplayMode enum which replaces the confusing
show_all_curves boolean with explicit, self-documenting states.
"""

from enum import Enum, auto
from typing import override


class DisplayMode(Enum):
    """
    Defines which curves should be displayed in the viewport.

    Replaces the confusing show_all_curves boolean with explicit states that
    clearly communicate intent without requiring coordination with other state.

    The Problem with show_all_curves Boolean
    =========================================
    The old boolean approach had implicit semantics that required developers
    to remember multiple coordination rules:

    - show_all_curves=True → Show all visible curves
    - show_all_curves=False + selected_curve_names empty → Show active only
    - show_all_curves=False + selected_curve_names non-empty → Show selected

    This created confusion because the boolean's meaning changed based on
    another piece of state (selected_curve_names), making the code harder
    to understand and maintain.

    The DisplayMode Solution
    =========================
    DisplayMode makes the intent explicit and self-contained:

    - ALL_VISIBLE: Show all curves marked as visible (clear intent)
    - SELECTED: Show only selected curves (clear intent)
    - ACTIVE_ONLY: Show only the active curve (clear intent)

    Migration Path
    ==============
    Old code:
        if show_all_curves:
            # Show all curves
        elif selected_curve_names:
            # Show selected curves
        else:
            # Show active curve only

    New code:
        match display_mode:
            case DisplayMode.ALL_VISIBLE:
                # Show all curves
            case DisplayMode.SELECTED:
                # Show selected curves
            case DisplayMode.ACTIVE_ONLY:
                # Show active curve only

    Or with simple if/elif:
        if display_mode == DisplayMode.ALL_VISIBLE:
            # Show all curves
        elif display_mode == DisplayMode.SELECTED:
            # Show selected curves
        else:  # DisplayMode.ACTIVE_ONLY
            # Show active curve only

    Examples
    ========
    >>> # Convert from legacy boolean
    >>> mode = DisplayMode.from_legacy(show_all_curves=True, has_selection=False)
    >>> mode
    <DisplayMode.ALL_VISIBLE: 1>

    >>> # Convert to legacy for gradual migration
    >>> mode = DisplayMode.SELECTED
    >>> show_all, should_select = mode.to_legacy()
    >>> show_all
    False
    >>> should_select
    True

    >>> # Use in rendering logic
    >>> def get_curves_to_render(mode: DisplayMode) -> list[str]:
    ...     if mode == DisplayMode.ALL_VISIBLE:
    ...         return get_all_visible_curves()
    ...     elif mode == DisplayMode.SELECTED:
    ...         return get_selected_curves()
    ...     else:  # ACTIVE_ONLY
    ...         return [get_active_curve()]
    """

    ALL_VISIBLE = auto()  # Show all curves with visible=True (old: show_all_curves=True)
    SELECTED = auto()  # Show only selected curves (old: show_all_curves=False + selected_curve_names)
    ACTIVE_ONLY = auto()  # Show only active curve (old: show_all_curves=False + empty selection)

    @classmethod
    def from_legacy(cls, show_all_curves: bool, has_selection: bool) -> "DisplayMode":
        """
        Convert legacy boolean state to DisplayMode enum.

        This method enables gradual migration from the old boolean approach
        to the new explicit enum approach.

        Args:
            show_all_curves: Legacy boolean indicating whether to show all curves
            has_selection: Whether there are selected curves (len(selected_curve_names) > 0)

        Returns:
            Corresponding DisplayMode enum value

        Conversion Logic:
            - show_all_curves=True → ALL_VISIBLE
            - show_all_curves=False + has_selection=True → SELECTED
            - show_all_curves=False + has_selection=False → ACTIVE_ONLY

        Examples:
            >>> # Legacy: show all visible curves
            >>> DisplayMode.from_legacy(show_all_curves=True, has_selection=False)
            <DisplayMode.ALL_VISIBLE: 1>

            >>> # Legacy: show selected curves
            >>> DisplayMode.from_legacy(show_all_curves=False, has_selection=True)
            <DisplayMode.SELECTED: 2>

            >>> # Legacy: show active curve only
            >>> DisplayMode.from_legacy(show_all_curves=False, has_selection=False)
            <DisplayMode.ACTIVE_ONLY: 3>
        """
        if show_all_curves:
            return cls.ALL_VISIBLE
        elif has_selection:
            return cls.SELECTED
        else:
            return cls.ACTIVE_ONLY

    def to_legacy(self) -> tuple[bool, bool]:
        """
        Convert DisplayMode to legacy boolean state.

        This method supports gradual migration by allowing new code using
        DisplayMode to interoperate with old code still using booleans.

        Returns:
            Tuple of (show_all_curves, should_have_selection)
            - show_all_curves: Legacy boolean for showing all curves
            - should_have_selection: Whether selection should be non-empty

        Conversion Logic:
            - ALL_VISIBLE → (True, False) - show all, selection doesn't matter
            - SELECTED → (False, True) - don't show all, selection must exist
            - ACTIVE_ONLY → (False, False) - don't show all, no selection

        Examples:
            >>> DisplayMode.ALL_VISIBLE.to_legacy()
            (True, False)

            >>> DisplayMode.SELECTED.to_legacy()
            (False, True)

            >>> DisplayMode.ACTIVE_ONLY.to_legacy()
            (False, False)

        Migration Example:
            >>> # New code using DisplayMode
            >>> mode = DisplayMode.SELECTED
            >>>
            >>> # Interoperate with old code
            >>> show_all, should_select = mode.to_legacy()
            >>> old_api.set_visibility(show_all_curves=show_all)
            >>> if should_select:
            ...     old_api.ensure_selection_exists()
        """
        if self == DisplayMode.ALL_VISIBLE:
            return (True, False)
        elif self == DisplayMode.SELECTED:
            return (False, True)
        else:  # ACTIVE_ONLY
            return (False, False)

    @property
    def display_name(self) -> str:
        """
        Get human-readable display name for UI.

        Returns:
            User-friendly string describing the display mode

        Examples:
            >>> DisplayMode.ALL_VISIBLE.display_name
            'All Visible Curves'

            >>> DisplayMode.SELECTED.display_name
            'Selected Curves'

            >>> DisplayMode.ACTIVE_ONLY.display_name
            'Active Curve Only'
        """
        if self == DisplayMode.ALL_VISIBLE:
            return "All Visible Curves"
        elif self == DisplayMode.SELECTED:
            return "Selected Curves"
        else:  # ACTIVE_ONLY
            return "Active Curve Only"

    @property
    def description(self) -> str:
        """
        Get detailed description for tooltips and documentation.

        Returns:
            Detailed description of what this mode displays

        Examples:
            >>> DisplayMode.ALL_VISIBLE.description
            'Display all curves marked as visible in the viewport'
        """
        if self == DisplayMode.ALL_VISIBLE:
            return "Display all curves marked as visible in the viewport"
        elif self == DisplayMode.SELECTED:
            return "Display only the curves selected in the tracking points panel"
        else:  # ACTIVE_ONLY
            return "Display only the currently active curve for editing"

    @override
    def __str__(self) -> str:
        """
        Return human-readable string for logging and debugging.

        Returns:
            Human-readable display name

        Examples:
            >>> str(DisplayMode.ALL_VISIBLE)
            'All Visible Curves'

            >>> logger.debug(f"Display mode: {mode}")  # Uses __str__ automatically
            Display mode: All Visible Curves
        """
        return self.display_name
