"""
PyQuota: Python wrapper for Linux quotactl(2) APIs.

Kernel support: >= 2.4.22. Project quota requires >= 4.1; Q_GETNEXTQUOTA requires >= 4.6.
"""

from enum import IntEnum
from typing import Iterator, NamedTuple, Optional

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
    IIF_BGRACE,
    IIF_FLAGS,
    IIF_IGRACE,
    InvalidError,
    NotFoundError,
    PermissionError,
    QIF_BLIMITS,
    QIF_BTIME,
    QIF_ILIMITS,
    QIF_INODES,
    QIF_ITIME,
    QIF_SPACE,
    QFMT_VFS_OLD as _QFMT_VFS_OLD,
    QFMT_VFS_V0 as _QFMT_VFS_V0,
    QFMT_VFS_V1 as _QFMT_VFS_V1,
    get_group_quota as _get_group_quota_raw,
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
    get_project_quota_info as _get_project_quota_info_raw,
    get_project_quota_info_partial as _get_project_quota_info_partial_raw,
    get_project_quota_partial as _get_project_quota_partial_raw,
    get_user_quota as _get_user_quota_raw,
    get_user_quota_format as _get_user_quota_format_raw,
    get_user_quota_info as _get_user_quota_info_raw,
    get_user_quota_info_partial as _get_user_quota_info_partial_raw,
    get_user_quota_partial as _get_user_quota_partial_raw,
    get_group_quota_format as _get_group_quota_format_raw,
    get_project_quota_format as _get_project_quota_format_raw,
    group_quota_off as _group_quota_off_raw,
    group_quota_on as _group_quota_on_raw,
    project_quota_off as _project_quota_off_raw,
    project_quota_on as _project_quota_on_raw,
    set_group_quota as _set_group_quota_raw,
    set_group_quota_info as _set_group_quota_info_raw,
    set_project_quota as _set_project_quota_raw,
    set_project_quota_info as _set_project_quota_info_raw,
    set_user_quota as _set_user_quota_raw,
    set_user_quota_info as _set_user_quota_info_raw,
    sync_group_quotas as _sync_group_quotas_raw,
    sync_project_quotas as _sync_project_quotas_raw,
    sync_user_quotas as _sync_user_quotas_raw,
    user_quota_off as _user_quota_off_raw,
    user_quota_on as _user_quota_on_raw,
)


# --- Enums and named result types ---


class QuotaFormat(IntEnum):
    """Quota filesystem format for quota_on / get_*_quota_format. Values match kernel QFMT_*."""

    VFS_OLD = _QFMT_VFS_OLD
    VFS_V0 = _QFMT_VFS_V0
    VFS_V1 = _QFMT_VFS_V1


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
    """Quotafile info: grace periods and flags. Tuple-like (indexing, unpacking)."""

    block_grace: int  # seconds before block soft limit becomes hard
    inode_grace: int  # seconds before inode soft limit becomes hard
    flags: int  # DQF_* bits

    @property
    def root_squash(self) -> bool:
        """True if DQF_ROOT_SQUASH is set (v1 format root squash enabled)."""
        return bool(self.flags & DQF_ROOT_SQUASH)

    @property
    def sys_file(self) -> bool:
        """True if DQF_SYS_FILE is set (quota stored in system inode)."""
        return bool(self.flags & DQF_SYS_FILE)


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


def _run_with_context(fn, device: Optional[str] = None, quota_id: Optional[int] = None):
    """Run fn(); on APIError, attach device and id to the exception and re-raise."""
    try:
        return fn()
    except APIError as e:
        e.device = device  # type: ignore[attr-defined]
        e.id = quota_id  # type: ignore[attr-defined]
        raise


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


# --- Get API: always return named tuple (Quota, NextQuota, QuotaInfo); tuple-compatible (indexing, unpacking) ---


def get_user_quota(device: str, uid: int) -> Quota:
    """Get user quota. Returns Quota named tuple (tuple-compatible).
    See also: set_user_quota, get_user_quota_partial."""
    return _run_with_context(
        lambda: _quota_from_tuple(_get_user_quota_raw(device, uid)),
        device=device,
        quota_id=uid,
    )


def get_next_user_quota(device: str, uid: int) -> NextQuota:
    """Get next user quota (id >= uid). Returns NextQuota named tuple (tuple-compatible).
    See also: iter_user_quotas, get_user_quota."""
    return _run_with_context(
        lambda: _next_quota_from_tuple(_get_next_user_quota_raw(device, uid)),
        device=device,
        quota_id=uid,
    )


