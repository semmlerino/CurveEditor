# Qt/Pytest Testing Guide for CurveEditor

*Optimized for LLM consumption - focus on patterns and critical safety*

## Critical Safety Rules

### ⚠️ FATAL: Qt Threading Violations

**The Timeline Oscillation Bug**: A `self._fps_spinbox` typo in `PlaybackController.set_frame_rate()` lived undetected because the Protocol method was never tested. When finally called, it crashed the application. This is why **EVERY Protocol method MUST have test coverage**.

```python
# ERROR: "Fatal Python error: Aborted"
# CAUSE: QPixmap in worker thread
# FIX:
from tests.qt_test_helpers import ThreadSafeTestImage
image = ThreadSafeTestImage(100, 100)  # Never QPixmap in threads
```

```python
# ERROR: "RuntimeError: Internal C++ object already deleted"
# CAUSE: Qt widget deleted at C++ level while Python reference exists
# FIX:
try:
    if self.widget is not None:
        self.widget.setText("text")
except RuntimeError:
    pass  # Widget was deleted
```

### ⚠️ FATAL: QObject Resource Accumulation - SOLUTION

**Problem**: QObjects without explicit parents accumulate in session-scope QApplication, causing resource exhaustion and crashes in large test suites.

**Solution**: All QObjects must have explicit lifecycle management:
- Set parent to QApplication for Qt ownership tracking
- Call `deleteLater()` + `processEvents()` in fixture teardown
- For event filters: Use `before_close_func` parameter with qtbot.addWidget()

**Problem**: Event filters accumulate globally when MainWindow instances aren't properly cleaned up.

**Solution**: Remove event filters in `before_close_func` BEFORE widget destruction:
```python
def cleanup_event_filter(window):
    app = QApplication.instance()
    if app and hasattr(window, 'global_event_filter'):
        app.removeEventFilter(window.global_event_filter)

qtbot.addWidget(window, before_close_func=cleanup_event_filter)
```

**Problem**: `QApplication.setStyleSheet()` applied repeatedly reprocesses styles for ALL widgets.

**Solution**: Apply stylesheet once using flag check:
```python
app = QApplication.instance()
if not getattr(app, '_dark_theme_applied', False):
    app.setStyleSheet(get_dark_theme_stylesheet())
    app._dark_theme_applied = True
```

```python
# ❌ BAD - No cleanup, QObjects accumulate
@pytest.fixture
def file_load_signals(app):
    signals = FileLoadSignals()  # Orphaned QObject!
    yield signals
    # No cleanup - object persists in QApplication

# ❌ BAD - Event filter without cleanup
@pytest.fixture
def main_window(qtbot):
    window = MainWindow()  # Installs global event filter
    qtbot.addWidget(window)
    yield window
    # Event filter NOT removed - accumulates in QApplication!

# ✅ GOOD - Explicit parent and cleanup
@pytest.fixture
def file_load_signals(qtbot, qapp):
    """QObject with proper lifecycle management."""
    signals = FileLoadSignals()
    # Set parent to QApplication for Qt ownership
    signals.setParent(qapp)

    yield signals

    # Explicit cleanup
    try:
        signals.setParent(None)
        signals.deleteLater()
        qapp.processEvents()  # Process deleteLater
    except RuntimeError:
        pass  # Already deleted

# ✅ GOOD - Event filter cleanup with before_close_func
@pytest.fixture
def main_window(qtbot, qapp):
    """MainWindow with deterministic event filter cleanup."""
    def cleanup_event_filter(window):
        """Remove global event filter before window closes."""
        app = QApplication.instance()
        if app and hasattr(window, 'global_event_filter'):
            try:
                app.removeEventFilter(window.global_event_filter)
            except RuntimeError:
                pass

    window = MainWindow()
    # CRITICAL: before_close_func runs BEFORE widget destruction
    qtbot.addWidget(window, before_close_func=cleanup_event_filter)
    yield window
    # qtbot handles cleanup including before_close_func

# ✅ GOOD - Application-level stylesheet applied only ONCE
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            # Check if stylesheet already applied (avoid reapplying in tests)
            if not getattr(app, '_dark_theme_applied', False):
                app.setStyleSheet(get_dark_theme_stylesheet())
                app._dark_theme_applied = True  # Mark as applied
            # Subsequent MainWindow creations skip expensive reprocessing
```

