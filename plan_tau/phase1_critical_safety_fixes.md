## 🔴 **PHASE 1: CRITICAL SAFETY FIXES (WEEK 1)**

**Objective:** Fix all race conditions, documentation mismatches, and CLAUDE.md violations
**Total Effort:** 18-26 hours (reduced from 25-35 by simplifying Task 1.2)
**Priority:** CRITICAL - Must complete before any other work
**Time Saved:** 5-6 hours by skipping StateManager QueuedConnection work (Phase 3 will delete it)

---

### **Task 1.1: Fix Property Setter Race Conditions**
**Time:** 4-6 hours
**Files:** 3 files
**Impact:** Prevents timeline desync bugs

#### **Issue Description:**
Property setters like `self.current_frame = N` update ApplicationState **synchronously**, but UI updates happen **later** via queued signal callbacks. This creates a race window where State=N but UI=N-1.

#### **Files to Fix:**

##### **1. ui/state_manager.py:424-458 (total_frames.setter)**

**Current (BUGGY):**
```python
@total_frames.setter
def total_frames(self, count: int) -> None:
    """Set total frames by creating synthetic image_files list (DEPRECATED)."""
    count = max(1, count)
    current_total = self._app_state.get_total_frames()

    if current_total != count:
        # Create synthetic image_files list
        synthetic_files = [f"<synthetic_frame_{i+1}>" for i in range(count)]
        self._app_state.set_image_files(synthetic_files)

        # Clamp current frame if it exceeds new total
        if self.current_frame > count:
            self.current_frame = count  # ❌ BUG: Synchronous property write
```

**Fixed:**
```python
@total_frames.setter
def total_frames(self, count: int) -> None:
    """Set total frames by creating synthetic image_files list (DEPRECATED)."""
    count = max(1, count)
    current_total = self._app_state.get_total_frames()

    if current_total != count:
        # Create synthetic image_files list
        synthetic_files = [f"<synthetic_frame_{i+1}>" for i in range(count)]
        self._app_state.set_image_files(synthetic_files)

        # Clamp current frame if it exceeds new total
        if self.current_frame > count:
            # Explicit clamping before direct state update (preserves 1-based frame invariant)
            clamped_frame = max(1, count)
            self._app_state.set_frame(clamped_frame)  # ✅ FIXED: Direct state update with clamping
```

**Why this works:** We bypass the property setter (avoiding nested signal emission) but preserve the clamping logic to maintain the 1-based frame invariant. StateManager doesn't have UI widgets to update—the frame_changed signal from ApplicationState will trigger UI updates via Qt.QueuedConnection in FrameChangeCoordinator.

##### **2. ui/state_manager.py:523-541 (set_image_files)**

**Current (BUGGY):**
```python
def set_image_files(self, files: list[str]) -> None:
    """Set the list of image files (delegated to ApplicationState)."""
    self._app_state.set_image_files(files)
    new_total = self._app_state.get_total_frames()

    # Clamp current frame if it exceeds new total
    if self.current_frame > new_total:
        self.current_frame = new_total  # ❌ BUG: Synchronous property write
```

**Fixed:**
```python
def set_image_files(self, files: list[str]) -> None:
    """Set the list of image files (delegated to ApplicationState)."""
    self._app_state.set_image_files(files)
    new_total = self._app_state.get_total_frames()

    # Clamp current frame if it exceeds new total
    if self.current_frame > new_total:
        # Explicit clamping before direct state update (preserves 1-based frame invariant)
        clamped_frame = max(1, new_total)
        self._app_state.set_frame(clamped_frame)  # ✅ FIXED: Direct state update with clamping
```

**Why this works:** Same as above—we bypass the property setter (avoiding nested signal emission) but preserve the clamping logic. StateManager delegates frame storage to ApplicationState, and UI updates happen via queued signals.

##### **3. ui/timeline_tabs.py:652-655**

**Current (POTENTIAL BUG):**
```python
def set_frame_range(self, min_frame: int, max_frame: int) -> None:
    # ...
    if self.current_frame < min_frame:
        self.current_frame = min_frame  # ❌ POTENTIAL BUG
    elif self.current_frame > max_frame:
        self.current_frame = max_frame  # ❌ POTENTIAL BUG
```

