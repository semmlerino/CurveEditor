#!/usr/bin/env python3
"""
Test if imageio can actually load an EXR file.
Usage: python3 test_imageio_exr.py /path/to/file.exr
"""

import sys

if len(sys.argv) < 2:
    print("Usage: python3 test_imageio_exr.py /path/to/file.exr")
    sys.exit(1)

exr_path = sys.argv[1]

print(f"Testing EXR load: {exr_path}")
print("=" * 60)

# Test imageio
try:
    import imageio
    import imageio.v3 as iio
    print(f"imageio version: {imageio.__version__}")

    # Try to list available plugins
    print("\nAttempting to load with imageio...")
    try:
        img_data = iio.imread(exr_path)
        print(f"✓ SUCCESS! Loaded EXR: shape={img_data.shape}, dtype={img_data.dtype}")
        print(f"  Value range: [{img_data.min():.4f}, {img_data.max():.4f}]")
    except Exception as e:
        print(f"✗ FAILED: {e}")

        # Try with explicit plugins
        print("\nTrying with explicit plugin hints...")
        for plugin_name in ['pillow', 'GDAL', 'tifffile']:
            try:
                print(f"  Trying plugin={plugin_name}...")
                img_data = iio.imread(exr_path, plugin=plugin_name)
                print(f"  ✓ SUCCESS with {plugin_name}! shape={img_data.shape}")
                break
            except Exception as e2:
                print(f"    ✗ {plugin_name} failed: {e2}")

except ImportError as e:
    print(f"✗ imageio not available: {e}")

print("\n" + "=" * 60)
print("If all methods failed, you need to add a Rez package:")
print("  rez search openimageio")
print("  rez search openexr")
print("  rez search oiio")
