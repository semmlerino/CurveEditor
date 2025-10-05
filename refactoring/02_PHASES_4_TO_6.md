# Selection State Refactoring - Phases 4-6: Integration & Testing

**Navigation**: [← Phases 1-3](01_PHASES_1_TO_3.md) | [Phases 7-8 & Completion →](03_PHASES_7_TO_8_AND_COMPLETION.md)

---
## Phase 4: Update MultiCurveManager

**Files Modified**: `ui/multi_curve_manager.py`
**Dependencies**: Phase 1-3 complete
**Risk Level**: LOW (backward compatible via deprecation properties)

### 🤖 Recommended Agent

**`python-implementation-specialist`**
- **Scope**: `ui/multi_curve_manager.py` only
- **Task**: Add backward-compat properties, update methods to use ApplicationState
- **Reasoning**: Standard implementation with deprecation pattern
- **Context to provide**:
  - Phases 1-3 implementation results
  - Any fixes from post-Phase 3 review
  - Full Phase 4 specification from this document

### Step 4.1: Add Backward-Compatible selected_curve_names Property

**Location**: `ui/multi_curve_manager.py:47-48`

**BEFORE**:
```python
# NEW: Track selected curves for multi-curve display
self.selected_curve_names: set[str] = set()
```

**AFTER**:
```python
# REMOVED: selected_curve_names now in ApplicationState
# Backward-compatible property provided below for gradual migration
```

**Add this property at class level** (after `__init__`):

```python
@property
def selected_curve_names(self) -> set[str]:
    """
    DEPRECATED: Access selected curves via ApplicationState.

    This property is deprecated and will be removed in Phase 8.
    Use: get_application_state().get_selected_curves()

    Returns:
        Set of selected curve names from ApplicationState
    """
    import warnings
    warnings.warn(
        "manager.selected_curve_names is deprecated. "
        "Use get_application_state().get_selected_curves() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return self._app_state.get_selected_curves()

@selected_curve_names.setter
def selected_curve_names(self, value: set[str]) -> None:
    """
    DEPRECATED: Set selected curves via ApplicationState.

    This setter is deprecated and will be removed in Phase 8.
    Use: get_application_state().set_selected_curves(value)

    Args:
        value: Set of curve names to select
    """
    import warnings
    warnings.warn(
        "Setting manager.selected_curve_names is deprecated. "
        "Use get_application_state().set_selected_curves() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    self._app_state.set_selected_curves(value)
```

### Step 4.2: Update set_curves_data Method

**Location**: `ui/multi_curve_manager.py:76-135`

**Key changes**:
1. Use `app_state.set_selected_curves()` instead of `self.selected_curve_names`
2. Remove manual `widget.display_mode =` assignment (deprecated)

**BEFORE**:
```python
def set_curves_data(
    self,
    curves: dict[str, CurveDataList],
    metadata: dict[str, dict[str, Any]] | None = None,
    active_curve: str | None = None,
    selected_curves: list[str] | None = None,
) -> None:
    """[docstring]"""
    # Use batch mode to prevent signal storms
    self._app_state.begin_batch()
    try:
        # Set all curve data in ApplicationState
        for name, data in curves.items():
            curve_metadata = metadata.get(name) if metadata else None
            self._app_state.set_curve_data(name, data, curve_metadata)

            # Set default metadata if not provided
            if not curve_metadata:
                current_meta = self._app_state.get_curve_metadata(name)
                if "visible" not in current_meta:
                    self._app_state.set_curve_visibility(name, True)

        # Update selected curves if specified
        if selected_curves is not None:
            self.selected_curve_names = set(selected_curves)
            # CRITICAL FIX: Update display mode to SELECTED when curves are selected
            # This fixes the bug where selecting multiple curves only shows one
            if selected_curves:
                self.widget.display_mode = DisplayMode.SELECTED  # ❌ OLD WAY
        elif not self.selected_curve_names:
            # If no selection specified and no existing selection, default to active curve
            self.selected_curve_names = {active_curve} if active_curve else set()

        # ... rest of method ...
```

