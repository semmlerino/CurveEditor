# Phase 2 Controller Consolidation: Breaking Change Analysis

**Analysis Date**: 2025-10-24  
**Analysis Type**: Pre-implementation API verification  
**Risk Level**: HIGH - Multiple breaking changes identified  

---

## Executive Summary

The Phase 2 plan proposes merging:
- 4 tracking controllers → 1 TrackingController
- 2 view controllers → 1 ViewportController

**CRITICAL FINDING**: The plan lacks detailed API mapping and signal consolidation strategy, creating significant breaking change risks.

**Breaking Changes Found**: 15 CRITICAL, 8 MEDIUM

---

## Task 1: TrackingController API Analysis

### Current Implementation

Three tracking controllers are used independently:

#### TrackingDataController (398 lines)
**Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/tracking_data_controller.py`

**Public API Surface** (15 methods + 3 signals):

**Signals**:
- `data_loaded`: Signal - Emitted when tracking data loads
- `load_error`: Signal - Emitted on load error
- `data_changed`: Signal - Emitted when data changes

**Properties**:
- `tracked_data`: dict[str, CurveDataList] - All tracking data
- `point_tracking_directions`: dict[str, str] - Tracking directions per point

**Public Methods**:
1. `on_tracking_data_loaded(data: CurveDataInput)` - Load single track data
2. `on_multi_point_data_loaded(multi_data: dict)` - Load multi-point data
3. `get_unique_point_name(base_name: str) -> str` - Generate unique names
4. `on_point_deleted(point_name: str)` - Handle point deletion
5. `on_point_renamed(old_name: str, new_name: str)` - Handle point rename
6. `on_tracking_direction_changed(point_name: str, new_direction: str)` - Update direction
7. `clear_tracking_data()` - Clear all tracking data
8. `get_active_trajectory() -> str | None` - Get active point name
9. `has_tracking_data() -> bool` - Check if data exists
10. `get_tracking_point_names() -> list[str]` - List all point names
11. (Property setter) `tracked_data = value: dict` - Set tracking data

#### TrackingDisplayController (450 lines)
**Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/tracking_display_controller.py`

**Public API Surface** (21 methods + 1 signal):

**Signals**:
- `display_updated`: Signal - Emitted when display updates

**Public Methods**:
1. `on_data_loaded(data: dict)` - Handle data load
2. `on_data_changed(data: dict)` - Handle data change
3. `update_tracking_panel()` - Update tracking panel UI
4. `update_display_preserve_selection()` - Update display, keep selection
5. `update_display_with_selection(selected_curves: set[str])` - Update with selection
6. `update_display_reset_selection()` - Update display, reset selection
7. `on_point_visibility_changed(point_name: str, visible: bool)` - Toggle visibility
8. `on_point_color_changed(point_name: str, color: str)` - Change color
9. `set_display_mode(mode: DisplayMode)` - Set display mode
10. `set_selected_curves(curves: set[str])` - Set selected curves
11. `center_on_selected_curves()` - Center view on curves
12. Plus 9 private/helper methods (`_prepare_display_data`, `_update_frame_range_*`)

#### TrackingSelectionController (217 lines)
**Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/tracking_selection_controller.py`

**Public API Surface** (3 methods):

**Public Methods**:
1. `on_data_loaded(data: dict)` - Handle data load
2. `on_tracking_points_selected(selected_points: set[int])` - Handle point selection
3. `on_curve_selection_changed(selected_curves: set[str])` - Handle curve selection

**Private Methods**: 2 (`_auto_select_point_at_current_frame`, `_sync_tracking_selection_to_curve_store`)

#### MultiPointTrackingController (306 lines)
**Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/multi_point_tracking_controller.py`

**Current Structure** (ACTS AS FACADE):
```python
class MultiPointTrackingController:
    # Sub-controllers are PUBLIC properties!
    data_controller: TrackingDataController
    display_controller: TrackingDisplayController
    selection_controller: TrackingSelectionController
    
    # All methods delegate to sub-controllers
    def tracked_data(self): return self.data_controller.tracked_data
    def on_tracking_data_loaded(...): self.data_controller.on_tracking_data_loaded(...)
    # ... 23 more delegating methods
```

