"""Integration tests: require Linux, root (or CAP_SYS_ADMIN), and a block device with quota.

Run only in a safe test environment:
    PYQUOTA_INTEGRATION=1 sudo -E pytest tests/test_integration.py -v

Skip by default (no root, or no env var).
"""

import os
import pytest

# Skip entire module unless integration tests are explicitly requested
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PYQUOTA_INTEGRATION") != "1",
        reason="Set PYQUOTA_INTEGRATION=1 and run with privilege to run integration tests",
    ),
]


def test_import_and_has_quota_functions():
    """Smoke test: module loads and exposes quota functions."""
    import pyquota as pq

    assert callable(pq.user_quota_on)
    assert callable(pq.get_user_quota_format)


# Add more integration tests only when you have a dedicated test device, e.g.:
#
# def test_get_user_quota_on_test_device():
#     import pyquota as pq
#     # Use a loop device or test partition path, e.g. "/dev/loop0" or "/dev/sda1"
#     # fmt = pq.get_user_quota_format("/dev/sda1")  # may raise if quota not enabled
#     # pq.get_user_quota("/dev/sda1", 0)
#     pass
