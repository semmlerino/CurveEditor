# TEST REMEDIATION PLAN - Fixing Testing Best Practice Violations

**Created**: 2025-09-25
**Priority**: HIGH - Multiple critical violations found
**Estimated Total Effort**: 8-12 hours

## Executive Summary

Our codebase violates multiple testing best practices from UNIFIED_TESTING_GUIDE:
- 🔴 **CRITICAL**: QPixmap in tests (crash risk), Protocol compliance failures
- 🔴 **HIGH**: hasattr() destroying type info, untested Protocol methods
- 🟡 **MEDIUM**: Signal chain gaps, no dead code detection

## Phase 1: Critical Threading & Crash Risks (2 hours)

### 1.1 Replace QPixmap with ThreadSafeTestImage

**Files to fix**:
```bash
grep -l "QPixmap" tests/*.py
# Returns: test_helpers.py, run_tests_safe.py, test_grid_centering.py,
#          test_core_models.py, qt_test_helpers.py
```

**Action**: Replace all QPixmap usage in tests
```python
# ❌ BEFORE (can crash)
pixmap = QPixmap(100, 100)

# ✅ AFTER (thread-safe)
from tests.thread_safe_image import ThreadSafeTestImage
image = ThreadSafeTestImage(100, 100)
```

**Create**: `tests/thread_safe_image.py`
```python
"""Thread-safe image for testing (from UNIFIED_TESTING_GUIDE)."""

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QColor

class ThreadSafeTestImage:
    """Thread-safe test double for QPixmap using QImage internally."""

    def __init__(self, width: int = 100, height: int = 100):
        self._image = QImage(width, height, QImage.Format.Format_RGB32)
        self._width = width
        self._height = height
        self._image.fill(QColor(255, 255, 255))

    def fill(self, color: QColor = None) -> None:
        if color is None:
            color = QColor(255, 255, 255)
        self._image.fill(color)

    def isNull(self) -> bool:
        return self._image.isNull()

    def size(self) -> QSize:
        return QSize(self._width, self._height)

    def to_qimage(self) -> QImage:
        """Get underlying QImage for operations that need it."""
        return self._image
```

### 1.2 Fix Protocol Compliance Failures

**Current failures**:
```
FrameNavigationController does not implement FrameNavigationProtocol
ActionHandlerController does not implement ActionHandlerProtocol
UIInitializationController does not implement UIInitializationProtocol
ViewOptionsController does not implement ViewOptionsProtocol
PointEditorController does not implement PointEditorProtocol
```

**Action**: Ensure all controllers fully implement their protocols
```bash
# Find missing methods
for controller in FrameNavigation ActionHandler UIInitialization ViewOptions PointEditor; do
  echo "=== $controller ==="
  diff <(grep "def " ui/protocols/controller_protocols.py | grep -A10 "${controller}Protocol") \
       <(grep "def " ui/controllers/*${controller,,}*.py)
done
```

## Phase 2: Type Safety Violations (2 hours)

### 2.1 Replace hasattr() Usage

**Find all violations**:
```bash
grep -n "hasattr" --include="*.py" -r . --exclude-dir=tests --exclude-dir=venv
```

**Files to fix**:
1. `ui/controllers/playback_controller.py:245-247`
2. `ui/timeline_tabs.py:621`

**Pattern to replace**:
```python
# ❌ BEFORE (destroys type info)
if hasattr(self.parent(), "curve_widget"):
    curve_widget = self.parent().curve_widget

# ✅ AFTER Option 1: None check
parent = self.parent()
if parent is not None:
    curve_widget = getattr(parent, "curve_widget", None)
    if curve_widget is not None:
        # use curve_widget

# ✅ AFTER Option 2: Try/except for Qt objects
try:
    if self.parent() is not None:
        curve_widget = self.parent().curve_widget  # pyright: ignore[reportAttributeAccessIssue]
        if curve_widget is not None:
            # use curve_widget
except (AttributeError, RuntimeError):
    pass  # Parent deleted or no attribute
```

### 2.2 Add Type Guards Where hasattr() is Necessary

**Create**: `core/type_guards.py`
```python
"""Type guards for runtime type checking."""

from typing import TypeGuard, Any
from ui.curve_view_widget import CurveViewWidget

def has_curve_widget(obj: Any) -> TypeGuard[object]:
    """Type guard for objects with curve_widget attribute."""
    return hasattr(obj, "curve_widget") and isinstance(
        getattr(obj, "curve_widget", None), CurveViewWidget
    )

# Use as:
# if has_curve_widget(self.parent()):
#     self.parent().curve_widget  # Type checker knows this exists
```

## Phase 3: Protocol Method Testing (4 hours)

### 3.1 Audit All Protocol Methods