def get_user_quota_info(device: str) -> QuotaInfo:
    """Get user quotafile info. Returns QuotaInfo (tuple-like; .root_squash, .sys_file).
    See also: set_user_quota_info."""
    return _run_with_context(
        lambda: _quota_info_from_tuple(_get_user_quota_info_raw(device)),
        device=device,
    )


def get_group_quota(device: str, gid: int) -> Quota:
    """Get group quota. See also: set_group_quota, get_group_quota_partial."""
    return _run_with_context(
        lambda: _quota_from_tuple(_get_group_quota_raw(device, gid)),
        device=device,
        quota_id=gid,
    )


def get_next_group_quota(device: str, gid: int) -> NextQuota:
    """Get next group quota (id >= gid). See also: iter_group_quotas, get_group_quota."""
    return _run_with_context(
        lambda: _next_quota_from_tuple(_get_next_group_quota_raw(device, gid)),
        device=device,
        quota_id=gid,
    )


def get_group_quota_info(device: str) -> QuotaInfo:
    """Get group quotafile info. See also: set_group_quota_info."""
    return _run_with_context(
        lambda: _quota_info_from_tuple(_get_group_quota_info_raw(device)),
        device=device,
    )


def get_project_quota(device: str, projid: int) -> Quota:
    """Get project quota. See also: set_project_quota, get_project_quota_partial."""
    return _run_with_context(
        lambda: _quota_from_tuple(_get_project_quota_raw(device, projid)),
        device=device,
        quota_id=projid,
    )


def get_next_project_quota(device: str, projid: int) -> NextQuota:
    """Get next project quota (id >= projid). See also: iter_project_quotas, get_project_quota."""
    return _run_with_context(
        lambda: _next_quota_from_tuple(_get_next_project_quota_raw(device, projid)),
        device=device,
        quota_id=projid,
    )


def get_project_quota_info(device: str) -> QuotaInfo:
    """Get project quotafile info. See also: set_project_quota_info."""
    return _run_with_context(
        lambda: _quota_info_from_tuple(_get_project_quota_info_raw(device)),
        device=device,
    )


# --- Iterators (use get_next_* under the hood; get_next_* remains the primitive for a single "next" query) ---


def iter_user_quotas(device: str, start_uid: int = 0) -> Iterator[NextQuota]:
    """Yield NextQuota for each user with quota on device (id >= start_uid). Uses get_next_user_quota.
    See also: get_next_user_quota."""
    uid = start_uid
    while True:
        try:
            nq = get_next_user_quota(device, uid)
        except NotFoundError:
            break
        yield nq
        uid = nq.id + 1


def iter_group_quotas(device: str, start_gid: int = 0) -> Iterator[NextQuota]:
    """Yield NextQuota for each group with quota on device (id >= start_gid). See also: get_next_group_quota."""
    gid = start_gid
    while True:
        try:
            nq = get_next_group_quota(device, gid)
        except NotFoundError:
            break
        yield nq
        gid = nq.id + 1


def iter_project_quotas(device: str, start_projid: int = 0) -> Iterator[NextQuota]:
    """Yield NextQuota for each project with quota on device (id >= start_projid). See also: get_next_project_quota."""
    projid = start_projid
    while True:
        try:
            nq = get_next_project_quota(device, projid)
        except NotFoundError:
            break
        yield nq
        projid = nq.id + 1


# --- Partial (allow incomplete kernel data); named tuple only ---

def get_user_quota_partial(device: str, uid: int) -> QuotaPartial:
    """Get user quota allowing partial kernel data. Unset fields are None. See also: get_user_quota."""
    return _run_with_context(
        lambda: _quota_partial_from_tuple(_get_user_quota_partial_raw(device, uid)),
        device=device,
        quota_id=uid,
    )


def get_next_user_quota_partial(device: str, uid: int) -> NextQuotaPartial:
    """See also: get_next_user_quota."""
    return _run_with_context(
        lambda: _next_quota_partial_from_tuple(_get_next_user_quota_partial_raw(device, uid)),
        device=device,
        quota_id=uid,
    )


def get_user_quota_info_partial(device: str) -> QuotaInfoPartial:
    """See also: get_user_quota_info."""
    return _run_with_context(
        lambda: _quota_info_partial_from_tuple(_get_user_quota_info_partial_raw(device)),
        device=device,
    )


def get_group_quota_partial(device: str, gid: int) -> QuotaPartial:
    """See also: get_group_quota."""
    return _run_with_context(
        lambda: _quota_partial_from_tuple(_get_group_quota_partial_raw(device, gid)),
        device=device,
        quota_id=gid,
    )


