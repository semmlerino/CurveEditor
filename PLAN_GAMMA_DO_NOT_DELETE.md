# PLAN GAMMA - PHASES 1-3: DETAILED IMPLEMENTATION GUIDE
## DO NOT DELETE - ACTIVE REFACTORING PLAN

### Overview
This document contains exhaustive implementation details for Phases 1-3 of the CurveEditor refactoring.
Total expected reduction: ~2,200 lines of code
Timeline: Days 1-7

---

## PHASE 1: QUICK WINS (Day 1)
### Zero-risk cleanup for immediate impact

#### 1.1 Remove Duplicate Service Getter
**File**: `services/data_service.py`
**Lines**: 944-949
**Action**: DELETE these lines

```python
# REMOVE THIS DUPLICATE (lines 944-949):
def get_data_service() -> DataService:
    """Get the singleton DataService instance."""
    global _data_service_instance
    if _data_service_instance is None:
        _data_service_instance = DataService()
    return _data_service_instance
```

**Verification**:
```bash
# Ensure only one get_data_service exists
grep -r "def get_data_service" services/
# Should only show: services/__init__.py
```

#### 1.2 Delete Backup Files
**Files to remove**:
```bash
rm services/transform_service.py.backup
rm ui/curve_view_widget.py.backup
rm controllers/file_operations_manager.py.backup
rm core/curve_data.py.backup
```

**Verification**:
```bash
find . -name "*.backup" -type f
# Should return empty
```

#### 1.3 Move Profiling Tools
**Create directory and relocate**:
```bash
# Create tools directory
mkdir -p tools/profiling

# Move profiling files
mv profiling/cache_analysis.py tools/profiling/
mv profiling/cache_profiler.py tools/profiling/
mv profiling/zoom_cache_performance_fix.py tools/profiling/
mv profiling/zoom_cache_test.py tools/profiling/

# Remove old directory
rmdir profiling/
```

**Update imports in test files**:
```python
# Before:
from profiling.cache_profiler import CacheProfiler

# After:
from tools.profiling.cache_profiler import CacheProfiler
```

#### 1.4 Remove Obsolete Documentation
**Files to delete** (40+ markdown files):
```bash
# Sprint and report files
rm BACKGROUND_PANNING_FIX.md
rm BASEDPYRIGHT_IMPROVEMENT_REPORT.md
rm BASEDPYRIGHT_TYPESAFETY_AGENTREPORT.md
rm BEFORE_AFTER_EXAMPLE.md
rm COMMIT_READY.md
rm CRITICAL_FIX_RUNTIME.md
rm DOCUMENTATION_COMPLIANCE_AUDIT.md
rm DUPLICATE_CODE_ANALYSIS.md
rm EMERGENCY_QUALITY_RECOVERY_SPRINT.md
rm HASATTR_REFACTOR_SUMMARY.md
rm INTEGRATION_GAPS.md
rm INTERACTION_SERVICE_REFACTOR.md
rm LINTING_RESULTS.md
rm MAIN_WINDOW_REFACTOR.md
rm NEXT_PHASE_DECISION_MATRIX.md
rm NEXT_STEPS_COMPREHENSIVE_PLAN.md
rm NEXT_STEPS_PLAN.md
rm NEXT_STEPS_PLAN_FINAL.md
rm PATH_FORWARD_DECISION_MATRIX.md
rm PHASE_1_2_COMPLETION_REPORT.md
rm PHASE_2_COMPLETION_REPORT.md
rm PHASE_2_TYPE_SAFETY_PLAN.md
rm PHASE_2_WEEK1_SUMMARY.md
rm PHASE_2_WEEK2_PROGRESS.md
rm PHASE_2_WEEK3_SUMMARY.md
rm QUALITY_METRICS_COMPARISON.md
rm QUALITY_TRIAGE_MATRIX.md
rm QUICK_WINS_PROGRESS.md
rm READY_FOR_NEXT_STEPS.md
rm REFACTORING_PLAN.md
rm RELEASE_NOTES_SPRINT11.md
rm REMEDIATION_PLAN.md
rm STRICT_TYPESAFETY_REPORT.md
rm TYPESAFETY_FINAL_REPORT.md
rm ZOOM_SYNC_FIX.md
rm WEEK1_SPRINT_COMPLETION_REPORT.md
rm TEST_SUITE_COMPLIANCE_REPORT.md
rm TEST_SUITE_FINAL_REPORT.md
rm TYPE_ERROR_FIX_REPORT.md
rm PROTECTED_MEMBER_REFACTORING.md
rm PERFORMANCE_OPTIMIZATIONS_SUMMARY.md
rm QT_THREADING_FIX_SUMMARY.md
rm LINTING_TYPECHECKING_AGENTREPORT.md
```

