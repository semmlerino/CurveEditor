# CurveEditor: Transformation System Refactoring Guide

## Overview

This document provides a step-by-step plan to complete the migration from the legacy transformation system to the unified transformation system in CurveEditor. This is the **highest priority** refactoring task as it resolves critical architectural inconsistencies.

## Current State Analysis

### Problems with Current Implementation

1. **Dual System Coexistence**: Both `TransformStabilizer` (legacy) and `UnifiedTransformationService` (new) are active
2. **Inconsistent Transformation Calls**: Some parts use old methods, others use new
3. **Patch-based Integration**: The unified system is applied via patches rather than native integration
4. **Incomplete Migration**: Several files still reference legacy transformation methods

### Files Requiring Changes

**Legacy System Files (To Remove/Refactor)**:
- `transform_fix.py` - Legacy stabilizer
- `services/transform_stabilizer.py` - Old stabilizer service
- `services/transformation_shim.py` - Compatibility layer
- `services/transformation_integration.py` - Legacy integration

**Core System Files (To Update)**:
- `main_window.py` - Remove legacy initialization
- `curve_view.py` - Update transformation calls
- `services/curve_service.py` - Use unified transformations
- `signal_registry.py` - Remove legacy dependencies

## Refactoring Plan

### Phase 1: Remove Legacy Dependencies (1-2 days)

#### Step 1.1: Update Main Window Initialization

**Current Code**:
```python
# main_window.py lines 47-56
# DEPRECATED: Old transform system (will be removed)
from transform_fix import TransformStabilizer

# NEW: Auto-activate unified transformation system
try:
    from services.main_window_unified_patch import apply_unified_transform_patch
    apply_unified_transform_patch()
    print("✅ Unified transformation system activated")
except Exception as e:
    print(f"⚠️  Using legacy transformation system: {e}")
```

**Refactored Code**:
```python
# main_window.py
from services.unified_transformation_service import UnifiedTransformationService

# In MainWindow.__init__()
def __init__(self):
    # ... existing initialization ...

    # Initialize unified transformation system
    self._setup_transformation_system()

def _setup_transformation_system(self):
    """Initialize the unified transformation system."""
    try:
        # Clear any existing transform cache
        UnifiedTransformationService.clear_cache()
        logger.info("✅ Unified transformation system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize transformation system: {e}")
        raise
```

#### Step 1.2: Remove Legacy Imports

Remove these imports from all files:
```python
# REMOVE THESE LINES:
from transform_fix import TransformStabilizer
from services.transform_stabilizer import TransformStabilizer
from services.transformation_shim import TransformationShim
```

**Add these imports instead**:
```python
# ADD THESE LINES:
from services.unified_transformation_service import UnifiedTransformationService
from services.view_state import ViewState
```

#### Step 1.3: Update Setup UI Method

**Current Code**:
```python
# main_window.py lines 366-375
def setup_ui(self):
    # ... UI setup ...

    # Initialize the TransformStabilizer to prevent curve shifting issues
    if hasattr(self, 'curve_view') and self.curve_view:
        try:
            # Install the transform stabilizer to ensure consistent coordinate transformations
            TransformStabilizer.install(self.curve_view)
            logger.info("TransformStabilizer installed successfully")
        except Exception as e:
            logger.error(f"Failed to install TransformStabilizer: {str(e)}")
```

**Refactored Code**:
```python
def setup_ui(self):
    # ... UI setup ...

    # Transformation system is now initialized in __init__
    # No additional setup needed here
    logger.info("UI setup complete with unified transformation system")
```

### Phase 2: Update Transformation Calls (2-3 days)

#### Step 2.1: Update CurveView Point Transformations

**Target File**: `curve_view.py`

**Current Pattern**:
```python
# Replace this pattern:
def some_method(self):
    # Legacy transformation
    widget_x, widget_y = self.transform_point_to_widget(data_x, data_y)
```

