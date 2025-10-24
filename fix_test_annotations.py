#!/usr/bin/env python3
"""Script to automatically add missing type annotations to test files."""

import re
import sys
from pathlib import Path


def infer_type_from_value(value: str) -> str:
    """Infer type annotation from assignment value."""
    value = value.strip()

    # Boolean
    if value in ("True", "False"):
        return "bool"
    # None
    if value == "None":
        return "object | None"
    # Integer
    if re.match(r"^-?\d+$", value):
        return "int"
    # Float
    if re.match(r"^-?\d+\.\d+$", value):
        return "float"
    # String
    if value.startswith('"') or value.startswith("'"):
        return "str"
    # List
    if value.startswith("["):
        return "list[object]"
    # Set
    if value == "set()":
        return "set[int]"
    # Default to object
    return "object"


def fix_class_annotations(file_path: Path) -> int:
    """Add missing class attribute annotations."""
    content = file_path.read_text()
    lines = content.split("\n")

    fixes = 0
    i = 0
    while i < len(lines):
        line = lines[i]

        # Find class definition
        class_match = re.match(r"^(\s*)class (\w+)", line)
        if class_match:
            indent = class_match.group(1)
            class_name = class_match.group(2)

            # Skip to __init__ or first method
            j = i + 1
            attrs_to_add = []

            # Look for __init__ method
            while j < len(lines):
                init_line = lines[j]

                if re.match(r"^\s*def __init__", init_line):
                    # Found __init__, scan for self.attr = assignments
                    k = j + 1
                    while k < len(lines) and (lines[k].strip().startswith("self.") or lines[k].strip() == "" or ":" in lines[k] or "#" in lines[k] or lines[k].strip().startswith('"""') or lines[k].strip().startswith("from ") or lines[k].strip().startswith("import ")):
                        assign_line = lines[k].strip()
                        assign_match = re.match(r"self\.(\w+)\s*=\s*(.+?)(?:\s*#.*)?$", assign_line)
                        if assign_match:
                            attr_name = assign_match.group(1)
                            value = assign_match.group(2)

                            # Check if annotation already exists in class body
                            has_annotation = False
                            for m in range(i + 1, j):
                                if re.match(rf"^\s*{attr_name}:\s*", lines[m]):
                                    has_annotation = True
                                    break

                            if not has_annotation and not attr_name.startswith("_"):
                                type_hint = infer_type_from_value(value)
                                attrs_to_add.append((attr_name, type_hint))

                        k += 1
                    break

                j += 1

            # Add annotations after class definition
            if attrs_to_add:
                # Find insertion point (after docstring or class line)
                insert_pos = i + 1

                # Skip docstring if present
                if insert_pos < len(lines) and '"""' in lines[insert_pos]:
                    # Skip to end of docstring
                    while insert_pos < len(lines) and not (lines[insert_pos].strip().endswith('"""') and insert_pos > i + 1):
                        insert_pos += 1
                    insert_pos += 1

                # Skip empty lines
                while insert_pos < len(lines) and lines[insert_pos].strip() == "":
                    insert_pos += 1

                # Add blank line and annotations
                new_lines = []
                for attr_name, type_hint in attrs_to_add:
                    new_lines.append(f"{indent}    {attr_name}: {type_hint}")
                    fixes += 1

                if new_lines:
                    new_lines.append("")  # Blank line after annotations
                    lines = lines[:insert_pos] + new_lines + lines[insert_pos:]
                    i = insert_pos + len(new_lines)
                    continue

        i += 1

    if fixes > 0:
        file_path.write_text("\n".join(lines))

    return fixes


def main():
    """Fix all test files."""
    test_files = [
        "tests/test_integration_real.py",
        "tests/test_main_window_store_integration.py",
        "tests/test_qt_utils.py",
        "tests/test_rendering_real.py",
        "tests/test_timeline_integration.py",
        "tests/test_timeline_tabs.py",
        "tests/test_ui_service.py",
    ]

    total_fixes = 0
    for file_name in test_files:
        file_path = Path(file_name)
        if file_path.exists():
            fixes = fix_class_annotations(file_path)
            if fixes > 0:
                print(f"Fixed {fixes} annotations in {file_name}")
                total_fixes += fixes
        else:
            print(f"Warning: {file_name} not found", file=sys.stderr)

    print(f"\nTotal fixes: {total_fixes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
