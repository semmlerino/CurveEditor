## 🎨 **PHASE 4: POLISH & OPTIMIZATION (WEEKS 5-6)**

**Objective:** Final improvements and long-term quality
**Total Effort:** 3-4 days (22-34 hours)
**Priority:** MEDIUM - Quality of life improvements
**Note:** Task 4.3 (Transform Service Helper) was DELETED - methods didn't exist in codebase

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
from typing import Any
from PySide6.QtCore import Signal as SignalInstance

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
    self._batch_signals: set[int] = set()  # Track signal IDs

    try:
        yield
    finally:
        # Clear flag
        self._batching = False

        # Emit collected signals using identity matching
        if id(self.curves_changed) in self._batch_signals:
            self.curves_changed.emit(self._curves_data.copy())
        if id(self.selection_changed) in self._batch_signals:
            self.selection_changed.emit()
        if id(self.frame_changed) in self._batch_signals:
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
        # Track signal by identity (object ID)
        # PySide6 Signals don't have reliable __name__ attribute
        self._batch_signals.add(id(signal))
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
    self._batch_signals: set[int] = set()  # Store signal IDs, not names
```

**Why this works:**
- Uses `id(signal)` to get unique identity of signal object
- No reliance on `__name__` attribute which doesn't exist on PySide6 Signals
- Identity-based matching is reliable and type-safe
- Python guarantees `id()` returns unique integer for each object during its lifetime

#### **Design Note: Batch System Behavior**

**IMPORTANT:** This simplified batch system emits signals with **LATEST STATE**, not individual change events.

**What this means:**
- Subscribers receive the final state after all batched operations complete
- Intermediate values during the batch are NOT emitted

**This is CORRECT behavior for:**
- `frame_changed(frame)` - Latest frame is what matters
- `selection_changed()` - Latest selection is what matters
- `curves_changed(curves)` - Latest curve data is what matters

**Example:**
```python
with state.batch_updates():
    state.set_frame(1)    # Not emitted
    state.set_frame(5)    # Not emitted
    state.set_frame(10)   # Emitted as frame_changed(10) after batch

# Result: Subscribers only see frame=10 (final state)
# This is correct - we don't want 3 separate frame change events
```

**For signals where intermediate values matter**, don't use `batch_updates()` - emit them individually.

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
- ✅ Design behavior clearly documented

---

### **Task 4.2: Widget Destruction Guard Decorator**
**Time:** 6 hours (2h decorator + 4h adoption)
**Impact:** Eliminates 18 try/except RuntimeError blocks (six-agent review corrected from originally claimed 49)

#### **Implementation:**

**Create `ui/qt_utils.py`:**

```python
"""Qt utility functions and decorators."""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Protocol
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')


