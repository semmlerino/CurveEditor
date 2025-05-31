#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Smoothing Operations for Curve Editor Main Window.

This module contains the smoothing-related operations that were previously
in MainWindow, helping to reduce the MainWindow class size.
"""

import logging
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer

from services.analysis_service import AnalysisService as CurveDataOperations
from services.dialog_service import DialogService
from services.unified_transformation_service import UnifiedTransformationService

if TYPE_CHECKING:
    from main_window import MainWindow

logger = logging.getLogger(__name__)


class SmoothingOperations:
    """Handles smoothing operations for MainWindow."""

    @staticmethod
    def apply_ui_smoothing(window: 'MainWindow'):
        """Apply smoothing based on inline UI controls."""
        if not window.curve_data or len(window.curve_data) < 3:
            QMessageBox.information(window, "Info", "Not enough points to smooth curve.")
            return

        # Save auto-center state and temporarily disable it during smoothing
        was_auto_center_enabled = getattr(window, 'auto_center_enabled', False)
        window.auto_center_enabled = False

        # Save current view state
        current_scale_to_image = getattr(window.curve_view, 'scale_to_image', True)
        current_zoom = getattr(window.curve_view, 'zoom_factor', 1.0)
        current_offset_x = getattr(window.curve_view, 'offset_x', 0)
        current_offset_y = getattr(window.curve_view, 'offset_y', 0)

        logger.info(f"INLINE SMOOTH - Before: scale_to_image={current_scale_to_image}, "
                   f"zoom={current_zoom}, offset_x={current_offset_x}, offset_y={current_offset_y}")

        try:
            # Apply moving average smoothing
            data_ops = CurveDataOperations(window.curve_data)
            window.curve_data = data_ops.get_data()  # type: ignore[assignment]
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Smoothing failed: {e}")
            return

        # Restore view properties
        window.curve_view.scale_to_image = current_scale_to_image
        window.curve_view.zoom_factor = current_zoom
        window.curve_view.offset_x = current_offset_x
        window.curve_view.offset_y = current_offset_y

        # Update points with preserved view
        window.curve_view.setPoints(window.curve_data, window.image_width, window.image_height, preserve_view=True)

        # Ensure scale_to_image state is restored
        window.curve_view.scale_to_image = current_scale_to_image

        logger.info(f"INLINE SMOOTH - After: scale_to_image={window.curve_view.scale_to_image}, "
                   f"zoom={window.curve_view.zoom_factor}, offset_x={window.curve_view.offset_x}, "
                   f"offset_y={window.curve_view.offset_y}")

        window.add_to_history()

        # Use a timer to ensure proper update
        def delayed_inline_update():
            window.curve_view.update()
            logger.info("Inline smooth view updated with delay")

        # 10ms delay
        QTimer.singleShot(10, delayed_inline_update)

        # Restore auto-center state
        if was_auto_center_enabled:
            window.auto_center_enabled = True
            logger.info("Restored auto-center state after inline smooth")

    @staticmethod
    def apply_smooth_operation(window: 'MainWindow'):
        """Entry point for smoothing operations using unified transformation system."""
        if not window.curve_data:
            QMessageBox.information(window, "Info", "No curve data loaded.")
            return

        # Save critical view state parameters
        current_zoom = getattr(window.curve_view, 'zoom_factor', 1.0)
        current_offset_x = getattr(window.curve_view, 'offset_x', 0.0)
        current_offset_y = getattr(window.curve_view, 'offset_y', 0.0)
        current_scale_to_image = getattr(window.curve_view, 'scale_to_image', True)
        current_flip_y = getattr(window.curve_view, 'flip_y_axis', True)

        logger.info(f"SMOOTH - Before: zoom={current_zoom}, offset=({current_offset_x},{current_offset_y}), "
                   f"scale_to_image={current_scale_to_image}")

        # Use stable transformation context
        reference_points = {}
        try:
            with UnifiedTransformationService.stable_transformation_context(window.curve_view) as transform:
                # Get selected indices
                selected_indices = getattr(window.curve_view, 'selected_indices', [])
                selected_point_idx = getattr(window.curve_view, 'selected_point_idx', -1)

                # Store reference points for verification
                if window.curve_data and len(window.curve_data) > 0:
                    reference_indices = [0]
                    if len(window.curve_data) > 2:
                        reference_indices.append(len(window.curve_data) // 2)
                    reference_indices.append(len(window.curve_data) - 1)

                    for idx in reference_indices:
                        if 0 <= idx < len(window.curve_data):
                            point = window.curve_data[idx]
                            screen_x, screen_y = transform.apply(point[1], point[2])
                            reference_points[idx] = (point[0], screen_x, screen_y)
                            logger.info(f"Reference point {idx}: frame={point[0]}, "
                                      f"screen=({screen_x:.2f},{screen_y:.2f})")

                # Show smooth dialog
                modified_data = DialogService.show_smooth_dialog(
                    parent_widget=window,
                    curve_data=window.curve_data,
                    selected_indices=selected_indices,
                    selected_point_idx=selected_point_idx
                )

                if modified_data is not None:
                    window.curve_data = modified_data

                    # Restore view transform parameters
                    window.curve_view.zoom_factor = current_zoom
                    window.curve_view.offset_x = current_offset_x
                    window.curve_view.offset_y = current_offset_y
                    window.curve_view.scale_to_image = current_scale_to_image
                    window.curve_view.flip_y_axis = current_flip_y

                    # Save original parameters
                    original_zoom = window.curve_view.zoom_factor
                    original_offset_x = window.curve_view.offset_x
                    original_offset_y = window.curve_view.offset_y
                    original_flip_y = window.curve_view.flip_y_axis
                    original_scale_to_image = window.curve_view.scale_to_image

                    logger.info(f"SMOOTH - Original params: zoom={original_zoom}, "
                               f"offset=({original_offset_x}, {original_offset_y}), "
                               f"flip_y={original_flip_y}, scale_to_image={original_scale_to_image}")

                    try:
                        # Update view with preservation
                        window.curve_view.setPoints(
                            window.curve_data,
                            window.image_width,
                            window.image_height,
                            preserve_view=True,
                        )

                        # Force-restore transformation parameters
                        window.curve_view.zoom_factor = original_zoom
                        window.curve_view.offset_x = original_offset_x
                        window.curve_view.offset_y = original_offset_y
                        window.curve_view.flip_y_axis = original_flip_y
                        window.curve_view.scale_to_image = original_scale_to_image

                    except Exception as e:
                        logger.error(f"Error in stable smoothing operation: {e}")
                        window.statusBar().showMessage(f"Smoothing failed: {e}", 3000)

                    finally:
                        window.add_to_history()
                        window.statusBar().showMessage("Smoothing applied successfully with drift correction", 3000)

        except Exception as e:
            logger.error(f"Error in stable smoothing operation: {e}")
            window.statusBar().showMessage(f"Smoothing failed: {e}", 3000)

        # Log final transform state
        current_zoom = getattr(window.curve_view, 'zoom_factor', 1.0)
        current_offset_x = getattr(window.curve_view, 'offset_x', 0.0)
        current_offset_y = getattr(window.curve_view, 'offset_y', 0.0)
        logger.info(f"SMOOTH - After: zoom={current_zoom}, offset=({current_offset_x},{current_offset_y}), "
                   f"scale_to_image={getattr(window.curve_view, 'scale_to_image', True)}")