**Fixed:**
```python
def set_frame_range(self, min_frame: int, max_frame: int) -> None:
    # ...
    if self.current_frame < min_frame:
        # Update internal tracking FIRST
        self._current_frame = min_frame
        # Update visual state FIRST
        self._on_frame_changed(min_frame)
        # Then delegate
        self.current_frame = min_frame
    elif self.current_frame > max_frame:
        # Update internal tracking FIRST
        self._current_frame = max_frame
        # Update visual state FIRST
        self._on_frame_changed(max_frame)
        # Then delegate
        self.current_frame = max_frame
```

#### **Verification Steps:**

```bash
# 1. Search for all current_frame property writes that might have this issue
grep -rn "self.current_frame = " ui/ --include="*.py"

# Expected locations:
# - ui/state_manager.py:454 (total_frames.setter - FIXED)
# - ui/state_manager.py:536 (set_image_files - FIXED)
# - ui/timeline_tabs.py:653, 655 (set_frame_range - FIXED)

# 2. Verify fixes use _app_state.set_frame() directly
grep -A 2 "if self.current_frame > " ui/state_manager.py

# 3. Run timeline desync tests
~/.local/bin/uv run pytest tests/test_timeline_scrubbing.py -v
~/.local/bin/uv run pytest tests/test_timeline_focus_behavior.py -v
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v

# 4. Manual test: Rapid timeline clicking should stay in sync
# Run app, load data, rapidly click different timeline tabs
# UI should always match ApplicationState
```

#### **Success Metrics:**
- ✅ All 3 race condition locations fixed (2 in state_manager.py, 1 in timeline_tabs.py)
- ✅ StateManager uses _app_state.set_frame() for clamping (not self.current_frame property)
- ✅ timeline_tabs uses immediate visual updates before delegation
- ✅ All timeline tests pass
- ✅ Manual rapid-clicking test shows no desync

---

### **Task 1.2: Verify Critical Qt.QueuedConnection Usage**
**Time:** 3-4 hours (verification only - down from 8 hours)
**Files:** 3 files (worker threads + FrameChangeCoordinator only)
**Impact:** Verify thread safety and proven timing fixes, document policy, avoid wasted work

#### **⚠️ SCOPE CHANGE: Verification Only**
Six-agent review determined:
- ✅ **Worker thread signals** already use QueuedConnection (verify correctness)
- ✅ **FrameChangeCoordinator** already uses QueuedConnection (proven necessary for deterministic ordering)
- ❌ **Skip blanket-application** to 50+ StateManager connections (Phase 3 will remove StateManager entirely - avoid refactoring soon-to-be-deleted code)
- 📋 **Document policy** in CLAUDE.md for future connection decisions

**Key Insight**: Don't spend 6-8 hours adding Qt.QueuedConnection to StateManager forwarding when Phase 3 Task 3.3 will delete StateManager in 2-3 weeks. Focus on proven necessary cases only.

#### **Verification Tasks:**

##### **1. Verify Worker Thread Signals (REQUIRED - Thread Safety)**

Check that ALL worker→main thread signals use Qt.QueuedConnection:

```bash
# Search for worker signal connections
grep -A 5 "worker\." ui/image_sequence_browser.py | grep "\.connect"
grep -A 5 "Worker" ui/file_operations.py | grep "\.connect"

# Verify each shows Qt.QueuedConnection
```

**Files to verify:**
- `ui/image_sequence_browser.py`: DirectoryScanWorker, thumbnail workers
- `ui/file_operations.py`: FileLoadWorker

**Expected pattern (CORRECT):**
```python
from PySide6.QtCore import Qt

# Worker thread signals MUST use QueuedConnection (modern syntax)
worker.finished.connect(
    self._on_finished,
    type=Qt.ConnectionType.QueuedConnection  # Cross-thread safety
)
worker.progress.connect(
    self._on_progress,
    type=Qt.ConnectionType.QueuedConnection
)
worker.error.connect(
    self._on_error,
    type=Qt.ConnectionType.QueuedConnection
)
```

**If missing Qt.QueuedConnection:** Add it (thread safety requirement).

**If using old syntax**: Update from `Qt.QueuedConnection` → `type=Qt.ConnectionType.QueuedConnection` (modern PySide6 style).

##### **2. Verify FrameChangeCoordinator (PROVEN NECESSARY)**

Check that FrameChangeCoordinator uses Qt.QueuedConnection for deterministic ordering:

```bash
# Check frame_change_coordinator.py
grep -A 10 "def connect" ui/controllers/frame_change_coordinator.py | grep "Qt.QueuedConnection"
```

