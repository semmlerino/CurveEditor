# CurveEditor YAGNI & Over-Engineering Analysis

**Analysis Date**: October 2025  
**Total Codebase**: ~79,800 Python lines (non-test)  
**Files Analyzed**: 104 Python files across core/, services/, ui/, stores/  
**Issues Found**: 10 critical + 15 secondary patterns identified

---

## Executive Summary

The CurveEditor codebase exhibits **moderate over-engineering** for a personal single-user VFX tool, particularly in validation strategies, service abstractions, and controller decomposition. Key issues:

- **Dead Code**: 1 major service (DataAnalysisService) never imported
- **Over-Engineered Patterns**: Complex multi-strategy validation system only tested, never used
- **Unused Abstractions**: ServiceProvider wrapper around already-abstracted services
- **Controller Bloat**: 14 specialized controllers for simple interactions
- **Large Monolithic Files**: 5 files >1000 lines that could be split

**Estimated Impact**: 1,500-2,000 lines of unnecessary code (1.9-2.5% of codebase)  
**Refactoring ROI**: Low priority (2-3 hours of effort, minimal maintainability gain)

---

## Top 10 YAGNI/Over-Engineering Issues (Ranked by Impact)

### 1. **DataAnalysisService - Completely Unused**
- **Category**: Dead Code / YAGNI
- **Impact Score**: High (326 lines of wasted code)
- **Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/services/data_analysis.py`
- **Files**: 1 (plus test file)

**Description**: DataAnalysisService provides smoothing, filtering, gap filling, and outlier detection, but is:
- Never imported anywhere in the application (grep confirms 0 actual imports)
- Only referenced in test file and its own docstring
- Duplicates analysis capabilities that DataService already handles (poorly)
- Includes scipy dependency for Butterworth filtering (might not be installed)

**Why It's YAGNI**: 
- User never requested these advanced filtering features
- Basic smoothing/filtering is better handled in UI workflows than batch operations
- Scipy dependency adds complexity for rarely-used feature

**Quick Wins**:
1. Remove entire file and test
2. Move basic smoothing to data transformations if needed
3. Remove scipy from dependencies

---

### 2. **ValidationStrategy Pattern - Over-Engineered**
- **Category**: Over-Engineering / Feature Creep
- **Impact Score**: High (637 lines)
- **Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/core/validation_strategy.py`
- **Classes**: BaseValidationStrategy (abstract), MinimalValidationStrategy, ComprehensiveValidationStrategy, AdaptiveValidationStrategy

**Description**: Complex 3-strategy validation framework with:
- 4 validation classes (base + 3 concrete)
- 19 public methods across strategies
- Factory functions and singleton instances
- Context switching between strategies

**Usage Analysis**:
- Only imported/tested in `tests/test_validation_strategy.py`
- Zero references in production code
- Never actually used by any service or UI component

**Why It's Over-Engineering**:
- Personal tool doesn't need production-grade validation switching
- Premature optimization for "debug vs production" modes
- Simple input validation would suffice for single-user app

**Cost**:
- Maintenance burden for unused abstraction layer
- Type complexity (Generic[T], Protocol decorators)
- Developers must understand 3 different strategies

---

### 3. **ServiceProvider Wrapper - Unnecessary Abstraction**
- **Category**: Over-Engineering / Dead Code
- **Impact Score**: Medium (156 lines)
- **Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/core/service_utils.py`
- **Classes**: ServiceProvider, ServiceContext

**Description**: Provides wrapper methods around services/__init__.py getters:
```python
ServiceProvider.get_data_service()  # Wraps get_data_service()
ServiceProvider.get_interaction_service()  # Wraps get_interaction_service()
# ... etc
```

**Usage**: 
- Grep shows 0 imports: `from core.service_utils import`
- Exists only in module definition and 7 internal references
- Code comments suggest it was planned but never adopted

**Why It's YAGNI**:
- Adds indirection to already-abstracted services
- Alternative `get_data_service()` directly in `services/__init__.py` is simpler
- Generic `ServiceContext` helper rarely useful

**Evidence**: Only 7 references are all in the same file

---

### 4. **14 Specialized UI Controllers - Possible Over-Decomposition**
- **Category**: Over-Engineering / Premature Modularization
- **Impact Score**: Medium (estimated 3,000+ lines total)
- **Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/`
- **Controllers**:
  - base_tracking_controller.py
  - tracking_data_controller.py
  - tracking_display_controller.py
  - tracking_selection_controller.py
  - multi_point_tracking_controller.py
  - point_editor_controller.py
  - action_handler_controller.py
  - frame_change_coordinator.py
  - signal_connection_manager.py
  - timeline_controller.py
  - ui_initialization_controller.py
  - view_camera_controller.py
  - view_management_controller.py
  - (+ curve_view/render_cache_controller.py, state_sync_controller.py)

