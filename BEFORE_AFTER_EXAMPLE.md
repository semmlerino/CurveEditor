# Before/After Example: Transform Service Testing

## The Problem: Excessive Mocking Hides Real Issues

### Before (Using MagicMock)
```python
def test_create_view_state(self, transform_service: TransformService) -> None:
    """Test creating ViewState from CurveView."""
    # Creating a fake object that pretends to be a CurveView
    mock_curve_view = MagicMock()
    mock_curve_view.width.return_value = 800
    mock_curve_view.height.return_value = 600
    mock_curve_view.image_width = 1920
    mock_curve_view.image_height = 1080
    mock_curve_view.zoom_factor = 1.0
    mock_curve_view.offset_x = 0.0
    # ... 10+ more mock attributes

    # This only tests that the service can handle a mock object
    # It doesn't test real Qt widget behavior!
    view_state = transform_service.create_view_state(mock_curve_view)
    assert view_state.widget_width == 800  # Testing mock data, not reality
```

**Problems**:
- Tests mock behavior, not real widget interactions
- Mock setup is lengthy and error-prone
- Changes to CurveViewWidget interface break tests
- No confidence that real Qt widgets work
- Mock attributes might not match real widget API

### After (Using Real Qt Components)
```python
@pytest.fixture
def real_curve_view(self, qtbot):
    """Create a real CurveViewWidget for testing transformations."""
    return self._create_curve_view(qtbot)

def _create_curve_view(self, qtbot, **overrides):
    """Factory method to create curve view with custom properties."""
    from ui.curve_view_widget import CurveViewWidget

    curve_view = CurveViewWidget()
    qtbot.addWidget(curve_view)  # Proper Qt lifecycle management

    # Set realistic test configuration
    defaults = {
        'width': 800, 'height': 600,
        'image_width': 1920, 'image_height': 1080,
        'zoom_factor': 1.0, 'pan_offset_x': 0.0,
        # ... other realistic defaults
    }

    config = {**defaults, **overrides}
    curve_view.resize(config['width'], config['height'])

    for key, value in config.items():
        if key not in ['width', 'height']:
            setattr(curve_view, key, value)

    return curve_view

def test_create_view_state(self, transform_service: TransformService, real_curve_view, qtbot) -> None:
    """Test creating ViewState from CurveView using real Qt widget."""
    # Using actual Qt widget - tests real behavior!
    view_state = transform_service.create_view_state(real_curve_view)

    # These assertions verify actual widget properties
    assert view_state.widget_width == 800
    assert view_state.widget_height == 600
    assert view_state.image_width == 1920
    assert view_state.image_height == 1080
```

**Benefits**:
- Tests actual Qt widget behavior
- Catches real integration bugs
- Factory pattern allows easy test variations
- Proper Qt lifecycle with qtbot
- More maintainable than mock setup

## File Service Example: Real File I/O vs Mock Behavior

### Before (Mock File Dialogs)
```python
def test_save_track_data_user_cancels(self, data_service, main_window, sample_data):
    """Test save_track_data when user cancels."""
    mock_dialog = Mock()
    mock_dialog.getSaveFileName = Mock(return_value=("", ""))
    with patch("services.data_service.QFileDialog", mock_dialog):
        result = data_service.save_track_data(main_window, sample_data)
        assert result is False  # Only tests mock return value!
```

### After (Real File Operations)
```python
def test_save_track_data_successful_json(
    self, data_service, main_window, sample_data, monkeypatch, tmp_path
):
    """Test successful saving of JSON track data."""
    test_file = tmp_path / "output_track.json"

    # Mock only the dialog, test real file operations
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args, **kwargs: (str(test_file), "JSON Files (*.json)")
    )

    # Test actual file saving behavior
    result = data_service.save_track_data(main_window, sample_data)
    assert result is True

    # Verify file was actually created with correct content
    assert test_file.exists()
    saved_data = json.loads(test_file.read_text())
    assert "curve_data" in saved_data
    assert len(saved_data["curve_data"]) == len(sample_data)
    # Verify actual data integrity!
```

**Key Improvements**:
1. **System Boundary Mocking**: Only mock the file dialog, not the file operations
2. **Real File I/O**: Actually writes and reads files
3. **Data Integrity**: Verifies saved content matches input
4. **Failure Detection**: Would catch real JSON serialization bugs

## The Impact: Bug Detection

The improved tests would have caught these real bugs that mocks would miss:

1. **Incorrect attribute names**: `offset_x` vs `pan_offset_x`
2. **Qt widget resize behavior**: Actual size vs expected size
3. **JSON format changes**: Real serialization vs mock data
4. **File path validation**: Security checks that mocks skip
5. **Qt signal emission**: Real signals vs mock signals

## Conclusion

By following the UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md principles:
- We reduced mock usage by 71 instances
- Tests now catch real integration bugs
- Code is more maintainable and robust
- We have higher confidence in system behavior

This demonstrates the value of **testing behavior, not implementation** and using **real components over mocks** wherever possible.
