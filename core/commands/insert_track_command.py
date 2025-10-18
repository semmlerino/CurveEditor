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

from core.commands.base_command import Command
from core.insert_track_algorithm import (
    average_multiple_sources,
    calculate_offset,
    create_averaged_curve,
    fill_gap_with_source,
    find_gap_around_frame,
    find_overlap_frames,
    interpolate_gap,
)
from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

logger = get_logger("insert_track_command")


class InsertTrackCommand(Command):
    """Command for Insert Track operation with undo/redo support."""

    def __init__(self, selected_curves: list[str], current_frame: int):
        """Initialize Insert Track command.

        Args:
            selected_curves: Names of selected tracking curves
            current_frame: Current frame (determines gap location)
        """
        super().__init__("Insert Track")
        self.selected_curves = selected_curves
        self.current_frame = current_frame

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
        try:
            # Get tracked data from MultiPointTrackingController
            if main_window.multi_point_controller is None:
                logger.error("Main window missing multi_point_controller")
                return False

            controller = main_window.multi_point_controller
            tracked_data = controller.tracked_data

            if not self.selected_curves:
                logger.error("No curves selected for Insert Track")
                return False

            # Save original data for undo
            for curve_name in self.selected_curves:
                if curve_name in tracked_data:
                    self.original_data[curve_name] = copy.deepcopy(tracked_data[curve_name])

            # Determine scenario
            curves_with_data_at_current = []
            curves_without_data_at_current = []

            for curve_name in self.selected_curves:
                if curve_name not in tracked_data:
                    continue

                curve_data = tracked_data[curve_name]
                frames = {p[0] for p in curve_data}

                if self.current_frame in frames:
                    curves_with_data_at_current.append(curve_name)
                else:
                    curves_without_data_at_current.append(curve_name)

            # Execute appropriate scenario
            if len(self.selected_curves) == 1 and curves_without_data_at_current:
                # Scenario 1: Single point with no data at current frame - interpolate
                success = self._execute_scenario_1(main_window, curves_without_data_at_current[0])
                self.scenario = 1

            elif curves_without_data_at_current and curves_with_data_at_current:
                # Scenario 2: Multiple points, one (or more) without data - fill gap
                success = self._execute_scenario_2(
                    main_window, curves_without_data_at_current, curves_with_data_at_current
                )
                self.scenario = 2

            elif len(curves_without_data_at_current) == 0 and len(self.selected_curves) >= 2:
                # Scenario 3: All selected curves have data - create averaged curve (requires 2+ curves)
                success = self._execute_scenario_3(main_window, curves_with_data_at_current)
                self.scenario = 3

            else:
                logger.error(f"Invalid scenario: no data at current frame for all {len(self.selected_curves)} curves")
                return False

            if success:
                self.executed = True
                logger.info(f"Insert Track executed successfully (Scenario {self.scenario})")

            return success

        except Exception as e:
            logger.error(f"Error executing Insert Track: {e}")
            return False

    def _execute_scenario_1(self, main_window: MainWindowProtocol, target_curve: str) -> bool:
        """Execute Scenario 1: Interpolate gap in single curve.

        Args:
            main_window: Reference to main window
            target_curve: Name of curve with gap

        Returns:
            True if successful
        """
        controller = main_window.multi_point_controller
        tracked_data = controller.tracked_data

        curve_data = tracked_data[target_curve]

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
        tracked_data[target_curve] = new_curve_data

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
        tracked_data = controller.tracked_data

        # Track if at least one target was successfully filled
        any_success = False

        # Process each target curve
        for target_name in target_curves:
            target_data = tracked_data[target_name]

            # Find gap
            gap = find_gap_around_frame(target_data, self.current_frame)
            if gap is None:
                logger.warning(f"No gap found in '{target_name}' around frame {self.current_frame}")
                continue

            gap_start, gap_end = gap

            # Collect source data and calculate offsets
            source_data_list = []
            offset_list = []

            for source_name in source_curves:
                source_data = tracked_data[source_name]

                # Find overlap frames
                before_overlap, after_overlap = find_overlap_frames(target_data, source_data, gap_start, gap_end)

                # Need at least one overlap frame
                overlap_frames = before_overlap + after_overlap
                if not overlap_frames:
                    logger.warning(f"No overlap between '{target_name}' and '{source_name}'")
                    continue

                # Calculate offset
                offset = calculate_offset(target_data, source_data, overlap_frames)

                source_data_list.append(source_data)
                offset_list.append(offset)

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
                    if source_name in [src for src in source_curves if tracked_data[src] in source_data_list]:
                        logger.info(source_name)

            logger.info(f"section: [{gap_start}, {gap_end}]")
            logger.info(f"overlap: [{overlap_before}, {overlap_after}]")

            # Fill gap
            if len(source_data_list) == 1:
                # Single source
                new_curve_data = fill_gap_with_source(
                    target_data, source_data_list[0], gap_start, gap_end, offset_list[0]
                )
            else:
                # Multiple sources - average them
                gap_frames = list(range(gap_start, gap_end + 1))
                averaged_points = average_multiple_sources(source_data_list, gap_frames, offset_list)

                # Merge averaged points with target data
                from core.models import CurvePoint

                target_points = [CurvePoint.from_tuple(p) if isinstance(p, tuple) else p for p in target_data]
                all_points = target_points + averaged_points

                # Sort and convert
                all_points.sort(key=lambda p: p.frame)
                new_curve_data = [p.to_tuple4() for p in all_points]

            # Update tracked data (ensure proper type with list() conversion)
            self.new_data[target_name] = list(new_curve_data)
            tracked_data[target_name] = list(new_curve_data)

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
        tracked_data = controller.tracked_data

        # 3DEqualizer-style console output
        logger.info("--------------- insert track v1.0 ---------------")
        logger.info("multiple points selected")
        logger.info(f"averaging {len(source_curves)} source points:")
        for source_name in source_curves:
            logger.info(source_name)

        # Collect source curves
        source_curves_dict = {name: tracked_data[name] for name in source_curves}

        # Create averaged curve
        new_curve_name, averaged_data = create_averaged_curve(source_curves_dict)

        if not averaged_data:
            logger.warning("Averaged curve is empty (no common frames)")
            return False

        # Ensure unique name
        base_name = "avrg"
        counter = 1
        new_curve_name = f"{base_name}_{counter:02d}"
        while new_curve_name in tracked_data:
            counter += 1
            new_curve_name = f"{base_name}_{counter:02d}"

        # Add new curve to tracked data
        tracked_data[new_curve_name] = averaged_data
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
        # Update tracking panel
        if main_window.multi_point_controller is not None:
            main_window.multi_point_controller.update_tracking_panel()

        # If this is the active curve, update the display
        if main_window.active_timeline_point is not None:
            if main_window.active_timeline_point == curve_name:
                # Update curve display
                if main_window.curve_widget:
                    curve_data = main_window.multi_point_controller.tracked_data[curve_name]
                    main_window.curve_widget.set_curve_data(curve_data)

        # Update timeline
        if main_window.update_timeline_tabs is not None:
            main_window.update_timeline_tabs(main_window.multi_point_controller.tracked_data[curve_name])

    def _update_ui_new_curve(self, main_window: MainWindowProtocol, curve_name: str) -> None:
        """Update UI after creating a new averaged curve.

        Args:
            main_window: Reference to main window
            curve_name: Name of new curve
        """
        # Update tracking panel
        if main_window.multi_point_controller is not None:
            main_window.multi_point_controller.update_tracking_panel()

        # Set as active curve - always do this for newly created curves
        main_window.active_timeline_point = curve_name

        # Get curve data (needed for both curve widget and timeline updates)
        curve_data = main_window.multi_point_controller.tracked_data[curve_name]

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
        try:
            if not self.executed:
                return False

            controller = main_window.multi_point_controller
            tracked_data = controller.tracked_data

            # Scenario 3: Remove created curve
            if self.scenario == 3 and self.created_curve_name:
                if self.created_curve_name in tracked_data:
                    del tracked_data[self.created_curve_name]
                    logger.info(f"Removed averaged curve '{self.created_curve_name}'")

            # Scenarios 1 & 2: Restore original data
            for curve_name, original_data in self.original_data.items():
                tracked_data[curve_name] = copy.deepcopy(original_data)
                self._update_ui(main_window, curve_name)

            # Update tracking panel
            if main_window.multi_point_controller is not None:
                main_window.multi_point_controller.update_tracking_panel()

            self.executed = False
            logger.info("Insert Track undone")
            return True

        except Exception as e:
            logger.error(f"Error undoing Insert Track: {e}")
            return False

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo Insert Track operation.

        Args:
            main_window: Reference to main window

        Returns:
            True if successful
        """
        try:
            controller = main_window.multi_point_controller
            tracked_data = controller.tracked_data

            # Scenario 3: Re-add created curve
            if self.scenario == 3 and self.created_curve_name:
                tracked_data[self.created_curve_name] = copy.deepcopy(self.new_data[self.created_curve_name])
                self._update_ui_new_curve(main_window, self.created_curve_name)

            # Scenarios 1 & 2: Re-apply new data
            for curve_name, new_data in self.new_data.items():
                if curve_name != self.created_curve_name:  # Skip scenario 3's created curve
                    tracked_data[curve_name] = copy.deepcopy(new_data)
                    self._update_ui(main_window, curve_name)

            # Update tracking panel
            if main_window.multi_point_controller is not None:
                main_window.multi_point_controller.update_tracking_panel()

            self.executed = True
            logger.info("Insert Track redone")
            return True

        except Exception as e:
            logger.error(f"Error redoing Insert Track: {e}")
            return False
