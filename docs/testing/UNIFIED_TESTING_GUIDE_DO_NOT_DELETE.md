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

### Essential Fixtures
```python
@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()

@pytest.fixture
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

## Decision Functions (Not Pseudo-Code)

### Signal Testing Strategy
```python
def choose_signal_testing_approach(obj, signal_name: str):
    """Determine correct signal testing approach."""
    if isinstance(obj, QObject) and hasattr(obj, signal_name):
        # Real Qt object with real signal
        from pytestqt.qt_compat import qt_api
        signal = getattr(obj, signal_name)
        return qt_api.QtTest.QSignalSpy(signal)
    elif isinstance(obj, Mock):
        # Mock object needs TestSignal
        return TestSignal()
    else:
        raise TypeError(f"Cannot test signal on {type(obj)}")

def should_use_real_component(component_type: str) -> bool:
    """Decide whether to mock or use real component."""
    mock_these = {'external_api', 'network', 'subprocess', 'file_io_when_testing_logic'}
    return component_type not in mock_these
```

## Complete Test Patterns

### TestSignal Implementation (Complete)
```python
class TestSignal:
    """Complete signal test double for non-Qt objects."""
    def __init__(self):
        self.emissions = []
        self.callbacks = []

    def emit(self, *args):
        self.emissions.append(args)
        for callback in self.callbacks:
            callback(*args)

    def connect(self, callback):
        self.callbacks.append(callback)

    def disconnect(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    @property
    def was_emitted(self):
        return len(self.emissions) > 0

    @property
    def emit_count(self):
        return len(self.emissions)
```

### Test CurveViewWidget Pattern
```python
def test_curve_view_point_manipulation(qtbot, curve_widget):
    """Test point operations in CurveViewWidget."""
    # Setup test data
    points = [
        CurvePoint(0, 0.0, 0.0, PointStatus.KEYFRAME),
        CurvePoint(10, 1.0, 1.0, PointStatus.NORMAL)
    ]
    curve_widget.set_curve_data(points)

    # Test selection
    spy = qt_api.QtTest.QSignalSpy(curve_widget.point_selected)
    curve_widget.select_point(0)

    assert len(spy) == 1
    assert spy[0][0] == 0  # First point selected
    assert 0 in curve_widget.selected_indices

    # Test point movement
    move_spy = qt_api.QtTest.QSignalSpy(curve_widget.point_moved)
    curve_widget.update_point(0, 5, 0.5, 0.5)

    assert len(move_spy) == 1
    assert curve_widget.curve_data[0].frame == 5
```

### Test Modal Dialog Pattern
```python
def test_curve_editor_dialog(qtbot, monkeypatch):
    """Test dialog without blocking."""
    # Mock exec to prevent blocking
    monkeypatch.setattr(QDialog, "exec",
                       lambda self: QDialog.DialogCode.Accepted)

    dialog = CurvePropertiesDialog()
    qtbot.addWidget(dialog)

    # Set values
    dialog.fps_spinbox.setValue(60)
    dialog.duration_spinbox.setValue(100)

    result = dialog.exec()
    assert result == QDialog.DialogCode.Accepted
    assert dialog.get_fps() == 60
```

### Test Worker Thread Pattern
```python
def test_background_image_loading(qtbot):
    """Test threading with proper cleanup."""
    from services import ImageLoaderThread

    loader = ImageLoaderThread()
    spy = qt_api.QtTest.QSignalSpy(loader.finished)

    # Use ThreadSafeTestImage for thread safety
    with patch('services.QImage', ThreadSafeTestImage):
        loader.load_path = "/test/image.png"
        loader.start()

        # Wait for completion
        qtbot.waitUntil(lambda: not loader.isRunning(), timeout=5000)

    assert len(spy) == 1

    # Cleanup
    if loader.isRunning():
        loader.quit()
        loader.wait(1000)
```

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

### Safe Image Operations
```python
def process_curve_thumbnail(curve_data):
    """Process image in thread-safe manner."""
    # Worker thread code
    image = ThreadSafeTestImage(200, 100)  # NOT QPixmap

    # Process with QImage internally
    painter = safe_painter(image.get_qimage())
    # ... draw curve ...

    # Return QImage for main thread to convert to QPixmap
    return image.get_qimage()

def test_concurrent_thumbnail_generation():
    """Test parallel image processing."""
    import threading

    def worker(curve_id: int, results: list):
        try:
            # Safe: Uses ThreadSafeTestImage
            thumbnail = process_curve_thumbnail(test_curves[curve_id])
            results.append((curve_id, thumbnail))
        except Exception as e:
            results.append((curve_id, str(e)))

    results = []
    threads = []

    for i in range(5):
        t = threading.Thread(target=worker, args=(i, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == 5
    assert all(isinstance(r[1], QImage) for r in results)
```

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

## Anti-Patterns Reference

### Never Do These
```python
# ❌ QPixmap in worker thread → FATAL CRASH
threading.Thread(target=lambda: QPixmap(100, 100))

# ❌ QSignalSpy with mock → TypeError
spy = QSignalSpy(mock.signal)

# ❌ Qt container truthiness → False when empty!
if self.layout:  # WRONG
if self.layout is not None:  # CORRECT

# ❌ GUI creation in worker thread → CRASH
class Worker(QThread):
    def run(self):
        dialog = QDialog()  # FATAL

# ❌ Unprotected parent access → RuntimeError
super().__init__(parent)  # Parent might be deleted

# ❌ Mock class under test → Pointless
controller = Mock(spec=Controller)
```

### Always Do These
```python
# ✅ Widget cleanup
qtbot.addWidget(widget)

# ✅ Explicit None checks
if widget is not None:

# ✅ Initialize before super
self.data = []
super().__init__()

# ✅ RuntimeError protection
try:
    widget.method()
except RuntimeError:
    pass

# ✅ Test ALL Protocol methods
def test_every_protocol_method():
    """Even if unused in production."""
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
| `RuntimeError: Internal C++ object` | Widget deleted | try/except RuntimeError |
| `TypeError` with QSignalSpy | Using mock | Use real Qt signal |
| `AttributeError: _fps_spinbox` | Untested Protocol | Test all Protocol methods |
| Widget not cleaned | Missing addWidget | qtbot.addWidget(widget) |
| Test hangs | Worker not quit | worker.quit() in cleanup |
| `if self.layout` is False | Qt truthiness | Use `is not None` |

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

## Summary

**Core Principle**: Test behavior, not implementation.

**Threading Rule**: QPixmap = main thread only, QImage = any thread.

**Protocol Rule**: Every Protocol method needs coverage to catch typos.

**Cleanup Rule**: Always use qtbot.addWidget() for automatic cleanup.

---
*Version 2025.01 - Optimized for Claude Code and LLM consumption*
*ThreadSafeTestImage available in tests/qt_test_helpers.py*