def get_next_group_quota_partial(device: str, gid: int) -> NextQuotaPartial:
    return _run_with_context(
        lambda: _next_quota_partial_from_tuple(_get_next_group_quota_partial_raw(device, gid)),
        device=device,
        quota_id=gid,
    )


def get_group_quota_info_partial(device: str) -> QuotaInfoPartial:
    return _run_with_context(
        lambda: _quota_info_partial_from_tuple(_get_group_quota_info_partial_raw(device)),
        device=device,
    )


def get_project_quota_partial(device: str, projid: int) -> QuotaPartial:
    """See also: get_project_quota."""
    return _run_with_context(
        lambda: _quota_partial_from_tuple(_get_project_quota_partial_raw(device, projid)),
        device=device,
        quota_id=projid,
    )


def get_next_project_quota_partial(device: str, projid: int) -> NextQuotaPartial:
    return _run_with_context(
        lambda: _next_quota_partial_from_tuple(_get_next_project_quota_partial_raw(device, projid)),
        device=device,
        quota_id=projid,
    )


def get_project_quota_info_partial(device: str) -> QuotaInfoPartial:
    return _run_with_context(
        lambda: _quota_info_partial_from_tuple(_get_project_quota_info_partial_raw(device)),
        device=device,
    )


def _limits_from_quota(quota) -> tuple:
    """Extract (block_hard, block_soft, inode_hard, inode_soft) from Quota or 8-tuple. set_quota uses only these four."""
    if hasattr(quota, "block_hard_limit"):
        return (quota.block_hard_limit, quota.block_soft_limit, quota.inode_hard_limit, quota.inode_soft_limit)
    return (quota[0], quota[1], quota[3], quota[4])


def _validate_limits(
    block_hard_limit: int,
    block_soft_limit: int,
    inode_hard_limit: int,
    inode_soft_limit: int,
) -> None:
    """Raise ValueError if any limit is not an int or is negative."""
    for name, val in [
        ("block_hard_limit", block_hard_limit),
        ("block_soft_limit", block_soft_limit),
        ("inode_hard_limit", inode_hard_limit),
        ("inode_soft_limit", inode_soft_limit),
    ]:
        if not isinstance(val, int):
            raise TypeError(f"{name} must be int, got {type(val).__name__}")
        if val < 0:
            raise ValueError(f"{name} must be >= 0, got {val}")


def set_user_quota(
    device: str,
    uid: int,
    block_hard_limit: Optional[int] = None,
    block_soft_limit: Optional[int] = None,
    inode_hard_limit: Optional[int] = None,
    inode_soft_limit: Optional[int] = None,
    *,
    limits_from=None,
):
    """Set user quota limits. Pass the four limits, or limits_from=<Quota/8-tuple> to use the four limit fields from get_user_quota. Limits must be non-negative ints. QuotaPartial with None limits is not accepted.
    See also: get_user_quota."""
    if limits_from is not None:
        block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit = _limits_from_quota(limits_from)
    if block_hard_limit is None or block_soft_limit is None or inode_hard_limit is None or inode_soft_limit is None:
        raise TypeError(
            "set_user_quota() requires either four limit arguments or limits_from= (Quota/8-tuple with all four limits set)"
        )
    _validate_limits(block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit)
    return _run_with_context(
        lambda: _set_user_quota_raw(device, uid, block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit),
        device=device,
        quota_id=uid,
    )


def set_group_quota(
    device: str,
    gid: int,
    block_hard_limit: Optional[int] = None,
    block_soft_limit: Optional[int] = None,
    inode_hard_limit: Optional[int] = None,
    inode_soft_limit: Optional[int] = None,
    *,
    limits_from=None,
):
    """Set group quota limits. Pass the four limits or limits_from=; limits must be non-negative ints. See also: get_group_quota."""
    if limits_from is not None:
        block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit = _limits_from_quota(limits_from)
    if block_hard_limit is None or block_soft_limit is None or inode_hard_limit is None or inode_soft_limit is None:
        raise TypeError(
            "set_group_quota() requires either four limit arguments or limits_from= (Quota/8-tuple with all four limits set)"
        )
    _validate_limits(block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit)
    return _run_with_context(
        lambda: _set_group_quota_raw(device, gid, block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit),
        device=device,
        quota_id=gid,
    )


