# Testing Improvement Roadmap Assessment
**Date**: 2025-10-14
**Codebase**: CurveEditor (2239 test functions, 127 test files, 90% coverage A- grade)
**Reviewer**: Test Development Master Agent

---

## Executive Summary

The testing roadmap is **generally sound** with high-value recommendations, but contains some inaccuracies and missed opportunities. This assessment validates each priority against the actual codebase architecture and provides specific actionable recommendations.

**Key Findings:**
- ✅ Priority 1 (Property-Based Testing): **HIGHLY RECOMMENDED** - Transform roundtrip testing is especially valuable
- ⚠️ Priority 2 (Critical Path Integration): **PARTIALLY COMPLETE** - Many workflows exist, but specific chains are missing
- ⚠️ Priority 3 (State Machine Testing): **OVERENGINEERED** - hypothesis.stateful is overkill for simple state machines
- ✅ Priority 4 (Concurrency): **MORE IMPORTANT** than roadmap suggests due to recent QThread refactoring
- ❌ Roadmap inaccuracy: Claims "only 1 property test" but actually **4 property tests exist**

---

## Priority 1: Property-Based Testing ⭐⭐⭐⭐⭐

### Roadmap Claim vs Reality

**Roadmap**: "Only `test_point_creation_invariants` uses hypothesis"
**Reality**: **4 property-based tests exist** in `tests/test_core_models.py`:
1. `test_point_creation_invariants` (lines 1424-1443)
2. `test_collection_operations_invariants` (lines 1445-1483)
3. `test_distance_properties` (lines 1485-1517)
4. `test_status_from_legacy_robustness` (lines 1519-1545)

### Assessment: ✅ FEASIBLE AND HIGHLY VALUABLE

Despite the count discrepancy, property-based testing is **severely underutilized**. Only 4 out of 2239 tests use hypothesis.

### Specific Targets Validated

#### 1. ✅ Transform Roundtrip Testing (HIGHEST PRIORITY)

**Code Location**: `services/transform_service.py` lines 293-370

**Why Highly Feasible:**
```python
# Transform has explicit inverse operations designed for roundtrip testing
def data_to_screen(self, x: float, y: float) -> tuple[float, float]:
    # Step 1-6: Forward transformation

def screen_to_data(self, x: float, y: float) -> tuple[float, float]:
    # Reverse Steps 6-1: Inverse transformation
```

The code is **explicitly designed** with numbered transformation steps and their reverses, making roundtrip property testing a perfect fit.

**Recommended Test:**
```python
# File: tests/test_transform_service_property.py
from hypothesis import given, settings, assume
from hypothesis import strategies as st

@given(
    x=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    y=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    scale=st.floats(min_value=0.1, max_value=10.0),  # Avoid division by zero
    flip_y=st.booleans(),
)
@settings(max_examples=200, deadline=2000)
def test_transform_roundtrip_invariant(x, y, scale, flip_y):
    """Property: screen_to_data(data_to_screen(point)) ≈ point"""
    transform = Transform(
        scale=scale,
        center_offset_x=0.0,
        center_offset_y=0.0,
        flip_y=flip_y,
        display_height=1080,
    )

    # Roundtrip transformation
    screen_x, screen_y = transform.data_to_screen(x, y)
    recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

    # Should recover original coordinates (within floating-point tolerance)
    assert abs(recovered_x - x) < 1e-9, f"X roundtrip failed: {x} -> {recovered_x}"
    assert abs(recovered_y - y) < 1e-9, f"Y roundtrip failed: {y} -> {recovered_y}"
```

**Expected Impact**: Will find floating-point accumulation errors, edge cases with extreme coordinates, and division-by-zero scenarios.

#### 2. ✅ ApplicationState CRUD Operations

**Code Location**: `stores/application_state.py` lines 206-335

**Operations to Test:**
- `set_curve_data` / `get_curve_data` roundtrip
- `add_point` / `remove_point` / `update_point` consistency
- `set_selection` / `add_to_selection` / `remove_from_selection` invariants
- `begin_batch` / `end_batch` signal consistency