**Critical Distinction**:
- `QWidget`: Use `qtbot.addWidget(widget)` for automatic cleanup
- `QWidget` with event filters: Use `qtbot.addWidget(widget, before_close_func=cleanup)`
- `QObject` (non-widget): Must set parent OR manually clean up
- Background threads: Must `join()` before fixture teardown
- **Never** rely on `__del__` or `gc.collect()` for Qt cleanup - use `before_close_func`

### Protocol Testing Rule
Every method in a Protocol interface MUST have test coverage, even if unused:
```python
class PlaybackControllerProtocol(Protocol):
    def set_frame_rate(self, fps: int) -> None: ...  # Had typo: self._fps_spinbox

def test_set_frame_rate_programmatic():
    """Would have caught the typo immediately."""
    controller.set_frame_rate(60)
    assert controller.fps_spinbox.value() == 60
```

## CurveEditor Test Imports

### Standard Test Setup
```python
import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PySide6.QtWidgets import QApplication, QWidget, QDialog
from PySide6.QtGui import QImage, QColor
from pytestqt.qtbot import QtBot
from pytestqt.qt_compat import qt_api

# CurveEditor specific
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from services import get_transform_service, get_data_service
from core.models import CurvePoint, PointCollection, PointStatus
from tests.qt_test_helpers import ThreadSafeTestImage, safe_painter
```

### Fixture Scopes

| Scope | Lifetime | Use Case | Example |
|-------|----------|----------|---------|
| `function` | Per test (default) | Test isolation, mutable state | Widget instances |
| `class` | Per test class | Shared setup for test group | Mock services |
| `module` | Per test file | Expensive setup | Database connection |
| `session` | Entire test run | Single instance needed | QApplication |

**Critical**: Session-scope QApplication requires explicit QObject cleanup - see "QObject Resource Accumulation" section above.

### conftest.py Structure

Shared fixtures belong in `tests/conftest.py` for automatic discovery:

```python
# tests/conftest.py - Shared fixtures for entire CurveEditor test suite
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow

@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication - created once for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()

@pytest.fixture
def curve_widget(qtbot) -> CurveViewWidget:
    """Function-scope CurveViewWidget - fresh for each test."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)  # CRITICAL: Auto cleanup
    return widget

@pytest.fixture
def main_window(qtbot) -> MainWindow:
    """MainWindow with proper lifecycle management."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window
```

### Essential Fixtures
```python
@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()

@pytest.fixture  # Default scope="function" for isolation
def curve_widget(qtbot) -> CurveViewWidget:
    """CurveViewWidget with cleanup."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)  # CRITICAL: Auto cleanup
    return widget

@pytest.fixture
def main_window(qtbot) -> MainWindow:
    """MainWindow with proper cleanup."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window
```

## Essential Test Patterns

### Signal Testing

**Signal test doubles**:
- ✅ `QSignalSpy` for real Qt objects: `spy = QSignalSpy(widget.signal_name)`
- ✅ `TestSignal` for mocks: Available in `tests/test_helpers.py`
- ❌ Never `QSignalSpy` with Mock → `TypeError`

### Error Testing

```python
# Test exceptions with message validation
with pytest.raises(ValueError, match="Frame must be >= 0"):
    curve.set_frame(-1)
```

### Modal Dialog Testing

```python
# Mock exec to prevent blocking
monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
```

**Full examples**: See `tests/test_production_patterns_example.py` for production-realistic patterns.

## TDD Bug Fix Workflow

### RED-GREEN-REFACTOR for Bug Fixes
```python
# 1. RED: Write failing test that exposes bug
def test_timeline_oscillation_bug_fix():
    """Test would have caught the self._fps_spinbox typo."""
    controller = PlaybackController()

    # This line would fail with original bug:
    # AttributeError: 'PlaybackController' has no attribute '_fps_spinbox'
    controller.set_frame_rate(60)

    # Verify both UI and state updated
    assert controller.fps_spinbox.value() == 60
    assert controller.playback_timer.interval() == int(1000/60)

# 2. Fix the bug (in playback_controller.py):
# - self._fps_spinbox.setValue(fps)  # BUG
# + self.fps_spinbox.setValue(fps)   # FIX

# 3. GREEN: Test passes, bug fixed!
# 4. Run full suite to ensure no regressions
```

## Threading Safety Patterns

### Thread Cleanup in Fixtures

**CRITICAL**: Background threads must fully stop before fixture teardown to prevent segfaults.

#### Per-Fixture Thread Cleanup