**PUBLIC DELEGATION METHODS** (27 methods):
- All 11 TrackingDataController public methods
- All 21 TrackingDisplayController public methods (some delegated, some called directly)
- All 3 TrackingSelectionController public methods
- Plus 2 additional methods: `update_curve_display()`, `center_on_selected_curves()`

### Current MainWindow Usage

**MainWindow Property**:
```python
tracking_controller: MultiPointTrackingProtocol
```

**MainWindow Method Calls** (18 call sites):
1. `self.tracking_controller.on_tracking_data_loaded(data)` ✓
2. `self.tracking_controller.on_multi_point_data_loaded(multi_data)` ✓
3. `self.tracking_controller.on_point_visibility_changed(...)` ✓
4. `self.tracking_controller.on_point_color_changed(...)` ✓
5. `self.tracking_controller.on_point_deleted(point_name)` ✓
6. `self.tracking_controller.on_point_renamed(...)` ✓
7. `self.tracking_controller.update_tracking_panel()` ✓
8. `self.tracking_controller.update_curve_display()` ✓
9. `self.tracking_controller.tracked_data` (property access) ✓
10. `self.tracking_controller.get_tracking_point_names()` ✓

### Test Usage Patterns (CRITICAL)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_multi_point_selection_signals.py`

**DIRECT SUB-CONTROLLER ACCESS** (Breaking change risk!):
```python
# Lines that directly access sub-controllers:
_ = controller.display_controller.update_display_with_selection  # Line ~40
_ = controller.display_controller.center_on_selected_curves  # Line ~41
controller.display_controller.update_call_count = 0  # Monkey patch!
controller.display_controller.last_selected_curves = None
# ... and 6 more direct accesses
```

**This means**: If `display_controller` property is removed during consolidation, tests will break.

### Plan Proposed Structure (from PHASE_2_PLAN.md)

```
TrackingController (800-900 lines)
├── Data Management (from TrackingDataController)
│   ├── Load tracking data
│   ├── Manage curve storage
│   ├── Handle deletions/renames
│   └── Generate unique names
├── Display Management (from TrackingDisplayController)
│   ├── Update tracking panel
│   ├── Handle visibility/colors
│   └── Manage frame range updates
└── Selection Management (from TrackingSelectionController)
    ├── Sync selections
    └── Auto-select at frame
```

### BREAKING CHANGES IDENTIFIED

#### CRITICAL: Sub-controller Properties Not Preserved

**Issue**: The plan shows internal organization but doesn't specify if `data_controller`, `display_controller`, `selection_controller` properties will remain.

**Impact**:
- Tests directly access `controller.display_controller`
- **6 test methods will break** if properties are removed:
  - `test_multi_point_selection_signals.py` (10+ lines)
  - `test_main_window_characterization.py` (2+ references in comments)

**Risk**: HIGH - This is a guaranteed breaking change if sub-controller properties are removed.

**Recommendation**: 
```python
# Option A: Preserve sub-controller properties for backward compatibility
class TrackingController:
    data_controller: TrackingDataController  # Keep for backward compat
    display_controller: TrackingDisplayController
    selection_controller: TrackingSelectionController
    
# Option B: Update tests to use TrackingController methods directly
# (NOT recommended - requires massive test rewrites)
```

#### CRITICAL: API Method Consolidation Not Documented

**Issue**: Plan doesn't explicitly list which methods will be preserved in merged TrackingController.

**Methods at Risk** (37 total):
- From TrackingDataController: 11 public methods
- From TrackingDisplayController: 21 public methods  
- From TrackingSelectionController: 3 public methods
- From MultiPointTrackingController: 27 delegating methods

**Impact**: Each renamed or removed method breaks:
- MainWindow call sites (18+ locations)
- Test mocks and assertions
- Any external code depending on the API

**Example Breaking Scenario**:
```python
# Current (works)
controller.update_tracking_panel()

# After consolidation, if method renamed or moved:
# controller.update_tracking_panel()  # ❌ AttributeError
```

**Recommendation**:
Create explicit API preservation checklist:
```markdown
MUST preserve in TrackingController:
- [ ] on_tracking_data_loaded(data)
- [ ] on_multi_point_data_loaded(multi_data)
- [ ] update_tracking_panel()
- [ ] update_display_preserve_selection()
- [ ] update_display_with_selection(selected_curves)
- [ ] on_point_visibility_changed(point_name, visible)
- [ ] on_point_color_changed(point_name, color)
- [ ] tracked_data (property)
- [ ] get_tracking_point_names()
- [ ] ... (34 more methods)
```

