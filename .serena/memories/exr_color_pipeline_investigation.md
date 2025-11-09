# EXR Color Pipeline Investigation

## Current Color Pipeline: EXR Load to Display

### 1. EXR LOADING PIPELINE

**Entry Point**: `io_utils/exr_loader.py`

**Load Chain**:
1. User loads EXR via UI → `load_exr_as_qimage(file_path)`
2. Tries multiple backends in order:
   - OpenImageIO (OIIO) - preferred in VFX facilities
   - OpenEXR (official library)
   - Pillow (if compiled with EXR support)
   - imageio (fallback auto-detection)

3. Each backend reads EXR as **float32 HDR data** (values can exceed 1.0)

4. **All backends apply `_tone_map_hdr()`** before conversion to 8-bit

### 2. TONE MAPPING IMPLEMENTATION

**Function**: `_tone_map_hdr()` (lines 382-444 in exr_loader.py)

**Current Process**:
1. **Negative value clamping**: `np.maximum(img_data, 0)` 
2. **Exposure adjustment** (luminance-based):
   - Calculates median brightness (50th percentile)
   - Target mid-gray: 0.18 (standard 18% gray)
   - Exposure = target_mid_gray / mid_gray
   - Clamped to range [0.5, 4.0] to prevent extreme brightening
3. **Apply exposure**: `img_data * exposure`
4. **Soft clipping for highlights**:
   - Linear pass-through for values ≤ 1.0
   - Exponential rolloff for values > 1.0: `1.0 - exp(-(img_data - 1.0))`
5. **Gamma correction** (linear → sRGB):
   - Standard gamma = 2.2
   - Formula: `img_data ^ (1.0 / 2.2)`
6. **Channel handling**:
   - Grayscale → RGB (replicate 3x)
   - Single channel → RGB
   - RGBA → RGB (drops alpha)
7. **Final safety clamp**: [0.0, 1.0]

### 3. BACKEND-SPECIFIC COLOR HANDLING

#### OpenImageIO (OIIO) Backend
- Reads pixels as `oiio.FLOAT`
- Extracts RGB channels directly (or grayscale)
- Applies `_tone_map_hdr()` to entire image

#### OpenEXR (Official) Backend
- Reads R, G, B channels separately using `Imath.PixelType.FLOAT`
- Stacks channels into numpy array
- Applies `_tone_map_hdr()`

#### Pillow Backend
- Opens EXR and converts to RGB mode
- Normalizes if max > 1.0: `img_data / 255.0`
- **ISSUE**: Normalizes by 255 if max > 1.0, but EXR max could be >255

#### imageio Backend
- Auto-detects available plugins
- Direct imread (format conversion not explicit)
- Applies `_tone_map_hdr()`

### 4. DISPLAY PIPELINE

**Data Flow**:
1. Tone-mapped float32 [0.0, 1.0] → 8-bit uint8 [0-255]
2. Create QImage: `Format_RGB888` or `Format_RGBA8888`
3. Copy image data to ensure persistence
4. Convert to QPixmap: `QPixmap.fromImage(qimage)`
5. Display in CurveViewWidget or preview widgets

**Cache Path**:
- `SafeImageCacheManager` stores QImage (thread-safe)
- Main thread converts QImage → QPixmap for display
- LRU eviction with configurable cache size

## IDENTIFIED ISSUES & LIMITATIONS

### 1. COLOR SPACE ISSUES

**Issue**: No explicit color space handling
- EXR files may be in linear color space (no gamma)
- Current tone mapping assumes linear input
- No ICC profile support
- No color space conversion metadata preserved

**Impact**: 
- Colors may appear incorrect if EXR uses specific color profile
- No distinction between linear and sRGB EXRs

### 2. TONE MAPPING AGGRESSIVENESS

**Issue**: Percentile-based exposure (median/50th percentile) can be too aggressive
- Very dark images with few bright pixels will brighten excessively
- Very bright images with few dark pixels will darken excessively
- Exposure clamp [0.5, 4.0] is arbitrary