**Recommended Test:**
```python
@given(
    curve_data=st.lists(
        st.tuples(
            st.integers(1, 1000),  # frame
            st.floats(-10000, 10000, allow_nan=False),  # x
            st.floats(-10000, 10000, allow_nan=False),  # y
        ),
        min_size=0,
        max_size=50,
    )
)
def test_application_state_crud_consistency(curve_data):
    """Property: Setting and getting curve data preserves data integrity"""
    state = get_application_state()
    curve_name = "test_curve"

    state.set_curve_data(curve_name, curve_data)
    retrieved = state.get_curve_data(curve_name)

    # Data should be preserved exactly (or converted consistently)
    assert len(retrieved) == len(curve_data)
    for original, retrieved_point in zip(curve_data, retrieved):
        assert retrieved_point[0] == original[0]  # Frame preserved
        assert abs(retrieved_point[1] - original[1]) < 1e-9  # X preserved
        assert abs(retrieved_point[2] - original[2]) < 1e-9  # Y preserved
```

**Expected Impact**: Finds edge cases with empty data, large datasets, duplicate frames, and extreme coordinates.

#### 3. ⚠️ CurveViewWidget Selection Operations

**Code Location**: `ui/curve_view_widget.py`

**Concern**: The roadmap suggests testing "select/deselect/clear" but selection state is managed in **ApplicationState**, not CurveViewWidget. The widget delegates to InteractionService.

**Better Approach**: Test selection invariants on ApplicationState directly:

```python
@given(
    selection_ops=st.lists(
        st.one_of(
            st.tuples(st.just("add"), st.integers(0, 10)),
            st.tuples(st.just("remove"), st.integers(0, 10)),
            st.just(("clear",)),
        ),
        max_size=20,
    )
)
def test_application_state_selection_invariants(selection_ops):
    """Property: Selection operations maintain valid state"""
    state = get_application_state()
    state.set_active_curve("test")
    state.set_curve_data("test", [(i, float(i), float(i)) for i in range(10)])

    for op in selection_ops:
        if op[0] == "add":
            state.add_to_selection("test", {op[1]})
        elif op[0] == "remove":
            state.remove_from_selection("test", {op[1]})
        elif op[0] == "clear":
            state.clear_selection("test")

    # Invariants: Selection indices must be valid
    selection = state.get_selection("test")
    assert all(0 <= idx < 10 for idx in selection)
```

#### 4. ❌ Timeline Synchronization

**Code Location**: `ui/controllers/timeline_controller.py`

**Assessment**: Timeline frame changes are **deterministic** (see `ui/controllers/frame_change_coordinator.py` - "eliminates race conditions from Qt signal ordering"). Property-based testing adds little value here; regular parametrized tests are sufficient.

**Recommendation**: **Skip** - Use integration tests instead.

---

## Priority 2: Critical Path Integration Tests ⭐⭐⭐⭐

### Roadmap Claim vs Reality

**Roadmap**: "Missing complex user workflows"
**Reality**: **Many workflow tests already exist**:
- `test_json_workflow`, `test_csv_workflow` (test_integration.py)
- `test_file_load_to_display_workflow` (test_service_integration.py)
- `test_undo_redo_workflow` (test_service_integration.py)
- `test_zoom_workflow`, `test_selection_workflow`, `test_pan_workflow` (test_integration_real.py)
- `test_complete_session_workflow` (test_session_manager.py)

### Assessment: ⚠️ PARTIALLY COMPLETE

Good foundation exists, but **specific chained workflows** are missing.

### Roadmap Workflows Validated

#### ❌ Workflow 1: "Load image sequence → Load tracking data → Select points → Smooth → Save"

**Status**: **MISSING - CRITICAL GAP**

