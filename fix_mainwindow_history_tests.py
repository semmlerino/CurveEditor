#!/usr/bin/env python3
"""Fix TestHistoryWithMainWindow tests by reordering setup."""

filepath = "/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_interaction_service.py"

with open(filepath, 'r') as f:
    content = f.read()

# Fix test_add_to_history_with_main_window_history - move setup before first add_to_history call
content = content.replace(
    '''    def test_add_to_history_with_main_window_history(self) -> None:
        """Test add_to_history using main_window's history."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        main_window.history_index = -1
        main_window.max_history_size = 50
        main_window.curve_widget = view
        main_window.curve_view = view

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Should have added to main_window's history
        assert len(main_window.history) == 1  # pyright: ignore[reportArgumentType]
        assert main_window.history_index == 0''',
    '''    def test_add_to_history_with_main_window_history(self) -> None:
        """Test add_to_history using main_window's history."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        # Set up main_window BEFORE calling add_to_history
        main_window.history_index = -1
        main_window.max_history_size = 50
        main_window.curve_widget = view
        main_window.curve_view = view

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Should have added to main_window's history
        assert len(main_window.history) == 1  # pyright: ignore[reportArgumentType]
        assert main_window.history_index == 0'''
)

# Fix test_undo_with_main_window_history - move setup before first add_to_history call
content = content.replace(
    '''    def test_undo_with_main_window_history(self) -> None:
        """Test undo using main_window's history system."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        main_window.history_index = -1
        main_window.curve_widget = view
        main_window.curve_view = view

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify and add new state
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo
        assert main_window.history_index == 1
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]

        # Should have decremented index
        assert main_window.history_index == 0''',
    '''    def test_undo_with_main_window_history(self) -> None:
        """Test undo using main_window's history system."""
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(cast(CurveDataList, test_data))
        main_window = MockMainWindow()
        # Set up main_window BEFORE calling add_to_history
        main_window.history_index = -1
        main_window.curve_widget = view
        main_window.curve_view = view

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify and add new state
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo
        assert main_window.history_index == 1
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]

        # Should have decremented index
        assert main_window.history_index == 0'''
)

with open(filepath, 'w') as f:
    f.write(content)

print("Fixed TestHistoryWithMainWindow tests")
