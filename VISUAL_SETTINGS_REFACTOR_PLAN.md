# Visual Settings Refactor Plan

**Issue ID:** DRY-2024-001
**Created:** 2025-10-26
**Status:** Planning
**Priority:** Medium (Bug Fix + Technical Debt Reduction)

---

## Executive Summary

**Problem:** Visual rendering parameters (16 configurable) are scattered across Widget and RenderState (only 4/16 present in RenderState as configurable settings), with architectural incompleteness causing maintenance hazards when adding new visual controls.

**Root Cause:** No single source of truth for rendering parameters. Adding a slider requires manual coordination across Widget → RenderState → Renderer with no type-system enforcement, making it easy to forget steps.

**Current Bug Status:**
- ✅ **Working:** `point_radius` and `line_width` renderer uses RenderState values (committed code uses `render_state.line_width + 1` pattern)
- ❌ **Broken:** `selected_point_radius` exists in widget but NOT wired through RenderState (renderer uses hardcoded +2 offset)
- 📊 **Missing:** 12/16 configurable parameters not in RenderState (grid colors, selected variants, display toggles, etc.)
- ⚠️ **Clarification:** Plan examples show old hardcoded pattern for illustration; actual code already uses render_state

**Impact:**
- **User-facing:** Minor cosmetic bug (selected points always +2px, not independently configurable)
- **Developer-facing:** Architectural incompleteness creates maintenance hazard for adding visual controls
- **Priority:** Moderate (code quality improvement + minor bug fix, not critical functionality)

**Solution:** Introduce `VisualSettings` dataclass as single source of truth, consolidating 16 configurable visual parameters with type-safe extraction and comprehensive validation.

**Implementation Complexity:** 5 phases + critical test migration phase (25 construction sites require backward-compatible `create_for_tests()` wrapper)

---

## Problem Statement

### Bug Discovery Timeline

1. User asked if point size slider still exists (it was created but never added to UI)
2. We added visualization panel with point_size and line_width sliders
3. User reported: "Neither slider seems to be doing anything at all"
4. Root cause: Renderer used hardcoded values, ignoring widget properties

### Current Architecture Issues

**Three-way duplication** when adding a rendering parameter:

```python
# 1. CurveViewWidget property (ui/curve_view_widget.py:245)
self.point_radius: int = 5
self.line_width: int = 2

# 2. RenderState field (rendering/render_state.py:65)
point_radius: int = 3  # ⚠️ Different default!
line_width: int = 2

# 3. RenderState.compute() extraction (rendering/render_state.py:213)
point_radius=widget.point_radius,
line_width=widget.line_width,

# 4. Renderer usage (rendering/optimized_curve_renderer.py:1151)
line_width = 3 if is_active else 2  # ❌ IGNORED RenderState!
point_radius = 7 if is_active else 5  # ❌ IGNORED RenderState!
```

