"""
Session Manager for CurveEditor.

Handles saving and loading of application session state to provide
automatic restoration of previously loaded files and settings.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages session persistence for the CurveEditor application.

    Saves and loads session data including last loaded files, view state,
    frame position, and other user preferences to maintain continuity
    between application sessions.
    """

    def __init__(self, project_root: Path | None = None):
        """
        Initialize the session manager.

        Args:
            project_root: Root directory of the project. If None, determined automatically.
        """
        self.project_root = project_root or self._find_project_root()
        self.session_dir = self.project_root / "session"
        self.session_file = self.session_dir / "last_session.json"

        # Ensure session directory exists
        self.session_dir.mkdir(exist_ok=True)

        logger.info(f"SessionManager initialized with session file: {self.session_file}")

    def _find_project_root(self) -> Path:
        """Find the project root directory (directory containing main.py)."""
        current_dir = Path(__file__).parent
        while current_dir.parent != current_dir:  # Stop at filesystem root
            if (current_dir / "main.py").exists():
                return current_dir
            current_dir = current_dir.parent

        # Fallback to current directory if main.py not found
        logger.warning("Could not find main.py, using current directory as project root")
        return Path.cwd()

    def _make_relative_path(self, file_path: str) -> str:
        """
        Convert absolute path to relative path if file is within project tree.

        Args:
            file_path: Absolute file path

        Returns:
            Relative path if within project, otherwise absolute path
        """
        try:
            abs_path = Path(file_path).resolve()
            project_root_abs = self.project_root.resolve()

            # Check if file is within project directory
            if abs_path.is_relative_to(project_root_abs):
                relative_path = abs_path.relative_to(project_root_abs)
                logger.debug(f"Converted to relative path: {relative_path}")
                return relative_path.as_posix()  # Use POSIX format for cross-platform compatibility
            else:
                logger.debug(f"File outside project, keeping absolute path: {abs_path}")
                return abs_path.as_posix()  # Use POSIX format for cross-platform compatibility
        except (ValueError, OSError) as e:
            logger.warning(f"Error making relative path for {file_path}: {e}")
            return file_path

    def _resolve_path(self, path: str) -> str | None:
        """
        Resolve a stored path (relative or absolute) to an absolute path.

        Args:
            path: Stored path (relative or absolute)

        Returns:
            Absolute path if file exists, None otherwise
        """
        try:
            # Normalize Windows backslashes to forward slashes for cross-platform compatibility
            normalized_path = path.replace("\\", "/")
            stored_path = Path(normalized_path)

            if stored_path.is_absolute():
                # Already absolute path
                resolved_path = stored_path
            else:
                # Relative path - resolve against project root
                resolved_path = (self.project_root / stored_path).resolve()

            if resolved_path.exists():
                logger.debug(f"Resolved path: {path} -> {resolved_path}")
                return str(resolved_path)
            else:
                logger.warning(f"Stored path no longer exists: {resolved_path}")
                return None

        except (ValueError, OSError) as e:
            logger.warning(f"Error resolving path {path}: {e}")
            return None

    def save_session(self, session_data: dict[str, Any]) -> bool:
        """
        Save session data to file.

        Args:
            session_data: Dictionary containing session state

        Returns:
            True if save successful, False otherwise
        """
        # Check if session persistence is disabled
        if os.environ.get("CURVE_EDITOR_NO_SESSION", "").lower() == "true":
            logger.info("Session persistence disabled by environment variable")
            return True

        try:
            # Process file paths to make them relative when possible
            processed_data = session_data.copy()

            if "tracking_file" in processed_data and processed_data["tracking_file"]:
                processed_data["tracking_file"] = self._make_relative_path(processed_data["tracking_file"])

            if "image_directory" in processed_data and processed_data["image_directory"]:
                processed_data["image_directory"] = self._make_relative_path(processed_data["image_directory"])

            # Save recent directories
            if "recent_directories" in processed_data and processed_data["recent_directories"]:
                # Make paths relative where possible
                processed_data["recent_directories"] = [
                    self._make_relative_path(path) for path in processed_data["recent_directories"]
                ]

            # Add metadata
            processed_data["_metadata"] = {"saved_at": str(Path.cwd().resolve()), "version": "1.0"}

            # Write session data
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Session saved successfully to {self.session_file}")
            return True

        except (OSError, TypeError, ValueError) as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session(self) -> dict[str, Any] | None:
        """
        Load session data from file.

        Returns:
            Dictionary containing session state, or None if load failed
        """
        # Check if session clearing is requested
        if os.environ.get("CURVE_EDITOR_CLEAR_SESSION", "").lower() == "true":
            logger.info("Session clearing requested by environment variable")
            self.clear_session()
            return None

        # Check if session persistence is disabled
        if os.environ.get("CURVE_EDITOR_NO_SESSION", "").lower() == "true":
            logger.info("Session persistence disabled by environment variable")
            return None

        if not self.session_file.exists():
            logger.info("No session file found")
            return None

        try:
            with open(self.session_file, encoding="utf-8") as f:
                session_data = json.load(f)

            # Validate and resolve file paths
            if "tracking_file" in session_data and session_data["tracking_file"]:
                resolved_path = self._resolve_path(session_data["tracking_file"])
                if resolved_path:
                    session_data["tracking_file"] = resolved_path
                else:
                    logger.warning("Stored tracking file no longer exists")
                    session_data["tracking_file"] = None

            if "image_directory" in session_data and session_data["image_directory"]:
                resolved_path = self._resolve_path(session_data["image_directory"])
                if resolved_path and Path(resolved_path).is_dir():
                    session_data["image_directory"] = resolved_path
                else:
                    logger.warning("Stored image directory no longer exists")
                    session_data["image_directory"] = None

            # Load recent directories
            if "recent_directories" in session_data and isinstance(session_data["recent_directories"], list):
                resolved_recents = []
                for path in session_data["recent_directories"]:
                    resolved = self._resolve_path(path)
                    if resolved and Path(resolved).exists():
                        resolved_recents.append(resolved)
                session_data["recent_directories"] = resolved_recents

            logger.info(f"Session loaded successfully from {self.session_file}")
            return session_data

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def clear_session(self) -> bool:
        """
        Clear the current session file.

        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.info("Session file cleared")
            return True
        except OSError as e:
            logger.error(f"Failed to clear session: {e}")
            return False

    def has_session(self) -> bool:
        """
        Check if a valid session file exists.

        Returns:
            True if session file exists and is readable
        """
        return self.session_file.exists() and self.session_file.is_file()

    def create_session_data(
        self,
        tracking_file: str | None = None,
        image_directory: str | None = None,
        current_frame: int = 1,
        zoom_level: float = 1.0,
        pan_offset: tuple[float, float] = (0.0, 0.0),
        window_geometry: tuple[int, int, int, int] | None = None,
        active_points: list[str] | None = None,
        view_bounds: tuple[float, float, float, float] | None = None,
        recent_directories: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a session data dictionary with the provided values.

        Args:
            tracking_file: Path to last loaded tracking file
            image_directory: Path to last loaded image directory
            current_frame: Current frame number
            zoom_level: Current zoom level
            pan_offset: Current pan offset (x, y)
            window_geometry: Window geometry (x, y, width, height)
            active_points: List of active point names (for multi-point tracking)
            view_bounds: View bounds (min_x, min_y, max_x, max_y)
            recent_directories: List of recently visited directories

        Returns:
            Dictionary containing session data
        """
        return {
            "tracking_file": tracking_file,
            "image_directory": image_directory,
            "current_frame": current_frame,
            "zoom_level": zoom_level,
            "pan_offset": list(pan_offset),
            "window_geometry": list(window_geometry) if window_geometry else None,
            "active_points": active_points or [],
            "view_bounds": list(view_bounds) if view_bounds else None,
            "recent_directories": recent_directories if recent_directories else [],
        }

    def restore_session_state(self, main_window: Any, session_data: dict[str, Any]) -> None:
        """Restore application state from session data.

        Args:
            main_window: Reference to the main window
            session_data: Session data dictionary to restore from
        """
        try:
            # Extract file paths
            tracking_file = session_data.get("tracking_file")
            image_directory = session_data.get("image_directory")

            # Restore frame position
            current_frame = session_data.get("current_frame", 1)

            # Restore view state
            zoom_level = session_data.get("zoom_level", 1.0)
            pan_offset = tuple(session_data.get("pan_offset", [0.0, 0.0]))

            # Restore active points for multi-point data
            active_points = session_data.get("active_points", [])

            # Restore recent directories
            if "recent_directories" in session_data and isinstance(session_data["recent_directories"], list):
                if hasattr(main_window, "state_manager") and hasattr(
                    main_window.state_manager, "set_recent_directories"
                ):
                    main_window.state_manager.set_recent_directories(session_data["recent_directories"])

            # Load files using background thread if available
            if hasattr(main_window, "file_load_worker") and main_window.file_load_worker:
                logger.info("Loading session files via background thread")
                main_window.file_load_worker.start_work(tracking_file, image_directory)

                # Store session data to restore state after files are loaded
                main_window._pending_session_data = {
                    "current_frame": current_frame,
                    "zoom_level": zoom_level,
                    "pan_offset": pan_offset,
                    "active_points": active_points,
                }
            else:
                # Fallback to direct loading if no worker available
                logger.warning("No file load worker available, using direct loading")
                if tracking_file and hasattr(main_window, "file_operations_manager"):
                    # Simulate file opened event for session restoration
                    main_window.file_operations_manager.open_file()

        except Exception as e:
            logger.error(f"Failed to restore session state: {e}")
            # Fallback to burger data on error
            if hasattr(main_window, "file_operations_manager"):
                main_window.file_operations_manager.load_burger_tracking_data()

    def load_session_or_fallback(self, main_window: Any) -> None:
        """Load session data if available, otherwise fallback to burger data.

        Args:
            main_window: Reference to the main window
        """
        # Try to load session data first
        session_data = self.load_session()

        if session_data:
            logger.info("Loading files from session data")
            self.restore_session_state(main_window, session_data)
        else:
            logger.info("No session found, falling back to burger data")
            if hasattr(main_window, "file_operations_manager"):
                main_window.file_operations_manager.load_burger_tracking_data()
