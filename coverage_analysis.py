#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Coverage Analysis for CurveEditor.

This script analyzes test coverage for the CurveEditor project,
providing detailed metrics for all modules and services.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class CoverageAnalyzer:
    """Analyzes test coverage for the CurveEditor project."""

    def __init__(self, project_root: Path):
        """Initialize the coverage analyzer.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self.coverage_data: Dict[str, float] = {}

    def analyze_coverage(self) -> bool:
        """Run coverage analysis using unittest.

        Returns:
            True if coverage meets the target (>80%), False otherwise
        """
        logger.info("Starting coverage analysis...")

        try:
            # Check if coverage is installed
            import coverage
        except ImportError:
            logger.error("Coverage package not installed. Please run: pip install coverage")
            return False

        # Create coverage instance
        cov = coverage.Coverage(
            source=[
                str(self.project_root),
                str(self.project_root / 'services'),
                str(self.project_root / 'signal_connectors')
            ],
            omit=[
                '*/tests/*',
                '*/test_*.py',
                '*/__init__.py',
                '*/docs/*',
                '*/examples/*',
                '*/debug_*.py',
                '*/analyze_*.py',
                '*/fix_*.py',
                '*/run_*.py',
                '*/test_runner.py',
                '*/coverage_analysis.py'
            ]
        )

        # Start coverage
        cov.start()

        # Run all tests
        import unittest
        loader = unittest.TestLoader()
        suite = loader.discover(str(self.project_root / 'tests'), pattern='test_*.py')
        runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
        result = runner.run(suite)

        # Stop coverage and save data
        cov.stop()
        cov.save()

        # Get coverage report
        logger.info("\n" + "="*60)
        logger.info("COVERAGE REPORT")
        logger.info("="*60)

        # Print to console and capture data
        from io import StringIO
        coverage_stream = StringIO()
        cov.report(file=coverage_stream)
        coverage_output = coverage_stream.getvalue()

        # Parse coverage data
        total_coverage = self._parse_coverage_output(coverage_output)

        # Print the report
        print(coverage_output)

        # Check if tests passed
        if not result.wasSuccessful():
            logger.error(f"\n❌ {len(result.failures)} tests failed, {len(result.errors)} errors occurred")
            return False

        # Check coverage threshold
        if total_coverage >= 80.0:
            logger.info(f"\n✅ Coverage {total_coverage:.1f}% exceeds 80% target!")
            return True
        else:
            logger.warning(f"\n⚠️  Coverage {total_coverage:.1f}% is below 80% target")
            return False

    def _parse_coverage_output(self, output: str) -> float:
        """Parse coverage output to extract total coverage percentage.

        Args:
            output: Coverage report output

        Returns:
            Total coverage percentage
        """
        lines = output.strip().split('\n')
        for line in reversed(lines):
            if line.startswith('TOTAL'):
                parts = line.split()
                if len(parts) >= 4:
                    coverage_str = parts[-1].rstrip('%')
                    try:
                        return float(coverage_str)
                    except ValueError:
                        pass
        return 0.0

    def generate_detailed_report(self):
        """Generate a detailed HTML coverage report."""
        try:
            import coverage
            cov = coverage.Coverage()
            cov.load()

            # Generate HTML report
            html_dir = self.project_root / 'coverage_html_report'
            cov.html_report(directory=str(html_dir))
            logger.info(f"\n📊 Detailed HTML report generated at: {html_dir}/index.html")

        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")

    def check_module_coverage(self) -> Dict[str, Dict[str, float]]:
        """Check coverage for specific modules.

        Returns:
            Dictionary with module coverage data
        """
        modules_to_check = {
            'Core': ['main_window.py', 'application_state.py', 'ui_initializer.py',
                     'main_window_operations.py', 'main_window_smoothing.py'],
            'Services': [f'services/{f}' for f in [
                'curve_service.py', 'file_service.py', 'image_service.py',
                'dialog_service.py', 'settings_service.py', 'history_service.py',
                'analysis_service.py', 'unified_transformation_service.py'
            ]],
            'UI Components': ['ui_components.py', 'toolbar_components.py',
                             'timeline_components.py', 'visualization_components.py'],
            'Signal Connectors': [f'signal_connectors/{f}' for f in [
                'edit_signal_connector.py', 'file_signal_connector.py',
                'view_signal_connector.py', 'ui_signal_connector.py'
            ]]
        }

        results = {}

        try:
            import coverage
            cov = coverage.Coverage()
            cov.load()

            for category, files in modules_to_check.items():
                category_coverage = {}
                for file in files:
                    file_path = self.project_root / file
                    if file_path.exists():
                        try:
                            analysis = cov.analysis2(str(file_path))
                            executed = len(analysis[1])
                            missing = len(analysis[3])
                            total = executed + missing
                            if total > 0:
                                coverage_pct = (executed / total) * 100
                                category_coverage[file] = coverage_pct
                        except Exception:
                            pass

                if category_coverage:
                    results[category] = category_coverage

        except Exception as e:
            logger.error(f"Failed to analyze module coverage: {e}")

        return results


def main():
    """Main entry point for coverage analysis."""
    # Get project root
    project_root = Path(__file__).parent

    # Create analyzer
    analyzer = CoverageAnalyzer(project_root)

    # Run coverage analysis
    coverage_ok = analyzer.analyze_coverage()

    # Generate detailed report
    analyzer.generate_detailed_report()

    # Check module-specific coverage
    module_coverage = analyzer.check_module_coverage()

    if module_coverage:
        logger.info("\n" + "="*60)
        logger.info("MODULE COVERAGE BREAKDOWN")
        logger.info("="*60)

        for category, files in module_coverage.items():
            logger.info(f"\n{category}:")
            for file, coverage in sorted(files.items()):
                status = "✅" if coverage >= 80 else "⚠️ "
                logger.info(f"  {status} {file}: {coverage:.1f}%")

    # Return appropriate exit code
    return 0 if coverage_ok else 1


if __name__ == '__main__':
    sys.exit(main())
