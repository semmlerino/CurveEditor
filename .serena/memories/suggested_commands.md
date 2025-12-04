# CurveEditor Development Commands

## Essential Commands (use `uv run` prefix)

### Running the Application
```bash
uv run python main.py
```

### Testing
```bash
# Run all tests (3100+ test cases)
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_curve_view.py

# PREFERRED: Stop at first failure, quiet output
uv run pytest tests/ -xq

# Run with verbose output and stop on first failure
uv run pytest tests/ -v -x

# Run with short traceback
uv run pytest tests/ --tb=short

# Disable parallel (for debugging single test)
uv run pytest tests/test_foo.py -n0
```

### Linting (Ruff)
```bash
# Check all files
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Check specific file
uv run ruff check ui/main_window.py
```

### Type Checking (Basedpyright)
```bash
# Check all files (using wrapper script)
./bpr

# Show only errors
./bpr --errors-only

# Show summary only
./bpr --summary

# Check specific file
./bpr ui/main_window.py

# Verify config excludes irrelevant folders
./bpr --check-config
```

### Syntax Check
```bash
python3 -m py_compile <file.py>
```

## WSL Environment Fallback

If `uv` is unavailable, use `.venv/bin/python3` directly:
```bash
.venv/bin/python3 -m pytest tests/
.venv/bin/python3 -m ruff check .
.venv/bin/python3 ./bpr
```

## Git Commands
```bash
git status
git add .
git commit -m "message"
git log --oneline -n 10
```

## Performance Testing
```bash
# Run benchmark tests
uv run pytest tests/ -m benchmark
```

## Coverage Analysis
```bash
uv run pytest tests/ --cov=. --cov-report=html
```

## Debugging Test Failures

For crashes or hard aborts:
```bash
export PYTHONFAULTHANDLER=1 && uv run pytest tests/ \
  -vv -x --maxfail=1 --tb=short -s \
  --log-cli-level=DEBUG \
  2>&1 | tee /tmp/pytest_diag.log
```
