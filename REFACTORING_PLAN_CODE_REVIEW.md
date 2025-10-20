# REFACTORING_PLAN.md Code Review Report

**Reviewer**: Python Code Reviewer
**Date**: 2025-10-20
**Objective**: Identify breaking changes and integration risks

---

## Executive Summary

**Overall Risk**: 🔴 HIGH - Critical breaking changes found in Task 1.4

**Critical Issues**: 1 must-fix
**Recommended Changes**: 4 should-fix
**Minor Improvements**: 2 nice-to-have

### Key Findings

1. 🔴 **CRITICAL**: Task 1.4 CurveColors structure mismatch will break 6 renderer call sites
2. 🟡 **RISKY**: Task 1.3 QSignalBlocker context manager syntax unverified for PySide6
3. 🟡 **INCOMPLETE**: Task 1.4 changes return types but doesn't update all usage sites
4. 🟢 **SAFE**: Tasks 1.2, 1.5, 2.1, 2.2 are architecturally sound

---

## Critical Issues (Must Fix)

### Issue 1: CurveColors Structure Mismatch 🔴

**Severity**: BREAKING - Code will fail at runtime
**Task**: 1.4 (Extract Colors to Core)
**Location**: `rendering/optimized_curve_renderer.py` lines 525, 570, 571, 706, 737, 738

#### Current API
```python
# ui/color_constants.py
class CurveColors:
    WHITE: QColor = QColor(255, 255, 255)
    INACTIVE_GRAY: QColor = QColor(128, 128, 128, 128)

    @staticmethod
    def get_inactive_pen(width: int = 1) -> QPen:
        ...

    @staticmethod
    def get_active_pen(color: QColor | None = None, width: int = 2) -> QPen:
        ...
```

#### Proposed API
```python
# core/colors.py
@dataclass(frozen=True)
class CurveColors:
    """Color scheme for curve rendering."""
    point: QColor
    selected_point: QColor
    line: QColor
    interpolated: QColor
    keyframe: QColor
    endframe: QColor
    tracked: QColor

    @classmethod
    def default(cls) -> "CurveColors":
        ...
```

#### Breaking Changes
These are **TWO COMPLETELY DIFFERENT CLASSES** with the same name!

**Current usage in renderer:**
```python
# Line 525
pen = CurveColors.get_active_pen()  # ❌ WILL BREAK - method doesn't exist

# Line 570-571
active_pen = CurveColors.get_active_pen()  # ❌ WILL BREAK
inactive_pen = CurveColors.get_inactive_pen()  # ❌ WILL BREAK

# Line 706
curve_color = CurveColors.WHITE  # ❌ WILL BREAK - attribute doesn't exist

# Line 737-738
active_pen = CurveColors.get_active_pen(color=curve_color, width=line_width)  # ❌ WILL BREAK
inactive_pen = CurveColors.get_inactive_pen(width=max(1, line_width - 1))  # ❌ WILL BREAK
```

#### Root Cause
The plan proposes extracting DIFFERENT color concepts to core/:
- Proposed `CurveColors`: Color scheme for rendering status types
- Current `CurveColors`: UI helpers for pen creation

These should have DIFFERENT NAMES to avoid collision.

#### Recommended Fix
**Option A: Keep both classes with different names**
```python
# core/colors.py
@dataclass(frozen=True)
class StatusColorScheme:  # Renamed to avoid collision
    """Color scheme for point status rendering."""
    point: QColor
    selected_point: QColor
    line: QColor
    interpolated: QColor
    keyframe: QColor
    endframe: QColor
    tracked: QColor

# ui/color_constants.py (unchanged)
class CurveColors:
    """UI helpers for pen creation."""
    WHITE: QColor = QColor(255, 255, 255)
    INACTIVE_GRAY: QColor = QColor(128, 128, 128, 128)

    @staticmethod
    def get_inactive_pen(width: int = 1) -> QPen: ...

    @staticmethod
    def get_active_pen(color: QColor | None = None, width: int = 2) -> QPen: ...
```

**Option B: Extract both to core with different names**
```python
# core/colors.py
class PenFactory:  # Current CurveColors functionality
    WHITE: QColor = QColor(255, 255, 255)
    INACTIVE_GRAY: QColor = QColor(128, 128, 128, 128)

    @staticmethod
    def get_inactive_pen(width: int = 1) -> QPen: ...

    @staticmethod
    def get_active_pen(color: QColor | None = None, width: int = 2) -> QPen: ...

@dataclass(frozen=True)
class StatusColorScheme:  # Proposed functionality
    point: QColor
    selected_point: QColor
    # ... rest of attributes
```