**AFTER**:
```python
def set_curves_data(
    self,
    curves: dict[str, CurveDataList],
    metadata: dict[str, dict[str, Any]] | None = None,
    active_curve: str | None = None,
    selected_curves: list[str] | None = None,
) -> None:
    """
    Set multiple curves to display.

    Args:
        curves: Dictionary mapping curve names to curve data
        metadata: Optional dictionary with per-curve metadata (visibility, color, etc.)
        active_curve: Name of the currently active curve for editing
        selected_curves: Optional list of curves to select for display
    """
    # Use batch mode to prevent signal storms
    self._app_state.begin_batch()
    try:
        # Set all curve data in ApplicationState
        for name, data in curves.items():
            curve_metadata = metadata.get(name) if metadata else None
            self._app_state.set_curve_data(name, data, curve_metadata)

            # Set default metadata if not provided
            if not curve_metadata:
                current_meta = self._app_state.get_curve_metadata(name)
                if "visible" not in current_meta:
                    self._app_state.set_curve_visibility(name, True)

        # NEW: Update selection in ApplicationState (single source of truth)
        if selected_curves is not None:
            self._app_state.set_selected_curves(set(selected_curves))
            # NO MANUAL display_mode UPDATE NEEDED - computed automatically! ✅
        elif active_curve:
            # Default to active curve if no selection specified
            self._app_state.set_selected_curves({active_curve})

        # Set the active curve
        if active_curve and active_curve in curves:
            self._app_state.set_active_curve(active_curve)
            # Update the single curve data for backward compatibility
            self.widget.set_curve_data(curves[active_curve])
        elif curves:
            # Default to first curve if no active curve specified
            first_curve = next(iter(curves.keys()))
            self._app_state.set_active_curve(first_curve)
            self.widget.set_curve_data(curves[first_curve])
        else:
            self._app_state.set_active_curve(None)
            self.widget.set_curve_data([])
    finally:
        self._app_state.end_batch()

    # Trigger repaint to show all curves
    self.widget.update()
    logger.debug(
        f"Set {len(curves)} curves, active: {self._app_state.active_curve}, "
        f"selected: {self._app_state.get_selected_curves()}, "
        f"mode: {self._app_state.display_mode}"
    )
```

### Step 4.3: Update set_selected_curves Method

**Location**: `ui/multi_curve_manager.py:252-269`

**BEFORE**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """[docstring]"""
    self.selected_curve_names = set(curve_names)

    # ... rest of implementation ...
```

**AFTER**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """
    Set selected curves for display.

    Args:
        curve_names: List of curve names to select
    """
    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(curve_names))

    # Update widget's ordered list for rendering order
    self.widget.selected_curve_names = set(curve_names)
    self.widget.selected_curves_ordered = list(curve_names)

    # Trigger repaint
    self.widget.update()

    logger.debug(
        f"Selected curves: {self._app_state.get_selected_curves()}, "
        f"Active: {self._app_state.active_curve}, "
        f"Mode: {self._app_state.display_mode}"
    )
```

### Step 4.4: Update center_on_selected_curves Method

**Location**: `ui/multi_curve_manager.py:271-336`

**BEFORE**:
```python
def center_on_selected_curves(self) -> None:
    """[docstring]"""
    all_curve_names = self._app_state.get_all_curve_names()
    logger.debug(
        f"center_on_selected_curves called with selected: {self.selected_curve_names}, ApplicationState curves: {all_curve_names}"
    )
    if not self.selected_curve_names or not all_curve_names:
        # ... rest ...

    for curve_name in self.selected_curve_names:
        # ... rest ...
```

**AFTER**:
```python
def center_on_selected_curves(self) -> None:
    """Center view on all selected curves."""
    all_curve_names = self._app_state.get_all_curve_names()
    selected_curves = self._app_state.get_selected_curves()  # NEW: Read from ApplicationState

    logger.debug(
        f"center_on_selected_curves called with selected: {selected_curves}, ApplicationState curves: {all_curve_names}"
    )
    if not selected_curves or not all_curve_names:
        logger.debug("Early return - no selected curves or no data in ApplicationState")
        return

    # Collect all points from all selected curves
    all_points: list[tuple[float, float]] = []

    for curve_name in selected_curves:  # NEW: Use ApplicationState selection
        if curve_name in all_curve_names:
            # ... rest unchanged ...
```

### Verification Steps

1. **Type check**:
   ```bash
   ./bpr ui/multi_curve_manager.py
   ```

