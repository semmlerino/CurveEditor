# CurveEditor Development Commands

## Essential Commands (use `uv run` prefix)

### Running the Application
```bash
uv run python main.py
```

### Testing
```bash
# Run all tests (1945+ test cases)
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_curve_view.py

# Run with verbose output and stop on first failure
uv run pytest tests/ -v -x

# Run with short traceback
uv run pytest tests/ --tb=short

# Quick test run (quiet mode)
uv run pytest tests/ -q
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

## Git Commands
```bash
git status
git add .
git commit -m "message"
git log --oneline -n 10
```

## System Commands (Linux/WSL2)
```bash
ls          # List files
cd          # Change directory
grep        # Search in files
find        # Find files
cat         # Display file contents
head/tail   # Show file start/end
```

## Virtual Environment
```bash
# Already managed by uv - no need to activate manually
# uv handles venv automatically when using `uv run`
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
