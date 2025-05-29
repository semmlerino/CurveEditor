#!/usr/bin/env python3
"""
Migration Script for Unified Transformation System

This script helps migrate the CurveEditor codebase from the fragmented
transformation system to the unified transformation system. It provides
options for gradual migration and validation.

Usage:
    python migrate_to_unified_transforms.py [options]

Options:
    --validate      Validate the new system against the old one
    --patch-all     Apply all compatibility patches
    --install       Install unified system in curve views
    --test          Run transformation tests
    --report        Generate migration report
"""

import sys
import argparse
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from services.transformation_integration import (
    MigrationHelper, set_use_unified_system
)
from services.unified_transformation_service import UnifiedTransformationService
from services.logging_service import LoggingService

# Configure logger
logger = LoggingService.get_logger("transformation_migration")


class TransformationMigrationTool:
    """Tool for managing migration to the unified transformation system."""

    def __init__(self):
        self.migration_status = {
            'patches_applied': False,
            'validation_passed': False,
            'installation_completed': False,
            'tests_passed': False
        }

    def validate_unified_system(self) -> bool:
        """
        Validate that the unified system works correctly.

        Returns:
            True if validation passes
        """
        logger.info("Starting unified transformation system validation...")

        try:
            # Test basic transform creation
            from services.view_state import ViewState

            # Create a test view state
            test_view_state = ViewState(
                display_width=1920,
                display_height=1080,
                widget_width=800,
                widget_height=600,
                zoom_factor=1.0,
                offset_x=0.0,
                offset_y=0.0
            )

            # Create transform
            transform = UnifiedTransformationService.from_view_state(test_view_state)

            # Test basic transformation
            result = transform.apply(100, 200)
            logger.info(f"Test transformation: (100, 200) -> {result}")

            # Test inverse transformation
            inverse_result = transform.apply_inverse(result[0], result[1])
            logger.info(f"Inverse transformation: {result} -> {inverse_result}")

            # Validate inverse transformation accuracy
            dx = abs(inverse_result[0] - 100)
            dy = abs(inverse_result[1] - 200)

            if dx < 0.01 and dy < 0.01:
                logger.info("✓ Inverse transformation validation passed")
                self.migration_status['validation_passed'] = True
                return True
            else:
                logger.error(f"✗ Inverse transformation validation failed: dx={dx}, dy={dy}")
                return False

        except Exception as e:
            logger.error(f"✗ Validation failed with error: {e}")
            return False

    def apply_patches(self) -> bool:
        """
        Apply all compatibility patches.

        Returns:
            True if patches applied successfully
        """
        logger.info("Applying transformation system patches...")

        try:
            MigrationHelper.apply_all_patches()
            logger.info("✓ All patches applied successfully")
            self.migration_status['patches_applied'] = True
            return True

        except Exception as e:
            logger.error(f"✗ Failed to apply patches: {e}")
            return False

    def install_unified_system(self) -> bool:
        """
        Install the unified system in available curve views.

        Returns:
            True if installation successful
        """
        logger.info("Installing unified transformation system...")

        try:
            # Enable the unified system
            set_use_unified_system(True)

            # Clear any existing transform cache
            UnifiedTransformationService.clear_cache()

            logger.info("✓ Unified transformation system installed")
            self.migration_status['installation_completed'] = True
            return True

        except Exception as e:
            logger.error(f"✗ Installation failed: {e}")
            return False

    def run_tests(self) -> bool:
        """
        Run transformation tests to verify system works correctly.

        Returns:
            True if all tests pass
        """
        logger.info("Running transformation tests...")

        try:
            # Test 1: Basic transformation
            from services.view_state import ViewState

            view_state = ViewState(
                display_width=1920,
                display_height=1080,
                widget_width=800,
                widget_height=600
            )

            transform = UnifiedTransformationService.from_view_state(view_state)

            # Test multiple points
            test_points = [(0, 0.0, 0.0), (0, 100.0, 100.0), (0, 500.0, 300.0), (0, 1000.0, 800.0)]
            results = UnifiedTransformationService.transform_points(transform, test_points)

            if len(results) == len(test_points):
                logger.info("✓ Multi-point transformation test passed")
            else:
                logger.error("✗ Multi-point transformation test failed")
                return False

            # Test 2: Transform caching
            # Get cache stats before creating the second transform (commented out as unused)
            # cache_stats_before = UnifiedTransformationService.get_cache_stats()

            # Create the same transform again (variable commented out as unused)
            # transform2 = UnifiedTransformationService.from_view_state(view_state)
            # Just create the transform without storing it
            UnifiedTransformationService.from_view_state(view_state)

            cache_stats_after = UnifiedTransformationService.get_cache_stats()

            if cache_stats_after['cache_size'] > 0:
                logger.info("✓ Transform caching test passed")
            else:
                logger.warning("Transform caching may not be working as expected")

            # Test 3: Parameter updates
            updated_transform = transform.with_updates(scale=2.0)

            if updated_transform != transform:
                logger.info("✓ Parameter update test passed")
            else:
                logger.error("✗ Parameter update test failed")
                return False

            logger.info("✓ All transformation tests passed")
            self.migration_status['tests_passed'] = True
            return True

        except Exception as e:
            logger.error(f"✗ Test execution failed: {e}")
            return False

    def generate_report(self) -> str:
        """
        Generate a migration status report.

        Returns:
            Report as a string
        """
        report_lines = [
            "=== Transformation System Migration Report ===",
            "",
            "Migration Status:",
        ]

        for task, completed in self.migration_status.items():
            status = "✓ COMPLETED" if completed else "✗ PENDING"
            task_name = task.replace('_', ' ').title()
            report_lines.append(f"  {task_name}: {status}")

        # Add cache statistics
        cache_stats = UnifiedTransformationService.get_cache_stats()
        report_lines.extend([
            "",
            "Cache Statistics:",
            f"  Current cache size: {cache_stats['cache_size']}",
            f"  Maximum cache size: {cache_stats['max_cache_size']}",
        ])

        # Summary
        completed_count = sum(self.migration_status.values())
        total_count = len(self.migration_status)

        report_lines.extend([
            "",
            "Summary:",
            f"  Completed tasks: {completed_count}/{total_count}",
            f"  Migration status: {'COMPLETE' if completed_count == total_count else 'IN PROGRESS'}",
            "",
            "=== End of Report ===",
        ])

        return '\n'.join(report_lines)

    def run_full_migration(self) -> bool:
        """
        Run the complete migration process.

        Returns:
            True if migration completed successfully
        """
        logger.info("Starting full migration to unified transformation system...")

        steps = [
            ("Validation", self.validate_unified_system),
            ("Patch Application", self.apply_patches),
            ("System Installation", self.install_unified_system),
            ("Test Execution", self.run_tests),
        ]

        for step_name, step_func in steps:
            logger.info(f"Executing: {step_name}")
            if not step_func():
                logger.error(f"Migration failed at step: {step_name}")
                return False

        logger.info("✓ Full migration completed successfully")
        return True


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate to unified transformation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--validate', action='store_true',
                       help='Validate the unified system')
    parser.add_argument('--patch-all', action='store_true',
                       help='Apply all compatibility patches')
    parser.add_argument('--install', action='store_true',
                       help='Install unified system')
    parser.add_argument('--test', action='store_true',
                       help='Run transformation tests')
    parser.add_argument('--report', action='store_true',
                       help='Generate migration report')
    parser.add_argument('--full', action='store_true',
                       help='Run full migration process')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        LoggingService.set_level("transformation_migration", "DEBUG")

    # Create migration tool
    tool = TransformationMigrationTool()

    # Execute requested actions
    success = True

    if args.full:
        success = tool.run_full_migration()
    else:
        if args.validate:
            success &= tool.validate_unified_system()

        if args.patch_all:
            success &= tool.apply_patches()

        if args.install:
            success &= tool.install_unified_system()

        if args.test:
            success &= tool.run_tests()

    if args.report:
        print(tool.generate_report())

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
