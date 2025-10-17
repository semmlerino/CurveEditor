#!/usr/bin/env python3
"""Automated fixer for reportUnused* warnings from basedpyright."""

import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Issue:
    """Represents a single basedpyright warning."""
    file: str
    line: int
    col: int
    type: Literal["reportUnusedCallResult", "reportUnusedVariable", "reportUnusedParameter"]
    message: str
    var_name: str | None = None


def parse_basedpyright_output() -> list[Issue]:
    """Parse basedpyright output to extract unused code issues."""
    result = subprocess.run(
        ["/home/gabrielh/.local/bin/uv", "run", "basedpyright"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
        shell=False
    )

    issues = []
    # Pattern: /path/file.py:123:45 - warning: ... (reportUnused...)
    pattern = r'^\s*(/[^:]+):(\d+):(\d+) - warning: (.+) \((reportUnused(?:CallResult|Variable|Parameter))\)'

    # Check both stdout and stderr
    output = result.stdout + result.stderr
    for line in output.split('\n'):
        match = re.match(pattern, line)
        if match:
            file_path, line_num, col_num, message, issue_type = match.groups()

            # Extract variable/parameter name from message
            var_name = None
            if 'Variable "' in message:
                var_match = re.search(r'Variable "([^"]+)"', message)
                if var_match:
                    var_name = var_match.group(1)
            elif '"' in message and '" is not accessed' in message:
                var_match = re.search(r'"([^"]+)" is not accessed', message)
                if var_match:
                    var_name = var_match.group(1)

            issues.append(Issue(
                file=file_path,
                line=int(line_num),
                col=int(col_num),
                type=issue_type,  # type: ignore[arg-type]
                message=message,
                var_name=var_name
            ))

    return issues


def fix_unused_call_result(lines: list[str], issue: Issue) -> bool:
    """Fix reportUnusedCallResult by assigning to _."""
    if issue.line > len(lines):
        return False

    line_idx = issue.line - 1
    line = lines[line_idx]

    # Check if already assigned
    if re.match(r'^\s*[_\w]+ = ', line):
        return False

    # Add _ = prefix, preserving indentation
    indent_match = re.match(r'^(\s*)', line)
    indent = indent_match.group(1) if indent_match else ''
    content = line.lstrip()

    lines[line_idx] = f"{indent}_ = {content}"
    return True


def fix_unused_variable(lines: list[str], issue: Issue) -> bool:
    """Fix reportUnusedVariable by replacing with _."""
    if issue.line > len(lines) or not issue.var_name:
        return False

    line_idx = issue.line - 1
    line = lines[line_idx]
    var_name = issue.var_name

    # Pattern 1: for var in ... -> for _ in ...
    if f'for {var_name} in ' in line:
        lines[line_idx] = line.replace(f'for {var_name} in ', 'for _ in ', 1)
        return True

    # Pattern 2: var = value -> _ = value (only if standalone assignment)
    pattern = rf'\b{re.escape(var_name)}\b\s*='
    if re.search(pattern, line) and not re.search(r'[,\(]', line[:line.index(var_name)]):
        lines[line_idx] = re.sub(rf'\b{re.escape(var_name)}\b', '_', line, count=1)
        return True

    # Pattern 3: unpacking (x, var, y) = ... -> (x, _, y) = ...
    unpack_pattern = rf'([,\(])\s*{re.escape(var_name)}\s*([,\)])'
    if re.search(unpack_pattern, line):
        lines[line_idx] = re.sub(unpack_pattern, r'\1_\2', line, count=1)
        return True

    return False


def fix_unused_parameter(lines: list[str], issue: Issue) -> bool:
    """Fix reportUnusedParameter by prefixing with _."""
    if issue.line > len(lines) or not issue.var_name:
        return False

    line_idx = issue.line - 1
    line = lines[line_idx]
    var_name = issue.var_name

    # Already prefixed with _
    if f'_{var_name}' in line or var_name.startswith('_'):
        return False

    # Find the parameter and prefix it
    # Pattern: param_name: Type or param_name, or param_name) or param_name=default
    pattern = rf'\b{re.escape(var_name)}\b(?=[\s,:\)=])'
    if re.search(pattern, line):
        lines[line_idx] = re.sub(pattern, f'_{var_name}', line, count=1)
        return True

    return False


def fix_file(file_path: str, issues: list[Issue]) -> int:
    """Fix all issues in a single file."""
    path = Path(file_path)
    if not path.exists():
        return 0

    lines = path.read_text().splitlines(keepends=True)
    if not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    # Sort issues by line number (descending) to avoid line number shifts
    issues_sorted = sorted(issues, key=lambda x: x.line, reverse=True)

    fixed_count = 0
    for issue in issues_sorted:
        if issue.type == "reportUnusedCallResult":
            if fix_unused_call_result(lines, issue):
                fixed_count += 1
        elif issue.type == "reportUnusedVariable":
            if fix_unused_variable(lines, issue):
                fixed_count += 1
        elif issue.type == "reportUnusedParameter":
            if fix_unused_parameter(lines, issue):
                fixed_count += 1

    if fixed_count > 0:
        path.write_text(''.join(lines))

    return fixed_count


def main() -> None:
    """Main entry point."""
    print("Parsing basedpyright output...")
    issues = parse_basedpyright_output()

    # Filter to test files only
    test_issues = [i for i in issues if '/tests/' in i.file]

    print(f"\nFound {len(test_issues)} issues in test files:")
    by_type = defaultdict(int)
    for issue in test_issues:
        by_type[issue.type] += 1

    for issue_type, count in sorted(by_type.items()):
        print(f"  {issue_type}: {count}")

    # Group by file
    by_file = defaultdict(list)
    for issue in test_issues:
        by_file[issue.file].append(issue)

    print(f"\nProcessing {len(by_file)} test files...")

    total_fixed = 0
    files_modified = 0

    for file_path, file_issues in sorted(by_file.items()):
        fixed = fix_file(file_path, file_issues)
        if fixed > 0:
            files_modified += 1
            total_fixed += fixed
            print(f"  {Path(file_path).name}: fixed {fixed}/{len(file_issues)} issues")

    print(f"\n✓ Fixed {total_fixed} issues in {files_modified} files")
    print("\nRun './bpr' to verify remaining issues.")


if __name__ == "__main__":
    main()