2. **Test set_curves_data uses ApplicationState**:
   ```python
   from ui.multi_curve_manager import MultiCurveManager
   from ui.curve_view_widget import CurveViewWidget
   from stores.application_state import get_application_state, reset_application_state
   from core.display_mode import DisplayMode
   from core.models import CurvePoint

   reset_application_state()
   widget = CurveViewWidget()
   manager = MultiCurveManager(widget)
   app_state = get_application_state()

   # Set curves with selection
   manager.set_curves_data(
       {"curve1": [CurvePoint(1, 10, 20)], "curve2": [CurvePoint(1, 30, 40)]},
       selected_curves=["curve1", "curve2"]
   )

   # ApplicationState updated
   assert app_state.get_selected_curves() == {"curve1", "curve2"}
   assert app_state.display_mode == DisplayMode.SELECTED
   print("✅ Manager updates ApplicationState correctly")
   ```

3. **Test backward-compat property**:
   ```python
   import warnings

   # Old API (reading field) still works but warns
   with warnings.catch_warnings(record=True) as w:
       warnings.simplefilter("always")
       selected = manager.selected_curve_names
       assert len(w) == 1
       assert "deprecated" in str(w[0].message).lower()
       assert selected == {"curve1", "curve2"}

   print("✅ Backward-compat property works")
   ```

### Rollback Instructions

1. Revert: `git checkout ui/multi_curve_manager.py`
2. Type check: `./bpr ui/multi_curve_manager.py`

---

## Phase 5: Update Controllers

**Files Modified**:
- `ui/controllers/multi_point_tracking_controller.py`
- `ui/controllers/curve_view/curve_data_facade.py`
- `ui/main_window.py`

**Dependencies**: Phase 1-4 complete
**Risk Level**: MEDIUM (fixes synchronization loop bug)

### 🤖 Recommended Agent

**`python-implementation-specialist`**
- **Scope**: 3 controller files (explicit scope per file)
- **Task**: Remove synchronization loop, update controllers to use ApplicationState
- **Reasoning**: Clear specification, critical bug fix well-documented
- **Context to provide**:
  - Phases 1-4 results
  - Full Phase 5 specification
  - Critical fixes: "FIX #1: Remove synchronization loop", "FIX #5: Remove redundant update", "FIX #7: Edge case handling"

### 🔍 Post-Phase 5 Review (Launch in Parallel)

After completing Phases 4-5, **launch verification team in parallel**:

**Agent 1: `python-code-reviewer`**
- **Task**: "Review Phases 4-5 changes for code quality and correctness"
- **Files**: `ui/multi_curve_manager.py`, all Phase 5 controller files

**Agent 2: `type-system-expert`**
- **Task**: "Verify type safety in modified controllers and manager"
- **Files**: Same as above

**Agent 3: `deep-debugger`**
- **Task**: "Verify synchronization loop fix eliminates race condition. Analyze signal flow in on_tracking_points_selected"
- **Files**: Focus on `ui/controllers/multi_point_tracking_controller.py`

**Synthesis**: Review all three reports, verify race condition fixed, fix any issues before Phase 6.

### Step 5.1: Remove Synchronization Loop and Redundant Update

**Location**: `ui/controllers/multi_point_tracking_controller.py:342-377`

**CRITICAL**: This fixes the original race condition bug.

**BEFORE**:
```python
def on_tracking_points_selected(self, point_names: list[str]) -> None:
    """Handle selection of tracking points from panel."""
    # Set the last selected point as the active timeline point
    self.main_window.active_timeline_point = point_names[-1] if point_names else None

    # ❌ SYNCHRONIZATION LOOP - THIS LINE CREATES THE BUG:
    # Synchronize table selection FIRST (before update_curve_display queries it)
    # This prevents race condition where set_selected_points() clears selection mid-update
    if self.main_window.tracking_panel:
        self.main_window.tracking_panel.set_selected_points(point_names)  # ← REMOVE THIS

    # Synchronize selection state to CurveDataStore
    self._sync_tracking_selection_to_curve_store(point_names)

    # Update the curve display with MANUAL_SELECTION context
    self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=point_names)

    # ... rest of method ...
```