**Impact**:
- Bright/overexposed images become muddy
- Dark/underexposed images become washed out
- Loss of detail in highlights and shadows

### 3. GAMMA CORRECTION INFLEXIBILITY

**Issue**: Hard-coded gamma 2.2 for all content
- Different monitors/platforms may need different gamma
- No user control or preference system
- No distinction between sRGB and linear content

### 4. PILLOW BACKEND NORMALIZATION BUG

**Issue** (line 255):
```python
img_data = _tone_map_hdr(img_data / 255.0 if img_data.max() > 1.0 else img_data)
```

This logic is **backwards**:
- Divides by 255 if max > 1.0 (wrong - max > 1.0 is already normalized)
- Doesn't divide if max ≤ 1.0 (but should handle both 0-1 and 0-255 ranges)

### 5. ALPHA CHANNEL LOSS

**Issue**: RGBA images have alpha dropped during conversion
- No alpha blending against background
- No transparency information preserved
- Different from sRGB with alpha support

### 6. NO HDR METADATA PRESERVATION

**Issue**: No metadata from EXR preserved
- Exposure time
- White point
- Chromacity
- Color rendering intent
- All lost after tone mapping

### 7. INCONSISTENT BACKEND NORMALIZATION

**Issue**: Different backends may normalize differently
- OIIO: Direct float32 read
- OpenEXR: Direct float32 read
- Pillow: May return 0-255 or 0-1 range
- imageio: Depends on plugin (unpredictable)

Result: Same EXR may display differently depending on which backend loads it

## MISSING FEATURES

1. **Exposure control UI**: Users can't adjust tone mapping aggressiveness
2. **Gamma slider**: No user control over gamma correction
3. **Highlight recovery**: No per-channel clipping or soft clipping controls
4. **Shadow lifting**: No shadow detail recovery
5. **Color space selector**: Can't specify input color space
6. **Metadata display**: No way to see EXR metadata (exposure, etc.)
7. **HDR histogram**: No visualization of HDR value distribution
8. **White balance**: No color temperature adjustment

## FILE LOCATIONS

### EXR Loading
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/io_utils/exr_loader.py` - Main loader with backends
- Functions: `load_exr_as_qimage()`, `load_exr_as_qpixmap()`, `_tone_map_hdr()`
- Backends: `_load_exr_with_oiio()`, `_load_exr_with_openexr()`, `_load_exr_with_pillow()`, `_load_exr_with_imageio()`

### Color Management  
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/color_manager.py` - Theme colors (does NOT handle EXR display colors)

### Image Caching
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/services/image_cache_manager.py` - SafeImageCacheManager
- Method: `_load_image_from_disk()` (line 280) calls exr_loader

### Display
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/curve_view_widget.py` - Renders background image
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/services/data_service.py` - get_background_image()

### Tests
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_exr_loader.py` - Tests (basic coverage)

## COMPATIBILITY NOTES

### VFX Facility Deployment
- Documented in CLAUDE.md (EXR Backend Priority section)
- Tested configuration: `rez env oiio-3.0.4.0 ... -- python3 main.py`
- EXR support gracefully degrades if backends unavailable
- Diagnostic tools: check_exr_backends.py, test_imageio_exr.py, test_rez_exr_packages.sh

## SUMMARY

The current EXR implementation is **functionally complete but color-management naive**:
- ✅ Successfully loads EXRs from multiple backends
- ✅ Basic HDR→LDR tone mapping prevents overexposure
- ✅ Thread-safe caching and background loading
- ❌ No color space awareness
- ❌ No user controls for tone mapping
- ❌ Tone mapping aggressiveness may be incorrect for varied content
- ❌ Pillow backend has normalization logic bug
- ❌ No metadata preservation
- ❌ Inconsistent inter-backend behavior