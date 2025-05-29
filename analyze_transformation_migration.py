#!/usr/bin/env python
"""Analyze the current state of transformation system migration."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class TransformationMigrationAnalyzer:
    """Analyzes the codebase to understand transformation system usage."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.legacy_patterns = {
            'TransformStabilizer': r'TransformStabilizer',
            'transform_point_legacy': r'transform_point_legacy',
            'TransformationIntegration': r'TransformationIntegration',
            'install_unified_system': r'install_unified_system',
            'get_transform (legacy)': r'(?<!unified_)get_transform\s*\(',
        }
        self.unified_patterns = {
            'UnifiedTransformationService': r'UnifiedTransformationService',
            'unified_transform.Transform': r'from services\.unified_transform import Transform',
            'Transform type': r'Transform\[',
        }

    def find_usage(self, pattern: str, exclude_dirs: Set[str] = None) -> List[Tuple[str, int, str]]:
        """Find all usages of a pattern in Python files."""
        exclude_dirs = exclude_dirs or {'__pycache__', '.git', 'docs', 'tests'}
        results = []

        for py_file in self.project_root.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    if re.search(pattern, line):
                        rel_path = py_file.relative_to(self.project_root)
                        results.append((str(rel_path), i + 1, line.strip()))
            except Exception as e:
                print(f"Error reading {py_file}: {e}")

        return results

    def analyze_migration_status(self) -> Dict[str, any]:
        """Analyze the current state of transformation migration."""
        print("Analyzing transformation system migration status...\n")

        results = {
            'legacy_usage': {},
            'unified_usage': {},
            'files_using_legacy': set(),
            'files_using_unified': set(),
            'compatibility_layer_usage': [],
            'migration_complete': False
        }

        # Find legacy system usage
        print("=== Legacy System Usage ===")
        for name, pattern in self.legacy_patterns.items():
            usage = self.find_usage(pattern)
            results['legacy_usage'][name] = usage

            if usage:
                print(f"\n{name}: {len(usage)} occurrences")
                for file_path, line_num, line_content in usage[:3]:  # Show first 3
                    print(f"  {file_path}:{line_num} - {line_content[:80]}...")
                    results['files_using_legacy'].add(file_path)
                if len(usage) > 3:
                    print(f"  ... and {len(usage) - 3} more")

        # Find unified system usage
        print("\n=== Unified System Usage ===")
        for name, pattern in self.unified_patterns.items():
            usage = self.find_usage(pattern)
            results['unified_usage'][name] = usage

            if usage:
                print(f"\n{name}: {len(usage)} occurrences")
                for file_path, line_num, line_content in usage[:3]:  # Show first 3
                    print(f"  {file_path}:{line_num} - {line_content[:80]}...")
                    results['files_using_unified'].add(file_path)
                if len(usage) > 3:
                    print(f"  ... and {len(usage) - 3} more")

        # Check transformation_integration.py usage (compatibility layer)
        compat_usage = self.find_usage(r'from services\.transformation_integration import')
        results['compatibility_layer_usage'] = compat_usage

        print("\n=== Compatibility Layer Usage ===")
        if compat_usage:
            print(f"Found {len(compat_usage)} files using transformation_integration:")
            for file_path, line_num, line_content in compat_usage:
                print(f"  {file_path}:{line_num} - {line_content}")
        else:
            print("No files using transformation_integration (good!)")

        # Determine if migration is complete
        legacy_count = sum(len(usage) for usage in results['legacy_usage'].values())
        results['migration_complete'] = legacy_count == 0 and not compat_usage

        return results

    def generate_migration_report(self, results: Dict[str, any]) -> str:
        """Generate a detailed migration report."""
        report = []
        report.append("# Transformation System Migration Report\n")
        report.append(f"Date: 2025-05-30\n")

        # Summary
        report.append("## Summary\n")
        legacy_files = len(results['files_using_legacy'])
        unified_files = len(results['files_using_unified'])
        compat_files = len(results['compatibility_layer_usage'])

        report.append(f"- Files using legacy system: {legacy_files}")
        report.append(f"- Files using unified system: {unified_files}")
        report.append(f"- Files using compatibility layer: {compat_files}")
        report.append(f"- Migration complete: {'✅ Yes' if results['migration_complete'] else '❌ No'}\n")

        # Files needing migration
        if results['files_using_legacy']:
            report.append("## Files Requiring Migration\n")
            for file_path in sorted(results['files_using_legacy']):
                report.append(f"- [ ] {file_path}")
            report.append("")

        # Compatibility layer files
        if results['compatibility_layer_usage']:
            report.append("## Files Using Compatibility Layer\n")
            report.append("These files should be updated to use UnifiedTransformationService directly:\n")
            for file_path, _, _ in results['compatibility_layer_usage']:
                report.append(f"- [ ] {file_path}")
            report.append("")

        # Action items
        report.append("## Action Items\n")
        report.append("1. Replace all `TransformationIntegration` imports with `UnifiedTransformationService`")
        report.append("2. Update `transform_point_legacy` calls to use the unified API")
        report.append("3. Remove `services/transformation_integration.py` once migration is complete")
        report.append("4. Update tests to use the unified system")
        report.append("5. Remove any `install_unified_system` calls")

        return "\n".join(report)

def main():
    """Run the transformation migration analysis."""
    project_root = "/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor"
    analyzer = TransformationMigrationAnalyzer(project_root)

    # Analyze current state
    results = analyzer.analyze_migration_status()

    # Generate report
    report = analyzer.generate_migration_report(results)

    # Save report
    report_path = Path(project_root) / "docs" / "transformation_migration_status.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n=== Report saved to {report_path} ===")

    # Show summary
    print("\n=== Migration Summary ===")
    if results['migration_complete']:
        print("✅ Transformation system migration is COMPLETE!")
        print("   The compatibility layer can be removed.")
    else:
        legacy_count = sum(len(usage) for usage in results['legacy_usage'].values())
        print(f"❌ Migration in progress: {legacy_count} legacy references remain")
        print(f"   {len(results['files_using_legacy'])} files need updating")

if __name__ == "__main__":
    main()
