# PLAN GAMMA - PHASES 4-8: DETAILED IMPLEMENTATION GUIDE
## Continuation of Refactoring Plan

### Overview
This document contains Phases 4-8 of the CurveEditor refactoring.
Total expected reduction: ~4,000 lines of code
Timeline: Days 8-15

---

## PHASE 4: CONTROLLER CONSOLIDATION (Days 8-10)
### Reduce from 13 controllers to 3

#### 4.1 Current Controller Analysis

**Current Controllers** (13 total, ~140KB):
```
EventCoordinator.py              # 9.6KB - Event routing
EventFilterController.py         # 2.5KB - Event filtering (MERGE)
FileOperationsManager.py         # 38KB  - File operations (LARGEST)
FrameNavigationController.py     # 9.6KB - Frame navigation
PlaybackController.py            # 9.6KB - Playback control
PointEditController.py          # 14KB  - Point editing
SmoothingController.py          # 5.1KB - Smoothing dialog (MERGE)
StateChangeController.py        # 5.8KB - State updates (MERGE)
TimelineController.py           # 3.6KB - Timeline ops (MERGE)
TrackingPanelController.py      # 8.9KB - Tracking panel
ViewUpdateManager.py            # 22.6KB - View updates
ZoomController.py               # 10.8KB - Zoom operations
```

#### 4.2 Consolidation Strategy

##### 4.2.1 Create DataController
**Merge**: FileOperationsManager + file-related operations
```python
# controllers/data_controller.py (~40KB)
class DataController:
    """Consolidated data operations controller."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.file_io = get_file_io_service()
        self.data_analysis = get_data_analysis_service()

    # From FileOperationsManager:
    def load_curve_file(self, filepath: str): ...
    def save_curve_file(self, filepath: str): ...
    def load_image_sequence(self, path: str): ...

    # Thread management
    def _load_in_background(self, filepath: str): ...
```

##### 4.2.2 Create ViewController
**Merge**: ViewUpdateManager + ZoomController + FrameNavigationController
```python
# controllers/view_controller.py (~35KB)
class ViewController:
    """Consolidated view management controller."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.transform_core = get_transform_core()

    # From ViewUpdateManager:
    def update_view_state(self): ...
    def refresh_display(self): ...

    # From ZoomController:
    def zoom_in(self): ...
    def zoom_out(self): ...
    def fit_to_window(self): ...

    # From FrameNavigationController:
    def navigate_to_frame(self, frame: int): ...
    def next_frame(self): ...
    def previous_frame(self): ...
```

##### 4.2.3 Create InteractionController
**Merge**: Remaining interaction controllers
```python
# controllers/interaction_controller.py (~30KB)
class InteractionController:
    """Consolidated user interaction controller."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.interaction_service = get_interaction_service()

    # From PointEditController:
    def edit_point(self, index: int): ...
    def delete_point(self, index: int): ...

    # From TrackingPanelController:
    def update_tracking_panel(self): ...

    # From PlaybackController:
    def play(self): ...
    def pause(self): ...
    def stop(self): ...

    # Merged small controllers:
    def apply_smoothing(self): ...  # From SmoothingController
    def filter_events(self, event): ...  # From EventFilterController
```

#### 4.3 Remove Micro-Controllers

**Delete these files**:
```bash
rm controllers/event_filter_controller.py      # Move to InteractionController
rm controllers/smoothing_controller.py         # Move to InteractionController
rm controllers/state_change_controller.py      # Move to ViewController
rm controllers/timeline_controller.py          # Move to ViewController
```

#### 4.4 Update MainWindow Integration

**ui/modernized_main_window.py**:
```python
# Before:
from controllers import (
    EventCoordinator, FileOperationsManager,
    FrameNavigationController, PlaybackController,
    # ... 10 more imports
)

class MainWindow:
    def __init__(self):
        self.event_coordinator = EventCoordinator(self)
        self.file_manager = FileOperationsManager(self)
        # ... 11 more controller instances

# After:
from controllers import DataController, ViewController, InteractionController

class MainWindow:
    def __init__(self):
        self.data_controller = DataController(self)
        self.view_controller = ViewController(self)
        self.interaction_controller = InteractionController(self)
```