**Expected (CORRECT):**
```python
# ui/controllers/frame_change_coordinator.py
from PySide6.QtCore import Qt

_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    type=Qt.ConnectionType.QueuedConnection | Qt.ConnectionType.UniqueConnection
)
```

**Rationale:** Commit 51c500e ("fix(signals): Fix timeline-curve desynchronization with Qt.QueuedConnection") already applied this fix. Verify it's still in place.

**Note**: If UniqueConnection is missing, add it to prevent duplicate connections if coordinator is connected multiple times.

##### **3. Add Qt Connection Policy to CLAUDE.md**

Document when to use Qt.QueuedConnection (see Task 1.2 Part 4 below).

##### **4. Re-evaluate After Phase 3**

After Phase 3 removes StateManager, reassess if additional Qt.QueuedConnection needed for direct ApplicationState→Component connections. Likely answer: NO (except workers already covered).

#### **Verification Steps:**

```bash
# 1. Count worker thread signal connections with QueuedConnection (any syntax)
grep -r "worker.*\.connect" ui/ --include="*.py" -A 2 | grep -E "(Qt\.QueuedConnection|ConnectionType\.QueuedConnection)" | wc -l
# Should show: 8+ (all worker signals)

# 2. Verify FrameChangeCoordinator uses QueuedConnection (check for UniqueConnection too)
grep -A 10 "frame_changed.connect" ui/controllers/frame_change_coordinator.py | grep -E "(QueuedConnection|UniqueConnection)"
# Should show: both QueuedConnection and UniqueConnection

# 3. Check if old syntax is used (for migration reference)
grep -r "Qt\.QueuedConnection[^)]" ui/ --include="*.py"
# If matches found, consider updating to modern type=Qt.ConnectionType.QueuedConnection syntax

# 4. Run signal timing tests
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v

# 5. Verify no regressions in timing-sensitive tests
~/.local/bin/uv run pytest tests/test_timeline_scrubbing.py -v
~/.local/bin/uv run pytest tests/test_timeline_focus_behavior.py -v
```

#### **Success Metrics:**
- ✅ All worker thread signals use Qt.QueuedConnection (thread safety)
- ✅ FrameChangeCoordinator uses Qt.QueuedConnection + UniqueConnection (deterministic ordering, no duplicates)
- ✅ Modern PySide6 syntax: `type=Qt.ConnectionType.QueuedConnection` (preferred over old style)
- ✅ Qt Connection Policy added to CLAUDE.md (includes UniqueConnection, thread affinity, best practices)
- ✅ All timing tests pass
- ✅ Saved 5-6 hours by skipping StateManager connections (Phase 3 will delete them)

---

### **Task 1.3: Replace All hasattr() with None Checks**
**Time:** 8-12 hours
**Files:** 15 files, 46 instances (19 already fixed in commit e80022d)
**Impact:** CLAUDE.md compliance, type safety, reduces type ignores by ~8% (184 ignores: 174 obsolete + ~10 from hasattr)

#### **⚠️ NOTE: Type Ignore Reduction Clarification**
- **This task alone**: ~8% reduction (184 of 2,202 total ignores)
  - 174 obsolete `reportUnnecessaryTypeIgnoreComment` (already flagged by basedpyright)
  - ~10 ignores directly related to hasattr() calls
- **30% reduction target**: Requires completing ALL 4 phases of Plan TAU (not just Task 1.3)
- **Already completed**: 19 hasattr() instances fixed in commit e80022d (not mentioned in original plan)

#### **Issue Description:**
CLAUDE.md documents this as anti-pattern. Type checker loses all attribute information with hasattr().

#### **Files to Fix (Prioritized by Count):**

##### **1. ui/image_sequence_browser.py (12 instances)**

**Pattern 1: Chained hasattr() (Lines 483-485):**

**Before:**
```python
if parent is not None and hasattr(parent, "state_manager") and parent.state_manager is not None:
    state_manager = parent.state_manager
    if state_manager and hasattr(state_manager, "recent_directories"):
        recent_dirs = state_manager.recent_directories
```

**After:**
```python
if (
    parent is not None
    and parent.state_manager is not None
    and parent.state_manager.recent_directories is not None
):
    recent_dirs = parent.state_manager.recent_directories
```

**Pattern 2: Single hasattr() (Line 1906):**

**Before:**
```python
if not hasattr(self, "tree_view"):
    return
```

