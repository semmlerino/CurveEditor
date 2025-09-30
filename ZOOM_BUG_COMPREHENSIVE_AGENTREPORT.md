# Comprehensive Agent Report: Zoom-Float Bug Analysis
*Generated: January 2025*

## Executive Summary

Six specialized agents performed deep code review of the CurveEditor zoom system. The zoom-float bug persists due to multiple compounding issues, with overcomplicated architecture masking the root causes. The codebase has grown to 10 abstraction layers for what should be a simple coordinate transformation.

## Critical Findings: What Is Broken

### 1. PRIMARY BUG: Scale Compounding Mismatch
**Location**: `ui/curve_view_widget.py:534-567`
- Widget calculates `total_scale = fit_scale * zoom_factor`
- Passes compound scale as ViewState.zoom_factor
- Transform treats this as simple zoom, not compound
- **Impact**: Curves drift because pan adjustments assume wrong scale basis

### 2. Integer Precision Loss
**Location**: `services/transform_service.py:141-144`
- ViewState uses `int` for display_width/height (should be `float`)
- Sub-pixel precision lost during conversions
- **Impact**: Cumulative drift from rounding errors

### 3. Transform Cache Invalidation Race
**Location**: `ui/curve_view_widget.py:1042-1043`
- Cache cleared → Transform rebuilt with NEW zoom but OLD pan
- Pan adjustment calculated from wrong base position
- **Impact**: Incorrect pan compensation during zoom

### 4. Mathematical Errors
**Location**: `services/transform_service.py:733-736`
- Division by zero check threshold mismatch (1e-10 vs 1e-9)
- Unused zoom_ratio calculation indicates incomplete logic
- Pre-calculated values can become stale
- **Impact**: Potential crashes and incorrect transformations

### 5. Type Safety Collapse
- 43 `Any` type warnings destroying type information
- `hasattr()` usage prevents static analysis (16 instances)
- `cast()` operations causing precision loss (12 consecutive casts)
- **Impact**: Silent type mismatches causing coordinate drift

## Architecture Problems: Overcomplicated Design

### Abstraction Layer Count: 10 Layers
1. Mouse wheel event
2. CurveViewWidget.wheelEvent()
3. CurveViewWidget.get_transform()
4. ViewState.from_curve_view() (16 hasattr checks)
5. ViewState.quantized_for_cache()
6. TransformService.create_transform_from_view_state()
7. TransformService._create_transform_cached()
8. TransformService._create_transform_cached_explicit() (13 params)
9. Transform.__init__() (200+ lines validation)
10. Transform.data_to_screen()

**Actual needed**: 3 layers maximum

### Code Volume vs Value
- **Transform system**: 2,000+ lines
- **Essential logic**: ~20 lines
- **Overhead ratio**: 100:1

### Dead/Unused Code
- `CacheConfig`: Defined but never used (18 lines)
- `stability_hash`: Computed but rarely used
- `manual_offset_x/y`: Almost always 0
- Multiple unused calculations in curve_view_widget.py

## What Remains To Be Fixed

### Immediate Fixes Required (Zoom Bug)
1. **Separate fit_scale from zoom_factor**
   - Store separately in ViewState
   - Apply in correct order in transform pipeline
   - Fix pan adjustment calculations

2. **Fix precision loss**
   - Change ViewState display dimensions to float
   - Remove premature int conversions
   - Maintain sub-pixel precision throughout

3. **Make zoom operations atomic**
   - Capture state before changes
   - Calculate all adjustments with consistent state
   - Apply all changes together

4. **Fix cache invalidation timing**
   - Ensure transforms use consistent geometry
   - Remove processEvents() call causing races
   - Validate transform consistency

### Architectural Simplification Required
1. **Merge ViewState and Transform**
   - Single ViewTransform class
   - Direct state + transformation methods
   - Eliminate intermediate creation steps

2. **Remove unnecessary abstractions**
   - Delete CacheConfig entirely
   - Simplify ValidationConfig to boolean
   - Remove 10 _get_* methods with hasattr

3. **Flatten transform pipeline**
   - Reduce from 10 to 3 layers
   - Remove pre-calculations (nanosecond "optimization")
   - Calculate on-demand

4. **Fix type safety**
   - Replace union dict with typed dataclass
   - Remove all cast() usage
   - Fix ViewState.with_updates() type bypass

### Performance Optimizations Needed
1. **Vectorization opportunities**
   - Batch coordinate transformations
   - Use NumPy for multi-point operations
   - Integer math for screen-space calculations

2. **Cache simplification**
   - Remove quantization complexity
   - Simple direct caching or none
   - Fix claimed 99.9% hit rate (misleading)

## Risk Assessment

### High Risk Issues
- Scale compounding mismatch (causes visible bug)
- Integer precision loss (cumulative drift)
- Division by zero protection mismatch (crash potential)

### Medium Risk Issues
- Cache invalidation timing (incorrect transforms)
- Type safety collapse (silent failures)
- Pre-calculated stale values (state sync)

### Low Risk Issues
- Overcomplicated architecture (maintenance burden)
- Dead code (confusion)
- Performance micro-optimizations (negligible impact)

## Recommended Fix Priority

### Phase 1: Fix Zoom Bug (Critical)
1. Separate fit_scale and zoom_factor
2. Fix ViewState float precision
3. Make zoom operations atomic
4. Fix pan adjustment calculations

### Phase 2: Type Safety (Important)
1. Replace _parameters dict with dataclass
2. Fix ViewState.with_updates()
3. Remove hasattr() usage
4. Add proper type annotations

### Phase 3: Simplification (Valuable)
1. Merge ViewState and Transform
2. Remove unused code
3. Flatten abstraction layers
4. Simplify caching

### Phase 4: Performance (Nice-to-have)
1. Implement vectorization
2. Optimize hot paths
3. Add performance benchmarks

## Success Metrics

- **Bug Fixed**: No curve floating during zoom
- **Code Reduced**: Transform system <500 lines (from 2000+)
- **Type Safety**: 0 type errors, <10 warnings
- **Performance**: Maintain 60fps during zoom
- **Cache**: Real hit rate >95% (not claimed)

## Conclusion

The zoom-float bug stems from a fundamental scale calculation mismatch compounded by precision loss and timing issues. The overcomplicated architecture (10 layers for a simple transformation) makes debugging extremely difficult. A focused fix of the scale handling followed by aggressive simplification will resolve both the immediate bug and long-term maintainability issues.

**Bottom Line**: The system needs surgical fixes for the zoom bug, then major architectural simplification to prevent future issues.