#### Phase 4 Verification Checklist
- [ ] 3 consolidated controllers created
- [ ] 10 micro-controllers removed
- [ ] MainWindow updated to use new controllers
- [ ] All controller methods migrated
- [ ] Run tests: `python -m pytest tests/test_controller*.py`
- [ ] Type check: `./bpr controllers/`

**Expected reduction**: ~1,200 lines

---

## PHASE 5: VALIDATION SIMPLIFICATION (Day 11)
### Replace 659-line abstraction with utilities

#### 5.1 Delete Complex Validation System

**Remove files**:
```bash
rm core/validation_strategy.py      # 659 lines
rm core/y_flip_strategy.py         # ~100 lines
```

#### 5.2 Create Simple Validation Utilities

**core/validation_utils.py** (~50 lines total):
```python
"""Simple validation utilities."""
import math
from typing import TypeGuard, Tuple

def is_valid_coordinate(
    x: object,
    y: object
) -> TypeGuard[Tuple[float, float]]:
    """Runtime type guard for coordinates."""
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return False
    return math.isfinite(x) and math.isfinite(y)

def ensure_valid_scale(scale: float, min_val: float = 1e-10) -> float:
    """Ensure scale is valid, return safe default if not."""
    if not isinstance(scale, (int, float)):
        return 1.0
    if math.isfinite(scale) and scale > 0:
        return max(scale, min_val)
    return 1.0

def ensure_positive_dimensions(
    width: float,
    height: float
) -> Tuple[float, float]:
    """Ensure dimensions are positive."""
    safe_width = abs(width) if width != 0 else 1.0
    safe_height = abs(height) if height != 0 else 1.0
    return safe_width, safe_height

def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range."""
    return max(min_val, min(max_val, value))

def sanitize_point_data(points: list) -> list:
    """Ensure all points have valid coordinates."""
    valid_points = []
    for point in points:
        if hasattr(point, 'x') and hasattr(point, 'y'):
            if is_valid_coordinate(point.x, point.y):
                valid_points.append(point)
    return valid_points
```

#### 5.3 Update Service Usage

**Replace validation strategy usage**:
```python
# Before (in TransformService):
from core.validation_strategy import get_validation_strategy

class TransformService:
    def __init__(self):
        self.validation = get_validation_strategy("adaptive")
        self.validation.set_context(is_render_loop=True)

    def transform(self, x, y):
        if self.validation.should_validate():
            x, y = self.validation.validate_coordinates(x, y)
        # ... complex logic

# After (in transform_core.py):
from core.validation_utils import is_valid_coordinate, ensure_valid_scale

class TransformCore:
    def transform(self, x, y):
        if not is_valid_coordinate(x, y):
            return 0.0, 0.0  # Simple fallback
        # ... simplified logic
```

#### Phase 5 Verification Checklist
- [ ] Complex validation files removed
- [ ] Simple utilities created
- [ ] All validation callsites updated
- [ ] Type errors fixed (5 known issues)
- [ ] Run tests: `python -m pytest tests/test_validation*.py`
- [ ] Type check: `./bpr core/`

**Expected reduction**: ~600 lines

---

## PHASE 6: MAINWINDOW MERGE (Day 12)
### Consolidate dual implementations

#### 6.1 Analyze Differences

**Compare implementations**:
```bash
# Generate diff report
diff -u ui/main_window.py ui/modernized_main_window.py > mainwindow_diff.txt
```

**Key differences to preserve**:
- Modernized: Better theme support
- Modernized: Animation framework
- Original: Some legacy compatibility code

#### 6.2 Migration Strategy

1. **Backup original**:
```bash
cp ui/main_window.py ui/main_window_legacy.py.archive
```

2. **Extract unique features from original**:
```python
# Features to migrate:
# - Legacy file format support (if any)
# - Specific keyboard shortcuts
# - Custom dialogs
```

