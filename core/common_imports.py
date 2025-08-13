#!/usr/bin/env python
"""
Common imports used across the CurveEditor codebase.

This module centralizes frequently used imports to reduce duplication
and ensure consistency across the application.
"""

# Standard library imports
import json
import logging
import os
import sys
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache, wraps
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Protocol,
    TypeGuard,
    TypeVar,
    cast,
    final,
    overload,
    runtime_checkable,
)

# Third-party imports
import numpy as np

# Export all for easy importing
__all__ = [
    # Standard library
    "logging",
    "json",
    "sys",
    "os",
    "Path",
    "Callable",
    "Sequence",
    "contextmanager",
    "dataclass",
    "Enum",
    "auto",
    "wraps",
    "lru_cache",
    # Typing
    "TYPE_CHECKING",
    "Any",
    "Optional",
    "Protocol",
    "TypeVar",
    "TypeGuard",
    "cast",
    "overload",
    "runtime_checkable",
    "final",
    # Third-party
    "np",
]
