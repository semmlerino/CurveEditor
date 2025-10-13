# Repository Guidelines

## Project Structure & Module Organization
Core app code lives in `core/` (models and utilities). `services/` contains the four service singletons (Transform, Data, Interaction, UI). `controllers/` and `ui/` host PySide6 controllers and widgets, while `rendering/` holds drawing pipelines. Data import/export helpers sit in `data/` and `io_utils/`. Tests reside in `tests/` with fixtures under `tests/fixtures/`. Tooling scripts live in `scripts/` and `commands/`. `main.py` is the entrypoint; supporting docs are under `docs/`.

## Build, Test, and Development Commands
```
pip install -r requirements.txt           # install dependencies inside a venv
python main.py                            # launch the editor
pytest tests/                             # run unit and integration suite
pytest --cov=. --cov-report=term-missing  # check coverage before PRs
ruff check .                              # lint; add --fix to auto-correct
./bpr                                     # basedpyright type checking shim
```
Run these locally before pushing; CI mirrors the sequence.

## Coding Style & Naming Conventions
Use PEP 8 with four-space indentation and descriptive snake_case for modules, functions, and variables. Qt widget subclasses stay in CamelCase (`CurveViewWidget`). Place UI components in `ui/components` and controller glue in `controllers/`. Prefer dataclasses in `core` when modeling state. Run `ruff` prior to committing and respect ignore rules in `basedpyrightconfig.json`. Provide type hints and concise docstrings when behavior is non-obvious.

## Testing Guidelines
Use `pytest` with descriptive `test_*.py` files under `tests/`. Share fixtures from `tests/fixtures` and keep sample assets small. Cover regression paths for zoom/pan, selection, and service handoffs. Maintain Codecov status—add integration checks when UI service interactions change. Only skip tests with documented rationale.

## Commit & Pull Request Guidelines
Follow Conventional Commits (`fix:`, `feat:`, `docs:`, `refactor:`). Messages describe scope and outcome, e.g., `fix: repair interaction service undo stack`. Branch names should match intent (`feature/velocity-vectors`). PRs must summarize behavior changes, link issues, and note migrations. Attach UI screenshots or clips when visuals shift, and include evidence of `pytest`, `ruff`, and `./bpr` runs.

## Environment & Configuration Tips
Develop against Python 3.12+. User preferences persist at `~/.curveEditor/settings.json`; do not commit personal configs. Large footage lives in `archive_obsolete/` or off-repo storage to keep history lean.