def set_project_quota(
    device: str,
    projid: int,
    block_hard_limit: Optional[int] = None,
    block_soft_limit: Optional[int] = None,
    inode_hard_limit: Optional[int] = None,
    inode_soft_limit: Optional[int] = None,
    *,
    limits_from=None,
):
    """Set project quota limits. Pass the four limits or limits_from=; limits must be non-negative ints. See also: get_project_quota."""
    if limits_from is not None:
        block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit = _limits_from_quota(limits_from)
    if block_hard_limit is None or block_soft_limit is None or inode_hard_limit is None or inode_soft_limit is None:
        raise TypeError(
            "set_project_quota() requires either four limit arguments or limits_from= (Quota/8-tuple with all four limits set)"
        )
    _validate_limits(block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit)
    return _run_with_context(
        lambda: _set_project_quota_raw(device, projid, block_hard_limit, block_soft_limit, inode_hard_limit, inode_soft_limit),
        device=device,
        quota_id=projid,
    )


# --- quota_on / quota_off / format / sync / set_info (wrapped for error context) ---


def user_quota_on(device: str, quota_format: int, quota_file: str) -> None:
    """Turn on user quotas. See also: user_quota_off, QuotaFormat."""
    _run_with_context(
        lambda: _user_quota_on_raw(device, quota_format, quota_file),
        device=device,
    )


def user_quota_off(device: str) -> None:
    """Turn off user quotas. See also: user_quota_on."""
    _run_with_context(lambda: _user_quota_off_raw(device), device=device)


def get_user_quota_format(device: str) -> int:
    """Get user quota format (QFMT_*). See also: QuotaFormat, user_quota_on."""
    return _run_with_context(lambda: _get_user_quota_format_raw(device), device=device)


def sync_user_quotas(device: Optional[str]) -> None:
    """Sync user quota usage to disk. device=None syncs all. See also: sync_group_quotas."""
    _run_with_context(lambda: _sync_user_quotas_raw(device), device=device)


def set_user_quota_info(device: str, block_grace: int, inode_grace: int, flags: int) -> None:
    """Set user quotafile info (grace periods, flags). See also: get_user_quota_info."""
    _run_with_context(
        lambda: _set_user_quota_info_raw(device, block_grace, inode_grace, flags),
        device=device,
    )


def group_quota_on(device: str, quota_format: int, quota_file: str) -> None:
    """Turn on group quotas. See also: group_quota_off, QuotaFormat."""
    _run_with_context(
        lambda: _group_quota_on_raw(device, quota_format, quota_file),
        device=device,
    )


def group_quota_off(device: str) -> None:
    """Turn off group quotas. See also: group_quota_on."""
    _run_with_context(lambda: _group_quota_off_raw(device), device=device)


def get_group_quota_format(device: str) -> int:
    """Get group quota format. See also: QuotaFormat."""
    return _run_with_context(lambda: _get_group_quota_format_raw(device), device=device)


def sync_group_quotas(device: Optional[str]) -> None:
    """Sync group quota usage to disk. device=None syncs all."""
    _run_with_context(lambda: _sync_group_quotas_raw(device), device=device)


def set_group_quota_info(device: str, block_grace: int, inode_grace: int, flags: int) -> None:
    """Set group quotafile info. See also: get_group_quota_info."""
    _run_with_context(
        lambda: _set_group_quota_info_raw(device, block_grace, inode_grace, flags),
        device=device,
    )


def project_quota_on(device: str, quota_format: int, quota_file: str) -> None:
    """Turn on project quotas. See also: project_quota_off, QuotaFormat."""
    _run_with_context(
        lambda: _project_quota_on_raw(device, quota_format, quota_file),
        device=device,
    )


def project_quota_off(device: str) -> None:
    """Turn off project quotas. See also: project_quota_on."""
    _run_with_context(lambda: _project_quota_off_raw(device), device=device)


def get_project_quota_format(device: str) -> int:
    """Get project quota format. See also: QuotaFormat."""
    return _run_with_context(lambda: _get_project_quota_format_raw(device), device=device)


def sync_project_quotas(device: Optional[str]) -> None:
    """Sync project quota usage to disk. device=None syncs all."""
    _run_with_context(lambda: _sync_project_quotas_raw(device), device=device)


def set_project_quota_info(device: str, block_grace: int, inode_grace: int, flags: int) -> None:
    """Set project quotafile info. See also: get_project_quota_info."""
    _run_with_context(
        lambda: _set_project_quota_info_raw(device, block_grace, inode_grace, flags),
        device=device,
    )


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
    "QuotaFormat",
    "QuotaInfo",
    "QuotaInfoPartial",
    "QuotaPartial",
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
    "iter_group_quotas",
    "iter_project_quotas",
    "iter_user_quotas",
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