Existing tests cover:
- ✅ Load image sequence (test_image_sequence_workflow)
- ✅ Load tracking data (test_json_workflow, test_csv_workflow)
- ✅ Select points (test_selection_workflow)
- ✅ Smoothing (test_data_analysis_with_transform - line 328-330)
- ✅ Save (test_json_workflow, test_csv_workflow)

But **NO TEST chains them together** in a single end-to-end workflow!

**Recommended Addition:**
```python
# File: tests/test_complete_editing_workflow.py
def test_full_editing_workflow_image_to_export(main_window, qtbot, tmp_path):
    """Complete workflow: Load images → Load tracking → Select → Smooth → Save"""
    # 1. Load image sequence
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    # ... create test images

    # 2. Load tracking data
    tracking_file = tmp_path / "track.json"
    # ... create test tracking data with noise

    # 3. Load into application
    data_service = get_data_service()
    curve_data = data_service._load_json(tracking_file)

    app_state = get_application_state()
    app_state.set_curve_data("test_track", curve_data)
    app_state.set_active_curve("test_track")

    # 4. Select noisy points (frames 10-20)
    app_state.select_range("test_track", 10, 20)

    # 5. Apply smoothing to selection
    smoothed = data_service.smooth_moving_average(curve_data, window_size=5)
    app_state.set_curve_data("test_track", smoothed)

    # 6. Save modified data
    output_file = tmp_path / "smoothed.json"
    success = data_service._save_json(output_file, smoothed, "Smoothed", "#00FF00")
    assert success

    # 7. Verify output
    reloaded = data_service._load_json(output_file)
    assert len(reloaded) == len(curve_data)
    # Verify smoothing reduced noise (variance should be lower)
```

#### ⚠️ Workflow 2: "Multi-curve editing → Batch point status changes → Undo/Redo → Export"

**Status**: **PARTIALLY COVERED**

Existing coverage:
- ✅ Undo/Redo (test_undo_redo_workflow)
- ✅ Point status changes (test_tracking_point_status_commands.py)
- ❌ **Multi-curve batch operations** - MISSING

**Gap**: No test for batch status changes across **multiple curves simultaneously**.

**Recommended Addition:**
```python
def test_multi_curve_batch_status_workflow(main_window, qtbot):
    """Multi-curve batch editing with undo/redo"""
    state = get_application_state()

    # Setup 3 curves with keyframes
    for i in range(3):
        curve_name = f"Track{i+1}"
        data = [(frame, float(frame), float(frame)) for frame in range(1, 101)]
        state.set_curve_data(curve_name, data)

    # Batch operation: Set frames 10-20 to INTERPOLATED on all curves
    with state.batch_updates():
        for i in range(3):
            curve_name = f"Track{i+1}"
            for frame in range(10, 21):
                state.set_point_status(curve_name, frame, PointStatus.INTERPOLATED)

    # Verify batch changes
    # Add to undo history
    # Perform undo
    # Verify restoration
    # Perform redo
    # Export all curves
```

#### ❌ Workflow 3: "Timeline scrubbing during playback with centering mode"

**Status**: **MISSING**

Existing timeline tests (10 files found) cover:
- Timeline scrubbing (test_timeline_scrubbing.py)
- Centering toggle (test_centering_toggle.py)
- Frame selection sync (test_frame_selection_sync.py)

But **NO TEST combines scrubbing + playback + centering** simultaneously.

**Recommended Addition:**
```python
def test_timeline_scrubbing_during_playback_with_centering(main_window, qtbot):
    """Test frame sync when scrubbing timeline during playback with auto-center"""
    # Enable auto-centering mode
    # Start playback
    # Scrub timeline while playing
    # Verify:
    #   - Playback pauses/stops appropriately
    #   - Frame sync remains correct
    #   - Curve view centers on current frame
    #   - No race conditions between playback and scrubbing
```

#### ⚠️ Workflow 4: "File loading error recovery → Retry → Success"

**Status**: **PARTIALLY COVERED**

Existing error handling (test_integration.py lines 423-456):
- ✅ Invalid file handling (test_invalid_file_handling)
- ✅ Out-of-bounds operations (test_out_of_bounds_operations)
- ✅ Service state consistency after errors