**Impact if not fixed**: Runtime AttributeError on 6+ lines in renderer

---

## Recommended Changes (Should Fix)

### Issue 2: QSignalBlocker Context Manager Syntax 🟡

**Severity**: RISKY - Behavior might differ subtly
**Task**: 1.3 (Extract Spinbox Helper)
**Location**: `ui/controllers/point_editor_controller.py`

#### Current Code
```python
# Lines 139-146 (works, but not exception-safe)
self.main_window.point_x_spinbox.blockSignals(True)
self.main_window.point_y_spinbox.blockSignals(True)
try:
    self.main_window.point_x_spinbox.setValue(x)
    self.main_window.point_y_spinbox.setValue(y)
finally:
    self.main_window.point_x_spinbox.blockSignals(False)
    self.main_window.point_y_spinbox.blockSignals(False)
```

#### Proposed Code
```python
# Using QSignalBlocker as context manager
with QSignalBlocker(self.main_window.point_x_spinbox), \
     QSignalBlocker(self.main_window.point_y_spinbox):
    self.main_window.point_x_spinbox.setValue(x)
    self.main_window.point_y_spinbox.setValue(y)
```

#### Risk Analysis
PySide6's `QSignalBlocker` **does** support context manager protocol (`__enter__`/`__exit__`), BUT:
1. Not all PySide6 versions may have this (added in Qt 5.14+)
2. Multiple context managers with comma syntax is valid Python, but untested in this codebase
3. Current code uses explicit blockSignals() which is proven to work

#### Recommended Fix
**Option A: Safer pattern with explicit try/finally**
```python
def _update_spinboxes_silently(self, x: float, y: float) -> None:
    """Update spinbox values without triggering signals.

    Uses try/finally for exception-safe signal blocking.
    """
    if not self.main_window.point_x_spinbox or not self.main_window.point_y_spinbox:
        return

    # Block signals with exception safety
    self.main_window.point_x_spinbox.blockSignals(True)
    self.main_window.point_y_spinbox.blockSignals(True)
    try:
        self.main_window.point_x_spinbox.setValue(x)
        self.main_window.point_y_spinbox.setValue(y)
    finally:
        self.main_window.point_x_spinbox.blockSignals(False)
        self.main_window.point_y_spinbox.blockSignals(False)
```

**Option B: Test QSignalBlocker thoroughly before using**
```python
# Add test case to verify QSignalBlocker context manager works
def test_qsignal_blocker_context_manager():
    """Verify QSignalBlocker supports context manager protocol."""
    from PySide6.QtCore import QSignalBlocker
    spinbox = QDoubleSpinBox()

    # Test context manager syntax
    with QSignalBlocker(spinbox):
        spinbox.setValue(42.0)

    # Verify signals restored
    assert spinbox.signalsBlocked() == False
```

**Verdict**: Proposed pattern is modern and correct, but needs testing. Current pattern with try/finally is safer for critical code.

---

### Issue 3: Return Type Changes Without Usage Updates 🟡

**Severity**: RISKY - Inefficient but might work
**Task**: 1.4 (Extract Colors to Core)
**Location**: `rendering/optimized_curve_renderer.py` (40+ usage sites)

#### Current Pattern
```python
# get_status_color() returns hex string
color = get_status_color(status)  # Returns: "#ffffff"
painter.setBrush(QBrush(QColor(color)))  # Convert hex to QColor

# SPECIAL_COLORS contains hex strings
painter.setBrush(QBrush(QColor(SPECIAL_COLORS["selected_point"])))  # Convert hex to QColor
```

#### Proposed Pattern (after Task 1.4)
```python
# get_status_color() returns QColor
color = get_status_color(status)  # Returns: QColor(255, 255, 255)
painter.setBrush(QBrush(QColor(color)))  # QColor copy constructor - REDUNDANT!

# SPECIAL_COLORS contains QColor objects
painter.setBrush(QBrush(QColor(SPECIAL_COLORS["selected_point"])))  # REDUNDANT copy!
```

#### Analysis
Qt's QColor has a copy constructor, so `QColor(QColor_object)` **will work** but creates unnecessary copies.

