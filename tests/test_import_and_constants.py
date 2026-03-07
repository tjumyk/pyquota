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


def test_quota_format_enum_members():
    """QuotaFormat provides VFS_OLD, VFS_V0, VFS_V1 as ints; values are distinct."""
    import pyquota as pq

    assert hasattr(pq.QuotaFormat, "VFS_OLD")
    assert hasattr(pq.QuotaFormat, "VFS_V0")
    assert hasattr(pq.QuotaFormat, "VFS_V1")
    assert isinstance(pq.QuotaFormat.VFS_OLD, int)
    assert isinstance(pq.QuotaFormat.VFS_V0, int)
    assert isinstance(pq.QuotaFormat.VFS_V1, int)
    assert pq.QuotaFormat.VFS_OLD != pq.QuotaFormat.VFS_V0 or pq.QuotaFormat.VFS_V0 != pq.QuotaFormat.VFS_V1


def test_quota_info_flags_constants():
    import pyquota as pq

    assert hasattr(pq, "DQF_ROOT_SQUASH")
    assert hasattr(pq, "DQF_SYS_FILE")
    assert isinstance(pq.DQF_ROOT_SQUASH, int)
    assert isinstance(pq.DQF_SYS_FILE, int)


def test_quota_format_enum():
    """QuotaFormat enum matches kernel QFMT_* and is usable where int format is expected."""
    import pyquota as pq

    assert hasattr(pq, "QuotaFormat")
    # Values match C extension (kernel QFMT_*)
    assert pq.QuotaFormat.VFS_OLD == pq._native.QFMT_VFS_OLD
    assert pq.QuotaFormat.VFS_V0 == pq._native.QFMT_VFS_V0
    assert pq.QuotaFormat.VFS_V1 == pq._native.QFMT_VFS_V1
    assert isinstance(pq.QuotaFormat.VFS_V0, int)


def test_quota_info_tuple_like_and_flag_properties():
    """QuotaInfo is tuple-like and has .root_squash and .sys_file from flags."""
    import pyquota as pq

    info = pq.QuotaInfo(block_grace=86400, inode_grace=86400, flags=0)
    assert info[0] == 86400 and info[1] == 86400 and info[2] == 0
    assert info.root_squash is False
    assert info.sys_file is False
    info2 = pq.QuotaInfo(0, 0, pq.DQF_ROOT_SQUASH)
    assert info2.root_squash is True
    info3 = pq.QuotaInfo(0, 0, pq.DQF_SYS_FILE)
    assert info3.sys_file is True


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


def test_iter_quotas_exported():
    import pyquota as pq

    assert hasattr(pq, "iter_user_quotas")
    assert hasattr(pq, "iter_group_quotas")
    assert hasattr(pq, "iter_project_quotas")
    assert callable(pq.iter_user_quotas)


def test_errno_constants_exported():
    import pyquota as pq

    for name in ("EACCES", "EBUSY", "EFAULT", "EINVAL", "ENOENT", "ENOSYS", "ENOTBLK", "EPERM", "ERANGE", "ESRCH"):
        assert hasattr(pq, name), f"missing {name}"
        assert isinstance(getattr(pq, name), int)
