# CurveEditor Logging System Guide

This document provides information about the logging system in CurveEditor, including how to configure log levels and use the system for debugging.

## Overview

CurveEditor uses a structured logging system that allows:
- Granular control of log levels for different parts of the application
- Log output to both console and file
- Easy configuration through a JSON configuration file
- Command-line tools for adjusting log levels

## Log Locations

By default, logs are stored in:
- `~/.curve_editor/logs/curve_editor.log`

Console output is also enabled by default, showing the same log messages that are written to the file.

## Log Levels

The logging system supports the standard Python logging levels:

| Level    | Value | Description                                     |
|----------|-------|-------------------------------------------------|
| DEBUG    | 10    | Detailed information for diagnostic purposes    |
| INFO     | 20    | General information about program execution     |
| WARNING  | 30    | Potential issues that don't prevent execution   |
| ERROR    | 40    | Errors that prevent a function from completing  |
| CRITICAL | 50    | Critical errors that may cause program failure  |

## Configuration

### Configuration File

The logging configuration is stored in a JSON file at:
```
~/.curve_editor/logs/logging_config.json
```

This file allows you to set different log levels for different modules. The default configuration looks like this:

```json
{
  "global": "INFO",
  "curve_view": "INFO",
  "main_window": "INFO",
  "services": {
    "curve_service": "INFO",
    "image_service": "INFO",
    "file_service": "INFO",
    "dialog_service": "INFO",
    "analysis_service": "INFO",
    "visualization_service": "INFO",
    "centering_zoom_service": "INFO",
    "settings_service": "INFO",
    "history_service": "INFO",
    "input_service": "INFO"
  }
}
```

### Changing Log Levels

#### Using the Configuration Tool

The CurveEditor provides a command-line tool for managing log levels:

1. **View Current Configuration**:
   ```
   python logging_config.py --list
   ```

2. **Set Log Level for a Module**:
   ```
   python logging_config.py --set curve_view DEBUG
   ```

3. **Set Log Level for a Service**:
   ```
   python logging_config.py --set services.curve_service DEBUG
   ```

4. **Reset to Default Configuration**:
   ```
   python logging_config.py --reset
   ```

#### Environment Variable

You can also set the global log level using an environment variable:

```
CURVE_EDITOR_LOG_LEVEL=DEBUG python main.py
```

This will override the global level in the configuration file for the current session.

## Debugging with Logs

### Enabling Debug Logs

For detailed debugging information, set the log level to DEBUG:

```
python logging_config.py --set global DEBUG
```

This will enable all debug logs. You can also enable debug logs for specific components:

```
python logging_config.py --set curve_view DEBUG
python logging_config.py --set services.curve_service DEBUG
```

### Common Debug Scenarios

1. **Tracking View Operations**:
   ```
   python logging_config.py --set curve_view DEBUG
   ```
   This will show detailed information about view transformations, zooming, and panning.

2. **Debugging Service Operations**:
   ```
   python logging_config.py --set services.curve_service DEBUG
   python logging_config.py --set services.analysis_service DEBUG
   ```
   This will show detailed information about curve operations and analysis.

3. **Tracking Main Window Activities**:
   ```
   python logging_config.py --set main_window DEBUG
   ```
   This will show UI operations and event handling in the main window.

## Log Format

The log format for console output is:
```
[LEVEL] module_name: message
```

The log format for file output is:
```
timestamp [LEVEL] module_name: message
```

## For Developers

When adding new code or modifying existing code, use the logging service instead of print statements:

```python
from services.logging_service import LoggingService

# Get a logger for your module
logger = LoggingService.get_logger("your_module_name")

# Use the logger instead of print statements
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Something might be wrong")
logger.error("Something is definitely wrong")
logger.critical("Something catastrophic happened")
```

## Troubleshooting

### Logs Not Appearing

If logs are not appearing:

1. Check that the log directory exists:
   ```
   ls -la ~/.curve_editor/logs/
   ```

2. Verify the current log level:
   ```
   python logging_config.py --list
   ```

3. Try setting a lower log level:
   ```
   python logging_config.py --set global DEBUG
   ```

### Too Many Logs

If there are too many logs making it difficult to find relevant information:

1. Increase the global log level:
   ```
   python logging_config.py --set global WARNING
   ```

2. Only enable DEBUG for specific modules you're interested in:
   ```
   python logging_config.py --set global INFO
   python logging_config.py --set curve_view DEBUG
   ```

## Conclusion

The logging system provides a flexible way to get insights into the CurveEditor application's operation. By adjusting log levels, you can control the amount of information you receive, making it easier to diagnose issues or understand the application's behavior.