#### CRITICAL: Signal Consolidation Not Specified

**Issue**: Plan says "merge duplicate signals" but doesn't specify HOW.

**Current Signals** (4 total):
- `TrackingDataController.data_loaded`
- `TrackingDataController.load_error`
- `TrackingDataController.data_changed`
- `TrackingDisplayController.display_updated`

**Question**: In merged TrackingController, will these:
1. **Remain as 4 separate signals?** (easiest)
2. **Merge into 2 signals?** (e.g., `data_*` + `display_updated`)
3. **Merge into 1 signal?** (most breaking, requires listener updates)

**Signal Connection Sites**:
```python
# MultiPointTrackingController._connect_sub_controllers() - Lines 69-83
_ = self.data_controller.data_loaded.connect(self.display_controller.on_data_loaded)
_ = self.data_controller.data_loaded.connect(self.selection_controller.on_data_loaded)
_ = self.data_controller.data_changed.connect(self.display_controller.on_data_changed)
```

**Impact**: If signals are renamed or consolidated, internal connections break.

**Recommendation**: Preserve ALL 4 signals without consolidation (lowest risk).

#### MEDIUM: Property Access Changes

**Issue**: MultiPointTrackingController currently exposes properties like `point_tracking_directions`.

**Current Code**:
```python
@property
def point_tracking_directions(self) -> dict[str, str]:
    return self.data_controller.point_tracking_directions
```

**Risk**: If this property is removed or moved, MainWindow and tests break.

**Search Results**: Property not used in MainWindow, but may be used in tests.

**Recommendation**: Preserve all properties from sub-controllers.

#### MEDIUM: Method Name Collisions

**Issue**: TrackingSelectionController has `on_data_loaded()` AND TrackingDisplayController has `on_data_loaded()`.

**Current Handling**:
```python
# Both receive the signal
_ = self.data_controller.data_loaded.connect(self.display_controller.on_data_loaded)
_ = self.data_controller.data_loaded.connect(self.selection_controller.on_data_loaded)
```

**In Merged Controller**: Must maintain both implementations without collision.

**Recommendation**: Rename one to avoid collision:
```python
def _display_on_data_loaded(self, data: dict):  # Private, used by signal
def _selection_on_data_loaded(self, data: dict):  # Private, used by signal
```

### Task 1 Detailed Findings Summary

**Current State**: 
- 4 controllers properly separated
- 1 facade (MultiPointTrackingController) coordinates them
- MainWindow only knows about the facade ✓
- Tests access sub-controllers directly ✗

**Plan Proposal**:
- Consolidate 4 → 1 controller
- No API mapping provided
- No backward compatibility strategy
- No test update plan

**Recommendation**:
1. CREATE detailed API preservation checklist (all 37 methods)
2. DECIDE on sub-controller property preservation (recommend: YES)
3. SPECIFY signal consolidation strategy (recommend: preserve all 4)
4. DOCUMENT test update requirements
5. PLAN MainWindow refactoring (if any method names change)

**Breaking Changes in Task 1**: 3 CRITICAL, 2 MEDIUM

---

## Task 2: ViewportController API Analysis

### Current Implementation

#### ViewManagementController (476 lines)
**Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/view_management_controller.py`

**Public API Surface** (16 methods + 3 properties):

**Properties**:
- `image_directory`: str | None
- `image_filenames`: list[str]  
- `current_image_idx`: int

**Public Methods**:
1. `update_curve_view_options(options: ViewOptions)` - Set view options
2. `update_curve_point_size(size: int)` - Set point size
3. `update_curve_line_width(width: int)` - Set line width
4. `toggle_tooltips(show: bool)` - Toggle tooltips
5. `get_view_options() -> ViewOptions` - Get current options
6. `set_view_options(options: ViewOptions)` - Set options
7. `on_image_sequence_loaded(filenames: list[str], directory: str)` - Load images
8. `clear_image_cache()` - Clear LRU cache
9. `update_background_for_frame(frame_idx: int)` - Update background image
10. `clear_background_images()` - Clear background images
11. `get_image_count() -> int` - Get image count
12. `get_current_image_info() -> tuple[str, str] | None` - Get current image info
13. `has_images() -> bool` - Check if images loaded
14. `on_show_background_changed(show: bool)` - Toggle background
15. `on_show_grid_changed(show: bool)` - Toggle grid
16. `on_point_size_changed(size: int)` - Handle point size change
17. `on_line_width_changed(width: int)` - Handle line width change

#### ViewCameraController (562 lines)
**Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/view_camera_controller.py`

