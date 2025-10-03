#!/usr/bin/env python
"""
Compatibility layer for gradual migration to ApplicationState.

Allows old code to continue working during transition.
Will be removed in Week 10 after full migration.

This mixin provides backward-compatible properties that forward
old attribute access patterns to the new ApplicationState while
logging deprecation warnings to guide migration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.type_aliases import CurveDataList
from stores.application_state import get_application_state

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StateMigrationMixin:
    """
    Mixin providing backward-compatible properties.

    Forwards old attribute access to ApplicationState while
    logging deprecation warnings.

    Usage:
        class CurveViewWidget(StateMigrationMixin, QWidget):
            # Old code using self.curve_data still works
            pass

    Design:
        - Only warns once per attribute per instance (no spam)
        - Uses ApplicationState as single source of truth
        - Batch mode for multi-curve updates (performance)
        - Compatible with existing code patterns

    Migration Path:
        Week 2: Add to components needing compatibility
        Weeks 3-9: Migrate components one-by-one
        Week 10: Remove this file (all migrated)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._app_state = get_application_state()
        self._migration_warnings_shown: set[str] = set()

    # ==================== Single Curve Properties ====================

    @property
    def curve_data(self) -> CurveDataList:
        """DEPRECATED: Use get_application_state().get_curve_data()"""
        self._warn_deprecated("curve_data", "get_application_state().get_curve_data()")
        return self._app_state.get_curve_data()

    @curve_data.setter
    def curve_data(self, value: CurveDataList) -> None:
        """DEPRECATED: Use ApplicationState.set_curve_data()"""
        self._warn_deprecated("curve_data setter", "ApplicationState.set_curve_data()")
        if self._app_state.active_curve:
            self._app_state.set_curve_data(self._app_state.active_curve, value)

    @property
    def selected_indices(self) -> set[int]:
        """DEPRECATED: Use get_application_state().get_selection()"""
        self._warn_deprecated("selected_indices", "get_application_state().get_selection()")
        return self._app_state.get_selection()

    @selected_indices.setter
    def selected_indices(self, value: set[int]) -> None:
        """DEPRECATED: Use ApplicationState.set_selection()"""
        self._warn_deprecated("selected_indices setter", "ApplicationState.set_selection()")
        if self._app_state.active_curve:
            self._app_state.set_selection(self._app_state.active_curve, value)

    # ==================== Multi-Curve Properties ====================

    @property
    def curves_data(self) -> dict[str, CurveDataList]:
        """DEPRECATED: Use ApplicationState multi-curve methods"""
        self._warn_deprecated("curves_data", "ApplicationState multi-curve methods")
        return {name: self._app_state.get_curve_data(name) for name in self._app_state.get_all_curve_names()}

    @curves_data.setter
    def curves_data(self, value: dict[str, CurveDataList]) -> None:
        """DEPRECATED: Use ApplicationState.set_curve_data() per curve"""
        self._warn_deprecated("curves_data setter", "ApplicationState.set_curve_data()")
        self._app_state.begin_batch()
        try:
            for curve_name, data in value.items():
                self._app_state.set_curve_data(curve_name, data)
        finally:
            self._app_state.end_batch()

    # ==================== Frame State ====================

    @property
    def current_frame(self) -> int:
        """DEPRECATED: Use get_application_state().current_frame"""
        self._warn_deprecated("current_frame", "get_application_state().current_frame")
        return self._app_state.current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """DEPRECATED: Use ApplicationState.set_frame()"""
        self._warn_deprecated("current_frame setter", "ApplicationState.set_frame()")
        self._app_state.set_frame(value)

    # ==================== Helper Methods ====================

    def _warn_deprecated(self, old_api: str, new_api: str) -> None:
        """Log deprecation warning once per attribute.

        Args:
            old_api: The old API being accessed (e.g., "curve_data")
            new_api: The recommended replacement API

        Note:
            Only warns once per attribute per instance to avoid log spam.
            Warnings include class name for easy tracking of migration progress.
        """
        if old_api not in self._migration_warnings_shown:
            logger.warning(f"DEPRECATED: {old_api} used in {self.__class__.__name__}. " f"Migrate to: {new_api}")
            self._migration_warnings_shown.add(old_api)
