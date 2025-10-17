#!/usr/bin/env python3
"""Automatically fix reportPrivateUsage warnings by adding type ignore comments."""

import re
import subprocess
from collections import defaultdict
from pathlib import Path


def parse_basedpyright_errors():
    """Parse basedpyright output for reportPrivateUsage errors."""
    result = subprocess.run(['./bpr'], capture_output=True, text=True, cwd='/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

    errors = []
    # Pattern: /path/file.py:123:45 - warning: "_member" is protected...
    # Note: Lines may have leading whitespace
    pattern = r'^\s*(.+):(\d+):(\d+) - warning: "([^"]+)" is (?:protected|private)'

    for line in result.stderr.split('\n'):
        if 'reportPrivateUsage' not in line:
            continue

        match = re.match(pattern, line)
        if match:
            errors.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'col': int(match.group(3)),
                'member': match.group(4)
            })

    return errors


def fix_file(filepath, file_errors):
    """Add pyright ignore comments to a file for all errors."""
    path = Path(filepath)

    if not path.exists():
        print(f"Warning: {filepath} does not exist")
        return 0

    with open(path, 'r') as f:
        lines = f.readlines()

    # Sort errors by line number (reverse) to modify from bottom up
    # This prevents line number shifts as we modify
    file_errors.sort(key=lambda e: e['line'], reverse=True)

    fixed_count = 0
    for error in file_errors:
        line_idx = error['line'] - 1

        if line_idx >= len(lines):
            print(f"Warning: Line {error['line']} out of range in {filepath}")
            continue

        line = lines[line_idx]

        # Skip if already has pyright ignore
        if 'pyright: ignore[reportPrivateUsage]' in line:
            continue

        # Add ignore comment at end of line
        stripped = line.rstrip()
        lines[line_idx] = f"{stripped}  # pyright: ignore[reportPrivateUsage]\n"
        fixed_count += 1

    # Write back modified file
    with open(path, 'w') as f:
        f.writelines(lines)

    return fixed_count


def main():
    """Main execution."""
    print("Parsing basedpyright errors...")
    errors = parse_basedpyright_errors()

    if not errors:
        print("No reportPrivateUsage errors found!")
        return

    print(f"Found {len(errors)} reportPrivateUsage errors")

    # Group by file
    by_file = defaultdict(list)
    for error in errors:
        by_file[error['file']].append(error)

    print(f"Affecting {len(by_file)} files")

    # Fix each file
    total_fixed = 0
    for filepath, file_errors in sorted(by_file.items()):
        fixed = fix_file(filepath, file_errors)
        if fixed > 0:
            print(f"  {Path(filepath).name}: Fixed {fixed} warnings")
            total_fixed += fixed

    print(f"\nTotal fixed: {total_fixed} warnings")

    # Run basedpyright again to verify
    print("\nVerifying fixes...")
    result = subprocess.run(['./bpr', '2>&1', '|', 'grep', '-c', 'reportPrivateUsage'],
                          shell=True, capture_output=True, text=True,
                          cwd='/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor')

    remaining = result.stdout.strip()
    print(f"Remaining reportPrivateUsage warnings: {remaining}")


if __name__ == '__main__':
    main()