```python
@pytest.fixture
def worker(file_load_signals):
    """Worker with proper thread cleanup."""
    worker = FileLoadWorker(file_load_signals)
    yield worker

    # Ensure cleanup even if test fails
    try:
        worker.stop()
        # Wait for thread to FULLY stop with timeout
        if worker._thread and worker._thread.is_alive():
            worker._thread.join(timeout=2.0)
            if worker._thread.is_alive():
                import warnings
                warnings.warn(f"Worker thread did not stop within timeout")
    except (RuntimeError, AttributeError):
        pass  # Already stopped
```

#### Global Thread Cleanup (Autouse Fixtures)

**NEW (2025-01)**: Tests can create background threads outside fixtures (MainWindow workers, service threads). Without cleanup, these threads can **deadlock with `processEvents()`** during test teardown.

```python
@pytest.fixture(autouse=True)
def cleanup_background_threads():
    """Clean up ALL background threads after each test.

    CRITICAL: Must run BEFORE processEvents() to prevent deadlock.
    Uses minimal timeout to avoid blocking test execution.
    """
    yield

    # Enumerate and stop all non-daemon background threads
    try:
        import threading
        import logging

        active_threads = [
            t for t in threading.enumerate()
            if t != threading.main_thread() and not t.daemon and t.is_alive()
        ]

        if active_threads:
            logger = logging.getLogger(__name__)
            # CRITICAL: Use minimal timeout (10ms) to avoid blocking
            # Longer timeouts accumulate: 0.5s × 2264 tests = 18+ minutes + hangs
            for thread in active_threads:
                thread.join(timeout=0.01)

            # Log remaining threads at DEBUG level (not warning)
            still_alive = [t for t in active_threads if t.is_alive()]
            if still_alive:
                logger.debug(f"Background threads still running: {[t.name for t in still_alive]}")
    except Exception:
        pass
```

**Why Both Cleanup Strategies?**
- **Per-fixture cleanup**: Catches threads from specific fixtures (2.0s timeout for controlled fixtures)
- **Global cleanup**: Catches orphaned threads from tests (0.01s = 10ms to avoid blocking)
- **Order matters**: Thread cleanup → processEvents() → gc.collect()
- **Performance**: 0.01s × 2264 tests = 22s overhead vs 0.5s = 18+ minutes + hangs
- **Prevents deadlocks**: Ensures clean teardown in test suites of any size

**Verified**: Full CurveEditor test suite (2264 tests) completes in 3 minutes with zero crashes.

### Safe Image Operations

**Thread-safe image processing**:
```python
# ✅ Worker thread: Use ThreadSafeTestImage (not QPixmap)
image = ThreadSafeTestImage(200, 100)

# ✅ Use safe_painter context manager
with safe_painter(image.get_qimage()) as painter:
    painter.drawLine(0, 0, 100, 100)
# painter.end() called automatically

# ✅ Return QImage (main thread converts to QPixmap)
return image.get_qimage()
```

**Available in**: `tests/qt_test_helpers.py`

## Type Ignore Patterns

### Basedpyright Specific Rules
```python
# Use specific diagnostic codes, not blanket ignores
widget.set_data(data)  # pyright: ignore[reportArgumentType]
return value  # pyright: ignore[reportReturnType]
self.attr = val  # pyright: ignore[reportAssignmentType]
obj.maybe_none.method()  # pyright: ignore[reportOptionalMemberAccess]

# NEVER: # type: ignore  (too broad, enforced by basedpyrightconfig.json)
```

## Test Anti-Patterns & Best Practices

### ❌ Never Do These

**Fatal errors**:
- QPixmap in worker thread → FATAL CRASH
- GUI creation in worker threads (QDialog, QWidget in QThread.run())
- QSignalSpy with Mock objects → TypeError

**Common mistakes**:
- Qt container truthiness: `if self.layout:` (use `is not None`)
- Execution order dependencies (test_02 depends on test_01)
- Global/shared state between tests
- Over-mocking (testing mocks, not code)
- Tests without assertions
- Multiple concepts per test (split into separate tests)
- Unclear test names (`test_1` → `test_curve_rejects_duplicate_frames`)

### ✅ Always Do These

```python
# Widget cleanup
qtbot.addWidget(widget)

# Explicit None checks
if widget is not None:

# Initialize before super
self.data = []
super().__init__()

# RuntimeError protection for deleted widgets
try:
    widget.method()
except RuntimeError:
    pass

# Test ALL Protocol methods (prevents typo bugs)
```

## Command Reference