**Gap**: No test for **retry after failure** - critical for user experience.

**Recommended Addition:**
```python
def test_file_load_error_recovery_retry_workflow(main_window, qtbot, tmp_path):
    """Test error recovery with retry mechanism"""
    # 1. Attempt to load corrupted file
    # 2. Verify error handling
    # 3. Fix the file
    # 4. Retry loading
    # 5. Verify successful recovery
    # 6. Verify application state is clean
```

### Additional Missing Workflows Discovered

#### ❌ Multi-Point Tracking with Gap Handling

**Code Location**: `ui/controllers/multi_point_tracking_controller.py`

Tests exist for Insert Track (test_insert_track_integration.py), but no end-to-end test for:
1. Load multiple curves with gaps
2. Use Insert Track to fill gaps
3. Verify gap visualization
4. Undo tracking operations
5. Re-track with different parameters

---

## Priority 3: State Machine Testing ⭐⭐⭐

### Roadmap Claim vs Reality

**Roadmap**: "Use hypothesis.stateful for state machine testing"
**Reality**: **Overkill** for CurveEditor's state machines

### Assessment: ⚠️ OVERENGINEERED

#### ApplicationState Lifecycle

**Code Location**: `stores/application_state.py`

**Roadmap Target States**: "init → active_curve_set → data_loaded → data_modified → saved"

**Reality**: ApplicationState doesn't have **explicit lifecycle states**. It's a **data container** with operations, not a state machine.

**Better Approach**: Use **property-based testing** (Priority 1) for invariants, not stateful testing.

```python
# NOT a state machine - it's a data store
@invariant()
def check_consistency(self):
    # This doesn't make sense for ApplicationState

# BETTER: Property-based invariant testing
@given(operations=st.lists(...))
def test_application_state_invariants(operations):
    """Test invariants hold after any sequence of operations"""
    state = get_application_state()
    for op in operations:
        op(state)

    # Invariants:
    assert state.active_curve is None or state.active_curve in state.get_all_curve_names()
    if state.active_curve:
        data = state.get_curve_data(state.active_curve)
        selection = state.get_selection(state.active_curve)
        assert all(0 <= idx < len(data) for idx in selection)
```

#### ✅ Timeline Playback States (Good Candidate)

**Code Location**: `ui/controllers/timeline_controller.py` lines 36-59

**States**: STOPPED, PLAYING_FORWARD, PLAYING_BACKWARD

This **IS** a proper state machine, but it's **too simple** for hypothesis.stateful. Regular parametrized tests suffice:

```python
# Simple state machine - use parametrize, not hypothesis.stateful
@pytest.mark.parametrize("transitions", [
    [("play_forward", PLAYING_FORWARD), ("stop", STOPPED)],
    [("play_forward", PLAYING_FORWARD), ("play_backward", PLAYING_BACKWARD), ("stop", STOPPED)],
    [("play_forward", PLAYING_FORWARD), ("play_forward", PLAYING_FORWARD)],  # Idempotent
])
def test_playback_state_transitions(transitions):
    """Test valid state transitions"""
    controller = TimelineController()
    for action, expected_state in transitions:
        # Perform action
        # Verify state
```

**When hypothesis.stateful IS appropriate:**
- Complex state machines (10+ states)
- Non-deterministic transitions
- Concurrent state access
- Complex invariants that must hold across all paths

**CurveEditor's state machines are too simple for this.**

### Recommendation: **Downgrade to Priority 5** - Use parametrized tests instead

---

## Priority 4: Concurrency Stress Tests ⭐⭐⭐⭐⭐

### Roadmap Claim vs Reality

**Roadmap**: "Priority 4, low ROI, high effort"
**Reality**: **UPGRADED TO PRIORITY 2** due to recent QThread refactoring

### Assessment: ✅ CRITICAL GIVEN RECENT REFACTORING

