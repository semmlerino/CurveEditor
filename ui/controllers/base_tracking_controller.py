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
        self._app_state: ApplicationState = get_application_state()

        logger.debug(f"{self.__class__.__name__} base initialization complete")
