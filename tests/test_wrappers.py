"""Tests for Python wrapper layer (get_* return named tuples; partial APIs; set_quota)."""

import pytest

import pyquota as pq


def test_quota_from_tuple():
    t = (100, 80, 50, 10, 8, 3, 0, 0)
    q = pq._quota_from_tuple(t)
    assert q.block_hard_limit == 100
    assert q.block_soft_limit == 80
    assert q.block_current == 50
    assert q.inode_hard_limit == 10
    assert q.inode_soft_limit == 8
    assert q.inode_current == 3
    assert q.block_time == 0
    assert q.inode_time == 0


def test_next_quota_from_tuple():
    t = (100, 80, 50, 10, 8, 3, 0, 0, 1000)
    nq = pq._next_quota_from_tuple(t)
    assert nq.block_hard_limit == 100
    assert nq.id == 1000


def test_quota_info_from_tuple():
    t = (604800, 604800, 1)
    info = pq._quota_info_from_tuple(t)
    assert info.block_grace == 604800
    assert info.inode_grace == 604800
    assert info.flags == 1


def test_get_user_quota_raises_without_device(monkeypatch):
    """get_user_quota propagates APIError from C layer."""
    import pyquota

    def fake_raw(device, uid):
        raise pyquota.APIError("No disk quota for the indicated user...")

    monkeypatch.setattr(pyquota, "_get_user_quota_raw", fake_raw)
    with pytest.raises(pyquota.APIError):
        pyquota.get_user_quota("/dev/nonexistent", 1000)


def test_get_user_quota_returns_quota(monkeypatch):
    """get_user_quota returns Quota named tuple (tuple-compatible)."""
    raw = (102400, 92160, 0, 0, 0, 0, 0, 0)

    def fake_raw(device, uid):
        return raw

    import pyquota

    monkeypatch.setattr(pyquota, "_get_user_quota_raw", fake_raw)
    q = pyquota.get_user_quota("/dev/sda1", 1000)
    assert q == pq.Quota(
        block_hard_limit=102400,
        block_soft_limit=92160,
        block_current=0,
        inode_hard_limit=0,
        inode_soft_limit=0,
        inode_current=0,
        block_time=0,
        inode_time=0,
    )
    # Named tuple is tuple-compatible (indexing, unpacking)
    assert q[0] == 102400 and q[1] == 92160


def test_get_user_quota_info_returns_quota_info(monkeypatch):
    import pyquota

    raw = (86400, 86400, 0)

    def fake_raw(device):
        return raw

    monkeypatch.setattr(pyquota, "_get_user_quota_info_raw", fake_raw)
    info = pyquota.get_user_quota_info("/dev/sda1")
    assert info == pq.QuotaInfo(block_grace=86400, inode_grace=86400, flags=0)


def test_get_next_user_quota_returns_next_quota(monkeypatch):
    import pyquota

    raw = (100, 80, 0, 0, 0, 0, 0, 0, 1000)

    def fake_raw(device, uid):
        return raw

    monkeypatch.setattr(pyquota, "_get_next_user_quota_raw", fake_raw)
    nq = pyquota.get_next_user_quota("/dev/sda1", 0)
    assert nq.id == 1000
    assert nq.block_hard_limit == 100


def test_get_user_quota_partial_returns_QuotaPartial(monkeypatch):
    """get_user_quota_partial returns QuotaPartial; when valid=QIF_ALL all fields are set."""
    raw = (100, 80, 50, 10, 8, 3, 0, 0, pq._native.QIF_ALL)

    def fake_raw(device, uid):
        return raw

    monkeypatch.setattr(pq, "_get_user_quota_partial_raw", fake_raw)
    result = pq.get_user_quota_partial("/dev/sda1", 1000)
    assert isinstance(result, pq.QuotaPartial)
    assert result.block_hard_limit == 100
    assert result.block_current == 50
    assert result.inode_time == 0
    assert all(
        getattr(result, f) is not None
        for f in ("block_hard_limit", "block_soft_limit", "block_current", "inode_hard_limit", "inode_soft_limit", "inode_current", "block_time", "inode_time")
    )


def test_get_user_quota_partial_none_for_invalid_bits(monkeypatch):
    """When valid mask is partial, only set bits get non-None values (library interprets QIF_*)."""
    # Only QIF_BLIMITS and QIF_SPACE set -> block limits and block_current valid
    raw = (100, 80, 50, 0, 0, 0, 0, 0, pq._native.QIF_BLIMITS | pq._native.QIF_SPACE)

    def fake_raw(device, uid):
        return raw

    monkeypatch.setattr(pq, "_get_user_quota_partial_raw", fake_raw)
    result = pq.get_user_quota_partial("/dev/sda1", 1000)
    assert result.block_hard_limit == 100
    assert result.block_soft_limit == 80
    assert result.block_current == 50
    assert result.inode_hard_limit is None
    assert result.inode_soft_limit is None
    assert result.inode_current is None
    assert result.block_time is None
    assert result.inode_time is None


