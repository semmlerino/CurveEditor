# 🎯 PLAN TAU: Comprehensive Code Quality Improvement Plan
## **DO NOT DELETE**

**Created:** 2025-10-14
**Status:** READY FOR IMPLEMENTATION
**Total Estimated Effort:** 80-120 hours (2-3 weeks)
**Verified Issues:** 24/33 independently confirmed
**Expected Impact:** ~3,000 lines eliminated, 5 critical bugs fixed, architecture simplified

---

## 📋 **TABLE OF CONTENTS**

1. [Executive Summary](#executive-summary)
2. [Phase 1: Critical Safety Fixes (Week 1)](#phase-1-critical-safety-fixes-week-1)
3. [Phase 2: Quick Wins (Week 2)](#phase-2-quick-wins-week-2)
4. [Phase 3: Architectural Refactoring (Weeks 3-4)](#phase-3-architectural-refactoring-weeks-3-4)
5. [Phase 4: Polish & Optimization (Weeks 5-6)](#phase-4-polish--optimization-weeks-5-6)
6. [Verification & Testing Strategy](#verification--testing-strategy)
7. [Success Metrics](#success-metrics)
8. [Risk Mitigation](#risk-mitigation)
9. [Rollback Plan](#rollback-plan)

---

## 🎯 **EXECUTIVE SUMMARY**

This plan addresses **24 verified code quality issues** discovered through a three-agent code review, focusing on KISS/DRY violations in the frame/timeline/curve subsystems.

### **Critical Issues Fixed:**
- ✅ 5 property setter race conditions (timeline desync bugs)
- ✅ 46 hasattr() CLAUDE.md violations
- ✅ 0 explicit Qt.QueuedConnection (documentation mismatch)
- ✅ 2 god objects (2,645 lines → 7 focused services)

### **Code Reduction:**
- ~3,000 lines of unnecessary code eliminated
- ~1,258 duplications removed
- ~350 lines of deprecated delegation removed

### **Quality Improvements:**
- Type ignore count: 1,093 → ~700 (35% reduction)
- CLAUDE.md compliance: 100%
- Code-documentation alignment: Restored
- Single Responsibility Principle: Enforced

---

## 🔴 **PHASE 1: CRITICAL SAFETY FIXES (WEEK 1)**

**Objective:** Fix all race conditions, documentation mismatches, and CLAUDE.md violations
**Total Effort:** 25-35 hours
**Priority:** CRITICAL - Must complete before any other work

---

### **Task 1.1: Fix Property Setter Race Conditions**
**Time:** 4-6 hours
**Files:** 3 files
**Impact:** Prevents timeline desync bugs

#### **Issue Description:**
Property setters like `self.current_frame = N` update ApplicationState **synchronously**, but UI updates happen **later** via queued signal callbacks. This creates a race window where State=N but UI=N-1.

#### **Files to Fix:**

##### **1. ui/state_manager.py:454**

**Current (BUGGY):**
```python
def _on_show_all_curves_changed(self, show_all: bool) -> None:
    """Handle show all curves toggle."""
    if show_all:
        # Reset to first frame when showing all curves
        self.current_frame = 1  # ❌ BUG: Synchronous property write
```

**Fixed:**
```python
def _on_show_all_curves_changed(self, show_all: bool) -> None:
    """Handle show all curves toggle."""
    if show_all:
        # Update internal tracking FIRST
        self._internal_frame = 1

        # Update UI immediately (if we have UI components)
        if hasattr(self, '_frame_spinbox') and self._frame_spinbox is not None:
            self._frame_spinbox.setValue(1)

        # Then delegate to ApplicationState (triggers queued callbacks)
        self.current_frame = 1
```

##### **2. ui/state_manager.py:536**

**Current (BUGGY):**
```python
def _on_total_frames_changed(self, new_total: int) -> None:
    """Handle total frames change."""
    if self._current_frame > new_total:
        self.current_frame = new_total  # ❌ BUG: Synchronous property write
```

**Fixed:**
```python
def _on_total_frames_changed(self, new_total: int) -> None:
    """Handle total frames change."""
    if self._current_frame > new_total:
        # Update internal tracking FIRST
        self._internal_frame = new_total

        # Update UI immediately
        if hasattr(self, '_frame_spinbox') and self._frame_spinbox is not None:
            self._frame_spinbox.setValue(new_total)

        # Then delegate to ApplicationState
        self.current_frame = new_total
```

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
# 1. Search for all property writes that might have this issue
grep -rn "self.current_frame = " ui/ --include="*.py"

# 2. Run timeline desync tests
~/.local/bin/uv run pytest tests/test_timeline_scrubbing.py -v
~/.local/bin/uv run pytest tests/test_timeline_focus_behavior.py -v
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v

# 3. Manual test: Rapid timeline clicking should stay in sync
# Run app, load data, rapidly click different timeline tabs
# UI should always match ApplicationState
```

#### **Success Metrics:**
- ✅ All 3 property writes use internal tracking pattern
- ✅ All timeline tests pass
- ✅ Manual rapid-clicking test shows no desync

---

### **Task 1.2: Add Explicit Qt.QueuedConnection**
**Time:** 6-8 hours
**Files:** 7 files, 50+ signal connections
**Impact:** Matches documentation/commit messages, prevents race conditions

#### **Issue Description:**
Documentation and commit messages claim Qt.QueuedConnection is used, but actual code uses default Qt.AutoConnection (which resolves to DirectConnection for same-thread = SYNCHRONOUS).

#### **Pattern to Apply:**

**Before (Implicit):**
```python
_ = self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)
```

**After (Explicit):**
```python
from PySide6.QtCore import Qt

_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    Qt.QueuedConnection  # Explicit: defer to event loop
)
```

#### **Files to Update:**

##### **1. ui/controllers/frame_change_coordinator.py (HIGH PRIORITY)**

**Lines 110-118:**
```python
def connect(self) -> None:
    """Connect to signals with explicit connection types."""
    if self._connected:
        return

    from PySide6.QtCore import Qt

    # Connect with EXPLICIT Qt.QueuedConnection for cross-component frame changes
    # This ensures deterministic ordering: ApplicationState updates first,
    # then coordinator callback runs after event loop processes
    _ = self.main_window.state_manager.frame_changed.connect(
        self.on_frame_changed,
        Qt.QueuedConnection  # EXPLICIT: Defer to event loop
    )

    # Connect to playback signals for cache optimization
    if self.timeline_controller:
        _ = self.timeline_controller.playback_started.connect(
            self._on_playback_started,
            Qt.QueuedConnection  # EXPLICIT
        )
        _ = self.timeline_controller.playback_stopped.connect(
            self._on_playback_stopped,
            Qt.QueuedConnection  # EXPLICIT
        )

    self._connected = True
    logger.debug("FrameChangeCoordinator signals connected with Qt.QueuedConnection")
```

##### **2. ui/state_manager.py (HIGH PRIORITY)**

**Lines 70-73:**
```python
from PySide6.QtCore import Qt

# Forward ApplicationState signals with EXPLICIT QueuedConnection
# This ensures subscribers receive signals in next event loop iteration,
# preventing synchronous nested execution
_ = self._app_state.frame_changed.connect(
    self.frame_changed.emit,
    Qt.QueuedConnection  # EXPLICIT: Prevent nested execution
)

_ = self._app_state.selection_changed.connect(
    self._on_app_state_selection_changed,
    Qt.QueuedConnection  # EXPLICIT
)
```

##### **3. ui/controllers/signal_connection_manager.py**

**Lines 143-232 (40+ connections):**

Apply this pattern to ALL ApplicationState signal connections:

```python
from PySide6.QtCore import Qt

# File operation signals (worker thread → main thread)
_ = self.main_window.file_operations.tracking_data_loaded.connect(
    ...,
    Qt.QueuedConnection  # EXPLICIT: Cross-thread
)

# State manager signals (cross-component)
_ = self.main_window.state_manager.frame_changed.connect(
    ...,
    Qt.QueuedConnection  # EXPLICIT: Prevent nested execution
)

# Apply to all ~40 connections in this file
```

##### **4. ui/controllers/timeline_controller.py**

**Lines 97, 197-206:**

Widget signals (spinbox, slider) can remain DirectConnection (same object):
```python
# Widget signals within same controller - DirectConnection is fine
_ = self.playback_timer.timeout.connect(self._on_playback_timer)
_ = self.frame_spinbox.valueChanged.connect(self._on_frame_changed)
```

But timeline controller's outgoing signals should be explicit:
```python
from PySide6.QtCore import Qt

# Outgoing frame_changed signal should be explicit for subscribers
# (subscribers will receive this via QueuedConnection if they request it)
```

##### **5. ui/timeline_tabs.py**

**Lines 376-378:**
```python
from PySide6.QtCore import Qt

_ = self._app_state.curves_changed.connect(
    self._on_curves_changed,
    Qt.QueuedConnection  # EXPLICIT: Cross-component
)
_ = self._app_state.active_curve_changed.connect(
    self._on_active_curve_changed,
    Qt.QueuedConnection  # EXPLICIT
)
_ = self._app_state.selection_changed.connect(
    self._on_selection_changed,
    Qt.QueuedConnection  # EXPLICIT
)
```

##### **6. ui/image_sequence_browser.py (Cross-Thread)**

**Lines for DirectoryScanWorker and thumbnail workers:**
```python
from PySide6.QtCore import Qt

# Worker thread signals MUST use QueuedConnection
worker.progress.connect(
    self._on_scan_progress,
    Qt.QueuedConnection  # EXPLICIT: Worker → Main thread
)
worker.sequences_found.connect(
    self._on_sequences_found,
    Qt.QueuedConnection  # EXPLICIT: Worker → Main thread
)
worker.finished.connect(
    self._on_scan_finished,
    Qt.QueuedConnection  # EXPLICIT: Worker → Main thread
)
worker.error.connect(
    self._on_scan_error,
    Qt.QueuedConnection  # EXPLICIT: Worker → Main thread
)
```

##### **7. ui/controllers/multi_point_tracking_controller.py**

**Lines 62-64:**
```python
from PySide6.QtCore import Qt

_ = self._app_state.curves_changed.connect(
    self._on_curves_changed,
    Qt.QueuedConnection  # EXPLICIT
)
_ = self._app_state.active_curve_changed.connect(
    self._on_active_curve_changed,
    Qt.QueuedConnection  # EXPLICIT
)
_ = self._app_state.selection_state_changed.connect(
    self._on_selection_state_changed,
    Qt.QueuedConnection  # EXPLICIT
)
```

#### **Verification Steps:**

```bash
# 1. Verify all connections now explicit
grep -rn "\.connect(" ui/controllers/ | grep -v "Qt.QueuedConnection" | grep -v "Qt.DirectConnection"
# Should show only widget-internal connections (spinbox, slider, etc.)

# 2. Count explicit QueuedConnection uses (should be 50+)
grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | wc -l

# 3. Run signal timing tests
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v

# 4. Check for race conditions
~/.local/bin/uv run pytest tests/test_timeline_scrubbing.py -v -k rapid

# 5. Manual verification: Run app, enable debug logging, verify signal order
# Look for "Queued connection" messages in logs
```

#### **Success Metrics:**
- ✅ 50+ explicit Qt.QueuedConnection connections added
- ✅ 0 implicit connections for cross-component signals
- ✅ All timing tests pass
- ✅ No race condition warnings in tests

---

### **Task 1.3: Replace All hasattr() with None Checks**
**Time:** 8-12 hours
**Files:** 15 files, 46 instances
**Impact:** CLAUDE.md compliance, type safety, reduces type ignores by ~30%

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
- ✅ Type checker warnings reduced by ~30%
- ✅ CLAUDE.md compliance achieved

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

echo "2. Checking Qt.QueuedConnection count..."
COUNT=$(grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | wc -l)
if [ "$COUNT" -ge 50 ]; then
    echo "✅ PASS: $COUNT explicit QueuedConnection uses"
else
    echo "❌ FAIL: Only $COUNT explicit uses, need 50+"
    exit 1
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
- ✅ 50+ explicit Qt.QueuedConnection connections
- ✅ 0 property setter race conditions
- ✅ All critical tests pass
- ✅ Type checker errors = 0
- ✅ Documentation matches code

---

## ⚡ **PHASE 2: QUICK WINS (WEEK 2)**

**Objective:** High-impact, low-effort improvements
**Total Effort:** 15 hours
**Priority:** HIGH - Fast ROI

---

### **Task 2.1: Frame Clamping Utility**
**Time:** 4 hours
**Impact:** Eliminates 60 duplications

#### **Implementation:**

**1. Create utility module: `core/frame_utils.py`**

```python
"""Frame manipulation utilities."""

def clamp_frame(frame: int, min_frame: int, max_frame: int) -> int:
    """Clamp frame value to valid range [min_frame, max_frame].

    Args:
        frame: Frame number to clamp
        min_frame: Minimum valid frame (inclusive)
        max_frame: Maximum valid frame (inclusive)

    Returns:
        Clamped frame value

    Examples:
        >>> clamp_frame(5, 1, 10)
        5
        >>> clamp_frame(0, 1, 10)
        1
        >>> clamp_frame(15, 1, 10)
        10
    """
    return max(min_frame, min(max_frame, frame))


def is_frame_in_range(frame: int, min_frame: int, max_frame: int) -> bool:
    """Check if frame is within valid range.

    Args:
        frame: Frame number to check
        min_frame: Minimum valid frame (inclusive)
        max_frame: Maximum valid frame (inclusive)

    Returns:
        True if frame is in range

    Examples:
        >>> is_frame_in_range(5, 1, 10)
        True
        >>> is_frame_in_range(0, 1, 10)
        False
    """
    return min_frame <= frame <= max_frame
```

**2. Create tests: `tests/test_frame_utils.py`**

```python
"""Tests for frame manipulation utilities."""

import pytest
from core.frame_utils import clamp_frame, is_frame_in_range


class TestClampFrame:
    """Tests for clamp_frame function."""

    def test_frame_within_range(self):
        """Frame within range should be unchanged."""
        assert clamp_frame(5, 1, 10) == 5
        assert clamp_frame(1, 1, 10) == 1
        assert clamp_frame(10, 1, 10) == 10

    def test_frame_below_min(self):
        """Frame below min should be clamped to min."""
        assert clamp_frame(0, 1, 10) == 1
        assert clamp_frame(-5, 1, 10) == 1

    def test_frame_above_max(self):
        """Frame above max should be clamped to max."""
        assert clamp_frame(11, 1, 10) == 10
        assert clamp_frame(100, 1, 10) == 10

    def test_single_frame_range(self):
        """Range with min == max should return that frame."""
        assert clamp_frame(0, 5, 5) == 5
        assert clamp_frame(5, 5, 5) == 5
        assert clamp_frame(10, 5, 5) == 5


class TestIsFrameInRange:
    """Tests for is_frame_in_range function."""

    def test_frame_in_range(self):
        """Frame in range should return True."""
        assert is_frame_in_range(5, 1, 10) is True
        assert is_frame_in_range(1, 1, 10) is True
        assert is_frame_in_range(10, 1, 10) is True

    def test_frame_out_of_range(self):
        """Frame out of range should return False."""
        assert is_frame_in_range(0, 1, 10) is False
        assert is_frame_in_range(11, 1, 10) is False
```

**3. Update call sites (19 files):**

**ui/timeline_tabs.py:329, 677:**
```python
# Before:
frame = max(self.min_frame, min(self.max_frame, frame))

# After:
from core.frame_utils import clamp_frame
frame = clamp_frame(frame, self.min_frame, self.max_frame)
```

**stores/frame_store.py:99:**
```python
# Before:
frame = max(self._min_frame, min(frame, self._max_frame))

# After:
from core.frame_utils import clamp_frame
frame = clamp_frame(frame, self._min_frame, self._max_frame)
```

**ui/controllers/timeline_controller.py:278:**
```python
# Before:
frame = max(1, min(frame, self.frame_spinbox.maximum()))

# After:
from core.frame_utils import clamp_frame
frame = clamp_frame(frame, 1, self.frame_spinbox.maximum())
```

**Automated replacement script: `tools/replace_frame_clamping.py`**

```python
#!/usr/bin/env python3
"""Replace frame clamping duplications with utility function."""

import re
from pathlib import Path

PATTERN = re.compile(
    r'(\w+)\s*=\s*max\(([^,]+),\s*min\(([^,]+),\s*\1\)\)',
    re.MULTILINE
)

def replace_clamping(content: str, file_path: Path) -> tuple[str, int]:
    """Replace frame clamping patterns."""

    replacements = 0
    lines = content.split('\n')
    new_lines = []
    needs_import = False

    for line in lines:
        match = PATTERN.search(line)
        if match:
            var, min_val, max_val = match.groups()
            indent = len(line) - len(line.lstrip())
            replacement = f"{' ' * indent}{var} = clamp_frame({var}, {min_val}, {max_val})"
            new_lines.append(replacement)
            needs_import = True
            replacements += 1
            print(f"  Replaced: {line.strip()}")
            print(f"  With:     {replacement.strip()}")
        else:
            new_lines.append(line)

    content = '\n'.join(new_lines)

    # Add import if needed
    if needs_import and 'from core.frame_utils import clamp_frame' not in content:
        # Find first import block
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i

        lines.insert(import_index + 1, 'from core.frame_utils import clamp_frame')
        content = '\n'.join(lines)

    return content, replacements

def main():
    """Process all files with frame clamping."""
    files_with_pattern = [
        "ui/timeline_tabs.py",
        "stores/frame_store.py",
        "ui/controllers/timeline_controller.py",
        # Add more files as found by grep
    ]

    total = 0
    for file_path in files_with_pattern:
        path = Path(file_path)
        if path.exists():
            print(f"\nProcessing {file_path}...")
            content = path.read_text()
            new_content, count = replace_clamping(content, path)
            if count > 0:
                path.write_text(new_content)
                total += count
                print(f"  Fixed {count} instances")

    print(f"\n✅ Total replacements: {total}")

if __name__ == "__main__":
    main()
```

#### **Verification Steps:**

```bash
# 1. Create and test utility
~/.local/bin/uv run pytest tests/test_frame_utils.py -v

# 2. Find all clamping patterns
grep -rn "max.*min.*frame" ui/ stores/ core/ --include="*.py"

# 3. Run replacement script
python3 tools/replace_frame_clamping.py

# 4. Verify imports added
grep -r "from core.frame_utils import clamp_frame" ui/ stores/ --include="*.py"

# 5. Run tests to ensure behavior unchanged
~/.local/bin/uv run pytest tests/ -k frame -v
```

#### **Success Metrics:**
- ✅ 60+ uses of `clamp_frame()` instead of inline clamping
- ✅ All frame-related tests pass
- ✅ New utility has 100% test coverage

---

### **Task 2.2: Remove Redundant list() in deepcopy()**
**Time:** 2-3 hours
**Impact:** Code clarity + slight performance

#### **Files to Fix:**

**core/commands/curve_commands.py (Multiple instances):**

**Lines 48-49:**
```python
# Before:
self.new_data: list[LegacyPointData] = copy.deepcopy(list(new_data))
self.old_data: list[LegacyPointData] | None = copy.deepcopy(list(old_data)) if old_data is not None else None

# After:
self.new_data: list[LegacyPointData] = copy.deepcopy(new_data)
self.old_data: list[LegacyPointData] | None = copy.deepcopy(old_data) if old_data is not None else None
```

**Lines 133-134:**
```python
# Before:
self.old_points: list[LegacyPointData] | None = copy.deepcopy(list(old_points)) if old_points else None
self.new_points: list[LegacyPointData] | None = copy.deepcopy(list(new_points)) if new_points else None

# After:
self.old_points: list[LegacyPointData] | None = copy.deepcopy(old_points) if old_points else None
self.new_points: list[LegacyPointData] | None = copy.deepcopy(new_points) if new_points else None
```

**Automated fix script: `tools/fix_deepcopy_list.py`**

```python
#!/usr/bin/env python3
"""Remove redundant list() wrapper around copy.deepcopy()."""

import re
from pathlib import Path

PATTERN = re.compile(r'copy\.deepcopy\(list\(([^)]+)\)\)')

def fix_deepcopy(content: str) -> tuple[str, int]:
    """Replace deepcopy(list(x)) with deepcopy(x)."""
    replacements = 0

    def replacer(match):
        nonlocal replacements
        replacements += 1
        return f'copy.deepcopy({match.group(1)})'

    new_content = PATTERN.sub(replacer, content)
    return new_content, replacements

def main():
    """Process command files."""
    files = [
        "core/commands/curve_commands.py",
        "core/commands/insert_track_command.py",
    ]

    total = 0
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            new_content, count = fix_deepcopy(content)
            if count > 0:
                path.write_text(new_content)
                print(f"Fixed {count} instances in {file_path}")
                total += count

    print(f"\n✅ Total replacements: {total}")

if __name__ == "__main__":
    main()
```

#### **Verification Steps:**

```bash
# 1. Find pattern
grep -rn "deepcopy(list(" core/commands/ --include="*.py"

# 2. Run fix
python3 tools/fix_deepcopy_list.py

# 3. Verify gone
grep -rn "deepcopy(list(" core/commands/ --include="*.py"
# Should be: 0 results

# 4. Run command tests
~/.local/bin/uv run pytest tests/test_curve_commands.py -v
~/.local/bin/uv run pytest tests/test_insert_track_command.py -v
```

#### **Success Metrics:**
- ✅ 0 instances of `deepcopy(list(x))` pattern
- ✅ All command tests pass
- ✅ Undo/redo functionality unchanged

---

### **Task 2.3: Frame Status NamedTuple**
**Time:** 4 hours
**Impact:** Type safety + readability

#### **Implementation:**

**1. Add NamedTuple to `core/models.py`:**

```python
from typing import NamedTuple

class FrameStatus(NamedTuple):
    """Status information for a single frame in timeline.

    Attributes:
        keyframe_count: Number of keyframe points
        interpolated_count: Number of interpolated points
        tracked_count: Number of tracked points
        endframe_count: Number of endframe points
        normal_count: Number of normal points
        is_startframe: True if this is the first frame with data
        is_inactive: True if frame has no active tracking
        has_selected: True if any points are selected in this frame
    """
    keyframe_count: int
    interpolated_count: int
    tracked_count: int
    endframe_count: int
    normal_count: int
    is_startframe: bool
    is_inactive: bool
    has_selected: bool

    @property
    def total_points(self) -> int:
        """Total number of points in this frame."""
        return (
            self.keyframe_count
            + self.interpolated_count
            + self.tracked_count
            + self.endframe_count
            + self.normal_count
        )

    @property
    def is_empty(self) -> bool:
        """True if frame has no points."""
        return self.total_points == 0
```

**2. Update `services/data_service.py` return type:**

```python
def get_frame_range_point_status(
    self,
    curve_data: CurveDataList,
    selected_indices: set[int] | None = None,
) -> dict[int, FrameStatus]:  # Changed from dict[int, tuple]
    """Get point status information for each frame.

    Returns:
        Dictionary mapping frame number to FrameStatus
    """
    from core.models import FrameStatus

    frame_status: dict[int, FrameStatus] = {}

    # ... existing logic ...

    # Instead of returning tuple:
    # return (keyframe_count, interpolated_count, ...)

    # Return NamedTuple:
    frame_status[frame] = FrameStatus(
        keyframe_count=keyframe_count,
        interpolated_count=interpolated_count,
        tracked_count=tracked_count,
        endframe_count=endframe_count,
        normal_count=normal_count,
        is_startframe=is_startframe,
        is_inactive=is_inactive,
        has_selected=has_selected,
    )

    return frame_status
```

**3. Update consumers (5 callsites):**

**ui/timeline_tabs.py:441-450:**

**Before:**
```python
(
    keyframe_count,
    interpolated_count,
    tracked_count,
    endframe_count,
    _normal_count,
    is_startframe,
    is_inactive,
    has_selected,
) = status_data
```

**After:**
```python
# Direct attribute access - much cleaner!
status = status_data
keyframe_count = status.keyframe_count
interpolated_count = status.interpolated_count
tracked_count = status.tracked_count
endframe_count = status.endframe_count
is_startframe = status.is_startframe
is_inactive = status.is_inactive
has_selected = status.has_selected

# Or even better - use status directly:
if status.has_selected:
    # ...
if status.is_startframe:
    # ...
```

Apply same pattern to all 5 callsites.

#### **Verification Steps:**

```bash
# 1. Find all tuple unpacking sites
grep -rn "keyframe_count," ui/ --include="*.py" -A 10

# 2. Run tests
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
~/.local/bin/uv run pytest tests/test_data_service.py -v

# 3. Type check
~/.local/bin/uv run ./bpr ui/timeline_tabs.py
# Should show improved type inference
```

#### **Success Metrics:**
- ✅ FrameStatus NamedTuple defined with docstrings
- ✅ All 5 callsites updated to use named attributes
- ✅ All timeline tests pass
- ✅ Type checker shows improved inference

---

### **Task 2.4: Frame Range Extraction Utility**
**Time:** 3 hours
**Impact:** DRY compliance

#### **Implementation:**

**Add to `core/frame_utils.py`:**

```python
from core.type_aliases import CurveDataList

def get_frame_range_from_curve(curve_data: CurveDataList) -> tuple[int, int] | None:
    """Extract min/max frame numbers from curve data.

    Args:
        curve_data: List of curve points (frame, x, y, ...) tuples

    Returns:
        (min_frame, max_frame) or None if no valid frames found

    Examples:
        >>> data = [(1, 10.0, 20.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        >>> get_frame_range_from_curve(data)
        (1, 5)
        >>> get_frame_range_from_curve([])
        None
    """
    if not curve_data:
        return None

    frames = [int(point[0]) for point in curve_data if len(point) >= 3]
    if not frames:
        return None

    return (min(frames), max(frames))


def get_frame_range_with_limits(
    curve_data: CurveDataList,
    max_range: int = 200,
) -> tuple[int, int] | None:
    """Extract frame range with optional limiting for performance.

    Args:
        curve_data: List of curve points
        max_range: Maximum frame range allowed (for UI performance)

    Returns:
        (min_frame, limited_max_frame) or None

    Examples:
        >>> data = [(1, 0, 0), (1000, 0, 0)]  # Very wide range
        >>> get_frame_range_with_limits(data, max_range=200)
        (1, 200)  # Limited to 200 frames
    """
    range_result = get_frame_range_from_curve(curve_data)
    if range_result is None:
        return None

    min_frame, max_frame = range_result

    # Limit range for performance
    if max_frame - min_frame + 1 > max_range:
        max_frame = min_frame + max_range - 1

    return (min_frame, max_frame)
```

**Add tests to `tests/test_frame_utils.py`:**

```python
class TestGetFrameRangeFromCurve:
    """Tests for get_frame_range_from_curve function."""

    def test_normal_curve(self):
        """Normal curve should return min/max frames."""
        data = [(1, 10.0, 20.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        assert get_frame_range_from_curve(data) == (1, 5)

    def test_empty_curve(self):
        """Empty curve should return None."""
        assert get_frame_range_from_curve([]) is None

    def test_single_point(self):
        """Single point should return same frame for min/max."""
        data = [(42, 10.0, 20.0)]
        assert get_frame_range_from_curve(data) == (42, 42)

    def test_invalid_points_skipped(self):
        """Points with < 3 elements should be skipped."""
        data = [(1, 10.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        assert get_frame_range_from_curve(data) == (3, 5)


class TestGetFrameRangeWithLimits:
    """Tests for get_frame_range_with_limits function."""

    def test_within_limit(self):
        """Range within limit should be unchanged."""
        data = [(1, 0, 0), (50, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 50)

    def test_exceeds_limit(self):
        """Range exceeding limit should be truncated."""
        data = [(1, 0, 0), (1000, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 200)
```

**Update call sites:**

**ui/controllers/multi_point_tracking_controller.py:823-845:**

**Before:**
```python
def _update_frame_range_from_data(self, curve_data: CurveDataList) -> None:
    """Update frame range based on single curve data."""
    if not curve_data:
        return

    frames = [int(point[0]) for point in curve_data if len(point) >= 3]
    if frames:
        min_frame = min(frames)
        max_frame = max(frames)
        # ... set frame range ...
```

**After:**
```python
from core.frame_utils import get_frame_range_from_curve

def _update_frame_range_from_data(self, curve_data: CurveDataList) -> None:
    """Update frame range based on single curve data."""
    frame_range = get_frame_range_from_curve(curve_data)
    if frame_range is not None:
        min_frame, max_frame = frame_range
        # ... set frame range ...
```

**ui/timeline_tabs.py:417-434:**

**Before:**
```python
frames = [int(point[0]) for point in curve_data if len(point) >= 3]
if frames:
    min_frame = min(frames)
    max_frame = max(frames)

    # Also consider image sequence
    if self._state_manager:
        image_sequence_frames = self._state_manager.total_frames
        max_frame = max(max_frame, image_sequence_frames)

    # Limit to reasonable number
    max_timeline_frames = 200
    if max_frame - min_frame + 1 > max_timeline_frames:
        max_frame = min_frame + max_timeline_frames - 1
```

**After:**
```python
from core.frame_utils import get_frame_range_with_limits

frame_range = get_frame_range_from_curve(curve_data)
if frame_range is not None:
    min_frame, max_frame = frame_range

    # Also consider image sequence
    if self._state_manager:
        image_sequence_frames = self._state_manager.total_frames
        max_frame = max(max_frame, image_sequence_frames)

    # Apply limit for performance
    _, max_frame = get_frame_range_with_limits(
        [(min_frame, 0, 0), (max_frame, 0, 0)],
        max_range=200
    )
```

#### **Verification Steps:**

```bash
# 1. Run new tests
~/.local/bin/uv run pytest tests/test_frame_utils.py::TestGetFrameRangeFromCurve -v

# 2. Update call sites
# (Manual - only 2 files)

# 3. Run affected tests
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
```

#### **Success Metrics:**
- ✅ 2 utilities added with tests
- ✅ 2 callsites simplified
- ✅ All tests pass

---

### **Task 2.5: Remove SelectionContext Enum**
**Time:** 4 hours
**Impact:** Simplifies branching logic

#### **Implementation:**

**1. Identify current SelectionContext usage:**

```bash
grep -rn "SelectionContext" ui/controllers/multi_point_tracking_controller.py
```

**2. Replace with explicit methods:**

**Before (Lines 688-821 - 134-line method with branching):**
```python
def update_curve_display(
    self,
    context: SelectionContext = SelectionContext.DEFAULT,
    selected_points: list[str] | None = None,
) -> None:
    """Update curve display based on context."""

    # ... 50 lines of setup ...

    if context == SelectionContext.DEFAULT:
        # Preserve selection
        self.main_window.curve_widget.set_curves_data(
            all_curves_data, metadata, active_curve
        )
    elif context == SelectionContext.MANUAL_SELECTION:
        # Use provided selection
        selected_curves_list = selected_points or []
        self.main_window.curve_widget.set_curves_data(
            all_curves_data, metadata, active_curve, selected_curves=selected_curves_list
        )
    else:
        # Reset to active curve
        self.main_window.curve_widget.set_curves_data(
            all_curves_data, metadata, active_curve, selected_curves=[active_curve]
        )
```

**After (3 focused methods):**
```python
def update_display_preserve_selection(self) -> None:
    """Update display, preserving current selection."""
    curves, metadata, active = self._prepare_display_data()
    self.main_window.curve_widget.set_curves_data(curves, metadata, active)


def update_display_with_selection(self, selected: list[str]) -> None:
    """Update display with specific curve selection.

    Args:
        selected: List of curve names to select
    """
    curves, metadata, active = self._prepare_display_data()
    self.main_window.curve_widget.set_curves_data(
        curves, metadata, active, selected_curves=selected
    )


def update_display_reset_selection(self) -> None:
    """Update display, resetting selection to active curve only."""
    curves, metadata, active = self._prepare_display_data()
    selected = [active] if active else []
    self.main_window.curve_widget.set_curves_data(
        curves, metadata, active, selected_curves=selected
    )


def _prepare_display_data(self) -> tuple[dict, dict, str | None]:
    """Prepare curve data for display (common logic).

    Returns:
        (all_curves_data, metadata, active_curve)
    """
    # ... extract common setup logic from old update_curve_display ...
    active_curve = self._app_state.active_curve

    # Get all curves
    all_curves_data = {}
    metadata = {}
    for curve_name in self._app_state.get_all_curve_names():
        curve_data = self._app_state.get_curve_data(curve_name)
        if curve_data:
            all_curves_data[curve_name] = curve_data
            metadata[curve_name] = self._app_state.get_curve_metadata(curve_name)

    return all_curves_data, metadata, active_curve
```

**3. Update all callsites:**

**Before:**
```python
# Various calls with context enum
self.update_curve_display(SelectionContext.DEFAULT)
self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=points)
self.update_curve_display(SelectionContext.DATA_LOADING)
```

**After:**
```python
# Explicit method calls - self-documenting
self.update_display_preserve_selection()
self.update_display_with_selection(points)
self.update_display_reset_selection()
```

**4. Remove SelectionContext enum:**

Delete from file or mark as deprecated if external code uses it.

#### **Verification Steps:**

```bash
# 1. Find all SelectionContext uses
grep -rn "SelectionContext" ui/ --include="*.py"

# 2. After refactoring, should only be in tests (if any)

# 3. Run controller tests
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v

# 4. Manual test: Load multi-point data, verify display updates correctly
```

#### **Success Metrics:**
- ✅ SelectionContext enum removed
- ✅ 3 focused methods replace 1 complex method
- ✅ All branching logic eliminated
- ✅ All tests pass

---

### **Phase 2 Completion Checklist:**

```bash
cat > verify_phase2.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Phase 2 Verification ==="

echo "1. Frame clamping utility..."
if grep -q "from core.frame_utils import clamp_frame" ui/timeline_tabs.py; then
    echo "✅ PASS: clamp_frame utility in use"
else
    echo "❌ FAIL: clamp_frame not imported"
    exit 1
fi

echo "2. Redundant list() removed..."
COUNT=$(grep -r "deepcopy(list(" core/commands/ --include="*.py" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS: No redundant list() in deepcopy"
else
    echo "❌ FAIL: Found $COUNT redundant list() patterns"
    exit 1
fi

echo "3. FrameStatus NamedTuple..."
if grep -q "class FrameStatus(NamedTuple):" core/models.py; then
    echo "✅ PASS: FrameStatus defined"
else
    echo "❌ FAIL: FrameStatus not found"
    exit 1
fi

echo "4. SelectionContext removed..."
COUNT=$(grep -r "SelectionContext\." ui/controllers/multi_point_tracking_controller.py | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS: SelectionContext enum removed"
else
    echo "❌ FAIL: SelectionContext still in use ($COUNT instances)"
    exit 1
fi

echo "5. Running Quick Win tests..."
~/.local/bin/uv run pytest tests/test_frame_utils.py -v
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
~/.local/bin/uv run pytest tests/test_curve_commands.py -v

echo "=== Phase 2 COMPLETE ==="
EOF

chmod +x verify_phase2.sh
./verify_phase2.sh
```

**Phase 2 Success Criteria:**
- ✅ ~300 lines of duplicated code eliminated
- ✅ 5 new utilities added
- ✅ All Quick Win tests pass
- ✅ Type safety improved (FrameStatus)
- ✅ Code readability improved

---

## 🏗️ **PHASE 3: ARCHITECTURAL REFACTORING (WEEKS 3-4)**

**Objective:** Split god objects, remove technical debt
**Total Effort:** 10-12 days
**Priority:** HIGH - Architecture quality

---

### **Task 3.1: Split MultiPointTrackingController**
**Time:** 2-3 days
**Impact:** 1,165 lines → 3 controllers (~400 lines each)

#### **Current Issues:**
- Handles 7 different concerns in one 1,165-line class
- 30 methods with unclear responsibilities
- Difficult to test (mock 20+ dependencies)

#### **New Architecture:**

```
MultiPointTrackingController (1,165 lines)
    ↓ SPLIT INTO ↓
├── TrackingDataController (~400 lines)
│   ├── load_single_point_data()
│   ├── load_multi_point_data()
│   ├── _parse_tracking_file()
│   └── _validate_tracking_data()
│
├── TrackingDisplayController (~400 lines)
│   ├── update_display_preserve_selection()
│   ├── update_display_with_selection()
│   ├── update_display_reset_selection()
│   ├── _prepare_display_data()
│   └── _update_timeline_for_tracking()
│
└── TrackingSelectionController (~350 lines)
    ├── sync_panel_to_view()
    ├── sync_view_to_panel()
    ├── handle_panel_selection_changed()
    └── handle_view_selection_changed()
```

#### **Implementation Plan:**

**Step 1: Create new controller files**

**File: `ui/controllers/tracking_data_controller.py`**

```python
"""Controller for loading and validating tracking data."""

from pathlib import Path
from PySide6.QtCore import QObject, Signal
from stores.application_state import get_application_state
from core.type_aliases import CurveDataList

class TrackingDataController(QObject):
    """Handles loading tracking data from files.

    Responsibilities:
        - Load single-point tracking data
        - Load multi-point tracking data
        - Parse and validate tracking files
        - Emit signals when data loaded

    Signals:
        data_loaded: Emitted when tracking data successfully loaded
                     Args: (curve_name, curve_data)
        load_error: Emitted when loading fails
                    Args: (error_message)
    """

    data_loaded = Signal(str, list)  # curve_name, curve_data
    load_error = Signal(str)

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize tracking data controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window
        self._app_state = get_application_state()

    def load_single_point_data(self, file_path: Path) -> bool:
        """Load single tracking point from file.

        Args:
            file_path: Path to tracking data file

        Returns:
            True if loaded successfully
        """
        try:
            # Extract logic from MultiPointTrackingController.load_single_point_tracking_data
            data = self._parse_tracking_file(file_path)
            if not data:
                self.load_error.emit(f"No valid data in {file_path.name}")
                return False

            # Validate data
            if not self._validate_tracking_data(data):
                self.load_error.emit(f"Invalid data format in {file_path.name}")
                return False

            # Store in ApplicationState
            curve_name = file_path.stem
            self._app_state.set_curve_data(curve_name, data)

            # Emit success signal
            self.data_loaded.emit(curve_name, data)
            return True

        except Exception as e:
            self.load_error.emit(f"Error loading {file_path.name}: {e}")
            return False

    def load_multi_point_data(self, tracking_data: dict[str, CurveDataList]) -> bool:
        """Load multiple tracking points.

        Args:
            tracking_data: Dictionary mapping curve names to curve data

        Returns:
            True if loaded successfully
        """
        # Extract logic from MultiPointTrackingController.load_multi_point_tracking_data
        pass

    def _parse_tracking_file(self, file_path: Path) -> CurveDataList:
        """Parse tracking data from file.

        Args:
            file_path: Path to file

        Returns:
            List of curve points
        """
        # Extract parsing logic
        pass

    def _validate_tracking_data(self, data: CurveDataList) -> bool:
        """Validate tracking data format.

        Args:
            data: Curve data to validate

        Returns:
            True if valid
        """
        # Extract validation logic
        pass
```

**File: `ui/controllers/tracking_display_controller.py`**

```python
"""Controller for updating tracking point display."""

from PySide6.QtCore import QObject, Signal
from stores.application_state import get_application_state

class TrackingDisplayController(QObject):
    """Handles visual display of tracking data.

    Responsibilities:
        - Update curve view with tracking data
        - Manage curve visibility
        - Sync timeline with tracking data

    Signals:
        display_updated: Emitted when display refreshed
    """

    display_updated = Signal()

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize tracking display controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window
        self._app_state = get_application_state()

    def update_display_preserve_selection(self) -> None:
        """Update display, preserving current selection."""
        curves, metadata, active = self._prepare_display_data()
        self.main_window.curve_widget.set_curves_data(curves, metadata, active)
        self.display_updated.emit()

    def update_display_with_selection(self, selected: list[str]) -> None:
        """Update display with specific curve selection."""
        curves, metadata, active = self._prepare_display_data()
        self.main_window.curve_widget.set_curves_data(
            curves, metadata, active, selected_curves=selected
        )
        self.display_updated.emit()

    def update_display_reset_selection(self) -> None:
        """Update display, resetting selection to active curve only."""
        curves, metadata, active = self._prepare_display_data()
        selected = [active] if active else []
        self.main_window.curve_widget.set_curves_data(
            curves, metadata, active, selected_curves=selected
        )
        self.display_updated.emit()

    def _prepare_display_data(self) -> tuple[dict, dict, str | None]:
        """Prepare curve data for display (common logic)."""
        # Extract from MultiPointTrackingController.update_curve_display
        pass
```

**File: `ui/controllers/tracking_selection_controller.py`**

```python
"""Controller for synchronizing tracking point selection."""

from PySide6.QtCore import QObject, Signal, Qt
from stores.application_state import get_application_state

class TrackingSelectionController(QObject):
    """Handles selection synchronization between panel and view.

    Responsibilities:
        - Sync panel selection → curve view
        - Sync curve view selection → panel
        - Handle selection change events
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize tracking selection controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window
        self._app_state = get_application_state()
        self._syncing = False  # Prevent circular updates

    def connect_signals(self) -> None:
        """Connect selection synchronization signals."""
        # Panel → View
        if self.main_window.tracking_panel is not None:
            _ = self.main_window.tracking_panel.selection_changed.connect(
                self.handle_panel_selection_changed,
                Qt.QueuedConnection
            )

        # ApplicationState → Both
        _ = self._app_state.selection_state_changed.connect(
            self._on_selection_state_changed,
            Qt.QueuedConnection
        )

    def sync_panel_to_view(self, selected_curve: str) -> None:
        """Update curve view based on panel selection.

        Args:
            selected_curve: Name of curve selected in panel
        """
        if self._syncing:
            return

        self._syncing = True
        try:
            # Update ApplicationState
            self._app_state.set_active_curve(selected_curve)

            # Update curve view will happen via signal
        finally:
            self._syncing = False

    def handle_panel_selection_changed(self, curve_name: str) -> None:
        """Handle selection change in tracking panel.

        Args:
            curve_name: Newly selected curve name
        """
        self.sync_panel_to_view(curve_name)

    def _on_selection_state_changed(self) -> None:
        """Handle selection state change from ApplicationState."""
        if self._syncing:
            return

        # Update panel and view to reflect new selection
        pass
```

**Step 2: Create facade controller**

**File: `ui/controllers/multi_point_tracking_controller.py` (NEW - Facade)**

```python
"""Facade controller for multi-point tracking (delegates to sub-controllers)."""

from PySide6.QtCore import QObject, Signal
from ui.controllers.tracking_data_controller import TrackingDataController
from ui.controllers.tracking_display_controller import TrackingDisplayController
from ui.controllers.tracking_selection_controller import TrackingSelectionController

class MultiPointTrackingController(QObject):
    """Facade for multi-point tracking functionality.

    This is a thin facade that delegates to specialized controllers:
        - TrackingDataController: Loading and parsing
        - TrackingDisplayController: Visual updates
        - TrackingSelectionController: Selection synchronization

    Maintains backward compatibility with existing MainWindow references.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize multi-point tracking controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window

        # Create sub-controllers
        self.data_controller = TrackingDataController(main_window)
        self.display_controller = TrackingDisplayController(main_window)
        self.selection_controller = TrackingSelectionController(main_window)

        # Connect sub-controller signals
        self._connect_sub_controllers()

    def _connect_sub_controllers(self) -> None:
        """Wire up sub-controllers."""
        # Data loaded → Update display
        _ = self.data_controller.data_loaded.connect(
            lambda: self.display_controller.update_display_reset_selection()
        )

        # Connect selection controller signals
        self.selection_controller.connect_signals()

    # Backward compatibility methods (delegate to sub-controllers)

    def load_single_point_tracking_data(self, file_path) -> bool:
        """Load single point (delegates to data controller)."""
        return self.data_controller.load_single_point_data(file_path)

    def load_multi_point_tracking_data(self, data: dict) -> bool:
        """Load multi-point (delegates to data controller)."""
        return self.data_controller.load_multi_point_data(data)

    def update_curve_display(self, selected: list[str] | None = None) -> None:
        """Update display (delegates to display controller)."""
        if selected is not None:
            self.display_controller.update_display_with_selection(selected)
        else:
            self.display_controller.update_display_preserve_selection()
```

**Step 3: Migration strategy**

1. **Phase 3.1a:** Create new controller files with extracted logic
2. **Phase 3.1b:** Create facade controller for backward compatibility
3. **Phase 3.1c:** Update MainWindow to use facade (no other code changes needed)
4. **Phase 3.1d:** Run tests to verify functionality preserved
5. **Phase 3.1e:** (Optional) Gradually update callers to use sub-controllers directly

#### **Verification Steps:**

```bash
# 1. Verify file structure
ls -la ui/controllers/tracking_*.py
# Should show:
# - tracking_data_controller.py
# - tracking_display_controller.py
# - tracking_selection_controller.py
# - multi_point_tracking_controller.py (facade)

# 2. Count lines per file
wc -l ui/controllers/tracking_*.py
# Each should be ~300-400 lines

# 3. Run comprehensive tracking tests
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v
~/.local/bin/uv run pytest tests/test_insert_track_integration.py -v

# 4. Manual test: Load multi-point tracking file, verify all features work
```

#### **Success Metrics:**
- ✅ 1,165 lines split into 3 controllers (~400 lines each)
- ✅ All tracking tests pass
- ✅ Backward compatibility maintained (facade pattern)
- ✅ Each controller has single responsibility

---

### **Task 3.2: Split InteractionService**
**Time:** 4-5 days
**Impact:** 1,480 lines → 4 services (~300-400 lines each)

#### **Current Issues:**
- Handles 8 different concerns in one 1,480-line class
- 48 methods mixing mouse events, commands, selection, point manipulation
- 114-line `add_to_history()` method with deep nesting

#### **New Architecture:**

```
InteractionService (1,480 lines)
    ↓ SPLIT INTO ↓
├── MouseInteractionService (~300 lines)
│   ├── handle_mouse_press()
│   ├── handle_mouse_move()
│   ├── handle_mouse_release()
│   ├── handle_wheel()
│   └── handle_key_press()
│
├── SelectionService (~400 lines)
│   ├── find_point_at()
│   ├── select_point()
│   ├── select_all()
│   ├── clear_selection()
│   ├── rubber_band_selection()
│   └── get_selection_info()
│
├── CommandService (~350 lines)
│   ├── execute_command()
│   ├── undo()
│   ├── redo()
│   ├── can_undo/can_redo()
│   └── clear_history()
│
└── PointManipulationService (~400 lines)
    ├── move_point()
    ├── delete_points()
    ├── nudge_points()
    ├── toggle_point_status()
    └── validate_point_move()
```

*(Due to length constraints, detailed implementation similar to Task 3.1)*

#### **Verification Steps:**

```bash
# Run interaction service tests
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
~/.local/bin/uv run pytest tests/test_interaction_mouse_events.py -v
~/.local/bin/uv run pytest tests/test_interaction_history.py -v
```

#### **Success Metrics:**
- ✅ 1,480 lines split into 4 services
- ✅ All interaction tests pass
- ✅ Command history functionality preserved
- ✅ Mouse/keyboard events work correctly

---

### **Task 3.3: Remove StateManager Data Delegation**
**Time:** 3-4 days
**Impact:** Removes ~350 lines of deprecated delegation

#### **Current Issues:**
- StateManager has ~350 lines of properties that just delegate to ApplicationState
- Comments say "DEPRECATED: delegated to ApplicationState"
- Creates confusion: "Which API should I use?"
- Two sources of truth (StateManager vs ApplicationState)

#### **Implementation Strategy:**

**Step 1: Identify all delegation properties**

```bash
# Find all @property decorators that delegate
grep -A 5 "@property" ui/state_manager.py | grep -B 3 "_app_state"
```

**Step 2: Create migration script**

```python
#!/usr/bin/env python3
"""Migrate from StateManager data access to ApplicationState."""

import re
from pathlib import Path

# Patterns to replace
REPLACEMENTS = [
    # state_manager.track_data → app_state.get_curve_data(active)
    (
        r'(\w+)\.track_data',
        r'get_application_state().get_curve_data(get_application_state().active_curve)'
    ),
    # state_manager.current_frame → app_state.current_frame
    (
        r'state_manager\.current_frame',
        r'get_application_state().current_frame'
    ),
    # Add more patterns...
]

def migrate_file(file_path: Path) -> int:
    """Migrate a single file."""
    content = file_path.read_text()
    original = content

    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    # Add import if needed
    if content != original and 'from stores.application_state import get_application_state' not in content:
        # Add import at top
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                lines.insert(i, 'from stores.application_state import get_application_state')
                break
        content = '\n'.join(lines)

    if content != original:
        file_path.write_text(content)
        return 1
    return 0

# Run on all files...
```

**Step 3: Remove delegation properties from StateManager**

Keep only UI-specific properties:
- `zoom_level`
- `pan_offset`
- `window_size`
- `window_position`
- `is_fullscreen`
- `current_tool`

Remove all data-related properties:
- `track_data` (use `app_state.get_curve_data()`)
- `current_frame` (use `app_state.current_frame`)
- `has_data` (use `app_state.get_curve_data() is not None`)
- `data_bounds` (calculate from `app_state.get_curve_data()`)
- `selected_points` (use `app_state.get_selection()`)
- All other data delegations

#### **Verification Steps:**

```bash
# 1. Count properties before
grep -c "@property" ui/state_manager.py
# Before: ~50

# 2. Run migration
python3 tools/migrate_state_manager.py

# 3. Count properties after
grep -c "@property" ui/state_manager.py
# After: ~15 (only UI properties)

# 4. Run full test suite
~/.local/bin/uv run pytest tests/ -x
```

#### **Success Metrics:**
- ✅ ~350 lines removed from StateManager
- ✅ Only UI-specific properties remain
- ✅ All tests pass
- ✅ Single source of truth (ApplicationState)

---

### **Phase 3 Completion Checklist:**

```bash
cat > verify_phase3.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Phase 3 Verification ==="

echo "1. MultiPointTrackingController split..."
if [ -f "ui/controllers/tracking_data_controller.py" ] && \
   [ -f "ui/controllers/tracking_display_controller.py" ] && \
   [ -f "ui/controllers/tracking_selection_controller.py" ]; then
    echo "✅ PASS: Sub-controllers created"
else
    echo "❌ FAIL: Missing sub-controllers"
    exit 1
fi

echo "2. InteractionService split..."
if [ -f "services/mouse_interaction_service.py" ] && \
   [ -f "services/selection_service.py" ] && \
   [ -f "services/command_service.py" ] && \
   [ -f "services/point_manipulation_service.py" ]; then
    echo "✅ PASS: Service split complete"
else
    echo "❌ FAIL: Services not split"
    exit 1
fi

echo "3. StateManager delegation removed..."
PROP_COUNT=$(grep -c "@property" ui/state_manager.py)
if [ "$PROP_COUNT" -lt 20 ]; then
    echo "✅ PASS: StateManager simplified ($PROP_COUNT properties)"
else
    echo "❌ FAIL: Too many properties remaining ($PROP_COUNT)"
    exit 1
fi

echo "4. Running architectural tests..."
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
~/.local/bin/uv run pytest tests/test_state_manager.py -v

echo "=== Phase 3 COMPLETE ==="
EOF

chmod +x verify_phase3.sh
./verify_phase3.sh
```

**Phase 3 Success Criteria:**
- ✅ 2,645 lines of god objects → 7 focused services
- ✅ ~350 lines of delegation removed
- ✅ All architectural tests pass
- ✅ Single Responsibility Principle enforced
- ✅ Backward compatibility maintained

---

## 🎨 **PHASE 4: POLISH & OPTIMIZATION (WEEKS 5-6)**

**Objective:** Final improvements and long-term quality
**Total Effort:** 1-2 weeks
**Priority:** MEDIUM - Quality of life improvements

---

### **Task 4.1: Simplify Batch Update System**
**Time:** 1 day
**Impact:** Removes 105 lines of over-engineering

#### **Current Issues:**
- Nested batch support via reference counting
- Reentrancy protection for single-threaded code
- Signal deduplication (Qt already handles efficiently)
- 105 lines for main-thread-only application

#### **Simplified Implementation:**

**stores/application_state.py - Replace lines 931-1043:**

**Before (Complex):**
```python
def begin_batch(self) -> None:
    """Begin batch update mode (supports nesting)."""
    self._assert_main_thread()
    self._batch_depth += 1  # Nested support
    logger.debug(f"Batch update depth: {self._batch_depth}")

def end_batch(self) -> None:
    """End batch update mode, emit signals if no more nesting."""
    self._assert_main_thread()
    if self._batch_depth <= 0:
        logger.warning("end_batch called without begin_batch")
        return

    self._batch_depth -= 1
    if self._batch_depth == 0:
        self._flush_pending_signals()

def _flush_pending_signals(self) -> None:
    """Emit all pending signals (deduplicated)."""
    unique_signals: dict[SignalInstance, tuple[Any, ...]] = {}
    for signal, args in self._pending_signals:
        unique_signals[signal] = args

    self._emitting_batch = True  # Reentrancy protection
    try:
        for signal, args in unique_signals.items():
            signal.emit(*args)
    finally:
        self._emitting_batch = False
        self._pending_signals.clear()

@contextmanager
def batch_updates(self):
    """Context manager for batch updates."""
    self.begin_batch()
    try:
        yield
    finally:
        self.end_batch()
```

**After (Simple):**
```python
@contextmanager
def batch_updates(self):
    """Context manager for batch updates.

    Defers signal emission until end of batch for performance.
    For single-threaded main-thread-only use.

    Example:
        with state.batch_updates():
            state.set_curve_data("Track1", data1)
            state.set_curve_data("Track2", data2)
            # Signals emitted once at end
    """
    self._assert_main_thread()

    # Set batching flag
    self._batching = True
    self._batch_signals: set[str] = set()  # Track which signals to emit

    try:
        yield
    finally:
        # Clear flag
        self._batching = False

        # Emit collected signals
        if 'curves_changed' in self._batch_signals:
            self.curves_changed.emit(self._curves_data.copy())
        if 'selection_changed' in self._batch_signals:
            self.selection_changed.emit()
        if 'frame_changed' in self._batch_signals:
            self.frame_changed.emit(self._current_frame)

        # Clear collected signals
        self._batch_signals.clear()

def _emit(self, signal: SignalInstance, args: tuple[Any, ...]) -> None:
    """Emit signal or defer if batching.

    Args:
        signal: Signal to emit
        args: Signal arguments
    """
    if self._batching:
        # Just track that this signal needs emission
        signal_name = signal.__name__ if hasattr(signal, '__name__') else 'unknown'
        self._batch_signals.add(signal_name)
    else:
        # Emit immediately
        signal.emit(*args)
```

**Update __init__:**
```python
def __init__(self) -> None:
    # ... existing init ...

    # Simplified batching (no nesting, no reentrancy)
    self._batching: bool = False
    self._batch_signals: set[str] = set()
```

#### **Verification Steps:**

```bash
# 1. Count lines before
sed -n '931,1043p' stores/application_state.py | wc -l
# Before: 113 lines

# 2. Apply simplification

# 3. Count lines after
grep -A 50 "def batch_updates" stores/application_state.py | wc -l
# After: ~40 lines (73 lines saved)

# 4. Run batch tests
~/.local/bin/uv run pytest tests/stores/test_application_state.py::test_batch_updates -v
```

#### **Success Metrics:**
- ✅ 73 lines removed (105 → 32)
- ✅ No nested batch support (unnecessary)
- ✅ No reentrancy protection (single-threaded)
- ✅ All batch update tests pass

---

### **Task 4.2: Widget Destruction Guard Decorator**
**Time:** 10 hours (2h decorator + 8h adoption)
**Impact:** Eliminates 49 duplications

#### **Implementation:**

**Create `ui/qt_utils.py`:**

```python
"""Qt utility functions and decorators."""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


def safe_slot(func: Callable[P, R]) -> Callable[P, R | None]:
    """Decorator to guard Qt slot handlers against widget destruction.

    If the widget is being destroyed (raises RuntimeError on attribute access),
    the handler returns None without executing. Otherwise, executes normally.

    This prevents errors when signals fire during widget cleanup.

    Args:
        func: Slot handler function to guard

    Returns:
        Wrapped function that safely handles widget destruction

    Example:
        @safe_slot
        def _on_curves_changed(self, curves: dict) -> None:
            # No try/except needed - decorator handles destruction
            self.update_display(curves)
    """
    @wraps(func)
    def wrapper(self: object, *args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            # Test if widget is being destroyed
            _ = self.isVisible()  # type: ignore[attr-defined]
        except RuntimeError:
            # Widget being destroyed - skip handler
            logger.debug(
                f"Skipped {func.__name__} - widget being destroyed"
            )
            return None
        except AttributeError:
            # Not a widget (doesn't have isVisible) - execute anyway
            pass

        # Widget OK - execute handler
        return func(self, *args, **kwargs)

    return wrapper


def safe_slot_logging(verbose: bool = False) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Parameterized version of safe_slot with configurable logging.

    Args:
        verbose: If True, log every skip. If False, only log at debug level.

    Returns:
        Decorator function

    Example:
        @safe_slot_logging(verbose=True)
        def _on_data_changed(self, data): ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        @wraps(func)
        def wrapper(self: object, *args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                _ = self.isVisible()  # type: ignore[attr-defined]
            except RuntimeError:
                if verbose:
                    logger.info(
                        f"Widget destroyed - skipped {func.__name__}"
                    )
                else:
                    logger.debug(
                        f"Widget destroyed - skipped {func.__name__}"
                    )
                return None
            except AttributeError:
                pass

            return func(self, *args, **kwargs)

        return wrapper

    return decorator
```

**Create tests: `tests/test_qt_utils.py`:**

```python
"""Tests for Qt utility functions."""

import pytest
from PySide6.QtWidgets import QWidget
from ui.qt_utils import safe_slot, safe_slot_logging


class TestSafeSlot:
    """Tests for safe_slot decorator."""

    def test_normal_execution(self, qtbot):
        """Decorator should not interfere with normal execution."""
        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.called = False
                self.arg_received = None

            @safe_slot
            def handler(self, arg):
                self.called = True
                self.arg_received = arg
                return "success"

        widget = TestWidget()
        qtbot.addWidget(widget)

        result = widget.handler("test_arg")

        assert result == "success"
        assert widget.called is True
        assert widget.arg_received == "test_arg"

    def test_widget_being_destroyed(self, qtbot):
        """Decorator should return None if widget being destroyed."""
        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.called = False

            @safe_slot
            def handler(self):
                self.called = True
                return "success"

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Close widget (starts destruction)
        widget.close()
        widget.deleteLater()

        # Process events to start destruction
        qtbot.wait(10)

        # Handler should return None, not call body
        result = widget.handler()

        assert result is None
        assert widget.called is False

    def test_non_widget_object(self):
        """Decorator should work on non-widget objects too."""
        class NotAWidget:
            def __init__(self):
                self.called = False

            @safe_slot
            def handler(self, arg):
                self.called = True
                return arg * 2

        obj = NotAWidget()
        result = obj.handler(21)

        assert result == 42
        assert obj.called is True
```

**Update widgets to use decorator:**

**ui/timeline_tabs.py:385-402 - Before:**
```python
def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle curves changed signal."""
    try:
        _ = self.isVisible()  # Check if widget being destroyed
    except RuntimeError:
        return

    # ... handler implementation ...
```

**After:**
```python
from ui.qt_utils import safe_slot

@safe_slot
def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Handle curves changed signal."""
    # No try/except needed - decorator handles it
    # ... handler implementation ...
```

**Apply to all 22 files with destruction guards.**

#### **Verification Steps:**

```bash
# 1. Count try/except RuntimeError before
grep -r "except RuntimeError" ui/ --include="*.py" -c
# Before: 49

# 2. Apply decorator to all handlers

# 3. Count try/except RuntimeError after
grep -r "except RuntimeError" ui/ --include="*.py" -c
# After: 0 (all replaced with decorator)

# 4. Count @safe_slot uses
grep -r "@safe_slot" ui/ --include="*.py" -c
# Should be: 49

# 5. Run widget tests
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
~/.local/bin/uv run pytest tests/test_qt_utils.py -v
```

#### **Success Metrics:**
- ✅ 49 try/except blocks → 49 @safe_slot decorators
- ✅ All widget tests pass
- ✅ Decorator tests have 100% coverage
- ✅ Code more readable (no boilerplate)

---

### **Task 4.3: Transform Service Helper**
**Time:** 6 hours
**Impact:** Simplifies 58 occurrences of 3-step pattern

*(Implementation details similar to previous tasks)*

---

### **Task 4.4: Active Curve Data Helper**
**Time:** 12 hours
**Impact:** Simplifies 33 occurrences of 4-step pattern

*(Implementation details similar to previous tasks)*

---

### **Task 4.5: Type Ignore Incremental Cleanup**
**Time:** Ongoing (30-40 hours total)
**Impact:** 1,093 → ~700 (35% reduction)

#### **Strategy:**

**Week 5-6: Focus on high-value files**
- Fix hasattr()-related ignores (should reduce ~30% automatically)
- Target files with 10+ ignores
- Focus on ui/image_sequence_browser.py (57 ignores)
- Focus on ui/main_window.py (26 ignores)

**Long-term (Ongoing):**
- Add to code review checklist: No new type ignores
- Fix 5-10 per week during normal development
- Target: < 500 by end of next quarter

#### **Quick Wins:**

Many ignores are in chained hasattr() checks:
```python
# Before: 6 type ignores
if parent is not None and hasattr(parent, "state_manager") and parent.state_manager is not None:  # pyright: ignore[...]
    state_manager = parent.state_manager  # pyright: ignore[...]
    if state_manager and hasattr(state_manager, "recent_directories"):  # pyright: ignore[...]
        recent_dirs = state_manager.recent_directories  # pyright: ignore[...]

# After: 0 type ignores
if (
    parent is not None
    and parent.state_manager is not None
    and parent.state_manager.recent_directories is not None
):
    recent_dirs = parent.state_manager.recent_directories
```

---

### **Phase 4 Completion Checklist:**

```bash
cat > verify_phase4.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Phase 4 Verification ==="

echo "1. Batch system simplified..."
BATCH_LINES=$(grep -A 50 "def batch_updates" stores/application_state.py | wc -l)
if [ "$BATCH_LINES" -lt 60 ]; then
    echo "✅ PASS: Batch system simplified ($BATCH_LINES lines)"
else
    echo "❌ FAIL: Batch system still complex ($BATCH_LINES lines)"
    exit 1
fi

echo "2. Safe slot decorator in use..."
DECORATOR_COUNT=$(grep -r "@safe_slot" ui/ --include="*.py" -c)
if [ "$DECORATOR_COUNT" -ge 40 ]; then
    echo "✅ PASS: Decorator adopted ($DECORATOR_COUNT uses)"
else
    echo "⚠️  PARTIAL: Only $DECORATOR_COUNT uses"
fi

echo "3. Type ignores reduced..."
IGNORE_COUNT=$(grep -r "# type: ignore\|# pyright: ignore" --include="*.py" | wc -l)
if [ "$IGNORE_COUNT" -lt 800 ]; then
    echo "✅ PASS: Type ignores reduced to $IGNORE_COUNT"
else
    echo "⚠️  IN PROGRESS: $IGNORE_COUNT type ignores (target: < 700)"
fi

echo "4. Running polish tests..."
~/.local/bin/uv run pytest tests/test_qt_utils.py -v
~/.local/bin/uv run pytest tests/stores/test_application_state.py -v

echo "=== Phase 4 COMPLETE ==="
EOF

chmod +x verify_phase4.sh
./verify_phase4.sh
```

---

## ✅ **VERIFICATION & TESTING STRATEGY**

### **Continuous Verification (After Each Task):**

```bash
# Run after EVERY task completion
cat > verify_task.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Task Verification ==="

# 1. Type check (should stay at 0 errors)
echo "1. Type checking..."
~/.local/bin/uv run ./bpr --errors-only

# 2. Run affected tests
echo "2. Running affected tests..."
~/.local/bin/uv run pytest tests/ -x -q --tb=short

# 3. Check for syntax errors
echo "3. Checking syntax..."
find ui/ services/ core/ stores/ -name "*.py" -exec python3 -m py_compile {} \;

echo "✅ Task verification passed"
EOF

chmod +x verify_task.sh
```

### **Phase Completion Verification:**

Each phase has its own `verify_phaseN.sh` script (defined above).

### **Full Integration Test:**

```bash
cat > verify_all.sh << 'EOF'
#!/bin/bash
set -e

echo "=== PLAN TAU - FULL VERIFICATION ==="

echo "Running Phase 1 verification..."
./verify_phase1.sh

echo "Running Phase 2 verification..."
./verify_phase2.sh

echo "Running Phase 3 verification..."
./verify_phase3.sh

echo "Running Phase 4 verification..."
./verify_phase4.sh

echo ""
echo "=== FULL TEST SUITE ==="
~/.local/bin/uv run pytest tests/ -v --tb=short

echo ""
echo "=== TYPE CHECKING ==="
~/.local/bin/uv run ./bpr

echo ""
echo "=== FINAL STATISTICS ==="

echo "hasattr() count:"
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l

echo "Qt.QueuedConnection count:"
grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | wc -l

echo "Type ignores:"
grep -r "# type: ignore\|# pyright: ignore" --include="*.py" | wc -l

echo "God objects split:"
wc -l ui/controllers/tracking_*.py services/*_service.py

echo ""
echo "=== ✅ PLAN TAU VERIFICATION COMPLETE ==="
EOF

chmod +x verify_all.sh
```

---

## 📊 **SUCCESS METRICS**

### **Phase 1 Success Metrics:**
- ✅ 0 hasattr() in production code (46 → 0)
- ✅ 50+ explicit Qt.QueuedConnection (0 → 50+)
- ✅ 0 property setter race conditions (5 → 0)
- ✅ Type checker errors: 0 (maintained)
- ✅ Documentation matches code: YES

### **Phase 2 Success Metrics:**
- ✅ ~300 lines of duplication eliminated
- ✅ 5 new utilities with tests
- ✅ Type safety improved (FrameStatus NamedTuple)
- ✅ SelectionContext enum removed

### **Phase 3 Success Metrics:**
- ✅ 2,645 lines of god objects → 7 services (~350 lines each)
- ✅ ~350 lines of StateManager delegation removed
- ✅ Single Responsibility Principle: Enforced
- ✅ All architectural tests pass

### **Phase 4 Success Metrics:**
- ✅ Batch system: 105 → 32 lines (73 lines saved)
- ✅ Destruction guards: 49 duplications → 1 decorator
- ✅ Type ignores: 1,093 → ~700 (35% reduction)

### **Overall Success Metrics:**
- ✅ **Code Reduced:** ~3,000 lines eliminated
- ✅ **Quality Improved:** CLAUDE.md 100% compliance
- ✅ **Architecture:** God objects split into focused services
- ✅ **Type Safety:** 35% reduction in type ignores
- ✅ **Testing:** All 100+ tests passing
- ✅ **Documentation:** Code matches documentation

---

## ⚠️ **RISK MITIGATION**

### **Risk 1: Breaking Changes During Split**
**Mitigation:**
- Use facade pattern for backward compatibility
- Gradual migration (old code still works)
- Comprehensive tests after each step
- Create branch per phase, merge after verification

### **Risk 2: Test Failures**
**Mitigation:**
- Run tests after EVERY task
- Fix tests immediately (don't accumulate)
- Use `pytest -x` to stop on first failure
- Keep `verify_task.sh` script running

### **Risk 3: Type Checker Regression**
**Mitigation:**
- Run `./bpr --errors-only` after every change
- Target: Maintain 0 errors throughout
- Fix type issues immediately
- Don't proceed if errors introduced

### **Risk 4: Performance Regression**
**Mitigation:**
- Run performance tests after Phase 3
- Profile before/after for god object splits
- Verify no slowdown in frame changes
- Benchmark timeline scrubbing speed

### **Risk 5: Merge Conflicts**
**Mitigation:**
- Create dedicated branch: `plan-tau-implementation`
- Commit after each task completion
- Merge main regularly into branch
- Small, frequent commits > large batch

---

## 🔄 **ROLLBACK PLAN**

### **Per-Task Rollback:**

```bash
# If a task fails, rollback to previous commit
git log --oneline -10  # Find last good commit
git reset --hard <commit-hash>
git clean -fd
```

### **Per-Phase Rollback:**

```bash
# If entire phase problematic, rollback to phase start
git log --grep="Phase N START" --oneline
git reset --hard <phase-start-commit>
```

### **Full Rollback:**

```bash
# Nuclear option - restore from plan start
git log --grep="PLAN TAU START" --oneline
git reset --hard <plan-start-commit>
```

### **Rollback Safety:**

**Before starting Phase 1:**
```bash
# Create safety tag
git tag -a plan-tau-start -m "PLAN TAU: Before implementation"
git push origin plan-tau-start
```

**Before each phase:**
```bash
git tag -a plan-tau-phase-N-start -m "PLAN TAU: Phase N start"
```

**To rollback to any tag:**
```bash
git checkout plan-tau-phase-N-start
git checkout -b plan-tau-retry
```

---

## 📅 **IMPLEMENTATION TIMELINE**

### **Week 1: Critical Safety (Phase 1)**
- **Mon-Tue:** Task 1.1 + 1.2 (Race conditions + Qt.QueuedConnection)
- **Wed-Thu:** Task 1.3 (hasattr() replacement)
- **Fri:** Task 1.4 + Phase 1 verification

### **Week 2: Quick Wins (Phase 2)**
- **Mon:** Tasks 2.1 + 2.2 (Frame utils + deepcopy)
- **Tue:** Tasks 2.3 + 2.4 (NamedTuple + frame range)
- **Wed:** Task 2.5 (SelectionContext removal)
- **Thu-Fri:** Phase 2 verification + documentation

### **Week 3: Architecture Part 1 (Phase 3)**
- **Mon-Wed:** Task 3.1 (Split MultiPointTrackingController)
- **Thu-Fri:** Start Task 3.2 (Split InteractionService)

### **Week 4: Architecture Part 2 (Phase 3)**
- **Mon-Wed:** Finish Task 3.2 (InteractionService split)
- **Thu:** Task 3.3 (StateManager delegation removal)
- **Fri:** Phase 3 verification

### **Week 5: Polish Part 1 (Phase 4)**
- **Mon:** Task 4.1 (Batch system simplification)
- **Tue-Wed:** Task 4.2 (Safe slot decorator)
- **Thu-Fri:** Tasks 4.3 + 4.4 (Helper methods)

### **Week 6: Polish Part 2 & Final Verification (Phase 4)**
- **Mon-Wed:** Task 4.5 (Type ignore cleanup)
- **Thu:** Full verification suite
- **Fri:** Documentation updates + merge to main

---

## 📝 **COMMIT MESSAGE TEMPLATE**

Use consistent commit messages:

```bash
# Format:
<phase>(<task>): <description>

# Examples:
phase1(race-conditions): Fix property setter race in StateManager
phase1(qt-signals): Add explicit Qt.QueuedConnection to 50+ connections
phase1(hasattr): Replace hasattr() with None checks (15 files)

phase2(frame-utils): Extract frame clamping utility (60 duplications eliminated)
phase2(selection): Remove SelectionContext enum, add explicit methods

phase3(tracking-controller): Split MultiPointTrackingController into 3 controllers
phase3(interaction-service): Split InteractionService into 4 services
phase3(state-manager): Remove deprecated data delegation (~350 lines)

phase4(batch): Simplify batch update system (105 → 32 lines)
phase4(decorator): Add @safe_slot decorator (49 uses)
```

---

## 🎓 **POST-IMPLEMENTATION CHECKLIST**

After completing all phases:

- [ ] All verification scripts pass (`verify_all.sh`)
- [ ] Full test suite passes (114 tests)
- [ ] Type checker clean (0 errors)
- [ ] Code review completed
- [ ] Documentation updated
- [ ] CLAUDE.md compliance verified
- [ ] Performance benchmarks run (no regression)
- [ ] Branch merged to main
- [ ] Tag created: `plan-tau-complete`
- [ ] Retrospective document created

---

## 📚 **DOCUMENTATION UPDATES**

After completion, update:

1. **CLAUDE.md:**
   - Add examples using new utilities
   - Document split controller architecture
   - Update best practices section

2. **README.md:**
   - Update architecture diagram
   - Document new service structure
   - Add utility function examples

3. **TESTING_ROADMAP_ASSESSMENT.md:**
   - Update with new controller tests
   - Note improved coverage

4. **Create PLAN_TAU_RETROSPECTIVE.md:**
   - What went well
   - What was challenging
   - Lessons learned
   - Metrics achieved

---

## 🎯 **FINAL NOTES**

### **Key Principles:**

1. **Test After Every Change:** Never proceed with failing tests
2. **Small Commits:** Commit after each task completion
3. **Verify Continuously:** Run verification scripts frequently
4. **Document as You Go:** Update comments and docs during implementation
5. **Ask for Help:** If stuck, consult team or pause for review

### **Success Criteria Summary:**

This plan is COMPLETE when:
- ✅ All 4 phases verified
- ✅ 0 critical bugs remain
- ✅ ~3,000 lines of unnecessary code removed
- ✅ CLAUDE.md 100% compliance
- ✅ All 114 tests passing
- ✅ Type checker clean (0 errors)
- ✅ Architecture simplified (god objects split)
- ✅ Code-documentation alignment restored

### **Expected Outcome:**

A cleaner, more maintainable codebase with:
- Fewer bugs (race conditions eliminated)
- Better architecture (SRP enforced)
- Improved type safety (35% fewer ignores)
- Enhanced readability (DRY compliance)
- Faster development velocity (simpler code)

---

**END OF PLAN TAU**

**Status:** ✅ READY FOR IMPLEMENTATION
**Last Updated:** 2025-10-14
**Next Action:** Begin Phase 1, Task 1.1