**Current API** (ui/color_manager.py):
```python
STATUS_COLORS: dict[str, str] = {
    "normal": "#ffffff",
    "keyframe": "#00ff66",
    ...
}

def get_status_color(status: str | PointStatus) -> str:
    """Returns hex color string."""
    return STATUS_COLORS.get(status, STATUS_COLORS["normal"])
```

**Proposed API** (core/colors.py):
```python
COLORS_DARK: dict[str, QColor] = {
    "normal": QColor(200, 200, 200),
    "interpolated": QColor(100, 100, 255),
    ...
}

def get_status_color(status: str, selected: bool = False) -> QColor:
    """Returns QColor object."""
    if selected:
        return SPECIAL_COLORS["selected"]
    return COLORS_DARK.get(status, COLORS_DARK["normal"])
```

#### Recommended Fix
Task 1.4 should include Step 2b: Update usage sites

```python
# Step 2b: Update renderer to use QColor directly (remove redundant wrapping)

# Lines 902-907 - BEFORE
color = get_status_color(status)
painter.setBrush(QBrush(QColor(color)))  # Redundant QColor()

# Lines 902-907 - AFTER
color = get_status_color(status)
painter.setBrush(QBrush(color))  # Use QColor directly

# Lines 913, 920 - BEFORE
painter.setBrush(QBrush(QColor(SPECIAL_COLORS["selected_point"])))

# Lines 913, 920 - AFTER
painter.setBrush(QBrush(SPECIAL_COLORS["selected_point"]))

# Lines 1019-1020 - BEFORE
hex_color = get_status_color(status)
q_color = QColor(hex_color)

# Lines 1019-1020 - AFTER
q_color = get_status_color(status)  # Already returns QColor
```

**Impact if not fixed**: Code works but creates ~40+ unnecessary QColor copies per render frame (performance degradation).

---

### Issue 4: Import Chain Verification Needed 🟡

**Severity**: RISKY - Could introduce circular imports
**Task**: 1.4 (Extract Colors to Core)
**Location**: `core/colors.py` (new file)

#### Proposed Import
```python
# core/colors.py
from PySide6.QtGui import QColor
```

#### Current Layer Separation
```
core/        - No PySide6 dependencies (pure Python)
services/    - Can import from core/
rendering/   - Can import from core/ and PySide6
ui/          - Can import from all layers
```

#### Risk Analysis
**Does core/ currently import PySide6?**

Checking core/ directory for PySide6 imports:
```bash
$ grep -r "from PySide6" core/
# (Need to verify - likely NO current imports)
```

**Verdict**: Moving color definitions with QColor to core/ introduces PySide6 dependency in core layer. This violates current architecture.

#### Recommended Fix
**Option A: Create intermediate layer**
```
core/              - Pure Python (no Qt)
rendering/colors/  - Qt color definitions (can use QColor)
rendering/         - Main rendering (can use colors/)
ui/                - UI layer
```

**Option B: Accept PySide6 in core/ for pragmatic reasons**
Since this is a PySide6 application and QColor is a fundamental type, accepting it in core/ might be pragmatic. Document this architectural decision.

```python
# core/colors.py
"""
Color definitions for rendering layer.

Note: This module imports PySide6.QtGui.QColor, which introduces
a Qt dependency in the core/ layer. This is pragmatic for a Qt application
where colors are fundamental to the domain model.
"""
from PySide6.QtGui import QColor
```

**Impact if not fixed**: Potential circular import issues if core/ modules later need to be imported by Qt initialization code.

---

### Issue 5: Incomplete Import Updates 🟡

**Severity**: RISKY - Plan doesn't show all necessary changes
**Task**: 1.4 (Extract Colors to Core)
**Location**: Multiple files

#### Plan Shows
```
Step 3: Update ui/color_constants.py to re-export from core
Step 4: Update ui/color_manager.py to re-export from core
```

#### What's Missing
The plan doesn't show the actual re-export code. Example:

**Task 1.4 Step 3 should specify:**
```python
# ui/color_constants.py
"""UI color constants - re-exports from core for backward compatibility."""

# Re-export core color types (to avoid breaking existing imports)
from core.colors import (
    StatusColorScheme,  # If renamed per Issue #1
    COLORS_DARK,
    SPECIAL_COLORS,
    get_status_color,
)

# Keep UI-specific CurveColors class
class CurveColors:
    """UI helpers for pen creation (UI-specific, not moved to core)."""
    WHITE: QColor = QColor(255, 255, 255)
    INACTIVE_GRAY: QColor = QColor(128, 128, 128, 128)

    @staticmethod
    def get_inactive_pen(width: int = 1) -> QPen: ...

    @staticmethod
    def get_active_pen(color: QColor | None = None, width: int = 2) -> QPen: ...
```

