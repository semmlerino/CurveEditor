# Phase 2 Breaking Changes - Code Location Reference

**Purpose**: Quick reference for all code locations affected by Phase 2 consolidation

**Generated**: 2025-10-24

---

## Task 1: Tracking Controller Consolidation - Code Locations

### Files to Merge

#### TrackingDataController
**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/tracking_data_controller.py`
**Size**: 398 lines
**Status**: Will be merged into TrackingController
**Line Range**: 22-397

**Key Components**:
- Class definition: Line 22
- Signals: Lines 39-41
- __init__: Lines 43-54
- Properties: Lines 79-99 (tracked_data), Line 52 (point_tracking_directions)
- Methods: Lines 93-397

#### TrackingDisplayController
**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/tracking_display_controller.py`
**Size**: 450 lines
**Status**: Will be merged into TrackingController
**Line Range**: 42-449

**Key Components**:
- Class definition: Line 42
- Signal: Line 56
- __init__: Lines 58-65
- Methods: Lines 67-449

#### TrackingSelectionController
**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/tracking_selection_controller.py`
**Size**: 217 lines
**Status**: Will be merged into TrackingController
**Line Range**: 17-216

**Key Components**:
- Class definition: Line 17
- __init__: Lines 27-34
- Methods: Lines 36-216

#### MultiPointTrackingController (Facade)
**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/multi_point_tracking_controller.py`
**Size**: 306 lines
**Status**: Will contain merged TrackingController or be replaced
**Line Range**: 35-306

**Key Components**:
- Sub-controller instantiation: Lines 57-59
- Signal connections: Lines 70-83
- Delegating methods: Lines 96-306

### MainWindow Usage - Tracking Controllers

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/main_window.py`

**Property Declaration**:
- Line 183: `tracking_controller: MultiPointTrackingProtocol`

**Instantiation**:
- Line 239: `self.tracking_controller = MultiPointTrackingController(self)`

**Method Calls** (18+ locations):
```
Line 668: self.tracking_controller.on_tracking_data_loaded(data)
Line 673: self.tracking_controller.on_multi_point_data_loaded(multi_data)
Line 979: self.tracking_controller.on_point_visibility_changed(...)
Line 983: self.tracking_controller.on_point_color_changed(...)
Line 987: self.tracking_controller.on_point_deleted(point_name)
Line 991: self.tracking_controller.on_point_renamed(...)
Line 995: self.tracking_controller.update_tracking_panel()
Line 999: self.tracking_controller.update_curve_display()
Line 571: self.tracking_controller.tracked_data (property access)
Line 576: self.tracking_controller.get_tracking_point_names()
```

### Test Files - Tracking Sub-controller Access

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_multi_point_selection_signals.py`

**Direct Sub-controller Access Locations**:
```
Lines ~40-41: Access controller.display_controller methods
Lines ~50-60: Monkey-patch operations on controller.display_controller
Lines ~70+: Assertions checking controller.display_controller state
```

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_main_window_characterization.py`

**Comments Referencing Sub-controllers**:
```
Search: "data_controller", "display_controller" in comments
```

### Import Locations

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/__init__.py`

**Exports Tracking Controllers**:
- TrackingDataController import
- TrackingDisplayController import
- TrackingSelectionController import
- MultiPointTrackingController import

**Status**: Will need updating to export merged TrackingController

---

## Task 2: View Controller Consolidation - Code Locations

### Files to Merge

#### ViewManagementController
**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/view_management_controller.py`
**Size**: 476 lines
**Status**: Will be merged into ViewportController
**Line Range**: 41-475

**Key Components**:
- Class definition: Line 41
- __init__: Lines 51-73
- Properties: Lines 64-71 (image_directory, image_filenames, current_image_idx, image_cache, etc.)
- Methods: Lines 77-475

#### ViewCameraController
**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/view_camera_controller.py`
**Size**: 562 lines
**Status**: Will be merged into ViewportController
**Line Range**: 69-561

**Key Components**:
- Class definition: Line 69
- Protocol: Lines 13-66 (CurveViewProtocol)
- __init__: Lines 85-100
- Properties: Lines 92-100 (widget, zoom_factor, pan_offset_x, pan_offset_y, _transform_cache)
- Methods: Lines 104-561

### MainWindow Usage - View Controllers

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/main_window.py`

**Property Declarations**:
- Line 180: `view_management_controller: ViewManagementProtocol`
- Line 182: `background_controller: ViewManagementProtocol`

**Instantiation**:
- Line 236: `self.view_management_controller = ViewManagementController(self)`
- Line 237: `self.background_controller = self.view_management_controller` (alias)

**Method Calls** (4+ direct call sites):
```
Line 301: self.view_management_controller.toggle_tooltips()
Line 1077: self.view_management_controller.get_view_options()
```

**Property Access** (using getattr for safety):
```
Line 554: getattr(self.view_management_controller, "image_filenames", [])
Line 560: getattr(self.view_management_controller, "current_image_idx", 0)
```

### Service Layer Usage - ViewCameraController

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/services/transform_service.py`

**Likely Usage Pattern** (indirect access through service):
- ViewCameraController methods used for coordinate transforms
- Need to verify all service-level dependencies

---

## Task 3: SessionManager Integration (Existing Module)

### SessionManager Module

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/session_manager.py`

**Current Status**:
- Module exists but is NOT integrated into MainWindow
- MainWindow has `session_manager` property that returns None

**MainWindow Reference**:
```
File: /mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/main_window.py
Search for: "session_manager" property
Status: Not instantiated, returns None
```

---

## Controllers Import Chain

### Main Import File

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/__init__.py`