**AFTER**:
```python
def on_tracking_points_selected(self, point_names: list[str]) -> None:
    """
    Handle selection of tracking points from panel.

    FIX #1: Synchronization loop removed - panel already has correct selection.
    FIX #5: Redundant ApplicationState update removed - panel already updated it.

    The panel has already:
    1. Updated its UI selection
    2. Updated ApplicationState via _on_selection_changed()
    3. Emitted this signal

    We just need to handle OTHER responsibilities (timeline, store sync, display).
    NO need to sync back to panel - that creates circular dependency!

    Args:
        point_names: List of selected point names (curve names/trajectories)
    """
    # Set the last selected point as the active timeline point
    self.main_window.active_timeline_point = point_names[-1] if point_names else None

    # ✅ REMOVED synchronization loop (panel already has correct selection)
    # ✅ REMOVED redundant ApplicationState update (panel already did it)

    # Synchronize selection state to CurveDataStore (backward compatibility)
    self._sync_tracking_selection_to_curve_store(point_names)

    # Update the curve display with MANUAL_SELECTION context
    self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=point_names)

    # Center view on selected point at current frame
    # Small delay to ensure curve data and point selection are processed
    if self.main_window.curve_widget and point_names:
        if callable(getattr(self.main_window.curve_widget, "center_on_selection", None)):
            # Use small delay to allow widget updates to complete
            def safe_center_on_selection():
                if self.main_window.curve_widget and not self.main_window.curve_widget.isHidden():
                    self.main_window.curve_widget.center_on_selection()

            QTimer.singleShot(10, safe_center_on_selection)
            logger.debug("Scheduled centering on selected point after 10ms delay")

    logger.debug(f"Selected tracking points: {point_names}")
```

### Step 5.2: Update set_display_mode with Edge Case Handling

**Location**: `ui/controllers/multi_point_tracking_controller.py:894-920`

**FIX #7**: Handle edge case when no active curve available.

**BEFORE**:
```python
def set_display_mode(self, mode: DisplayMode) -> None:
    """[docstring]"""
    widget = self.main_window.curve_widget
    if not widget:
        return

    # ❌ OLD: Set display_mode directly
    widget.display_mode = mode

    # Handle mode-specific logic
    if mode == DisplayMode.SELECTED:
        # ... logic ...
```

**AFTER**:
```python
def set_display_mode(self, mode: DisplayMode) -> None:
    """
    Set display mode for curve rendering.

    Updates ApplicationState which automatically computes display_mode.

    Args:
        mode: DisplayMode to set
    """
    widget = self.main_window.curve_widget
    if not widget:
        return

    # NEW: Update ApplicationState based on desired mode
    if mode == DisplayMode.ALL_VISIBLE:
        self._app_state.set_show_all_curves(True)

    elif mode == DisplayMode.SELECTED:
        self._app_state.set_show_all_curves(False)

        # FIX #7: Handle edge case when no curves available
        current_selection = self._app_state.get_selected_curves()
        if not current_selection:
            if widget.active_curve_name:
                # Select active curve
                self._app_state.set_selected_curves({widget.active_curve_name})
            else:
                # No active curve - can't achieve SELECTED mode
                logger.warning(
                    "Cannot set SELECTED mode: no curves selected and no active curve available. "
                    "Mode will remain ACTIVE_ONLY."
                )
                # Still set show_all to False as requested
                # display_mode will compute to ACTIVE_ONLY automatically

    elif mode == DisplayMode.ACTIVE_ONLY:
        self._app_state.set_show_all_curves(False)
        self._app_state.set_selected_curves(set())  # Clear selection

    # Trigger repaint
    widget.update()

    logger.debug(
        f"Set display mode: requested={mode}, "
        f"show_all={self._app_state.get_show_all_curves()}, "
        f"selected={self._app_state.get_selected_curves()}, "
        f"computed_mode={self._app_state.display_mode}"
    )
```

### Step 5.3: Update set_selected_curves Method

**Location**: `ui/controllers/multi_point_tracking_controller.py:922-945`

**BEFORE**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """[docstring]"""
    widget = self.main_window.curve_widget
    if not widget:
        return

    # Update widget state
    widget.selected_curve_names = set(curve_names)
    widget.selected_curves_ordered = list(curve_names)

    # ... rest ...
```

**AFTER**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """
    Set selected curves for display.

    Args:
        curve_names: List of curve names to select
    """
    widget = self.main_window.curve_widget
    if not widget:
        return

    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(curve_names))

    # Update widget's ordered list for rendering order (backward compatibility)
    widget.selected_curve_names = set(curve_names)
    widget.selected_curves_ordered = list(curve_names)

    # Trigger repaint
    widget.update()

    logger.debug(
        f"Selected curves: {self._app_state.get_selected_curves()}, "
        f"Active: {self._app_state.active_curve}, "
        f"Mode: {self._app_state.display_mode}"
    )
```

