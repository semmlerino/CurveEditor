#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging configuration utility for CurveEditor.

This module provides tools to configure logging levels for different
parts of the application through a configuration file or command-line arguments.
"""

import os
import json
import logging
import argparse
from typing import Dict, Any, Optional

from services.logging_service import LoggingService

# Default configuration path
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.expanduser("~"), ".curve_editor", "logging_config.json")

# Default logging levels per module
DEFAULT_CONFIG = {
    "global": "DEBUG",
    "curve_view": "DEBUG",
    "main_window": "DEBUG",
    "services": {
        "curve_service": "DEBUG",
        "image_service": "DEBUG",
        "file_service": "DEBUG",
        "dialog_service": "DEBUG",
        "analysis_service": "DEBUG",
        "visualization_service": "DEBUG",
        "centering_zoom_service": "DEBUG",
        "settings_service": "DEBUG",
        "history_service": "DEBUG",
        "input_service": "DEBUG"
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
    """Apply the logging configuration to the application."""
    # Initialize the root logger with global level
    global_level = get_level(config.get("global", "INFO"))
    logger = LoggingService.setup_logging(level=global_level)

    # Apply specific module levels
    for module, level in config.items():
        if module == "global":
            continue

        if isinstance(level, dict):
            # Handle nested configurations (e.g., services)
            module_dict: Dict[str, Any] = level  # Explicit type annotation
            for submodule_key, sublevel_value in module_dict.items():
                # We can skip type check for submodule_key as it's always a string in dict keys
                # We only need to type-check the sublevel value
                if not isinstance(sublevel_value, str):
                    continue
                    
                # Create logger for submodule
                module_logger = LoggingService.get_logger(f"{module}.{submodule_key}")
                module_logger.setLevel(get_level(sublevel_value))
        else:
            # Handle flat configurations
            module_logger = LoggingService.get_logger(module)
            if isinstance(level, str):
                module_logger.setLevel(get_level(level))

    logger.info(f"Logging configuration applied: global level={logging.getLevelName(global_level)}")


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
