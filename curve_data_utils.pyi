from typing import List, Tuple, Sequence

# curve_data is list of (frame, x, y, type)
def compute_interpolated_curve_data(
    curve_data: List[Tuple[int, float, float, str]],
    selected_indices: Sequence[int]
) -> List[Tuple[int, float, float, str]]: ...