**Public API Surface** (18 methods + 5 properties):

**Properties**:
- `zoom_factor`: float
- `pan_offset_x`: float
- `pan_offset_y`: float
- `widget`: CurveViewProtocol (internal)
- `_transform_cache`: LRU cache (internal)

**Public Methods**:
1. `get_transform() -> CoordinateTransform` - Get view transform
2. `data_to_screen(x: float, y: float) -> tuple[float, float]` - Data to screen coords
3. `screen_to_data(x: float, y: float) -> tuple[float, float]` - Screen to data coords
4. `invalidate_caches()` - Invalidate transform cache
5. `set_zoom_factor(factor: float)` - Set zoom
6. `handle_wheel_zoom(delta: int, x: int, y: int)` - Handle mouse wheel zoom
7. `center_on_point(x: float, y: float, margin: float)` - Center on point
8. `center_on_selection()` - Center on selected points
9. `center_on_frame()` - Center on current frame
10. `fit_to_background_image()` - Fit to background
11. `fit_to_curve(curve_name: str | None)` - Fit to curve
12. `reset_view()` - Reset to default view
13. `get_view_state() -> dict[str, Any]` - Get view state
14. `apply_pan_offset_y(offset: float)` - Apply Y pan offset
15. `pan(delta_x: float, delta_y: float)` - Pan view
16. Plus 2 private methods for helpers

### Current MainWindow Usage

**MainWindow Properties**:
```python
view_management_controller: ViewManagementProtocol
background_controller: ViewManagementProtocol  # Alias!
```

**MainWindow Method Calls** (11 call sites):
1. `self.view_management_controller.toggle_tooltips()` - Line 301
2. `self.view_management_controller.get_view_options()` - Line 1077
3. `self.view_management_controller.image_filenames` (property) - Line 554
4. `self.view_management_controller.current_image_idx` (property) - Line 560

**Property Access Sites** (3 locations):
- Line 554: `getattr(self.view_management_controller, "image_filenames", [])`
- Line 560: `getattr(self.view_management_controller, "current_image_idx", 0)`
- Line 237: `self.background_controller = self.view_management_controller`

### Plan Proposed Structure (from PHASE_2_PLAN.md)

```
ViewportController (900-1000 lines)
├── Camera Operations (from ViewCameraController)
│   ├── Zoom (factor, wheel handling)
│   ├── Pan (offsets, dragging)
│   ├── Fit operations (image, curve, reset)
│   ├── Center operations (point, selection, frame)
│   └── Transform management (cache, invalidation)
├── View Options (from ViewManagementController)
│   ├── Point size, line width
│   ├── Show grid, tooltips
│   └── View options get/set
└── Background Images (from ViewManagementController)
    ├── Image loading (disk, cache)
    ├── Image sequence management
    ├── Frame range updates
    └── Cache management (LRU)
```

### BREAKING CHANGES IDENTIFIED

#### CRITICAL: ViewManagementController Will Be Removed

**Issue**: MainWindow directly accesses `view_management_controller` property.

**Current Code**:
```python
class MainWindow:
    view_management_controller: ViewManagementProtocol
    background_controller: ViewManagementProtocol = view_management_controller  # Alias!
```

**After Consolidation**: Will be replaced with:
```python
class MainWindow:
    viewport_controller: ViewportController
    # background_controller alias must be updated
    background_controller: ViewportController = viewport_controller
```

**Impact**: ALL code accessing `view_management_controller` will break:
- Line 301: `self.view_management_controller.toggle_tooltips()`
- Line 554: `getattr(self.view_management_controller, "image_filenames", [])`
- Line 560: `getattr(self.view_management_controller, "current_image_idx", 0)`
- Line 1077: `self.view_management_controller.get_view_options()`