**New Pattern**:
```python
def some_method(self):
    # Unified transformation
    transform = UnifiedTransformationService.from_curve_view(self)
    widget_x, widget_y = transform.apply(data_x, data_y)
```

#### Step 2.2: Update Batch Transformations

**Current Pattern**:
```python
# Replace this pattern:
def paint_points(self):
    for point in self.points:
        x, y = self.transform_point_to_widget(point[1], point[2])
        # Draw point at x, y
```

**New Pattern**:
```python
def paint_points(self):
    # Batch transformation for better performance
    transform = UnifiedTransformationService.from_curve_view(self)
    qt_points = UnifiedTransformationService.transform_points_qt(transform, self.points)
    for i, qt_point in enumerate(qt_points):
        # Draw point at qt_point.x(), qt_point.y()
```

#### Step 2.3: Update CurveService Methods

**Target File**: `services/curve_service.py`

**Current Code**:
```python
# Replace existing transformation code in CurveService
@staticmethod
def select_points_in_rect(curve_view: Any, main_window: Any, selection_rect: QRect) -> int:
    # Create a view state from the curve view for transformation
    view_state = ViewState.from_curve_view(curve_view)
    transform = TransformationService.calculate_transform(view_state)

    for i, point in enumerate(curve_view.points):
        _, point_x, point_y = point[:3]
        # Transform point to widget coordinates using pre-calculated transform
        tx, ty = transform.apply(point_x, point_y)
        # ... rest of method
```

**Refactored Code**:
```python
@staticmethod
def select_points_in_rect(curve_view: Any, main_window: Any, selection_rect: QRect) -> int:
    # Use unified transformation service
    transform = UnifiedTransformationService.from_curve_view(curve_view)

    for i, point in enumerate(curve_view.points):
        _, point_x, point_y = point[:3]
        # Transform point to widget coordinates
        tx, ty = UnifiedTransformationService.transform_point(transform, point_x, point_y)
        # ... rest of method
```

### Phase 3: Remove Legacy Files (1 day)

#### Step 3.1: Delete Legacy Files

Remove these files entirely:
```bash
rm transform_fix.py
rm services/transform_stabilizer.py
rm services/transformation_shim.py
rm services/transformation_integration.py
rm services/main_window_unified_patch.py
```

#### Step 3.2: Update Imports in Remaining Files

Search and replace in all files:
```python
# Find and replace:
from services.transformation_service import TransformationService
# With:
from services.unified_transformation_service import UnifiedTransformationService

# Find and replace:
TransformationService.calculate_transform
# With:
UnifiedTransformationService.from_view_state

# Find and replace:
TransformationService.transform_point
# With:
UnifiedTransformationService.transform_point
```

### Phase 4: Update Smoothing Operations (1 day)

#### Step 4.1: Refactor Stable Transformation Context

**Current Code**:
```python
# main_window.py apply_smooth_operation method
def apply_smooth_operation(self):
    # ... existing code ...

    # 2. Create a stable transform for the operation
    stable_transform = TransformationService.create_stable_transform_for_operation(self.curve_view)

    # 3. Track reference points before any changes
    reference_points = TransformStabilizer.track_reference_points(before_data, stable_transform)
```

**Refactored Code**:
```python
def apply_smooth_operation(self):
    # Use the new stable transformation context manager
    with UnifiedTransformationService.stable_transformation_context(self.curve_view) as stable_transform:
        # Get selected indices
        selected_indices = getattr(self.curve_view, 'selected_indices', [])
        selected_point_idx = getattr(self.curve_view, 'selected_point_idx', -1)

        # Show smooth dialog and get modified data
        modified_data = DialogService.show_smooth_dialog(
            parent_widget=self,
            curve_data=self.curve_data,
            selected_indices=selected_indices,
            selected_point_idx=selected_point_idx
        )

        if modified_data is not None:
            # Update curve data - transformation stability is handled by context manager
            self.curve_data = modified_data
            self.curve_view.setPoints(
                self.curve_data,
                self.image_width,
                self.image_height,
                preserve_view=True
            )
            self.add_to_history()
            self.statusBar().showMessage("Smoothing applied successfully", 3000)
```