**Keep these files** (active documentation):
- CLAUDE.md
- README.md (if exists)
- docs/ directory contents
- PRODUCTION_DEPLOYMENT_CHECKLIST.md
- PLAN_GAMMA_DO_NOT_DELETE.md
- PLAN_GAMMA_PHASES_4-8.md

#### Phase 1 Verification Checklist
- [ ] Duplicate service getter removed
- [ ] All .backup files deleted
- [ ] Profiling tools moved to /tools
- [ ] Obsolete markdown files removed
- [ ] Run tests: `python -m pytest tests/`
- [ ] Type check: `./bpr`
- [ ] Lint: `ruff check . --fix`

**Expected reduction**: ~500 lines + 40 files removed

---

## PHASE 2: PROTOCOL CONSOLIDATION (Days 2-3)
### Create single source of truth for all protocols

#### 2.1 Create Protocol Directory Structure
```bash
mkdir -p protocols
touch protocols/__init__.py
touch protocols/ui.py
touch protocols/services.py
touch protocols/data.py
```

#### 2.2 Identify and Map Current Protocols

**Files containing Protocol definitions** (31 files, 82 protocols):
```python
# Main locations:
services/service_protocols.py  # Primary service protocols
ui/main_window.py              # MainWindowProtocol (1 of 6)
ui/modernized_main_window.py   # MainWindowProtocol (2 of 6)
ui/curve_view_widget.py        # CurveViewProtocol (1 of 3)
controllers/*.py                # Various controller protocols
tests/fixtures/*.py             # Test protocols
```

**Protocol mapping to new structure**:

##### protocols/ui.py
```python
from typing import Protocol, Optional, Any
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

class MainWindowProtocol(Protocol):
    """Unified MainWindow interface."""
    # Core properties
    current_frame: int
    total_frames: int
    curve_view: 'CurveViewProtocol'

    # UI elements
    timeline_slider: QWidget
    frame_spin: QWidget
    status_bar: QWidget

    # Methods
    def update_timeline(self, frame: int) -> None: ...
    def set_curve_data(self, data: list) -> None: ...
    def show_error(self, message: str) -> None: ...

class CurveViewProtocol(Protocol):
    """Focused curve view interface."""
    # Rendering
    def update(self) -> None: ...
    def repaint(self) -> None: ...
    def width(self) -> int: ...
    def height(self) -> int: ...

    # Data
    curve_data: list
    points: list

    # Interaction
    selected_point_idx: int
    drag_active: bool

    # Transform
    zoom_factor: float
    offset_x: float
    offset_y: float
```

##### protocols/services.py
```python
from typing import Protocol, Optional, Any

class ServiceProtocol(Protocol):
    """Base service interface."""
    def initialize(self) -> None: ...
    def cleanup(self) -> None: ...
    def get_status(self) -> dict: ...

class TransformServiceProtocol(Protocol):
    """Transform service interface."""
    def transform_to_scene(self, x: float, y: float) -> tuple[float, float]: ...
    def transform_to_view(self, x: float, y: float) -> tuple[float, float]: ...
    def get_scale(self) -> float: ...
    def set_scale(self, scale: float) -> None: ...

class DataServiceProtocol(Protocol):
    """Data service interface."""
    def load_curve_data(self, filepath: str) -> list: ...
    def save_curve_data(self, filepath: str, data: list) -> bool: ...
    def analyze_data(self, data: list) -> dict: ...

class InteractionServiceProtocol(Protocol):
    """Interaction service interface."""
    def handle_click(self, x: float, y: float) -> None: ...
    def handle_drag(self, dx: float, dy: float) -> None: ...
    def select_point(self, index: int) -> None: ...
```

##### protocols/data.py
```python
from typing import Protocol
from dataclasses import dataclass

class CurvePointProtocol(Protocol):
    """Curve point interface."""
    frame: int
    x: float
    y: float
    status: str

class StateProtocol(Protocol):
    """Application state interface."""
    def save_state(self) -> dict: ...
    def restore_state(self, state: dict) -> None: ...

class CurveDataProtocol(Protocol):
    """Curve data container interface."""
    points: list
    frame_range: tuple[int, int]
    def get_point_at_frame(self, frame: int) -> Optional[CurvePointProtocol]: ...
```