**Bug Pattern:** Easy to forget step 2, 3, or 4 → silent failure (sliders don't work)

### Current Visual Parameters Inventory

**In CurveViewWidget (16 configurable parameters - VERIFIED):**
- Display toggles (7): `show_grid`, `show_points`, `show_lines`, `show_labels`, `show_velocity_vectors`, `show_all_frame_numbers`, `show_background`
- Grid (3): `grid_size`, `grid_color`, `grid_line_width`
- Points (2): `point_radius`, `selected_point_radius`
- Lines (4): `line_width`, `line_color`, `selected_line_width`, `selected_line_color`

**CRITICAL NOTE:** All 16 parameters must be included in VisualSettings (see Fix #1 in amendments below)

**In RenderState (4 configurable parameters - VERIFIED):**
- `show_background`, `show_grid`, `point_radius`, `line_width`

**Missing from RenderState (12 parameters - VERIFIED):**
- Display toggles (5): `show_points`, `show_lines`, `show_labels`, `show_velocity_vectors`, `show_all_frame_numbers`
- Grid (3): `grid_size`, `grid_color`, `grid_line_width`
- Points/Lines (4): `selected_point_radius`, `line_color`, `selected_line_width`, `selected_line_color`

**Analysis:** Some toggles (show_points, show_lines) are widget-level filters and don't need to be in RenderState. But colors, sizes, and opacity DO need to be passed to renderer.

---

## Strategic Priorities

### 1. Correctness (P0)
**Goal:** Sliders must actually work
**Why:** User-facing bug, core functionality broken

### 2. Maintainability (P0)
**Goal:** Prevent future bugs when adding visual controls
**Why:** Reduces cognitive load, eliminates manual coordination

### 3. Type Safety (P1)
**Goal:** Compiler enforces parameter extraction
**Why:** Can't forget to add field to RenderState

### 4. Testability (P1)
**Goal:** Easy to create test RenderState with custom visuals
**Why:** Enables property-based testing of rendering

### 5. Performance (P2)
**Goal:** No performance regression
**Why:** Rendering is hot path (47x optimized)

---

## Dependencies

### Prerequisites
- [x] Bug fix applied (renderer uses render_state values) - **COMPLETED**
- [ ] Test suite passes (verify no regressions from bug fix)
- [ ] Understand which parameters are renderer-facing vs widget-only

### Blocking Issues
- None (can proceed immediately)

### Nice-to-Have (Not Blocking)
- Session state persistence for visual settings
- Visual settings presets (themes)

---

## Proposed Solution: VisualSettings Dataclass

### Architecture

**Single Source of Truth:**

```python
# rendering/visual_settings.py (NEW FILE)
from dataclasses import dataclass, field
from PySide6.QtGui import QColor

@dataclass  # Mutable - controllers modify fields directly
class VisualSettings:
    """All configurable visual rendering parameters.

    This is the single source of truth for rendering appearance.
    Sliders/checkboxes update these values, renderer reads them.

    Design Principles:
    - Mutable for controller updates (NOT frozen)
    - Created per-widget instance (not shared across widgets)
    - Sensible defaults (match current widget behavior)
    - Type-safe (compiler catches missing parameters)
    - Comprehensive validation (all numeric fields checked)

    Usage Pattern:
        # In CurveViewWidget.__init__:
        self.visual = VisualSettings()  # Per-widget instance

        # Controllers modify directly:
        widget.visual.point_radius = 10  # Mutable field assignment

    Note on Defaults:
        point_radius=5 matches CurveViewWidget default and fixes latent bug
        where RenderState had incorrect default of 3 (never used in practice).
    """

    # Point rendering
    point_radius: int = 5
    selected_point_radius: int = 7

    # Line rendering
    line_width: int = 2
    selected_line_width: int = 3
    line_color: QColor = field(default_factory=lambda: QColor(200, 200, 200))
    selected_line_color: QColor = field(default_factory=lambda: QColor(255, 255, 100))

    # Grid
    show_grid: bool = False
    grid_size: int = 50
    grid_line_width: int = 1
    grid_color: QColor = field(default_factory=lambda: QColor(100, 100, 100, 50))

    # Background
    show_background: bool = True

    # Display toggles (widget-level filters, but included for completeness)
    show_points: bool = True
    show_lines: bool = True
    show_labels: bool = False
    show_velocity_vectors: bool = False
    show_all_frame_numbers: bool = False

    def __post_init__(self) -> None:
        """Validate all visual settings.

        Comprehensive validation prevents invalid values from reaching renderer.
        All numeric parameters must be positive.
        """
        # Point radius validation
        if self.point_radius <= 0:
            raise ValueError(f"point_radius must be positive: {self.point_radius}")
        if self.selected_point_radius <= 0:
            raise ValueError(f"selected_point_radius must be positive: {self.selected_point_radius}")

        # Line width validation
        if self.line_width <= 0:
            raise ValueError(f"line_width must be positive: {self.line_width}")
        if self.selected_line_width <= 0:
            raise ValueError(f"selected_line_width must be positive: {self.selected_line_width}")

        # Grid validation
        if self.grid_size <= 0:
            raise ValueError(f"grid_size must be positive: {self.grid_size}")
        if self.grid_line_width <= 0:
            raise ValueError(f"grid_line_width must be positive: {self.grid_line_width}")

        # Note: Boolean display toggles (show_points, show_lines, etc.) don't need validation
```

### Data Flow

**Before (Broken):**
```
Slider → Widget Property → (manually extract to RenderState) → (ignored by Renderer)
```

**After (Fixed):**
```
Slider → widget.visual.point_radius → RenderState.visual → Renderer.visual.point_radius
         ↓ (automatic)                 ↓ (automatic)       ↓ (enforced)
         VisualSettings                VisualSettings      Must use visual.*
```

### Code Changes Overview

**CurveViewWidget (BEFORE):**
```python
class CurveViewWidget:
    def __init__(self):
        self.point_radius: int = 5
        self.line_width: int = 2
        self.show_grid: bool = False
        # ... 11 more visual parameters scattered
```

**CurveViewWidget (AFTER):**
```python
class CurveViewWidget:
    def __init__(self):
        # Single visual settings object
        self.visual: VisualSettings = VisualSettings()

    # Optional: Backward-compatible properties
    @property
    def point_radius(self) -> int:
        return self.visual.point_radius

    @point_radius.setter
    def point_radius(self, value: int) -> None:
        self.visual.point_radius = value
        self.update()  # Trigger repaint
```

**RenderState (BEFORE):**
```python
@dataclass
class RenderState:
    show_background: bool
    show_grid: bool = True
    point_radius: int = 3  # ⚠️ Wrong default!
    line_width: int = 2
    # ❌ Missing: selected_point_radius, grid colors, etc.
```

**RenderState (AFTER):**
```python
@dataclass(frozen=True)  # Keep frozen=True for immutability!
class RenderState:
    # Configurable visual settings in one field! ✨
    visual: VisualSettings  # Mutable nested object (allowed in frozen dataclass)

    # Core data
    points: CurveDataList
    current_frame: int
    # ... other fields

    @classmethod
    def compute(cls, widget):
        return cls(
            visual=widget.visual,  # Single line for 16 parameters!
            points=widget.points,
            # ... other fields
        )
```

**Renderer (CURRENT - base values already use RenderState):**
```python
# ✅ Base values use RenderState (committed code)
line_width = render_state.line_width + (1 if is_active else 0)
point_radius = render_state.point_radius + (2 if is_active else 0)

# ❌ Selected points use hardcoded offset (the actual bug)
selected_radius = point_radius + 2  # Ignores widget.selected_point_radius
```

**Renderer (AFTER - use VisualSettings):**
```python
# ✅ All values from VisualSettings
line_width = render_state.visual.selected_line_width if is_active else render_state.visual.line_width
point_radius = render_state.visual.selected_point_radius if is_active else render_state.visual.point_radius

# ✅ No hardcoded offsets
selected_radius = render_state.visual.selected_point_radius  # Respects slider
```

**Slider Controller (BEFORE):**
```python
def update_curve_point_size(self, value: int) -> None:
    if not self.main_window.curve_widget:
        return
    self.main_window.curve_widget.point_radius = value
    self.main_window.curve_widget.selected_point_radius = value + 2
    self.main_window.curve_widget.update()
```

**Slider Controller (AFTER):**
```python
def update_curve_point_size(self, value: int) -> None:
    if not self.main_window.curve_widget:
        return
    # Update visual settings (single source of truth)
    self.main_window.curve_widget.visual.point_radius = value
    self.main_window.curve_widget.visual.selected_point_radius = value + 2
    self.main_window.curve_widget.update()
```

---

## Phased Implementation

### Phase 0: Validation & Baseline (Day 1 - 2.5 hours)

**Goals:**
- Establish current baseline with comprehensive visual regression testing
- Verify current state (sliders work, but selected_point_radius broken)
- Document current behavior for comparison after refactor

**Tasks:**

1. **Run full test suite and record results**
   ```bash
   uv run pytest tests/ -v | tee phase0_test_results.txt
   # Expected: All pass, 3175+ tests
   ```

2. **Manual smoke test**
   - Load 2DTrackDatav2.txt
   - Verify point_radius slider changes point size (2→20 range)
   - Verify line_width slider changes line width (1→10 range)
   - **Note broken behavior:** Selected points always +2px regardless of setting

3. **Create comprehensive baseline screenshots (10 total)**

   **Point size variations (4 screenshots):**
   - point_radius=2 (minimum)
   - point_radius=6 (default)
   - point_radius=10 (mid-range)
   - point_radius=20 (maximum)

   **Line width variations (3 screenshots):**
   - line_width=1 (minimum)
   - line_width=5 (mid-range)
   - line_width=10 (maximum)

   **Combined variations (3 screenshots):**
   - Small: point=2, line=1
   - Default: point=6, line=2
   - Large: point=20, line=10

   **Screenshot naming:** `baseline_p{radius}_l{width}.png`
   **Save location:** `tests/visual_regression/baseline/`

4. **Document current visual parameter defaults**
   Create `tests/visual_regression/current_defaults.txt`:
   ```
   point_radius=5
   selected_point_radius=7
   line_width=2
   selected_line_width=3
   show_grid=False
   # ... all 16 configurable parameters
   ```

**Success Criteria:**
- [ ] All tests pass (pytest)
- [ ] Sliders visually change rendering
- [ ] 10 baseline screenshots captured and saved
- [ ] No console errors during screenshot capture
- [ ] Defaults documented in current_defaults.txt
- [ ] Confirmed: selected_point_radius broken (always +2, not configurable)

**Verification:**
```bash
uv run pytest tests/ -v
ls -la tests/visual_regression/baseline/  # Should have 10 .png files
cat tests/visual_regression/current_defaults.txt  # Should list all 16 configurable parameters
```

**Why Enhanced Testing:**
- 10 screenshots (not 6) provide better coverage for regression detection
- Tests currently check implementation details (point_radius==5), not visual behavior
- Visual regression testing is CRITICAL for catching unintended appearance changes

---

### Phase 1: Create VisualSettings (Day 1 - 3 hours)

**Goals:**
- Introduce VisualSettings dataclass
- No behavior changes (parallel system)
- Validate with tests

**Tasks:**

1. **Create rendering/visual_settings.py**
   ```python
   # Complete dataclass with ALL 21 visual parameters (16 configurable + 5 display toggles)
   # Validation in __post_init__ for all numeric fields
   # Factory methods for common configurations (optional)
   ```

2. **Add to CurveViewWidget (parallel, not replacing)**
   ```python
   def __init__(self, parent=None):
       super().__init__(parent)

       # CRITICAL: Initialize visual settings FIRST (before any property access)
       # Location: Immediately after super().__init__() call
       # Reason: Phase 2 properties will reference self.visual
       self.visual: VisualSettings = VisualSettings()

       # Keep existing properties (backward compatibility during migration)
       self.point_radius: int = 5  # Will be removed in Phase 5
       # ...
   ```

   **CRITICAL REQUIREMENT:**
   - `self.visual = VisualSettings()` MUST be the first line after `super().__init__(parent)`
   - If placed after line 245 (where `self.point_radius` is set), Phase 2 will crash
   - Verify initialization order in actual file before committing

3. **Create unit tests**
   ```python
   # tests/test_visual_settings.py
   def test_visual_settings_defaults():
       """Verify defaults match CurveViewWidget current behavior."""
       vs = VisualSettings()
       assert vs.point_radius == 5
       assert vs.line_width == 2
       assert vs.show_grid is False

   def test_visual_settings_validation():
       """Verify invalid values raise errors."""
       with pytest.raises(ValueError, match="point_radius must be positive"):
           VisualSettings(point_radius=0)
   ```

**Success Criteria:**
- [ ] `rendering/visual_settings.py` created
- [ ] Tests pass: `pytest tests/test_visual_settings.py -v`
- [ ] Type checking passes: `./bpr rendering/visual_settings.py`
- [ ] CurveViewWidget has `self.visual` attribute
- [ ] No behavior changes (existing code unchanged)

**Rollback:** Delete visual_settings.py, remove self.visual attribute

---

### Phase 2: Integrate into RenderState (Day 2 - 4 hours)

**Goals:**
- Replace 5 scattered fields with single `visual` field
- Simplify RenderState.compute()
- No renderer changes yet (validate state extraction first)

**Tasks:**

1. **Add type-safe protocol for RenderState.compute()** (Type Safety Fix)
   ```python
   # rendering/render_state.py (add before RenderState class)

   from typing import Protocol
   from PySide6.QtGui import QImage, QPixmap

   class WidgetWithVisual(Protocol):
       """Protocol for widgets providing visual settings.

       This protocol defines the minimal interface required by RenderState.compute()
       for type-safe extraction of widget state. Using a protocol instead of 'Any'
       enables type checking and documents dependencies explicitly.
       """
       # Visual settings
       visual: VisualSettings

       # View transform
       zoom_factor: float
       pan_offset_x: float
       pan_offset_y: float
       manual_offset_x: float
       manual_offset_y: float
       flip_y_axis: bool

       # Background
       show_background: bool
       background_image: QImage | QPixmap | None

       # Image dimensions
       image_width: int
       image_height: int

       # Widget methods
       def width(self) -> int: ...
       def height(self) -> int: ...
   ```

2. **Update RenderState dataclass**
   ```python
   @dataclass(frozen=True)  # KEEP frozen=True (immutability contract)
   class RenderState:
       # Replace these 4 fields:
       # show_background: bool
       # show_grid: bool = True
       # point_radius: int = 3
       # line_width: int = 2

       # With single field:
       visual: VisualSettings  # Mutable child in frozen parent (valid Python)
   ```

3. **Update RenderState.compute() with type-safe protocol**
   ```python
   @classmethod
   def compute(cls, widget: WidgetWithVisual) -> "RenderState":  # Changed from Any
       return cls(
           visual=widget.visual,  # ✨ Single line replaces 4! (Type-checked)
           # ... other fields unchanged
       )
   ```

3. **Update RenderState validation**
   ```python
   def __post_init__(self):
       # Remove visual parameter validation (now in VisualSettings)
       # Keep other validations (widget dimensions, etc.)
   ```

4. **Add 4 compatibility properties (temporary migration layer)**
   ```python
   # Renderer uses 4 visual parameters from VisualSettings - need properties for ALL
   @property
   def show_background(self) -> bool:
       return self.visual.show_background

   @property
   def show_grid(self) -> bool:
       return self.visual.show_grid

   @property
   def point_radius(self) -> int:
       return self.visual.point_radius

   @property
   def line_width(self) -> int:
       return self.visual.line_width
   ```

   **CRITICAL:** All 4 properties required. Renderer has 5 call sites for VisualSettings fields:
   - Line 349: `render_state.show_background`
   - Line 355: `render_state.show_grid`
   - Line 832: `render_state.point_radius`
   - Line 1152: `render_state.line_width`
   - Line 1164: `render_state.point_radius`

**Success Criteria:**
- [ ] `WidgetWithVisual` protocol added (type safety)
- [ ] RenderState has `visual: VisualSettings` field
- [ ] RenderState.compute() signature changed to `widget: WidgetWithVisual` (was `widget: Any`)
- [ ] All 4 compatibility properties added (show_background, show_grid, point_radius, line_width)
- [ ] All tests pass (compatibility properties maintain behavior)
- [ ] Type checking passes: `./bpr rendering/render_state.py`
- [ ] Renderer still works (5 VisualSettings call sites verified)

**Rollback:** Revert render_state.py to Phase 1 state

---

### Phase 2.5: Test Construction Migration (Day 2 - 1 hour) ⚡ CRITICAL

**Goals:**
- Fix breaking change from Phase 2 (25 test construction sites)
- Maintain test readability and backward compatibility
- Enable smooth transition to new RenderState structure

**Background:**
Phase 2 removes `show_background`, `show_grid`, `point_radius`, `line_width` as dataclass fields, replacing them with `visual: VisualSettings`. However, 25 test files construct `RenderState(point_radius=5, show_grid=False, ...)` using keyword arguments. These will fail with `TypeError: unexpected keyword argument` after Phase 2.

**Test files affected (25 construction sites):**
- `tests/test_unified_curve_rendering.py` (13 sites)
- `tests/test_grid_centering.py` (8 sites)
- `tests/test_integration_real.py` (3 sites)
- `tests/test_rendering_real.py` (1 site)

**Tasks:**

1. **Add backward-compatible test constructor**
   ```python
   # rendering/render_state.py (add after RenderState class)

   @classmethod
   def create_for_tests(
       cls,
       *,
       # Visual settings (now in VisualSettings)
       show_background: bool = True,
       show_grid: bool = True,
       point_radius: int = 3,
       line_width: int = 2,
       # All other RenderState fields
       points: CurveDataList,
       current_frame: int,
       selected_points: set[int],
       widget_width: int,
       widget_height: int,
       zoom_factor: float = 1.0,
       pan_offset_x: float = 0.0,
       pan_offset_y: float = 0.0,
       manual_offset_x: float = 0.0,
       manual_offset_y: float = 0.0,
       flip_y_axis: bool = False,
       background_image: QImage | QPixmap | None = None,
       image_width: int = 0,
       image_height: int = 0,
       # Multi-curve fields (CORRECTED parameter names match RenderState)
       curves_data: dict[str, CurveDataList] | None = None,  # NOT all_curve_data
       display_mode: "DisplayMode | None" = None,
       selected_curve_names: set[str] | None = None,  # NOT selected_curves
       selected_curves_ordered: list[str] | None = None,
       curve_metadata: dict[str, dict[str, object]] | None = None,
       active_curve_name: str | None = None,  # NOT active_curve
       visible_curves: frozenset[str] | None = None,
   ) -> "RenderState":
       """Backward-compatible constructor for test code.

       Accepts visual parameters as keyword args and packages them into
       VisualSettings internally. This preserves test readability while
       supporting the new VisualSettings architecture.

       Example:
           render_state = RenderState.create_for_tests(
               points=test_points,
               current_frame=10,
               selected_points=set(),
               widget_width=800,
               widget_height=600,
               point_radius=5,      # Packaged into VisualSettings
               show_grid=False,     # Packaged into VisualSettings
           )
       """
       return cls(
           # Package visual parameters into VisualSettings
           visual=VisualSettings(
               show_background=show_background,
               show_grid=show_grid,
               point_radius=point_radius,
               line_width=line_width,
           ),
           # Pass through all other fields
           points=points,
           current_frame=current_frame,
           selected_points=selected_points,
           widget_width=widget_width,
           widget_height=widget_height,
           zoom_factor=zoom_factor,
           pan_offset_x=pan_offset_x,
           pan_offset_y=pan_offset_y,
           manual_offset_x=manual_offset_x,
           manual_offset_y=manual_offset_y,
           flip_y_axis=flip_y_axis,
           background_image=background_image,
           image_width=image_width,
           image_height=image_height,
           # Multi-curve fields (corrected parameter names)
           curves_data=curves_data or {},
           display_mode=display_mode,
           selected_curve_names=selected_curve_names or set(),
           selected_curves_ordered=selected_curves_ordered or [],
           curve_metadata=curve_metadata or {},
           active_curve_name=active_curve_name,
           visible_curves=visible_curves,
       )
   ```

2. **Update test construction sites (25 files)**

   **Search pattern:**
   ```bash
   grep -n "RenderState(" tests/test_unified_curve_rendering.py tests/test_grid_centering.py tests/test_integration_real.py tests/test_rendering_real.py
   ```

   **Replace pattern:**
   ```python
   # BEFORE (breaks after Phase 2)
   render_state = RenderState(
       points=test_points,
       current_frame=10,
       point_radius=5,        # ❌ Not a dataclass field anymore
       show_grid=False,       # ❌ Not a dataclass field anymore
       # ...
   )

   # AFTER (works with new structure)
   render_state = RenderState.create_for_tests(
       points=test_points,
       current_frame=10,
       point_radius=5,        # ✅ Packaged into VisualSettings
       show_grid=False,       # ✅ Packaged into VisualSettings
       # ...
   )
   ```

3. **Verify all tests pass**
   ```bash
   pytest tests/test_unified_curve_rendering.py -v
   pytest tests/test_grid_centering.py -v
   pytest tests/test_integration_real.py -v
   pytest tests/test_rendering_real.py -v
   ```

**Success Criteria:**
- [ ] `RenderState.create_for_tests()` classmethod added
- [ ] All 25 test construction sites updated to use `create_for_tests()`
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Type checking passes: `./bpr tests/`
- [ ] No `TypeError: unexpected keyword argument` errors

**Rollback:** Revert test files and remove `create_for_tests()` method

**Note:** This phase is **REQUIRED** before Phase 3. Skipping it will cause all 25 tests to fail after Phase 2.

---

### Phase 3: Update Renderer (Day 2-3 - 5 hours)

**Goals:**
- Remove hardcoded values
- Use render_state.visual.* everywhere
- Remove compatibility properties
- Verify visual correctness

**Tasks:**

1. **Audit renderer for hardcoded visual values**
   ```bash
   grep -n "= [0-9]" rendering/optimized_curve_renderer.py | grep -E "(radius|width|opacity|color)"
   # Focus on line 935: selected_radius = point_radius + 2 (hardcoded offset)
   ```

2. **Replace hardcoded selected point/line logic**
   ```python
   # BEFORE (line 935):
   selected_radius = point_radius + 2  # ❌ Hardcoded offset

   # AFTER:
   # Use selected_point_radius directly from VisualSettings
   selected_radius = render_state.visual.selected_point_radius

   # BEFORE (line 1151):
   line_width = render_state.line_width + (1 if is_active else 0)

   # AFTER:
   # Use selected_line_width for active curves
   line_width = render_state.visual.selected_line_width if is_active else render_state.visual.line_width
   ```

3. **Remove RenderState compatibility properties**
   ```python
   # Delete these from RenderState:
   # @property
   # def point_radius(self) -> int:
   #     return self.visual.point_radius
   ```

4. **Visual regression testing**
   - Load 2DTrackDatav2.txt
   - Capture screenshots at slider values: 2, 6, 10, 20 (point size)
   - Capture screenshots at slider values: 1, 5, 10 (line width)
   - Compare to Phase 0 baseline

**Success Criteria:**
- [ ] No hardcoded visual values in renderer
- [ ] All tests pass
- [ ] Type checking passes: `./bpr rendering/`
- [ ] Visual regression test passes (screenshots match baseline)
- [ ] Sliders change rendering smoothly (no jumps)

**Rollback:** Revert renderer changes, restore compatibility properties

---

### Phase 3.5: Verification Gate (Day 3 - 15 minutes) **CRITICAL**

**Goals:**
- Verify ALL renderer references updated before removing compatibility properties
- Prevent runtime AttributeError from missed references
- Gate between Phase 3 and Phase 4

**Tasks:**

1. **Verify no direct render_state property access remains (EXPANDED SCOPE)**
   ```bash
   # Must return 0 results for VisualSettings fields - CHECK ALL PYTHON FILES:
   grep -r "render_state\.point_radius" --include="*.py" --exclude-dir=".venv" .
   grep -r "render_state\.line_width" --include="*.py" --exclude-dir=".venv" .
   grep -r "render_state\.show_grid" --include="*.py" --exclude-dir=".venv" .
   grep -r "render_state\.show_background" --include="*.py" --exclude-dir=".venv" .
   ```

   **Note:** All 5 visual parameter references are in `rendering/optimized_curve_renderer.py`.
   No references exist outside rendering/ (verified via codebase grep).

2. **Verify all renderer usage goes through visual**
   ```bash
   # Must have results (confirms migration):
   grep -r "render_state\.visual\." --include="*.py" .
   ```

3. **Manual code inspection**
   - Open `rendering/optimized_curve_renderer.py`
   - Search for `render_state.` (without `visual`)
   - Verify ONLY non-visual fields accessed (points, current_frame, etc.)
   - Check `ui/curve_view_widget.py` for widget property access
   - Check `tests/` for RenderState construction patterns

**Success Criteria:**
- [ ] Zero results for VisualSettings properties (point_radius, line_width, show_grid, show_background)
- [ ] All VisualSettings parameter access goes through `render_state.visual.*`
- [ ] Manual inspection confirms no missed references (check ui/, tests/, protocols/)
- [ ] All tests still pass
- [ ] Verified: No dynamic attribute access (`getattr`, `__dict__`) on visual fields

**BLOCKER:** If ANY verification fails, DO NOT proceed to Phase 4. Return to Phase 3 and fix missed references.

**Actual Scope (Verified):**
- 5 total visual parameter references, ALL in `rendering/optimized_curve_renderer.py`
- Lines: 348 (show_background), 354 (show_grid), 831 (point_radius), 1151 (line_width), 1163 (point_radius)
- No references outside rendering/ directory
- Verification is straightforward: check these 5 lines use `render_state.visual.*`

**Why This Matters:**
- Phase 4 removes compatibility properties from RenderState
- Any remaining `render_state.point_radius` → runtime AttributeError
- This gate ensures all 5 references migrated to `render_state.visual.*`

---

### Phase 4: Update Controllers (Day 3 - 3 hours)

**Goals:**
- Update slider controllers to use widget.visual
- Remove widget property setters (use visual directly)
- Verify all UI controls work

**Tasks:**

1. **Update ViewManagementController slider handlers**
   ```python
   @Slot(int)
   def update_curve_point_size(self, value: int) -> None:
       if not self.main_window.curve_widget:
           return

       # Update VisualSettings (single source of truth)
       self.main_window.curve_widget.visual.point_radius = value
       self.main_window.curve_widget.visual.selected_point_radius = value + 2

       # Trigger repaint
       self.main_window.curve_widget.update()
       logger.debug(f"Updated point size to {value}")

   @Slot(int)
   def update_curve_line_width(self, value: int) -> None:
       if not self.main_window.curve_widget:
           return

       self.main_window.curve_widget.visual.line_width = value
       self.main_window.curve_widget.visual.selected_line_width = value + 1
       self.main_window.curve_widget.update()
       logger.debug(f"Updated line width to {value}")
   ```

2. **Update grid toggle controller (if exists)**

4. **Manual UI testing checklist**
   - [ ] Point Size slider changes point size
   - [ ] Line Width slider changes line width
   - [ ] Background toggle works
   - [ ] Grid toggle works
   - [ ] All changes visible immediately (no lag)

**Success Criteria:**
- [ ] All slider/checkbox handlers updated
- [ ] All tests pass
- [ ] Manual UI test checklist complete
- [ ] No console errors

**Rollback:** Revert controller changes

---

### Phase 5: Cleanup & Documentation (Day 4 - 2 hours)

**Goals:**
- Remove obsolete code
- Document new pattern
- Create migration guide

**Tasks:**

1. **Remove obsolete CurveViewWidget properties**
   ```python
   # DELETE (now in self.visual):
   # self.point_radius: int = 5
   # self.selected_point_radius: int = 7
   # self.line_width: int = 2
   # self.show_grid: bool = False
   # etc.
   ```

2. **Add backward-compatible properties (OPTIONAL)**
   ```python
   # Only if other code needs them during migration
   @property
   def point_radius(self) -> int:
       """DEPRECATED: Use widget.visual.point_radius instead."""
       return self.visual.point_radius
   ```

3. **Update CLAUDE.md with new pattern**
   ```markdown
   ## Adding Configurable Rendering Parameters

   To add a new slider/control for rendering appearance:

   1. **Add to VisualSettings** (rendering/visual_settings.py)
      ```python
      @dataclass
      class VisualSettings:
          new_parameter: int = 10  # Add with default
      ```

   2. **Create slider in UI** (ui/controllers/ui_initialization_controller.py)
      ```python
      slider = QSlider(...)
      slider.setValue(10)
      ```

   3. **Connect to controller** (ui/controllers/view_management_controller.py)
      ```python
      def update_new_parameter(self, value: int) -> None:
          self.main_window.curve_widget.visual.new_parameter = value
          self.main_window.curve_widget.update()
      ```

   4. **Use in renderer** (rendering/optimized_curve_renderer.py)
      ```python
      param = render_state.visual.new_parameter
      ```

   That's it! No manual extraction needed - RenderState.compute()
   automatically passes widget.visual to renderer.
   ```

4. **Create test pattern example**
   ```python
   def test_new_parameter_affects_rendering():
       """Verify new slider actually changes rendering."""
       widget = CurveViewWidget()

       # Set slider value
       widget.visual.new_parameter = 20

       # Compute render state
       state = RenderState.compute(widget)

       # Verify value propagated
       assert state.visual.new_parameter == 20
   ```

**Success Criteria:**
- [ ] Obsolete properties removed from CurveViewWidget
- [ ] CLAUDE.md updated with new pattern
- [ ] Test pattern documented
- [ ] All tests still pass
- [ ] Type checking still passes

**Rollback:** Restore deleted properties if needed

---

## Success Metrics

### Quantitative Metrics

**Code Quality:**
- [ ] Lines of code reduced by ~15-20 (net)
- [ ] Number of visual parameter declarations: 14 → 1 (VisualSettings)
- [ ] RenderState fields reduced: 5 → 1 (visual)
- [ ] Type errors: 0 (maintained)

**Test Coverage:**
- [ ] New tests added: ~5 (VisualSettings validation, property tests)
- [ ] All existing tests pass: 3175/3175
- [ ] Visual regression tests: 10 screenshots match baseline

**Performance:**
- [ ] No performance regression (rendering time unchanged)
- [ ] Memory footprint unchanged (VisualSettings ~200 bytes)

### Qualitative Metrics

**Maintainability:**
- [ ] Adding new slider: 4 steps → 4 steps (but simpler)
  - Old: Add property, add to RenderState, add extraction, update renderer (easy to forget)
  - New: Add to VisualSettings, create slider, connect controller, use in renderer (enforced by types)

**Correctness:**
- [ ] Sliders work correctly ✅ (user-reported bug fixed)
- [ ] No visual regressions ✅ (baseline screenshots match)
- [ ] No silent failures ✅ (type system enforces usage)

**Developer Experience:**
- [ ] Pattern documented in CLAUDE.md
- [ ] Example test provided
- [ ] Migration guide created

---

## Implementation Checklist

### Pre-Flight Checks
- [ ] Read full refactor plan
- [ ] Understand current bug and root cause
- [ ] Review VisualSettings design
- [ ] Allocate 4 days for implementation
- [ ] **CRITICAL:** Commit renderer fix (uncommitted changes to optimized_curve_renderer.py)
- [ ] Verify git status clean before creating feature branch
- [ ] Create feature branch: `refactor/visual-settings-dry`

### Phase 0: Validation (Day 1 - 2.5h)
- [ ] Run test suite: `uv run pytest tests/ -v | tee phase0_test_results.txt`
- [ ] Record baseline: All tests pass (3175+)
- [ ] Manual test: Load 2DTrackDatav2.txt
- [ ] Verify sliders work (point size 2→20, line width 1→10)
- [ ] Confirm broken behavior: selected_point_radius always +2
- [ ] Create directory: `tests/visual_regression/baseline/`
- [ ] Capture 10 baseline screenshots (4 point sizes, 3 line widths, 3 combined)
- [ ] Document current defaults in `tests/visual_regression/current_defaults.txt`
- [ ] Verify 10 .png files saved correctly

### Phase 1: Create VisualSettings (Day 1 - 3h)
- [ ] Create file: `rendering/visual_settings.py`
- [ ] Define VisualSettings dataclass (21 fields total: 16 configurable + 5 display toggles, mutable, NOT frozen)
- [ ] Add COMPLETE validation in `__post_init__` (all 6 numeric fields)
- [ ] Include all 21 fields: point_radius, selected_point_radius, line_width, selected_line_width, line_color, selected_line_color, show_grid, grid_size, grid_line_width, grid_color, show_background, show_points, show_lines, show_labels, show_velocity_vectors, show_all_frame_numbers
- [ ] **CRITICAL:** Add to CurveViewWidget `__init__` as FIRST line after `super().__init__()`
- [ ] Exact location: After line ~152 `super().__init__(parent)`
- [ ] Code: `self.visual: VisualSettings = VisualSettings()`
- [ ] Keep existing properties (parallel system for backward compatibility)
- [ ] Create test file: `tests/test_visual_settings.py`
- [ ] Test: Defaults match current behavior (point_radius=5, line_width=2, show_points=True, etc.)
- [ ] Test: Validation raises on invalid values (6 numeric field tests)
- [ ] Type check: `./bpr rendering/visual_settings.py`
- [ ] Run tests: `pytest tests/test_visual_settings.py -v`
- [ ] Verify `self.visual` initialized before properties (grep check)
- [ ] Commit: "feat: Add VisualSettings dataclass with 21 visual parameters (Phase 1)"

### Phase 2: Integrate RenderState (Day 2 - 4h)
- [ ] Edit `rendering/render_state.py`
- [ ] Replace 4 fields with `visual: VisualSettings`
- [ ] **CRITICAL:** Keep `@dataclass(frozen=True)` (do NOT remove frozen status)
- [ ] Update `RenderState.compute()` to pass `widget.visual`
- [ ] Remove visual validation from `__post_init__` (now in VisualSettings)
- [ ] Add 4 compatibility properties: `show_background`, `show_grid`, `point_radius`, `line_width`
- [ ] Verify 5 VisualSettings renderer call sites covered (lines 348, 354, 831, 1151, 1163)
- [ ] Type check: `./bpr rendering/render_state.py`
- [ ] Run all tests: `pytest tests/ -v`
- [ ] Verify sliders still work (manual test)
- [ ] Commit: "feat: Integrate VisualSettings into RenderState (Phase 2)"

### Phase 3: Update Renderer (Day 2-3 - 5h)
- [ ] Audit hardcoded values: `grep -n "selected_radius = point_radius + 2" rendering/optimized_curve_renderer.py`
- [ ] Replace: `selected_radius = point_radius + 2` (line 935) → `render_state.visual.selected_point_radius`
- [ ] Replace: `line_width = render_state.line_width + (1 if is_active else 0)` (line 1151) → `render_state.visual.selected_line_width if is_active else render_state.visual.line_width`
- [ ] Replace: `point_radius = render_state.point_radius + (2 if is_active else 0)` (line 1163) → `render_state.visual.selected_point_radius if is_active else render_state.visual.point_radius`
- [ ] **DO NOT remove compatibility properties yet** (Phase 3.5 verifies first)
- [ ] Type check: `./bpr rendering/`
- [ ] Run all tests: `pytest tests/ -v`
- [ ] Visual regression: Capture 10 screenshots (same as Phase 0)
- [ ] Compare to baseline: Should be identical
- [ ] Manual test: Slider changes rendering smoothly
- [ ] Commit: "feat: Renderer uses VisualSettings for selected points (Phase 3)"

### Phase 3.5: Verification Gate (Day 3 - 15min) **CRITICAL - EXPANDED SCOPE**
- [ ] grep -r "render_state\.point_radius" --include="*.py" --exclude-dir=".venv" . → Must return 0 results
- [ ] grep -r "render_state\.line_width" --include="*.py" --exclude-dir=".venv" . → Must return 0 results
- [ ] grep -r "render_state\.show_grid" --include="*.py" --exclude-dir=".venv" . → Must return 0 results
- [ ] grep -r "render_state\.show_background" --include="*.py" --exclude-dir=".venv" . → Must return 0 results
- [ ] grep -r "render_state\.visual\." --include="*.py" . → Must have 5 results (all in rendering/optimized_curve_renderer.py)
- [ ] Manual inspection: Verify lines 348, 354, 831, 1151, 1163 use `render_state.visual.*`
- [ ] **BLOCKER:** If ANY grep fails, return to Phase 3 and fix
- [ ] All tests still pass: `pytest tests/ -v`
- [ ] Remove compatibility properties from RenderState NOW (after verification)
- [ ] Type check: `./bpr rendering/render_state.py`
- [ ] Commit: "refactor: Remove RenderState compatibility properties (Phase 3.5)"

### Phase 4: Update Controllers (Day 3 - 3h)
- [ ] Edit `ui/controllers/view_management_controller.py`
- [ ] Update `update_curve_point_size()` to use `widget.visual.point_radius`
- [ ] Update `update_curve_line_width()` to use `widget.visual.line_width`
- [ ] Update grid toggle handler (if exists)
- [ ] Type check: `./bpr ui/controllers/`
- [ ] Run all tests: `pytest tests/ -v`
- [ ] Manual UI test: All sliders/checkboxes work
- [ ] No console errors
- [ ] Commit: "feat: Controllers use VisualSettings (Phase 4)"

### Phase 5: Cleanup (Day 4 - 2h)
- [ ] Edit `ui/curve_view_widget.py`
- [ ] Delete obsolete properties: `self.point_radius`, `self.line_width`, etc.
- [ ] Add backward-compatible properties if needed (deprecated warnings)
- [ ] Edit `CLAUDE.md`
- [ ] Add "Adding Configurable Rendering Parameters" section
- [ ] Document 4-step process
- [ ] Add test pattern example
- [ ] Type check: `./bpr ui/`
- [ ] Run all tests: `pytest tests/ -v`
- [ ] Commit: "docs: Document VisualSettings pattern (Phase 5)"

### Post-Implementation
- [ ] Full test suite: `pytest tests/ -v` (all pass)
- [ ] Type check full project: `./bpr` (0 errors)
- [ ] Manual smoke test: Load data, use all sliders
- [ ] Visual regression: Compare final to baseline (identical)
- [ ] Code review: Check diff for unintended changes
- [ ] Merge to main branch
- [ ] Close this document (move to completed/)

---

## Risk Mitigation

### Risk 1: Performance Regression
**Likelihood:** Low
**Impact:** High (rendering is hot path)
**Mitigation:**
- VisualSettings is small dataclass (~200 bytes)
- Passed by reference (no deep copy)
- No additional computation in hot path
- Benchmark before/after if concerned

**Rollback:** Revert to Phase N-1

### Risk 2: Visual Regressions
**Likelihood:** Medium
**Impact:** High (user-visible)
**Mitigation:**
- Baseline screenshots in Phase 0
- Visual regression test in Phase 3
- Manual testing after each phase
- Verify defaults match exactly

**Rollback:** Revert renderer changes, restore hardcoded values

### Risk 3: Breaking Tests
**Likelihood:** Medium
**Impact:** Medium (blocks progress)
**Mitigation:**
- Run tests after each phase
- Compatibility properties during migration
- Incremental changes (5 phases, not big bang)

**Rollback:** Revert to last passing commit

### Risk 4: Merge Conflicts
**Likelihood:** Low (personal project)
**Impact:** Low
**Mitigation:**
- Work in feature branch
- Rebase on main before merging
- Keep phases small (easy to resolve conflicts)

**Rollback:** N/A (resolve conflicts manually)

---

## Testing Strategy

### Unit Tests (Automated)

**New Tests (tests/test_visual_settings.py):**
```python
def test_visual_settings_defaults():
    """Defaults match CurveViewWidget behavior."""
    vs = VisualSettings()
    assert vs.point_radius == 5
    assert vs.selected_point_radius == 7
    assert vs.line_width == 2
    assert vs.show_grid is False

def test_visual_settings_validation_point_radius():
    """Negative point radius raises error."""
    with pytest.raises(ValueError, match="point_radius must be positive"):
        VisualSettings(point_radius=0)

def test_visual_settings_validation_grid_size():
    """Negative grid size raises error."""
    with pytest.raises(ValueError, match="grid_size must be positive"):
        VisualSettings(grid_size=0)

def test_render_state_uses_visual_settings():
    """RenderState.compute() extracts VisualSettings."""
    widget = MockCurveViewWidget()
    widget.visual = VisualSettings(point_radius=10, line_width=5)

    state = RenderState.compute(widget)

    assert state.visual.point_radius == 10
    assert state.visual.line_width == 5
```

**Existing Tests (Regression):**
- All 3175 tests must continue passing
- Run after each phase

### Integration Tests (Manual)

**Slider Functionality:**
1. Load 2DTrackDatav2.txt
2. Open Visualization panel
3. Move Point Size slider: 2 → 6 → 10 → 20
   - Verify points change size smoothly
   - No jumps or artifacts
4. Move Line Width slider: 1 → 5 → 10
   - Verify lines change width smoothly
5. Toggle Grid checkbox
   - Grid appears/disappears
6. Toggle Background checkbox
   - Background appears/disappears

**Visual Regression:**
- Capture screenshots at standardized settings
- Compare to baseline pixel-by-pixel (or visually)
- 6 screenshots total:
  - Point size: 2, 6, 10, 20
  - Line width: 1, 5, 10

 

---

## Rollback Plan

### Per-Phase Rollback

**If Phase N fails:**
1. Identify last passing commit: `git log --oneline`
2. Revert to that commit: `git revert <commit-hash>`
3. Verify tests pass: `pytest tests/ -v`
4. Document failure reason in this plan
5. Fix root cause before retrying

 

---

## Appendix: Files Modified

### Created Files (2)
```
CREATE  rendering/visual_settings.py     (~80 lines)
CREATE  tests/test_visual_settings.py    (~50 lines)
```

### Modified Files (5)
```
EDIT    rendering/render_state.py        (-8 fields, +1 field, -10 extraction lines)
EDIT    ui/curve_view_widget.py          (-14 properties, +1 visual object)
EDIT    rendering/optimized_curve_renderer.py  (-4 hardcoded values, +4 render_state.visual.*)
EDIT    ui/controllers/view_management_controller.py  (update 2 slider handlers)
EDIT    CLAUDE.md                         (+30 lines documentation)
```

### Total Impact
```
Lines added:   ~140 (new files + docs)
Lines removed: ~50  (duplicate fields + hardcoded values)
Net change:    +90 lines
```

**Benefit:** Permanent DRY improvement, prevents future bugs

---

## Plan Revisions (2025-10-26)

**Status:** Plan revised based on 5-agent verification findings

### Critical Issues Fixed

**1. Mutability Conflict Resolved**
- **Issue:** Original design claimed "frozen=True for snapshots" but code was mutable
- **Fix:** Clarified VisualSettings is mutable (NOT frozen) for controller modifications
- **Impact:** Controllers can now use `widget.visual.point_radius = value` directly
- **Location:** Lines 127-151 (VisualSettings design)

**2. Initialization Location Specified**
- **Issue:** Plan didn't specify WHERE to add `self.visual = VisualSettings()`
- **Fix:** Must be first line after `super().__init__()` in CurveViewWidget
- **Impact:** Prevents AttributeError in Phase 2 when properties reference self.visual
- **Location:** Lines 361-379 (Phase 1, Task 2)

**3. Phase 3.5 Verification Gate Added**
- **Issue:** No verification between updating renderer (Phase 3) and removing properties (Phase 4)
- **Fix:** New Phase 3.5 with grep-based verification before property removal
- **Impact:** Prevents runtime AttributeError from missed references
- **Location:** Lines 525-567, 873-885 (Phase 3.5 definition and checklist)

### Design Improvements

**4. Complete Validation Added**
- **Issue:** Only 3/13 numeric fields validated
- **Fix:** Added validation for selected_point_radius, selected_line_width, grid_size, grid_line_width
- **Impact:** Prevents invalid values from reaching renderer
- **Location:** Lines 173-199 (`__post_init__` validation)

**5. Bug Scope Clarified**
- **Issue:** Plan claimed "sliders non-functional" (overstated urgency)
- **Fix:** Clarified point_radius/line_width work, only selected_point_radius broken
- **Impact:** Accurate priority assessment (moderate, not critical)
- **Location:** Lines 10-26 (Executive Summary)

**6. Enhanced Visual Regression Testing**
- **Issue:** Plan had 6 screenshots, insufficient coverage
- **Fix:** Increased to 10 screenshots with comprehensive test matrix
- **Impact:** Better regression detection, documents expected visual behavior
- **Location:** Lines 326-399 (Phase 0), 821-830 (checklist)

### Verification Methodology

**Agent deployment:**
- 5 specialized agents (Explore, Code Reviewer, Type Expert, Deep Debugger, Refactoring Expert)
- 23 findings analyzed
- 4 contradictions resolved via code inspection
- 3 consensus critical issues (2+ agents)
- 4 single-agent findings verified

**Key findings:**
- Renderer DOES use render_state values in committed code (uncommitted fix improves it further)
- Default mismatch (widget=5, RenderState=3) already handled by compute() method
- Parameter count was 17, not 14 (3 parameters missed in original inventory)
- Verification scope must check all files, not just rendering/ (comprehensive search needed)
- All 4 compatibility properties required, not just 2 (5 renderer call sites for visual fields)
- 4 tests check exact values (not 45+ as originally estimated)
- Type system allows mutable fields in frozen dataclass (design is type-safe)
- 25 test construction sites break after Phase 2 (requires Phase 2.5 migration)

### Plan Status: AMENDED AND READY FOR IMPLEMENTATION

**Amendments Applied (2025-10-26 - Initial Plan Review):**
1. ✅ Parameter count corrected: 14 → 16 configurable parameters
2. ✅ Compatibility properties expanded: 2 → 4 properties
4. ✅ Verification scope expanded: rendering/ → all Python files
5. ✅ Bug status clarified: Renderer fix exists uncommitted, must commit before Phase 0

**Amendments Applied (2025-10-26 - Post 5-Agent Critical Findings):**
6. ✅ **Phase 2.5 added: Test Migration** (BLOCKER) - 25 test construction sites need `RenderState.create_for_tests()`
7. ✅ **Type Safety Protocol added** (HIGH) - `WidgetWithVisual` protocol replaces `widget: Any` in compute()
8. ✅ **Test count corrected** - 4 tests check exact values (not 45+ as originally stated):
   - tests/test_curve_view.py:87 (point_radius == 5)
   - tests/test_curve_view.py:88 (selected_point_radius == 7)
   - tests/test_data_flow.py:731 (point_radius == 10)
   - tests/test_protocols.py:131 (point_radius == 3)

**Amendments Applied (2025-10-26 - Post Code Verification):**
9. ✅ **background_opacity removed** (PHANTOM) - 21 references purged, field never existed in codebase
10. ✅ **Phase 2.5 create_for_tests() signature FIXED** (was BLOCKER) - Parameter names corrected:
    - ✅ `curves_data` (was incorrectly `all_curve_data`)
    - ✅ `active_curve_name` (was incorrectly `active_curve`)
    - ✅ `selected_curve_names` (was incorrectly `selected_curves`)
    - ✅ All RenderState fields included (`selected_curves_ordered`, `curve_metadata`, `visible_curves`)
11. ✅ **Phase 3.5 scope CORRECTED** (GOOD NEWS) - Claim of "268 references outside rendering/" was wrong:
    - Actual: 5 total visual parameter references, ALL in rendering/optimized_curve_renderer.py
    - Outside rendering/: 0 references (not 268!)
    - Verification will be trivial (single file, 5 lines)
12. ✅ **Phase 2 ordering VERIFIED** - Protocol added AFTER implementation (Phase 1 → Phase 2 sequence is correct)

**Amendments Applied (2025-10-26 - Post 5-Agent Verification):**
13. ✅ **Missing display properties ADDED** (was BLOCKER) - Added 5 display toggles to VisualSettings:
    - `show_points`, `show_lines`, `show_labels`, `show_velocity_vectors`, `show_all_frame_numbers`
    - Total: 16 → 21 fields in VisualSettings (all CurveViewWidget visual properties)
14. ✅ **frozen=True preserved in RenderState** (was DESIGN ERROR) - Plan now keeps `@dataclass(frozen=True)`
    - Nested mutable VisualSettings in frozen RenderState is valid Python
    - Maintains immutability contract for RenderState itself
15. ✅ **Plan examples updated** (was MISLEADING) - Corrected to show current code patterns:
    - Current code already uses `render_state.line_width + 1` (not hardcoded `3 if active else 2`)
    - Actual bug is selected_radius hardcoded `+2` (line 935)
16. ✅ **Current state clarified** - Renderer already uses RenderState for base values (committed code)

**ALL BLOCKERS RESOLVED:** Plan is now ready for implementation (see Amendments 13-16).

---

## Conclusion

This refactor addresses a real user-reported bug while eliminating technical debt that makes adding visual controls error-prone. The phased approach allows incremental validation and easy rollback if issues arise.

**Key Principle:** KISS (Keep It Simple, Stupid)
- Single source of truth (VisualSettings)
- Type system enforces correct usage
- Impossible to forget extraction step
- Clear documentation for future developers

**Expected Outcome:**
- Bug fixed ✅
- Code more maintainable ✅
- Pattern documented ✅
- No regressions ✅

---

**Ready to implement? Start with Phase 0 validation.**
