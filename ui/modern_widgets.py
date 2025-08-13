#!/usr/bin/env python
"""
Modern Widget Components for CurveEditor
Custom widgets with modern design patterns and enhanced user experience
"""

from PySide6.QtCore import Property, QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ModernCard(QFrame):
    """Modern card widget with shadow and hover effects."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("modernCard")
        self.title = title
        self._hover = False
        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self):
        """Setup the card UI with modern styling."""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setContentsMargins(0, 0, 0, 0)

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(16, 16, 16, 16)

        # Title label if provided
        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setObjectName("cardTitle")
            self.title_label.setStyleSheet("""
                QLabel#cardTitle {
                    font-size: 16px;
                    font-weight: 600;
                    color: #212529;
                    padding-bottom: 8px;
                }
            """)
            self.main_layout.addWidget(self.title_label)

        # Content area
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)

    def _setup_animations(self):
        """Setup hover animations."""
        self.shadow_animation = QPropertyAnimation(self, b"pos")
        self.shadow_animation.setDuration(200)
        self.shadow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def addWidget(self, widget: QWidget):
        """Add widget to card content area."""
        self.content_layout.addWidget(widget)

    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """Custom paint for modern card appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw shadow
        if self._hover:
            shadow_color = QColor(0, 0, 0, 40)
        else:
            shadow_color = QColor(0, 0, 0, 20)

        shadow_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRoundedRect(shadow_rect, 8, 8)

        # Draw card background
        card_rect = self.rect().adjusted(0, 0, -4, -4)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRoundedRect(card_rect, 8, 8)

        super().paintEvent(event)


class ModernButton(QPushButton):
    """Modern button with animations and multiple variants."""

    def __init__(self, text: str = "", variant: str = "primary", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self._animation_progress = 0
        self._setup_style()
        self._setup_animations()

    def _setup_style(self):
        """Apply variant-specific styling."""
        base_style = """
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                font-size: 14px;
                min-height: 36px;
            }
        """

        variant_styles = {
            "primary": """
                QPushButton {
                    background-color: #007bff;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """,
            "secondary": """
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #545b62;
                }
            """,
            "success": """
                QPushButton {
                    background-color: #28a745;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """,
            "outline": """
                QPushButton {
                    background-color: transparent;
                    color: #007bff;
                    border: 2px solid #007bff;
                }
                QPushButton:hover {
                    background-color: #007bff;
                    color: white;
                }
            """,
        }

        self.setStyleSheet(base_style + variant_styles.get(self.variant, variant_styles["primary"]))

    def _setup_animations(self):
        """Setup click ripple animation."""
        self.click_animation = QPropertyAnimation(self, b"_animation_progress")
        self.click_animation.setDuration(300)
        self.click_animation.setStartValue(0)
        self.click_animation.setEndValue(100)
        self.click_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def mousePressEvent(self, event):
        """Trigger animation on click."""
        self.click_position = event.pos()
        self.click_animation.start()
        super().mousePressEvent(event)

    @Property(int)
    def _animation_progress(self):
        return self.__animation_progress

    @_animation_progress.setter
    def _animation_progress(self, value):
        self.__animation_progress = value
        self.update()


class ModernProgressBar(QWidget):
    """Custom progress bar with modern design."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max_value = 100
        self._text = ""
        self._color = QColor("#007bff")
        self.setFixedHeight(24)

    def setValue(self, value: int):
        """Set progress value."""
        self._value = min(value, self._max_value)
        self.update()

    def setMaximum(self, maximum: int):
        """Set maximum value."""
        self._max_value = maximum
        self.update()

    def setText(self, text: str):
        """Set progress text."""
        self._text = text
        self.update()

    def setColor(self, color: QColor):
        """Set progress bar color."""
        self._color = color
        self.update()

    def paintEvent(self, event):
        """Custom paint for modern progress bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#e9ecef")))
        painter.drawRoundedRect(bg_rect, 12, 12)

        # Progress
        if self._max_value > 0:
            progress = self._value / self._max_value
            progress_width = int(bg_rect.width() * progress)

            if progress_width > 0:
                progress_rect = QRect(0, 0, progress_width, bg_rect.height())

                # Gradient effect
                gradient = QLinearGradient(0, 0, progress_width, 0)
                gradient.setColorAt(0, self._color)
                gradient.setColorAt(1, self._color.lighter(120))

                painter.setBrush(QBrush(gradient))
                painter.drawRoundedRect(progress_rect, 12, 12)

        # Text
        if self._text:
            painter.setPen(QPen(QColor("#212529")))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, self._text)


