#!/usr/bin/env python3
"""Simple configuration for CurveEditor - single-user desktop application.

Only configures truly optional features. Critical bug fixes are permanent.
"""

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Simple runtime configuration for optional features.

    Bug fixes from PLAN_A are permanent - not configurable:
    - Quantization precision fix (always uses precision/10 for zoom)
    - Progressive error recovery (always enabled for safety)
    - Spatial indexing (always enabled for performance)
    - Optimized rendering (always enabled for performance)

    Only optional features with performance impact are configurable.
    """

    # Debug mode - forces expensive validation in production
    force_debug_validation: bool = False

    # Unified transformation system - new metadata-aware data loading
    # Default to True - system is production-ready per comprehensive review
    use_metadata_aware_data: bool = True

    @classmethod
    def from_environment(cls) -> "AppConfig":
        """Load configuration from environment variables.

        Environment variables:
        - CURVE_EDITOR_DEBUG_VALIDATION: Force debug validation (true/false)
        - USE_METADATA_AWARE_DATA: Use new coordinate metadata system (true/false)
        """

        def parse_bool(value: str) -> bool:
            return value.lower() in ("true", "1", "yes", "on")

        return cls(
            force_debug_validation=parse_bool(os.getenv("CURVE_EDITOR_DEBUG_VALIDATION", "")),
            use_metadata_aware_data=parse_bool(
                os.getenv("USE_METADATA_AWARE_DATA", "true")
            ),  # Default to true per class definition
        )

    def summary(self) -> str:
        """Get human-readable summary of configuration."""
        lines = [
            "CurveEditor Configuration:",
            f"  Debug Validation: {'ON' if self.force_debug_validation else 'OFF'}",
            f"  Metadata-Aware Data: {'ON' if self.use_metadata_aware_data else 'OFF'}",
        ]
        return "\n".join(lines)


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance.

    Returns:
        AppConfig singleton instance
    """
    global _config
    if _config is None:
        _config = AppConfig.from_environment()
    return _config


def reset_config() -> None:
    """Reset configuration (mainly for testing)."""
    global _config
    _config = None


if __name__ == "__main__":
    # Demo/testing
    print("Testing configuration...")
    config = get_config()
    print(config.summary())

    print("\nWith monitoring enabled:")
    os.environ["CURVE_EDITOR_MONITORING"] = "true"
    reset_config()
    config = get_config()
    print(config.summary())