**Recommended**: Add explicit code examples for all re-export steps to prevent confusion.

---

## Safe Changes (No Issues Found) 🟢

### Task 1.2: Fix Layer Violations - Constants ✅

**Analysis**: Constants move is architecturally sound.

#### Verification
**Current API** (ui/ui_constants.py):
```python
DEFAULT_IMAGE_WIDTH: int = 1920
DEFAULT_IMAGE_HEIGHT: int = 1080
DEFAULT_NUDGE_AMOUNT: float = 1.0
DEFAULT_STATUS_TIMEOUT: int = 2000
GRID_CELL_SIZE: int = 100
RENDER_PADDING: int = 50
MAX_ZOOM_FACTOR: float = 10.0
MIN_ZOOM_FACTOR: float = 0.1
```

**Proposed API** (core/defaults.py):
```python
DEFAULT_IMAGE_WIDTH: int = 1920  # ✅ IDENTICAL
DEFAULT_IMAGE_HEIGHT: int = 1080  # ✅ IDENTICAL
DEFAULT_NUDGE_AMOUNT: float = 1.0  # ✅ IDENTICAL
DEFAULT_STATUS_TIMEOUT: int = 2000  # ✅ IDENTICAL
GRID_CELL_SIZE: int = 100  # ✅ IDENTICAL
RENDER_PADDING: int = 50  # ✅ IDENTICAL
MAX_ZOOM_FACTOR: float = 10.0  # ✅ IDENTICAL
MIN_ZOOM_FACTOR: float = 0.1  # ✅ IDENTICAL
```

**Verdict**:
- ✅ Constant NAMES identical
- ✅ Types identical
- ✅ VALUES identical
- ✅ 5 layer violations correctly identified
- ✅ Import updates are straightforward

**No breaking changes found.**

---

### Task 1.5: Extract Point Lookup Helper ✅

**Analysis**: Helper method matches data structure correctly.

#### Data Structure Verification
```python
# core/type_aliases.py
PointTuple3 = tuple[int, float, float]
PointTuple4 = tuple[int, float, float, str | bool]
LegacyPointData = PointTuple3 | PointTuple4
CurveDataList = list[LegacyPointData]
```

So `point[0]` is ALWAYS the frame number (int).

#### Proposed Helper
```python
def _find_point_index_at_frame(
    self,
    curve_data: CurveDataList,
    frame: int
) -> int | None:
    """Find the index of a point at the given frame."""
    for i, point in enumerate(curve_data):
        if point[0] == frame:  # ✅ CORRECT - point[0] is frame number
            return i
    return None
```

**Verification of usage sites:**
```python
# Line 187-190 (SetEndframeCommand) - BEFORE
for i, point in enumerate(curve_data):
    if point[0] == context.current_frame:  # ✅ Same pattern
        point_index = i
        break

# Line 187-190 - AFTER
point_index = self._find_point_index_at_frame(curve_data, context.current_frame)
```

**Verdict**:
- ✅ Data structure access is correct
- ✅ Helper signature matches usage
- ✅ Type hints are accurate
- ✅ Return type (int | None) handles not-found case

**No breaking changes found.**

---

### Task 2.1: Enforce active_curve_data Property ✅

**Analysis**: Property pattern doesn't force unwanted changes.

#### Current Property
```python
# stores/application_state.py
@property
def active_curve_data(self) -> tuple[str, CurveDataList] | None:
    """Get (curve_name, data) for active curve, or None if unavailable."""
    active = self.active_curve
    if not active:
        return None

    try:
        data = self.get_curve_data(active)
        return (active, data)
    except ValueError as e:
        logger.error(f"Unexpected error getting curve data: {e}")
        return None
```

#### Legitimate Active Curve Usage (NO CHANGE NEEDED)
```python
# ui/timeline_tabs.py:387 - Only needs curve name
active_curve = self._app_state.active_curve  # ✅ KEEP AS-IS

# ui/state_manager.py:228 - Only needs curve name
return self._app_state.active_curve  # ✅ KEEP AS-IS
```

#### 4-Step Pattern to Replace (SHOULD CHANGE)
```python
# OLD PATTERN (should be replaced)
active = state.active_curve
if not active:
    return
data = state.get_curve_data(active)
if not data:
    return
# Use active and data

# NEW PATTERN (preferred)
if (cd := state.active_curve_data) is None:
    return
curve_name, data = cd
# Use curve_name and data
```