3. **Merge into modernized**:
```python
# ui/modernized_main_window.py
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Add migrated features here
        self._setup_legacy_support()  # New method
```

4. **Replace original**:
```bash
rm ui/main_window.py
mv ui/modernized_main_window.py ui/main_window.py
```

#### 6.3 Update All Imports

```bash
# Find and replace all imports
grep -r "from ui.modernized_main_window import" --include="*.py" | \
  xargs sed -i 's/modernized_main_window/main_window/g'
```

#### Phase 6 Verification Checklist
- [ ] Features extracted from original
- [ ] Modernized version enhanced
- [ ] Original deleted
- [ ] Modernized renamed to main_window.py
- [ ] All imports updated
- [ ] Run tests: `python -m pytest tests/test_main_window*.py`
- [ ] UI smoke test: `python main.py`

**Expected reduction**: ~576 lines

---

## PHASE 7: COORDINATE SYSTEM CONSOLIDATION (Day 13)
### Merge 4 files into 1

#### 7.1 Files to Merge

**Current structure**:
```
core/coordinate_detector.py    # ~150 lines
core/coordinate_system.py      # ~100 lines
core/coordinate_types.py       # ~50 lines
core/y_flip_strategy.py        # ~100 lines
```

#### 7.2 Create Unified Module

**core/coordinate_transforms.py** (~250 lines after dedup):
```python
"""Unified coordinate transformation module."""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple

# From coordinate_types.py
@dataclass
class CoordinateSpace:
    """Coordinate space definition."""
    origin: Tuple[float, float]
    y_up: bool
    normalized: bool

# From coordinate_system.py
class CoordinateSystem(Enum):
    """Supported coordinate systems."""
    THREEDE_EQUALIZER = "3de"
    MAYA = "maya"
    NUKE = "nuke"
    STANDARD = "standard"

# From coordinate_detector.py
class CoordinateDetector:
    """Auto-detect coordinate system from file."""

    @staticmethod
    def detect_from_file(filepath: str) -> CoordinateSystem:
        """Detect coordinate system from file format."""
        # Detection logic here
        pass

# From y_flip_strategy.py (simplified)
class CoordinateTransform:
    """Handle coordinate transformations."""

    def __init__(self, system: CoordinateSystem):
        self.system = system
        self.y_flip = system in [CoordinateSystem.THREEDE_EQUALIZER]

    def transform(self, x: float, y: float, height: float) -> Tuple[float, float]:
        """Apply coordinate transformation."""
        if self.y_flip:
            y = height - y
        return x, y
```

#### 7.3 Remove Old Files

```bash
rm core/coordinate_detector.py
rm core/coordinate_system.py
rm core/coordinate_types.py
rm core/y_flip_strategy.py
```

#### 7.4 Update Imports

```python
# Before:
from core.coordinate_detector import CoordinateDetector
from core.coordinate_system import CoordinateSystem
from core.y_flip_strategy import YFlipStrategy

# After:
from core.coordinate_transforms import (
    CoordinateDetector,
    CoordinateSystem,
    CoordinateTransform
)
```

#### Phase 7 Verification Checklist
- [ ] Unified module created
- [ ] All classes/functions migrated
- [ ] Old files removed
- [ ] All imports updated
- [ ] Run tests: `python -m pytest tests/test_coordinate*.py`
- [ ] Type check: `./bpr core/`

**Expected reduction**: ~150 lines through deduplication

---

## PHASE 8: TEST CONSOLIDATION (Days 14-15)
### Reduce from 65+ to ~30 test files

#### 8.1 Test File Mapping

**Cache tests** (merge 3 → 1):
```bash
# Merge into tests/test_cache.py:
cat tests/test_cache_performance.py >> tests/test_cache.py
cat tests/test_quantized_cache_critical.py >> tests/test_cache.py
cat tests/benchmark_cache.py >> tests/test_cache.py

# Remove originals:
rm tests/test_cache_performance.py
rm tests/test_quantized_cache_critical.py
rm tests/benchmark_cache.py
```