class ModernLoadingSpinner(QWidget):
    """Animated loading spinner widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._color = QColor("#007bff")

    def start(self):
        """Start spinning animation."""
        self._timer.start(50)
        self.show()

    def stop(self):
        """Stop spinning animation."""
        self._timer.stop()
        self.hide()

    def _rotate(self):
        """Rotate the spinner."""
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)

        # Draw spinner arc
        pen = QPen(self._color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(-15, -15, 30, 30, 0, 270 * 16)


class ModernToast(QFrame):
    """Toast notification widget."""

    closed = Signal()

    def __init__(self, message: str, variant: str = "info", duration: int = 3000, parent=None):
        super().__init__(parent)
        self.message = message
        self.variant = variant
        self.duration = duration
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self):
        """Setup toast UI."""
        self.setObjectName("modernToast")
        self.setFixedHeight(50)
        self.setMinimumWidth(200)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)

        # Message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)

        # Close button
        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.clicked.connect(self.close_toast)
        close_btn.setFixedSize(20, 20)

        layout.addWidget(icon_label)
        layout.addWidget(message_label, 1)
        layout.addWidget(close_btn)

        # Style based on variant
        variant_styles = {
            "info": "background: #17a2b8; color: white;",
            "success": "background: #28a745; color: white;",
            "warning": "background: #ffc107; color: #212529;",
            "error": "background: #dc3545; color: white;",
        }

        self.setStyleSheet(f"""
            QFrame#modernToast {{
                {variant_styles.get(self.variant, variant_styles["info"])}
                border-radius: 6px;
                font-size: 14px;
            }}
            QToolButton {{
                background: transparent;
                color: inherit;
                border: none;
                font-size: 20px;
                font-weight: bold;
            }}
        """)

    def _setup_animation(self):
        """Setup show/hide animations."""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        # Fade in
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)

        # Fade out
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(200)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(self.deleteLater)

        # Auto-hide timer
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.close_toast)

    def show_toast(self):
        """Show the toast with animation."""
        self.show()
        self.fade_in.start()

    def close_toast(self):
        """Close the toast with animation."""
        self.fade_out.start()
        self.closed.emit()


class ModernTimeline(QWidget):
    """Modern timeline widget with smooth scrubbing."""

    frame_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_frames = 100
        self.current_frame = 1
        self._is_scrubbing = False
        self._hover_frame = -1
        self.setFixedHeight(60)
        self.setMouseTracking(True)

    def set_total_frames(self, total: int):
        """Set total number of frames."""
        self.total_frames = max(1, total)
        self.update()

    def set_current_frame(self, frame: int):
        """Set current frame."""
        self.current_frame = max(1, min(frame, self.total_frames))
        self.update()

    def mousePressEvent(self, event):
        """Start scrubbing."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_scrubbing = True
            self._update_frame_from_position(event.pos())

    def mouseMoveEvent(self, event):
        """Update during scrubbing or hover."""
        if self._is_scrubbing:
            self._update_frame_from_position(event.pos())
        else:
            # Update hover state
            old_hover = self._hover_frame
            self._hover_frame = self._get_frame_at_position(event.pos())
            if old_hover != self._hover_frame:
                self.update()

    def mouseReleaseEvent(self, event):
        """Stop scrubbing."""
        self._is_scrubbing = False

    def leaveEvent(self, event):
        """Clear hover state."""
        self._hover_frame = -1
        self.update()

    def _update_frame_from_position(self, pos: QPoint):
        """Update current frame based on mouse position."""
        frame = self._get_frame_at_position(pos)
        if frame != self.current_frame:
            self.current_frame = frame
            self.frame_changed.emit(frame)
            self.update()

    def _get_frame_at_position(self, pos: QPoint) -> int:
        """Get frame number at given position."""
        if self.total_frames <= 0:
            return 1
        frame_width = self.width() / self.total_frames
        frame = int(pos.x() / frame_width) + 1
        return max(1, min(frame, self.total_frames))

    def paintEvent(self, event):
        """Paint modern timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#f8f9fa"))

        # Frame segments
        if self.total_frames > 0:
            frame_width = self.width() / self.total_frames

            for i in range(self.total_frames):
                frame_num = i + 1
                x = i * frame_width
                rect = QRect(int(x), 0, int(frame_width), self.height())

                # Draw frame background
                if frame_num == self.current_frame:
                    painter.fillRect(rect, QColor("#007bff"))
                elif frame_num == self._hover_frame:
                    painter.fillRect(rect, QColor("#e9ecef"))

                # Draw frame number for key frames
                if frame_num % 5 == 0 or frame_num == 1 or frame_num == self.total_frames:
                    painter.setPen(QPen(QColor("#6c757d" if frame_num != self.current_frame else "white")))
                    painter.setFont(QFont("Segoe UI", 9))
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(frame_num))

                # Draw separator
                if i > 0:
                    painter.setPen(QPen(QColor("#dee2e6"), 1))
                    painter.drawLine(int(x), 0, int(x), self.height())
