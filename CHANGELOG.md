# Changelog

## [Unreleased]

### Added
- Implemented centralized logging system via new `LoggingService` to replace debug print statements
- Created `logging_config.py` with support for JSON configuration and module-specific log levels
- Added comprehensive logging guide in `docs/logging_guide.md`
- Added implementation progress tracking document in `docs/implementation_progress.md`
- Integrated logging system with main application startup in `main.py`
- Created protocol system in `services/protocols.py` for standardized interface definitions
- Added comprehensive protocol system documentation in `docs/protocol_system.md`
- Implemented type aliases for common data structures in the protocol system
- Extended protocol system to cover all service interfaces:
  - Added FileServiceProtocol for file operations
  - Added ImageSequenceProtocol and ImageServiceProtocol for image handling
  - Added HistoryStateProtocol and HistoryContainerProtocol for history management
  - Added DialogServiceProtocol for dialog operations
- Created new transformation system to ensure consistent coordinate transformations:
  - Added `TransformationService` for centralized transform calculation and application
  - Added `Transform` class to encapsulate coordinate transformations
  - Added `ViewState` class to capture all view parameters
  - Added `TransformStabilizer` module for maintaining view stability during operations
  - Added documentation in `docs/curve_shift_fix.md` explaining the transformation system
  - Added diagnostic capabilities for detecting and fixing curve shifting issues
  - Implemented transform caching for performance optimization

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
- Fixed circular dependency between TransformationService and CenteringZoomService
- Improved direct property access using protocol properties instead of getattr calls
- Fixed curve shifting issue that occurred during smoothing operations:
  - Refactored `apply_smooth_operation` method to use stable transformation system
  - Updated CurveView's paintEvent to use consistent transformation logic
  - Fixed background image rendering to maintain proper alignment during operations
  - Added diagnostic logging to help identify and resolve transformation inconsistencies
  - Implemented point position verification to detect unexpected shifts
  - Fixed type compatibility issues between QPointF and tuple return types in transform methods
  - Added robust error handling for transformation functions across multiple view classes
  - Fixed "floating curve" issue by ensuring both curve and background image use identical transformation parameters

### Changed
- Enhanced `safe_operation` decorator to automatically add operations to history when successful (only when `record_history=True`).
- Completed code consolidation by renaming all legacy operations files to .deprecated and ensuring proper import patterns throughout the codebase.
- Updated documentation to reflect current architecture and code consolidation status.
- Replaced debug print statements in key files with proper logging:
  - Converted debug prints in `curve_view.py` to use LoggingService
  - Converted debug prints in `main_window.py` to use LoggingService
- Updated TransformationService to use protocol-based type hints
- Updated VisualizationService to use protocol-based type hints and more consistent method signatures
- Standardized service method parameter types using the new protocol system
- Updated all remaining services to use protocol-based interfaces:
  - Updated FileService to use MainWindowProtocol
  - Updated ImageService to use CurveViewProtocol, ImageSequenceProtocol, and MainWindowProtocol
  - Updated HistoryService to use HistoryContainerProtocol
  - Updated DialogService to use MainWindowProtocol and PointsList types
- Increased protocol coverage from 30% to 80% across the codebase