**After:**
```python
if self.tree_view is None:
    return
```

Apply this pattern to all 12 instances in the file.

##### **2. ui/controllers/timeline_controller.py (9 instances - all in __del__)**

**Before:**
```python
def __del__(self) -> None:
    """Disconnect all signals to prevent memory leaks."""
    # Disconnect playback timer
    try:
        if hasattr(self, "playback_timer"):
            _ = self.playback_timer.timeout.disconnect(self._on_playback_timer)
            self.playback_timer.stop()
    except (RuntimeError, AttributeError):
        pass

    try:
        if hasattr(self, "frame_spinbox"):
            _ = self.frame_spinbox.valueChanged.disconnect(self._on_frame_changed)
    except (RuntimeError, AttributeError):
        pass

    # ... 7 more hasattr() checks
```

**After:**
```python
def __del__(self) -> None:
    """Disconnect all signals to prevent memory leaks."""
    # Disconnect playback timer
    try:
        if self.playback_timer is not None:
            _ = self.playback_timer.timeout.disconnect(self._on_playback_timer)
            self.playback_timer.stop()
    except (RuntimeError, AttributeError):
        pass

    try:
        if self.frame_spinbox is not None:
            _ = self.frame_spinbox.valueChanged.disconnect(self._on_frame_changed)
    except (RuntimeError, AttributeError):
        pass

    # ... same pattern for remaining 7 checks
```

##### **3. ui/controllers/signal_connection_manager.py (5 instances)**

**Before:**
```python
def __del__(self) -> None:
    """Disconnect signals to prevent memory leaks."""
    try:
        if hasattr(self, "main_window") and hasattr(self.main_window, "file_operations"):
            file_ops = self.main_window.file_operations
            # ... disconnect 8 signals
```

**After:**
```python
def __del__(self) -> None:
    """Disconnect signals to prevent memory leaks."""
    try:
        if (
            self.main_window is not None
            and self.main_window.file_operations is not None
        ):
            file_ops = self.main_window.file_operations
            # ... disconnect 8 signals
```

##### **4. services/interaction_service.py (4 instances)**

**Lines 692, 696:**

**Before:**
```python
if undo_btn is not None and hasattr(undo_btn, "setEnabled"):
    undo_btn.setEnabled(can_undo)
if redo_btn is not None and hasattr(redo_btn, "setEnabled"):
    redo_btn.setEnabled(can_redo)
```

**After:**
```python
# Type hints should ensure buttons have setEnabled method
# If button exists, it has setEnabled (it's a QPushButton)
if undo_btn is not None:
    undo_btn.setEnabled(can_undo)
if redo_btn is not None:
    redo_btn.setEnabled(can_redo)
```

**Lines 1043, 1121:**

**Before:**
```python
if hasattr(view, "update"):
    view.update()
if hasattr(view, "pan_offset_y"):
    y_offset = view.pan_offset_y
```

**After:**
```python
# CurveViewProtocol guarantees these methods exist
view.update()
if view.pan_offset_y is not None:
    y_offset = view.pan_offset_y
```

##### **5. core/commands/shortcut_commands.py (3 instances)**

**Lines 51, 55, 77:**

**Before:**
```python
if not hasattr(main_window, "multi_point_controller"):
    return
if hasattr(main_window, "tracking_panel"):
    panel = main_window.tracking_panel
if hasattr(main_window, "tracking_panel") and main_window.tracking_panel:
    # ...
```

**After:**
```python
if main_window.multi_point_controller is None:
    return
if main_window.tracking_panel is not None:
    panel = main_window.tracking_panel
if main_window.tracking_panel is not None:
    # ...
```

##### **6. Remaining Files (2 instances each):**

Apply the same pattern to:
- `ui/controllers/ui_initialization_controller.py` (2 instances)
- `ui/controllers/multi_point_tracking_controller.py` (2 instances)
- `ui/controllers/point_editor_controller.py` (2 instances)
- `ui/tracking_points_panel.py` (1 instance)
- `ui/session_manager.py` (1 instance)
- `ui/global_event_filter.py` (1 instance)
- `ui/file_operations.py` (1 instance)
- `ui/curve_view_widget.py` (1 instance)
- `ui/main_window_builder.py` (1 instance)
- `ui/widgets/card.py` (1 instance)

#### **Automated Replacement Script:**

Create `tools/fix_hasattr.py`:

```python
#!/usr/bin/env python3
"""Replace hasattr() with None checks in production code."""

import re
from pathlib import Path

def fix_hasattr_pattern(content: str) -> str:
    """Replace common hasattr patterns with None checks."""

    # Pattern 1: hasattr(self, "attr")
    content = re.sub(
        r'hasattr\(self,\s*["\'](\w+)["\']\)',
        r'self.\1 is not None',
        content
    )

    # Pattern 2: hasattr(obj, "attr")
    content = re.sub(
        r'hasattr\((\w+),\s*["\'](\w+)["\']\)',
        r'\1.\2 is not None',
        content
    )

    return content

def process_file(file_path: Path) -> int:
    """Process a single file, return count of replacements."""
    content = file_path.read_text()
    original = content

    # Apply fixes
    content = fix_hasattr_pattern(content)

    if content != original:
        file_path.write_text(content)
        count = content.count(" is not None") - original.count(" is not None")
        print(f"Fixed {count} instances in {file_path}")
        return count
    return 0

def main():
    """Process all production files."""
    directories = ["ui", "services", "core"]
    total = 0

    for directory in directories:
        path = Path(directory)
        if path.exists():
            for py_file in path.rglob("*.py"):
                # Skip test files
                if "test" not in str(py_file):
                    total += process_file(py_file)

    print(f"\nTotal replacements: {total}")
    print("Please review changes and run tests!")

if __name__ == "__main__":
    main()
```

#### **Verification Steps:**

```bash
# 1. Count hasattr() before fix
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
# Should be: 46

# 2. Run automated fix
python3 tools/fix_hasattr.py

# 3. Count hasattr() after fix
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
# Should be: 0 (in production code)

# 4. Run type checker (should see improvement)
~/.local/bin/uv run ./bpr --errors-only
# Errors should remain 0, warnings should decrease

# 5. Run full test suite
~/.local/bin/uv run pytest tests/ -x -q
# All tests should pass

# 6. Spot check converted files
grep -A 2 "is not None" ui/controllers/timeline_controller.py | head -20
# Should show clean None checks in __del__
```

#### **Success Metrics:**
- ✅ 0 hasattr() in production code (ui/, services/, core/)
- ✅ All tests pass
- ✅ Type checker warnings reduced by ~8% (184 ignores removed)
- ✅ CLAUDE.md compliance achieved (prefer None checks over hasattr)
- ✅ Verify reduction: `basedpyright 2>&1 | grep reportUnnecessaryTypeIgnoreComment | wc -l` should show 0

---

### **Task 1.4: Verify FrameChangeCoordinator Implementation**
**Time:** 2-4 hours
**Files:** 1 file
**Impact:** Closes documentation-code gap

#### **Action Items:**

1. **Update Comments to Match Reality** (frame_change_coordinator.py:111):

**Before:**
```python
# Connect with default Qt.AutoConnection (DirectConnection for same thread)
```

**After:**
```python
# Connect with EXPLICIT Qt.QueuedConnection to defer execution
# This ensures deterministic ordering: State updates → Event loop → Coordinator
```

2. **Verify Deterministic Phase Ordering:**

Ensure `on_frame_changed()` method executes phases in correct order:
- Phase 1: Update background image
- Phase 2: Apply centering
- Phase 3: Invalidate caches
- Phase 4: Update timeline widgets
- Phase 5: Trigger repaint

3. **Add Unit Test for Signal Timing:**

Create `tests/test_frame_coordinator_timing.py`:

```python
"""Test FrameChangeCoordinator signal timing and ordering."""

import pytest
from PySide6.QtCore import QEventLoop, Qt
from ui.controllers.frame_change_coordinator import FrameChangeCoordinator

def test_frame_change_uses_queued_connection(main_window):
    """Verify frame_changed signal uses Qt.QueuedConnection."""
    coordinator = FrameChangeCoordinator(
        main_window,
        main_window.curve_widget,
        main_window.view_management,
        main_window.timeline_controller,
        main_window.timeline_tabs
    )
    coordinator.connect()

    # Get the signal connection
    frame_signal = main_window.state_manager.frame_changed

    # Verify connection exists
    assert frame_signal.receivers(frame_signal) > 0

    # Emit signal and verify it's queued (not immediate)
    call_count = 0
    original_method = coordinator.on_frame_changed

    def counting_wrapper(frame):
        nonlocal call_count
        call_count += 1
        original_method(frame)

    coordinator.on_frame_changed = counting_wrapper

    # Emit signal
    frame_signal.emit(42)

    # Should NOT have been called yet (queued)
    assert call_count == 0, "Signal should be queued, not immediate"

    # Process event loop
    loop = QEventLoop()
    loop.processEvents()

    # NOW it should have been called
    assert call_count == 1, "Signal should execute after event loop"

def test_deterministic_phase_ordering(main_window):
    """Verify coordinator executes phases in correct order."""
    coordinator = FrameChangeCoordinator(
        main_window,
        main_window.curve_widget,
        main_window.view_management,
        main_window.timeline_controller,
        main_window.timeline_tabs
    )

    execution_order = []

    # Patch methods to track execution order
    original_bg = coordinator._update_background
    original_center = coordinator._apply_centering
    original_cache = coordinator._invalidate_caches
    original_widgets = coordinator._update_timeline_widgets
    original_repaint = coordinator._trigger_repaint

    def track(phase):
        def wrapper(*args, **kwargs):
            execution_order.append(phase)
            return locals()[f"original_{phase}"](*args, **kwargs)
        return wrapper

    coordinator._update_background = track("bg")
    coordinator._apply_centering = track("center")
    coordinator._invalidate_caches = track("cache")
    coordinator._update_timeline_widgets = track("widgets")
    coordinator._trigger_repaint = track("repaint")

    # Trigger frame change
    coordinator.on_frame_changed(42)

    # Verify order
    assert execution_order == ["bg", "center", "cache", "widgets", "repaint"], \
        f"Wrong execution order: {execution_order}"
```

#### **Verification Steps:**

```bash
# 1. Run new timing tests
~/.local/bin/uv run pytest tests/test_frame_coordinator_timing.py -v

# 2. Verify comments match code
grep -A 5 "Connect with" ui/controllers/frame_change_coordinator.py

# 3. Run full coordinator tests
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v
```

#### **Success Metrics:**
- ✅ Comments accurately describe Qt.QueuedConnection usage
- ✅ New timing tests pass
- ✅ Phase ordering test passes
- ✅ Documentation matches implementation

---

### **Phase 1 Completion Checklist:**

```bash
# Run full verification suite
cat > verify_phase1.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Phase 1 Verification ==="

echo "1. Checking hasattr() count..."
COUNT=$(grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS: 0 hasattr() in production code"
else
    echo "❌ FAIL: Found $COUNT hasattr() instances"
    exit 1
fi

echo "2. Verifying worker thread QueuedConnection usage..."
COUNT=$(grep -r "worker.*\.connect" ui/ --include="*.py" -A 2 | grep "Qt.QueuedConnection" | wc -l)
if [ "$COUNT" -ge 8 ]; then
    echo "✅ PASS: $COUNT worker signals use QueuedConnection"
else
    echo "⚠️  WARNING: Only $COUNT worker signals found, expected 8+"
fi

echo "3. Running type checker..."
~/.local/bin/uv run ./bpr --errors-only
if [ $? -eq 0 ]; then
    echo "✅ PASS: Type checker clean"
else
    echo "❌ FAIL: Type errors found"
    exit 1
fi

echo "4. Running critical tests..."
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v
~/.local/bin/uv run pytest tests/test_timeline_scrubbing.py -v
~/.local/bin/uv run pytest tests/test_timeline_focus_behavior.py -v

echo "=== Phase 1 COMPLETE ==="
EOF

chmod +x verify_phase1.sh
./verify_phase1.sh
```

**Phase 1 Success Criteria:**
- ✅ 0 hasattr() in production code
- ✅ Worker threads use Qt.QueuedConnection (8+ signals verified)
- ✅ FrameChangeCoordinator uses Qt.QueuedConnection + UniqueConnection (verified)
- ✅ Modern PySide6 connection syntax adopted (type=Qt.ConnectionType.QueuedConnection)
- ✅ Qt Connection Policy documented in CLAUDE.md (thread affinity, UniqueConnection, best practices)
- ✅ 0 property setter race conditions
- ✅ All critical tests pass
- ✅ Type checker errors = 0
- ✅ 5-6 hours saved by skipping wasted StateManager work

---


---

**Navigation:**
- [← Back to Overview](README.md)
- [→ Next: Phase 2 Quick Wins](phase2_quick_wins.md)
- [Verification & Testing](verification_and_testing.md)