### Step 5.4: Update curve_data_facade.py

**Location**: `ui/controllers/curve_view/curve_data_facade.py:155-164`

**BEFORE**:
```python
if selected_curves is not None:
    self.widget.selected_curve_names = set(selected_curves)
    self.widget.selected_curves_ordered = list(selected_curves)
    if selected_curves:
        self.widget.display_mode = DisplayMode.SELECTED  # ❌ OLD WAY
        logger.info(f"  display_mode AFTER setting SELECTED: {self.widget.display_mode}")
    elif not self.widget.selected_curve_names:
        # Default to active curve
        self.widget.selected_curve_names = {active_curve} if active_curve else set()
        self.widget.selected_curves_ordered = [active_curve] if active_curve else []
```

**AFTER**:
```python
if selected_curves is not None:
    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(selected_curves))

    # Update widget's ordered list for rendering (backward compatibility)
    self.widget.selected_curve_names = set(selected_curves)
    self.widget.selected_curves_ordered = list(selected_curves)

    # NO MANUAL display_mode UPDATE - computed automatically! ✅
    logger.info(f"  display_mode AUTO-computed: {self._app_state.display_mode}")
elif active_curve:
    # Default to active curve
    self._app_state.set_selected_curves({active_curve})
    self.widget.selected_curve_names = {active_curve}
    self.widget.selected_curves_ordered = [active_curve]
```

### Step 5.5: Add ApplicationState reference to curve_data_facade.py

**Location**: `ui/controllers/curve_view/curve_data_facade.py` (in `__init__`)

**CODE TO ADD**:
```python
def __init__(self, widget: CurveViewWidget):
    self.widget = widget

    # NEW: ApplicationState reference
    from stores.application_state import get_application_state
    self._app_state = get_application_state()
```

### Step 5.6: Update main_window.py

**Location**: `ui/main_window.py:941-943`

**BEFORE**:
```python
def _on_display_mode_changed(self, mode: DisplayMode) -> None:
    """Handle display mode changes from tracking panel."""
    self.curve_widget.display_mode = mode  # ❌ OLD WAY

    # Trigger widget repaint
    self.curve_widget.update()
```

**AFTER**:
```python
def _on_display_mode_changed(self, mode: DisplayMode) -> None:
    """
    Handle display mode changes from tracking panel.

    Note: TrackingPanel already updated ApplicationState in _on_display_mode_checkbox_toggled.
    This handler is for legacy signal compatibility during migration.
    The mode parameter tells us what mode was intended, but ApplicationState is already correct.
    """
    # NEW: ApplicationState already updated by TrackingPanel
    # Just trigger repaint to reflect the change
    self.curve_widget.update()

    logger.debug(
        f"Display mode signal received: {mode}, "
        f"ApplicationState mode: {self._app_state.display_mode}"
    )
```

### Step 5.7: Add ApplicationState reference to main_window.py

**Location**: `ui/main_window.py` (in `__init__`, after other service references)

**CODE TO ADD**:
```python
# In __init__, after other initializations:
from stores.application_state import get_application_state
self._app_state = get_application_state()
```

### Verification Steps

1. **Type check all controller files**:
   ```bash
   ./bpr ui/controllers/multi_point_tracking_controller.py
   ./bpr ui/controllers/curve_view/curve_data_facade.py
   ./bpr ui/main_window.py
   ```

2. **Test synchronization loop fixed**:
   ```python
   # This test would previously cause race condition
   from ui.tracking_points_panel import TrackingPointsPanel
   from stores.application_state import get_application_state, reset_application_state
   from core.models import CurvePoint

   reset_application_state()
   panel = TrackingPointsPanel()
   app_state = get_application_state()

   # Add data
   panel.set_tracked_data({
       "Track1": [CurvePoint(1, 10, 20)],
       "Track2": [CurvePoint(1, 30, 40)]
   })

   # Ctrl+click multiple items (simulated)
   panel.set_selected_points(["Track1", "Track2"])

   # Should NOT cause race condition
   assert app_state.get_selected_curves() == {"Track1", "Track2"}
   print("✅ Synchronization loop eliminated")
   ```

