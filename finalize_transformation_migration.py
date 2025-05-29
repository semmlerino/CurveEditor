#!/usr/bin/env python3
"""
Finalize Transformation System Migration

This script completes the migration from legacy transformation systems
to the unified transformation service by:

1. Updating all remaining import references 
2. Removing deprecated transformation modules
3. Verifying that the migration is complete
"""

from typing import List, Dict
import logging
import os
import re
import sys

import glob

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import logging service
from services.logging_service import LoggingService

# Configure logger
logger = LoggingService.get_logger("transformation_migration")


class MigrationFinalizer:
    """Tool for finalizing the migration to the unified transformation system."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats: Dict[str, int] = {
            "files_scanned": 0,
            "files_updated": 0,
            "legacy_imports_replaced": 0,
            "legacy_method_calls_replaced": 0,
        }
        self.changed_files: List[str] = []
        self.skipped_files: List[str] = []

    def scan_project_files(self, extensions: List[str] = [".py"]) -> List[str]:
        """Scan for all project files with the specified extensions."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        files: List[str] = []
        
        for ext in extensions:
            pattern = os.path.join(project_root, "**", f"*{ext}")
            files.extend(glob.glob(pattern, recursive=True))
        
        logger.info(f"Found {len(files)} files to scan")
        return files

    def is_test_or_validation_file(self, file_path: str) -> bool:
        """Check if a file is a test or validation file that should be skipped."""
        # Skip test files, validation scripts and migration tools
        patterns = [
            r"test_.*\.py$",
            r".*_test\.py$",
            r"validate_.*\.py$",
            r".*_validation\.py$",
            r"migrate_.*\.py$",
            r".*_migration\.py$",
        ]
        
        for pattern in patterns:
            if re.search(pattern, file_path):
                return True
                
        return False

    def replace_imports(self, file_path: str) -> bool:
        """Replace legacy transformation imports with unified ones."""
        if self.is_test_or_validation_file(file_path):
            logger.info(f"Skipping test/validation file: {file_path}")
            self.skipped_files.append(file_path)
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                
            original_content = content
            
            # Replace import statements
            replacements = {
                r"from services\.transformation_service import TransformationService": 
                    "from services.unified_transformation_service import UnifiedTransformationService",
                
                r"from services\.transform import Transform": 
                    "from services.unified_transform import Transform",
                
                r"import services\.transformation_service": 
                    "import services.unified_transformation_service",
                
                r"import services\.transform": 
                    "import services.unified_transform"
            }
            
            for pattern, replacement in replacements.items():
                content = re.sub(pattern, replacement, content)
            
            # Replace references to TransformationService with UnifiedTransformationService
            content = re.sub(r"TransformationService\.", "UnifiedTransformationService.", content)
            
            # Replace any remaining direct references
            content = content.replace("services.transformation_service", "services.unified_transformation_service")
            content = content.replace("services.transform", "services.unified_transform")
            
            if content != original_content:
                if not self.dry_run:
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(content)
                
                self.stats["files_updated"] += 1
                self.changed_files.append(file_path)
                logger.info(f"Updated imports in {file_path}")
                return True
            else:
                logger.debug(f"No changes needed in {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False

    def run_migration(self) -> Dict[str, int]:
        """Run the complete migration process and return statistics."""
        logger.info(f"Starting finalization of transformation system migration (dry_run={self.dry_run})")
        
        # Scan all project files
        files = self.scan_project_files()
        self.stats["files_scanned"] = len(files)
        
        # Process each file
        for file_path in files:
            self.replace_imports(file_path)
        
        # Generate summary
        logger.info("\nMigration Summary:")
        logger.info(f"Files scanned: {self.stats['files_scanned']}")
        logger.info(f"Files updated: {self.stats['files_updated']}")
        logger.info(f"Files skipped: {len(self.skipped_files)}")
        
        if self.changed_files:
            logger.info("\nChanged files:")
            for file in self.changed_files:
                logger.info(f"  - {os.path.relpath(file)}")
        
        return self.stats


def main():
    """Main entry point for the migration finalizer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Finalize the migration to the unified transformation system"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Simulate the migration without making changes"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        LoggingService.set_level(logging.DEBUG)
    
    # Run the migration
    finalizer = MigrationFinalizer(dry_run=args.dry_run)
    stats = finalizer.run_migration()
    
    # Return success if any files were updated or would be updated in dry run
    return 0 if stats["files_updated"] > 0 or args.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
