#!/usr/bin/env python3
"""Replace hasattr() with None checks in production code.

This script handles PLAN TAU Phase 1, Task 1.3: Replace All hasattr() with None Checks.
It processes all Python files in ui/, services/, and core/ directories.
"""

import re
from pathlib import Path


def fix_single_hasattr(content: str) -> str:
    """Replace single hasattr() patterns with None checks."""

    # Pattern 1: hasattr(self, "attr") -> self.attr is not None
    content = re.sub(r'\bhasattr\(self,\s*["\'](\w+)["\']\)', r"self.\1 is not None", content)

    # Pattern 2: hasattr(obj, "attr") -> obj.attr is not None
    content = re.sub(r'\bhasattr\((\w+),\s*["\'](\w+)["\']\)', r"\1.\2 is not None", content)

    # Pattern 3: hasattr(self.obj, "attr") -> self.obj.attr is not None
    content = re.sub(r'\bhasattr\(self\.(\w+),\s*["\'](\w+)["\']\)', r"self.\1.\2 is not None", content)

    return content


def fix_chained_hasattr(content: str) -> str:
    """Fix chained hasattr() patterns."""

    # Pattern: hasattr(obj, "attr1") and hasattr(obj, "attr2")
    # -> obj.attr1 is not None and obj.attr2 is not None
    # (Will be handled by single pattern recursively)

    # Pattern: obj is not None and hasattr(obj, "attr")
    # -> obj is not None and obj.attr is not None
    content = re.sub(
        r'(\w+) is not None and hasattr\(\1,\s*["\'](\w+)["\']\)', r"\1 is not None and \1.\2 is not None", content
    )

    # Pattern: obj and hasattr(obj, "attr")
    # -> obj is not None and obj.attr is not None
    content = re.sub(r'(\w+) and hasattr\(\1,\s*["\'](\w+)["\']\)', r"\1 is not None and \1.\2 is not None", content)

    return content


def fix_not_hasattr(content: str) -> str:
    """Fix negative hasattr() patterns."""

    # Pattern: not hasattr(self, "attr") -> self.attr is None
    content = re.sub(r'\bnot hasattr\(self,\s*["\'](\w+)["\']\)', r"self.\1 is None", content)

    # Pattern: not hasattr(obj, "attr") -> obj.attr is None
    content = re.sub(r'\bnot hasattr\((\w+),\s*["\'](\w+)["\']\)', r"\1.\2 is None", content)

    return content


def process_file(file_path: Path) -> tuple[int, list[str]]:
    """Process a single file, return count of replacements and list of changes."""
    content = file_path.read_text()
    original = content
    original_hasattr_count = content.count("hasattr(")

    # Apply fixes in order
    content = fix_not_hasattr(content)  # Handle 'not hasattr' first
    content = fix_chained_hasattr(content)  # Handle chained patterns
    content = fix_single_hasattr(content)  # Handle single patterns

    changes = []
    if content != original:
        file_path.write_text(content)
        new_hasattr_count = content.count("hasattr(")
        replacements = original_hasattr_count - new_hasattr_count

        # Find what was changed
        original_lines = original.split("\n")
        new_lines = content.split("\n")

        for i, (old, new) in enumerate(zip(original_lines, new_lines), 1):
            if old != new and "hasattr" in old:
                changes.append(f"  Line {i}: {old.strip()} -> {new.strip()}")

        return replacements, changes

    return 0, []


def main():
    """Process all production files."""
    directories = ["ui", "services", "core"]
    total = 0
    all_changes = []

    print("=" * 80)
    print("PLAN TAU Phase 1, Task 1.3: Replace hasattr() with None Checks")
    print("=" * 80)
    print()

    for directory in directories:
        path = Path(directory)
        if path.exists():
            for py_file in sorted(path.rglob("*.py")):
                # Skip test files
                if "test" not in str(py_file):
                    replacements, changes = process_file(py_file)
                    if replacements > 0:
                        print(f"\n{py_file}: {replacements} replacements")
                        for change in changes[:5]:  # Show first 5 changes per file
                            print(change)
                        if len(changes) > 5:
                            print(f"  ... and {len(changes) - 5} more")
                        total += replacements
                        all_changes.extend(changes)

    print("\n" + "=" * 80)
    print(f"TOTAL REPLACEMENTS: {total}")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run: grep -r 'hasattr(' ui/ services/ core/ --include='*.py' | wc -l")
    print("   Expected: 0")
    print("2. Run: ~/.local/bin/uv run ./bpr --errors-only")
    print("   Expected: 0 errors, reduced warnings")
    print("3. Run: ~/.local/bin/uv run pytest tests/ -x -q")
    print("   Expected: All tests pass")
    print()


if __name__ == "__main__":
    main()