3. **Test edge case handling**:
   ```python
   from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController
   from ui.main_window import MainWindow
   from core.display_mode import DisplayMode

   window = MainWindow()
   controller = window.multi_point_controller
   app_state = get_application_state()

   # Try to set SELECTED mode when no curves available
   # Should log warning but not crash
   controller.set_display_mode(DisplayMode.SELECTED)

   # Mode should be ACTIVE_ONLY (not SELECTED since no curves)
   assert app_state.display_mode == DisplayMode.ACTIVE_ONLY
   print("✅ Edge case handled correctly")
   ```

### Rollback Instructions

1. Revert all files:
   ```bash
   git checkout ui/controllers/multi_point_tracking_controller.py
   git checkout ui/controllers/curve_view/curve_data_facade.py
   git checkout ui/main_window.py
   ```

2. Type check:
   ```bash
   ./bpr ui/controllers/
   ./bpr ui/main_window.py
   ```

---

## Phase 6: Update Tests

**Files Modified**: All test files that use `display_mode` setter or `selected_curve_names`
**Dependencies**: Phase 1-5 complete
**Risk Level**: LOW (test updates only)

### 🤖 Recommended Agents (Launch in Parallel)

**Safe to parallelize** - Different test files, no overlap:

**Agent 1: `test-development-master`**
- **Scope**: Create new integration test file only
- **Task**: "Create `tests/test_selection_state_integration.py` per Phase 6.4 specification"
- **Reasoning**: Master at comprehensive test creation, Qt testing expertise
- **Context**: Full Phase 6.4 specification, all edge cases from reviews

**Agent 2: `test-type-safety-specialist`**
- **Scope**: Update existing test files only
- **Task**: "Update display_mode setter usages in existing tests per Phase 6.1-6.3"
- **Files**: `tests/test_display_mode_integration.py`, `tests/test_render_state.py`, `tests/test_multi_point_selection.py`
- **Reasoning**: Expert at fixing type-safe test code patterns
- **Context**: Phase 2.5 audit results, ApplicationState API

**Post-test verification**: Run full test suite manually, verify all pass.

### Step 6.1: Update Display Mode Integration Tests

**Location**: `tests/test_display_mode_integration.py` (multiple locations)

**Pattern to Replace**:
```python
# OLD:
curve_widget.display_mode = DisplayMode.ALL_VISIBLE

# NEW:
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_show_all_curves(True)
assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
```

**Specific Updates**:

1. **Line 58** - test_display_mode_getter_all_visible:
```python
# BEFORE:
curve_widget.display_mode = DisplayMode.ALL_VISIBLE
curve_widget.selected_curve_names = set()

# AFTER:
app_state.set_show_all_curves(True)
assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
# No need to clear selection - display_mode is computed
```

2. **Follow same pattern for all test methods** at lines 79, 96, 119, 142, etc.

### Step 6.2: Update Render State Tests

**Location**: `tests/test_render_state.py`

Follow same pattern as above. All `display_mode` setter usages should be replaced with ApplicationState setters.

### Step 6.3: Update Multi-Point Selection Tests

**Location**: `tests/test_multi_point_selection.py`

Same pattern. Focus on tests around lines 154, 161, 168, 365, 400, etc.

### Step 6.4: Create Comprehensive Integration Test

**Location**: Create new file `tests/test_selection_state_integration.py`