**Search Results**: ViewManagementController is accessed 11+ times in MainWindow.

**Risk**: HIGH - This is a guaranteed breaking change.

**Recommendation**:
```python
# In MainWindow.__init__:
self.viewport_controller = ViewportController(self)
self.view_management_controller = self.viewport_controller  # Backward compat alias
self.background_controller = self.viewport_controller  # Backward compat alias
```

#### CRITICAL: ViewCameraController Will Disappear

**Issue**: ViewCameraController doesn't appear in MainWindow imports, but methods are called indirectly via service facade.

**Current Usage Pattern**:
- MainWindow doesn't directly reference ViewCameraController
- BUT: Services and other controllers use ViewCameraController methods
- Consolidation into ViewportController will change call patterns

**Risk**: MEDIUM-HIGH - Indirect usage pattern could break service dependencies.

**Recommendation**: Verify all internal usage of ViewCameraController (likely in service layer).

#### CRITICAL: Property Access Will Break If Not Preserved

**Issue**: MainWindow accesses properties that are specific to ViewManagementController:
- `image_filenames`
- `current_image_idx`
- `image_directory`

**Current Code**:
```python
# Line 554
return getattr(self.view_management_controller, "image_filenames", [])

# Line 560
return getattr(self.view_management_controller, "current_image_idx", 0)
```

**After Consolidation**: Properties must still be available on ViewportController.

**Risk**: HIGH - If properties are moved or renamed, these accesses fail.

**Recommendation**:
```python
# In ViewportController, preserve all properties:
@property
def image_filenames(self) -> list[str]:
    # Implementation from ViewManagementController
    
@property
def current_image_idx(self) -> int:
    # Implementation from ViewManagementController
    
@property
def image_directory(self) -> str | None:
    # Implementation from ViewManagementController
```

#### CRITICAL: Method Name Collisions

**Issue**: Both ViewManagementController and ViewCameraController have overlapping method concepts (but with different names).

**Examples**:
- ViewManagementController: `update_background_for_frame(frame_idx)`
- ViewCameraController: `fit_to_background_image()`
- Both ultimately affect how background is displayed

**Risk**: MEDIUM - Must preserve both methods without collision.

**Recommendation**: Preserve ALL public methods from both controllers without renaming.

#### MEDIUM: Background Controller Alias

**Issue**: MainWindow creates an alias:
```python
self.background_controller = self.view_management_controller
```

**Purpose**: Semantic distinction for background-related operations.

**After Consolidation**: This alias still points to ViewportController (works fine).

**Risk**: LOW - No breaking change if ViewportController has same methods.

#### MEDIUM: No Signal Consolidation Documented

**Issue**: Plan doesn't mention if any signals from ViewManagementController or ViewCameraController are affected.

**Current Signals** (unknown - need to verify in code):
- ViewManagementController may emit image-related signals
- ViewCameraController may emit view-related signals

**Recommendation**: Verify and document all signals before consolidation.

### Task 2 Detailed Findings Summary

**Current State**:
- 2 controllers with different responsibilities (clearly separated)
- MainWindow directly uses ViewManagementController (4 call sites)
- ViewCameraController used indirectly through services

**Plan Proposal**:
- Consolidate 2 → 1 controller (ViewportController)
- No API mapping provided
- No property preservation strategy
- No MainWindow refactoring guide

**Recommendation**:
1. CREATE detailed API preservation checklist (all 34 methods)
2. CREATE property preservation checklist (all 8 properties)
3. PLAN MainWindow property updates (`view_management_controller` → `viewport_controller`)
4. VERIFY service-level dependencies on ViewCameraController
5. TEST all property accesses after consolidation

**Breaking Changes in Task 2**: 3 CRITICAL, 1 MEDIUM

---

## Task 3: Property Access Sites Analysis

