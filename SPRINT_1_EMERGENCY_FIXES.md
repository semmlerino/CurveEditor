# Sprint 1: Emergency Fixes - Technical Specification

## Critical Issues to Fix (Priority Order)

### 1. Threading Safety Violations [CRITICAL - Data Corruption Risk]

#### Issue #1: Double-Checked Locking Pattern
**File:** `services/__init__.py`, lines 66-107
**Risk:** Race conditions causing multiple service instances, data corruption
**Time to Fix:** 2 hours
**Testing Required:** 4 hours

```python
# BROKEN CODE (Current):
def get_data_service() -> DataService:
    global _data_service
    if _data_service is None:  # ❌ RACE CONDITION HERE
        with _service_lock:
            if _data_service is None:
                _data_service = DataService()
    return _data_service

# FIXED CODE:
def get_data_service() -> DataService:
    global _data_service
    with _service_lock:  # ✅ Always lock first
        if _data_service is None:
            _data_service = DataService()
    return _data_service
```

**Apply Same Fix To:**
- `get_transform_service()` - line 46
- `get_interaction_service()` - line 86
- `get_ui_service()` - line 106

#### Issue #2: Unsynchronized Service Caches
**Files:** Multiple service files
**Risk:** Dictionary corruption during concurrent access
**Time to Fix:** 4 hours
**Testing Required:** 4 hours

```python
# services/data_service.py - ADD at line 45:
import threading

class DataService:
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock
        self._recent_files: list[str] = []
        self._image_cache: dict[str, QImage] = {}
        self._cache_size_limit = 50

    # Wrap ALL cache access methods:
    def add_recent_file(self, path: str) -> None:
        with self._lock:
            self._recent_files.append(path)
            if len(self._recent_files) > 10:
                self._recent_files.pop(0)

    def cache_image(self, path: str, image: QImage) -> None:
        with self._lock:
            if len(self._image_cache) >= self._cache_size_limit:
                oldest = next(iter(self._image_cache))
                del self._image_cache[oldest]
            self._image_cache[path] = image
```

**Apply Similar Protection To:**
- `services/transform_service.py` - `_transform_cache` (line 89)
- `services/interaction_service.py` - history operations (line 145+)
- `ui/state_manager.py` - all state mutations

### 2. Critical Runtime Bugs [HIGH - User Impact]

#### Bug #1: Null Pointer Dereference
**File:** `ui/main_window.py`, line 1135
**Symptom:** AttributeError crash when loading files
**Time to Fix:** 15 minutes
**Testing Required:** 30 minutes

```python
# BROKEN:
self.file_load_thread.finished.connect(self.file_load_thread.deleteLater)

# FIXED:
if self.file_load_thread is not None:
    self.file_load_thread.finished.connect(self.file_load_thread.deleteLater)
```

#### Bug #2: Silent Exception Swallowing
**File:** `services/data_service.py`, line 607
**Symptom:** Errors hidden, debugging impossible
**Time to Fix:** 30 minutes
**Testing Required:** 1 hour

```python
# BROKEN:
try:
    # ... file loading code ...
except Exception:
    pass  # ❌ Hides all errors!

# FIXED:
try:
    # ... file loading code ...
except (json.JSONDecodeError, ValueError) as e:
    logger.debug(f"Failed to parse as JSON: {e}")
    # Try next format
except IOError as e:
    logger.warning(f"File access error: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error loading file: {e}", exc_info=True)
    raise  # Re-raise unexpected errors
```

#### Bug #3: Missing History Container Implementation
**File:** `services/interaction_service.py`
**Symptom:** History operations may fail silently
**Time to Fix:** 2 hours
**Testing Required:** 2 hours

```python
# ADD at line 50:
@dataclass
class HistoryContainer:
    """Thread-safe history container."""

    def __init__(self):
        self._lock = threading.Lock()
        self.history_stack: list[CompressedStateSnapshot] = []
        self.redo_stack: list[CompressedStateSnapshot] = []
        self.max_history = 100

    def push_state(self, snapshot: CompressedStateSnapshot) -> None:
        with self._lock:
            self.history_stack.append(snapshot)
            if len(self.history_stack) > self.max_history:
                self.history_stack.pop(0)
            self.redo_stack.clear()

    def undo(self) -> CompressedStateSnapshot | None:
        with self._lock:
            if self.history_stack:
                state = self.history_stack.pop()
                self.redo_stack.append(state)
                return self.history_stack[-1] if self.history_stack else None
            return None
```

### 3. Testing Infrastructure [MEDIUM - Quality Assurance]

#### Create Threading Test Suite
**File:** `tests/test_threading_safety.py` (NEW)
**Purpose:** Verify all threading fixes work correctly
**Time to Create:** 4 hours