#### 2.3 Migration Script

**Create migration helper** (`tools/migrate_protocols.py`):
```python
#!/usr/bin/env python3
import os
import re
from pathlib import Path

def update_imports(file_path: Path):
    """Update protocol imports in a file."""
    content = file_path.read_text()

    # Map old imports to new
    replacements = [
        (r'from services.service_protocols import (\w+Protocol)',
         r'from protocols.services import \1'),
        (r'from ui.main_window import MainWindowProtocol',
         r'from protocols.ui import MainWindowProtocol'),
        (r'from ui.modernized_main_window import MainWindowProtocol',
         r'from protocols.ui import MainWindowProtocol'),
        (r'from ui.curve_view_widget import CurveViewProtocol',
         r'from protocols.ui import CurveViewProtocol'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    file_path.write_text(content)

# Run on all Python files
for file in Path('.').rglob('*.py'):
    if 'protocols/' not in str(file):
        update_imports(file)
```

#### 2.4 Remove Old Protocol Definitions

**Files to clean**:
1. Remove protocol definitions from original files
2. Keep only implementations
3. Update TYPE_CHECKING blocks

**Example cleanup**:
```python
# Before (ui/main_window.py):
from typing import Protocol

class MainWindowProtocol(Protocol):
    # ... 50 lines of protocol definition
    pass

class MainWindow(QMainWindow):
    # ... implementation

# After:
from protocols.ui import MainWindowProtocol

class MainWindow(QMainWindow):
    # ... implementation only
```

#### Phase 2 Verification Checklist
- [ ] protocols/ directory created
- [ ] All protocols migrated (82 total)
- [ ] Duplicate protocols merged
- [ ] All imports updated
- [ ] Old protocol definitions removed
- [ ] Run tests: `python -m pytest tests/`
- [ ] Type check: `./bpr`
- [ ] Verify no protocol imports from old locations:
  ```bash
  grep -r "from.*Protocol" --include="*.py" | grep -v "from protocols"
  ```

**Expected reduction**: ~800 lines

---

## PHASE 3: SPLIT MONOLITHIC SERVICES (Days 4-7)
### Break down god objects into focused modules

#### 3.1 Split TransformService (1,556 lines → ~900 lines)

##### 3.1.1 Create New Service Files
```bash
touch services/transform_core.py      # ~400 lines
touch services/coordinate_service.py  # ~300 lines
touch services/cache_service.py        # ~200 lines
```

##### 3.1.2 Method Distribution

**services/transform_core.py** (Core transformation math):
```python
"""Core transformation operations."""
from dataclasses import dataclass
import numpy as np
from typing import Optional, Tuple

@dataclass
class Transform:
    """Simple transform without validation complexity."""
    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def to_scene(self, x: float, y: float) -> Tuple[float, float]:
        """Transform view coordinates to scene."""
        scene_x = (x - self.offset_x) / self.scale
        scene_y = (y - self.offset_y) / self.scale
        return scene_x, scene_y

    def to_view(self, x: float, y: float) -> Tuple[float, float]:
        """Transform scene coordinates to view."""
        view_x = x * self.scale + self.offset_x
        view_y = y * self.scale + self.offset_y
        return view_x, view_y

class TransformCore:
    """Core transformation service."""

    def __init__(self):
        self._transform = Transform()

    # Methods to move from TransformService:
    # - transform_to_scene()
    # - transform_to_view()
    # - compute_scale()
    # - compute_offset()
    # - apply_transform()
    # - inverse_transform()
    # - compose_transforms()
```

**services/coordinate_service.py** (Coordinate system handling):
```python
"""Coordinate system detection and conversion."""
from enum import Enum
from typing import Tuple, Optional

class CoordinateSystem(Enum):
    """Supported coordinate systems."""
    THREEDE_EQUALIZER = "3de"
    MAYA = "maya"
    NUKE = "nuke"
    STANDARD = "standard"

class CoordinateService:
    """Handle coordinate system operations."""

    def __init__(self):
        self._current_system = CoordinateSystem.STANDARD

    # Methods to move from TransformService:
    # - detect_coordinate_system()
    # - convert_coordinates()
    # - apply_y_flip()
    # - normalize_coordinates()
    # - denormalize_coordinates()
    # - get_coordinate_bounds()
```