**Integration tests** (merge 3 → 1):
```bash
# Merge into tests/test_integration.py:
cat tests/test_integration_real.py >> tests/test_integration.py
cat tests/test_controller_integration.py >> tests/test_integration.py

# Remove originals:
rm tests/test_integration_real.py
rm tests/test_controller_integration.py
```

**UI tests** (merge 5 → 2):
```bash
# Merge MainWindow tests:
cat tests/test_main_window_critical.py >> tests/test_main_window.py
cat tests/test_main_window_characterization.py >> tests/test_main_window.py
cat tests/test_main_window_threading_integration.py >> tests/test_main_window.py

# Keep separate:
# tests/test_curve_view.py
# tests/test_ui_components.py
```

#### 8.2 Remove Obsolete Tests

**Delete tests for removed code**:
```bash
# Tests for deleted controllers:
rm tests/test_event_filter_controller.py
rm tests/test_smoothing_controller.py
rm tests/test_state_change_controller.py
rm tests/test_timeline_controller.py

# Tests for deleted validation:
rm tests/test_validation_strategy.py
rm tests/test_y_flip_strategy.py
```

#### 8.3 Consolidation Summary

**Final test structure** (~30 files):
```
tests/
├── test_cache.py               # All cache tests
├── test_controllers.py         # 3 consolidated controllers
├── test_coordinate_transforms.py # Unified coordinate tests
├── test_data_service.py        # Data operations
├── test_integration.py         # All integration tests
├── test_main_window.py         # MainWindow tests
├── test_services.py            # Service tests
├── test_transforms.py          # Transform tests
├── test_ui_components.py       # UI component tests
└── ... (~20 more focused test files)
```

#### Phase 8 Verification Checklist
- [ ] Similar tests merged
- [ ] Obsolete tests removed
- [ ] Test count reduced to ~30
- [ ] All tests passing
- [ ] Coverage maintained: `pytest --cov=. tests/`
- [ ] No duplicate test names

**Expected reduction**: ~2,000 lines of test code

---

## FINAL METRICS AND VALIDATION

### Cumulative Impact (All Phases)
- **Production Code**: 8,365 → ~1,550 lines (81% reduction)
- **Test Code**: ~5,000 → ~2,500 lines (50% reduction)
- **Total Files**: 180+ → ~80 files (55% reduction)
- **Services**: 4 monoliths → 7 focused services
- **Controllers**: 13 → 3 consolidated
- **Protocols**: 82 scattered → ~20 centralized

### Final Validation Suite
```bash
# Complete validation script
#!/bin/bash
echo "Running final validation..."

# 1. Syntax check
python3 -m py_compile **/*.py

# 2. Type checking
./bpr

# 3. Linting
ruff check . --fix

# 4. Tests
python -m pytest tests/ -v

# 5. Coverage
pytest --cov=. --cov-report=html tests/

# 6. Performance benchmark
python tools/profiling/benchmark.py

echo "Validation complete!"
```

### Success Criteria
- [ ] All tests passing
- [ ] Type check clean (except Qt warnings)
- [ ] Linting clean
- [ ] Coverage ≥ 80%
- [ ] Performance improved by 15-20%
- [ ] Application runs without errors

### Rollback Plan
If critical issues arise:
1. `git tag pre-refactor` (before starting)
2. `git reset --hard pre-refactor` (if needed)
3. Review issues and adjust approach
4. Re-attempt with modifications

### Post-Refactoring Tasks
1. Update CLAUDE.md with new architecture
2. Create architecture diagram
3. Document new service boundaries
4. Update onboarding documentation
5. Performance profiling report

---

## Timeline Summary
- **Week 1** (Days 1-5): Phases 1-3 (Quick wins, protocols, service split)
- **Week 2** (Days 6-10): Phases 4-5 (Controllers, validation)
- **Week 3** (Days 11-15): Phases 6-8 (MainWindow, coordinates, tests)

Total: 15 working days (3 weeks)