### Essential Commands
```bash
# Test execution
pytest                          # All tests
pytest tests/test_curve_view.py # Single file
pytest -xvs                     # Stop on failure, verbose
pytest --lf                     # Last failed
pytest --ff                     # Failed first

# Debugging
pytest --pdb                    # Debugger on failure
pytest -l                       # Show locals
pytest --tb=short               # Short traceback

# Coverage (see pyproject.toml for config)
pytest --cov --cov-report=term-missing
pytest --cov --cov-report=html
```

### qtbot Key Methods
```python
qtbot.addWidget(widget)         # Auto cleanup (REQUIRED)
qtbot.waitExposed(widget)       # Wait for show
qtbot.wait(100)                 # Process events

# Signals
qtbot.waitSignal(signal, timeout=1000)
qtbot.assertNotEmitted(signal, wait=500)
qtbot.waitUntil(lambda: condition, timeout=1000)

# Interaction
qtbot.mouseClick(widget, Qt.LeftButton)
qtbot.keyClick(widget, Qt.Key_Return)
qtbot.keyClicks(widget, "text")
```

## Quick Diagnostic Table

| Error | Cause | Solution |
|-------|-------|----------|
| `Fatal Python error: Aborted` | QPixmap in thread | Use ThreadSafeTestImage |
| `Segmentation fault` in large test suites | Uncleaned QObjects accumulating | setParent(qapp) + deleteLater() in fixtures |
| `Segmentation fault` in conftest cleanup | Background threads blocking processEvents() | Add global thread cleanup BEFORE processEvents() in autouse fixture |
| `Timeout` during MainWindow creation | QApplication.setStyleSheet() reprocessing all widgets | Apply stylesheet once with flag check |
| `RuntimeError: Internal C++ object` | Widget deleted | try/except RuntimeError |
| `TypeError` with QSignalSpy | Using mock | Use real Qt signal |
| `AttributeError: _fps_spinbox` | Untested Protocol | Test all Protocol methods |
| Widget not cleaned | Missing addWidget | qtbot.addWidget(widget) |
| Test hangs | Worker not quit | worker.stop() + thread.join(timeout) |
| Full suite deadlock in processEvents() | Orphaned background threads | Enumerate and join() all threads in autouse fixture |
| `if self.layout` is False | Qt truthiness | Use `is not None` |
| Resource exhaustion in full suite | QObject accumulation | Explicit parent management in fixtures |
| Event filters not removed | Missing cleanup callback | Use before_close_func parameter |
| `fixture 'qtbot' not found` | Missing pytest-qt | pip install pytest-qt |
| `AssertionError: assert None` | Missing return value | Add return statement to function |
| `No tests collected` | Wrong file naming | Use test_*.py pattern |
| `ModuleNotFoundError` in tests | Wrong import path | Check PYTHONPATH or use relative imports |

## Coverage Configuration

Coverage settings are in `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["ui", "services", "core", "data", "rendering"]
omit = ["*/tests/*", "*_ui.py"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "def paintEvent",
]
```

## Test-Production State Alignment

**Critical Pattern**: Tests must simulate production state initialization, not manually trigger internal updates.

### Anti-Pattern: Manual Cache/State Updates

❌ **BAD - Manually updating state that production doesn't control**
```python
def test_ctrl_click_selection(curve_widget, qtbot):
    # ❌ Manually updating internal cache
    curve_widget._update_screen_points_cache()

    QTest.mouseClick(curve_widget, ...)
    # Test passes, but production may fail if cache isn't updated
```

✅ **GOOD - Let widget initialize naturally through Qt lifecycle**
```python
def test_ctrl_click_selection(curve_view_widget, qtbot):
    # ✅ Let widget show and render naturally
    curve_view_widget.show()
    qtbot.waitExposed(curve_view_widget)
    qtbot.wait(50)  # Allow paint event to complete

    # Production code path: spatial index rebuilds on demand
    QTest.mouseClick(curve_view_widget, ...)
```

**Why This Matters**:
- Tests calling `_update_screen_points_cache()` pass even though production never calls it
- The spatial index rebuilds automatically in `find_point_at_position()`, not via explicit cache updates
- Tests should verify the production code path, not an idealized version

**Discovery**: CurveEditor's Ctrl+click tests originally called `_update_screen_points_cache()` manually. Production worked correctly without it because the spatial index uses `transform.data_to_screen()` directly.

### Boundary Testing: Qt/QTest Edge Cases

**Critical**: QTest.mouseClick has boundary issues at exact widget edges.

