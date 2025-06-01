#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix direct logging.getLogger() calls to use LoggingService."""

import os
import re
from typing import List, Tuple

# List of files that need to be fixed
FILES_TO_FIX = [
    "signal_connectors/shortcut_signal_connector.py",
    "ui_components.py",
    "timeline_components.py",
    "utils.py",
    "csv_export.py",
    "signal_registry.py",
    "main_window_delegator.py",
    "signal_connectors/view_signal_connector.py",
    "signal_connectors/edit_signal_connector.py",
    "config.py",
    "main_window_smoothing.py",
    "main_window_operations.py",
    "application_state.py",
    "error_handling.py",
    "enhanced_curve_view.py"
]


def fix_logging_in_file(filepath: str) -> bool:
    """Fix logging.getLogger() calls in a single file.

    Args:
        filepath: Path to the file to fix

    Returns:
        True if file was modified, False otherwise
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Check if file already imports LoggingService
    if 'from services.logging_service import LoggingService' in content:
        print(f"✓ {filepath} already uses LoggingService")
        return False

    # Pattern to find logger = logging.getLogger(__name__) or similar
    logger_pattern = r'logger\s*=\s*logging\.getLogger\((.*?)\)'
    matches = list(re.finditer(logger_pattern, content))

    if not matches:
        print(f"- {filepath} has no logging.getLogger() calls")
        return False

    # Extract logger name from getLogger call
    logger_arg = matches[0].group(1).strip()

    # Determine the module name for LoggingService
    if logger_arg == '__name__':
        # Use the filename without extension as module name
        module_name = os.path.splitext(os.path.basename(filepath))[0]
    else:
        # Use the provided name, stripping quotes
        module_name = logger_arg.strip('"\'')

    # Replace import logging with LoggingService import
    if 'import logging' in content:
        # Find the import section
        import_section_end = 0
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(('import', 'from', '#', '"""', "'''")) and i > 10:
                import_section_end = i
                break

        # Check if we need to add LoggingService import
        new_lines = []
        added_import = False
        removed_logging = False

        for i, line in enumerate(lines):
            if line.strip() == 'import logging' and not removed_logging:
                # Replace with LoggingService import
                new_lines.append('from services.logging_service import LoggingService')
                removed_logging = True
                added_import = True
            elif line.startswith('import logging') and not removed_logging:
                # Handle cases like "import logging, os"
                imports = [imp.strip() for imp in line.replace('import', '').split(',')]
                other_imports = [imp for imp in imports if imp != 'logging']
                if other_imports:
                    new_lines.append(f"import {', '.join(other_imports)}")
                new_lines.append('from services.logging_service import LoggingService')
                removed_logging = True
                added_import = True
            else:
                new_lines.append(line)

        content = '\n'.join(new_lines)

    # Replace logger = logging.getLogger(...) with LoggingService.get_logger(...)
    content = re.sub(
        logger_pattern,
        f'logger = LoggingService.get_logger("{module_name}")',
        content
    )

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed {filepath} - using LoggingService.get_logger('{module_name}')")
        return True

    return False


def main():
    """Fix all files that use direct logging.getLogger() calls."""
    print("Fixing direct logging.getLogger() calls...\n")

    fixed_count = 0

    for file_path in FILES_TO_FIX:
        full_path = os.path.join("/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor", file_path)
        if os.path.exists(full_path):
            if fix_logging_in_file(full_path):
                fixed_count += 1
        else:
            print(f"✗ {file_path} not found")

    print(f"\nFixed {fixed_count} files.")


if __name__ == "__main__":
    main()
