#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix all direct logging.getLogger() calls to use LoggingService."""

import os
import re

# Project root
PROJECT_ROOT = "/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor"

# List of files that need to be fixed (from fix_logging_calls.py)
FILES_TO_FIX = [
    "signal_connectors/shortcut_signal_connector.py",
    "ui_components.py",
    "timeline_components.py",
    "csv_export.py",
    "signal_registry.py",
    "main_window_delegator.py",
    "signal_connectors/view_signal_connector.py",
    "signal_connectors/edit_signal_connector.py",
    "main_window_smoothing.py",
    "main_window_operations.py",
    "application_state.py",
    "error_handling.py",
    "enhanced_curve_view.py"
]

def fix_file(filepath):
    """Fix logging in a single file."""
    full_path = os.path.join(PROJECT_ROOT, filepath)

    if not os.path.exists(full_path):
        print(f"✗ {filepath} not found")
        return False

    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already fixed
    if 'from services.logging_service import LoggingService' in content:
        print(f"✓ {filepath} already uses LoggingService")
        return False

    # Check if file uses logging
    if 'logger = logging.getLogger' not in content:
        print(f"- {filepath} doesn't use logging")
        return False

    # Replace import logging with LoggingService import
    content = re.sub(
        r'^import logging$',
        'from services.logging_service import LoggingService',
        content,
        flags=re.MULTILINE
    )

    # Handle "import logging, other" style imports
    content = re.sub(
        r'^import logging,\s*(.+)$',
        r'import \1\nfrom services.logging_service import LoggingService',
        content,
        flags=re.MULTILINE
    )

    # Get module name from filename
    module_name = os.path.splitext(os.path.basename(filepath))[0]

    # Replace logger = logging.getLogger(__name__)
    content = re.sub(
        r'logger\s*=\s*logging\.getLogger\(__name__\)',
        f'logger = LoggingService.get_logger("{module_name}")',
        content
    )

    # Replace logger = logging.getLogger("name")
    content = re.sub(
        r'logger\s*=\s*logging\.getLogger\("([^"]+)"\)',
        r'logger = LoggingService.get_logger("\1")',
        content
    )

    # Write the fixed content
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Fixed {filepath}")
    return True

def main():
    """Fix all files."""
    print("Fixing all logging.getLogger() calls to use LoggingService...\n")

    fixed_count = 0
    for filepath in FILES_TO_FIX:
        if fix_file(filepath):
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")
    print("\nNOTE: Remember to test the application to ensure logging now writes to files correctly!")

if __name__ == "__main__":
    main()
