"""Stubs for pyquota: Linux quotactl(2) Python API."""

from typing import Literal, NamedTuple, Optional, Tuple, Union, overload

class APIError(Exception):
    """Base for quotactl failures. See quotactl(2) ERRORS."""

    errno: int


class PermissionError(APIError):
    """Raised when caller lacks CAP_SYS_ADMIN (EPERM)."""


class NotFoundError(APIError):
    """Raised when device/file/quota not found (ENOENT, ESRCH)."""


class InvalidError(APIError):
    """Raised for invalid args or state (EINVAL, ERANGE, EFAULT, etc.)."""


class Quota(NamedTuple):
    """Disk quota limits and current usage. Block limits in 1024-byte blocks; block_current in bytes.
    block_time, inode_time: Unix timestamps when grace expires, or 0."""

    block_hard_limit: int
    block_soft_limit: int
    block_current: int
    inode_hard_limit: int
    inode_soft_limit: int
    inode_current: int
    block_time: int
    inode_time: int


class NextQuota(NamedTuple):
    """Quota for next ID with active quota; includes id (uid/gid/projid)."""

    block_hard_limit: int
    block_soft_limit: int
    block_current: int
    inode_hard_limit: int
    inode_soft_limit: int
    inode_current: int
    block_time: int
    inode_time: int
    id: int


class QuotaInfo(NamedTuple):
    """Quotafile info: grace periods (seconds) and flags (DQF_*)."""

    block_grace: int
    inode_grace: int
    flags: int


class QuotaPartial(NamedTuple):
    """Quota from get_*_quota_partial. Fields are None when kernel did not supply them (see man 2 quotactl dqb_valid)."""

    block_hard_limit: Optional[int]
    block_soft_limit: Optional[int]
    block_current: Optional[int]
    inode_hard_limit: Optional[int]
    inode_soft_limit: Optional[int]
    inode_current: Optional[int]
    block_time: Optional[int]
    inode_time: Optional[int]


class NextQuotaPartial(NamedTuple):
    """Next quota from get_next_*_quota_partial. Quota fields are None when not set; id is always set."""

    block_hard_limit: Optional[int]
    block_soft_limit: Optional[int]
    block_current: Optional[int]
    inode_hard_limit: Optional[int]
    inode_soft_limit: Optional[int]
    inode_current: Optional[int]
    block_time: Optional[int]
    inode_time: Optional[int]
    id: int


class QuotaInfoPartial(NamedTuple):
    """Quotafile info from get_*_quota_info_partial. Fields are None when not set (dqi_valid)."""

    block_grace: Optional[int]
    inode_grace: Optional[int]
    flags: Optional[int]

# errno constants (for APIError.errno); see quotactl(2) ERRORS
EACCES: int
EBUSY: int
EFAULT: int
EINVAL: int
ENOENT: int
ENOSYS: int
ENOTBLK: int
EPERM: int
ERANGE: int
ESRCH: int

# Quota format constants (for quota_on, get_*_quota_format)
QFMT_VFS_OLD: int
QFMT_VFS_V0: int
QFMT_VFS_V1: int

# Quota info flags (get_*_quota_info result flags)
DQF_ROOT_SQUASH: int
DQF_SYS_FILE: int

# User quota
def user_quota_on(device: str, quota_format: int, quota_file: str) -> None: ...
def user_quota_off(device: str) -> None: ...
def get_user_quota(device: str, uid: int, return_type: Literal["named", "tuple"] = "named") -> Union[Quota, Tuple[int, int, int, int, int, int, int, int]]: ...
def get_user_quota_partial(device: str, uid: int) -> QuotaPartial: ...
def get_next_user_quota(device: str, uid: int, return_type: Literal["named", "tuple"] = "named") -> Union[NextQuota, Tuple[int, int, int, int, int, int, int, int, int]]: ...
def get_next_user_quota_partial(device: str, uid: int) -> NextQuotaPartial: ...
@overload
def set_user_quota(
    device: str,
    uid: int,
    block_hard_limit: int,
    block_soft_limit: int,
    inode_hard_limit: int,
    inode_soft_limit: int,
) -> None: ...
@overload
def set_user_quota(device: str, uid: int, *, quota: Union[Quota, Tuple[int, ...]]) -> None: ...
def set_user_quota(device: str, uid: int, block_hard_limit: int = ..., block_soft_limit: int = ..., inode_hard_limit: int = ..., inode_soft_limit: int = ..., *, quota: Optional[Union[Quota, Tuple[int, ...]]] = None) -> None: ...
def get_user_quota_info(device: str, return_type: Literal["named", "tuple"] = "named") -> Union[QuotaInfo, Tuple[int, int, int]]: ...
def get_user_quota_info_partial(device: str) -> QuotaInfoPartial: ...
def set_user_quota_info(device: str, block_grace: int, inode_grace: int, flags: int) -> None: ...
def get_user_quota_format(device: str) -> int: ...
def sync_user_quotas(device: Optional[str]) -> None: ...