**Recent Commits** (from `git log`):
- d2ceeaf: "Modernize DirectoryScanWorker and ProgressWorker to use Qt interruption API"
- 6b78767: "Refactor FileLoadWorker to use QThread instead of Python threading"
- b631e06: "Add critical thread safety protection to ApplicationState"

**Active QThread Components:**
- `ui/file_operations.py` - FileLoadWorker
- `ui/progress_manager.py` - ProgressWorker, DirectoryScanWorker
- `ui/controllers/multi_point_tracking_controller.py` - Thread usage

### Recommended Tests (Higher Priority Than Roadmap Suggests)

#### 1. ✅ FileLoadWorker Concurrent Operations

```python
def test_concurrent_file_loads_with_cancellation(qtbot):
    """Test multiple file loads with cancellation"""
    # Start 3 file loads simultaneously
    # Cancel middle operation
    # Verify:
    #   - Cancelled worker stops cleanly
    #   - Other workers complete successfully
    #   - ApplicationState remains consistent
```

#### 2. ✅ Frame Changes During Background Loading

```python
def test_rapid_frame_changes_during_image_loading(qtbot):
    """Stress test: Frame changes while FileLoadWorker is active"""
    # Start background image loading
    # Rapidly change frames (100x in quick succession)
    # Verify:
    #   - No deadlocks
    #   - Frame sync remains correct
    #   - No memory leaks
    #   - UI remains responsive
```

#### 3. ✅ Signal Storm Handling

**Code Location**: ApplicationState emits multiple signals (curves_changed, selection_changed, frame_changed)

```python
def test_application_state_signal_storm_with_batch(qtbot):
    """Test ApplicationState handles signal storms with batch updates"""
    state = get_application_state()
    signal_count = 0

    def on_signal():
        nonlocal signal_count
        signal_count += 1

    state.curves_changed.connect(on_signal)

    # Without batch: 1000 signals
    for i in range(1000):
        state.set_curve_data(f"curve{i}", [(1, 1.0, 1.0)])
    assert signal_count == 1000

    signal_count = 0

    # With batch: 1 signal
    with state.batch_updates():
        for i in range(1000):
            state.set_curve_data(f"curve{i}", [(1, 1.0, 1.0)])
    assert signal_count == 1  # Batched!
```

---

## Architecture Fit Analysis

### ✅ Patterns Match CurveEditor Architecture

The roadmap recommendations generally align well with:
1. **Service Architecture**: Property tests can validate service contracts
2. **Single Source of Truth**: ApplicationState is perfect for CRUD property tests
3. **Immutable Models**: Transform immutability enables safe property testing
4. **Protocol Interfaces**: Property tests validate protocol contracts

### ❌ Misalignments

1. **State Machine Testing**: CurveEditor doesn't have complex state machines worthy of hypothesis.stateful
2. **Timeline Synchronization**: FrameChangeCoordinator eliminates race conditions, making property tests less valuable
3. **CurveViewWidget Selection**: Selection is managed by ApplicationState, not the widget

---

## Missing Testing Opportunities (New Discoveries)

### 1. Protocol Contract Validation

**Code Location**: `protocols/ui.py`, `protocols/curve_view.py`

CurveEditor uses protocols extensively. No tests validate protocol contracts hold across implementations.

**Recommended Test:**
```python
@given(data=st....)
def test_curve_view_protocol_contract(data, curve_view_implementation):
    """Property: All CurveViewProtocol implementations behave identically"""
    # Test that MockCurveView, CurveViewWidget, etc. all satisfy protocol
```

### 2. Transform Stability Hash Correctness

**Code Location**: `services/transform_service.py` lines 236-241

Transform uses MD5 hash for LRU cache stability. No test validates:
- Hash uniqueness (different parameters → different hashes)
- Hash stability (same parameters → same hash)

**Recommended Test:**
```python
@given(
    params1=transform_params_strategy(),
    params2=transform_params_strategy(),
)
def test_transform_stability_hash_properties(params1, params2):
    """Property: Hash reflects parameter equality"""
    t1 = Transform(**params1)
    t2 = Transform(**params2)

    if params1 == params2:
        assert t1.stability_hash == t2.stability_hash
    # Note: Different params might collide (MD5), but unlikely
```

