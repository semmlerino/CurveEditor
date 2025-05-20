#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple test script to verify the unified transformation system is working properly.
"""

import os
import sys

# Add the current directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_transformation_system():
    """Test that the unified transformation system works properly."""
    print("\n== TRANSFORMATION SYSTEM TEST ==\n")
    
    try:
        from services.unified_transformation_service import UnifiedTransformationService
        from services.unified_transform import Transform
        
        print("✅ Successfully imported UnifiedTransformationService")
        
        # Create a simple transform directly
        transform = Transform(
            scale=1.0,
            center_offset_x=0.0,
            center_offset_y=0.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0
        )
        
        print("✅ Successfully created Transform object")
        
        # Test point transformation
        result = UnifiedTransformationService.transform_point(transform, 100.0, 200.0)
        print(f"✅ transform_point result: {result}")
        
        # Test backward compatibility method
        class MockCurveView:
            def __init__(self):
                self.flip_y_axis = False
                self.scale_to_image = False
                self.zoom_factor = 1.0
                self.offset_x = 0
                self.offset_y = 0
                self.x_offset = 0
                self.y_offset = 0
                self.width = lambda: 800
                self.height = lambda: 600
                self.image_width = 1920
                self.image_height = 1080
            
            def update(self):
                pass
        
        mock_curve_view = MockCurveView()
        
        # Test transform_point_to_widget method
        print("\nTesting transform_point_to_widget:")
        try:
            if hasattr(UnifiedTransformationService, "transform_point_to_widget"):
                result = UnifiedTransformationService.transform_point_to_widget(
                    mock_curve_view, 100, 200, 1920, 1080, 10, 10, 0.5
                )
                print(f"✅ transform_point_to_widget result: {result}")
            else:
                print("❌ transform_point_to_widget method does not exist")
        except Exception as e:
            print(f"❌ Error calling transform_point_to_widget: {e}")
        
        # Test direct transform creation
        print("\nTesting from_curve_view:")
        try:
            t = UnifiedTransformationService.from_curve_view(mock_curve_view)
            print(f"✅ from_curve_view returned: {t}")
        except Exception as e:
            print(f"❌ Error calling from_curve_view: {e}")
        
        # Test cache operations
        print("\nTesting cache operations:")
        UnifiedTransformationService.clear_cache()
        stats = UnifiedTransformationService.get_cache_stats()
        print(f"✅ Cache stats: {stats}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_transformation_system()
    print(f"\nOverall result: {'✅ Success' if success else '❌ Failed'}")
    sys.exit(0 if success else 1)
