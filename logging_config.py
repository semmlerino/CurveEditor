#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging configuration utility for CurveEditor.

This module provides tools to configure logging levels for different
parts of the application through a configuration file or command-line arguments.
"""

import argparse
import json
import logging
import os
from typing import Dict, Any, Optional

from services.logging_service import LoggingService

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.expanduser("~"), ".curve_editor", "logging_config.json")

# Default logging levels per module
DEFAULT_CONFIG = {
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


def get_level(level_name: str) -> int:
    """Convert a level name to logging level value."""
    # We use try/except instead of isinstance check since we know level_name is typed as str
    try:
        return getattr(logging, level_name.upper(), logging.INFO)
    except (AttributeError, TypeError):
        return logging.INFO


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load logging configuration from file or use defaults."""
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading logging config: {e}")
        return DEFAULT_CONFIG



def apply_config(config: Dict[str, Any]) -> None:
    """Apply the logging configuration to the application.

    This function is deprecated. Configuration is now applied directly
    in main.py through LoggingService.set_module_level().

    Args:
        config: Configuration dictionary

    Note:
        This function is kept for backward compatibility but does nothing.
        Remove calls to this function and apply configuration directly.
    """
    pass  # Configuration is now handled in main.py


def update_config(module: str, level: str, config_path: Optional[str] = None) -> None:
    """Update a specific module's logging level in the configuration."""
    config = load_config(config_path)

    # Handle nested paths like "services.curve_service"
    if "." in module:
        parts = module.split(".")
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = level
    else:
        config[module] = level

    # Save updated config
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Updated logging level for {module} to {level}")


def main():
    """Command-line interface for configuring logging."""
    parser = argparse.ArgumentParser(description="Configure CurveEditor logging")
    parser.add_argument("--config", help="Path to logging configuration file")
    parser.add_argument("--list", action="store_true", help="List current log levels")
    parser.add_argument("--set", nargs=2, metavar=("MODULE", "LEVEL"),
                       help="Set log level for a module")
    parser.add_argument("--reset", action="store_true", help="Reset to default configuration")

    args = parser.parse_args()

    config_path = args.config or DEFAULT_CONFIG_PATH

    if args.reset:
        with open(config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"Reset logging configuration to defaults at {config_path}")
        return

    if args.list:
        config = load_config(config_path)
        print("Current logging configuration:")
        print(json.dumps(config, indent=2))
        return

    if args.set:
        module, level = args.set
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level.upper() not in valid_levels:
            print(f"Invalid log level. Use one of: {', '.join(valid_levels)}")
            return

        update_config(module, level.upper(), config_path)
        return

    # If no options provided, just load and apply the config
    config = load_config(config_path)
    print("Current logging configuration:")
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
