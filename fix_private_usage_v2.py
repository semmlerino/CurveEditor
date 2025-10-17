#!/usr/bin/env python3
"""Fix all reportPrivateUsage warnings by adding type ignore comments."""

import re
import subprocess
from collections import defaultdict
from pathlib import Path


def main():
    # Run basedpyright and capture output
    result = subprocess.run(
        ['./bpr'],
        capture_output=True,
        text=True,
        cwd='/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor'
    )

    # Parse errors from combined output
    output = result.stdout + result.stderr

    errors = []
    pattern = r'^\s*(.+?):(\d+):(\d+)\s+-\s+warning:'

    for line in output.split('\n'):
        if 'reportPrivateUsage' in line:
            match = re.match(pattern, line)
            if match:
                errors.append({
                    'file': match.group(1),
                    'line': int(match.group(2)),
                })

    if not errors:
        print("No reportPrivateUsage errors found!")
        return

    print(f"Found {len(errors)} reportPrivateUsage errors")

    # Group by file and line
    by_file = defaultdict(set)
    for error in errors:
        by_file[error['file']].add(error['line'])

    print(f"Affecting {len(by_file)} files\n")

    # Fix each file
    total_fixed = 0
    for filepath in sorted(by_file.keys()):
        lines_to_fix = by_file[filepath]
        path = Path(filepath)

        if not path.exists():
            print(f"Warning: {filepath} does not exist")
            continue

        with open(path, 'r') as f:
            lines = f.readlines()

        fixed_count = 0
        for line_num in sorted(lines_to_fix, reverse=True):
            idx = line_num - 1
            if idx >= len(lines):
                continue

            line = lines[idx]

            # Skip if already has ignore
            if 'pyright: ignore[reportPrivateUsage]' in line:
                continue

            # Add ignore at end of line
            lines[idx] = line.rstrip() + '  # pyright: ignore[reportPrivateUsage]\n'
            fixed_count += 1

        if fixed_count > 0:
            with open(path, 'w') as f:
                f.writelines(lines)
            print(f"{path.name}: Fixed {fixed_count} warnings")
            total_fixed += fixed_count

    print(f"\nTotal fixed: {total_fixed} warnings")


if __name__ == '__main__':
    main()
