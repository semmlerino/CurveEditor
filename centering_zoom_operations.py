class ZoomOperations:
    @staticmethod
    def calculate_centering_offsets(widget_width, widget_height, display_width, display_height, offset_x=0, offset_y=0):
        """Calculate centering offsets for a view.
        Args:
            widget_width: Width of the widget
            widget_height: Height of the widget
            display_width: Width of the content/image
            display_height: Height of the content/image
            offset_x: Additional X offset (default 0)
            offset_y: Additional Y offset (default 0)
        Returns:
            (offset_x, offset_y): Centering offsets to apply
        """
        cx = (widget_width - (display_width)) / 2 + offset_x
        cy = (widget_height - (display_height)) / 2 + offset_y
        return cx, cy


    @staticmethod
    def center_on_selected_point(curve_view, point_idx=-1, preserve_zoom=True):
        """Center the view on the specified point index.

        If no index is provided, uses the currently selected point.

        Args:
            curve_view: The curve view instance
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.

        Returns:
            bool: True if centering was successful, False otherwise
        """
        # Get the target point index
        idx = point_idx if point_idx >= 0 else getattr(curve_view, "selected_point_idx", -1)
        
        # Validate curve data availability
        if idx < 0 or not hasattr(curve_view, 'main_window') or not getattr(curve_view.main_window, "curve_data", None):
            return False
            
        try:
            if idx < len(curve_view.main_window.curve_data):
                point = curve_view.main_window.curve_data[idx]
                _, x, y = point[:3]
                curve_view.selected_point_idx = idx
                
                # Set zoom level
                current_zoom = curve_view.zoom_factor if preserve_zoom else 1.0
                if not preserve_zoom:
                    ZoomOperations.reset_view(curve_view)
                    
                # Calculate view dimensions
                widget_width = curve_view.width()
                widget_height = curve_view.height()
                display_width = getattr(curve_view, "image_width", widget_width)
                display_height = getattr(curve_view, "image_height", widget_height)
                
                if getattr(curve_view, "background_image", None):
                    display_width = curve_view.background_image.width()
                    display_height = curve_view.background_image.height()
                    
                # Calculate scaling
                scale_x = widget_width / display_width
                scale_y = widget_height / display_height
                
                if preserve_zoom:
                    scale = min(scale_x, scale_y) * current_zoom
                else:
                    scale = min(scale_x, scale_y) * curve_view.zoom_factor
                    
                # Calculate offsets
                offset_x, offset_y = ZoomOperations.calculate_centering_offsets(widget_width, widget_height, display_width * scale, display_height * scale)
                
                # Calculate transformed point position
                if getattr(curve_view, "scale_to_image", False):
                    img_x = x * (display_width / curve_view.image_width)
                    img_y = y * (display_height / curve_view.image_height)
                    tx = offset_x + img_x * scale
                    
                    if getattr(curve_view, "flip_y_axis", False):
                        ty = offset_y + (display_height - img_y) * scale
                    else:
                        ty = offset_y + img_y * scale
                else:
                    tx = offset_x + x * scale
                    
                    if getattr(curve_view, "flip_y_axis", False):
                        ty = offset_y + (curve_view.image_height - y) * scale
                    else:
                        ty = offset_y + y * scale
                
                # Center point in view
                center_x = widget_width / 2
                center_y = widget_height / 2
                delta_x = center_x - tx
                delta_y = center_y - ty
                
                curve_view.offset_x = delta_x
                curve_view.offset_y = delta_y
                curve_view.update()
                return True
            else:
                return False
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def fit_selection(curve_view):
        """Fit the view to the bounding box of all selected points."""
        selected_points = getattr(curve_view, "selected_points", None)
        points = getattr(curve_view, "points", None)
        
        if (
            selected_points is not None
            and points is not None
            and len(selected_points) > 1
        ):
            xs = []
            ys = []
            for idx in selected_points:
                if 0 <= idx < len(points):
                    pt = points[idx]
                    x = pt[1]
                    y = pt[2]
                    xs.append(x)
                    ys.append(y)
                    
            if xs and ys:
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                bbox_width = max_x - min_x
                bbox_height = max_y - min_y
                
                # Add margins (25% of bbox size)
                margin_x = bbox_width * 0.25 if bbox_width > 0 else 10.0
                margin_y = bbox_height * 0.25 if bbox_height > 0 else 10.0
                min_x -= margin_x
                max_x += margin_x
                min_y -= margin_y
                max_y += margin_y
                
                bbox_width = max_x - min_x
                bbox_height = max_y - min_y
                
                widget_width = curve_view.width()
                widget_height = curve_view.height()
                display_width = getattr(curve_view, "image_width", widget_width)
                display_height = getattr(curve_view, "image_height", widget_height)
                
                # Calculate scale to fit bbox
                scale_x = widget_width / bbox_width if bbox_width > 0 else 1.0
                scale_y = widget_height / bbox_height if bbox_height > 0 else 1.0
                scale = min(scale_x, scale_y)
                scale = max(0.1, min(50.0, scale))  # Clamp scale
                
                # Calculate center point
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                
                # Set new zoom level
                curve_view.zoom_factor = scale
                
                # Calculate centering offsets
                widget_cx = widget_width / 2
                widget_cy = widget_height / 2
                
                # Handle coordinate transforms
                if getattr(curve_view, "background_image", None) and getattr(curve_view, "scale_to_image", False):
                    img_x = center_x + getattr(curve_view, "x_offset", 0)
                    img_y = center_y + getattr(curve_view, "y_offset", 0)
                    tx = 0 + img_x * scale
                    
                    if getattr(curve_view, "flip_y_axis", False):
                        ty = 0 + (display_height - img_y) * scale
                    else:
                        ty = 0 + img_y * scale
                else:
                    tx = 0 + center_x * scale
                    
                    if getattr(curve_view, "flip_y_axis", False):
                        ty = 0 + (display_height - center_y) * scale
                    else:
                        ty = 0 + center_y * scale
                
                # Set final offset
                curve_view.offset_x = widget_cx - tx
                curve_view.offset_y = widget_cy - ty
                
                # Mark as a fit operation
                curve_view.last_action_was_fit = True
                curve_view.update()
                return True
        return False

    @staticmethod
    def reset_view(curve_view):
        """Reset view to default state (zoom and position)."""
        curve_view.zoom_factor = 1.0
        
        # Reset all offset attributes
        for attr in ['x_offset', 'y_offset', 'offset_x', 'offset_y']:
            if hasattr(curve_view, attr):
                setattr(curve_view, attr, 0)
                
        curve_view.update()

    @staticmethod
    def zoom_view(curve_view, factor, mouse_x=None, mouse_y=None):
        """Zoom the view while keeping the mouse position fixed.

        Args:
            curve_view: The curve view instance
            factor: Zoom factor (> 1 to zoom in, < 1 to zoom out)
            mouse_x: X-coordinate to zoom around, if None uses center
            mouse_y: Y-coordinate to zoom around, if None uses center
        """
        old_zoom = curve_view.zoom_factor
        
        # Check if we should skip multi-selection handling
        skip_multi_selection = hasattr(curve_view, "last_action_was_fit") and getattr(curve_view, "last_action_was_fit", False)
        selected_points = getattr(curve_view, "selected_points", None)
        points = getattr(curve_view, "points", None)
        
        
        # Regular zoom handling for single point or no selection
        curve_view.zoom_factor = max(0.1, min(50.0, curve_view.zoom_factor * factor))
        
        # Handle mouse-centered zooming
        if mouse_x is not None and mouse_y is not None:
            widget_width = curve_view.width()
            widget_height = curve_view.height()
            zoom_ratio = factor - 1.0
            center_x = widget_width / 2
            center_y = widget_height / 2
            dx = mouse_x - center_x
            dy = mouse_y - center_y
            curve_view.offset_x -= dx * zoom_ratio
            curve_view.offset_y -= dy * zoom_ratio
        # If no mouse position but we have a selected point, center on it
        elif hasattr(curve_view, 'selected_point_idx') and curve_view.selected_point_idx >= 0:
            ZoomOperations.center_on_selected_point(curve_view, curve_view.selected_point_idx, preserve_zoom=True)
            
        # Reset the fit flag if it exists
        if hasattr(curve_view, "last_action_was_fit"):
            curve_view.last_action_was_fit = False
        
        curve_view.update()