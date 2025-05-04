# Debug Cleanup Plan

This document outlines a plan for cleaning up debug statements and implementing proper logging in the CurveEditor application.

## Current Issues

1. **Excessive Debug Printing**: Many files (especially `curve_view.py`) contain excessive print statements for debugging purposes.

2. **Inconsistent Debug Format**: Debug messages use inconsistent formats and prefixes.

3. **No Central Logging**: The application lacks a proper logging system for controlling verbosity and output destinations.

## Cleanup Strategy

### Phase 1: Audit and Analysis

1. **Audit all Debug Statements**:
   - Identify all print statements used for debugging
   - Categorize by importance (critical, informational, verbose)
   - Determine which can be removed entirely vs. converted to logging

2. **Analyze Performance Impact**:
   - Identify areas where debug output might affect performance
   - Prioritize cleanup in performance-sensitive areas (rendering, real-time operations)

### Phase 2: Implement Logging System

1. **Create Logging Module**:
   ```python
   # logging_service.py
   import logging
   import os

   class LoggingService:
       """Central logging service for the CurveEditor application."""

       @staticmethod
       def setup_logging(level=logging.INFO, log_file=None):
           """Set up the logging system."""
           # Configure root logger
           logger = logging.getLogger('curve_editor')
           logger.setLevel(level)

           # Console handler
           console_handler = logging.StreamHandler()
           console_handler.setLevel(level)
           console_formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
           console_handler.setFormatter(console_formatter)
           logger.addHandler(console_handler)

           # File handler (optional)
           if log_file:
               file_handler = logging.FileHandler(log_file)
               file_handler.setLevel(level)
               file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
               file_handler.setFormatter(file_formatter)
               logger.addHandler(file_handler)

           return logger

       @staticmethod
       def get_logger(name):
           """Get a logger with the specified name."""
           return logging.getLogger(f'curve_editor.{name}')
   ```

2. **Initialize Logging in Main Application Entry Point**:
   ```python
   from logging_service import LoggingService

   # In main.py or similar entry point
   def main():
       # Set up logging
       LoggingService.setup_logging(
           level=logging.INFO,  # Can be made configurable
           log_file="curve_editor.log"  # Optional
       )
       # Continue with application initialization
   ```

### Phase 3: Replace Debug Statements

1. **Replace Debug Prints in `curve_view.py`**:
   - Replace all print statements with appropriate logging calls
   - Use proper log levels (DEBUG, INFO, WARNING, ERROR)
   - Add context to log messages

2. **Clean up Debug Statements in Service Modules**:
   - Apply the same approach to all service modules
   - Ensure consistent log message formatting

3. **Add Configuration Options**:
   - Allow changing log levels via settings
   - Enable debug logging for development

## Implementation Example for `curve_view.py`

**Before**:
```python
def resetView(self) -> None:
    print(f"[DEBUG CurveView.resetView] End - State AFTER: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
    # Use the already imported CenteringZoomService at the top of the file
    ZoomOperations.reset_view(self)
    print(f"[DEBUG CurveView.resetView] End - State AFTER: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
```

**After**:
```python
def resetView(self) -> None:
    """Reset view to show all points."""
    logger.debug("Resetting view - State before: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
                 self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset)

    ZoomOperations.reset_view(self)

    logger.debug("View reset complete - State after: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
                 self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset)
```

## Testing Considerations

1. **Verify Functionality**: Ensure that the application still functions correctly after removing debug statements.

2. **Performance Testing**: Measure any performance improvements from reducing console output.

3. **Debug Verification**: Confirm that debugging is still effective with the new logging system.

## Timeline and Progress

1. **Audit (1-2 days)**: ✅ Complete
   - Completed full audit of debug statements across the codebase
   - Identified priority areas for conversion to logging system

2. **Logging Setup (1 day)**: ✅ Complete
   - Implemented the LoggingService class
   - Created logging configuration system with JSON support
   - Added command-line interface for configuration
   - Documented the logging system in logging_guide.md

3. **Cleanup (2-3 days)**: ⏳ In Progress (~60% complete)
   - ✅ Converted debug prints in curve_view.py
   - ✅ Converted debug prints in main_window.py
   - ✅ Converted debug prints in enhanced_curve_view.py
   - ⏳ Converting debug prints in service implementations (60% complete)
   - ⏳ Converting debug prints in analysis operations and dialogs

4. **Testing (1-2 days)**: ⏳ Started
   - Implemented basic tests for logging configuration
   - Started verification of logging functionality

5. **Additional Enhancements (2 days)**: 🔜 Planned
   - Add environment variable support for configuration
   - Add log rotation capability
   - Implement module-specific debug mode toggles

## Future Improvements

1. **Log Rotation**: Implement log rotation for long-running instances

2. **Remote Logging**: Add capability to send logs to remote servers

3. **Log Analysis**: Add log analysis tools for debugging and performance monitoring

## Conclusion

Implementing a proper logging system will improve code quality, make debugging more effective, and potentially improve performance by reducing unnecessary console output. This plan provides a structured approach to cleaning up debug statements while ensuring the application remains debuggable.