```python
#!/usr/bin/env python3
"""
Threading safety test suite for CurveEditor.
Tests all concurrent access patterns and verifies thread safety.
"""

import concurrent.futures
import threading
import time
from typing import Any
import pytest

from services import (
    get_data_service,
    get_transform_service,
    get_interaction_service,
    get_ui_service
)

class TestServiceThreadSafety:
    """Test thread safety of service layer."""

    def test_singleton_initialization_race(self):
        """Verify only one instance created under concurrent access."""
        results = set()
        barrier = threading.Barrier(20)  # Synchronize thread start

        def get_service():
            barrier.wait()  # All threads start together
            service = get_data_service()
            results.add(id(service))
            return service

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(get_service) for _ in range(100)]
            concurrent.futures.wait(futures)

        assert len(results) == 1, f"Multiple instances created: {len(results)}"

    def test_cache_concurrent_modifications(self):
        """Test cache operations under heavy concurrent load."""
        service = get_data_service()
        errors = []

        def cache_stress_test(thread_id: int):
            try:
                for i in range(1000):
                    # Rapid cache operations
                    key = f"key_{thread_id}_{i}"
                    service.cache_image(key, f"data_{thread_id}")
                    _ = service.get_cached_image(key)

                    # Verify cache size limit
                    if len(service._image_cache) > 50:
                        errors.append(f"Cache exceeded limit: {len(service._image_cache)}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = []
        for i in range(10):
            t = threading.Thread(target=cache_stress_test, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert not errors, f"Errors detected: {errors}"

    def test_history_concurrent_operations(self):
        """Test history stack under concurrent access."""
        service = get_interaction_service()

        def history_operations(thread_id: int):
            for i in range(100):
                # Simulate history operations
                service.add_to_history(mock_main_window())
                if i % 10 == 0:
                    service.undo(mock_main_window())
                if i % 15 == 0:
                    service.redo(mock_main_window())

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(history_operations, i) for i in range(5)]
            concurrent.futures.wait(futures)

        # Verify history integrity
        assert service._history_container is not None
        assert isinstance(service._history_container.history_stack, list)

def mock_main_window():
    """Create mock main window for testing."""
    class MockWindow:
        def __init__(self):
            self.curve_widget = MockCurveWidget()

    class MockCurveWidget:
        def __init__(self):
            self.curve_data = []
            self.selected_indices = set()

    return MockWindow()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

## Verification Checklist

### Before Starting
- [ ] Create git branch: `git checkout -b sprint1-emergency-fixes`
- [ ] Run baseline tests: `python -m pytest tests/`
- [ ] Record baseline performance: `python -m pytest tests/test_performance_benchmarks.py`
- [ ] Backup current state: `git stash` or commit WIP

### After Each Fix
- [ ] Run specific test for that fix
- [ ] Run full test suite
- [ ] Check performance hasn't degraded
- [ ] Commit with descriptive message

### Daily Checklist
- [ ] Morning: Review plan for the day
- [ ] Implement fixes (2-4 hours)
- [ ] Write/run tests (2-4 hours)
- [ ] Document changes
- [ ] Evening: Commit and push changes

### End of Sprint
- [ ] All tests passing (390/392 minimum)
- [ ] Performance maintained (±5% of baseline)
- [ ] No new ruff errors
- [ ] Documentation updated
- [ ] Code review completed
- [ ] Merge to main branch

## Commands Reference

```bash
# Activate environment
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run threading tests only
python -m pytest tests/test_threading_safety.py -v --tb=short

# Run performance benchmarks
python -m pytest tests/test_performance_benchmarks.py --benchmark-only

# Check for ruff errors
ruff check .

# Check type errors
./bpr

# Run specific test file
python -m pytest tests/test_curve_service.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Profile for performance
py-spy record -o profile.svg -- python main.py
```

## Rollback Plan

If any fix causes issues:

### Immediate Rollback
```bash
# Revert last commit
git revert HEAD

# Or reset to specific commit
git reset --hard <commit-hash>

# Apply emergency mutex wrapper
# In services/__init__.py, add:
_global_mutex = threading.Lock()

def emergency_wrapper(func):
    def wrapped(*args, **kwargs):
        with _global_mutex:
            return func(*args, **kwargs)
    return wrapped

# Apply to all service methods
```

### Investigation
1. Enable thread debugging:
```python
import threading
threading.settrace(lambda *args: print(args))
```

2. Use thread sanitizer:
```bash
python -X dev main.py  # Enable development mode
```

3. Add extensive logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

## Success Criteria

### Must Have (Sprint Fails Without)
- [ ] Zero threading-related crashes in 1000 test runs
- [ ] All 3 critical bugs fixed and verified
- [ ] Performance within 5% of baseline
- [ ] All existing tests still pass

### Should Have (Important)
- [ ] Comprehensive threading test suite (20+ tests)
- [ ] Documentation of all changes
- [ ] Code review approval

### Nice to Have (If Time Permits)
- [ ] Additional performance optimizations
- [ ] Extended stress testing
- [ ] Automated benchmark comparisons

## Time Allocation (2 Weeks)

### Week 1 (40 hours)
- Day 1-2: Threading fixes (16 hours)
- Day 3: Bug fixes (8 hours)
- Day 4: Testing (8 hours)
- Day 5: Integration & verification (8 hours)

### Week 2 (40 hours)
- Day 6-7: Extended testing (16 hours)
- Day 8: Performance verification (8 hours)
- Day 9: Documentation (8 hours)
- Day 10: Review & handoff (8 hours)

## Contact for Questions

- **Technical Lead:** Review threading design decisions
- **QA Team:** Coordinate testing efforts
- **DevOps:** CI/CD pipeline updates
- **Product Owner:** Progress updates

---

**Remember:** These are CRITICAL fixes. Take time to do them right. It's better to be thorough than fast.