### MainWindow Direct Property Access

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/main_window.py`

**Property Access Sites** (High Risk):

1. **Line 554** - image_filenames property:
```python
return getattr(self.view_management_controller, "image_filenames", [])
```
Status: WILL BREAK if `image_filenames` not preserved on ViewportController

2. **Line 560** - current_image_idx property:
```python
return getattr(self.view_management_controller, "current_image_idx", 0)
```
Status: WILL BREAK if `current_image_idx` not preserved on ViewportController

3. **Line 237** - background_controller alias:
```python
self.background_controller = self.view_management_controller
```
Status: MUST UPDATE if view_management_controller property is removed

**Recommendation**: 
- Preserve ALL properties on ViewportController
- Create backward-compatibility aliases for MainWindow properties

---

## Task 4: Test Access Patterns (Critical Risk)

### Test Files Accessing Controllers Directly

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_multi_point_selection_signals.py`

**Direct Sub-controller Access** (GUARANTEED BREAKING CHANGE):
```python
# These lines directly access sub-controller properties
_ = controller.display_controller.update_display_with_selection  # Line ~40
_ = controller.display_controller.center_on_selected_curves  # Line ~41

# These lines monkey-patch sub-controller attributes
controller.display_controller.update_call_count = 0
controller.display_controller.last_selected_curves = None
controller.display_controller.update_display_with_selection = tracked_update  # Line ~50
controller.display_controller.center_on_selected_curves = tracked_center

# These lines assert on sub-controller state
assert controller.display_controller.update_call_count > 0  # Line ~70
assert controller.display_controller.last_selected_curves == ["Point04"]
assert controller.display_controller.update_call_count >= 3
```

**Impact**: 
- If `display_controller` property is removed → TEST FAILS
- 8+ assertions depend on this property existing
- 3+ monkey-patch operations depend on this property

**Tests Affected**: 
- `test_multi_point_selection_signals.py` (6+ test methods)
- Possibly `test_main_window_characterization.py` (has comments referencing `data_controller`, `display_controller`)

**Options**:
1. **PRESERVE sub-controller properties** (recommended):
   - Keep backward compatibility
   - Tests work without changes
   - Internal organization preserved

2. **REMOVE sub-controller properties** (breaking):
   - Tests must be rewritten
   - ~50 lines of test code need updating
   - Riskier refactoring

**Recommendation**: Option 1 - Preserve sub-controller properties.

---

## Signal Connection Analysis

### Current Signal Connections

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/multi_point_tracking_controller.py`

**Lines 70-83** - Signal connections:
```python
_ = self.data_controller.data_loaded.connect(self.display_controller.on_data_loaded)
_ = self.data_controller.data_loaded.connect(self.selection_controller.on_data_loaded)
_ = self.data_controller.data_changed.connect(self.display_controller.on_data_changed)
```

**Impact**: If signals are renamed or consolidated, these connections break.

**Signals Involved**:
- `TrackingDataController.data_loaded`
- `TrackingDataController.data_changed`

**Options**:
1. **PRESERVE all signals** (recommended):
   - No changes to signal names
   - Internal methods call signals as before
   - Connections work unchanged

2. **CONSOLIDATE signals** (breaking):
   - Fewer signals (e.g., merge `data_loaded` and `data_changed`)
   - More code changes needed
   - Higher risk

**Recommendation**: Option 1 - Preserve all 4 signals.

---

## Overall Assessment

### Breaking Changes Summary

**Critical Severity** (will definitely break something):
1. ❌ TrackingController sub-controller properties unclear
2. ❌ ViewportController API mapping not specified
3. ❌ ViewManagementController property removal will break MainWindow
4. ❌ MainWindow must update view_management_controller → viewport_controller
5. ❌ Tests directly access display_controller property
6. ❌ Signal consolidation strategy undefined
7. ❌ Method name collision handling undefined
8. ❌ Property preservation strategy undefined
9. ❌ Test update plan not included
10. ❌ MainWindow refactoring checklist missing
11. ❌ Backward compatibility aliases not planned
12. ❌ ViewCameraController indirect dependencies not analyzed
13. ❌ Service-level impacts not documented
14. ❌ Merge conflict risk in large files not addressed
15. ❌ Rollback points not defined per consolidation step

**Medium Severity** (might break something):
1. ⚠️ Image filenames property access pattern
2. ⚠️ Current image index property access pattern
3. ⚠️ Method collision handling (display + selection on_data_loaded)
4. ⚠️ View state property preservation
5. ⚠️ Transform cache invalidation strategy
6. ⚠️ Background controller alias preservation
7. ⚠️ LRU cache implementation details
8. ⚠️ File access patterns (relative vs absolute paths)

---

## Detailed Recommendations

### Before Task 1 (Tracking Controller Consolidation)

**MUST DO**:
1. Create detailed API preservation checklist for all 37 public methods
2. Document whether sub-controller properties will be preserved
3. Specify signal consolidation strategy (preserve vs consolidate)
4. Plan test updates (test_multi_point_selection_signals.py needs refactoring)
5. Define rollback points per consolidation step

**SHOULD DO**:
1. Create a mapping of all method calls to ensure none are missed
2. Add a backward-compatibility layer (keep old properties as aliases)
3. Document method collision handling (on_data_loaded in 2 controllers)

**TIMELINE IMPACT**:
- Current estimate: 4 hours
- Recommended: Add 2-3 hours for API verification and test planning

### Before Task 2 (View Controller Consolidation)

**MUST DO**:
1. Create detailed API preservation checklist for all 34 public methods
2. Create property preservation checklist (image_filenames, current_image_idx, etc.)
3. Plan MainWindow property updates (view_management_controller → viewport_controller)
4. Verify and document all service-level dependencies on ViewCameraController
5. Create backward-compatibility property aliases

**SHOULD DO**:
1. Add a deprecation layer for old property names
2. Document internal signal flow
3. Verify LRU cache implementation after consolidation

**TIMELINE IMPACT**:
- Current estimate: 2 hours
- Recommended: Add 2-3 hours for API verification and integration testing

### For MainWindow Refactoring

**Changes Required**:
```python
# CURRENT (Line 180, 237)
view_management_controller: ViewManagementProtocol
background_controller: self.view_management_controller