**CODE TO ADD**:
```python
"""
Integration tests for centralized selection state architecture.

Tests the complete flow: UI → ApplicationState → rendering

Covers all edge cases identified in independent reviews:
- Batch mode state visibility
- Qt signal timing
- Invalid curve names
- Empty selection transitions
- Redundant update filtering
"""
import pytest
import warnings
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from stores.application_state import get_application_state, reset_application_state
from core.display_mode import DisplayMode
from core.models import CurvePoint
from ui.tracking_points_panel import TrackingPointsPanel
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow


class TestSelectionStateIntegration:
    """Test selection state flows through ApplicationState correctly."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        """Reset ApplicationState before each test."""
        reset_application_state()
        yield
        reset_application_state()

    def test_panel_selection_updates_app_state(self, qapp):
        """Test: Panel selection → ApplicationState → display_mode."""
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # Add tracking data
        panel.set_tracked_data({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })

        # User selects two curves
        panel.set_selected_points(["Track1", "Track2"])

        # ApplicationState updated
        assert app_state.get_selected_curves() == {"Track1", "Track2"}
        assert app_state.display_mode == DisplayMode.SELECTED

    def test_checkbox_updates_app_state(self, qapp):
        """Test: Checkbox toggle → ApplicationState → display_mode."""
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # User checks "show all"
        panel.display_mode_checkbox.setChecked(True)

        # ApplicationState updated
        assert app_state.get_show_all_curves() is True
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

    def test_widget_reads_from_app_state(self, qapp):
        """Test: ApplicationState → Widget display_mode property."""
        widget = CurveViewWidget()
        app_state = get_application_state()

        # Change ApplicationState
        app_state.set_show_all_curves(True)

        # Widget reflects ApplicationState
        assert widget.display_mode == DisplayMode.ALL_VISIBLE

        # Change to selection mode
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1"})

        # Widget reflects new mode
        assert widget.display_mode == DisplayMode.SELECTED

    def test_no_synchronization_loop(self, qapp):
        """
        Regression test: Selecting curves should NOT create sync loop.

        Original bug: on_tracking_points_selected() called set_selected_points()
        which triggered _on_selection_changed() during clearing phase = race condition.
        """
        window = MainWindow()
        panel = window.tracking_panel
        app_state = get_application_state()

        # Load data
        panel.set_tracked_data({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })

        # Track selection changed calls
        selection_changed_count = 0
        original_handler = panel._on_selection_changed

        def track_selection_changed():
            nonlocal selection_changed_count
            selection_changed_count += 1
            original_handler()

        panel._on_selection_changed = track_selection_changed

        # Simulate Ctrl+click (multi-select)
        panel.set_selected_points(["Track1", "Track2"])

        # Should only fire once (not multiple times from sync loop)
        assert selection_changed_count == 1
        assert app_state.get_selected_curves() == {"Track1", "Track2"}

    def test_regression_multi_curve_display_bug(self, qapp):
        """
        Regression test for: Selecting two curves only shows one.

        Original bug: selected_curve_names updated but display_mode not set to SELECTED.
        With new architecture, display_mode always correct (computed property).
        """
        window = MainWindow()
        app_state = get_application_state()

        # Simulate the exact user action that caused the bug
        window.tracking_panel.set_tracked_data({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })
        window.tracking_panel.set_selected_points(["Track1", "Track2"])

        # This should NOT fail (original bug: only one curve rendered)
        from rendering.render_state import RenderState
        render_state = RenderState.compute(window.curve_widget)
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert len(render_state.visible_curves) == 2

    # NEW TESTS: Edge cases from reviews

    def test_batch_mode_state_visibility(self, qapp):
        """
        Test: display_mode reflects changes immediately during batch.

        Batch mode defers signal emissions, NOT state visibility.
        """
        app_state = get_application_state()

        app_state.begin_batch()
        try:
            # Set selection
            app_state.set_selected_curves({"Track1"})
            # display_mode should update immediately, even in batch
            assert app_state.display_mode == DisplayMode.SELECTED

            # Change to show all
            app_state.set_show_all_curves(True)
            # Mode should change immediately
            assert app_state.display_mode == DisplayMode.ALL_VISIBLE
        finally:
            app_state.end_batch()

        # Signals emitted now, but state was visible throughout

    def test_batch_mode_conflicting_changes(self, qapp):
        """Test precedence when both show_all and selection change in batch."""
        app_state = get_application_state()

        app_state.begin_batch()
        try:
            app_state.set_selected_curves({"Track1"})  # Would give SELECTED
            app_state.set_show_all_curves(True)         # Would give ALL_VISIBLE
        finally:
            app_state.end_batch()

        # Last write wins: show_all takes priority
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

    def test_qt_signal_timing_no_circular_updates(self, qapp, qtbot):
        """
        Test: _updating flag timing doesn't cause circular updates.

        The QTimer fix ensures flag release happens after queued signals.
        """
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # Track how many times _on_selection_changed fires
        call_count = 0
        original = panel._on_selection_changed

        def tracked_handler():
            nonlocal call_count
            call_count += 1
            original()

        panel._on_selection_changed = tracked_handler

        # External update to ApplicationState (triggers reverse sync)
        app_state.set_selected_curves({"Track1"})

        # Wait for Qt signals to process
        qtbot.wait(100)

        # Should only fire once (from reverse sync), not loop
        assert call_count <= 1, f"Expected ≤1 call, got {call_count}"

    def test_invalid_curve_names_warns_but_works(self, qapp):
        """
        Test: Selecting non-existent curves warns but doesn't crash.

        Allows setting selection before curves load (session restoration).
        """
        app_state = get_application_state()

        # Set selection before loading curves (session restoration scenario)
        app_state.set_selected_curves({"Track1", "Track2"})
        # Should work, no crash
        assert app_state.get_selected_curves() == {"Track1", "Track2"}

        # Load curves
        app_state.set_curve_data("Track1", [CurvePoint(1, 10, 20)])

        # Select mixture of valid and invalid
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            app_state.set_selected_curves({"Track1", "FakeCurve"})

            # Should warn about invalid curve
            assert len(w) == 1
            assert "not yet loaded" in str(w[0].message)

        # Selection kept (permissive validation)
        assert app_state.get_selected_curves() == {"Track1", "FakeCurve"}

    def test_empty_selection_transitions(self, qapp):
        """Test all display mode transitions with empty selections."""
        app_state = get_application_state()

        # Start: ACTIVE_ONLY (no selection, no show_all)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

        # Select curves → SELECTED
        app_state.set_selected_curves({"Track1"})
        assert app_state.display_mode == DisplayMode.SELECTED

        # Clear selection → back to ACTIVE_ONLY
        app_state.set_selected_curves(set())
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

        # Enable show_all → ALL_VISIBLE
        app_state.set_show_all_curves(True)
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

        # Disable show_all with no selection → ACTIVE_ONLY
        app_state.set_show_all_curves(False)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

    def test_redundant_updates_filtered(self, qapp):
        """Test: Setting same value twice doesn't emit duplicate signals."""
        app_state = get_application_state()

        signal_count = 0

        def count_signals(selected: set[str], show_all: bool):
            nonlocal signal_count
            signal_count += 1

        app_state.selection_state_changed.connect(count_signals)

        # First update
        app_state.set_selected_curves({"Track1"})
        assert signal_count == 1

        # Same value again - should NOT emit signal
        app_state.set_selected_curves({"Track1"})
        assert signal_count == 1  # Still 1, not 2

    def test_set_display_mode_edge_case_no_active_curve(self, qapp):
        """
        Test: set_display_mode(SELECTED) when no active curve.

        Should log warning and remain in ACTIVE_ONLY mode.
        """
        window = MainWindow()
        controller = window.multi_point_controller
        app_state = get_application_state()

        # Ensure no active curve
        window.curve_widget.active_curve_name = None

        # Try to set SELECTED mode
        with pytest.warns(UserWarning, match="Cannot set SELECTED mode"):
            controller.set_display_mode(DisplayMode.SELECTED)

        # Mode should remain ACTIVE_ONLY
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY
```