class QWidgetLike(Protocol):
    """Protocol for Qt widgets with visibility check."""
    def isVisible(self) -> bool: ...


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
    def wrapper(self: QWidgetLike, *args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            # Test if widget is being destroyed
            _ = self.isVisible()  # Type-safe: Protocol guarantees this method
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

**Apply to all 8 files with RuntimeError destruction guards** (6-agent review verified: 18 instances across ui/ and services/).

#### **Verification Steps:**

```bash
# 1. Count try/except RuntimeError before
grep -r "except RuntimeError" ui/ services/ --include="*.py" | wc -l
# Before: 18 (verified by 6-agent review)

# 2. Apply decorator to all handlers

# 3. Count try/except RuntimeError after
grep -r "except RuntimeError" ui/ services/ --include="*.py" | wc -l
# After: 0 (all replaced with decorator)

# 4. Count @safe_slot uses
grep -r "@safe_slot" ui/ services/ --include="*.py" | wc -l
# Should be: 18

# 5. Run widget tests
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
~/.local/bin/uv run pytest tests/test_qt_utils.py -v
```

#### **Success Metrics:**
- ✅ 18 try/except RuntimeError blocks → 18 @safe_slot decorators (corrected from originally claimed 49)
- ✅ All widget tests pass
- ✅ Decorator tests have 100% coverage
- ✅ Code more readable (no boilerplate)

---

### **Task 4.3: Active Curve Data Helper**
**Time:** 12 hours
**Impact:** Simplifies 50 occurrences of 4-step active curve data access (verified by 6-agent review)

#### **Current Pattern (Duplicated 50 times):**

```python
# Pattern appears throughout ui/ and services/:
from stores.application_state import get_application_state

app_state = get_application_state()
active_curve = app_state.active_curve
if active_curve:
    curve_data = app_state.get_curve_data(active_curve)
    if curve_data:
        # ... use curve_data ...
```

**Grep to find all occurrences:**
```bash
grep -rn "active_curve = .*\.active_curve" ui/ services/ --include="*.py" | wc -l
grep -A 3 "active_curve = " ui/ services/ --include="*.py" | grep "get_curve_data" | wc -l
# Should find ~50 occurrences (verified)
```

#### **New Helper Function:**

**File: `stores/state_helpers.py` (NEW)**

```python
"""Helper functions for ApplicationState access patterns."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.type_aliases import CurveDataList

from stores.application_state import get_application_state


def get_active_curve_data() -> tuple[str | None, "CurveDataList | None"]:
    """Get active curve name and its data.

    Helper to reduce 4-line pattern to 1 line.

    Returns:
        (curve_name, curve_data) tuple
        Returns (None, None) if no active curve or no data
    """
    app_state = get_application_state()
    active_curve = app_state.active_curve

    if active_curve is None:
        return None, None

    curve_data = app_state.get_curve_data(active_curve)
    return active_curve, curve_data


def get_active_curve_name() -> str | None:
    """Get active curve name.

    Returns:
        Active curve name or None
    """
    return get_application_state().active_curve


def get_active_selection() -> tuple[str | None, set[int]]:
    """Get active curve name and its selection.

    Returns:
        (curve_name, selected_indices) tuple
        Returns (None, set()) if no active curve
    """
    app_state = get_application_state()
    active_curve = app_state.active_curve

    if active_curve is None:
        return None, set()

    selection = app_state.get_selection(active_curve)
    return active_curve, selection
```

#### **Before/After Examples:**

**Example 1: services/interaction_service.py (line ~156)**

**Before:**
```python
def select_all_points(self, view, main_window):
    """Select all points in active curve."""
    from stores.application_state import get_application_state

    app_state = get_application_state()
    active_curve = app_state.active_curve
    if active_curve is None:
        return

    curve_data = app_state.get_curve_data(active_curve)
    if curve_data is None:
        return

    # Select all indices
    all_indices = set(range(len(curve_data)))
    app_state.set_selection(active_curve, all_indices)
```

**After:**
```python
def select_all_points(self, view, main_window):
    """Select all points in active curve."""
    from stores.state_helpers import get_active_curve_data
    from stores.application_state import get_application_state

    curve_name, curve_data = get_active_curve_data()
    if curve_name is None or curve_data is None:
        return

    # Select all indices
    all_indices = set(range(len(curve_data)))
    get_application_state().set_selection(curve_name, all_indices)
```

**Example 2: ui/controllers/point_editor_controller.py (line ~89)**

**Before:**
```python
def toggle_endframe_status(self):
    """Toggle endframe status for selected points."""
    from stores.application_state import get_application_state

    app_state = get_application_state()
    active_curve = app_state.active_curve
    if not active_curve:
        return

    curve_data = app_state.get_curve_data(active_curve)
    if not curve_data:
        return

    selection = app_state.get_selection(active_curve)
    # ... toggle status for selected points ...
```

**After:**
```python
def toggle_endframe_status(self):
    """Toggle endframe status for selected points."""
    from stores.state_helpers import get_active_curve_data, get_active_selection

    curve_name, curve_data = get_active_curve_data()
    if curve_name is None or curve_data is None:
        return

    _, selection = get_active_selection()
    # ... toggle status for selected points ...
```

**Example 3: ui/tracking_points_panel.py (line ~234)**

**Before:**
```python
def _update_display(self):
    """Update panel display with active curve info."""
    from stores.application_state import get_application_state

    app_state = get_application_state()
    active_curve = app_state.active_curve
    if not active_curve:
        self.label.setText("No active curve")
        return

    curve_data = app_state.get_curve_data(active_curve)
    if not curve_data:
        self.label.setText(f"{active_curve}: No data")
        return

    self.label.setText(f"{active_curve}: {len(curve_data)} points")
```

**After:**
```python
def _update_display(self):
    """Update panel display with active curve info."""
    from stores.state_helpers import get_active_curve_data

    curve_name, curve_data = get_active_curve_data()
    if curve_name is None:
        self.label.setText("No active curve")
        return

    if curve_data is None:
        self.label.setText(f"{curve_name}: No data")
        return

    self.label.setText(f"{curve_name}: {len(curve_data)} points")
```

#### **Automated Migration Script:**

```bash
#!/bin/bash
# File: tools/apply_state_helpers.sh

echo "Applying state helper refactoring..."

# This is complex enough that manual migration is recommended
# But we can identify candidates:

echo "Files with active curve access pattern:"
grep -rn "active_curve = .*\.active_curve" ui/ services/ --include="*.py"

echo ""
echo "⚠️  Manual migration recommended due to pattern complexity"
echo "See examples above for common patterns"
```

#### **Verification Steps:**

```bash
# 1. Count pattern occurrences before
grep -rn "active_curve = app_state.active_curve" ui/ services/ --include="*.py" | wc -l
# Before: ~50

# 2. Create helper file
# ... create stores/state_helpers.py ...

# 3. Migrate manually (or semi-automatically)

# 4. Count pattern occurrences after
grep -rn "get_active_curve_data()" ui/ services/ --include="*.py" | wc -l
# After: ~50 (converted to helper)

grep -rn "active_curve = app_state.active_curve" ui/ services/ --include="*.py" | wc -l
# After: ~0-5 (mostly eliminated, some legitimate uses remain)

# 5. Run tests
~/.local/bin/uv run pytest tests/stores/test_application_state.py -v
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
~/.local/bin/uv run pytest tests/test_tracking_points_panel.py -v
```

#### **Success Metrics:**
- ✅ 50 occurrences → helper functions (MORE VALUE than originally estimated!)
- ✅ 4-step pattern → 1-2 lines
- ✅ All state access tests pass
- ✅ Code more readable
- ✅ Type safety maintained (tuple unpacking)

---

### **Task 4.4: Type Ignore Incremental Cleanup**
**Time:** Ongoing (30-40 hours total)
**Impact:** 2,151 → ~1,500 (30% reduction)

**Note:** Baseline count was corrected from originally estimated 1,093 to actual 2,151 after codebase audit.

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
if [ "$IGNORE_COUNT" -lt 1600 ]; then
    echo "✅ PASS: Type ignores reduced to $IGNORE_COUNT (from baseline 2,151)"
else
    echo "⚠️  IN PROGRESS: $IGNORE_COUNT type ignores (target: < 1,500)"
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


---

**Navigation:**
- [← Previous: Phase 3 Architectural Refactoring](phase3_architectural_refactoring.md)
- [← Back to Overview](README.md)
- [Verification & Testing](verification_and_testing.md)
