#!/usr/bin/env python
"""
Animation and theme utilities for the CurveEditor UI.

This module consolidates common animation patterns and theme-related
utilities to reduce code duplication across UI components.
"""

from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, SignalInstance
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QWidget

from ui.ui_constants import ANIMATION, COLORS_DARK, COLORS_LIGHT


class FrameNavigationWidget(Protocol):
    """Protocol for widgets with frame navigation buttons."""

    first_btn: QWidget
    prev_btn: QWidget
    next_btn: QWidget
    last_btn: QWidget


class AnimationFactory:
    """Factory for creating common animation patterns."""

    @staticmethod
    def create_shadow_effect(
        blur_radius: int = 15,
        x_offset: int = 0,
        y_offset: int = 2,
        color: str | None = None,
    ) -> QGraphicsDropShadowEffect:
        """
        Create a standardized drop shadow effect.

        Args:
            blur_radius: Blur radius for the shadow (default: 15)
            x_offset: Horizontal offset (default: 0)
            y_offset: Vertical offset (default: 2)
            color: Shadow color as hex string (optional)

        Returns:
            Configured QGraphicsDropShadowEffect
        """
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setXOffset(x_offset)
        shadow.setYOffset(y_offset)
        if color:
            from PySide6.QtGui import QColor

            shadow.setColor(QColor(color))
        return shadow

    @staticmethod
    def create_opacity_animation(
        widget: QWidget,
        duration: str = "normal",
        start_value: float = 0.0,
        end_value: float = 1.0,
        easing: QEasingCurve.Type = QEasingCurve.Type.InOutQuad,
    ) -> tuple[QGraphicsOpacityEffect, QPropertyAnimation]:
        """
        Create an opacity animation for a widget.

        Args:
            widget: Widget to animate
            duration: Duration key from ANIMATION dict ("fast", "normal", "slow")
            start_value: Starting opacity (0.0 to 1.0)
            end_value: Ending opacity (0.0 to 1.0)
            easing: Easing curve type

        Returns:
            Tuple of (opacity_effect, animation)
        """
        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(ANIMATION[f"duration_{duration}"])
        animation.setStartValue(start_value)
        animation.setEndValue(end_value)
        animation.setEasingCurve(easing)

        return opacity_effect, animation

    @staticmethod
    def create_property_animation(
        target: QWidget,
        property_name: bytes,
        duration: str = "normal",
        easing: QEasingCurve.Type = QEasingCurve.Type.InOutQuad,
    ) -> QPropertyAnimation:
        """
        Create a standardized property animation.

        Args:
            target: Target widget
            property_name: Property to animate (e.g., b"geometry", b"pos")
            duration: Duration key from ANIMATION dict ("fast", "normal", "slow")
            easing: Easing curve type

        Returns:
            Configured QPropertyAnimation
        """
        animation = QPropertyAnimation(target, property_name)
        animation.setDuration(ANIMATION[f"duration_{duration}"])
        animation.setEasingCurve(easing)
        return animation


class ThemeUtils:
    """Utilities for theme-related operations."""

    @staticmethod
    def get_theme_colors(theme: str) -> dict[str, str]:
        """
        Get the appropriate color palette for the given theme.

        Args:
            theme: Theme name ("dark" or "light")

        Returns:
            Color dictionary for the theme
        """
        return COLORS_DARK if theme == "dark" else COLORS_LIGHT

    @staticmethod
    def apply_shadow_for_theme(widget: QWidget, theme: str, blur_radius: int = 15) -> None:
        """
        Apply a theme-appropriate shadow to a widget.

        Args:
            widget: Widget to apply shadow to
            theme: Current theme ("dark" or "light")
            blur_radius: Shadow blur radius
        """
        colors = ThemeUtils.get_theme_colors(theme)
        shadow_color = colors.get("shadow", "#000000")
        shadow = AnimationFactory.create_shadow_effect(
            blur_radius=blur_radius,
            color=shadow_color,
        )
        widget.setGraphicsEffect(shadow)


class SignalConnectionUtils:
    """Utilities for common signal connection patterns."""

    @staticmethod
    def connect_to_frame_update(
        widget: object,  # Widget with navigation buttons - using object to handle different widget types
        callback: Callable[[int], None],
        min_frame: int,
        max_frame: int,
    ) -> None:
        """
        Connect frame navigation buttons with lambda patterns.

        Args:
            widget: Widget with first_btn, prev_btn, next_btn, last_btn attributes
            callback: Frame update callback function
            min_frame: Minimum frame value
            max_frame: Maximum frame value
        """
        if getattr(widget, "first_btn", None) is not None:
            widget.first_btn.clicked.connect(lambda: callback(min_frame))
        if getattr(widget, "last_btn", None) is not None:
            widget.last_btn.clicked.connect(lambda: callback(max_frame))
        if getattr(widget, "prev_btn", None) is not None:
            # Note: This logic seems incorrect - callback should not be called to get current frame
            # Using min_frame as fallback for now
            widget.prev_btn.clicked.connect(lambda: callback(max(min_frame, min_frame - 1)))
        if getattr(widget, "next_btn", None) is not None:
            # Note: This logic seems incorrect - callback should not be called to get current frame
            # Using max_frame as fallback for now
            widget.next_btn.clicked.connect(lambda: callback(min(max_frame, max_frame + 1)))

    @staticmethod
    def connect_with_lambda(signal: SignalInstance, callback: Callable[..., object], *args: object) -> object:
        """
        Connect a signal with a lambda wrapper.

        Args:
            signal: Signal to connect
            callback: Callback function
            *args: Arguments to pass to callback

        Returns:
            The connection object
        """
        return signal.connect(lambda: callback(*args))
