#!/usr/bin/env python

"""
StatusManager: Centralized status management service for the Curve Editor.

This service provides a unified interface for all status display operations,
eliminating the need for manual status update calls throughout the codebase.
It implements an event-driven pattern where status updates happen automatically
when data changes.
"""

from typing import TYPE_CHECKING

from core.protocols import MainWindowProtocol
from services.logging_service import LoggingService

if TYPE_CHECKING:
    pass

# Configure logger for this module
logger = LoggingService.get_logger("status_manager")


class StatusManager:
    """
    Centralized status management service.

    This service provides a single point of control for all status display
    operations in the application. It automatically detects data state and
    updates the appropriate UI components.

    Key Features:
    - Automatic status detection based on loaded data
    - Consistent status messages across the application
    - Event-driven updates when data changes
    - Centralized error handling for status operations
    """

    @staticmethod
    def update_status(main_window: MainWindowProtocol) -> None:
        """
        Update all status displays based on current application state.

        This is the main entry point for status updates. It analyzes the current
        data state and updates all relevant UI components with appropriate messages.

        Args:
            main_window: The main application window instance
        """
        try:
            # Update the main status label
            StatusManager._update_status_label(main_window)

            # Update UI control states based on data availability
            StatusManager._update_control_states(main_window)

            logger.debug("Status update completed successfully")

        except Exception as e:
            logger.error(f"Error updating status: {e}")
            # Fallback to safe default state
            StatusManager._set_fallback_status(main_window)

    @staticmethod
    def _update_status_label(main_window: MainWindowProtocol) -> None:
        """
        Update the main status label with appropriate message.

        Args:
            main_window: The main application window instance
        """
        if not hasattr(main_window, "info_label"):
            return

        # Detect current data state
        curve_data_loaded = StatusManager._has_curve_data(main_window)
        image_data_loaded = StatusManager._has_image_data(main_window)

        # Set appropriate status message
        if curve_data_loaded and image_data_loaded:
            point_count = len(main_window.curve_data)
            main_window.info_label.setText(f"{point_count} points loaded")
            logger.debug(f"Status: {point_count} points with images")
        elif curve_data_loaded:
            point_count = len(main_window.curve_data)
            main_window.info_label.setText(f"{point_count} points loaded (no images)")
            logger.debug(f"Status: {point_count} points, no images")
        elif image_data_loaded:
            main_window.info_label.setText("Images loaded (no curve data)")
            logger.debug("Status: Images loaded, no curve data")
        else:
            main_window.info_label.setText("No data loaded")
            logger.debug("Status: No data loaded")

    @staticmethod
    def _update_control_states(main_window: MainWindowProtocol) -> None:
        """
        Update UI control enabled states based on data availability.

        Args:
            main_window: The main application window instance
        """
        curve_data_loaded = StatusManager._has_curve_data(main_window)
        image_data_loaded = StatusManager._has_image_data(main_window)

        # Enable/disable controls based on data availability
        # This can be extended to update other UI elements consistently

        # Example: Enable export button only when curve data is available
        if hasattr(main_window, "export_button"):
            main_window.export_button.setEnabled(curve_data_loaded)

        # Example: Enable view controls when any data is available
        any_data_loaded = curve_data_loaded or image_data_loaded
        if hasattr(main_window, "center_button"):
            main_window.center_button.setEnabled(any_data_loaded)
        if hasattr(main_window, "reset_zoom_button"):
            main_window.reset_zoom_button.setEnabled(any_data_loaded)

    @staticmethod
    def _has_curve_data(main_window: MainWindowProtocol) -> bool:
        """
        Check if curve data is loaded and valid.

        Args:
            main_window: The main application window instance

        Returns:
            bool: True if valid curve data is loaded
        """
        return bool(hasattr(main_window, "curve_data") and main_window.curve_data and len(main_window.curve_data) > 0)

    @staticmethod
    def _has_image_data(main_window: MainWindowProtocol) -> bool:
        """
        Check if image data is loaded and valid.

        Args:
            main_window: The main application window instance

        Returns:
            bool: True if valid image data is loaded
        """
        return bool(
            hasattr(main_window, "curve_view")
            and hasattr(main_window.curve_view, "background_image")
            and main_window.curve_view.background_image is not None
            and not main_window.curve_view.background_image.isNull()
        )

    @staticmethod
    def _set_fallback_status(main_window: MainWindowProtocol) -> None:
        """
        Set fallback status when error occurs during status update.

        Args:
            main_window: The main application window instance
        """
        if hasattr(main_window, "info_label"):
            main_window.info_label.setText("Status update error")
            logger.warning("Using fallback status due to error")

    @staticmethod
    def on_curve_data_loaded(main_window: MainWindowProtocol) -> None:
        """
        Handle curve data loading event.

        This method should be called whenever curve data is loaded or changed.
        It provides a semantic interface for status updates based on specific events.

        Args:
            main_window: The main application window instance
        """
        logger.debug("Curve data loaded event triggered")
        StatusManager.update_status(main_window)

    @staticmethod
    def on_image_data_loaded(main_window: MainWindowProtocol) -> None:
        """
        Handle image data loading event.

        This method should be called whenever image data is loaded or changed.

        Args:
            main_window: The main application window instance
        """
        logger.debug("Image data loaded event triggered")
        StatusManager.update_status(main_window)

    @staticmethod
    def on_data_cleared(main_window: MainWindowProtocol) -> None:
        """
        Handle data clearing event.

        This method should be called whenever data is cleared or reset.

        Args:
            main_window: The main application window instance
        """
        logger.debug("Data cleared event triggered")
        StatusManager.update_status(main_window)

    @staticmethod
    def on_error_occurred(main_window: MainWindowProtocol, error_message: str) -> None:
        """
        Handle error event with custom status message.

        Args:
            main_window: The main application window instance
            error_message: Error message to display
        """
        logger.debug(f"Error event triggered: {error_message}")
        if hasattr(main_window, "info_label"):
            main_window.info_label.setText(f"Error: {error_message}")
