"""Pytest configuration and shared fixtures."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: tests that require root and a real quota device (deselect with -m 'not integration')",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """Skip all tests if pyquota cannot be imported (e.g. non-Linux or C extension not built)."""
    try:
        import pyquota  # noqa: F401
    except Exception:
        skip_no_native = pytest.mark.skip(reason="pyquota._native not available (Linux + build required)")
        for item in items:
            item.add_marker(skip_no_native)
