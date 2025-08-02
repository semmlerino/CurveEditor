from typing import Any

class ZoomOperations:
    @staticmethod
    def reset_view(curve_view: Any) -> None: ...
    @staticmethod
    def zoom_view(
        curve_view: Any, factor: float, mouse_x: float | None = None, mouse_y: float | None = None
    ) -> None: ...
    @staticmethod
    def handle_wheel_event(curve_view: Any, event: Any) -> None: ...
    @staticmethod
    def center_on_selected_point(curve_view: Any, point_idx: int = -1, preserve_zoom: bool = True) -> bool: ...
    @staticmethod
    def fit_selection(curve_view: Any) -> bool: ...
    @staticmethod
    def calculate_centering_offsets(
        widget_width: float,
        widget_height: float,
        display_width: float,
        display_height: float,
        offset_x: float = 0,
        offset_y: float = 0,
    ) -> tuple[float, float]: ...
