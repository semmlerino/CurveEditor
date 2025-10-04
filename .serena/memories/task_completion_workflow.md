# Task Completion Workflow

## Before Committing Changes

Always run these checks in order:

### 1. Syntax Check
```bash
python3 -m py_compile <modified_file.py>
```

### 2. Type Checking
```bash
./bpr --errors-only
```
- **Goal**: 0 production errors (test errors acceptable)
- Fix any new type errors introduced
- Use `pyright: ignore[specificRule]` only when necessary

### 3. Linting
```bash
uv run ruff check . --fix
```
- Auto-fixes most issues
- Review and fix any remaining warnings

### 4. Run Tests
```bash
# Quick check
uv run pytest tests/ -x -q

# Full test suite
uv run pytest tests/
```
- **Goal**: All tests passing
- Fix any broken tests before committing

### 5. Verify Changes
```bash
git status
git diff
```
- Review all changes
- Ensure no unintended modifications

## Validation Checklist

Before marking a task complete:

- [ ] Syntax check passes
- [ ] No new type errors (`./bpr --errors-only`)
- [ ] Ruff linting clean (`uv run ruff check .`)
- [ ] All tests passing (`uv run pytest tests/`)
- [ ] Changes reviewed (`git diff`)
- [ ] No silent attribute creation (validation before integration)
- [ ] Protocol interfaces respected (if modifying services/controllers)
- [ ] ApplicationState used (no local data storage)

## Integration Best Practices

1. **Validate structure first** - Check components exist before accessing
2. **Use type-safe access** - Prefer `is not None` over `hasattr()`
3. **Subscribe to signals** - Components auto-update via ApplicationState signals
4. **Batch operations** - Use `begin_batch()`/`end_batch()` for bulk changes

## Performance Considerations

- Rendering should maintain 47x optimization
- Transform cache hit rate should stay ~99.9%
- No memory leaks in ApplicationState
- Thread-safe signal emissions