# Group quota
def group_quota_on(device: str, quota_format: int, quota_file: str) -> None: ...
def group_quota_off(device: str) -> None: ...
def get_group_quota(device: str, gid: int, return_type: Literal["named", "tuple"] = "named") -> Union[Quota, Tuple[int, int, int, int, int, int, int, int]]: ...
def get_group_quota_partial(device: str, gid: int) -> QuotaPartial: ...
def get_next_group_quota(device: str, gid: int, return_type: Literal["named", "tuple"] = "named") -> Union[NextQuota, Tuple[int, int, int, int, int, int, int, int, int]]: ...
def get_next_group_quota_partial(device: str, gid: int) -> NextQuotaPartial: ...
@overload
def set_group_quota(
    device: str,
    gid: int,
    block_hard_limit: int,
    block_soft_limit: int,
    inode_hard_limit: int,
    inode_soft_limit: int,
) -> None: ...
@overload
def set_group_quota(device: str, gid: int, *, quota: Union[Quota, Tuple[int, ...]]) -> None: ...
def set_group_quota(device: str, gid: int, block_hard_limit: int = ..., block_soft_limit: int = ..., inode_hard_limit: int = ..., inode_soft_limit: int = ..., *, quota: Optional[Union[Quota, Tuple[int, ...]]] = None) -> None: ...
def get_group_quota_info(device: str, return_type: Literal["named", "tuple"] = "named") -> Union[QuotaInfo, Tuple[int, int, int]]: ...
def get_group_quota_info_partial(device: str) -> QuotaInfoPartial: ...
def set_group_quota_info(device: str, block_grace: int, inode_grace: int, flags: int) -> None: ...
def get_group_quota_format(device: str) -> int: ...
def sync_group_quotas(device: Optional[str]) -> None: ...

# Project quota (kernel >= 4.1)
def project_quota_on(device: str, quota_format: int, quota_file: str) -> None: ...
def project_quota_off(device: str) -> None: ...
def get_project_quota(device: str, projid: int, return_type: Literal["named", "tuple"] = "named") -> Union[Quota, Tuple[int, int, int, int, int, int, int, int]]: ...
def get_project_quota_partial(device: str, projid: int) -> QuotaPartial: ...
def get_next_project_quota(device: str, projid: int, return_type: Literal["named", "tuple"] = "named") -> Union[NextQuota, Tuple[int, int, int, int, int, int, int, int, int]]: ...
def get_next_project_quota_partial(device: str, projid: int) -> NextQuotaPartial: ...
@overload
def set_project_quota(
    device: str,
    projid: int,
    block_hard_limit: int,
    block_soft_limit: int,
    inode_hard_limit: int,
    inode_soft_limit: int,
) -> None: ...
@overload
def set_project_quota(device: str, projid: int, *, quota: Union[Quota, Tuple[int, ...]]) -> None: ...
def set_project_quota(device: str, projid: int, block_hard_limit: int = ..., block_soft_limit: int = ..., inode_hard_limit: int = ..., inode_soft_limit: int = ..., *, quota: Optional[Union[Quota, Tuple[int, ...]]] = None) -> None: ...
def get_project_quota_info(device: str, return_type: Literal["named", "tuple"] = "named") -> Union[QuotaInfo, Tuple[int, int, int]]: ...
def get_project_quota_info_partial(device: str) -> QuotaInfoPartial: ...
def set_project_quota_info(device: str, block_grace: int, inode_grace: int, flags: int) -> None: ...
def get_project_quota_format(device: str) -> int: ...
def sync_project_quotas(device: Optional[str]) -> None: ...
