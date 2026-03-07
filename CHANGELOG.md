# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- **Breaking:** **`QFMT_VFS_OLD`**, **`QFMT_VFS_V0`**, **`QFMT_VFS_V1`** are no longer exported from the package. Use **`QuotaFormat.VFS_OLD`**, **`QuotaFormat.VFS_V0`**, **`QuotaFormat.VFS_V1`** for `quota_on` and for comparing with the int return value of `get_*_quota_format()`.

## [0.1.3] - 2025-03-07

### Added

- **`iter_user_quotas(device, start_uid=0)`**, **`iter_group_quotas(device, start_gid=0)`**, **`iter_project_quotas(device, start_projid=0)`**: iterators yielding `NextQuota` for each ID with quota (use `get_next_*` for a single "next" query).
- **`QuotaFormat`** (IntEnum): `VFS_OLD`, `VFS_V0`, `VFS_V1` for `quota_on` / `get_*_quota_format`.
- **`QuotaInfo`** properties **`.root_squash`** and **`.sys_file`**: boolean views of DQF_* flags; type remains tuple-like (indexing, unpacking).
- **Error context**: exceptions raised from the public API have **`.device`** and **`.id`** set when applicable.
- **Validation**: `set_*_quota` requires limits to be non-negative ints; raises `ValueError`/`TypeError` before calling the kernel.
- **Docstrings**: "See also" cross-references on get/set/iter and related functions.

### Changed

- **Breaking:** `get_*_quota`, `get_next_*_quota`, and `get_*_quota_info` no longer accept `return_type`; they always return the named tuple (`Quota`, `NextQuota`, or `QuotaInfo`). Results are tuple-compatible (indexing, unpacking).
- **Breaking:** `set_*_quota` parameter `quota=` renamed to **`limits_from=`** to clarify that only the four limit fields are used (not usage or times).

## [0.1.2] - 2025-03-07

### Fixed

- C extension: add fallback definitions for `DQF_ROOT_SQUASH` and `DQF_SYS_FILE` when the build environment’s kernel headers do not define them (e.g. manylinux CI), so the module compiles and exports the constants with standard values.

## [0.1.1] - 2025-03-07

### Fixed

- Remove unused QIF_/IIF_ imports (IIF_ALL, QIF_ALL, QIF_LIMITS, QIF_TIMES, QIF_USAGE) from `pyquota/__init__.py`; only the bits used by partial conversion helpers are imported (fixes ruff F401).

## [0.1.0] - 2025-03-07

### Added

- `pyproject.toml` for PEP 517/518 build and project metadata
- Python package layout: `pyquota` package with `pyquota._native` C extension
- Type stubs (`pyquota/__init__.pyi`) for IDE and type checkers
- Named types: `Quota`, `NextQuota`, `QuotaInfo` (full data); `QuotaPartial`, `NextQuotaPartial`, `QuotaInfoPartial` (optional fields as `None` when not set)
- Unified get API: `get_*_quota`, `get_next_*_quota`, `get_*_quota_info` with optional `return_type` (`"named"` default, `"tuple"`)
- Partial APIs: `get_*_quota_partial`, `get_*_quota_info_partial` (named tuples only; validity mask interpreted into `None` fields; QIF_*/IIF_* on `pyquota._native` only)
- `set_*_quota(..., quota=Quota_or_8tuple)` to pass result of `get_*_quota` directly; clear error when `quota=` is a `QuotaPartial` with `None` limits
- Hierarchical errors: `PermissionError`, `NotFoundError`, `InvalidError` subclasses of `APIError` (with `errno`)
- C docstrings for all extension functions
- CONTRIBUTING.md, CHANGELOG.md, SECURITY.md
- Unit tests (import, constants, wrappers, partial, set_quota styles) and CI workflow
- Optional Sphinx docs and integration test harness
- Conda environment (environment.yml) for build and test
- Coverage requirement: `fail_under = 50` in `pyproject.toml`

### Changed

- **Breaking:** `get_*_quota` etc. default to named tuples; `*_named` and `*_with_valid` removed in favor of `return_type` and `*_partial`
- README: requirements (kernel, privilege), units, API overview, breaking change notice, error hierarchy
- Error messages in C extension aligned with quotactl(2) ERRORS
- CI: Python 3.9–3.14 matrix; .gitignore expanded (bytecode, venv, docs build)
- `[project.urls]` Documentation set to GitHub Pages URL; Changelog and Repository unchanged

### Removed

- CMake build: `CMakeLists.txt` removed; the project is built with setuptools only

## [0.0.3] - 2019

- Initial release (simple C extension wrapper for quotactl).
