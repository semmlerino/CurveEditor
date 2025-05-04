# Changelog

## [Unreleased]

### Added
- Implemented centralized logging system via new `LoggingService` to replace debug print statements
- Created `logging_config.py` with support for JSON configuration and module-specific log levels
- Added comprehensive logging guide in `docs/logging_guide.md`
- Added implementation progress tracking document in `docs/implementation_progress.md`
- Integrated logging system with main application startup in `main.py`

### Fixed
- Fixed TypeError: safe_operation() got an unexpected keyword argument 'record_history' by updating the `safe_operation` decorator in `error_handling.py` to support the `record_history` parameter.
- `record_history` parameter now controls whether operations automatically add state changes to the undo/redo history.
- Added test script to verify the fix works correctly.
- Fixed AttributeError: 'CurveService' has no attribute 'set_point_radius' by updating the `EnhancedCurveView.set_point_radius` method to correctly call `CurveService.set_point_size` instead.
- Fixed ModuleNotFoundError issues by updating imports to use service modules instead of legacy operations files:
  - Updated curve_view.py to use CenteringZoomService
  - Updated main_window.py to use proper service imports
  - Fixed import in services/dialog_service.py to use AnalysisService
  - Resolved circular dependency in services/analysis_service.py by creating an internal CurveDataProcessor class
  - Fixed create_processor method signature in analysis_service.py that was still referencing legacy class
  - Updated multiple visualization_operations imports in enhanced_curve_view.py

### Changed
- Enhanced `safe_operation` decorator to automatically add operations to history when successful (only when `record_history=True`).
- Completed code consolidation by renaming all legacy operations files to .deprecated and ensuring proper import patterns throughout the codebase.
- Updated documentation to reflect current architecture and code consolidation status.
- Replaced debug print statements in key files with proper logging:
  - Converted debug prints in `curve_view.py` to use LoggingService
  - Converted debug prints in `main_window.py` to use LoggingService
