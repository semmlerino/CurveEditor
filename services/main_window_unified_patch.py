"""
Patch for MainWindow to use Unified Transformation System

This patch updates main_window.py to use the new unified transformation system
instead of the deprecated TransformStabilizer. This demonstrates how to migrate
existing code to the new system.
"""

def apply_unified_transform_patch():
    """
    Apply the unified transformation system patch to MainWindow.

    This function shows how to migrate from the old TransformStabilizer
    to the new stable_transformation_context.
    """
    import sys
    import importlib

    try:
        # Import the unified system
        from services.transformation_integration import (
            stable_transform_operation,
            ValidationHelper
        )

        # Import MainWindow (this will work if this patch is imported from main_window.py)
        if 'main_window' in sys.modules:
            main_window_module = sys.modules['main_window']
            MainWindow = main_window_module.MainWindow

            # Store original apply_smoothing method if not already stored
            if not hasattr(MainWindow, '_original_apply_smoothing'):
                MainWindow._original_apply_smoothing = MainWindow.apply_smoothing

            # Create new apply_smoothing method using unified system
            def apply_smoothing_unified(self, smoothing_factor=None):
                """
                Apply curve smoothing with unified transformation system.

                This new implementation uses stable_transform_operation instead
                of the old TransformStabilizer approach.
                """
                from services.logging_service import LoggingService
                logger = LoggingService.get_logger("main_window")

                if not hasattr(self, 'curve_data') or not self.curve_data:
                    logger.warning("No curve data available for smoothing")
                    return

                # Determine smoothing factor
                if smoothing_factor is None:
                    smoothing_factor = getattr(self, 'default_smoothing_factor', 0.5)

                logger.info(f"Applying smoothing with factor {smoothing_factor} using unified transform system")

                # Use the new stable transformation context
                with stable_transform_operation(self.curve_view) as stable_transform:
                    # Store original data for comparison
                    before_data = self.curve_data.copy()

                    # Apply smoothing using existing CurveDataOperations
                    CurveDataOperations = getattr(main_window_module, 'CurveDataOperations', None)
                    if CurveDataOperations:
                        modified_data = CurveDataOperations.smooth_curve(
                            before_data, smoothing_factor
                        )
                    else:
                        # Fallback: simple smoothing implementation
                        modified_data = self._apply_simple_smoothing(before_data, smoothing_factor)

                    # Update curve data
                    self.curve_data = modified_data

                    # Update the curve view with preserve_view=True
                    self.curve_view.setPoints(
                        self.curve_data,
                        getattr(self, 'image_width', 1920),
                        getattr(self, 'image_height', 1080),
                        preserve_view=True
                    )

                    # Add to history
                    if hasattr(self, 'add_to_history'):
                        self.add_to_history()

                # Update status
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage("Smoothing applied successfully with unified transform system", 3000)

                logger.info("Smoothing completed with unified transformation system")

            # Helper method for simple smoothing
            def apply_simple_smoothing(self, data, factor):
                """Simple smoothing implementation as fallback."""
                if len(data) < 3:
                    return data

                smoothed = []
                for i, point in enumerate(data):
                    if i == 0 or i == len(data) - 1:
                        smoothed.append(point)
                    else:
                        prev_point = data[i - 1]
                        next_point = data[i + 1]

                        # Weighted average
                        weight = 1.0 / factor
                        new_x = (prev_point[1] + point[1] * (weight - 2) + next_point[1]) / weight
                        new_y = (prev_point[2] + point[2] * (weight - 2) + next_point[2]) / weight

                        smoothed_point = (point[0], new_x, new_y) + point[3:]
                        smoothed.append(smoothed_point)

                return smoothed

            # Patch the methods
            MainWindow.apply_smoothing = apply_smoothing_unified
            MainWindow._apply_simple_smoothing = apply_simple_smoothing

            # Mark as patched
            MainWindow._unified_transform_patched = True

            logger.info("MainWindow patched to use unified transformation system")
            return True

    except Exception as e:
        print(f"Failed to apply unified transform patch: {e}")
        return False

    return False


def create_migration_example():
    """
    Create a practical example showing the migration from old to new system.

    This demonstrates the before/after code patterns.
    """

    # OLD APPROACH (deprecated)
    old_code_example = '''
    # Old approach using TransformStabilizer
    from transform_fix import TransformStabilizer

    # Calculate stable transform
    stable_transform = TransformStabilizer.calculate_stable_transform(self.curve_view)

    # Track reference points
    reference_points = TransformStabilizer.track_reference_points(
        self.curve_data, stable_transform
    )

    # Apply operation
    self.curve_data = modified_data
    self.curve_view.setPoints(self.curve_data, ...)

    # Verify stability
    is_stable = TransformStabilizer.verify_reference_points(
        self.curve_data, reference_points, stable_transform
    )
    '''

    # NEW APPROACH (recommended)
    new_code_example = '''
    # New approach using unified transformation system
    from services.transformation_integration import stable_transform_operation

    # Use context manager for automatic stability
    with stable_transform_operation(self.curve_view) as stable_transform:
        # Apply operation - stability is guaranteed automatically
        self.curve_data = modified_data
        self.curve_view.setPoints(self.curve_data, ...)

        # Context manager handles verification and restoration
    '''

    return {
        'old_approach': old_code_example,
        'new_approach': new_code_example,
        'benefits': [
            'Automatic stability tracking',
            'Cleaner, more readable code',
            'Built-in error handling',
            'No manual reference point management',
            'Guaranteed restoration of view state'
        ]
    }


# Auto-apply patch if this module is imported
if __name__ != '__main__':
    # Try to apply the patch when imported
    try:
        apply_unified_transform_patch()
    except:
        pass  # Silent fail if not in the right context
