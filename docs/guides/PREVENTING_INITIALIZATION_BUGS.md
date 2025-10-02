# Preventing Initialization Order Bugs

## The Problem

**AttributeError**: Calling methods that access attributes before those attributes are initialized.

**Example**: `_populate_drives()` accessed `self.tree_view` before it was created in `_setup_ui()`.

---

## 4-Layer Defense Strategy

### ✅ Layer 1: Static Type Checking (Basedpyright)

**File**: `basedpyrightconfig.json`

```json
{
  "reportUninitializedInstanceVariable": "warning"  // Changed from "none"
}
```

**Benefits**:
- Catches issues at development time
- No runtime overhead
- IDE integration (red squiggles)

**Limitations**:
- May not track initialization order in helper methods like `_setup_ui()`
- Can produce false positives

---

### ✅ Layer 2: Type Annotations on Class Attributes

**Before**:
```python
class MyDialog(QDialog):
    def __init__(self):
        self._setup_ui()

    def _setup_ui(self):
        self.tree_view = QTreeView()  # No type hint
```

**After**:
```python
class MyDialog(QDialog):
    # Explicit type annotations help type checker
    tree_view: QTreeView
    file_model: QFileSystemModel
    drive_selector: QComboBox | None

    def __init__(self):
        self._setup_ui()
```

**Benefits**:
- Type checker knows these attributes *should* exist
- Better IDE autocomplete
- Documents expected attributes

**When to Use**:
- For all UI widgets created in `_setup_ui()` or similar methods
- For any attribute accessed by multiple methods

---

### ✅ Layer 3: Defensive Guards in Methods

**Before**:
```python
def _populate_drives(self) -> None:
    # CRASHES if tree_view doesn't exist yet
    current_index = self.tree_view.currentIndex()
```

**After**:
```python
def _populate_drives(self) -> None:
    # Defensive guard prevents AttributeError
    if not hasattr(self, "tree_view"):
        return

    current_index = self.tree_view.currentIndex()
```

**Benefits**:
- Prevents runtime crashes
- Makes dependencies explicit
- Safe to call at any time

**When to Use**:
- Methods called from `__init__` that depend on other attributes
- Methods that might be called in different initialization orders
- Helper methods used in complex UI setup

**Trade-off**: Uses `hasattr()` which type checkers may not like, but it's acceptable for runtime safety in initialization code.

---

### ✅ Layer 4: Integration Tests

**File**: `tests/test_image_sequence_browser_init.py`

```python
def test_dialog_initializes_without_errors(self, qapp: QApplication):
    """Test that dialog can be created without AttributeError."""
    # This would have caught the bug!
    dialog = ImageSequenceBrowserDialog()

    assert hasattr(dialog, "tree_view")
    assert hasattr(dialog, "file_model")

    dialog.close()
```

**Benefits**:
- Catches issues that static analysis misses
- Tests real runtime behavior
- Quick to write for dialogs and widgets

**When to Use**:
- For all complex dialogs with multi-step initialization
- After fixing initialization bugs (regression test)
- For widgets that use `_setup_ui()` patterns

---

## Best Practices for Complex UI Initialization

### Pattern 1: Separate Creation from Population

```python
def _setup_ui(self) -> None:
    # Phase 1: Create all widgets
    self.tree_view = QTreeView()
    self.file_model = QFileSystemModel()
    self.drive_selector = QComboBox()

    # Phase 2: Configure widgets (safe now)
    self._configure_tree_view()
    self._populate_drives()
```

### Pattern 2: Use Lazy Initialization

```python
@property
def tree_view(self) -> QTreeView:
    if not hasattr(self, "_tree_view"):
        self._tree_view = QTreeView()
    return self._tree_view
```

### Pattern 3: Document Dependencies

```python
def _populate_drives(self) -> None:
    """Populate drive selector.

    REQUIRES:
        - self.tree_view must be initialized
        - self.file_model must be initialized
    """
```

---

## Checklist for New Dialogs/Widgets

- [ ] Add type annotations for all instance attributes
- [ ] Create all widgets before configuring them
- [ ] Add defensive guards to helper methods
- [ ] Write integration test that constructs the widget
- [ ] Run `./bpr` to check for uninitialized warnings
- [ ] Test on all platforms (Windows, Linux, macOS)

---

## Real-World Example: The Fix

**Bug Location**: `ui/image_sequence_browser.py:239`

**Before**:
```python
def _setup_ui(self) -> None:
    # Line 239 - CRASHES on Windows
    if sys.platform == "win32":
        self.drive_selector = QComboBox()
        self._populate_drives()  # ❌ tree_view doesn't exist yet!

    # Line 309 - tree_view created here
    self.tree_view = QTreeView()
```

**After**:
```python
def _setup_ui(self) -> None:
    if sys.platform == "win32":
        self.drive_selector = QComboBox()
        # Removed _populate_drives() call

    # Line 309 - Create tree_view
    self.tree_view = QTreeView()

    # Line 323 - NOW safe to call ✅
    self._populate_drives()
```

**Plus defensive guard**:
```python
def _populate_drives(self) -> None:
    if not hasattr(self, "tree_view"):  # ✅ Extra safety
        return
```

---

## Summary

Use **all 4 layers** for maximum protection:

1. **Basedpyright**: Catch issues during development
2. **Type Annotations**: Document expected attributes
3. **Defensive Guards**: Prevent runtime crashes
4. **Integration Tests**: Verify real behavior

**Cost**: ~5 minutes per dialog
**Benefit**: Zero production AttributeErrors
