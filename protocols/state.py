#!/usr/bin/env python
"""
Focused protocols for ApplicationState (Interface Segregation Principle).

These protocols allow clients to depend on minimal interfaces rather than
the entire ApplicationState class. This improves testability, reduces coupling,
and makes dependencies explicit.

Usage:
    # Instead of depending on full ApplicationState:
    def some_function(state: ApplicationState):
        frame = state.current_frame  # Uses 1 of 50+ methods

    # Depend on minimal protocol:
    def some_function(frames: FrameProvider):
        frame = frames.current_frame  # Clear dependency

    # Easy to mock in tests:
    class MockFrameProvider:
        current_frame: int = 42

    test_some_function(MockFrameProvider())  # 1 line mock vs 50+ method mock
"""

from typing import Protocol, runtime_checkable

from PySide6.QtCore import Signal

from core.type_aliases import CurveDataList


@runtime_checkable
class FrameProvider(Protocol):
    """Provides current frame information.

    Use this protocol when components only need to read the current frame.
    Avoids depending on the entire ApplicationState interface.

    Example:
        class FrameDisplay:
            def __init__(self, frames: FrameProvider):
                self._frames = frames

            def show_frame(self):
                print(f"Current frame: {self._frames.current_frame}")
    """

    @property
    def current_frame(self) -> int:
        """Get the current frame number."""
        ...


@runtime_checkable
class CurveDataProvider(Protocol):
    """Provides read-only access to curve data.

    Use this protocol when components only need to read curve data.
    Prevents accidental modifications and clarifies intent.

    Example:
        class CurveAnalyzer:
            def __init__(self, data: CurveDataProvider):
                self._data = data

            def analyze(self, curve_name: str):
                curve_data = self._data.get_curve_data(curve_name)
                # Read-only analysis...
    """

    def get_curve_data(self, curve_name: str | None = None) -> CurveDataList:
        """Get curve data by name."""
        ...

    def get_all_curve_names(self) -> list[str]:
        """Get list of all curve names."""
        ...

    @property
    def active_curve(self) -> str | None:
        """Get the currently active curve name."""
        ...


@runtime_checkable
class CurveDataModifier(Protocol):
    """Provides write access to curve data.

    Use this protocol when components need to modify curve data.
    Clearly indicates mutating operations.

    Example:
        class CurveEditor:
            def __init__(self, data: CurveDataModifier):
                self._data = data

            def smooth_curve(self, curve_name: str, smoothed_data: CurveDataList):
                self._data.set_curve_data(curve_name, smoothed_data)
    """

    def set_curve_data(self, curve_name: str, data: CurveDataList) -> None:
        """Set curve data by name."""
        ...

    def delete_curve(self, curve_name: str) -> None:
        """Delete a curve."""
        ...


@runtime_checkable
class SelectionProvider(Protocol):
    """Provides read-only access to selection state.

    Use this protocol when components only need to read selection.

    Example:
        class SelectionDisplay:
            def __init__(self, selection: SelectionProvider):
                self._selection = selection
                selection.selection_changed.connect(self._on_selection_changed)

            def show_selection(self, curve_name: str):
                indices = self._selection.get_selection(curve_name)
                print(f"Selected: {indices}")
    """

    def get_selection(self, curve_name: str | None = None) -> set[int]:
        """Get selected point indices for curve."""
        ...

    selection_changed: Signal
    """Signal emitted when selection changes."""


@runtime_checkable
class SelectionModifier(Protocol):
    """Provides write access to selection state.

    Use this protocol when components need to modify selection.

    Example:
        class SelectionTool:
            def __init__(self, selection: SelectionModifier):
                self._selection = selection

            def select_point(self, curve_name: str, index: int):
                self._selection.set_selection(curve_name, {index})
    """

    def set_selection(self, curve_name: str, indices: set[int]) -> None:
        """Set selected point indices for curve."""
        ...

    def clear_selection(self, curve_name: str | None = None) -> None:
        """Clear selection for curve."""
        ...


@runtime_checkable
class ImageSequenceProvider(Protocol):
    """Provides read-only access to image sequence information.

    Use this protocol when components need image sequence data.

    Example:
        class ImageDisplay:
            def __init__(self, images: ImageSequenceProvider):
                self._images = images

            def load_current_image(self):
                files = self._images.get_image_files()
                directory = self._images.get_image_directory()
                # Load image...
    """

    def get_image_files(self) -> list[str]:
        """Get list of image file paths."""
        ...

    def get_image_directory(self) -> str | None:
        """Get directory containing images."""
        ...

    def get_total_frames(self) -> int:
        """Get total number of frames in sequence."""
        ...


# Composite protocols for common use cases

@runtime_checkable
class CurveState(CurveDataProvider, CurveDataModifier, Protocol):
    """Combined read/write access to curve data.

    Use this when component needs both read and write access.
    Still more focused than full ApplicationState.
    """
    pass


@runtime_checkable
class SelectionState(SelectionProvider, SelectionModifier, Protocol):
    """Combined read/write access to selection.

    Use this when component needs both read and write selection access.
    """
    pass


@runtime_checkable
class FrameAndCurveProvider(FrameProvider, CurveDataProvider, Protocol):
    """Provides frame and curve read access.

    Use this when component needs both frame and curve data for rendering
    or analysis operations.

    Example:
        class CurveRenderer:
            def __init__(self, state: FrameAndCurveProvider):
                self._state = state

            def render(self, curve_name: str):
                frame = self._state.current_frame
                data = self._state.get_curve_data(curve_name)
                # Render curve at frame...
    """
    pass
