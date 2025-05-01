# Changelog

## [Unreleased]

### Fixed
- Fixed TypeError: safe_operation() got an unexpected keyword argument 'record_history' by updating the `safe_operation` decorator in `error_handling.py` to support the `record_history` parameter.
- `record_history` parameter now controls whether operations automatically add state changes to the undo/redo history.
- Added test script to verify the fix works correctly.
- Fixed AttributeError: 'CurveService' has no attribute 'set_point_radius' by updating the `EnhancedCurveView.set_point_radius` method to correctly call `CurveService.set_point_size` instead.

### Changed
- Enhanced `safe_operation` decorator to automatically add operations to history when successful (only when `record_history=True`).
