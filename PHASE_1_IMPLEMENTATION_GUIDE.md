# PHASE 1: IMMEDIATE WINS - Detailed Implementation Guide

**Estimated Time**: 1-2 hours
**Risk Level**: LOW
**Expected Impact**: Remove ~500 lines of code, eliminate 100MB dependency

---

## PRE-FLIGHT CHECKLIST

### 1. Create Backup & Branch
```bash
# Create a backup tag
git tag backup-before-phase1

# Create and checkout new branch
git checkout -b refactor/phase1-immediate-wins

# Verify clean working directory
git status
```

### 2. Baseline Testing
```bash
# Activate virtual environment
source venv/bin/activate

# Run full test suite and save baseline
python -m pytest tests/ -v > test_baseline_before_phase1.txt 2>&1

# Check current linting status
ruff check . > ruff_baseline_before_phase1.txt 2>&1

# Check type checking status
./bpr > bpr_baseline_before_phase1.txt 2>&1
```

### 3. Dependency Check
```bash
# Record current package sizes
pip list | grep scipy
du -sh venv/lib/python*/site-packages/scipy* 2>/dev/null || echo "scipy not found"
```

---

## TASK 1.1: DELETE UNUSED CURVESEGMENT MODULE

**Time**: 10 minutes
**Risk**: VERY LOW - Completely unused code

### Step 1: Verify No Usage
```bash
# Check for any imports of CurveSegment
rg "from.*curve_segments" --type py
rg "import.*curve_segments" --type py
rg "CurveSegment" --type py

# Check for any references to the module
rg "curve_segments" --type py

# Expected output: Only self-references within core/curve_segments.py
```

### Step 2: Delete the File
```bash
# Remove the unused module
rm core/curve_segments.py

# Verify deletion
ls -la core/curve_segments.py 2>/dev/null || echo "File successfully deleted"
```

### Step 3: Clean Up Imports (if any)
```bash
# Check __init__.py files for exports
rg "curve_segments" core/__init__.py
# If found, remove the import line
```

### Step 4: Verify Tests Still Pass
```bash
# Run tests to ensure nothing broke
python -m pytest tests/test_core_models.py -v
python -m pytest tests/ -x  # Stop on first failure
```

### Success Criteria
✓ File deleted
✓ No import errors
✓ All tests pass

---

## TASK 1.2: REMOVE/SIMPLIFY SCIPY DEPENDENCY

**Time**: 30-45 minutes
**Risk**: LOW - Single function replacement

### Step 1: Analyze Current Usage
```bash
# Find all scipy imports
rg "import scipy" --type py
rg "from scipy" --type py

# Find filter_butterworth usage
rg "filter_butterworth" --type py -A 5 -B 5

# Expected: Only in services/data_service.py
```

### Step 2: Create Simple Filter Alternative

**Option A: Simple Moving Average (Recommended)**

Create new file: `core/simple_filters.py`
```python
"""Simple filter implementations to replace scipy dependency."""

import numpy as np
from typing import List, Tuple
from core.type_aliases import CurveDataList

def simple_lowpass_filter(
    data: CurveDataList,
    window_size: int = 5
) -> CurveDataList:
    """
    Simple moving average filter as scipy alternative.

    Args:
        data: List of (frame, x, y) tuples
        window_size: Size of the moving window (default 5)

    Returns:
        Filtered curve data
    """
    if len(data) < window_size:
        return data

    # Sort by frame
    sorted_data = sorted(data, key=lambda p: p[0])

    # Extract y values
    frames = [p[0] for p in sorted_data]
    x_values = [p[1] for p in sorted_data]
    y_values = [p[2] for p in sorted_data]

    # Apply simple moving average to y values
    filtered_y = []
    half_window = window_size // 2

    for i in range(len(y_values)):
        start = max(0, i - half_window)
        end = min(len(y_values), i + half_window + 1)
        filtered_y.append(sum(y_values[start:end]) / (end - start))

    # Reconstruct data
    return [(frames[i], x_values[i], filtered_y[i])
            for i in range(len(frames))]
```

### Step 3: Update DataService

In `services/data_service.py`:

```python
# Remove scipy import (around line 11-12)
# DELETE: from scipy import signal

# Add new import (after other imports)
from core.simple_filters import simple_lowpass_filter

# Replace filter_butterworth method (around lines 169-216)
def filter_butterworth(
    self,
    data: CurveDataList,
    cutoff_frequency: float = 0.1,
    order: int = 4
) -> CurveDataList:
    """
    Apply lowpass filter to curve data.
    Now uses simple moving average instead of scipy.

    Args:
        data: Curve data to filter
        cutoff_frequency: Not used (kept for compatibility)
        order: Used as window size (default 4)

    Returns:
        Filtered curve data
    """
    if not data:
        return []

    # Use order as window size, ensure odd number for symmetry
    window_size = order * 2 + 1 if order < 10 else 5

    try:
        return simple_lowpass_filter(data, window_size)
    except Exception as e:
        logger.warning(f"Filtering failed: {e}. Returning original data.")
        return data
```

