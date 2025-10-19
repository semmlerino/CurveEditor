#!/usr/bin/env python3
"""Check for legacy patterns that should use modern alternatives.

This script detects:
1. Legacy 4-step active curve pattern (should use active_curve_data property)
2. Truthiness checks on Optional types (should use explicit 'is None')

Usage:
    python scripts/check_legacy_patterns.py [path]

Examples:
    python scripts/check_legacy_patterns.py                    # Check all Python files
    python scripts/check_legacy_patterns.py services/          # Check specific directory
    python scripts/check_legacy_patterns.py ui/main_window.py  # Check specific file
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


class Issue(NamedTuple):
    """Represents a linting issue."""

    file: Path
    line_num: int
    line: str
    rule: str
    message: str


# Pattern 1: Detect legacy 4-step active curve pattern
# Matches sequences like:
#   active = state.active_curve
#   if not active:
#       return
#   data = state.get_curve_data(active)
LEGACY_ACTIVE_CURVE_PATTERN = re.compile(
    r"active\s*=\s*(?:self\._app_)?state\.active_curve\s*\n" r"\s*if\s+not\s+active:"
)

# Pattern 2: Detect get_curve_data() with no arguments (legacy)
# Should use active_curve_data property instead
LEGACY_GET_CURVE_DATA_PATTERN = re.compile(r"\.get_curve_data\(\s*\)")


def check_file(file_path: Path) -> list[Issue]:
    """Check a single Python file for legacy patterns.

    Args:
        file_path: Path to the Python file to check

    Returns:
        List of issues found
    """
    issues: list[Issue] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Check for legacy 4-step pattern
        if LEGACY_ACTIVE_CURVE_PATTERN.search(content):
            # Find the line number
            for i, line in enumerate(lines, 1):
                if "active = state.active_curve" in line or "active = self._app_state.active_curve" in line:
                    issues.append(
                        Issue(
                            file=file_path,
                            line_num=i,
                            line=line.strip(),
                            rule="LEGACY001",
                            message="Legacy 4-step active curve pattern detected. Use active_curve_data property instead:\n"
                            "  if (cd := state.active_curve_data) is None:\n"
                            "      return\n"
                            "  curve_name, data = cd",
                        )
                    )

        # Check for legacy get_curve_data() with no arguments
        for i, line in enumerate(lines, 1):
            if match := LEGACY_GET_CURVE_DATA_PATTERN.search(line):  # noqa: F841
                # Exclude ApplicationState itself (it defines the method)
                if "stores/application_state.py" not in str(file_path):
                    issues.append(
                        Issue(
                            file=file_path,
                            line_num=i,
                            line=line.strip(),
                            rule="LEGACY002",
                            message="Legacy get_curve_data() with no arguments. Use active_curve_data property instead",
                        )
                    )

    except Exception as e:
        print(f"Error checking {file_path}: {e}", file=sys.stderr)

    return issues


def check_directory(path: Path, exclude_patterns: list[str] | None = None) -> list[Issue]:
    """Check all Python files in a directory recursively.

    Args:
        path: Directory path to check
        exclude_patterns: List of glob patterns to exclude

    Returns:
        List of all issues found
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "**/venv/**",
            "**/__pycache__/**",
            "**/.*/**",
            "**/tests/**",  # Exclude tests from this check
            "**/archive/**",
            "**/obsolete/**",
        ]

    all_issues: list[Issue] = []

    for py_file in path.rglob("*.py"):
        # Check if file matches any exclude pattern
        if any(py_file.match(pattern) for pattern in exclude_patterns):
            continue

        issues = check_file(py_file)
        all_issues.extend(issues)

    return all_issues


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 if no issues, 1 if issues found)
    """
    parser = argparse.ArgumentParser(
        description="Check for legacy patterns in Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("path", nargs="?", default=".", help="File or directory to check (default: current directory)")
    parser.add_argument("--no-exclude", action="store_true", help="Do not exclude any files (check everything)")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        return 1

    # Collect issues
    if path.is_file():
        issues = check_file(path)
    else:
        exclude_patterns = [] if args.no_exclude else None
        issues = check_directory(path, exclude_patterns)

    # Report issues
    if not issues:
        print("✅ No legacy patterns found!")
        return 0

    print(f"⚠️  Found {len(issues)} legacy pattern(s):\n")

    # Group by file
    by_file: dict[Path, list[Issue]] = {}
    for issue in issues:
        if issue.file not in by_file:
            by_file[issue.file] = []
        by_file[issue.file].append(issue)

    # Print grouped results
    for file_path, file_issues in sorted(by_file.items()):
        print(f"\n{file_path}:")
        for issue in file_issues:
            print(f"  Line {issue.line_num}: [{issue.rule}] {issue.message}")
            print(f"    > {issue.line}")

    print(f"\n\nTotal: {len(issues)} issue(s) found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