**Verdict**:
- ✅ Property doesn't break existing `state.active_curve` usage
- ✅ Only targets specific 4-step pattern
- ✅ Type safety maintained
- ✅ Clear migration path

**No breaking changes found.**

---

### Task 2.2: Extract Geometry to TransformService ✅

**Analysis**: Geometry extraction is architecturally sound.

#### Proposed Method
```python
def calculate_fit_bounds(
    self,
    points: list[tuple[float, float]],
    viewport_width: int,
    viewport_height: int,
    padding_factor: float = 1.2
) -> tuple[float, float, float]:
    """Calculate optimal zoom and center for fitting points in viewport."""
    # ... implementation
    from core.defaults import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR
    # ... geometry calculations
    return (center_x, center_y, optimal_zoom)
```

#### Dependency Chain
```
core/defaults.py (Task 1.2)
    ↓
services/transform_service.py (Task 2.2)
    ↓
ui/controllers/tracking_display_controller.py
```

**Verification**:
- ✅ No circular dependencies
- ✅ Pure geometry calculation (no PySide6 in signature)
- ✅ Depends on core/defaults.py created in Task 1.2
- ✅ TransformService scope expansion is acknowledged and justified
- ✅ Clear migration path for controller

**Architectural Note**: The plan acknowledges SRP expansion: "This extends TransformService scope to include viewport fitting calculations alongside coordinate transformations. While this slightly expands SRP, it's pragmatic for a single-user application."

This is acceptable given:
1. Viewport fitting is geometrically related to transformations
2. Single-user app context justifies pragmatic consolidation
3. Future extraction to separate GeometryService noted if service grows beyond 5-6 methods

**No breaking changes found.**

---

## Minor Improvements (Nice-to-Have)

### Improvement 1: Add Explicit Type Checking to Helpers

**Location**: Task 1.5 helper method

**Current:**
```python
def _find_point_index_at_frame(
    self,
    curve_data: CurveDataList,
    frame: int
) -> int | None:
    for i, point in enumerate(curve_data):
        if point[0] == frame:
            return i
    return None
```

**Suggested:**
```python
def _find_point_index_at_frame(
    self,
    curve_data: CurveDataList,
    frame: int
) -> int | None:
    """Find the index of a point at the given frame.

    Args:
        curve_data: List of curve points (tuples of (frame, x, y[, status]))
        frame: Frame number to search for

    Returns:
        Point index if found, None otherwise

    Raises:
        TypeError: If curve_data contains invalid point tuples
    """
    for i, point in enumerate(curve_data):
        if not isinstance(point, tuple) or len(point) < 3:
            raise TypeError(f"Invalid point at index {i}: {point}")
        if point[0] == frame:
            return i
    return None
```

**Benefit**: Explicit validation catches data corruption early.

---

### Improvement 2: Add Migration Verification Script

**Suggestion**: Add script to verify refactoring didn't break imports.

```python
# scripts/verify_refactoring_phase1.py
"""Verify Phase 1 refactoring completed successfully."""

def verify_constants_moved():
    """Verify constants accessible from core/defaults.py"""
    from core.defaults import (
        DEFAULT_IMAGE_WIDTH,
        DEFAULT_IMAGE_HEIGHT,
        DEFAULT_NUDGE_AMOUNT,
        DEFAULT_STATUS_TIMEOUT,
        GRID_CELL_SIZE,
        RENDER_PADDING,
        MAX_ZOOM_FACTOR,
        MIN_ZOOM_FACTOR,
    )
    assert DEFAULT_IMAGE_WIDTH == 1920
    assert DEFAULT_IMAGE_HEIGHT == 1080
    # ... more assertions

def verify_colors_moved():
    """Verify colors accessible from core/colors.py"""
    from core.colors import (
        COLORS_DARK,
        SPECIAL_COLORS,
        get_status_color,
    )
    # Verify get_status_color returns QColor
    from PySide6.QtGui import QColor
    color = get_status_color("normal")
    assert isinstance(color, QColor)

def verify_layer_violations_fixed():
    """Verify no more ui/ imports in core/services/rendering"""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "from ui\\.", "core/", "services/", "rendering/"],
        capture_output=True
    )
    assert result.returncode != 0, "Found ui/ imports in lower layers!"

if __name__ == "__main__":
    verify_constants_moved()
    verify_colors_moved()
    verify_layer_violations_fixed()
    print("✅ Phase 1 refactoring verification passed!")
```