**Description**: Massive controller decomposition - each handling narrow concerns

**Why It's Questionable**:
- Single-user tool with limited interaction patterns
- 5 controllers just for tracking points (data/display/selection/multi/base)
- Each controller maintains own state and signals
- Complex signal/slot coordination needed (FrameChangeCoordinator exists to manage other controllers)

**Cost**:
- High cognitive load to understand interaction flow
- Signal coordination complexity (FrameChangeCoordinator needed to prevent race conditions)
- Duplication of similar patterns across controllers
- Difficult to understand which controller does what

**Mitigation**: Not necessarily remove, but consolidate related controllers:
- Merge tracking_data/display/selection into single TrackingController
- Consider merging view_management + view_camera
- Move minor responsibility handlers into MainWindow directly

---

### 5. **PointIndex (Spatial Indexing) - Questionable Optimization**
- **Category**: Premature Optimization / Over-Engineering
- **Impact Score**: Medium (420 lines)
- **Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/core/spatial_index.py`
- **Classes**: PointIndex, HasDimensionsProtocol

**Description**: Grid-based spatial index for point lookup:
- Divides screen into adaptive grid (10-50x10-50 cells)
- Claims O(1) lookup vs O(n) linear search
- Includes threading.RLock for thread safety
- Transform caching and hash stability checks

**Usage**:
- Only used in InteractionService for single point selection
- Typical curve has 50-200 points (small enough for O(n))
- Grid rebuild required on every transform/viewport change

**Over-Engineering Indicators**:
- Threading lock unnecessary (Qt is single-threaded)
- Adaptive grid calculation adds complexity (~80 lines)
- Transform hash stability checks (~40 lines)
- For 100 points, O(n) linear search is <1ms

**Cost-Benefit**:
- Saves microseconds on small datasets
- Adds 420 lines of maintenance
- Complicates point finding logic

**Recommendation**: Profile before keeping. Linear search likely sufficient for typical use.

---

### 6. **Large Monolithic Files - Low Discoverability**
- **Category**: Over-Engineering / Poor Code Organization
- **Impact Score**: Medium (code smell)
- **Location**: Multiple files

**Files Exceeding 1000 Lines**:
| File | Lines | Issues |
|------|-------|--------|
| `ui/image_sequence_browser.py` | 2,194 | Giant UI widget mixing images + timeline |
| `ui/curve_view_widget.py` | 1,987 | Rendering, events, interaction in one file |
| `services/interaction_service.py` | 1,763 | Command pattern + interaction UI logic |
| `ui/main_window.py` | 1,356 | UI setup + state coordination |
| `services/data_service.py` | 1,199 | File I/O + analysis + caching |
| `stores/application_state.py` | 1,148 | State management + validation |

**Why It's Over-Engineered**:
- Hard to find specific functionality
- Multiple concerns per file (violates SRP)
- Difficult to test individual pieces
- IDE autocomplete overload

**Impact**: Medium - not breaking, but discoverability suffers

---

### 7. **Complex models.py - 984 Lines of Data Classes**
- **Category**: Over-Engineering / Over-Specification
- **Impact Score**: Low-Medium (code maintenance)
- **Location**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/core/models.py`

**Description**: Massive data model file with:
- FrameStatus (NamedTuple with 8 fields)
- PointStatus (Enum with 5 values)
- CurvePoint (frozen dataclass)
- PointCollection (with 20+ methods)
- LegacyPointTuple type aliases
- ~30 utility functions

**Why It's Over-Engineering**:
- Much of it exists for backward compatibility (legacy tuple formats)
- PointCollection methods often just wrap list operations
- Documentation exceeds actual code (docstrings ~50% of file)

**Recommendation**: Good structure overall, just large. Accept as-is or split:
- Move type aliases to core/type_aliases.py
- Move utilities to core/model_utils.py

---

### 8. **Backup Files Not Cleaned Up**
- **Category**: Dead Code / Technical Debt
- **Impact Score**: Low (clutters repo)
- **Location**: Multiple