**services/cache_service.py** (Simplified caching):
```python
"""Simplified caching service."""
from functools import lru_cache
from typing import Optional, Dict, Any

class CacheService:
    """Handle transform caching."""

    def __init__(self):
        self._cache_hits = 0
        self._cache_misses = 0
        self._transform_cache: Dict[str, Any] = {}

    @lru_cache(maxsize=128)
    def get_cached_transform(self, key: str) -> Optional[object]:
        """Simple hash-based caching."""
        # Simplified from complex quantization
        return self._transform_cache.get(key)

    # Methods to move from TransformService:
    # - _create_cache_key() [simplified]
    # - clear_cache()
    # - get_cache_stats()
```

##### 3.1.3 Update Service Registry

**services/__init__.py**:
```python
# Add new service instances
_transform_core_instance = None
_coordinate_service_instance = None
_cache_service_instance = None

def get_transform_core() -> TransformCore:
    global _transform_core_instance
    if _transform_core_instance is None:
        from services.transform_core import TransformCore
        _transform_core_instance = TransformCore()
    return _transform_core_instance

def get_coordinate_service() -> CoordinateService:
    global _coordinate_service_instance
    if _coordinate_service_instance is None:
        from services.coordinate_service import CoordinateService
        _coordinate_service_instance = CoordinateService()
    return _coordinate_service_instance

def get_cache_service() -> CacheService:
    global _cache_service_instance
    if _cache_service_instance is None:
        from services.cache_service import CacheService
        _cache_service_instance = CacheService()
    return _cache_service_instance

# Update TransformService to delegate
class TransformService:
    """Facade for transform operations."""
    def __init__(self):
        self.core = get_transform_core()
        self.coordinates = get_coordinate_service()
        self.cache = get_cache_service()
```

#### 3.2 Split DataService (950 lines → ~650 lines)

##### 3.2.1 Create New Service Files
```bash
touch services/data_analysis.py   # ~200 lines
touch services/file_io_service.py # ~300 lines
touch services/image_service.py   # ~150 lines
```

##### 3.2.2 Method Distribution

**services/data_analysis.py**:
```python
"""Data analysis operations."""
import numpy as np
from typing import List, Dict, Any

class DataAnalysisService:
    """Handle data analysis operations."""

    # Methods to move from DataService:
    # - smooth_curve_data()
    # - detect_outliers()
    # - compute_statistics()
    # - filter_noise()
    # - interpolate_missing()
    # - resample_data()
```

**services/file_io_service.py**:
```python
"""File I/O operations."""
import json
from pathlib import Path
from typing import List, Dict, Any

class FileIOService:
    """Handle file operations."""

    # Methods to move from DataService:
    # - load_curve_file()
    # - save_curve_file()
    # - load_3de_data()
    # - load_maya_data()
    # - export_to_format()
    # - validate_file_format()
```

**services/image_service.py**:
```python
"""Image sequence handling."""
from pathlib import Path
from typing import List, Optional

class ImageService:
    """Handle image sequence operations."""

    # Methods to move from DataService:
    # - load_image_sequence()
    # - get_frame_image()
    # - cache_images()
    # - clear_image_cache()
    # - detect_sequence_pattern()
```

#### 3.3 Update Import Statements

**Migration pattern for all files**:
```python
# Before:
from services import get_transform_service
transform_service = get_transform_service()
result = transform_service.transform_to_scene(x, y)

# After:
from services import get_transform_core
transform_core = get_transform_core()
result = transform_core.to_scene(x, y)
```

#### Phase 3 Verification Checklist
- [ ] New service files created (6 total)
- [ ] Methods distributed correctly
- [ ] Service registry updated
- [ ] All imports updated
- [ ] Old monolithic services refactored
- [ ] Run tests: `python -m pytest tests/`
- [ ] Type check: `./bpr`
- [ ] Verify service sizes:
  ```bash
  wc -l services/*.py | sort -n
  ```

**Expected reduction**: ~900 lines through deduplication

### Success Metrics for Phases 1-3
- Total lines removed: ~2,200
- Files consolidated: 46 files removed/merged
- Services split: 2 monoliths → 6 focused services
- Protocols centralized: 82 → ~20 unique protocols
- Type errors fixed: 5 in validation_strategy.py

### Rollback Procedure
If any phase fails:
1. `git stash` current changes
2. `git checkout .` to revert
3. Review failure cause
4. Adjust plan and retry

### Next Steps
Continue with PLAN_GAMMA_PHASES_4-8.md for:
- Phase 4: Controller Consolidation
- Phase 5: Validation Simplification
- Phase 6: MainWindow Merge
- Phase 7: Coordinate System Consolidation
- Phase 8: Test Consolidation
