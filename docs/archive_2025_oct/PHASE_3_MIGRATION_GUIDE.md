# Phase 3 Migration Guide: Validation & Error Handling

This guide helps you migrate code to use the new validation and error handling architecture introduced in Phase 3.

## Table of Contents
1. [Validation Migration](#validation-migration)
2. [Error Handling Migration](#error-handling-migration)
3. [Service Configuration](#service-configuration)
4. [Testing Updates](#testing-updates)

## Validation Migration

### Old Pattern (Global Flag)
```python
# Old: Global validation flag
_ENABLE_FULL_VALIDATION = __debug__ or os.getenv("CURVE_EDITOR_FULL_VALIDATION", "").lower() in ("1", "true", "yes")

if _ENABLE_FULL_VALIDATION:
    if abs(x) > 1e12:
        raise ValueError(f"Coordinate too large: {x}")
```

### New Pattern (Instance Configuration)
```python
# New: Instance-based configuration
from services.transform_service import ValidationConfig

# Option 1: Create from environment
config = ValidationConfig.from_environment()

# Option 2: Use presets
config = ValidationConfig.for_production()  # Minimal validation
config = ValidationConfig.for_debug()       # Comprehensive validation

# Option 3: Custom configuration
config = ValidationConfig(
    enable_full_validation=True,
    max_coordinate=1e15,
    min_scale=1e-10,
    max_scale=1e12
)

# Use with services
service = TransformService(validation_config=config)
```

## Error Handling Migration

### Old Pattern (Inline Error Handling)
```python
# Old: Inline try/except blocks
class MyWidget(QWidget):
    def process_data(self):
        try:
            result = transform.data_to_screen(x, y)
        except ValueError as e:
            logger.error(f"Transform failed: {e}")
            # Use default values
            result = (0, 0)
```

### New Pattern (Error Handler Protocol)
```python
# New: Decoupled error handling
from ui.error_handlers import ErrorHandlerMixin, RecoveryStrategy

class MyWidget(QWidget, ErrorHandlerMixin):
    def process_data(self):
        try:
            result = transform.data_to_screen(x, y)
        except Exception as e:
            strategy = self.handle_error(e, "transform_data", fallback=(0, 0))

            if strategy == RecoveryStrategy.FALLBACK:
                result = (0, 0)
            elif strategy == RecoveryStrategy.RETRY:
                # Retry with safer values
                result = transform.data_to_screen(0, 0)
            elif strategy == RecoveryStrategy.ABORT:
                raise
```

## Service Configuration

### TransformService with Validation

#### Old Usage
```python
# Old: No configuration options
from services import get_transform_service

service = get_transform_service()
# Validation behavior determined by global flag
```

#### New Usage
```python
# New: Configurable validation
from services.transform_service import TransformService, ValidationConfig

# Production deployment
service = TransformService(
    validation_config=ValidationConfig.for_production()
)

# Development/testing
service = TransformService(
    validation_config=ValidationConfig.for_debug()
)

# Custom configuration
service = TransformService(
    validation_config=ValidationConfig(
        enable_full_validation=True,
        max_coordinate=1e20  # Custom limit
    )
)
```

### Coordinate System Support (Merged from UnifiedTransformService)

```python
# New: Coordinate system methods now in TransformService
service = get_transform_service()

# Set source coordinate system
service.set_source_coordinate_system("3de_720p")

# Normalize curve data
normalized = service.normalize_curve_data(raw_data)

# Denormalize for target system
output = service.denormalize_curve_data(normalized, "maya_1080p")
```

## Testing Updates

### Testing with Different Validation Modes

```python
import pytest
from services.transform_service import TransformService, ValidationConfig

class TestMyFeature:
    def test_production_behavior(self):
        """Test with production validation settings."""
        service = TransformService(
            validation_config=ValidationConfig.for_production()
        )
        # Should handle extreme values gracefully
        result = service.create_transform(...)
        assert result is not None

    def test_debug_validation(self):
        """Test with comprehensive validation."""
        service = TransformService(
            validation_config=ValidationConfig.for_debug()
        )
        # Should catch invalid values
        with pytest.raises(ValueError):
            service.create_transform(scale=0.0)
```

### Testing Error Recovery

```python
from ui.error_handlers import SilentTransformErrorHandler, StrictTransformErrorHandler

class TestErrorHandling:
    def test_silent_recovery(self):
        """Test silent error recovery for batch operations."""
        handler = SilentTransformErrorHandler()

        # Process batch without stopping on errors
        for item in batch:
            try:
                process(item)
            except Exception as e:
                context = ErrorContext(...)
                strategy = handler.handle_transform_error(e, context)
                # Continue processing

        # Check captured errors
        errors = handler.get_captured_errors()
        assert len(errors) > 0

    def test_strict_validation(self):
        """Test fail-fast behavior for development."""
        handler = StrictTransformErrorHandler()

        with pytest.raises(ValueError):
            # Should raise immediately
            handler.handle_validation_error(error, context)
```

## Common Migration Scenarios

### Scenario 1: Migrating a UI Component

```python
# Before
class CurveEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.transform_service = get_transform_service()

    def validate_input(self, x, y):
        if not math.isfinite(x) or not math.isfinite(y):
            QMessageBox.warning(self, "Invalid Input", "Coordinates must be finite")
            return False
        return True

# After
from ui.error_handlers import ErrorHandlerMixin, create_error_handler
from core.validation_strategy import get_validation_strategy

class CurveEditor(QWidget, ErrorHandlerMixin):
    def __init__(self):
        super().__init__()
        self.transform_service = get_transform_service()
        self.error_handler = create_error_handler("default", self)
        self.validation_strategy = get_validation_strategy("adaptive")

    def validate_input(self, x, y):
        # Set context for user input
        self.validation_strategy.set_context(is_user_input=True)

        # Validate coordinates
        result = self.validation_strategy.validate_coordinate(x, y, "user_input")

        if not result.is_valid:
            # Report issues through error handler
            self.error_handler.report_issues(result.issues)
            return False

        # Use validated values if they were corrected
        if result.validated_value:
            x, y = result.validated_value

        return True
```

### Scenario 2: Migrating a Service Method

```python
# Before
def process_transform(self, data):
    if _ENABLE_FULL_VALIDATION:
        # Expensive validation
        for point in data:
            if abs(point.x) > 1e12:
                raise ValueError(f"Point {point} out of range")

    # Process data
    return transformed_data

# After
def process_transform(self, data):
    # Use validation strategy
    strategy = self.validation_strategy  # Injected or from config

    # Validate data
    for point in data:
        result = strategy.validate_coordinate(point.x, point.y, "transform_input")
        if not result.is_valid and result.has_critical_issues():
            raise ValueError(f"Invalid point: {result.issues[0].format()}")

        # Use corrected values if available
        if result.validated_value:
            point = point.with_coordinates(*result.validated_value)

    # Process data
    return transformed_data
```

### Scenario 3: Environment-Based Configuration

```python
# Development environment
export CURVE_EDITOR_FULL_VALIDATION=1

# Production environment
export CURVE_EDITOR_FULL_VALIDATION=0

# In code
from services.transform_service import ValidationConfig

# Automatically uses environment setting
config = ValidationConfig.from_environment()
service = TransformService(validation_config=config)
```

## Best Practices

1. **Use Appropriate Error Handlers**
   - `DefaultTransformErrorHandler` for production UI
   - `SilentTransformErrorHandler` for batch operations and testing
   - `StrictTransformErrorHandler` for development and debugging

2. **Choose Validation Strategies Wisely**
   - `MinimalValidationStrategy` for performance-critical paths
   - `ComprehensiveValidationStrategy` for user input and data import
   - `AdaptiveValidationStrategy` for mixed scenarios

3. **Configure Services Explicitly**
   - Always pass `ValidationConfig` to services
   - Use environment-based config for deployment flexibility
   - Document expected validation levels in code

4. **Test Multiple Configurations**
   - Test with both production and debug configurations
   - Verify error recovery strategies work correctly
   - Use silent handlers in test suites to capture errors

## Rollback Instructions

If you need to temporarily rollback to the old behavior:

1. Set environment variable: `export CURVE_EDITOR_FULL_VALIDATION=0`
2. Use `ValidationConfig.for_production()` everywhere
3. Use `SilentTransformErrorHandler` to suppress error reporting

Note: The old `unified_transform_service.py` has been removed. All functionality is now in `transform_service.py`.

## Support

For questions or issues with the migration:
1. Check test files for examples: `tests/test_validation_strategy.py`, `tests/test_error_handlers.py`
2. Review the Phase 3 progress report: `PHASE_3_PROGRESS_REPORT.md`
3. Consult CLAUDE.md for updated patterns and examples

---
*Migration guide for Phase 3 architectural improvements*
*Last updated: January 2025*
