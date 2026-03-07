"""
PyQuota: Python wrapper for Linux quotactl(2) APIs.

Kernel support: >= 2.4.22. Project quota requires >= 4.1; Q_GETNEXTQUOTA requires >= 4.6.
"""

from typing import Literal, NamedTuple, Optional

from pyquota._native import (
    APIError,
    DQF_ROOT_SQUASH,
    DQF_SYS_FILE,
    EACCES,
    EBUSY,
    EFAULT,
    EINVAL,
    ENOENT,
    ENOSYS,
    ENOTBLK,
    EPERM,
    ERANGE,
    ESRCH,
    IIF_ALL,
    IIF_BGRACE,
    IIF_FLAGS,
    IIF_IGRACE,
    InvalidError,
    NotFoundError,
    PermissionError,
    QIF_ALL,
    QIF_BLIMITS,
    QIF_BTIME,
    QIF_ILIMITS,
    QIF_INODES,
    QIF_ITIME,
    QIF_LIMITS,
    QIF_SPACE,
    QIF_TIMES,
    QIF_USAGE,
    QFMT_VFS_OLD,
    QFMT_VFS_V0,
    QFMT_VFS_V1,
    get_group_quota as _get_group_quota_raw,
    get_group_quota_format,
    get_group_quota_info as _get_group_quota_info_raw,
    get_group_quota_info_partial as _get_group_quota_info_partial_raw,
    get_group_quota_partial as _get_group_quota_partial_raw,
    get_next_group_quota as _get_next_group_quota_raw,
    get_next_group_quota_partial as _get_next_group_quota_partial_raw,
    get_next_project_quota as _get_next_project_quota_raw,
    get_next_project_quota_partial as _get_next_project_quota_partial_raw,
    get_next_user_quota as _get_next_user_quota_raw,
    get_next_user_quota_partial as _get_next_user_quota_partial_raw,
    get_project_quota as _get_project_quota_raw,
    get_project_quota_format,
    get_project_quota_info as _get_project_quota_info_raw,
    get_project_quota_info_partial as _get_project_quota_info_partial_raw,
    get_project_quota_partial as _get_project_quota_partial_raw,
    get_user_quota as _get_user_quota_raw,
    get_user_quota_format,
    get_user_quota_info as _get_user_quota_info_raw,
    get_user_quota_info_partial as _get_user_quota_info_partial_raw,
    get_user_quota_partial as _get_user_quota_partial_raw,
    group_quota_off,
    group_quota_on,
    project_quota_off,
    project_quota_on,
    set_group_quota as _set_group_quota_raw,
    set_group_quota_info,
    set_project_quota as _set_project_quota_raw,
    set_project_quota_info,
    set_user_quota as _set_user_quota_raw,
    set_user_quota_info,
    sync_group_quotas,
    sync_project_quotas,
    sync_user_quotas,
    user_quota_off,
    user_quota_on,
)


# --- Named result types (units: block limits in 1024-byte blocks, block_current in bytes, grace in seconds) ---


class Quota(NamedTuple):
    """Disk quota limits and current usage for one user/group/project.

    Block limits are in 1024-byte disk quota blocks; block_current is in bytes.
    block_time and inode_time are Unix timestamps (seconds since epoch) when
    the grace period for exceeding the soft limit expires, or 0 if not over limit.
    """

    block_hard_limit: int  # 1024-byte blocks
    block_soft_limit: int  # 1024-byte blocks
    block_current: int  # bytes
    inode_hard_limit: int
    inode_soft_limit: int
    inode_current: int
    block_time: int  # Unix time when block grace expires; 0 if not over soft limit
    inode_time: int  # Unix time when inode grace expires; 0 if not over soft limit


class NextQuota(NamedTuple):
    """Quota for the next ID >= given ID that has an active quota (includes id)."""

    block_hard_limit: int
    block_soft_limit: int
    block_current: int
    inode_hard_limit: int
    inode_soft_limit: int
    inode_current: int
    block_time: int
    inode_time: int
    id: int  # uid, gid, or projid


class QuotaInfo(NamedTuple):
    """Quotafile info: grace periods and flags."""

    block_grace: int  # seconds before block soft limit becomes hard
    inode_grace: int  # seconds before inode soft limit becomes hard
    flags: int  # DQF_* bits


