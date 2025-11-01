#!/bin/bash
# Test different Rez package combinations to find which one can load EXR files
# Usage: ./test_rez_exr_packages.sh /path/to/file.exr

EXR_FILE="${1:-/shows/jack_ryan/shots/TB_090/TB_090_0020/publish/turnover/plate/input_plate/FG01/v001/exr/4312x2304/TB_090_0020_turnover-plate_FG01_lin_sgamut3cine_v001.1181.exr}"

echo "=========================================="
echo "Testing EXR Loading with Rez Packages"
echo "=========================================="
echo "EXR file: $EXR_FILE"
echo ""

# Base packages needed for the app
BASE_PACKAGES="PySide6_Essentials pillow typing_extensions psutil imageio numpy Jinja2"

# Array of packages to test
declare -a TEST_PACKAGES=(
    "oiio-3.0.1.0.py311"
    "oiio-3.0.4.0"
    "oiio-2.5.16.0"
    "openexr-3.3.2"
    "openexr-3.3.1"
    "openexr-3.2.4"
    "openexr-3.1.11"
)

# Create a Python test script
cat > /tmp/test_exr_load.py << 'PYEOF'
import sys
import os

exr_path = sys.argv[1] if len(sys.argv) > 1 else ""

if not os.path.exists(exr_path):
    print(f"ERROR: File not found: {exr_path}")
    sys.exit(1)

print(f"Testing: {exr_path}")

success = False

# Test OpenImageIO
try:
    import OpenImageIO as oiio
    print(f"  Trying OpenImageIO {oiio.VERSION_STRING if hasattr(oiio, 'VERSION_STRING') else 'unknown'}...")

    img_input = oiio.ImageInput.open(exr_path)
    if img_input:
        spec = img_input.spec()
        pixels = img_input.read_image(oiio.FLOAT)
        img_input.close()
        if pixels is not None:
            print(f"  ✓ SUCCESS with OpenImageIO! ({spec.width}x{spec.height}, {spec.nchannels} channels)")
            success = True
except ImportError:
    print("  OpenImageIO not available")
except Exception as e:
    print(f"  OpenImageIO failed: {e}")

# Test OpenEXR if OIIO didn't work
if not success:
    try:
        import OpenEXR
        import Imath
        print(f"  Trying OpenEXR...")

        exr_file = OpenEXR.InputFile(exr_path)
        header = exr_file.header()
        dw = header["dataWindow"]
        width = dw.max.x - dw.min.x + 1
        height = dw.max.y - dw.min.y + 1

        # Try to read a channel
        channels = list(header["channels"].keys())
        if channels:
            float_type = Imath.PixelType(Imath.PixelType.FLOAT)
            data = exr_file.channel(channels[0], float_type)
            if data:
                print(f"  ✓ SUCCESS with OpenEXR! ({width}x{height}, channels: {channels})")
                success = True
    except ImportError:
        print("  OpenEXR not available")
    except Exception as e:
        print(f"  OpenEXR failed: {e}")

# Test imageio as fallback
if not success:
    try:
        import imageio.v3 as iio
        print(f"  Trying imageio...")

        img_data = iio.imread(exr_path)
        print(f"  ✓ SUCCESS with imageio! (shape: {img_data.shape})")
        success = True
    except Exception as e:
        print(f"  imageio failed: {e}")

if success:
    print("  RESULT: ✓ EXR LOADED SUCCESSFULLY")
    sys.exit(0)
else:
    print("  RESULT: ✗ ALL METHODS FAILED")
    sys.exit(1)
PYEOF

echo "Testing packages..."
echo ""

WORKING_PACKAGES=()

for PKG in "${TEST_PACKAGES[@]}"; do
    echo "----------------------------------------"
    echo "Testing: $PKG"
    echo "----------------------------------------"

    # Run the test with this package
    rez env $PKG $BASE_PACKAGES -- python3 /tmp/test_exr_load.py "$EXR_FILE" 2>&1

    if [ $? -eq 0 ]; then
        WORKING_PACKAGES+=("$PKG")
        echo "✓ $PKG WORKS!"
    else
        echo "✗ $PKG failed"
    fi
    echo ""
done

echo "=========================================="
echo "RESULTS SUMMARY"
echo "=========================================="
if [ ${#WORKING_PACKAGES[@]} -eq 0 ]; then
    echo "✗ No working packages found!"
    echo ""
    echo "Next steps:"
    echo "  1. Verify the EXR file exists and is readable"
    echo "  2. Check rez search results for other versions"
    echo "  3. Contact VFX support for EXR-capable packages"
else
    echo "✓ Working packages:"
    for PKG in "${WORKING_PACKAGES[@]}"; do
        echo "  - $PKG"
    done
    echo ""
    echo "Recommended launch command:"
    echo "rez env ${WORKING_PACKAGES[0]} $BASE_PACKAGES -- SHOTBOT_DEBUG_LEVEL=all python3 /nethome/gabriel-h/Python/CurveEditor/curveeditor_bundle_temp/main.py"
fi
echo "=========================================="

# Cleanup
rm -f /tmp/test_exr_load.py
