#!/usr/bin/env python
"""
Error Recovery Manager for CurveEditor.

Provides graceful error handling, alternative path suggestions,
and user-friendly error messages for the image sequence browser.
"""

import os
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from core.logger_utils import get_logger

logger = get_logger("error_recovery_manager")


class ErrorType(Enum):
    """Types of errors that can occur during image sequence browsing."""

    PERMISSION_DENIED = "permission_denied"
    DIRECTORY_NOT_FOUND = "directory_not_found"
    NETWORK_TIMEOUT = "network_timeout"
    INVALID_PATH = "invalid_path"
    NO_SEQUENCES_FOUND = "no_sequences_found"
    SCAN_INTERRUPTED = "scan_interrupted"
    DISK_FULL = "disk_full"
    CORRUPTED_FILES = "corrupted_files"


class RecoveryAction(NamedTuple):
    """Represents a recovery action for an error."""

    action_type: str  # "retry", "alternative_path", "manual_browse", "ignore"
    message: str      # User-friendly message
    data: dict        # Additional data for the action


class ErrorRecoveryManager:
    """
    Manages error recovery for image sequence browsing operations.

    Provides user-friendly error messages, suggests alternative paths,
    and offers recovery actions for various error scenarios.
    """

    def __init__(self):
        """Initialize error recovery manager."""
        self._common_directories = self._get_common_directories()
        self._network_drive_patterns = ['\\\\', '//', 'smb://', 'ftp://']

    def _get_common_directories(self) -> list[Path]:
        """Get list of common directories that might contain image sequences."""
        common_dirs = []

        # User directories
        home = Path.home()
        common_dirs.extend([
            home / "Documents",
            home / "Desktop",
            home / "Pictures",
            home / "Downloads",
        ])

        # System-specific directories
        if os.name == 'nt':  # Windows
            # Common Windows locations
            common_dirs.extend([
                Path("C:/Users/Public/Documents"),
                Path("C:/Users/Public/Pictures"),
                Path("D:/"),  # Common secondary drive
            ])
        else:  # Unix-like
            common_dirs.extend([
                Path("/tmp"),
                Path("/usr/local/share"),
                Path("/opt"),
            ])

        # Filter to existing directories
        return [d for d in common_dirs if d.exists() and d.is_dir()]

    def handle_directory_access_error(self, path: str, error: Exception) -> RecoveryAction:
        """
        Handle directory access errors and suggest recovery actions.

        Args:
            path: Directory path that failed
            error: Exception that occurred

        Returns:
            RecoveryAction with suggested recovery
        """
        error_type = self._classify_error(error)

        if error_type == ErrorType.PERMISSION_DENIED:
            return self._handle_permission_error(path)
        elif error_type == ErrorType.DIRECTORY_NOT_FOUND:
            return self._handle_not_found_error(path)
        elif error_type == ErrorType.NETWORK_TIMEOUT:
            return self._handle_network_error(path)
        elif error_type == ErrorType.INVALID_PATH:
            return self._handle_invalid_path_error(path)
        else:
            return self._handle_generic_error(path, error)

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type based on exception."""
        if isinstance(error, PermissionError):
            return ErrorType.PERMISSION_DENIED
        elif isinstance(error, FileNotFoundError):
            return ErrorType.DIRECTORY_NOT_FOUND
        elif isinstance(error, OSError):
            # Check for network-related errors
            error_msg = str(error).lower()
            if any(keyword in error_msg for keyword in ['network', 'timeout', 'unreachable']):
                return ErrorType.NETWORK_TIMEOUT
            elif 'no space' in error_msg or 'disk full' in error_msg:
                return ErrorType.DISK_FULL
            else:
                return ErrorType.INVALID_PATH
        else:
            return ErrorType.INVALID_PATH

    def _handle_permission_error(self, path: str) -> RecoveryAction:
        """Handle permission denied errors."""
        message = (
            f"Permission denied accessing '{path}'.\n\n"
            "This directory requires administrator privileges or you don't have read access.\n"
            "Try selecting a different directory or contact your system administrator."
        )

        alternatives = self.suggest_alternative_paths(path)

        return RecoveryAction(
            action_type="alternative_path",
            message=message,
            data={
                "alternatives": alternatives,
                "can_retry": False,
                "suggested_action": "Choose a different directory"
            }
        )

    def _handle_not_found_error(self, path: str) -> RecoveryAction:
        """Handle directory not found errors."""
        # Check if it's a network path
        is_network = any(pattern in path for pattern in self._network_drive_patterns)

        if is_network:
            message = (
                f"Network location '{path}' is not accessible.\n\n"
                "The network drive may be disconnected or the server is unavailable.\n"
                "Check your network connection and try again."
            )
            can_retry = True
        else:
            message = (
                f"Directory '{path}' does not exist.\n\n"
                "The directory may have been moved, renamed, or deleted.\n"
                "Please select a different directory."
            )
            can_retry = False

        alternatives = self.suggest_alternative_paths(path)

        return RecoveryAction(
            action_type="alternative_path" if alternatives else "manual_browse",
            message=message,
            data={
                "alternatives": alternatives,
                "can_retry": can_retry,
                "is_network": is_network,
                "suggested_action": "Retry connection" if can_retry else "Choose different directory"
            }
        )

    def _handle_network_error(self, path: str) -> RecoveryAction:
        """Handle network timeout errors."""
        message = (
            f"Network timeout accessing '{path}'.\n\n"
            "The network location is taking too long to respond.\n"
            "This could be due to a slow connection or server issues.\n\n"
            "You can try again or select a local directory."
        )

        alternatives = [d for d in self._common_directories if not self._is_network_path(str(d))]

        return RecoveryAction(
            action_type="retry",
            message=message,
            data={
                "alternatives": [str(d) for d in alternatives],
                "can_retry": True,
                "timeout_seconds": 30,
                "suggested_action": "Retry with longer timeout"
            }
        )

    def _handle_invalid_path_error(self, path: str) -> RecoveryAction:
        """Handle invalid path errors."""
        message = (
            f"Invalid path format: '{path}'.\n\n"
            "The path contains invalid characters or has an incorrect format.\n"
            "Please enter a valid directory path."
        )

        # Try to suggest a corrected path
        corrected_path = self._suggest_path_correction(path)
        alternatives = [corrected_path] if corrected_path else []
        alternatives.extend(str(d) for d in self._common_directories[:3])

        return RecoveryAction(
            action_type="alternative_path",
            message=message,
            data={
                "alternatives": alternatives,
                "can_retry": False,
                "corrected_path": corrected_path,
                "suggested_action": "Enter valid path"
            }
        )

    def _handle_generic_error(self, path: str, error: Exception) -> RecoveryAction:
        """Handle generic errors."""
        message = (
            f"Error accessing '{path}': {str(error)}\n\n"
            "An unexpected error occurred while accessing this directory.\n"
            "Please try a different directory or contact support if the problem persists."
        )

        alternatives = self.suggest_alternative_paths(path)

        return RecoveryAction(
            action_type="alternative_path",
            message=message,
            data={
                "alternatives": alternatives,
                "can_retry": True,
                "error_details": str(error),
                "suggested_action": "Try different directory"
            }
        )

    def suggest_alternative_paths(self, failed_path: str) -> list[str]:
        """
        Suggest alternative paths when a path fails.

        Args:
            failed_path: Path that failed to access

        Returns:
            List of alternative path suggestions
        """
        alternatives = []

        try:
            failed_path_obj = Path(failed_path)

            # Try parent directories
            parent = failed_path_obj.parent
            while parent != parent.parent:  # Stop at root
                if parent.exists() and parent.is_dir():
                    alternatives.append(str(parent))
                    break
                parent = parent.parent

            # Try sibling directories
            if failed_path_obj.parent.exists():
                try:
                    for sibling in failed_path_obj.parent.iterdir():
                        if (sibling.is_dir() and
                            sibling.name != failed_path_obj.name and
                            len(alternatives) < 3):
                            alternatives.append(str(sibling))
                except (PermissionError, OSError):
                    pass

            # Add common directories if we don't have enough alternatives
            if len(alternatives) < 3:
                for common_dir in self._common_directories:
                    if str(common_dir) not in alternatives:
                        alternatives.append(str(common_dir))
                        if len(alternatives) >= 5:
                            break

        except Exception as e:
            logger.warning(f"Failed to suggest alternatives for {failed_path}: {e}")

        return alternatives

    def _suggest_path_correction(self, invalid_path: str) -> str | None:
        """
        Suggest a corrected version of an invalid path.

        Args:
            invalid_path: Invalid path string

        Returns:
            Corrected path or None if no correction possible
        """
        try:
            # Common corrections
            corrected = invalid_path.strip()

            # Fix common Windows path issues
            if os.name == 'nt':
                # Replace forward slashes with backslashes
                corrected = corrected.replace('/', '\\')

                # Add drive letter if missing
                if corrected.startswith('\\') and not corrected.startswith('\\\\'):
                    corrected = 'C:' + corrected
            else:
                # Fix common Unix path issues
                corrected = corrected.replace('\\', '/')

                # Ensure absolute path starts with /
                if not corrected.startswith('/') and not corrected.startswith('~'):
                    corrected = '/' + corrected

            # Expand user directory
            corrected = os.path.expanduser(corrected)

            # Check if corrected path exists
            if Path(corrected).exists():
                return corrected

        except Exception:
            pass

        return None

    def _is_network_path(self, path: str) -> bool:
        """Check if path is a network path."""
        return any(pattern in path for pattern in self._network_drive_patterns)

    def provide_user_guidance(self, error_type: ErrorType) -> str:
        """
        Provide user guidance for specific error types.

        Args:
            error_type: Type of error

        Returns:
            User-friendly guidance message
        """
        guidance_messages = {
            ErrorType.PERMISSION_DENIED: (
                "Permission Issues:\n"
                "• Try selecting a directory in your user folder (Documents, Desktop, etc.)\n"
                "• Contact your administrator if you need access to restricted folders\n"
                "• Make sure the directory isn't being used by another application"
            ),
            ErrorType.DIRECTORY_NOT_FOUND: (
                "Directory Not Found:\n"
                "• Check that the path is typed correctly\n"
                "• Verify the directory hasn't been moved or deleted\n"
                "• For network drives, ensure you're connected to the network"
            ),
            ErrorType.NETWORK_TIMEOUT: (
                "Network Issues:\n"
                "• Check your network connection\n"
                "• Try accessing the location through File Explorer first\n"
                "• Consider copying files to a local directory for better performance"
            ),
            ErrorType.INVALID_PATH: (
                "Invalid Path Format:\n"
                "• Use forward slashes (/) or backslashes (\\) as appropriate\n"
                "• Avoid special characters like < > | ? * \"\n"
                "• Make sure the path starts from a valid drive or root directory"
            ),
            ErrorType.NO_SEQUENCES_FOUND: (
                "No Image Sequences Found:\n"
                "• Make sure the directory contains numbered image files\n"
                "• Supported formats: JPG, PNG, EXR, DPX, TIFF, etc.\n"
                "• Files should follow naming patterns like 'name_001.jpg' or 'render.0001.exr'"
            ),
        }

        return guidance_messages.get(error_type, "Please try a different approach or contact support.")

    def get_recovery_suggestions(self, path: str, error_type: ErrorType) -> list[str]:
        """
        Get specific recovery suggestions for a path and error type.

        Args:
            path: Failed path
            error_type: Type of error that occurred

        Returns:
            List of recovery suggestions
        """
        suggestions = []

        if error_type == ErrorType.PERMISSION_DENIED:
            suggestions.extend([
                "Try running the application as administrator",
                "Select a directory in your user folder",
                "Check folder permissions in Properties"
            ])

        elif error_type == ErrorType.NETWORK_TIMEOUT:
            suggestions.extend([
                "Check network connection",
                "Try accessing through File Explorer first",
                "Copy files to local directory",
                "Increase network timeout settings"
            ])

        elif error_type == ErrorType.DIRECTORY_NOT_FOUND:
            suggestions.extend([
                "Verify the path is correct",
                "Check if directory was moved or renamed",
                "Browse to the directory manually"
            ])

        # Add common suggestions
        suggestions.extend([
            "Use the Browse button to select directory",
            "Try a different directory",
            "Contact support if problem persists"
        ])

        return suggestions[:5]  # Limit to 5 suggestions
