#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Batch import fixer for the CurveEditor project.
Fixes import organization in all Python files that need it.
"""

import subprocess
import sys
from pathlib import Path
from typing import List

# Files we've already fixed
FIXED_FILES = {
    # First session fixes
    'main_window.py',
    'curve_view.py',
    'ui_components.py',
    'menu_bar.py',
    'services/file_service.py',
    'services/curve_service.py',
    'signal_registry.py',
    # Second session fixes - component files
    'visualization_components.py',
    'smoothing_components.py',
    'point_edit_components.py',
    'status_components.py',
    'timeline_components.py',
    'toolbar_components.py',
    # Second session fixes - service files
    'services/visualization_service.py',
    'services/analysis_service.py',
    'services/dialog_service.py',
    'services/history_service.py',
    'services/image_service.py',
    # Second session fixes - other files
    'dialogs.py',
    'error_handling.py',
    # Third session fixes
    'services/settings_service.py',
    'batch_edit.py',
    'keyboard_shortcuts.py',
    'enhanced_curve_view.py',
    'logging_config.py',
    'config.py',
    'track_quality.py',
    'quick_filter_presets.py',
    'services/protocols.py'
}

# Files to skip (tools and scripts)
SKIP_FILES = {
    'analyze_imports.py',
    'fix_imports.py',
    'fix_all_imports.py',
    'test_runner.py',
    'debug_main.py'
}

def needs_fixing(file_path: Path) -> bool:
    """Check if a file needs import fixing."""
    # Skip if already fixed
    rel_path = str(file_path.relative_to(Path.cwd())).replace('\\', '/')
    if rel_path in FIXED_FILES:
        return False

    # Skip certain files
    if file_path.name in SKIP_FILES:
        return False

    # Skip test files and migrations
    if 'test' in file_path.name or 'migrate' in file_path.name:
        return False

    return True

def fix_imports_in_files(files: List[Path]):
    """Fix imports in the given files."""
    for file_path in files:
        print(f"Fixing imports in: {file_path}")
        result = subprocess.run(
            [sys.executable, 'fix_imports.py', str(file_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  ✓ {result.stdout.strip()}")
        else:
            print(f"  ✗ Error: {result.stderr.strip()}")

def main():
    """Main entry point."""
    project_root = Path.cwd()

    # Find all Python files
    py_files = list(project_root.rglob('*.py'))

    # Filter files that need fixing
    files_to_fix = [f for f in py_files if needs_fixing(f)]

    print(f"Found {len(files_to_fix)} files that need import fixing:")
    for f in sorted(files_to_fix):
        print(f"  - {f.relative_to(project_root)}")

    if not files_to_fix:
        print("No files need fixing!")
        return

    response = input("\nProceed with fixing? (y/N): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    fix_imports_in_files(files_to_fix)
    print("\nDone!")

if __name__ == '__main__':
    main()