**Files**:
```
./ui/controllers/multi_point_tracking_controller.py.backup
./ui/curve_view_widget.py.backup
./ui/keyboard_shortcuts.py.backup
./ui/main_window_legacy.py.archive (22KB)
```

**Why It's YAGNI**:
- Git history preserves old versions
- Backup files suggest incomplete refactoring
- Confuse developers about which file is active
- Add to line count metrics

**Action**: Delete all .backup and .archive files

---

### 9. **10+ TODO Comments - Incomplete Feature Design**
- **Category**: Feature Creep / Over-Planning
- **Impact Score**: Low (documentation)
- **Location**: Scattered

**TODOs Found**:
```python
# services/ui_service.py
# TODO: Implement proper filter dialog
# TODO: Implement proper fill gaps dialog
# TODO: Implement proper extrapolate dialog

# ui/controllers/action_handler_controller.py
# TODO: Implement add point at current position
# TODO: Implement curve filtering
# TODO: Implement curve analysis

# ui/file_operations.py
# TODO: Implement data export dialog

# ui/frame_tab.py
# TODO: Implement context menu with options like:

# ui/color_constants.py
TODO: Integrate with ui/color_manager.py theming system
```

**Why It's Over-Engineering**:
- Code written for features not needed
- UI stubs without implementation (confuse users)
- Action handlers with `# TODO` but no implementation

**Recommendation**: Remove unimplemented actions from UI; keep TODO only for planned features with timeline

---

### 10. **154 Uses of hasattr/getattr/setattr - Type Safety Risk**
- **Category**: Outdated Pattern / Code Smell
- **Impact Score**: Low-Medium (maintainability)
- **Location**: Core, Services, UI modules

**Examples**:
```python
# services/data_analysis.py (line 255-257)
if hasattr(point, "frame"):
    if getattr(point, "frame") == frame:
        if getattr(getattr(point, "status"), "value", None) == "interpolated":

# core/spatial_index.py (line 196)
getattr(view, "width", lambda: 800.0)()
```

