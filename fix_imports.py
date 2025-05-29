#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Import fixer for Python files.
Reorganizes imports according to PEP 8 standards.
"""

import re
from pathlib import Path

class ImportFixer:
    """Fixes import organization in Python files."""

    # Standard library modules
    STANDARD_LIBS = {
        'os', 'sys', 're', 'json', 'time', 'datetime', 'math',
        'functools', 'itertools', 'collections', 'typing', 'pathlib',
        'logging', 'inspect', 'types', 'copy', 'hashlib', 'subprocess',
        'argparse', 'unittest', 'abc', 'enum', 'warnings', 'traceback',
        'io', 'contextlib', 'dataclasses', 'weakref', 'operator'
    }

    # Third-party modules
    THIRD_PARTY = {'PySide6', 'coverage', 'numpy', 'matplotlib'}

    def __init__(self):
        self.standard_imports = []
        self.third_party_imports = []
        self.local_imports = []

    def categorize_import(self, import_line: str) -> str:
        """Categorize an import line."""
        # Extract module name
        if import_line.startswith('from '):
            match = re.match(r'from\s+(\S+)', import_line)
            if match:
                module = match.group(1).split('.')[0]
        elif import_line.startswith('import '):
            match = re.match(r'import\s+(\S+)', import_line)
            if match:
                module = match.group(1).split('.')[0]
        else:
            return 'unknown'

        if module in self.STANDARD_LIBS:
            return 'standard'
        elif module in self.THIRD_PARTY:
            return 'third_party'
        else:
            return 'local'

    def fix_file(self, file_path: Path) -> bool:
        """Fix imports in a single file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the import section
        import_start = -1
        import_end = -1
        imports = []
        pre_import_lines = []
        post_import_lines = []

        in_docstring = False
        docstring_count = 0

        for i, line in enumerate(lines):
            # Handle docstrings
            if '"""' in line or "'''" in line:
                docstring_count += line.count('"""') + line.count("'''")
                in_docstring = (docstring_count % 2 == 1)

            # Skip shebang and encoding
            if i < 2 and (line.startswith('#!') or 'coding:' in line or 'coding=' in line):
                pre_import_lines.append(line)
                continue

            # Skip module docstring
            if in_docstring or (i < 20 and line.strip().startswith('"""')):
                pre_import_lines.append(line)
                continue

            # Check for imports
            stripped = line.strip()
            if (stripped.startswith('import ') or stripped.startswith('from ')) and not stripped.startswith('#'):
                if import_start == -1:
                    import_start = i
                import_end = i
                imports.append(line)
            elif import_start == -1:
                pre_import_lines.append(line)
            elif import_start != -1 and i > import_end + 1 and stripped and not stripped.startswith('#'):
                # We've moved past imports
                post_import_lines = lines[i:]
                break
            elif import_start != -1:
                # Empty lines or comments within import section
                if not stripped or stripped.startswith('#'):
                    continue

        # Categorize imports
        self.standard_imports = []
        self.third_party_imports = []
        self.local_imports = []

        for imp in imports:
            category = self.categorize_import(imp.strip())
            if category == 'standard':
                self.standard_imports.append(imp)
            elif category == 'third_party':
                self.third_party_imports.append(imp)
            else:
                self.local_imports.append(imp)

        # Sort imports within each category
        self.standard_imports.sort()
        self.third_party_imports.sort()
        self.local_imports.sort()

        # Reconstruct file
        new_lines = pre_import_lines

        # Add organized imports
        if self.standard_imports:
            new_lines.extend(self.standard_imports)
            if self.third_party_imports or self.local_imports:
                new_lines.append('\n')

        if self.third_party_imports:
            new_lines.extend(self.third_party_imports)
            if self.local_imports:
                new_lines.append('\n')

        if self.local_imports:
            new_lines.extend(self.local_imports)

        # Add empty line after imports
        if imports and post_import_lines and not post_import_lines[0].strip():
            new_lines.append('\n')
        elif imports and post_import_lines:
            new_lines.append('\n')

        new_lines.extend(post_import_lines)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True

def main():
    """Test the import fixer on a sample file."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fix_imports.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    fixer = ImportFixer()
    if fixer.fix_file(file_path):
        print(f"Successfully fixed imports in {file_path}")
        print(f"Standard imports: {len(fixer.standard_imports)}")
        print(f"Third-party imports: {len(fixer.third_party_imports)}")
        print(f"Local imports: {len(fixer.local_imports)}")
    else:
        print(f"Failed to fix imports in {file_path}")

if __name__ == '__main__':
    main()
