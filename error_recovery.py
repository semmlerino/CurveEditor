#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Error recovery mechanisms for the CurveEditor application.

This module provides recovery strategies for critical operations that may fail.
It works in conjunction with the exceptions.py and error_handling.py modules
to provide a robust error handling and recovery system.
"""

import logging
import os
import json
import tempfile
import shutil
from typing import Any, Dict, List, Optional, Tuple, cast

from services.logging_service import LoggingService
from exceptions import (
    CurveEditorError, FileError, FileReadError, FileWriteError, 
    DataError, DataNotFoundError, DataProcessingError
)

# Configure module logger
logger = LoggingService.get_logger("error_recovery")


class ErrorRecovery:
    """Static class providing error recovery mechanisms for critical operations."""

    @staticmethod
    def recover_file_operation(operation: str, file_path: str, error: Exception) -> Optional[str]:
        """
        Attempt to recover from a file operation error.
        
        Args:
            operation: The file operation that failed ('read', 'write')
            file_path: Path to the file that caused the error
            error: The exception that was raised
            
        Returns:
            Optional alternative file path if recovery was successful
        """
        logger.info(f"Attempting to recover from {operation} error on {file_path}")
        
        if operation == 'read':
            return ErrorRecovery._recover_file_read(file_path, error)
        elif operation == 'write':
            return ErrorRecovery._recover_file_write(file_path, error)
        else:
            logger.error(f"Unknown file operation: {operation}")
            return None

    @staticmethod
    def _recover_file_read(file_path: str, error: Exception) -> Optional[str]:
        """
        Attempt to recover from a file read error.
        
        Recovery strategies:
        1. Try backup file if it exists
        2. Try auto-saved temporary file if it exists
        3. Check for partially downloaded files and repair if possible
        
        Args:
            file_path: Path to the file that couldn't be read
            error: The exception that was raised
            
        Returns:
            Alternative file path if recovery was successful
        """
        # Strategy 1: Check for backup file
        backup_file = f"{file_path}.bak"
        if os.path.exists(backup_file):
            logger.info(f"Found backup file: {backup_file}")
            return backup_file
            
        # Strategy 2: Check for auto-saved temp file
        temp_dir = tempfile.gettempdir()
        base_name = os.path.basename(file_path)
        auto_save_file = os.path.join(temp_dir, f"curve_editor_autosave_{base_name}")
        if os.path.exists(auto_save_file):
            logger.info(f"Found auto-save file: {auto_save_file}")
            return auto_save_file
            
        # Strategy 3: Check for partially downloaded files (for common formats)
        if file_path.endswith(('.json', '.txt')):
            try:
                partial_file = f"{file_path}.part"
                if os.path.exists(partial_file):
                    # Attempt to repair JSON file
                    if file_path.endswith('.json'):
                        repaired_path = ErrorRecovery._repair_json_file(partial_file)
                        if repaired_path:
                            return repaired_path
                    else:
                        # For text files, just use the partial file directly
                        logger.info(f"Using partial file: {partial_file}")
                        return partial_file
            except Exception as repair_error:
                logger.error(f"Failed to repair partial file: {repair_error}")
                
        logger.warning(f"No recovery options found for {file_path}")
        return None

    @staticmethod
    def _recover_file_write(file_path: str, error: Exception) -> Optional[str]:
        """
        Attempt to recover from a file write error.
        
        Recovery strategies:
        1. Try writing to a temporary file
        2. Check disk space and suggest cleanup if needed
        
        Args:
            file_path: Path to the file that couldn't be written
            error: The exception that was raised
            
        Returns:
            Alternative file path if recovery was successful
        """
        try:
            # Create a temp file in the same directory if possible
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                # If directory doesn't exist, use system temp directory
                dir_path = tempfile.gettempdir()
                
            base_name = os.path.basename(file_path)
            temp_file = os.path.join(dir_path, f"temp_{base_name}")
            
            # Ensure we can write to this location
            with open(temp_file, 'a') as f:
                f.write('')
                
            logger.info(f"Created alternative file for writing: {temp_file}")
            return temp_file
        except Exception as recovery_error:
            logger.error(f"Failed to create temporary file: {recovery_error}")
            
            # Check if disk space is the issue
            if ErrorRecovery._is_disk_space_issue(dir_path):
                logger.warning(f"Low disk space detected in {dir_path}")
                # Could trigger UI notification here
                
            return None

    @staticmethod
    def _repair_json_file(partial_file: str) -> Optional[str]:
        """
        Attempt to repair a partially downloaded/written JSON file.
        
        Args:
            partial_file: Path to the partial JSON file
            
        Returns:
            Path to repaired file if successful
        """
        try:
            with open(partial_file, 'r') as f:
                content = f.read().strip()
                
            # Add missing closing brackets if needed
            if content and content[-1] not in ['}', ']']:
                open_braces = content.count('{')
                close_braces = content.count('}')
                open_brackets = content.count('[')
                close_brackets = content.count(']')
                
                # Add missing closing braces and brackets
                content += '}' * (open_braces - close_braces)
                content += ']' * (open_brackets - close_brackets)
                
            # Validate JSON
            json.loads(content)
            
            # Write repaired content to new file
            repaired_file = f"{partial_file}_repaired"
            with open(repaired_file, 'w') as f:
                f.write(content)
                
            logger.info(f"Successfully repaired JSON file: {repaired_file}")
            return repaired_file
        except Exception as e:
            logger.error(f"Failed to repair JSON file: {e}")
            return None

    @staticmethod
    def _is_disk_space_issue(dir_path: str) -> bool:
        """
        Check if there's a disk space issue in the given directory.
        
        Args:
            dir_path: Directory to check
            
        Returns:
            True if disk space is low (less than 100MB)
        """
        try:
            if os.name == 'posix':
                # Unix/Linux/macOS
                stat = os.statvfs(dir_path)
                free_space = stat.f_frsize * stat.f_bavail
            else:
                # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(dir_path), None, None, 
                    ctypes.pointer(free_bytes)
                )
                free_space = free_bytes.value
                
            # Consider less than 100MB as low disk space
            return free_space < 100 * 1024 * 1024
        except Exception:
            # If we can't determine disk space, assume it's not the issue
            return False

    @staticmethod
    def recover_data_operation(data_type: str, data: Any, error: Exception) -> Optional[Any]:
        """
        Attempt to recover from a data operation error.
        
        Args:
            data_type: Type of data ('curve', 'settings', etc.)
            data: The data that caused the error
            error: The exception that was raised
            
        Returns:
            Recovered data if successful
        """
        logger.info(f"Attempting to recover {data_type} data")
        
        if data_type == 'curve':
            return ErrorRecovery._recover_curve_data(data, error)
        elif data_type == 'settings':
            return ErrorRecovery._recover_settings_data(data, error)
        else:
            logger.error(f"Unknown data type: {data_type}")
            return None

    @staticmethod
    def _recover_curve_data(data: List[Tuple], error: Exception) -> Optional[List[Tuple]]:
        """
        Attempt to recover curve data.
        
        Recovery strategies:
        1. Filter out invalid points
        2. Interpolate missing points
        3. Return a valid subset if possible
        
        Args:
            data: The curve data that caused the error
            error: The exception that was raised
            
        Returns:
            Recovered curve data if successful
        """
        try:
            if not data:
                return []
                
            # Filter out None or malformed points
            valid_data = [point for point in data if point and len(point) >= 3]
            
            if valid_data:
                logger.info(f"Recovered {len(valid_data)} valid points from {len(data)} total points")
                return valid_data
            else:
                logger.warning("Could not recover any valid points")
                return []
        except Exception as recovery_error:
            logger.error(f"Failed to recover curve data: {recovery_error}")
            return None

    @staticmethod
    def _recover_settings_data(data: Dict, error: Exception) -> Optional[Dict]:
        """
        Attempt to recover settings data.
        
        Recovery strategies:
        1. Remove invalid settings
        2. Reset to defaults for critical settings
        
        Args:
            data: The settings data that caused the error
            error: The exception that was raised
            
        Returns:
            Recovered settings data if successful
        """
        try:
            # Start with default critical settings
            default_critical = {
                "window_width": 1200,
                "window_height": 800,
                "recent_files": [],
                "recent_image_sequences": []
            }
            
            # If data is completely invalid, return defaults
            if not isinstance(data, dict):
                logger.warning("Settings data is not a dictionary, using defaults")
                return default_critical
                
            # Keep only valid entries
            valid_data = {}
            for key, value in data.items():
                # Skip entries with non-string keys
                if not isinstance(key, str):
                    continue
                    
                # Include valid entries
                valid_data[key] = value
                
            # Ensure critical settings exist
            for key, value in default_critical.items():
                if key not in valid_data:
                    valid_data[key] = value
                    
            logger.info(f"Recovered {len(valid_data)} valid settings")
            return valid_data
        except Exception as recovery_error:
            logger.error(f"Failed to recover settings data: {recovery_error}")
            return default_critical