❌ **BAD - Test data that maps to boundary coordinates**
```python
# This creates a point at screen (0, 0) - QTest fails!
test_data = [(0, 0.0, 0.0), (1, 100.0, 100.0)]
QTest.mouseClick(widget, Qt.LeftButton, QPoint(0, 0))  # Fails silently
```

✅ **GOOD - Offset coordinates to avoid widget boundaries**
```python
# Ensure all points are away from edges (add 50px margin)
test_data = [(i+1, float(50 + i*100), float(50 + i*100)) for i in range(5)]
QTest.mouseClick(widget, Qt.LeftButton, QPoint(51, 51))  # Works reliably
```

**Observed Behavior** (CurveEditor spatial index tests):
```
Point at (0.0, 0.0): Spatial index finds it ✓, QTest.mouseClick fails ✗
Point at (1.0, 1.0): Spatial index finds it ✓, QTest.mouseClick works ✓
```

**Root Cause**: Qt may not deliver mouse events at exact (0,0) or (width-1, height-1) coordinates. This is a test framework limitation, not a production bug.

**Solution**:
1. Add margin to test data coordinates (50px recommended)
2. Document why test data has offsets
3. Test boundary scenarios with offsets (1,1) instead of (0,0)

### Cache Invalidation Testing

When testing features that depend on cached state:

```python
def test_ctrl_click_after_zoom(curve_view_widget, qtbot):
    """Test that selection works after cache invalidation."""
    # Setup
    curve_view_widget.show()
    qtbot.waitExposed(curve_view_widget)

    # Invalidate caches through normal user action
    curve_view_widget.zoom_factor = 2.0  # Triggers cache rebuild
    curve_view_widget.update()
    qtbot.wait(10)

    # Test still works after cache invalidation
    QTest.mouseClick(...)
    assert selection_is_correct
```

**Don't**:
- Call internal `_invalidate_cache()` methods directly
- Assume caches are always fresh
- Test with idealized state that production doesn't guarantee

**Do**:
- Trigger cache invalidation through user actions (zoom, pan, data change)
- Verify code handles stale/missing caches correctly
- Test both fresh and post-invalidation states

### Production Workflow Testing Infrastructure

**Purpose**: Simplify writing production-realistic tests following best practices discovered during systematic test quality improvements.

**Key Fixtures** (available in all tests via `conftest.py`):

#### 1. `production_widget_factory` - Factory Pattern for Widget Setup

Factory fixture that creates widgets in production-ready state. Follows pytest "factory as fixture" pattern for multiple configurations per test.

```python
def test_multiple_scenarios(production_widget_factory, safe_test_data_factory):
    # Configuration 1: Widget shown and rendered
    widget = production_widget_factory(
        curve_data=safe_test_data_factory(5),
        show=True,           # Default: show widget
        wait_for_render=True # Default: wait for paint + cache rebuild
    )

    # Configuration 2: Same test, different setup
    widget = production_widget_factory(
        curve_data=safe_test_data_factory(10, spacing=50.0),
        wait_for_render=False  # Skip render wait for unit tests
    )
```

**Benefits**:
- Eliminates 6-8 lines of boilerplate setup per test
- Ensures consistent production state initialization
- Single source of truth for production-ready widget configuration

#### 2. `safe_test_data_factory` - Boundary-Safe Test Data

Factory fixture that generates test data avoiding (0,0) boundary issues where QTest.mouseClick fails.

```python
def test_with_safe_data(safe_test_data_factory):
    # Default: 50px margin, 100px spacing
    data = safe_test_data_factory(5)
    # → [(1, 50.0, 50.0), (2, 150.0, 150.0), ...]

    # Custom spacing for dense data
    dense = safe_test_data_factory(10, spacing=50.0)

    # Larger margin for edge case testing
    margin = safe_test_data_factory(3, start_margin=100.0, spacing=200.0)
```

**Benefits**:
- Prevents QTest boundary failures (0,0) automatically
- Configurable for different test scenarios
- Self-documenting (offset explains why)

#### 3. `user_interaction` - Realistic User Action Simulation

Fixture providing helpers that simulate production user interactions with proper coordinate transformations.

```python
def test_user_workflow(production_widget_factory, safe_test_data_factory, user_interaction):
    widget = production_widget_factory(safe_test_data_factory(5))

    # Method 1: Direct coordinate clicking
    user_interaction.click(widget, 50.0, 50.0)  # Data coordinates
    user_interaction.ctrl_click(widget, 150.0, 150.0)

    # Method 2: Point-level selection by index (recommended)
    user_interaction.select_point(widget, 0)         # Select first point
    user_interaction.select_point(widget, 1, ctrl=True)  # Ctrl+click second
```

