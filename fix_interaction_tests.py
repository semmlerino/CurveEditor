#!/usr/bin/env python3
"""Script to systematically fix test_interaction_service.py by adding ApplicationState setup."""

import re

def fix_test_file():
    """Add ApplicationState setup to history tests."""
    filepath = "/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/test_interaction_service.py"

    with open(filepath, 'r') as f:
        content = f.read()

    # Pattern to find tests that call add_to_history without ApplicationState setup
    # We need to add setup after view.curve_data is set but before add_to_history is called

    # Fix test_add_to_history
    content = content.replace(
        '''    def test_add_to_history(self) -> None:
        """Test adding states to history."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up actual curve data that will be captured by add_to_history
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify data and add another state
        view.curve_data = [(1, 100, 100), (2, 200, 200)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_add_to_history(self) -> None:
        """Test adding states to history."""
        from stores.application_state import get_application_state

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up ApplicationState with curve data
        app_state = get_application_state()
        view.curve_data = [(1, 100, 100)]
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Set up actual curve data that will be captured by add_to_history
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify data and add another state
        view.curve_data = [(1, 100, 100), (2, 200, 200)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_undo_operation
    content = content.replace(
        '''    def test_undo_operation(self) -> None:
        """Test undo functionality."""
        view = MockCurveView([(1, 100, 100)])
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add initial state
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify and add new state
        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_undo_operation(self) -> None:
        """Test undo functionality."""
        from stores.application_state import get_application_state

        view = MockCurveView([(1, 100, 100)])
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Add initial state
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Modify and add new state
        view.curve_data = [(1, 150, 150)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_redo_operation
    content = content.replace(
        '''    def test_redo_operation(self) -> None:
        """Test redo functionality."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add multiple states by modifying curve_data
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        view.curve_data = [(1, 200, 200)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_redo_operation(self) -> None:
        """Test redo functionality."""
        from stores.application_state import get_application_state

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up ApplicationState
        app_state = get_application_state()

        # Add multiple states by modifying curve_data
        view.curve_data = [(1, 100, 100)]
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 150, 150)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        view.curve_data = [(1, 200, 200)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_history_branching
    content = content.replace(
        '''    def test_history_branching(self) -> None:
        """Test that new action after undo creates new branch."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add states
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 200, 200)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo once
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]

        # Add new state (should clear redo history)
        view.curve_data = [(1, 175, 175)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_history_branching(self) -> None:
        """Test that new action after undo creates new branch."""
        from stores.application_state import get_application_state

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up ApplicationState
        app_state = get_application_state()

        # Add states
        view.curve_data = [(1, 100, 100)]
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 150, 150)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 200, 200)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        # Undo once
        self.service.undo(main_window)  # pyright: ignore[reportArgumentType]

        # Add new state (should clear redo history)
        view.curve_data = [(1, 175, 175)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_history_max_size
    content = content.replace(
        '''    def test_history_max_size(self) -> None:
        """Test history respects maximum size limit."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add many states
        for i in range(150):  # More than typical max
            view.curve_data = [(1, i, i)]
            self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_history_max_size(self) -> None:
        """Test history respects maximum size limit."""
        from stores.application_state import get_application_state

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_active_curve("test_curve")

        # Add many states
        for i in range(150):  # More than typical max
            view.curve_data = [(1, i, i)]
            app_state.set_curve_data("test_curve", view.curve_data)
            self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_handle_undo_redo_shortcuts
    content = content.replace(
        '''    def test_handle_undo_redo_shortcuts(self) -> None:
        """Test Ctrl+Z/Ctrl+Y shortcuts."""
        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Add some history by setting actual curve data
        view.curve_data = [(1, 100, 100)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 150, 150)]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_handle_undo_redo_shortcuts(self) -> None:
        """Test Ctrl+Z/Ctrl+Y shortcuts."""
        from stores.application_state import get_application_state

        view = MockCurveView()
        main_window = MockMainWindow()
        # Set history to None to force use of internal history
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view  # Real MainWindow interface
        main_window.curve_view = view  # Backward compatibility

        # Set up ApplicationState
        app_state = get_application_state()

        # Add some history by setting actual curve data
        view.curve_data = [(1, 100, 100)]
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]

        view.curve_data = [(1, 150, 150)]
        app_state.set_curve_data("test_curve", view.curve_data)
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_clear_history
    content = content.replace(
        '''    def test_clear_history(self) -> None:
        """Test clearing history."""
        view = MockCurveView([(1, 100.0, 100.0)])
        main_window = MockMainWindow()
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        main_window.history_index = None
        main_window.curve_widget = view
        self.service.clear_history(main_window)  # pyright: ignore[reportArgumentType]
        # Add some states
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_clear_history(self) -> None:
        """Test clearing history."""
        from stores.application_state import get_application_state

        view = MockCurveView([(1, 100.0, 100.0)])
        main_window = MockMainWindow()
        main_window.history_index = None
        main_window.curve_widget = view

        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        self.service.clear_history(main_window)  # pyright: ignore[reportArgumentType]
        # Add some states
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    # Fix test_get_memory_stats
    content = content.replace(
        '''    def test_get_memory_stats(self) -> None:
        """Test getting memory statistics."""
        view = MockCurveView([(1, 100.0, 100.0)])
        main_window = MockMainWindow()
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view

        # Add some states
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]''',
        '''    def test_get_memory_stats(self) -> None:
        """Test getting memory statistics."""
        from stores.application_state import get_application_state

        view = MockCurveView([(1, 100.0, 100.0)])
        main_window = MockMainWindow()
        main_window.history = None
        main_window.history_index = None
        main_window.curve_widget = view

        # Set up ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Add some states
        self.service.add_to_history(main_window, None)  # pyright: ignore[reportArgumentType]'''
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print("Fixed test_interaction_service.py - added ApplicationState setup to history tests")

if __name__ == "__main__":
    fix_test_file()