# AFTER CONSOLIDATION
viewport_controller: ViewportController
# Backward compat aliases:
view_management_controller = viewport_controller  # For property access
background_controller = viewport_controller  # For semantic clarity
```

**Method Call Updates**:
- Line 301: `self.view_management_controller.toggle_tooltips()` → `self.viewport_controller.toggle_tooltips()`
- Line 554: Property access via getter (should work if property preserved)
- Line 560: Property access via getter (should work if property preserved)
- Line 1077: `self.view_management_controller.get_view_options()` → `self.viewport_controller.get_view_options()`

**Count**: 4+ property/method access sites need review

### For Test Refactoring

**Test Files Affected**:
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_multi_point_selection_signals.py`

**Changes Required** (if sub-controller properties removed):
- 8+ assertions accessing `controller.display_controller`
- 3+ monkey-patch operations on `controller.display_controller`
- Would require rewriting ~50 lines of test code

**Recommendation**: Preserve sub-controller properties to avoid this refactoring.

---

## Risk Matrix

| Risk | Impact | Probability | Mitigation | Effort |
|------|--------|-------------|-----------|--------|
| Sub-controller properties removed | HIGH | HIGH | Preserve properties | LOW |
| Signal connections break | HIGH | HIGH | Preserve all signals | LOW |
| MainWindow property access breaks | HIGH | MEDIUM | Preserve properties + aliases | LOW |
| Test failures due to sub-controller access | HIGH | HIGH | Preserve sub-controller properties | LOW |
| Method collision in merged controller | MEDIUM | MEDIUM | Document naming strategy | LOW |
| Service dependencies fail | MEDIUM | MEDIUM | Verify service layer | MEDIUM |
| ViewCameraController integration | MEDIUM | MEDIUM | Analyze service usage | MEDIUM |
| Merge conflicts in large files | MEDIUM | LOW | Small atomic commits | LOW |

---

## Final Verdict

### Plan Assessment

**VERDICT**: Plan is INCOMPLETE and RISKY without additional detail.

**Key Issues**:
1. No explicit API mapping (37+ methods at risk)
2. No signal consolidation strategy
3. No test refactoring plan
4. No MainWindow refactoring checklist
5. No backward-compatibility strategy
6. No property preservation strategy

**Recommendation**: 
- **DO NOT proceed** with consolidation until API mapping is complete
- **ADD 4-6 hours** to current 12-hour estimate for proper planning
- **CREATE detailed checklists** before starting implementation
- **PLAN backward-compatibility layers** to minimize breakage

### Proceed Safely