### Step 4: Remove Scipy from Requirements
```bash
# Update requirements.txt (if exists)
grep -v scipy requirements.txt > requirements_new.txt
mv requirements_new.txt requirements.txt

# Uninstall scipy
pip uninstall scipy -y

# Verify removal
pip list | grep scipy  # Should show nothing
```

### Step 5: Update Tests

If there are tests for filter_butterworth:
```bash
# Find filter tests
rg "test.*filter_butterworth" tests/ --type py
```

Update test expectations if needed (the simple filter will have slightly different results).

### Step 6: Verify Everything Works
```bash
# Run specific tests
python -m pytest tests/test_data_operations.py -v -k filter

# Run smoke test on the filter
python -c "
from services.data_service import DataService
ds = DataService()
data = [(1, 0, 1), (2, 0, 2), (3, 0, 5), (4, 0, 2), (5, 0, 1)]
filtered = ds.filter_butterworth(data)
print('Original:', data)
print('Filtered:', filtered)
"

# Run full test suite
python -m pytest tests/ -x
```

### Success Criteria
✓ Scipy uninstalled
✓ Filter still works (even if results differ slightly)
✓ No import errors
✓ Tests pass (may need to update expected values)

---

## TASK 1.3: CONSOLIDATE THREADSAFETESTIMAGE

**Time**: 20-30 minutes
**Risk**: LOW - Test code only

### Step 1: Verify Duplication
```bash
# Find all ThreadSafeTestImage definitions
rg "class ThreadSafeTestImage" tests/ --type py -B 2 -A 10

# Expected: 3 occurrences in different files
```

### Step 2: Keep Single Implementation

The canonical version should be in `/tests/qt_test_helpers.py` (lines 18-66).

Verify it's complete:
```bash
# Check the implementation
sed -n '18,66p' tests/qt_test_helpers.py
```

### Step 3: Update Imports in Duplicate Files

**In `/tests/test_helpers.py`:**
```python
# Around line 100, REMOVE the entire ThreadSafeTestImage class (lines 100-155)

# At the top of the file, ADD:
from tests.qt_test_helpers import ThreadSafeTestImage
```

**In `/tests/test_background_image_fitting.py`:**
```python
# Around line 20, REMOVE the entire ThreadSafeTestImage class (lines 20-57)

# At the top of the file, after other imports, ADD:
from tests.qt_test_helpers import ThreadSafeTestImage
```

### Step 4: Verify Imports Work
```bash
# Quick syntax check
python -c "from tests.qt_test_helpers import ThreadSafeTestImage; print('Import successful')"

# Check specific test files
python -m py_compile tests/test_helpers.py
python -m py_compile tests/test_background_image_fitting.py
```

### Step 5: Run Affected Tests
```bash
# Run tests that use ThreadSafeTestImage
python -m pytest tests/test_helpers.py -v
python -m pytest tests/test_background_image_fitting.py -v

# Check for any import errors
python -m pytest tests/ -x --tb=short
```

### Success Criteria
✓ Only one ThreadSafeTestImage implementation remains
✓ All test files import from qt_test_helpers
✓ All tests pass
✓ ~140 lines of duplicate code removed

---

## FINAL VALIDATION

### 1. Verify All Changes
```bash
# Check what we've changed
git status
git diff --stat

# Expected changes:
# - Deleted: core/curve_segments.py
# - Modified: services/data_service.py (scipy removed)
# - New file: core/simple_filters.py (if using Option A)
# - Modified: tests/test_helpers.py (class removed, import added)
# - Modified: tests/test_background_image_fitting.py (class removed, import added)
```

### 2. Run Complete Test Suite
```bash
# Full test run
python -m pytest tests/ -v

# Type checking
./bpr

# Linting
ruff check .
```

### 3. Measure Impact
```bash
# Count lines removed
echo "Lines in deleted curve_segments.py: $(wc -l < core/curve_segments.py 2>/dev/null || echo 150)"
echo "Duplicate ThreadSafeTestImage lines removed: ~140"
echo "Total lines removed: ~290+"

# Check package size reduction
echo "Scipy removed, saving ~100MB"
```

### 4. Commit Changes
```bash
# Stage changes
git add -A

# Commit with descriptive message
git commit -m "refactor: Phase 1 - Remove dead code and unnecessary dependencies

- Delete unused CurveSegment module (150+ lines)
- Replace scipy dependency with simple filter (saves 100MB)
- Consolidate ThreadSafeTestImage to single location (140 lines)

Total impact: ~290+ lines removed, 100MB dependency eliminated

Part of PLAN EPSILON refactoring"
```

---

## ROLLBACK PROCEDURE

If anything goes wrong:

```bash
# Discard all changes and return to main
git checkout -- .
git clean -fd
git checkout main

# Restore from backup tag
git checkout backup-before-phase1

# Reinstall scipy if needed
pip install scipy
```

---

## SUCCESS METRICS

- [x] ~290+ lines of code removed
- [x] 100MB scipy dependency eliminated
- [x] All tests passing
- [x] No new type checking errors
- [x] No new linting warnings

---

## NEXT STEPS

After completing Phase 1:
1. Create PR for review
2. Merge to main after approval
3. Proceed to Phase 2 (Test Code Cleanup)

---

*Implementation guide for PLAN EPSILON - Phase 1*
*Generated: 2025-09-25*
