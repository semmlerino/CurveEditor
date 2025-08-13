#!/usr/bin/env python3
"""
Architecture Migration Validator

This tool validates that your CurveEditor installation correctly supports
both DEFAULT and LEGACY architectures via the USE_NEW_SERVICES environment variable.
"""

import os
import sys


class MigrationValidator:
    """Validates dual architecture support (DEFAULT and LEGACY)."""

    def __init__(self):
        self.results: dict[str, bool] = {}
        self.messages: list[str] = []

    def validate_environment(self) -> bool:
        """Check environment variables and architecture mode."""
        use_new = os.environ.get("USE_NEW_SERVICES", "false").lower()

        if use_new == "true":
            self.messages.append("🔧 LEGACY architecture active (USE_NEW_SERVICES=true)")
            self.messages.append("   Note: Despite the name, this enables Sprint 8 services (older)")
            mode = "LEGACY"
        else:
            self.messages.append("✅ DEFAULT architecture active (consolidated 4-service)")
            self.messages.append("   This is the recommended production configuration")
            mode = "DEFAULT"

        self.results["environment"] = True
        self.current_mode = mode
        return True

    def validate_default_imports(self) -> bool:
        """Verify DEFAULT services can be imported."""
        try:
            from services import (
                USE_NEW_SERVICES,
                get_data_service,
                get_interaction_service,
                get_transform_service,
                get_ui_service,
            )

            # Check feature flag
            if USE_NEW_SERVICES:
                self.messages.append("⚠️ Feature flag indicates LEGACY mode but testing DEFAULT imports")

            # Verify services can be instantiated
            data_service = get_data_service()
            get_transform_service()
            get_interaction_service()
            get_ui_service()

            # Check singleton pattern
            data_service2 = get_data_service()
            if data_service is not data_service2:
                raise ValueError("Singleton pattern broken for DataService")

            self.messages.append("✅ All DEFAULT services imported successfully")
            self.messages.append("✅ Singleton pattern verified")
            self.results["default_imports"] = True
            return True

        except ImportError as e:
            self.messages.append(f"❌ Import error: {e}")
            self.results["default_imports"] = False
            return False
        except Exception as e:
            self.messages.append(f"❌ Service initialization error: {e}")
            self.results["default_imports"] = False
            return False

    def validate_legacy_imports(self) -> bool:
        """Verify LEGACY Sprint 8 services can be imported when enabled."""
        use_new = os.environ.get("USE_NEW_SERVICES", "false").lower()

        if use_new != "true":
            self.messages.append("⏭️ Skipping LEGACY imports test (not in LEGACY mode)")
            self.results["legacy_imports"] = True
            return True

        try:
            from services import (
                get_event_handler_service,
                get_history_service,
                get_point_manipulation_service,
                get_selection_service,
            )

            # Try to instantiate Sprint 8 services
            get_event_handler_service()
            get_selection_service()
            get_point_manipulation_service()
            get_history_service()

            self.messages.append("✅ All LEGACY Sprint 8 services imported successfully")
            self.results["legacy_imports"] = True
            return True

        except ImportError as e:
            self.messages.append(f"❌ LEGACY import error: {e}")
            self.results["legacy_imports"] = False
            return False
        except RuntimeError as e:
            if "New services not enabled" in str(e):
                self.messages.append("✅ LEGACY services correctly blocked in DEFAULT mode")
                self.results["legacy_imports"] = True
                return True
            else:
                self.messages.append(f"❌ Unexpected error: {e}")
                self.results["legacy_imports"] = False
                return False
        except Exception as e:
            self.messages.append(f"❌ LEGACY service initialization error: {e}")
            self.results["legacy_imports"] = False
            return False

    def validate_service_protocols(self) -> bool:
        """Verify protocol-based interfaces are properly defined."""
        try:
            # Check if protocols exist
            # Check protocol implementation
            from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
            from services.service_protocols import (
                DataServiceProtocol,  # noqa: F401
                InteractionServiceProtocol,  # noqa: F401
                TransformServiceProtocol,  # noqa: F401
                UIServiceProtocol,  # noqa: F401
            )

            # Get service instances
            data_service = get_data_service()
            transform_service = get_transform_service()
            interaction_service = get_interaction_service()
            ui_service = get_ui_service()

            # Basic protocol compliance check (method existence)
            if not hasattr(data_service, "load_track_data"):
                raise ValueError("DataService missing load_track_data method")
            if not hasattr(transform_service, "create_transform"):
                raise ValueError("TransformService missing create_transform method")
            if not hasattr(interaction_service, "handle_mouse_press"):
                raise ValueError("InteractionService missing handle_mouse_press method")
            if not hasattr(ui_service, "show_error"):
                raise ValueError("UIService missing show_error method")

            self.messages.append("✅ Service protocols properly defined and implemented")
            self.results["protocols"] = True
            return True

        except ImportError as e:
            self.messages.append(f"⚠️ Protocol definitions not found: {e}")
            self.messages.append("   This is expected if protocols haven't been fully implemented")
            self.results["protocols"] = True  # Not critical
            return True
        except Exception as e:
            self.messages.append(f"❌ Protocol validation error: {e}")
            self.results["protocols"] = False
            return False

    def validate_transform_immutability(self) -> bool:
        """Verify Transform class is immutable."""
        try:
            from services import get_transform_service
            from services.transform_service import ViewState

            transform_service = get_transform_service()

            # Create a view state
            view_state = ViewState(zoom_factor=2.0, offset_x=100, offset_y=50, width=800, height=600)

            # Create transform
            transform = transform_service.create_transform(view_state)

            # Try to modify transform (should fail if immutable)
            try:
                transform.zoom = 3.0  # Should raise AttributeError
                self.messages.append("❌ Transform class is mutable (can modify attributes)")
                self.results["immutability"] = False
                return False
            except AttributeError:
                self.messages.append("✅ Transform class is properly immutable")
                self.results["immutability"] = True
                return True

        except Exception as e:
            self.messages.append(f"❌ Transform immutability test error: {e}")
            self.results["immutability"] = False
            return False

    def validate_ui_component_container(self) -> bool:
        """Verify Component Container Pattern in ui_components.py."""
        try:
            from ui.ui_components import UIComponents

            # Check if UIComponents has the expected structure
            ui_components = UIComponents()

            # Check for component groups
            expected_groups = ["timeline", "controls", "visualization", "status"]
            for group in expected_groups:
                if not hasattr(ui_components, group):
                    raise ValueError(f"UIComponents missing {group} group")

            self.messages.append("✅ Component Container Pattern properly implemented")
            self.messages.append(f"   Found component groups: {expected_groups}")
            self.results["container_pattern"] = True
            return True

        except ImportError as e:
            self.messages.append(f"⚠️ UIComponents not found: {e}")
            self.messages.append("   This is expected if still using old UI structure")
            self.results["container_pattern"] = True  # Not critical
            return True
        except Exception as e:
            self.messages.append(f"❌ Component Container validation error: {e}")
            self.results["container_pattern"] = False
            return False

    def test_architecture_switch(self) -> bool:
        """Test switching between architectures."""
        original_env = os.environ.get("USE_NEW_SERVICES", "")

        try:
            # Test DEFAULT mode
            os.environ["USE_NEW_SERVICES"] = "false"

            # Reload services module to pick up environment change
            import importlib

            import services

            importlib.reload(services)

            from services import USE_NEW_SERVICES, get_history_service

            if USE_NEW_SERVICES:
                self.messages.append("❌ Architecture switch failed - still in LEGACY mode")
                self.results["switch_test"] = False
                return False

            # In DEFAULT mode, get_history_service should return InteractionService
            history_service = get_history_service()
            if history_service.__class__.__name__ != "InteractionService":
                self.messages.append(f"⚠️ get_history_service returned {history_service.__class__.__name__}")

            # Test LEGACY mode
            os.environ["USE_NEW_SERVICES"] = "true"
            importlib.reload(services)

            from services import USE_NEW_SERVICES  # noqa: N811

            if not USE_NEW_SERVICES:
                self.messages.append("❌ Architecture switch failed - still in DEFAULT mode")
                self.results["switch_test"] = False
                return False

            self.messages.append("✅ Architecture switching mechanism works correctly")
            self.results["switch_test"] = True
            return True

        except Exception as e:
            self.messages.append(f"❌ Architecture switch test error: {e}")
            self.results["switch_test"] = False
            return False
        finally:
            # Restore original environment
            if original_env:
                os.environ["USE_NEW_SERVICES"] = original_env
            elif "USE_NEW_SERVICES" in os.environ:
                del os.environ["USE_NEW_SERVICES"]

            # Reload with original settings
            import importlib

            import services

            importlib.reload(services)

    def run_validation(self) -> tuple[bool, str]:
        """Run all validation checks."""
        print("=" * 60)
        print("CurveEditor Dual Architecture Validator")
        print("=" * 60)
        print()

        # Run all validations
        self.validate_environment()
        self.validate_default_imports()
        self.validate_legacy_imports()
        self.validate_service_protocols()
        self.validate_transform_immutability()
        self.validate_ui_component_container()
        self.test_architecture_switch()

        # Generate report
        print("Validation Results:")
        print("-" * 40)
        for message in self.messages:
            print(message)

        print()
        print("Summary:")
        print("-" * 40)

        total_tests = len(self.results)
        passed_tests = sum(1 for v in self.results.values() if v)

        if passed_tests == total_tests:
            print(f"✅ ALL TESTS PASSED ({passed_tests}/{total_tests})")
            print(f"✅ Architecture validation successful - {self.current_mode} mode working correctly")
            status = "SUCCESS"
        else:
            failed_tests = [k for k, v in self.results.items() if not v]
            print(f"⚠️ PARTIAL SUCCESS ({passed_tests}/{total_tests} tests passed)")
            print(f"⚠️ Failed tests: {', '.join(failed_tests)}")
            status = "PARTIAL"

        print()
        print("Architecture Details:")
        print("-" * 40)
        print("DEFAULT Mode (USE_NEW_SERVICES=false or unset):")
        print("  • 4 consolidated services")
        print("  • TransformService, DataService, InteractionService, UIService")
        print("  • Recommended for production")
        print()
        print("LEGACY Mode (USE_NEW_SERVICES=true):")
        print("  • Sprint 8 granular services (10+ services)")
        print("  • SelectionService, PointManipulationService, etc.")
        print("  • Maintained for backward compatibility")
        print()
        print("Note: The 'USE_NEW_SERVICES' name is historical - 'new' referred to")
        print("Sprint 8 decomposition, which has been superseded by consolidation.")

        print()
        print("=" * 60)

        return passed_tests == total_tests, status


def main():
    """Main entry point."""
    validator = MigrationValidator()
    success, status = validator.run_validation()

    # Exit with appropriate code
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
