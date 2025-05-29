#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Import analyzer for CurveEditor project.
Identifies and reports import organization issues.
"""

import re
from typing import List, Dict, Tuple, Set, Any, cast
from pathlib import Path

class ImportAnalyzer:
    """Analyzes Python files for import organization issues."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues: List[str] = []

    def analyze_file(self, file_path: Path) -> Dict[str, List[Tuple[int, str]] | List[str]]: 
        """Analyze imports in a single file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        imports: Dict[str, List[Tuple[int, str]] | List[str]] = {
            'standard': [],
            'third_party': [],
            'local': [],
            'commented': [],
            'issues': []
        }

        # Standard library modules
        standard_libs: Set[str] = {
            'os', 'sys', 're', 'json', 'time', 'datetime', 'math',
            'functools', 'itertools', 'collections', 'typing', 'pathlib',
            'logging', 'inspect', 'types', 'copy', 'hashlib', 'subprocess',
            'argparse', 'unittest'
        }

        # Third-party modules in this project
        third_party: Set[str] = {'PySide6', 'coverage'}

        import_section_ended = False
        last_import_line = -1

        for i, line in enumerate(lines):
            # Skip docstrings and comments at the beginning
            if i < 10 and (line.strip().startswith('"""') or line.strip().startswith('#')):
                continue

            # Check for imports
            import_match = re.match(r'^(from\s+(\S+)\s+import|import\s+(\S+))', line.strip())
            if import_match:
                last_import_line = i
                module = import_match.group(2) or import_match.group(3)
                module_root = module.split('.')[0]

                # Categorize import
                if module_root in standard_libs:
                    standard = cast(List[Tuple[int, str]], imports['standard']) 
                    standard.append((i, line.strip()))
                elif module_root in third_party:
                    third_party_imports = cast(List[Tuple[int, str]], imports['third_party'])
                    third_party_imports.append((i, line.strip()))
                else:
                    local = cast(List[Tuple[int, str]], imports['local'])
                    local.append((i, line.strip()))

            # Check for commented imports
            elif re.match(r'^#\s*(from\s+\S+\s+import|import\s+)', line.strip()):
                commented = cast(List[Tuple[int, str]], imports['commented'])
                commented.append((i, line.strip()))

            # Check if we've moved past imports
            elif last_import_line >= 0 and i > last_import_line + 2 and line.strip() and not line.strip().startswith('#'):
                import_section_ended = True

            # Check for late imports
            if import_section_ended and import_match:
                issues = cast(List[str], imports['issues'])
                issues.append(f"Line {i+1}: Late import: {line.strip()}")

        # Check import order
        standard = cast(List[Tuple[int, str]], imports['standard']) 
        third_party_imports = cast(List[Tuple[int, str]], imports['third_party'])
        local = cast(List[Tuple[int, str]], imports['local'])
        issues = cast(List[str], imports['issues'])
        
        if standard and third_party_imports:
            if standard[-1][0] > third_party_imports[0][0]:
                issues.append("Standard library imports mixed with third-party imports")

        if third_party_imports and local:
            if third_party_imports[-1][0] > local[0][0]:
                issues.append("Third-party imports mixed with local imports")

        return imports

    def find_circular_imports(self) -> List[Tuple[str, str]]:
        """Find potential circular imports."""
        import_graph: Dict[str, Set[str]] = {}

        # Build import graph
        for py_file in self.project_root.rglob('*.py'):
            if 'test' in py_file.name or '__pycache__' in str(py_file):
                continue

            module_name = str(py_file.relative_to(self.project_root)).replace('/', '.').replace('\\', '.')[:-3]

            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all local imports
            module_imports: Set[str] = set()
            for match in re.finditer(r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import', content):
                if not match.group(1).startswith(('PySide6', 'typing')):
                    module_imports.add(match.group(1))

            import_graph[module_name] = module_imports

        # Find cycles (simplified - only direct cycles)
        cycles: List[Tuple[str, str]] = []
        for module, module_imports in import_graph.items():
            for imported in module_imports:
                if imported in import_graph and module in import_graph[imported]:
                    cycle: Tuple[str, str] = (module, imported) if module < imported else (imported, module)
                    if cycle not in cycles:
                        cycles.append(cycle)

        return cycles

    def analyze_project(self) -> Dict[str, Any]:
        """Analyze all Python files in the project."""
        results: Dict[str, Any] = {
            'files_analyzed': 0,
            'import_issues': {},
            'commented_imports': {},
            'circular_imports': [],
            'summary': {
                'files_with_issues': 0,
                'total_issues': 0,
                'circular_imports': 0,
                'files_with_commented_imports': 0
            }
        }

        # Analyze each file
        for py_file in self.project_root.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'test' in py_file.name:
                continue

            rel_path = str(py_file.relative_to(self.project_root))
            file_imports = self.analyze_file(py_file)

            issues = cast(List[str], file_imports['issues'])
            if issues:
                results['import_issues'][rel_path] = issues
                results['summary']['files_with_issues'] += 1
                results['summary']['total_issues'] += len(issues)

            commented = cast(List[Tuple[int, str]], file_imports['commented'])
            if commented:
                results['commented_imports'][rel_path] = [c[1] for c in commented]
                results['summary']['files_with_commented_imports'] += 1

            results['files_analyzed'] += 1

        # Find circular imports
        circular_imports = self.find_circular_imports()
        results['circular_imports'] = circular_imports
        results['summary']['circular_imports'] = len(circular_imports)

        return results

def main():
    """Run import analysis on the CurveEditor project."""
    project_root = '/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor'
    analyzer = ImportAnalyzer(project_root)
    results = analyzer.analyze_project()

    print("=== CurveEditor Import Analysis ===\n")
    print(f"Files analyzed: {results['files_analyzed']}")
    print(f"Files with import issues: {results['summary']['files_with_issues']}")
    print(f"Total issues found: {results['summary']['total_issues']}")
    print(f"Files with commented imports: {results['summary']['files_with_commented_imports']}")
    print(f"Circular imports found: {len(results['circular_imports'])}")

    if results['import_issues']:
        print("\n=== Import Organization Issues ===")
        for file, issues in sorted(results['import_issues'].items()):
            print(f"\n{file}:")
            for issue in issues:
                print(f"  - {issue}")

    if results['commented_imports']:
        print("\n=== Commented Imports (to be removed) ===")
        for file, imports in sorted(results['commented_imports'].items()):
            print(f"\n{file}:")
            for imp in imports:
                print(f"  - {imp}")

    if results['circular_imports']:
        print("\n=== Circular Imports ===")
        for module1, module2 in results['circular_imports']:
            print(f"  - {module1} <-> {module2}")

    print("\n=== Recommendations ===")
    print("1. Reorganize imports in files with issues to follow: standard -> third-party -> local")
    print("2. Remove all commented-out imports")
    print("3. Resolve circular imports by refactoring or using TYPE_CHECKING")
    print("4. Move late imports to the top of files")

if __name__ == '__main__':
    main()
