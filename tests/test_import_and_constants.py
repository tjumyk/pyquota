"""Tests for module import and exported constants."""


def test_import_pyquota():
    """Import pyquota (package) and access C extension via public API."""
    import pyquota as pq

    assert pq is not None
    assert hasattr(pq, "get_user_quota")
    assert hasattr(pq, "APIError")


def test_api_error_is_exception():
    import pyquota as pq

    assert issubclass(pq.APIError, Exception)


def test_error_hierarchy():
    """PermissionError, NotFoundError, InvalidError are subclasses of APIError."""
    import pyquota as pq

    assert issubclass(pq.PermissionError, pq.APIError)
    assert issubclass(pq.NotFoundError, pq.APIError)
    assert issubclass(pq.InvalidError, pq.APIError)


def test_quota_format_constants():
    import pyquota as pq

    assert hasattr(pq, "QFMT_VFS_OLD")
    assert hasattr(pq, "QFMT_VFS_V0")
    assert hasattr(pq, "QFMT_VFS_V1")
    assert isinstance(pq.QFMT_VFS_OLD, int)
    assert isinstance(pq.QFMT_VFS_V0, int)
    assert isinstance(pq.QFMT_VFS_V1, int)
    # Values from linux/quota.h (may differ by kernel; at least distinct)
    assert pq.QFMT_VFS_OLD != pq.QFMT_VFS_V0 or pq.QFMT_VFS_V0 != pq.QFMT_VFS_V1


def test_quota_info_flags_constants():
    import pyquota as pq

    assert hasattr(pq, "DQF_ROOT_SQUASH")
    assert hasattr(pq, "DQF_SYS_FILE")
    assert isinstance(pq.DQF_ROOT_SQUASH, int)
    assert isinstance(pq.DQF_SYS_FILE, int)


def test_named_types_exported():
    import pyquota as pq

    assert hasattr(pq, "Quota")
    assert hasattr(pq, "QuotaInfo")
    assert hasattr(pq, "NextQuota")
    assert hasattr(pq, "QuotaPartial")
    assert hasattr(pq, "NextQuotaPartial")
    assert hasattr(pq, "QuotaInfoPartial")
    assert issubclass(pq.Quota, tuple)
    assert issubclass(pq.QuotaInfo, tuple)
    assert issubclass(pq.NextQuota, tuple)
    assert issubclass(pq.QuotaPartial, tuple)
    assert issubclass(pq.NextQuotaPartial, tuple)
    assert issubclass(pq.QuotaInfoPartial, tuple)


def test_errno_constants_exported():
    import pyquota as pq

    for name in ("EACCES", "EBUSY", "EFAULT", "EINVAL", "ENOENT", "ENOSYS", "ENOTBLK", "EPERM", "ERANGE", "ESRCH"):
        assert hasattr(pq, name), f"missing {name}"
        assert isinstance(getattr(pq, name), int)