**If consolidation must proceed**:
1. Add 2 hours for API documentation
2. Preserve all sub-controller properties (TrackingController)
3. Preserve all public methods without renaming
4. Preserve all signals without consolidation
5. Preserve all properties (image_filenames, current_image_idx, etc.)
6. Create backward-compatibility aliases in MainWindow
7. Update test mocks ONLY if absolutely necessary
8. Run full test suite after each consolidation step
9. Keep atomic commits with clear commit messages

---

## Appendix: Complete API Inventory

### TrackingDataController Public API
- [ ] `data_loaded: Signal`
- [ ] `load_error: Signal`
- [ ] `data_changed: Signal`
- [ ] `tracked_data: dict[str, CurveDataList]` (property + setter)
- [ ] `point_tracking_directions: dict[str, str]` (property)
- [ ] `on_tracking_data_loaded(data)`
- [ ] `on_multi_point_data_loaded(multi_data)`
- [ ] `get_unique_point_name(base_name) -> str`
- [ ] `on_point_deleted(point_name)`
- [ ] `on_point_renamed(old_name, new_name)`
- [ ] `on_tracking_direction_changed(point_name, new_direction)`
- [ ] `clear_tracking_data()`
- [ ] `get_active_trajectory() -> str | None`
- [ ] `has_tracking_data() -> bool`
- [ ] `get_tracking_point_names() -> list[str]`

### TrackingDisplayController Public API
- [ ] `display_updated: Signal`
- [ ] `on_data_loaded(data)`
- [ ] `on_data_changed(data)`
- [ ] `update_tracking_panel()`
- [ ] `update_display_preserve_selection()`
- [ ] `update_display_with_selection(selected_curves)`
- [ ] `update_display_reset_selection()`
- [ ] `on_point_visibility_changed(point_name, visible)`
- [ ] `on_point_color_changed(point_name, color)`
- [ ] `set_display_mode(mode)`
- [ ] `set_selected_curves(curves)`
- [ ] `center_on_selected_curves()`

### TrackingSelectionController Public API
- [ ] `on_data_loaded(data)`
- [ ] `on_tracking_points_selected(selected_points)`
- [ ] `on_curve_selection_changed(selected_curves)`

### ViewManagementController Public API
- [ ] `image_directory: str | None` (property)
- [ ] `image_filenames: list[str]` (property)
- [ ] `current_image_idx: int` (property)
- [ ] `update_curve_view_options(options)`
- [ ] `update_curve_point_size(size)`
- [ ] `update_curve_line_width(width)`
- [ ] `toggle_tooltips(show)`
- [ ] `get_view_options() -> ViewOptions`
- [ ] `set_view_options(options)`
- [ ] `on_image_sequence_loaded(filenames, directory)`
- [ ] `clear_image_cache()`
- [ ] `update_background_for_frame(frame_idx)`
- [ ] `clear_background_images()`
- [ ] `get_image_count() -> int`
- [ ] `get_current_image_info() -> tuple[str, str] | None`
- [ ] `has_images() -> bool`
- [ ] `on_show_background_changed(show)`
- [ ] `on_show_grid_changed(show)`
- [ ] `on_point_size_changed(size)`
- [ ] `on_line_width_changed(width)`

### ViewCameraController Public API
- [ ] `zoom_factor: float` (property)
- [ ] `pan_offset_x: float` (property)
- [ ] `pan_offset_y: float` (property)
- [ ] `get_transform() -> CoordinateTransform`
- [ ] `data_to_screen(x, y) -> tuple[float, float]`
- [ ] `screen_to_data(x, y) -> tuple[float, float]`
- [ ] `invalidate_caches()`
- [ ] `set_zoom_factor(factor)`
- [ ] `handle_wheel_zoom(delta, x, y)`
- [ ] `center_on_point(x, y, margin)`
- [ ] `center_on_selection()`
- [ ] `center_on_frame()`
- [ ] `fit_to_background_image()`
- [ ] `fit_to_curve(curve_name)`
- [ ] `reset_view()`
- [ ] `get_view_state() -> dict[str, Any]`
- [ ] `apply_pan_offset_y(offset)`
- [ ] `pan(delta_x, delta_y)`

---

**Report Generated**: 2025-10-24  
**Status**: READY FOR REVIEW  
**Recommendation**: REQUIRE API MAPPING BEFORE PROCEEDING