### Phase 5: Testing and Validation (2 days)

#### Step 5.1: Update Unit Tests

**Create new test file**: `tests/test_unified_transformation_complete.py`

```python
import pytest
from unittest.mock import Mock, MagicMock
from services.unified_transformation_service import UnifiedTransformationService
from services.view_state import ViewState

class TestUnifiedTransformationComplete:
    """Test the completely migrated transformation system."""

    def test_no_legacy_imports(self):
        """Ensure no legacy transformation imports exist."""
        # This test should pass after migration
        import main_window
        import services.curve_service

        # Check that legacy imports don't exist
        assert not hasattr(main_window, 'TransformStabilizer')
        assert not hasattr(services.curve_service, 'TransformationService')

    def test_unified_transformation_in_curve_service(self):
        """Test that CurveService uses unified transformations."""
        from services.curve_service import CurveService

        # Mock curve view
        curve_view = Mock()
        curve_view.width.return_value = 800
        curve_view.height.return_value = 600
        curve_view.zoom_factor = 1.0
        curve_view.offset_x = 0.0
        curve_view.offset_y = 0.0
        curve_view.points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]

        # Mock selection rect
        from PySide6.QtCore import QRect
        selection_rect = QRect(50, 100, 200, 200)

        # This should work without any legacy transformation calls
        result = CurveService.select_points_in_rect(curve_view, Mock(), selection_rect)
        assert isinstance(result, int)

    def test_transformation_cache_management(self):
        """Test that cache management works correctly."""
        # Clear cache
        UnifiedTransformationService.clear_cache()

        # Check cache stats
        stats = UnifiedTransformationService.get_cache_stats()
        assert stats['cache_size'] == 0

        # Create multiple transforms to test cache
        mock_view = Mock()
        mock_view.width.return_value = 800
        mock_view.height.return_value = 600

        for i in range(5):
            mock_view.zoom_factor = 1.0 + i * 0.1
            transform = UnifiedTransformationService.from_curve_view(mock_view)
            assert transform is not None

        # Check cache has entries
        stats = UnifiedTransformationService.get_cache_stats()
        assert stats['cache_size'] > 0
```

#### Step 5.2: Integration Testing

**Test Script**: `validate_transformation_migration.py`

