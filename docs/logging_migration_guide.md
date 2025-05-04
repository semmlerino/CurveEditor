# Logging Migration Guide

This document provides guidelines for migrating from debug print statements to the centralized logging system in the CurveEditor application.

## Overview

As part of the ongoing architectural improvements, we're replacing all debug print statements with proper logging through the `LoggingService`. This allows for:

1. Configurable log levels (DEBUG, INFO, WARNING, ERROR)
2. Module-specific logging configuration
3. Consistent log formatting
4. Optional file-based logging
5. Better integration with testing and debugging tools

## Migration Process

### Step 1: Import LoggingService and Configure Logger

At the top of each module, add:

```python
from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("module_name")
```

Replace `module_name` with a descriptive name for your module (typically the filename without extension).

### Step 2: Replace Print Statements

Replace print statements with appropriate logging calls:

| Original | Replacement |
|----------|-------------|
| `print("Debug info")` | `logger.debug("Debug info")` |
| `print(f"Status: {status}")` | `logger.info(f"Status: {status}")` |
| `print("Warning: file not found")` | `logger.warning("Warning: file not found")` |
| `print(f"Error: {e}")` | `logger.error(f"Error: {e}")` |

Choose the appropriate log level based on the severity and purpose of the message:

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: An indication that something unexpected happened, or may happen in the near future
- **ERROR**: Due to a more serious problem, the software has not been able to perform a function

### Step 3: Update Tests

If you have tests that verify output by patching `builtins.print`, update them to verify logger calls instead:

```python
# Before
with patch('builtins.print') as mock_print:
    function_with_prints()
    mock_print.assert_called_once_with("Expected message")

# After
with patch.object(logger, 'warning') as mock_logger:
    function_with_logging()
    mock_logger.assert_called_once_with("Expected message")
```

Be sure to import the logger from the module being tested:

```python
from module_being_tested import logger
```

## Example: VisualizationService Migration

The `VisualizationService` has been updated to use the new logging system:

```python
# Before
def update_timeline_for_image(index, curve_view, image_filenames):
    try:
        if not image_filenames:
            print("update_timeline_for_image: No image filenames available")
            return
    # ...

# After
def update_timeline_for_image(index, curve_view, image_filenames):
    try:
        if not image_filenames:
            logger.warning("No image filenames available")
            return
    # ...
```

The tests have also been updated to verify logger calls instead of print statements:

```python
# Before
def test_update_timeline_for_image_empty_list(self):
    with patch('builtins.print') as mock_print:
        VisualizationService.update_timeline_for_image(0, self.mock_curve_view, [])
        mock_print.assert_called_once_with("update_timeline_for_image: No image filenames available")

# After
def test_update_timeline_for_image_empty_list(self):
    with patch.object(logger, 'warning') as mock_logger:
        VisualizationService.update_timeline_for_image(0, self.mock_curve_view, [])
        mock_logger.assert_called_once_with("No image filenames available")
```

## Best Practices

1. **Use descriptive messages**: Include context in log messages to make debugging easier
2. **Consider log verbosity**: Use DEBUG for detailed information, INFO for general progress, etc.
3. **Don't overlog**: Avoid logging in tight loops or high-performance code paths
4. **Include context**: Add relevant variable values to help with debugging
5. **Be consistent**: Use the same log levels for similar types of events
6. **Update tests**: Ensure tests are updated to verify logging calls

## Next Steps

The following components still need logging migration:

1. Remaining service implementations
2. Analysis operations and dialogs
3. UI components

Refer to the [Implementation Progress](implementation_progress.md) document for the current status of the migration.
