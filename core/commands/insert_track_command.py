#!/usr/bin/env python
"""
Insert Track Command - 3DEqualizer-style gap filling command.

Implements the Command pattern for Insert Track operations,
providing full undo/redo support for all three scenarios:
1. Single point with gap - interpolate
2. Multiple points, one with gap - fill from source(s)
3. All points have data - create averaged curve
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING
from typing_extensions import override
if TYPE_CHECKING:
    from protocols.ui import MainWindowProtocol

from core.commands.curve_commands import CurveDataCommand
from core.insert_track_algorithm import (
    average_multiple_sources,
    calculate_offset,
    create_averaged_curve,
    deform_curve_with_interpolated_offset,
    fill_gap_with_source,
    find_gap_around_frame,
    find_overlap_frames,
    interpolate_gap,
)
from core.logger_utils import get_logger
from core.type_aliases import CurveDataList
from stores.application_state import get_application_state

logger = get_logger("insert_track_command")


class InsertTrackCommand(CurveDataCommand):
    """Command for Insert Track operation with undo/redo support.

    Supports three scenarios:
    1. Single curve with gap - interpolate the gap
    2. Multiple curves (some with gaps) - fill gaps using source curves
    3. All curves have data - create averaged curve
    """

    def __init__(self, selected_curves: list[str], current_frame: int):
        """Initialize Insert Track command.

        Args:
            selected_curves: Names of selected tracking curves
            current_frame: Current frame (determines gap location)
        """
        super().__init__("Insert Track")
        self.selected_curves: list[str] = selected_curves
        self.current_frame: int = current_frame

        # State for undo/redo
        self.original_data: dict[str, CurveDataList] = {}
        self.new_data: dict[str, CurveDataList] = {}
        self.created_curve_name: str | None = None  # For scenario 3
        self.scenario: int = 0  # Which scenario was executed

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute Insert Track operation.

        Determines scenario based on selection and current frame,
        then executes appropriate algorithm.

        Args:
            main_window: Reference to main window

        Returns:
            True if successful, False otherwise
        """

        def _execute_operation() -> bool:
            # Validate controller availability
            controller = main_window.multi_point_controller
            if controller is None:
                logger.error("Multi-point controller not available")
                return False

            app_state = get_application_state()

            if not self.selected_curves:
                logger.error("No curves selected for Insert Track")
                return False

            # Set target curve for undo/redo (use first selected curve)
            # This differs from _get_active_curve_data() which requires active curve
            self._target_curve = self.selected_curves[0]

            # Save original data for undo
            for curve_name in self.selected_curves:
                curve_data = app_state.get_curve_data(curve_name)
                if curve_data is not None:  # pyright: ignore[reportUnnecessaryComparison]
                    self.original_data[curve_name] = copy.deepcopy(curve_data)

            # Determine scenario using gap detection
            # A curve has a "gap" at current frame if find_gap_around_frame() returns non-None
            curves_with_gap_at_current: list[str] = []  # Curves with gaps (missing data) at current frame
            curves_without_gap_at_current: list[str] = []  # Curves with complete data at current frame

            for curve_name in self.selected_curves:
                curve_data = app_state.get_curve_data(curve_name)
                if curve_data is None:  # pyright: ignore[reportUnnecessaryComparison]
                    continue

                # Log frames in this curve for diagnostic purposes
                frames_in_curve = sorted([p[0] for p in curve_data])
                logger.info(
                    f"'{curve_name}' has {len(frames_in_curve)} frames: {frames_in_curve[:10]}...{frames_in_curve[-10:] if len(frames_in_curve) > 10 else ''}"
                )

                # Check if current frame is inside a gap (continuous sequence of missing frames)
                gap = find_gap_around_frame(curve_data, self.current_frame)

                if gap is not None:
                    # Current frame is inside a gap
                    curves_with_gap_at_current.append(curve_name)
                    logger.info(f"'{curve_name}' has gap at frame {self.current_frame}: {gap}")
                else:
                    # Current frame has data (not in a gap)
                    curves_without_gap_at_current.append(curve_name)
                    current_frame_exists = self.current_frame in frames_in_curve
                    logger.info(
                        f"'{curve_name}' has NO gap at frame {self.current_frame} (frame exists in data: {current_frame_exists})"
                    )

            # Diagnostic logging
            logger.info(
                f"Gap detection: {len(curves_with_gap_at_current)} with gaps, {len(curves_without_gap_at_current)} without gaps"
            )

            # Execute appropriate scenario
            if len(self.selected_curves) == 1 and curves_with_gap_at_current:
                # Scenario 1: Single curve with gap at current frame - interpolate
                success = self._execute_scenario_1(main_window, curves_with_gap_at_current[0])
                self.scenario = 1

            elif curves_with_gap_at_current and curves_without_gap_at_current:
                # Scenario 2: Some curves have gaps, others don't - fill gaps using complete curves
                # Target = curves with gaps (to be filled)
                # Source = curves without gaps (data source)
                success = self._execute_scenario_2(
                    main_window, curves_with_gap_at_current, curves_without_gap_at_current
                )
                self.scenario = 2

            elif len(curves_with_gap_at_current) == 0 and len(self.selected_curves) >= 2:
                # Scenario 3: All curves have data at current frame - create averaged curve
                # BUT: Verify at least one curve actually has data at current frame
                # (gap detection returns None for frames beyond all data, which isn't a real "no gap")
                curves_with_actual_data_at_frame: list[str] = []
                for curve_name in curves_without_gap_at_current:
                    curve_data = app_state.get_curve_data(curve_name)
                    if curve_data and any(p[0] == self.current_frame for p in curve_data):
                        curves_with_actual_data_at_frame.append(curve_name)

                if len(curves_with_actual_data_at_frame) >= 2:
                    # Valid Scenario 3: Multiple curves have actual data at current frame
                    success = self._execute_scenario_3(main_window, curves_with_actual_data_at_frame)
                    self.scenario = 3
                else:
                    logger.error(
                        f"Invalid scenario: no curves have data at frame {self.current_frame} "
                        + f"({len(curves_with_actual_data_at_frame)} curves with data, need 2+)"
                    )
                    return False

            else:
                logger.error(
                    f"Invalid scenario: all {len(self.selected_curves)} curves have gaps at frame {self.current_frame}"
                )
                return False

            if success:
                self.executed = True
                logger.info(f"Insert Track executed successfully (Scenario {self.scenario})")

            return success

        return self._safe_execute("executing", _execute_operation)

    def _execute_scenario_1(self, main_window: MainWindowProtocol, target_curve: str) -> bool:
        """Execute Scenario 1: Interpolate gap in single curve.

        Args:
            main_window: Reference to main window
            target_curve: Name of curve with gap

        Returns:
            True if successful
        """
        controller = main_window.multi_point_controller
        if controller is None:
            logger.error("Multi-point controller not available")
            return False
        app_state = get_application_state()

        curve_data = app_state.get_curve_data(target_curve)
        if curve_data is None:  # pyright: ignore[reportUnnecessaryComparison]
            logger.error(f"No data found for curve '{target_curve}'")
            return False

        # Find gap
        gap = find_gap_around_frame(curve_data, self.current_frame)
        if gap is None:
            logger.warning(f"No gap found around frame {self.current_frame}")
            return False

        gap_start, gap_end = gap

        # Find actual overlap frames (existing frames immediately outside gap boundaries)
        curve_frames = {p[0] for p in curve_data}
        overlap_before = max((f for f in curve_frames if f < gap_start), default=gap_start - 1)
        overlap_after = min((f for f in curve_frames if f > gap_end), default=gap_end + 1)

        # 3DEqualizer-style console output
        logger.info("--------------- insert track v1.0 ---------------")
        logger.info("one point selected")
        logger.info(f"target: {target_curve}")
        logger.info("source: reeling in target")
        logger.info(f"section: [{gap_start}, {gap_end}]")
        logger.info(f"overlap: [{overlap_before}, {overlap_after}]")

        # Interpolate gap
        new_curve_data = interpolate_gap(curve_data, gap_start, gap_end)

        # Verify interpolation succeeded (data changed)
        if len(new_curve_data) == len(curve_data):
            logger.warning(f"Interpolation failed for gap [{gap_start}, {gap_end}] - missing boundary points")
            return False

        # Update tracked data
        self.new_data[target_curve] = new_curve_data
        app_state = get_application_state()
        app_state.set_curve_data(target_curve, new_curve_data)

        # Sync DataService for rendering (critical for gap visualization)
        from services import get_data_service
        data_service = get_data_service()
        data_service.update_curve_data(new_curve_data)
        logger.info(f"Synced {target_curve} to DataService ({len(new_curve_data)} points)")

        # Update UI
        self._update_ui(main_window, target_curve)

        logger.info("done.")
        return True

    def _execute_scenario_2(
        self, main_window: MainWindowProtocol, target_curves: list[str], source_curves: list[str]
    ) -> bool:
        """Execute Scenario 2: Fill gap(s) using source curve(s).

        Args:
            main_window: Reference to main window
            target_curves: Curves with gaps to fill
            source_curves: Curves to copy data from

        Returns:
            True if successful
        """
        controller = main_window.multi_point_controller
        if controller is None:
            logger.error("Multi-point controller not available")
            return False
        app_state = get_application_state()

        # Track if at least one target was successfully filled
        any_success = False

        # Process each target curve
        for target_name in target_curves:
            target_data = app_state.get_curve_data(target_name)
            if target_data is None:  # pyright: ignore[reportUnnecessaryComparison]
                logger.warning(f"No data found for target curve '{target_name}'")
                continue

            # Find gap
            gap = find_gap_around_frame(target_data, self.current_frame)
            if gap is None:
                logger.warning(f"No gap found in '{target_name}' around frame {self.current_frame}")
                continue

            gap_start, gap_end = gap

            # Collect source data and calculate offsets
            # Also track overlap points for deformation (3DEqualizer's keylist)
            source_data_list: list[CurveDataList] = []
            offset_list: list[tuple[float, float]] = []
            overlap_points_per_source: list[list[tuple[int, tuple[float, float]]]] = []

            for source_name in source_curves:
                source_data = app_state.get_curve_data(source_name)
                if source_data is None:  # pyright: ignore[reportUnnecessaryComparison]
                    logger.warning(f"No data found for source curve '{source_name}'")
                    continue

                # Find overlap frames
                before_overlap, after_overlap = find_overlap_frames(target_data, source_data, gap_start, gap_end)

                # Need at least one overlap frame
                overlap_frames = before_overlap + after_overlap
                if not overlap_frames:
                    logger.warning(f"No overlap between '{target_name}' and '{source_name}'")
                    continue

                # Calculate average offset (used when only 1 overlap point exists)
                offset = calculate_offset(target_data, source_data, overlap_frames)

                # Calculate per-frame offsets for deformation (when 2+ overlap points exist)
                # Build list of (frame, (offset_x, offset_y)) for each overlap frame
                from core.models import CurvePoint

                target_points_dict = {p[0]: CurvePoint.from_tuple(p) for p in target_data}
                source_points_dict = {p[0]: CurvePoint.from_tuple(p) for p in source_data}

                overlap_points: list[tuple[int, tuple[float, float]]] = []
                for frame in sorted(overlap_frames):
                    if frame in target_points_dict and frame in source_points_dict:
                        t_pt = target_points_dict[frame]
                        s_pt = source_points_dict[frame]
                        frame_offset = (t_pt.x - s_pt.x, t_pt.y - s_pt.y)
                        overlap_points.append((frame, frame_offset))

                source_data_list.append(source_data)
                offset_list.append(offset)
                overlap_points_per_source.append(overlap_points)

            if not source_data_list:
                logger.error(f"No valid source curves found for '{target_name}'")
                continue

            # Find actual overlap frames for logging (existing frames immediately outside gap boundaries)
            target_frames = {p[0] for p in target_data}
            overlap_before = max((f for f in target_frames if f < gap_start), default=gap_start - 1)
            overlap_after = min((f for f in target_frames if f > gap_end), default=gap_end + 1)

            # 3DEqualizer-style console output
            total_selected = len(target_curves) + len(source_curves)
            logger.info("--------------- insert track v1.0 ---------------")
            if total_selected == 2:
                logger.info("2 points selected")
            else:
                logger.info("multiple points selected")

            logger.info(f"target: {target_name}")

            if len(source_data_list) == 1:
                logger.info(f"source: {source_curves[0]}")
            else:
                logger.info(f"averaging {len(source_data_list)} source points:")
                for source_name in source_curves:
                    # Check if this source's data is in our source_data_list
                    src_data = app_state.get_curve_data(source_name)
                    if src_data is not None and any(src_data == sd for sd in source_data_list):  # pyright: ignore[reportUnnecessaryComparison]
                        logger.info(source_name)

            logger.info(f"section: [{gap_start}, {gap_end}]")
            logger.info(f"overlap: [{overlap_before}, {overlap_after}]")

            # Fill gap (choose algorithm based on overlap points)
            if len(source_data_list) == 1:
                # Single source - check if we should use deformation
                overlap_points = overlap_points_per_source[0]

                if len(overlap_points) >= 2:
                    # Use deformation (interpolated offset) - 3DEqualizer _deformCurve
                    logger.info(f"Using deformation algorithm ({len(overlap_points)} overlap points)")
                    new_curve_data = deform_curve_with_interpolated_offset(
                        target_data, source_data_list[0], gap_start, gap_end, overlap_points
                    )
                else:
                    # Use constant offset - 3DEqualizer _offsetCurve
                    logger.info("Using constant offset algorithm (1 overlap point)")
                    new_curve_data = fill_gap_with_source(
                        target_data, source_data_list[0], gap_start, gap_end, offset_list[0]
                    )
            else:
                # Multiple sources - average them
                logger.info(f"Using averaging algorithm ({len(source_data_list)} sources)")
                gap_frames = list(range(gap_start, gap_end + 1))
                averaged_points = average_multiple_sources(source_data_list, gap_frames, offset_list)

                # Merge averaged points with target data
                from core.models import CurvePoint

                target_points = [CurvePoint.from_tuple(p) for p in target_data]
                all_points = target_points + averaged_points

                # Sort and convert
                all_points.sort(key=lambda p: p.frame)
                new_curve_data = [p.to_tuple4() for p in all_points]

            # Update tracked data (ensure proper type with list() conversion)
            self.new_data[target_name] = list(new_curve_data)
            app_state = get_application_state()
            app_state.set_curve_data(target_name, list(new_curve_data))

            # Sync DataService for rendering (critical for gap visualization)
            # DataService.segmented_curve must be updated so renderer knows the gap is filled
            from services import get_data_service
            data_service = get_data_service()
            data_service.update_curve_data(list(new_curve_data))
            logger.info(f"Synced {target_name} to DataService ({len(new_curve_data)} points)")

            # Update UI
            self._update_ui(main_window, target_name)

            logger.info("done.")

            # Mark success
            any_success = True

        return any_success

    def _execute_scenario_3(self, main_window: MainWindowProtocol, source_curves: list[str]) -> bool:
        """Execute Scenario 3: Create averaged curve from all sources.

        Args:
            main_window: Reference to main window
            source_curves: All selected curves (all have data at current frame)

        Returns:
            True if successful
        """
        controller = main_window.multi_point_controller
        if controller is None:
            logger.error("Multi-point controller not available")
            return False
        app_state = get_application_state()

        # 3DEqualizer-style console output
        logger.info("--------------- insert track v1.0 ---------------")
        logger.info("multiple points selected")
        logger.info(f"averaging {len(source_curves)} source points:")
        for source_name in source_curves:
            logger.info(source_name)

        # Collect source curves
        source_curves_dict: dict[str, CurveDataList] = {}
        for name in source_curves:
            curve_data = app_state.get_curve_data(name)
            if curve_data is not None:  # pyright: ignore[reportUnnecessaryComparison]
                source_curves_dict[name] = curve_data

        # Create averaged curve
        new_curve_name, averaged_data = create_averaged_curve(source_curves_dict)

        if not averaged_data:
            logger.warning("Averaged curve is empty (no common frames)")
            return False

        # Ensure unique name
        base_name = "avrg"
        counter = 1
        new_curve_name = f"{base_name}_{counter:02d}"
        all_curve_names = app_state.get_all_curve_names()
        while new_curve_name in all_curve_names:
            counter += 1
            new_curve_name = f"{base_name}_{counter:02d}"

        # Add new curve to tracked data
        app_state = get_application_state()
        app_state.set_curve_data(new_curve_name, averaged_data)
        self.created_curve_name = new_curve_name
        self.new_data[new_curve_name] = averaged_data

        # Update UI - add to tracking panel and select new curve
        self._update_ui_new_curve(main_window, new_curve_name)

        logger.info(f"Created averaged curve: {new_curve_name}")
        logger.info("done.")
        return True

    def _update_ui(self, main_window: MainWindowProtocol, curve_name: str) -> None:
        """Update UI after modifying a curve.

        Args:
            main_window: Reference to main window
            curve_name: Name of modified curve
        """
        # Check controller availability
        if main_window.multi_point_controller is None:
            logger.warning("Cannot update UI: multi-point controller not available")
            return

        # Update tracking panel
        main_window.multi_point_controller.update_tracking_panel()

        # Select only the modified curve and set as active
        app_state = get_application_state()
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({curve_name})
        app_state.set_active_curve(curve_name)  # Timeline needs active_curve to update
        logger.info(f"Selected and activated curve '{curve_name}' after Insert Track")

        # Get current active curve for diagnostics
        active_curve = app_state.active_curve
        logger.info(f"Insert Track update: modified='{curve_name}', active='{active_curve}'")

        # If this is the active curve, update the display
        if (app_state.active_curve is not None and app_state.active_curve == curve_name
                and main_window.curve_widget):
            curve_data = app_state.get_curve_data(curve_name)
            if curve_data is not None:  # pyright: ignore[reportUnnecessaryComparison]
                main_window.curve_widget.set_curve_data(curve_data)
                logger.info(f"Updated curve widget display for active curve '{curve_name}'")

        # Force repaint of curve view to ensure visibility (regardless of active curve)
        # This ensures the modified curve is visible even if it's not currently active
        if main_window.curve_widget:
            main_window.curve_widget.invalidate_caches()
            main_window.curve_widget.update()
            logger.info("Forced curve view repaint after Insert Track")

        # Update timeline
        if main_window.update_timeline_tabs is not None:
            curve_data = app_state.get_curve_data(curve_name)
            if curve_data is not None:  # pyright: ignore[reportUnnecessaryComparison]
                main_window.update_timeline_tabs(curve_data)

    def _update_ui_new_curve(self, main_window: MainWindowProtocol, curve_name: str) -> None:
        """Update UI after creating a new averaged curve.

        Args:
            main_window: Reference to main window
            curve_name: Name of new curve
        """
        # Check controller availability
        if main_window.multi_point_controller is None:
            logger.warning("Cannot update UI: multi-point controller not available")
            return

        # Update tracking panel
        main_window.multi_point_controller.update_tracking_panel()

        # Select only the new curve
        app_state = get_application_state()
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({curve_name})
        logger.info(f"Selected only new curve '{curve_name}' after Insert Track")

        # Set as active curve - always do this for newly created curves
        app_state = get_application_state()
        app_state.set_active_curve(curve_name)

        # Get curve data (needed for both curve widget and timeline updates)
        curve_data = app_state.get_curve_data(curve_name)
        if curve_data is None:  # pyright: ignore[reportUnnecessaryComparison]
            logger.warning(f"Cannot update UI: no data for new curve '{curve_name}'")
            return

        # Update curve display
        if main_window.curve_widget:
            main_window.curve_widget.set_curve_data(curve_data)

        # Update timeline
        if main_window.update_timeline_tabs is not None:
            main_window.update_timeline_tabs(curve_data)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo Insert Track operation.

        Args:
            main_window: Reference to main window

        Returns:
            True if successful
        """

        def _undo_operation() -> bool:
            if not self.executed:
                return False

            if not self._target_curve:
                logger.error("Missing target curve for undo")
                return False

            controller = main_window.multi_point_controller
            if controller is None:
                logger.error("Multi-point controller not available")
                return False

            # Scenario 3: Remove created curve
            if self.scenario == 3 and self.created_curve_name:
                app_state = get_application_state()
                if self.created_curve_name in app_state.get_all_curve_names():
                    app_state.delete_curve(self.created_curve_name)
                    logger.info(f"Removed averaged curve '{self.created_curve_name}'")

            # Scenarios 1 & 2: Restore original data
            app_state = get_application_state()
            for curve_name, original_data in self.original_data.items():
                app_state.set_curve_data(curve_name, copy.deepcopy(original_data))
                self._update_ui(main_window, curve_name)

            # Update tracking panel (controller already checked above)
            controller.update_tracking_panel()

            self.executed = False
            logger.info("Insert Track undone")
            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo Insert Track operation (uses stored target curve, not current active).

        Args:
            main_window: Reference to main window

        Returns:
            True if successful
        """

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            controller = main_window.multi_point_controller
            if controller is None:
                logger.error("Multi-point controller not available")
                return False

            # Scenario 3: Re-add created curve
            if self.scenario == 3 and self.created_curve_name:
                app_state = get_application_state()
                app_state.set_curve_data(self.created_curve_name, copy.deepcopy(self.new_data[self.created_curve_name]))
                self._update_ui_new_curve(main_window, self.created_curve_name)

            # Scenarios 1 & 2: Re-apply new data (use stored target, NOT current active)
            app_state = get_application_state()
            for curve_name, new_data in self.new_data.items():
                if curve_name != self.created_curve_name:  # Skip scenario 3's created curve
                    app_state.set_curve_data(curve_name, copy.deepcopy(new_data))
                    self._update_ui(main_window, curve_name)

            # Update tracking panel (controller already checked above)
            controller.update_tracking_panel()

            self.executed = True
            logger.info("Insert Track redone")
            return True

        return self._safe_execute("redoing", _redo_operation)
