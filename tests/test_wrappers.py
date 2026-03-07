"""Tests for Python wrapper layer (return_type, partial named tuples)."""

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


def test_get_user_quota_returns_quota_by_default(monkeypatch):
    """get_user_quota(device, uid) returns Quota named tuple by default."""
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


def test_get_user_quota_return_type_tuple(monkeypatch):
    """get_user_quota(..., return_type='tuple') returns raw tuple."""
    raw = (102400, 92160, 0, 0, 0, 0, 0, 0)
    monkeypatch.setattr(pq, "_get_user_quota_raw", lambda d, u: raw)
    result = pq.get_user_quota("/dev/sda1", 1000, return_type="tuple")
    assert result == raw


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


def test_set_user_quota_accepts_quota_keyword(monkeypatch):
    """set_user_quota(device, uid, quota=q) extracts the four limits from Quota and calls C layer."""
    import pyquota

    calls = []

    def fake_set(device, uid, bhard, bsoft, ihard, isoft):
        calls.append((device, uid, bhard, bsoft, ihard, isoft))
        return None

    monkeypatch.setattr(pyquota, "_set_user_quota_raw", fake_set)
    q = pyquota.Quota(block_hard_limit=100, block_soft_limit=80, block_current=50, inode_hard_limit=10, inode_soft_limit=8, inode_current=3, block_time=0, inode_time=0)
    pyquota.set_user_quota("/dev/sda1", 1000, quota=q)
    assert calls == [("/dev/sda1", 1000, 100, 80, 10, 8)]


def test_set_user_quota_rejects_quota_partial_with_none_limits(monkeypatch):
    """set_user_quota(device, uid, quota=QuotaPartial_with_None) raises; only full Quota is accepted."""
    import pyquota

    monkeypatch.setattr(pyquota, "_set_user_quota_raw", lambda *a: None)
    partial = pyquota.QuotaPartial(100, 80, 50, None, None, None, None, None)  # inode limits None
    with pytest.raises(TypeError, match="QuotaPartial may have None"):
        pyquota.set_user_quota("/dev/sda1", 1000, quota=partial)


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