### Step 6.5: Update All Other Test Files

**Search command to find all test files needing updates**:
```bash
grep -r "\.display_mode\s*=" tests/ --include="*.py" > /tmp/test_display_mode_usages.txt
grep -r "\.selected_curve_names" tests/ --include="*.py" > /tmp/test_selected_curve_names_usages.txt
```

**Update pattern for each file**:
1. Add import: `from stores.application_state import get_application_state, reset_application_state`
2. Add `reset_application_state()` in test setup
3. Replace `widget.display_mode = X` with appropriate `app_state.set_*()` calls
4. Add assertions to verify computed mode is correct

### Verification Steps

1. **Run all tests**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```
   Expected: All tests pass

2. **Run new integration test suite**:
   ```bash
   .venv/bin/python3 -m pytest tests/test_selection_state_integration.py -v
   ```
   Expected: All new edge case tests pass

3. **Check for deprecation warnings**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -W default::DeprecationWarning 2>&1 | grep -i deprecated
   ```
   Expected: Some warnings (from backward-compat code), but all tests pass

4. **Check coverage**:
   ```bash
   .venv/bin/python3 -m pytest tests/test_selection_state_integration.py \
     --cov=stores.application_state --cov-report=term-missing
   ```
   Goal: 100% coverage of new selection state methods

### Rollback Instructions

1. Revert all test files:
   ```bash
   git checkout tests/
   ```

2. Delete new integration test:
   ```bash
   rm tests/test_selection_state_integration.py
   ```

---

## Phase 7: Documentation and Session Persistence

---

**Next**: [Phases 7-8: Documentation & Cleanup](03_PHASES_7_TO_8_AND_COMPLETION.md)
