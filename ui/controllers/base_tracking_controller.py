"""Base class for tracking-related controllers.

This module provides a common base class for all tracking controllers,
establishing consistent initialization patterns and reducing code duplication.
"""

import logging

from PySide6.QtCore import QObject

from protocols.ui import MainWindowProtocol
from stores.application_state import ApplicationState, get_application_state

logger = logging.getLogger(__name__)


class BaseTrackingController(QObject):
    """Base class for tracking-related controllers.

    Provides common initialization pattern:
    - Stores main_window reference
    - Initializes ApplicationState connection
    - Sets up logging
    """

    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize base tracking controller.

        Args:
            main_window: Main window protocol interface
        """
        super().__init__()
        self.main_window: MainWindowProtocol = main_window
        # NOTE: Do not cache ApplicationState reference - it can be reset between tests
        # Use the _app_state property below instead, which gets fresh instance each time

        logger.debug(f"{self.__class__.__name__} base initialization complete")

    @property
    def _app_state(self) -> ApplicationState:
        """Get current ApplicationState instance (fresh every time for test isolation).

        This is a property to ensure we always get the current singleton instance,
        even if it's been reset between tests. Do not override with a cached attribute.
        """
        return get_application_state()