def test_set_user_quota_accepts_limits_from_keyword(monkeypatch):
    """set_user_quota(device, uid, limits_from=q) extracts the four limits from Quota and calls C layer."""
    import pyquota

    calls = []

    def fake_set(device, uid, bhard, bsoft, ihard, isoft):
        calls.append((device, uid, bhard, bsoft, ihard, isoft))
        return None

    monkeypatch.setattr(pyquota, "_set_user_quota_raw", fake_set)
    q = pyquota.Quota(block_hard_limit=100, block_soft_limit=80, block_current=50, inode_hard_limit=10, inode_soft_limit=8, inode_current=3, block_time=0, inode_time=0)
    pyquota.set_user_quota("/dev/sda1", 1000, limits_from=q)
    assert calls == [("/dev/sda1", 1000, 100, 80, 10, 8)]


def test_set_user_quota_rejects_limits_from_partial_with_none(monkeypatch):
    """set_user_quota(device, uid, limits_from=QuotaPartial_with_None) raises; all four limits required."""
    import pyquota

    monkeypatch.setattr(pyquota, "_set_user_quota_raw", lambda *a: None)
    partial = pyquota.QuotaPartial(100, 80, 50, None, None, None, None, None)  # inode limits None
    with pytest.raises(TypeError, match="limits_from"):
        pyquota.set_user_quota("/dev/sda1", 1000, limits_from=partial)


def test_set_user_quota_accepts_four_limits(monkeypatch):
    """set_user_quota(device, uid, bhard, bsoft, ihard, isoft) still works."""
    import pyquota

    calls = []

    def fake_set(device, uid, bhard, bsoft, ihard, isoft):
        calls.append((device, uid, bhard, bsoft, ihard, isoft))
        return None

    monkeypatch.setattr(pyquota, "_set_user_quota_raw", fake_set)
    pyquota.set_user_quota("/dev/sda1", 1000, 102400, 92160, 0, 0)
    assert calls == [("/dev/sda1", 1000, 102400, 92160, 0, 0)]


def test_get_user_quota_info_partial_none_for_invalid_bits(monkeypatch):
    """QuotaInfoPartial: only set IIF_* bits get non-None (library interprets dqi_valid)."""
    raw = (86400, 0, 0, pq._native.IIF_BGRACE)  # only block_grace valid

    def fake_raw(device):
        return raw

    monkeypatch.setattr(pq, "_get_user_quota_info_partial_raw", fake_raw)
    result = pq.get_user_quota_info_partial("/dev/sda1")
    assert result.block_grace == 86400
    assert result.inode_grace is None
    assert result.flags is None


def test_iter_user_quotas_yields_until_not_found(monkeypatch):
    """iter_user_quotas yields NextQuota for each get_next until NotFoundError."""
    import pyquota as pq

    calls = []

    def fake_next(device, uid):
        calls.append(uid)
        if uid == 0:
            return (100, 80, 0, 0, 0, 0, 0, 0, 1000)
        if uid == 1001:
            return (200, 160, 0, 0, 0, 0, 0, 0, 1001)
        raise pq.NotFoundError("no next")

    monkeypatch.setattr(pq, "_get_next_user_quota_raw", fake_next)
    items = list(pq.iter_user_quotas("/dev/sda1", 0))
    assert len(items) == 2
    assert items[0].id == 1000 and items[1].id == 1001
    assert calls == [0, 1001, 1002]  # 1002 call raises NotFoundError and stops iteration


def test_set_user_quota_rejects_negative_limit(monkeypatch):
    """set_user_quota raises ValueError if any limit is negative."""
    import pyquota as pq

    monkeypatch.setattr(pq, "_set_user_quota_raw", lambda *a: None)
    with pytest.raises(ValueError, match="block_hard_limit"):
        pq.set_user_quota("/dev/sda1", 1000, -1, 0, 0, 0)
    with pytest.raises(ValueError, match="inode_soft_limit"):
        pq.set_user_quota("/dev/sda1", 1000, 0, 0, 0, -1)


def test_api_error_gets_device_and_id(monkeypatch):
    """When get_user_quota raises, the exception has .device and .id set."""
    import pyquota as pq

    def raise_err(device, uid):
        raise pq.APIError("no quota")

    monkeypatch.setattr(pq, "_get_user_quota_raw", raise_err)
    try:
        pq.get_user_quota("/dev/sda1", 1000)
    except pq.APIError as e:
        assert e.device == "/dev/sda1"
        assert e.id == 1000
    else:
        pytest.fail("expected APIError")
