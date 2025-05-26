from typing import Protocol, Any, List

from services.protocols import PointsList

class BatchEditParentProtocol(Protocol):
    curve_view: Any
    curve_data: PointsList
    selected_indices: List[int]
    image_width: int
    image_height: int
    point_edit_layout: Any
    statusBar: Any
    add_to_history: Any
    update_curve_data: Any
    batch_edit_group: Any
    scale_button: Any
    offset_button: Any
    rotate_button: Any
    smooth_button: Any
    select_all_button: Any