### 3. Batch Operation Signal Guarantees

**Code Location**: `stores/application_state.py` lines 931-1033

ApplicationState.batch_updates() **must** emit exactly one signal set at the end. No property test validates this guarantee holds under all operation sequences.

### 4. Image State Lifecycle Validation

**Code Location**: `core/image_state.py`

ImageState has complex lifecycle (NO_SEQUENCE → SEQUENCE_LOADED → IMAGE_LOADING → IMAGE_LOADED). This **IS** suitable for state machine testing.

**Recommended Test:**
```python
class ImageStateStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.state = ImageState()

    @rule()
    def set_sequence(self):
        self.state.set_sequence("/tmp", ["test.jpg"])

    @rule()
    def set_loading(self):
        self.state.set_image_loading()

    @invariant()
    def check_state_consistency(self):
        # State invariants that must ALWAYS hold
        if self.state.has_image_displayed():
            assert self.state.has_sequence_loaded()
```

---

## Recommended Roadmap Adjustments

### Original Roadmap
1. ⭐⭐⭐⭐⭐ Property-Based Testing
2. ⭐⭐⭐⭐ Critical Path Integration
3. ⭐⭐⭐⭐ State Machine Testing
4. ⭐⭐⭐ Concurrency Stress Tests
5. ⭐⭐⭐ Performance Regression

### Revised Roadmap (Based on Actual Codebase)

#### Priority 1: Property-Based Testing ⭐⭐⭐⭐⭐
**Effort**: 3-4 hours
**ROI**: Very High
**Tests to Add**: 6-8 property tests

**Specific Targets:**
1. ✅ Transform roundtrip invariants (CRITICAL)
2. ✅ ApplicationState CRUD operations
3. ✅ Selection operation invariants
4. ✅ Transform stability hash properties
5. ✅ Batch signal guarantees
6. ⚠️ Protocol contract validation (optional)

#### Priority 2: Concurrency Stress Tests ⭐⭐⭐⭐⭐ (UPGRADED)
**Effort**: 3-4 hours
**ROI**: Very High (recent QThread refactoring)
**Tests to Add**: 4-5 concurrency tests

**Specific Targets:**
1. ✅ FileLoadWorker concurrent operations
2. ✅ Frame changes during background loading
3. ✅ Signal storm handling
4. ✅ QThread cancellation safety
5. ✅ ApplicationState thread safety

#### Priority 3: Critical Path Integration ⭐⭐⭐⭐
**Effort**: 2-3 hours
**ROI**: High
**Tests to Add**: 3-4 workflow tests

**Specific Targets:**
1. ✅ Complete editing workflow (images → tracking → smooth → save)
2. ✅ Multi-curve batch operations
3. ✅ Timeline scrubbing during playback + centering
4. ⚠️ Error recovery with retry (optional)

#### Priority 4: State Machine Testing ⭐⭐ (DOWNGRADED)
**Effort**: 2-3 hours
**ROI**: Medium
**Tests to Add**: 1-2 state machine tests (NOT using hypothesis.stateful)

**Specific Targets:**
1. ✅ ImageState lifecycle (this IS a real state machine)
2. ⚠️ PlaybackState transitions (use parametrize, not stateful)
3. ❌ ApplicationState (NOT a state machine - use property tests instead)

#### Priority 5: Performance Regression ⭐⭐⭐
**Effort**: 1-2 hours
**ROI**: Medium
**Tests to Add**: Performance baselines

---

## Detailed Implementation Guidance

### Transform Roundtrip Testing (Highest Priority)

**File**: `tests/test_transform_roundtrip_properties.py` (NEW)