class QuotaPartial(NamedTuple):
    """Quota from get_*_quota_partial. Fields are None when the kernel did not supply them (per man 2 quotactl dqb_valid)."""

    block_hard_limit: Optional[int]
    block_soft_limit: Optional[int]
    block_current: Optional[int]
    inode_hard_limit: Optional[int]
    inode_soft_limit: Optional[int]
    inode_current: Optional[int]
    block_time: Optional[int]
    inode_time: Optional[int]


class NextQuotaPartial(NamedTuple):
    """Next-quota from get_next_*_quota_partial. Quota fields are None when not set by kernel; id is always set."""

    block_hard_limit: Optional[int]
    block_soft_limit: Optional[int]
    block_current: Optional[int]
    inode_hard_limit: Optional[int]
    inode_soft_limit: Optional[int]
    inode_current: Optional[int]
    block_time: Optional[int]
    inode_time: Optional[int]
    id: int  # uid/gid/projid returned by kernel


class QuotaInfoPartial(NamedTuple):
    """Quotafile info from get_*_quota_info_partial. Fields are None when not set (per man 2 quotactl dqi_valid)."""

    block_grace: Optional[int]
    inode_grace: Optional[int]
    flags: Optional[int]


def _quota_from_tuple(t: tuple) -> Quota:
    return Quota(
        block_hard_limit=t[0],
        block_soft_limit=t[1],
        block_current=t[2],
        inode_hard_limit=t[3],
        inode_soft_limit=t[4],
        inode_current=t[5],
        block_time=t[6],
        inode_time=t[7],
    )


def _next_quota_from_tuple(t: tuple) -> NextQuota:
    return NextQuota(
        block_hard_limit=t[0],
        block_soft_limit=t[1],
        block_current=t[2],
        inode_hard_limit=t[3],
        inode_soft_limit=t[4],
        inode_current=t[5],
        block_time=t[6],
        inode_time=t[7],
        id=t[8],
    )


def _quota_info_from_tuple(t: tuple) -> QuotaInfo:
    return QuotaInfo(block_grace=t[0], inode_grace=t[1], flags=t[2])


def _quota_partial_from_tuple(t: tuple) -> QuotaPartial:
    """Interpret dqb_valid (man 2 quotactl): set field to None when its QIF_* bit is not set."""
    v = t[8]
    return QuotaPartial(
        block_hard_limit=t[0] if (v & QIF_BLIMITS) else None,
        block_soft_limit=t[1] if (v & QIF_BLIMITS) else None,
        block_current=t[2] if (v & QIF_SPACE) else None,
        inode_hard_limit=t[3] if (v & QIF_ILIMITS) else None,
        inode_soft_limit=t[4] if (v & QIF_ILIMITS) else None,
        inode_current=t[5] if (v & QIF_INODES) else None,
        block_time=t[6] if (v & QIF_BTIME) else None,
        inode_time=t[7] if (v & QIF_ITIME) else None,
    )


def _next_quota_partial_from_tuple(t: tuple) -> NextQuotaPartial:
    v = t[9]
    return NextQuotaPartial(
        block_hard_limit=t[0] if (v & QIF_BLIMITS) else None,
        block_soft_limit=t[1] if (v & QIF_BLIMITS) else None,
        block_current=t[2] if (v & QIF_SPACE) else None,
        inode_hard_limit=t[3] if (v & QIF_ILIMITS) else None,
        inode_soft_limit=t[4] if (v & QIF_ILIMITS) else None,
        inode_current=t[5] if (v & QIF_INODES) else None,
        block_time=t[6] if (v & QIF_BTIME) else None,
        inode_time=t[7] if (v & QIF_ITIME) else None,
        id=t[8],
    )


def _quota_info_partial_from_tuple(t: tuple) -> QuotaInfoPartial:
    """Interpret dqi_valid: IIF_BGRACE→block_grace, IIF_IGRACE→inode_grace, IIF_FLAGS→flags."""
    v = t[3]
    return QuotaInfoPartial(
        block_grace=t[0] if (v & IIF_BGRACE) else None,
        inode_grace=t[1] if (v & IIF_IGRACE) else None,
        flags=t[2] if (v & IIF_FLAGS) else None,
    )


# --- Unified get API: return_type="named" (default) or "tuple" ---

_ReturnType = Literal["named", "tuple"]