**Benefits**:
- Handles data-to-screen coordinate transformation
- Clear test intent (no manual QTest/QPointF boilerplate)
- Consistent interaction patterns across tests

#### Auto-Tagging System

Tests using production fixtures are automatically tagged with `@pytest.mark.production` by `conftest.py`:

```bash
# Run only production workflow tests
pytest -m production

# Run fast unit tests only (no Qt)
pytest -m unit

# Run everything except production tests
pytest -m "not production"

# List all production tests
pytest -m production --co -q
```

**Auto-tagging rules** (`pytest_collection_modifyitems` hook):
- Uses `production_widget_factory` or `user_interaction` → `@pytest.mark.production`
- Uses no Qt fixtures (`qtbot`, `qapp`) → `@pytest.mark.unit`

#### Validation Decorator: `@assert_production_realistic`

Decorator that validates tests don't use anti-patterns creating test-production mismatches.

```python
from tests.test_utils import assert_production_realistic

@assert_production_realistic
def test_selection(production_widget_factory, safe_test_data_factory):
    widget = production_widget_factory(safe_test_data_factory(5))

    # ✅ CORRECT: No manual cache updates
    # Cache rebuilds automatically via production code path
    assert widget.curve_data is not None

    # ❌ WRONG (would cause validation failure):
    # widget._update_screen_points_cache()  # Anti-pattern!
```

**Anti-patterns detected**:
- `_update_screen_points_cache()` - Manual cache update (production uses auto-rebuild)
- `._spatial_index` - Direct cache access (should use service methods)

**Features**:
- Smart comment filtering (ignores `# widget._update...` comments)
- `__tracebackhide__` for clean error messages
- Links to testing guide for correct patterns

#### Complete Example

```python
def test_ctrl_click_selection(production_widget_factory, safe_test_data_factory, user_interaction):
    """Example: Multi-selection using Ctrl+click (production-realistic)."""
    # Setup: Widget with safe test data, shown and rendered
    widget = production_widget_factory(curve_data=safe_test_data_factory(5))

    # Simulate user workflow
    user_interaction.select_point(widget, 0)         # Click first point
    user_interaction.select_point(widget, 1, ctrl=True)  # Ctrl+click second

    # Verify production state
    app_state = get_application_state()
    if (cd := app_state.active_curve_data) is None:
        pytest.fail("No active curve")
    curve_name, _ = cd
    selection = app_state.get_selection(curve_name)

    assert len(selection) == 2
    assert {0, 1}.issubset(selection)
```

**Code reduction**: 50% fewer lines vs manual setup (2 setup lines vs 8).

#### When to Use

**Use production fixtures when**:
- Testing user interactions (clicks, drags, keyboard)
- Testing view state changes (zoom, pan)
- Testing multi-step workflows
- Writing integration tests

**Use basic fixtures when**:
- Testing pure logic (no UI rendering needed)
- Testing service methods directly
- Unit testing models/commands
- Performance-critical test loops

**Full examples**: See `tests/test_production_patterns_example.py` for 8 comprehensive examples covering all patterns.

**Discovery**: Production workflow infrastructure developed during systematic test quality review (2025-10-21), aligned with pytest-qt best practices and "factory as fixture" pattern.

## Summary

**Core Principle**: Test behavior, not implementation.

**Threading Rule**: QPixmap = main thread only, QImage = any thread.

**Protocol Rule**: Every Protocol method needs coverage to catch typos.

**Cleanup Rules**:
- QWidgets: Use `qtbot.addWidget()` for automatic cleanup
- QObjects: Set parent to `qapp` OR explicit `deleteLater()` + `processEvents()`
- Background threads: Call `join(timeout)` before fixture teardown (per-fixture + autouse)

**Resource Management**: Session-scope QApplication requires explicit cleanup of all QObjects and background threads.

---
*Version 2025.10.4 - Optimized for Claude Code and LLM consumption*
*Consolidated from 1034 to 799 lines (23% reduction) - removed redundant examples, added references to test files*
*ThreadSafeTestImage available in tests/qt_test_helpers.py*
*QObject lifecycle patterns discovered via Context7 MCP (pytest-qt documentation)*
*Test-Production State Alignment patterns discovered via systematic failure analysis (2025-10-21)*
*Production Workflow Testing Infrastructure added (2025-10-21) - factory fixtures, auto-tagging, validation decorator*
