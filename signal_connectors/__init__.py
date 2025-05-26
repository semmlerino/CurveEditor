#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal Connectors Package for 3DE4 Curve Editor.

This package contains modular signal connector classes that handle
different aspects of signal connections in the application.
"""

from .edit_signal_connector import EditSignalConnector
from .file_signal_connector import FileSignalConnector
from .shortcut_signal_connector import ShortcutSignalConnector
from .ui_signal_connector import UISignalConnector
from .view_signal_connector import ViewSignalConnector
from .visualization_signal_connector import VisualizationSignalConnector

__all__ = [
    'EditSignalConnector',
    'FileSignalConnector',
    'ShortcutSignalConnector',
    'UISignalConnector',
    'ViewSignalConnector',
    'VisualizationSignalConnector',
]