def get_user_quota(device: str, uid: int, return_type: _ReturnType = "named"):
    """Get user quota. return_type: 'named' (default) -> Quota, 'tuple' -> raw 8-tuple."""
    raw = _get_user_quota_raw(device, uid)
    return _quota_from_tuple(raw) if return_type == "named" else raw


def get_next_user_quota(device: str, uid: int, return_type: _ReturnType = "named"):
    """Get next user quota (id >= uid). return_type: 'named' (default) -> NextQuota, 'tuple' -> raw 9-tuple."""
    raw = _get_next_user_quota_raw(device, uid)
    return _next_quota_from_tuple(raw) if return_type == "named" else raw


def get_user_quota_info(device: str, return_type: _ReturnType = "named"):
    """Get user quotafile info. return_type: 'named' (default) -> QuotaInfo, 'tuple' -> raw 3-tuple."""
    raw = _get_user_quota_info_raw(device)
    return _quota_info_from_tuple(raw) if return_type == "named" else raw


def get_group_quota(device: str, gid: int, return_type: _ReturnType = "named"):
    raw = _get_group_quota_raw(device, gid)
    return _quota_from_tuple(raw) if return_type == "named" else raw


def get_next_group_quota(device: str, gid: int, return_type: _ReturnType = "named"):
    raw = _get_next_group_quota_raw(device, gid)
    return _next_quota_from_tuple(raw) if return_type == "named" else raw


def get_group_quota_info(device: str, return_type: _ReturnType = "named"):
    raw = _get_group_quota_info_raw(device)
    return _quota_info_from_tuple(raw) if return_type == "named" else raw


def get_project_quota(device: str, projid: int, return_type: _ReturnType = "named"):
    raw = _get_project_quota_raw(device, projid)
    return _quota_from_tuple(raw) if return_type == "named" else raw


def get_next_project_quota(device: str, projid: int, return_type: _ReturnType = "named"):
    raw = _get_next_project_quota_raw(device, projid)
    return _next_quota_from_tuple(raw) if return_type == "named" else raw


def get_project_quota_info(device: str, return_type: _ReturnType = "named"):
    raw = _get_project_quota_info_raw(device)
    return _quota_info_from_tuple(raw) if return_type == "named" else raw


# --- Partial (allow incomplete kernel data); named tuple only ---

def get_user_quota_partial(device: str, uid: int) -> QuotaPartial:
    """Get user quota allowing partial kernel data. Unset fields are None."""
    return _quota_partial_from_tuple(_get_user_quota_partial_raw(device, uid))


def get_next_user_quota_partial(device: str, uid: int) -> NextQuotaPartial:
    return _next_quota_partial_from_tuple(_get_next_user_quota_partial_raw(device, uid))


def get_user_quota_info_partial(device: str) -> QuotaInfoPartial:
    return _quota_info_partial_from_tuple(_get_user_quota_info_partial_raw(device))


def get_group_quota_partial(device: str, gid: int) -> QuotaPartial:
    return _quota_partial_from_tuple(_get_group_quota_partial_raw(device, gid))


def get_next_group_quota_partial(device: str, gid: int) -> NextQuotaPartial:
    return _next_quota_partial_from_tuple(_get_next_group_quota_partial_raw(device, gid))


def get_group_quota_info_partial(device: str) -> QuotaInfoPartial:
    return _quota_info_partial_from_tuple(_get_group_quota_info_partial_raw(device))


def get_project_quota_partial(device: str, projid: int) -> QuotaPartial:
    return _quota_partial_from_tuple(_get_project_quota_partial_raw(device, projid))


def get_next_project_quota_partial(device: str, projid: int) -> NextQuotaPartial:
    return _next_quota_partial_from_tuple(_get_next_project_quota_partial_raw(device, projid))


def get_project_quota_info_partial(device: str) -> QuotaInfoPartial:
    return _quota_info_partial_from_tuple(_get_project_quota_info_partial_raw(device))


def _limits_from_quota(quota) -> tuple:
    """Extract (block_hard, block_soft, inode_hard, inode_soft) from Quota or 8-tuple. set_quota uses only these four."""
    if hasattr(quota, "block_hard_limit"):
        return (quota.block_hard_limit, quota.block_soft_limit, quota.inode_hard_limit, quota.inode_soft_limit)
    return (quota[0], quota[1], quota[3], quota[4])


