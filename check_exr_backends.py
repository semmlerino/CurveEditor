#!/usr/bin/env python3
"""
Diagnostic script to check which EXR backends are available.
Run this in your Rez environment to find which package provides EXR support.
"""

print("=" * 60)
print("EXR Backend Availability Check")
print("=" * 60)

# Check OpenImageIO
print("\n1. OpenImageIO (OIIO):")
try:
    import OpenImageIO as oiio
    print(f"   ✓ Available - version: {oiio.VERSION_STRING if hasattr(oiio, 'VERSION_STRING') else 'unknown'}")
except ImportError as e:
    print(f"   ✗ Not available: {e}")

# Check OpenEXR
print("\n2. OpenEXR:")
try:
    import Imath
    import OpenEXR
    version = OpenEXR.__version__ if hasattr(OpenEXR, '__version__') else 'unknown'
    print(f"   ✓ Available - version: {version}")
except ImportError as e:
    print(f"   ✗ Not available: {e}")

# Check Pillow EXR support
print("\n3. Pillow (with EXR support):")
try:
    from PIL import Image, features
    print(f"   Pillow version: {Image.__version__ if hasattr(Image, '__version__') else 'unknown'}")

    # Try to register EXR plugin if available
    try:
        from PIL import ExrImagePlugin
        print("   ✓ EXR plugin available")
    except ImportError:
        print("   ✗ EXR plugin not available")

except ImportError as e:
    print(f"   ✗ Pillow not available: {e}")

# Check imageio
print("\n4. imageio:")
try:
    import imageio
    print(f"   ✓ Available - version: {imageio.__version__}")

    # List available plugins
    try:
        import imageio.v3 as iio
        print("   Checking for EXR-capable plugins...")

        # Try to get known formats
        try:
            known_formats = iio.formats.known_extensions
            if '.exr' in known_formats:
                plugins = known_formats['.exr']
                print(f"   EXR plugins: {plugins}")
        except Exception:
            print("   Could not enumerate plugins")

    except ImportError:
        print("   imageio v3 API not available")

except ImportError as e:
    print(f"   ✗ Not available: {e}")

print("\n" + "=" * 60)
print("Recommendations:")
print("=" * 60)

print("""
Common Rez packages for EXR support (try adding to your rez command):
  - OpenImageIO (or oiio)
  - OpenEXR (or openexr)
  - ilmbase or Imath (may be bundled with OpenEXR)

Example rez commands to test:
  rez env OpenImageIO PySide6_Essentials pillow ... -- python3 check_exr_backends.py
  rez env openexr PySide6_Essentials pillow ... -- python3 check_exr_backends.py
  rez env oiio PySide6_Essentials pillow ... -- python3 check_exr_backends.py

To search for available packages:
  rez search OpenImageIO
  rez search openexr
  rez search oiio
""")