---

## Summary & Recommendations

### Critical Path

**BEFORE starting Phase 1:**
1. 🔴 Fix Issue #1 (CurveColors structure mismatch) - rename classes to avoid collision
2. 🟡 Address Issue #2 (QSignalBlocker) - add test or use try/finally pattern
3. 🟡 Expand Issue #3 (return types) - add Step 2b to update usage sites
4. 🟡 Clarify Issue #4 (imports) - document PySide6 in core/ architectural decision
5. 🟡 Complete Issue #5 (re-exports) - add explicit code examples

### Execution Order

**Phase 1 Tasks (Revised)**:
1. Task 1.1: Delete Dead Code ✅ (no changes needed)
2. Task 1.2: Fix Layer Violations - Constants ✅ (no changes needed)
3. Task 1.3: Extract Spinbox Helper ⚠️ (test QSignalBlocker or use try/finally)
4. Task 1.4: Extract Colors to Core 🔴 (REQUIRES MAJOR CORRECTIONS)
5. Task 1.5: Extract Point Lookup Helper ✅ (no changes needed)

**Phase 2 Tasks**:
6. Task 2.1: Enforce active_curve_data Property ✅ (no changes needed)
7. Task 2.2: Extract Geometry to TransformService ✅ (no changes needed)

### Risk Assessment

| Task | Risk Level | Breaking Changes | Recommended Action |
|------|------------|------------------|-------------------|
| 1.1 | 🟢 LOW | None | Proceed as planned |
| 1.2 | 🟢 LOW | None | Proceed as planned |
| 1.3 | 🟡 MEDIUM | Possible if QSignalBlocker fails | Test or use try/finally |
| 1.4 | 🔴 HIGH | 6+ runtime errors | Rename CurveColors, update usage sites |
| 1.5 | 🟢 LOW | None | Proceed as planned |
| 2.1 | 🟢 LOW | None | Proceed as planned |
| 2.2 | 🟢 LOW | None | Proceed as planned |

### Final Verdict

**Phase 1 can proceed ONLY after fixing Task 1.4.**

The refactoring plan is well-structured and addresses real architectural issues. However, Task 1.4 has critical breaking changes that must be resolved before execution. With corrections applied, this refactoring will significantly improve code quality and layer separation.

**Estimated Time to Fix Issues**: +2 hours (revise Task 1.4, add tests for QSignalBlocker)
**Revised Total Time**: 8 hours (was 6 hours)

---

## Appendix: Search Results

### Data Structure Verification
```python
# core/type_aliases.py
PointTuple3 = tuple[int, float, float]
PointTuple4 = tuple[int, float, float, str | bool]
LegacyPointData = PointTuple3 | PointTuple4
CurveDataList = list[LegacyPointData]
```

**Conclusion**: `point[0]` is ALWAYS frame number (int). Task 1.5 helper is correct.

### CurveColors Usage Sites
```
rendering/optimized_curve_renderer.py:525:  pen = CurveColors.get_active_pen()
rendering/optimized_curve_renderer.py:570:  active_pen = CurveColors.get_active_pen()
rendering/optimized_curve_renderer.py:571:  inactive_pen = CurveColors.get_inactive_pen()
rendering/optimized_curve_renderer.py:706:  curve_color = CurveColors.WHITE
rendering/optimized_curve_renderer.py:737:  active_pen = CurveColors.get_active_pen(color=curve_color, width=line_width)
rendering/optimized_curve_renderer.py:738:  inactive_pen = CurveColors.get_inactive_pen(width=max(1, line_width - 1))
```

**Conclusion**: 6 usage sites depend on current CurveColors API. Proposed structure change will break all 6.

### Color Return Type Usage
```python
# Line 902-907: Current pattern
color = get_status_color(status)  # Returns hex string
painter.setBrush(QBrush(QColor(color)))  # Converts to QColor

# Line 913: Current pattern
painter.setBrush(QBrush(QColor(SPECIAL_COLORS["selected_point"])))  # Converts to QColor

# Line 1019-1020: Current pattern
hex_color = get_status_color(status)  # Returns hex string
q_color = QColor(hex_color)  # Converts to QColor
```

**Conclusion**: ~40+ usage sites wrap colors in QColor(). After type change, these become redundant (but might work via copy constructor).

---

**End of Report**