def set_user_quota(
    device: str,
    uid: int,
    block_hard_limit: Optional[int] = None,
    block_soft_limit: Optional[int] = None,
    inode_hard_limit: Optional[int] = None,
    inode_soft_limit: Optional[int] = None,
    *,
    quota=None,
):
    """Set user quota limits. Pass the four limits, or quota=<Quota/8-tuple> from get_user_quota (only the four limit fields are used). QuotaPartial with None limits is not accepted; use get_user_quota() or pass limits explicitly."""
    if quota is not None:
        block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit = _limits_from_quota(quota)
    if block_hard_limit is None or block_soft_limit is None or inode_hard_limit is None or inode_soft_limit is None:
        raise TypeError(
            "set_user_quota() requires either four limit arguments or quota= from get_user_quota() "
            "(QuotaPartial may have None fields and cannot be used here)"
        )
    return _set_user_quota_raw(device, uid, block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit)


def set_group_quota(
    device: str,
    gid: int,
    block_hard_limit: Optional[int] = None,
    block_soft_limit: Optional[int] = None,
    inode_hard_limit: Optional[int] = None,
    inode_soft_limit: Optional[int] = None,
    *,
    quota=None,
):
    """Set group quota limits. Pass the four limits, or quota=<Quota/8-tuple> from get_group_quota."""
    if quota is not None:
        block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit = _limits_from_quota(quota)
    if block_hard_limit is None or block_soft_limit is None or inode_hard_limit is None or inode_soft_limit is None:
        raise TypeError(
            "set_group_quota() requires either four limit arguments or quota= from get_group_quota() "
            "(QuotaPartial may have None fields and cannot be used here)"
        )
    return _set_group_quota_raw(device, gid, block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit)


def set_project_quota(
    device: str,
    projid: int,
    block_hard_limit: Optional[int] = None,
    block_soft_limit: Optional[int] = None,
    inode_hard_limit: Optional[int] = None,
    inode_soft_limit: Optional[int] = None,
    *,
    quota=None,
):
    """Set project quota limits. Pass the four limits, or quota=<Quota/8-tuple> from get_project_quota."""
    if quota is not None:
        block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit = _limits_from_quota(quota)
    if block_hard_limit is None or block_soft_limit is None or inode_hard_limit is None or inode_soft_limit is None:
        raise TypeError(
            "set_project_quota() requires either four limit arguments or quota= from get_project_quota() "
            "(QuotaPartial may have None fields and cannot be used here)"
        )
    return _set_project_quota_raw(device, projid, block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit)


__all__ = [
    "APIError",
    "DQF_ROOT_SQUASH",
    "DQF_SYS_FILE",
    "EACCES",
    "EBUSY",
    "EFAULT",
    "EINVAL",
    "ENOENT",
    "ENOSYS",
    "ENOTBLK",
    "EPERM",
    "ERANGE",
    "ESRCH",
    "InvalidError",
    "NotFoundError",
    "NextQuota",
    "NextQuotaPartial",
    "PermissionError",
    "Quota",
    "QuotaInfo",
    "QuotaInfoPartial",
    "QuotaPartial",
    "QFMT_VFS_OLD",
    "QFMT_VFS_V0",
    "QFMT_VFS_V1",
    "get_group_quota",
    "get_group_quota_format",
    "get_group_quota_info",
    "get_group_quota_info_partial",
    "get_group_quota_partial",
    "get_next_group_quota",
    "get_next_group_quota_partial",
    "get_next_project_quota",
    "get_next_project_quota_partial",
    "get_next_user_quota",
    "get_next_user_quota_partial",
    "get_project_quota",
    "get_project_quota_format",
    "get_project_quota_info",
    "get_project_quota_info_partial",
    "get_project_quota_partial",
    "get_user_quota",
    "get_user_quota_format",
    "get_user_quota_info",
    "get_user_quota_info_partial",
    "get_user_quota_partial",
    "group_quota_off",
    "group_quota_on",
    "project_quota_off",
    "project_quota_on",
    "set_group_quota",
    "set_group_quota_info",
    "set_project_quota",
    "set_project_quota_info",
    "set_user_quota",
    "set_user_quota_info",
    "sync_group_quotas",
    "sync_project_quotas",
    "sync_user_quotas",
    "user_quota_off",
    "user_quota_on",
]