**Generate Protocol coverage report**:
```bash
# Find all Protocol classes
grep -h "class.*Protocol(Protocol)" -r . --include="*.py" | \
  sed 's/class \(.*\)Protocol.*/\1/' | sort -u > protocols.txt

# For each protocol, find test coverage
while read protocol; do
  echo "=== $protocol Protocol ==="
  # Find protocol methods
  grep -A50 "class ${protocol}Protocol" --include="*.py" -r . | \
    grep "def " | sed 's/.*def \([^(]*\).*/\1/'

  # Find tests
  echo "Tests found:"
  grep -l "${protocol}" tests/*.py 2>/dev/null || echo "NONE"
  echo
done < protocols.txt > protocol_coverage.txt
```

### 3.2 Create Protocol Test Template

**Template**: `tests/test_protocol_compliance_template.py`
```python
"""Template for testing Protocol compliance."""

import pytest
from typing import Protocol, runtime_checkable

def test_protocol_compliance(implementation, protocol_class):
    """Ensure implementation satisfies protocol."""
    # Check it's the right type
    assert isinstance(implementation, protocol_class)

    # Get all protocol methods
    protocol_methods = [
        name for name in dir(protocol_class)
        if not name.startswith('_') and callable(getattr(protocol_class, name))
    ]

    # Test each method exists and is callable
    for method_name in protocol_methods:
        assert hasattr(implementation, method_name), f"Missing {method_name}"
        method = getattr(implementation, method_name)
        assert callable(method), f"{method_name} is not callable"

def test_protocol_methods_have_tests(test_module, protocol_methods):
    """Ensure each protocol method has at least one test."""
    for method in protocol_methods:
        test_name = f"test_{method}"
        assert any(test_name in name for name in dir(test_module)), \
            f"No test found for {method}"
```

### 3.3 Add Missing Protocol Tests

**Priority protocols** (most critical first):
1. **FrameNavigationProtocol** - Core functionality
2. **ActionHandlerProtocol** - User actions
3. **ViewOptionsProtocol** - Display settings
4. **ServiceProtocol** - All services
5. **StateManagerProtocol** - State management

**Test pattern for each**:
```python
class Test{Protocol}Compliance:
    """Test {Protocol} implementation."""

    def test_all_methods_present(self, controller):
        """Test all protocol methods exist."""
        # List all protocol methods
        required_methods = [
            'method1', 'method2', 'method3'
        ]
        for method in required_methods:
            assert hasattr(controller, method)

    def test_{method}_api(self, controller):
        """Test {method} programmatic API."""
        # Test the method works correctly
        result = controller.{method}(test_input)
        assert result == expected

    def test_{method}_ui_path(self, controller, qtbot):
        """Test {method} via UI interaction."""
        # Test UI triggers the method
        qtbot.mouseClick(button, Qt.LeftButton)
        assert controller.state == expected
```

## Phase 4: Signal Chain Testing (2 hours)

### 4.1 Create Signal Chain Verification

**Create**: `tests/test_signal_chains.py`
```python
"""Test signal chains between controllers."""

import pytest
from PySide6.QtTest import QSignalSpy

class TestSignalChains:
    """Verify all required signal connections."""

    def test_playback_to_frame_nav_connection(self, main_window):
        """Test playback -> frame navigation chain."""
        # This connection is critical for oscillation
        playback = main_window.playback_controller
        frame_nav = main_window.frame_nav_controller

        # Verify connection exists (not just in test setup!)
        # Method 1: Use signal spy
        spy = QSignalSpy(playback.frame_requested)
        playback._on_playback_timer()

        assert spy.count() > 0, "Signal not emitted"

        # Verify frame actually updated
        initial = main_window.state_manager.current_frame
        playback._on_playback_timer()
        assert main_window.state_manager.current_frame != initial

    def test_all_critical_chains(self, main_window):
        """Test all critical signal chains are connected."""
        critical_chains = [
            (main_window.playback_controller.frame_requested,
             main_window.frame_nav_controller.set_frame,
             "Playback -> Frame Navigation"),

            (main_window.curve_widget.point_moved,
             main_window.on_point_moved,
             "Curve Widget -> Main Window"),

            (main_window.state_manager.frame_changed,
             main_window.on_state_frame_changed,
             "State Manager -> Main Window"),
        ]

        for signal, slot, description in critical_chains:
            # This is pseudocode - actual verification varies
            assert signal_is_connected_to(signal, slot), \
                f"Missing connection: {description}"
```

### 4.2 Add Connection Integrity Check

**Add to**: `ui/controllers/signal_connection_manager.py`
```python
def verify_critical_connections(self) -> tuple[bool, list[str]]:
    """Verify all critical connections are established."""
    failures = []

    # Define critical connections
    required = [
        ('playback.frame_requested', 'frame_nav.set_frame'),
        ('curve_widget.selection_changed', 'on_curve_selection_changed'),
        # ... more critical connections
    ]

    for signal_path, slot_path in required:
        if not self._is_connected(signal_path, slot_path):
            failures.append(f"{signal_path} -> {slot_path}")

    return len(failures) == 0, failures

def _is_connected(self, signal_path: str, slot_path: str) -> bool:
    """Check if a signal is connected to a slot."""
    # Implementation to check Qt signal connections
    # This is complex due to Qt's C++ internals
    pass
```