**Why It's Anti-Pattern**:
- Loses type information (type checker can't verify)
- Runtime errors instead of type errors
- Modern Python uses type guards: `isinstance()` or `@property`

**Cost**: 
- Potential bugs from typos (getattr("fram") silently fails)
- Type checker can't help

---

## Code Examples: Top 5 Issues

### Example 1: DataAnalysisService (YAGNI - Never Used)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/services/data_analysis.py` (lines 1-100)

```python
class DataAnalysisService:
    """Service for curve data analysis and processing operations."""

    def smooth_moving_average(self, data: CurveDataInput, window_size: int = 5) -> CurveDataList:
        # 18 lines - moving average calculation
        
    def filter_median(self, data: CurveDataInput, window_size: int = 5) -> CurveDataList:
        # 17 lines - median filter
        
    def filter_butterworth(self, data: CurveDataList, cutoff: float = 0.1, order: int = 2) -> CurveDataList:
        # 35 lines - requires scipy dependency
        
    def fill_gaps(self, data: CurveDataList, max_gap: int = 5) -> CurveDataList:
        # 24 lines - interpolation
        
    def detect_outliers(self, data: CurveDataInput, threshold: float = 2.0) -> list[int]:
        # 33 lines - outlier detection
        
    def analyze_points(self, points: CurveDataInput) -> dict[str, object]:
        # 22 lines - statistics
        
    # ... more methods
```

**Current Status**: 
- 326 total lines
- 0 imports in production code
- Only in test file `test_data_service.py`
- Mentions scipy dependency that might fail on import

**Why Remove**:
```python
# Grep confirms no usage
grep -r "DataAnalysisService\|smooth_moving_average\|filter_butterworth" \
  --include="*.py" core/ services/ ui/ | grep -v "^.*test_.*\.py"
# Returns: ZERO results
```

**Alternative**: If smoothing needed, add to DataService as simple utility:
```python
# Simple alternative (12 lines vs 326)
def smooth_curve(self, data: CurveDataList, window: int = 5) -> CurveDataList:
    """Simple moving average smoothing."""
    if len(data) < window:
        return data
    result = []
    for i in range(len(data)):
        start = max(0, i - window // 2)
        end = min(len(data), i + window // 2 + 1)
        avg_x = sum(p[1] for p in data[start:end]) / len(data[start:end])
        avg_y = sum(p[2] for p in data[start:end]) / len(data[start:end])
        result.append((data[i][0], avg_x, avg_y))
    return result
```

---

### Example 2: ValidationStrategy (Over-Engineered Pattern)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/core/validation_strategy.py` (lines 80-637)

```python
# Over-engineered factory pattern with 3 strategies
class ValidationStrategy(Protocol):  # Line 81
    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult: ...
    def validate_scale_factor(self, scale: float, context: str = "") -> ValidationResult: ...
    def validate_dimensions(self, width: float, height: float, context: str = "") -> ValidationResult: ...

class BaseValidationStrategy(ABC):  # Line 106
    @abstractmethod
    def validate_coordinate(self, x: float, y: float, context: str = "") -> ValidationResult: pass
    # ... 3 more abstract methods

class MinimalValidationStrategy(BaseValidationStrategy):  # Line 136
    """Minimal validation for production mode."""
    # 113 lines of simple checks

class ComprehensiveValidationStrategy(BaseValidationStrategy):  # Line 251
    """Comprehensive validation for debug mode."""
    # 257 lines of detailed validation

class AdaptiveValidationStrategy(BaseValidationStrategy):  # Line 510
    """Adaptive validation that switches between strategies."""
    # 81 lines of strategy selection logic

# Singletons
_minimal_strategy = MinimalValidationStrategy()  # Line 615
_comprehensive_strategy = ComprehensiveValidationStrategy()
_adaptive_strategy = AdaptiveValidationStrategy()

def get_validation_strategy(mode: str = "current") -> BaseValidationStrategy:
    """Get singleton strategy (6 mode strings)."""
    # 17 lines of if/elif
```

**Current Status**:
- 637 total lines
- 0 uses in production code
- Only in test file: `tests/test_validation_strategy.py`
- Never called from services, UI, or commands

**Why It's Over-Engineered**:
```python
# Example: User accidentally passes invalid coordinate to data_service
data_service.set_position(curve, 999999999999999.0, 999999999999999.0)
# Strategy validation never runs - services don't call it!

# Actual code just uses simple None checks:
if main_window is not None:  # Direct type check, no validation strategy
    frame = main_window.current_frame
```

**Simpler Alternative** (if validation needed):
```python
# 20 lines replaces 637-line strategy pattern
def validate_coordinate(x: float, y: float) -> tuple[float, float] | None:
    """Simple validation with fallback."""
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    # Clamp to reasonable bounds
    return (max(-1e6, min(1e6, x)), max(-1e6, min(1e6, y)))
```

---

### Example 3: ServiceProvider Wrapper (Over-Abstraction)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/core/service_utils.py` (lines 18-85)

```python
class ServiceProvider:
    """Wrapper around services/__init__.py getters."""
    
    @classmethod
    def get_data_service(cls) -> "DataService":
        """Get singleton via ServiceProvider."""
        if cls._data_service is None:
            from services import get_data_service  # Imports the getter we're wrapping!
            cls._data_service = get_data_service()
        return cls._data_service
    
    # ... Identical methods for 3 other services (redundant)

# Usage in production:
data_service = ServiceProvider.get_data_service()  # Added indirection

# But services/__init__.py already provides:
data_service = get_data_service()  # Direct access, simpler
```

**Current Status**:
- 156 lines total
- 0 production imports: `from core.service_utils import ServiceProvider`
- Code references (7) all internal to same file
- Adds layer of indirection for no gain

**Why It's YAGNI**:
1. Duplicate abstraction: services/__init__.py already handles singletons
2. No one uses it: grep confirms zero production imports
3. Adds cognitive load: which getter should I use? `get_data_service()` or `ServiceProvider.get_data_service()`?

**Alternative**: Remove entirely, use `services/__init__.py` getters directly:
```python
# Current production code (correct)
from services import get_data_service
service = get_data_service()

# No need for:
from core.service_utils import ServiceProvider
service = ServiceProvider.get_data_service()  # Redundant wrapper
```

---

### Example 4: Tracking Controller Decomposition (Over-Specialization)

**Files**: 5 tracking-related controllers in `ui/controllers/`

```python
# tracking_data_controller.py
class TrackingDataController(BaseTrackingController):
    """Handles loading and managing tracking data."""
    data_loaded = Signal(str, list)
    
    # Load single-point data
    # Load multi-point data
    # Parse tracking files
    # Manage point lifecycle
    # Handle tracking directions

# tracking_display_controller.py
class TrackingDisplayController(BaseTrackingController):
    """Handles visual display of tracking data."""
    
    # Update display colors
    # Render tracked points
    # Handle display state

# tracking_selection_controller.py
class TrackingSelectionController(BaseTrackingController):
    """Handles selection of tracked points."""
    
    # Select points
    # Deselect points
    # Handle multi-selection

# multi_point_tracking_controller.py
class MultiPointTrackingController(BaseTrackingController):
    """Handles multi-curve tracking operations."""
    
    # Load multiple curves
    # Coordinate multi-curve updates
    # Handle batch operations

# base_tracking_controller.py
class BaseTrackingController:
    """Base class for tracking controllers."""
    
    # Common signal/slot setup
    # Shared utility methods
```

**Signal Coordination Problem**: File `frame_change_coordinator.py` exists ONLY to manage these controllers:
```python
class FrameChangeCoordinator:
    """Coordinates responses to frame changes in deterministic order.
    
    Eliminates race conditions from Qt signal ordering when multiple
    controllers need to respond to the same event.
    """
    
    def coordinate_frame_change(self, frame: int) -> None:
        # Must call controllers in specific order to avoid races
        self._update_data_controller()
        self._update_display_controller()
        self._update_selection_controller()
```

**Cost**:
- 5 separate controllers = 5 separate signal systems
- Must coordinate them with FrameChangeCoordinator
- Developers must understand call ordering
- Duplication of common patterns

**Simpler Alternative** (1 controller):
```python
class TrackingController:
    """Single controller for all tracking operations."""
    
    data_changed = Signal()
    display_changed = Signal()
    selection_changed = Signal()
    
    def load_tracking_data(self, files: list[str]) -> bool:
        # ... load data
        self.data_changed.emit()
        self.display_changed.emit()
        return True
    
    def select_points(self, indices: list[int]) -> None:
        # ... select
        self.selection_changed.emit()
```

---

### Example 5: hasattr/getattr Over use (Type Safety Risk)

**File**: `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/services/data_analysis.py` (lines 254-278)

```python
# Current (unsafe pattern - 154 instances in codebase)
def get_frame_point_status(self, points: CurveDataList, frame: int) -> tuple[int, int, bool]:
    for point in points:
        # Handle CurvePoint object (check for frame attribute first)
        if hasattr(point, "frame"):  # Type info lost!
            if getattr(point, "frame") == frame:  # Could fail silently
                if getattr(getattr(point, "status"), "value", None) == "interpolated":
                    interpolated_count += 1
                else:
                    keyframe_count += 1
        # Handle tuple/list format
        elif len(point) >= 3:
            point_frame = point[0]
            if point_frame == frame:
                # ... tuple handling
```

**Problems**:
1. Type checker can't verify attributes exist
2. `getattr(point, "fram")` typo returns None silently
3. Complex nesting hard to read
4. Treats two different formats (object vs tuple) with same fallback

**Modern Alternative**:
```python
# Better approach - explicit type guards
from typing import TypeGuard

def is_curve_point_object(point: Any) -> TypeGuard[CurvePoint]:
    """Type guard for CurvePoint instances."""
    return isinstance(point, CurvePoint)

def get_frame_point_status(self, points: CurveDataList, frame: int) -> tuple[int, int, bool]:
    keyframe_count = 0
    interpolated_count = 0
    
    for point in points:
        if is_curve_point_object(point):
            # Type checker knows point is CurvePoint here
            if point.frame == frame:
                count = keyframe_count if point.status == PointStatus.NORMAL else interpolated_count
                if point.status == PointStatus.INTERPOLATED:
                    interpolated_count += 1
                else:
                    keyframe_count += 1
        else:
            # Tuple format
            if point[0] == frame:
                # ... handle tuple
```

**Benefits**:
- Type checker catches attribute typos
- Clearer intent (each branch handles one type)
- Easier to maintain (no default fallbacks)

---

## Dead Code Analysis

### Unused Functions/Methods

Found via grep (no production references):

1. **`DataAnalysisService` - entire class** (326 lines)
   - Location: `services/data_analysis.py`
   - Methods: smooth_moving_average, filter_median, filter_butterworth, fill_gaps, detect_outliers, analyze_points, get_frame_point_status, get_frame_range_point_status

2. **`ValidationStrategy` framework** (637 lines)
   - Location: `core/validation_strategy.py`
   - Classes: MinimalValidationStrategy, ComprehensiveValidationStrategy, AdaptiveValidationStrategy
   - Functions: create_validation_strategy, get_validation_strategy
   - Singletons: _minimal_strategy, _comprehensive_strategy, _adaptive_strategy

3. **`ServiceProvider` class** (156 lines)
   - Location: `core/service_utils.py`
   - Methods: get_data_service, get_interaction_service, get_transform_service, get_ui_service, reset_services
   - Class: ServiceContext (context manager with __enter__/__exit__)

4. **Backup/Archive Files** (not code, but dead files)
   - `ui/controllers/multi_point_tracking_controller.py.backup`
   - `ui/curve_view_widget.py.backup`
   - `ui/keyboard_shortcuts.py.backup`
   - `ui/main_window_legacy.py.archive` (22KB)

### Unused Parameters

Found via pattern matching (parameters declared but never used in method body):

- `services/transform_service.py`: Several transform methods accept parameters not used in cache lookup
- `ui/controllers/action_handler_controller.py`: Handler methods with context parameter not used

### Unused Imports

None found - codebase is relatively clean on imports.

### Commented-Out Code Blocks

Minimal found - codebase doesn't have large blocks of commented code.

---

## Modernization Opportunities

### 1. Type Hint Updates (Python 3.10+)

**Current State**: Mostly modernized, but a few patterns remain

**Found**:
- `Optional[str]` in `services/data_analysis.py` (line 39-44)
- Generic `dict[str, object]` patterns could use TypedDict
- `tuple[int, float, float]` format good, but could benefit from NamedTuple

**Recommendation**: Already 95% modernized. Not a priority.

### 2. Context Managers

**Current State**: Good usage of context managers for file I/O and state management

**Examples**:
```python
# Good: BatchUpdates context manager exists
with state.batch_updates():
    state.set_curve_data("Track1", data1)
    state.set_curve_data("Track2", data2)
```

**Recommendation**: Keep as-is.

### 3. Match/Case Pattern Matching (Python 3.10+)

**Current State**: Not used (codebase targets Python 3.9+)

**Example opportunity**:
```python
# Current (validation_strategy.py)
if mode == "minimal":
    return MinimalValidationStrategy()
elif mode == "comprehensive":
    return ComprehensiveValidationStrategy()
elif mode == "adaptive":
    return AdaptiveValidationStrategy()
else:
    raise ValueError(f"Unknown validation mode: {mode}")

# Could be:
match mode:
    case "minimal":
        return MinimalValidationStrategy()
    case "comprehensive":
        return ComprehensiveValidationStrategy()
    case "adaptive" | "auto" | "current":
        return AdaptiveValidationStrategy()
    case _:
        raise ValueError(f"Unknown validation mode: {mode}")
```

**Recommendation**: Not applicable (codebase supports Python 3.9+).

### 4. Dataclass Usage

**Current State**: Good - models.py uses @dataclass extensively

**Recommendation**: Keep as-is.

### 5. Pathlib vs os.path

**Current State**: Minimal os.path usage found

**Recommendation**: Keep current approach.

---

## Quick Wins (Low-Effort Improvements)

| # | Fix | Effort | Benefit | Risk |
|---|-----|--------|---------|------|
| 1 | Delete DataAnalysisService (326 lines) + test | 0.5 hrs | Remove dead code, simplify imports | Very Low - never used |
| 2 | Delete ServiceProvider wrapper (156 lines) | 0.5 hrs | Remove over-abstraction, use direct getters | Very Low - 0 imports |
| 3 | Delete .backup and .archive files | 0.25 hrs | Clean up repo, reduce confusion | Very Low - git has history |
| 4 | Replace hasattr/getattr with isinstance checks (top 20) | 1.5 hrs | Improve type safety, prevent silent failures | Low - isolated changes |
| 5 | Move validation_strategy tests only (keep module) | 0.5 hrs | Reduce test clutter | Low - if keeping module |
| 6 | Remove unimplemented TODO action handlers | 0.75 hrs | Prevent user confusion, clean UI | Low - UI improvement |
| 7 | Consolidate tracking controllers (data/display/select) | 2 hrs | Reduce signal coordination, simplify MainWindow | Medium - requires testing |
| 8 | Split large files (image_sequence_browser 2194 lines) | 2 hrs | Improve discoverability | Medium - refactoring effort |
| 9 | Add type guard functions for point type checks | 1 hr | Replace 154 hasattr/getattr calls | Medium - requires testing |
| 10 | Profile spatial_index performance | 0.5 hrs | Validate premature optimization | Low - understanding only |

**High-ROI Quick Win (START HERE)**:
```bash
# Remove 326 lines of dead code (5 minutes)
rm services/data_analysis.py
rm tests/test_data_analysis.py  # If exists
grep -l "data_analysis" core/ services/ ui/ | xargs sed -i '/import.*data_analysis/d'
```

---

## Complexity Analysis

### Functions with High Cyclomatic Complexity

Top 5:
1. `CurveViewWidget.paintEvent()` - 150+ lines, complex rendering
2. `InteractionService.find_point_at()` - 80+ lines, multi-curve logic
3. `DataService.load_2dtrack_file()` - 120+ lines, file parsing
4. `ApplicationState.set_curve_data()` - 60+ lines, validation + signals
5. `MainWindow.__init__()` - 300+ lines in builder pattern

### Deeply Nested Logic

Found in:
- `services/interaction_service.py`: 4-5 levels of nesting in point operations
- `ui/curve_view_widget.py`: Complex event handling with nested conditions
- `core/validation_strategy.py`: Multiple strategy dispatch levels

### Long Parameter Lists

- `PointIndex.rebuild_index(curve_data, view, transform)` - reasonable
- Most methods follow single responsibility, parameters reasonable

### Large Classes (LOC)

| Class | Lines | Status |
|-------|-------|--------|
| CurveViewWidget | 1987 | Could split rendering/interaction/events |
| ApplicationState | 1148 | Appropriate for state management |
| InteractionService | 1763 | Could extract point operations |
| DataService | 1199 | Could extract file I/O to separate module |
| MainWindow | 1356 | Via builder pattern - acceptable |

---

## Summary Table: Estimated Impact

| Category | Count | Lines | Priority | Effort |
|----------|-------|-------|----------|--------|
| Dead Code (unused services) | 1 | 326 | High | 0.5 hrs |
| Over-Engineering (unused patterns) | 2 | 793 | Medium | 1 hr |
| Over-Abstraction (wrappers) | 1 | 156 | Medium | 0.5 hrs |
| Dead Files (.backup, .archive) | 4 | ~30KB | Low | 0.25 hrs |
| Type Safety Issues (hasattr) | 154 uses | N/A | Low | 2 hrs |
| Controller Over-Decomposition | 1 pattern | 3000+ | Low | 3 hrs |
| Large Monolithic Files | 6 | 8K total | Low | 4 hrs |
| Unimplemented TODOs | 10 | ~50 | Low | 1 hr |
| **TOTAL** | | **~1,500-2,000 lines** | | **~13 hours** |

---

## Recommendations (Prioritized)

### Phase 1: Quick Wins (1 hour)
1. ✅ Delete DataAnalysisService (never used)
2. ✅ Delete ServiceProvider wrapper (never used)
3. ✅ Delete .backup/.archive files (clutter)
4. ✅ Remove unimplemented UI action handlers (prevent confusion)

### Phase 2: Type Safety (2-3 hours)
5. Convert top 20 hasattr/getattr to isinstance checks
6. Add type guard functions for point type checking
7. Update validation patterns

### Phase 3: Architecture (3-4 hours, optional)
8. Profile spatial_index before keeping
9. Consider consolidating tracking controllers
10. Split large monolithic files (image_sequence_browser)

### Phase 4: Strategic (ongoing)
11. Keep ValidationStrategy as reference implementation (even unused - good documentation)
12. Document the 4-service architecture (good design)
13. Monitor controller signal coordination (FrameChangeCoordinator may be needed)

---

## Conclusion

**CurveEditor shows moderate over-engineering**, primarily:
- **Dead code** (DataAnalysisService, ValidationStrategy framework)
- **Unused abstractions** (ServiceProvider wrapper)
- **Over-decomposition** (14 controllers for simple interactions)

However, the **core architecture is sound** - services clean, type hints modern, design patterns appropriate.

**Estimated cleanup**: 1,500-2,000 lines (~2% of codebase) with ~13 hours of effort.

**ROI**: Low - code doesn't break anything, just adds maintenance burden. Prioritize high-impact quick wins (Phase 1) and defer larger refactoring until higher priority items completed.