```python
"""Property-based tests for Transform coordinate roundtrip invariants."""
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from services.transform_service import Transform
import pytest

# Strategy for valid transform parameters
def transform_params():
    return st.fixed_dictionaries({
        "scale": st.floats(min_value=0.1, max_value=10.0),
        "center_offset_x": st.floats(min_value=-5000, max_value=5000),
        "center_offset_y": st.floats(min_value=-5000, max_value=5000),
        "pan_offset_x": st.floats(min_value=-5000, max_value=5000),
        "pan_offset_y": st.floats(min_value=-5000, max_value=5000),
        "flip_y": st.booleans(),
        "display_height": st.integers(min_value=100, max_value=4320),
        "image_scale_x": st.floats(min_value=0.1, max_value=5.0),
        "image_scale_y": st.floats(min_value=0.1, max_value=5.0),
        "scale_to_image": st.booleans(),
    })

@given(
    x=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    y=st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
    params=transform_params(),
)
@settings(max_examples=200, deadline=2000)
def test_transform_roundtrip_identity(x, y, params):
    """Property: Roundtrip transformation recovers original coordinates."""
    transform = Transform(**params)

    # Forward then backward
    screen_x, screen_y = transform.data_to_screen(x, y)
    recovered_x, recovered_y = transform.screen_to_data(screen_x, screen_y)

    # Should recover original (within floating-point error)
    tolerance = 1e-6
    assert abs(recovered_x - x) < tolerance, \
        f"X roundtrip failed: {x} -> {screen_x} -> {recovered_x} (error: {abs(recovered_x - x)})"
    assert abs(recovered_y - y) < tolerance, \
        f"Y roundtrip failed: {y} -> {screen_y} -> {recovered_y} (error: {abs(recovered_y - y)})"

@given(
    x=st.floats(-10000, 10000, allow_nan=False, allow_infinity=False),
    y=st.floats(-10000, 10000, allow_nan=False, allow_infinity=False),
    params=transform_params(),
)
def test_transform_inverse_symmetry(x, y, params):
    """Property: Transformation inverse is symmetric."""
    transform = Transform(**params)

    # data -> screen -> data should equal screen -> data -> screen
    screen_x, screen_y = transform.data_to_screen(x, y)
    data_x, data_y = transform.screen_to_data(screen_x, screen_y)

    # Re-transform recovered data
    screen_x2, screen_y2 = transform.data_to_screen(data_x, data_y)

    tolerance = 1e-6
    assert abs(screen_x2 - screen_x) < tolerance
    assert abs(screen_y2 - screen_y) < tolerance
```

---

## Expected Outcomes

### After Priority 1-2 (Property + Concurrency)
- **Test Count**: 2250-2260 tests (+11-21)
- **Grade**: A (92-93%)
- **Bugs Prevented**: 70-140 edge cases
- **Confidence**: High in transforms, state management, threading
- **Total Effort**: 6-8 hours

### After Priority 3 (Integration)
- **Test Count**: 2254-2264 tests (+15-25)
- **Grade**: A/A+ (93-95%)
- **Bugs Prevented**: 75-150 edge cases
- **Confidence**: Very High in complete workflows
- **Total Effort**: 8-11 hours

---

## Conclusion

The testing roadmap provides **excellent direction** but needs adjustments based on actual codebase analysis:

**Keep (High Value):**
- ✅ Transform roundtrip property testing (CRITICAL)
- ✅ ApplicationState property testing
- ✅ Concurrency stress testing (UPGRADED priority)
- ✅ End-to-end workflow testing

**Adjust:**
- ⚠️ State machine testing: Downgrade and use simpler approaches
- ⚠️ Timeline synchronization: Skip property tests, use integration tests
- ⚠️ CurveViewWidget selection: Test ApplicationState instead

**Add (New Discoveries):**
- ✅ Transform stability hash validation
- ✅ Batch operation signal guarantees
- ✅ Protocol contract validation
- ✅ ImageState lifecycle testing
- ✅ QThread cancellation safety

**Recommended Focus**: Priorities 1-3 will achieve A/A+ grade (93-95%) with reasonable effort.