**Current Exports**:
```python
from .action_handler_controller import ActionHandlerController
from .frame_change_coordinator import FrameChangeCoordinator
from .multi_point_tracking_controller import MultiPointTrackingController
from .point_editor_controller import PointEditorController
from .signal_connection_manager import SignalConnectionManager
from .timeline_controller import TimelineController
from .ui_initialization_controller import UIInitializationController
from .view_camera_controller import ViewCameraController
from .view_management_controller import ViewManagementController
```

**Status**: Will need updating to export consolidated controllers

### MainWindow Imports

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/main_window.py`
**Lines**: 63-85

**Current Imports**:
```python
from .controllers import (
    ActionHandlerController,
    MultiPointTrackingController,
    PointEditorController,
    SignalConnectionManager,
    TimelineController,
    UIInitializationController,
    ViewManagementController,
)
```

**Status**: Will need updating to use consolidated controller names

---

## Protocol Definitions

### Controller Protocols

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/protocols/controller_protocols.py`

**Relevant Protocols**:
- `MultiPointTrackingProtocol` - Used for type annotation
- `ViewManagementProtocol` - Used for type annotation

**Status**: Protocols may need updating or new protocols created

---

## Test Files Affected

### Direct Controller Tests

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_multi_point_selection_signals.py`

**Test Methods Using Sub-controllers**:
- Search for: `controller.display_controller`
- Search for: `controller.data_controller`
- Count: 8+ direct accesses

**Breaking Change**: Will fail if sub-controller properties removed

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_multi_point_selection.py`

**Test Methods**:
- Uses `tracking_selection_controller` patches
- May reference sub-controllers

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_main_window_characterization.py`

**Comments**:
- Search for: "display_controller", "data_controller"
- May reference consolidation expectations

### Integration Tests

**General Test Pattern**:
- MainWindow tests may instantiate tracking_controller
- View-related tests may use view_management_controller
- All controller instantiation patterns need review

---

## Signal Connection Points

### MultiPointTrackingController Signal Connections

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/multi_point_tracking_controller.py`

**Signal Connection Block**:
```
Lines 70-83: _connect_sub_controllers() method
```

**Signals Connected**:
```
Line 74: data_controller.data_loaded → display_controller.on_data_loaded
Line 75: data_controller.data_loaded → selection_controller.on_data_loaded
Line 76: data_controller.data_changed → display_controller.on_data_changed
```

**Impact**: These connections must be maintained in merged TrackingController

---

## Configuration/Documentation Files

### CLAUDE.md

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/CLAUDE.md`

**Sections to Update**:
- Controller documentation
- Architecture overview
- Common patterns

**Status**: Will need updating to document new consolidated controllers

### PHASE_2_PLAN.md

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/PHASE_2_PLAN.md`

**Sections Referencing Controllers**:
- Task 1: Tracking controller consolidation (detailed plan)
- Task 2: View controller consolidation (detailed plan)
- Task 3: SessionManager integration
- Testing strategy
- Rollback strategy

**Status**: Plan is good high-level overview but lacks API details

---

## Files NOT Requiring Changes (Keep As-Is)

These controllers are well-separated and should NOT be consolidated:

- `action_handler_controller.py` - Menu/toolbar actions only
- `ui_initialization_controller.py` - UI setup only
- `signal_connection_manager.py` - Signal wiring only
- `timeline_controller.py` - Timeline/playback only
- `multi_point_tracking_controller.py` - Already a coordinator (may become main tracking controller)
- `point_editor_controller.py` - Point editing only
- `frame_change_coordinator.py` - Frame change coordination only

---

## Summary of Changes

### Files to Delete (After Consolidation)
- `ui/controllers/tracking_data_controller.py`
- `ui/controllers/tracking_display_controller.py`
- `ui/controllers/tracking_selection_controller.py`
- `ui/controllers/view_management_controller.py`
- `ui/controllers/view_camera_controller.py`

### Files to Create
- `ui/controllers/tracking_controller.py` (merged from 4 files)
- `ui/controllers/viewport_controller.py` (merged from 2 files)

### Files to Modify
- `ui/main_window.py` (4+ property/method accesses)
- `ui/controllers/__init__.py` (exports)
- `tests/test_multi_point_selection_signals.py` (if sub-controllers removed)
- `CLAUDE.md` (documentation)

### Files to Leave Unchanged
- All other controllers
- All other test files (should pass without changes if consolidation done correctly)
- All service files

---

## Quick Reference: Line Number Index

### Tracking Controllers
- TrackingDataController: Lines 22-397 of tracking_data_controller.py
- TrackingDisplayController: Lines 42-449 of tracking_display_controller.py
- TrackingSelectionController: Lines 17-216 of tracking_selection_controller.py
- MultiPointTrackingController: Lines 35-306 of multi_point_tracking_controller.py

### View Controllers
- ViewManagementController: Lines 41-475 of view_management_controller.py
- ViewCameraController: Lines 69-561 of view_camera_controller.py

### MainWindow References
- Controller properties: Lines 177-185 of main_window.py
- Controller instantiation: Lines 233-244 of main_window.py
- Tracking calls: Lines 668-999 (distributed)
- View calls: Lines 301, 554, 560, 1077

### Test References
- Multi-point selection tests: test_multi_point_selection_signals.py (lines ~40-70)

---

**End of Code Location Reference**

Report Generated: 2025-10-24
Status: READY FOR IMPLEMENTATION PLANNING
