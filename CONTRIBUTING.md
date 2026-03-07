# Contributing to PyQuota

## Development setup

1. Clone the repository and enter the project directory.
2. Use either a **conda** environment or a **venv**:

   **Conda (recommended for this project):**
   ```bash
   conda env create -f environment.yml   # or: conda env update -f environment.yml
   conda activate pyquota
   pip install -e ".[dev]"
   ```

   **venv:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows (note: extension builds on Linux only)
   pip install -e ".[dev]"
   ```
3. Build requirements: Python development headers (e.g. `python3-dev`) and a C compiler (e.g. `build-essential` on Debian/Ubuntu).

## Running tests

With conda: `conda run -n pyquota pytest`, or after `conda activate pyquota` just:

```bash
pytest
```

Unit tests do not require root or a real block device. Integration tests (if enabled) require a loop device or test partition with quota and may need `sudo`; see [Integration tests](#integration-tests) below.

## Linting and type checking

```bash
ruff check pyquota tests
mypy pyquota
```

Configuration is in `pyproject.toml` where applicable.

## Building the documentation

Optional (requires `pip install -e ".[docs]"`):

```bash
cd docs && make html
```

Output is in `docs/_build/html`. The CI workflow builds docs on push to `main`/`master` and deploys to [GitHub Pages](https://tjumyk.github.io/pyquota/) when Pages is enabled in the repository settings (Settings → Pages → Source: GitHub Actions).

## Submitting changes

1. Open an issue or comment on an existing one to discuss larger changes.
2. Fork the repo, create a branch, and make your changes.
3. Add or update tests as needed; keep the test suite passing.
4. Run ruff and mypy (see above).
5. Open a pull request with a clear description and reference any related issues.

## Integration tests

Integration tests (if present) are skipped by default. They require:

- Linux with quota support and a block device or loop device with quotas enabled
- Root or appropriate capability to run quotactl

To run them (at your own risk, only in a safe test environment):

```bash
PYQUOTA_INTEGRATION=1 sudo -E pytest tests/ -k integration
```

Do not enable integration tests in CI unless using an isolated environment with a dedicated test device.

## Code style

- Python: follow PEP 8; use ruff for formatting/lint.
- C: keep the existing style in `pyquota.c`; no functional change to the low-level API without discussion.