```python
#!/usr/bin/env python3
"""
Validation script for transformation system migration.
Run this after completing the migration to ensure everything works.
"""

import sys
import traceback
from unittest.mock import Mock

def test_no_legacy_references():
    """Test that no legacy transformation references exist."""
    print("Testing for legacy transformation references...")

    # Try to import legacy modules - these should fail
    legacy_modules = [
        'transform_fix',
        'services.transform_stabilizer',
        'services.transformation_shim',
        'services.transformation_integration'
    ]

    for module_name in legacy_modules:
        try:
            __import__(module_name)
            print(f"❌ FAILED: Legacy module {module_name} still exists!")
            return False
        except ImportError:
            print(f"✅ OK: Legacy module {module_name} not found (expected)")

    return True

def test_unified_transformation_functionality():
    """Test basic unified transformation functionality."""
    print("Testing unified transformation functionality...")

    try:
        from services.unified_transformation_service import UnifiedTransformationService
        from services.view_state import ViewState

        # Create a mock curve view
        mock_curve_view = Mock()
        mock_curve_view.width.return_value = 800
        mock_curve_view.height.return_value = 600
        mock_curve_view.zoom_factor = 1.0
        mock_curve_view.offset_x = 0.0
        mock_curve_view.offset_y = 0.0
        mock_curve_view.flip_y_axis = True
        mock_curve_view.scale_to_image = True
        mock_curve_view.image_width = 1920
        mock_curve_view.image_height = 1080

        # Test transform creation
        transform = UnifiedTransformationService.from_curve_view(mock_curve_view)
        assert transform is not None
        print("✅ OK: Transform creation works")

        # Test point transformation
        result = UnifiedTransformationService.transform_point(transform, 100.0, 200.0)
        assert len(result) == 2
        print("✅ OK: Point transformation works")

        # Test batch transformation
        points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        results = UnifiedTransformationService.transform_points(transform, points)
        assert len(results) == 2
        print("✅ OK: Batch transformation works")

        # Test stable transformation context
        with UnifiedTransformationService.stable_transformation_context(mock_curve_view) as stable_transform:
            assert stable_transform is not None
        print("✅ OK: Stable transformation context works")

        return True

    except Exception as e:
        print(f"❌ FAILED: Unified transformation test failed: {e}")
        traceback.print_exc()
        return False

def test_main_window_initialization():
    """Test that main window initializes without legacy references."""
    print("Testing main window initialization...")

    try:
        # This is a basic import test
        import main_window

        # Check that legacy imports are not present
        source_lines = open('main_window.py', 'r').readlines()
        legacy_imports = [
            'from transform_fix import TransformStabilizer',
            'from services.transform_stabilizer import TransformStabilizer',
            'from services.transformation_shim import'
        ]

        for line in source_lines:
            for legacy_import in legacy_imports:
                if legacy_import in line and not line.strip().startswith('#'):
                    print(f"❌ FAILED: Found legacy import: {line.strip()}")
                    return False

        print("✅ OK: No legacy imports found in main_window.py")
        return True

    except Exception as e:
        print(f"❌ FAILED: Main window test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("TRANSFORMATION SYSTEM MIGRATION VALIDATION")
    print("=" * 60)

    tests = [
        test_no_legacy_references,
        test_unified_transformation_functionality,
        test_main_window_initialization
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: Test {test.__name__} crashed: {e}")
            failed += 1
        print("-" * 40)

    print(f"\nRESULTS: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 ALL TESTS PASSED! Migration completed successfully.")
        return 0
    else:
        print(f"💥 {failed} TESTS FAILED! Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Implementation Timeline

### Week 1
- **Day 1-2**: Phase 1 - Remove legacy dependencies
- **Day 3-5**: Phase 2 - Update transformation calls

### Week 2
- **Day 1**: Phase 3 - Remove legacy files
- **Day 2**: Phase 4 - Update smoothing operations
- **Day 3-4**: Phase 5 - Testing and validation
- **Day 5**: Documentation and cleanup

## Risk Mitigation

### Backup Strategy
```bash
# Before starting, create a backup branch
git checkout -b backup-before-transformation-migration
git push origin backup-before-transformation-migration

# Create feature branch for migration
git checkout -b refactor/complete-transformation-migration
```

### Incremental Testing
1. After each phase, run the validation script
2. Test with a small curve dataset
3. Verify UI responsiveness
4. Check transformation accuracy

### Rollback Plan
If issues arise:
1. Identify the problematic change
2. Revert to the last working commit
3. Apply fixes incrementally
4. Re-run validation

## Success Criteria

✅ **Migration Complete When**:
1. No legacy transformation files exist
2. All transformation calls use `UnifiedTransformationService`
3. No runtime errors during normal operations
4. All tests pass
5. UI remains responsive
6. Transformation accuracy is maintained

## Post-Migration Benefits

1. **Simplified Architecture**: Single transformation system
2. **Better Performance**: Optimized caching and batch operations
3. **Improved Maintainability**: No more dual-system complexity
4. **Enhanced Type Safety**: Better typing support
5. **Reduced Bug Risk**: Elimination of transformation system conflicts

---

**Estimated Total Effort**: 8-10 business days
**Risk Level**: Medium (well-tested migration path)
**Impact**: High (resolves critical architectural issue)

This migration represents the most important refactoring task for the CurveEditor project and should be prioritized above all other improvements.