## Phase 5: Dead Code Detection (2 hours)

### 5.1 Generate Coverage Report

**Run coverage analysis**:
```bash
# Full coverage with branch analysis
pytest --cov=. --cov-branch --cov-report=html --cov-report=term-missing

# Find methods with 0% coverage
grep -E "def.*0%" htmlcov/index.html > zero_coverage_methods.txt

# Find Protocol methods never called
for file in $(find . -name "*.py" -path "*/protocols/*"); do
  echo "=== $file ==="
  grep "def " $file | while read line; do
    method=$(echo $line | sed 's/.*def \([^(]*\).*/\1/')
    count=$(grep -r "$method" . --include="*.py" | wc -l)
    if [ $count -le 1 ]; then
      echo "DEAD CODE: $method"
    fi
  done
done
```

### 5.2 Create Dead Code Report

**Generate**: `dead_code_report.md`
```markdown
# Dead Code Analysis Report

## Protocol Methods Never Called
- PlaybackControllerProtocol.set_frame_rate() ✅ FIXED
- [List other dead methods found]

## Public Methods with 0% Coverage
- [List methods]

## Recommended Actions
1. Delete truly dead code
2. Add tests for methods that should be kept
3. Mark deprecated methods clearly
```

## Phase 6: Continuous Compliance (1 hour)

### 6.1 Add Pre-commit Hook

**Create**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: local
    hooks:
      - id: no-hasattr
        name: Check for hasattr usage
        entry: sh -c 'git diff --cached --name-only | xargs grep -l "hasattr" && exit 1 || exit 0'
        language: system
        files: \.py$

      - id: protocol-test-coverage
        name: Check Protocol test coverage
        entry: python scripts/check_protocol_coverage.py
        language: python
        files: ^ui/protocols/.*\.py$
```

### 6.2 Add CI Check

**Add to**: `.github/workflows/tests.yml` (or equivalent)
```yaml
- name: Check testing best practices
  run: |
    # No hasattr in non-test code
    ! grep -r "hasattr" --include="*.py" --exclude-dir=tests --exclude-dir=venv .

    # No QPixmap in tests
    ! grep -r "QPixmap" tests/

    # Protocol coverage check
    python scripts/check_protocol_coverage.py
```

## Success Criteria

### Phase 1 ✓
- [ ] No QPixmap usage in tests
- [ ] All Protocol compliance checks pass
- [ ] No threading crashes in tests

### Phase 2 ✓
- [ ] Zero hasattr() calls in production code
- [ ] Type guards for necessary runtime checks
- [ ] Basedpyright passes with no suppressions

### Phase 3 ✓
- [ ] 100% of Protocol methods have tests
- [ ] Both UI and API paths tested
- [ ] Protocol compliance tests for all 25+ protocols

### Phase 4 ✓
- [ ] All critical signal chains tested
- [ ] Signal integrity verification in place
- [ ] No missing production connections

### Phase 5 ✓
- [ ] Coverage report generated
- [ ] Dead code identified and removed
- [ ] All public methods have >0% coverage

### Phase 6 ✓
- [ ] Pre-commit hooks prevent violations
- [ ] CI catches best practice violations
- [ ] Compliance is automatic

## Rollback Plan

Each phase can be rolled back independently:
```bash
git tag before-test-remediation
git checkout -b test-remediation-phase-{N}
# Make changes
# If issues arise:
git checkout main
```

## Timeline

- **Week 1**: Phases 1-2 (Critical fixes)
- **Week 2**: Phases 3-4 (Protocol testing)
- **Week 3**: Phases 5-6 (Dead code & automation)

## Commands Reference

```bash
# Find violations
grep -rn "hasattr" --include="*.py" .
grep -rn "QPixmap" tests/
grep -h "class.*Protocol(Protocol)" -r .

# Run targeted tests
pytest tests/test_protocol_compliance.py -xvs
pytest tests/test_signal_chains.py -xvs

# Coverage analysis
pytest --cov=ui/controllers --cov-report=term-missing
pytest --cov=ui/protocols --cov-report=html

# Type checking
./bpr ui/controllers/
ruff check . --select=ANN  # Check annotations
```

## Notes

- Priority on CRITICAL issues that can cause crashes
- Each phase is independently valuable
- Tests should follow TDD where possible
- Document why if hasattr() is truly needed
- Consider ThreadSafeTestImage for all image testing

---
*Last Updated: 2025-09-25*
*Estimated Effort: 8-12 hours total*
*Priority: HIGH - Multiple critical violations*
