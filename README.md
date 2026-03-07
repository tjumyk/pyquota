# PyQuota

PyQuota is a Python wrapper for the Linux [quotactl(2)](http://man7.org/linux/man-pages/man2/quotactl.2.html) APIs.

## Requirements

- **Linux** with quota support (kernel built with `CONFIG_QUOTA`)
- **Privilege**: root or `CAP_SYS_ADMIN` for quota operations
- **Kernel**: >= 2.4.22; project quota requires >= 4.1; `Q_GETNEXTQUOTA` requires >= 4.6

XFS-specific quotactl commands (e.g. `Q_XQUOTAON`) are not supported.

**Future work:** Linux 5.13+ adds `quotactl_fd()`, which uses a file descriptor instead of a device path (useful for filesystems without a block device, e.g. UBIFS). This wrapper does not yet support it.

### Breaking changes (current release)

- **`get_user_quota`**, **`get_next_user_quota`**, **`get_user_quota_info`** (and group/project) **always return named tuples** (`Quota`, `NextQuota`, `QuotaInfo`). The `return_type` parameter has been removed; results are tuple-compatible (indexing, unpacking).
- **`get_user_quota_named`** and other **`*_named`** functions are **removed**; use the corresponding `get_*`.
- **`get_user_quota_with_valid`** and other **`*_with_valid`** functions are **replaced by `get_*_quota_partial`** (and `get_*_quota_info_partial`), which return **named tuples only** (`QuotaPartial`, `NextQuotaPartial`, `QuotaInfoPartial`) with optional fields as `None` when not set.
- **`QFMT_VFS_OLD`**, **`QFMT_VFS_V0`**, **`QFMT_VFS_V1`** are **no longer exported**. Use **`QuotaFormat.VFS_OLD`**, **`QuotaFormat.VFS_V0`**, **`QuotaFormat.VFS_V1`** for `quota_on` and for comparing with `get_*_quota_format()` return value.
- **`DQF_ROOT_SQUASH`**, **`DQF_SYS_FILE`** are **no longer exported**. Use **`QuotaInfoFlags.ROOT_SQUASH`**, **`QuotaInfoFlags.SYS_FILE`** for `set_*_quota_info(..., flags=...)` (combine with `|`).
- **`EACCES`**, **`EPERM`**, and other errno constants are **no longer exported**. Use **`QuotaErrno.EACCES`**, **`QuotaErrno.EPERM`**, etc. for comparing with `APIError.errno`.

## Installation

```bash
pip install pyquota
```

From source (build deps: Python development headers, C compiler):

```bash
git clone https://github.com/tjumyk/pyquota.git && cd pyquota
pip install -e .
```

## Units

- **Block limits** (`block_hard_limit`, `block_soft_limit`): in **1024-byte** disk quota blocks ([quotactl(2)](http://man7.org/linux/man-pages/man2/quotactl.2.html))
- **Current block usage** (`block_current`): in **bytes**
- **Inode limits/current**: inodes (count)
- **Grace periods** (`block_grace`, `inode_grace` in `QuotaInfo`): in **seconds** before soft limit becomes hard
- **Time limits** (`block_time`, `inode_time` in `Quota`): **Unix timestamps** (seconds since epoch) when grace expires, or 0 if not over soft limit

## API overview

| quotactl command   | User quota                  | Group quota                  | Project quota                 |
|--------------------|-----------------------------|------------------------------|-------------------------------|
| Q_QUOTAON          | `user_quota_on`             | `group_quota_on`             | `project_quota_on`           |
| Q_QUOTAOFF         | `user_quota_off`            | `group_quota_off`            | `project_quota_off`           |
| Q_GETQUOTA         | `get_user_quota`           | `get_group_quota`            | `get_project_quota`           |
| Q_GETNEXTQUOTA     | `get_next_user_quota`      | `get_next_group_quota`       | `get_next_project_quota`      |
| Q_SETQUOTA         | `set_user_quota`           | `set_group_quota`            | `set_project_quota`          |
| Q_GETINFO          | `get_user_quota_info`      | `get_group_quota_info`       | `get_project_quota_info`      |
| Q_SETINFO          | `set_user_quota_info`      | `set_group_quota_info`      | `set_project_quota_info`      |
| Q_GETFMT           | `get_user_quota_format`    | `get_group_quota_format`    | `get_project_quota_format`    |
| Q_SYNC             | `sync_user_quotas`         | `sync_group_quotas`         | `sync_project_quotas`         |

**Return type:** `get_*_quota`, `get_next_*_quota`, and `get_*_quota_info` return **named tuples** (`Quota`, `NextQuota`, `QuotaInfo`), which are tuple-compatible (indexing and unpacking work). `QuotaInfo` has **`.root_squash`** and **`.sys_file`** properties; use **`QuotaInfoFlags`** (IntEnum: `ROOT_SQUASH`, `SYS_FILE`) for `set_*_quota_info(..., flags=...)` (combine with `|`). **`iter_user_quotas(device, start_uid=0)`** (and `iter_group_quotas`, `iter_project_quotas`) yield `NextQuota` for each ID with quota; they use `get_next_*` under the hood, so `get_next_*` remains the primitive for a single "next" query. **`QuotaFormat`** (IntEnum: `VFS_OLD`, `VFS_V0`, `VFS_V1`) can be used for `quota_on` / format checks. **Errors** raised from the public API have **`.device`** and **`.id`** set when applicable. **`set_*_quota`** validates that limits are non-negative ints.

**Partial validity:** When the kernel may return incomplete data, use **`get_*_quota_partial`** or **`get_*_quota_info_partial`**. They return **named tuples** (`QuotaPartial`, etc.) where **fields the kernel did not set are `None`** (interpreted from the kernel’s valid mask per man 2 quotactl). Use e.g. `if q.block_hard_limit is not None:`. According to the man page, the kernel *currently* always fills all fields and sets the valid mask to QIF_ALL/IIF_ALL on get; the valid mask is used on *set* to indicate which fields the caller provides. The partial API exists for forward compatibility if a kernel ever returns incomplete data.

## Usage

```python
import pyquota as pq

# Turn on user quota for a filesystem (QuotaFormat)
pq.user_quota_on("/dev/sda1", pq.QuotaFormat.VFS_V0, "/aquota.user")

# Turn off user quota
pq.user_quota_off("/dev/sda1")

# Get quota (returns Quota named tuple; tuple-compatible)
quota = pq.get_user_quota("/dev/sda1", 1000)
print(quota.block_hard_limit, quota.block_current)

# Get next user with quota (kernel >= 4.6), or iterate all
next_quota = pq.get_next_user_quota("/dev/sda1", 1000)  # next_quota.id is the uid
for nq in pq.iter_user_quotas("/dev/sda1"):
    print(nq.id, nq.block_current)

# Set user quota (hard 100MB, soft 90MB, no inode limits)
pq.set_user_quota("/dev/sda1", 1000, 102400, 92160, 0, 0)

# Or take the four limit fields from a Quota (e.g. from get_user_quota)
q = pq.get_user_quota("/dev/sda1", 1000)
pq.set_user_quota("/dev/sda1", 1000, limits_from=q)

# Quotafile info (tuple-like; .root_squash and .sys_file for flags)
info = pq.get_user_quota_info("/dev/sda1")
print(info.block_grace, info.inode_grace)
print(info.root_squash, info.sys_file)

pq.set_user_quota_info("/dev/sda1", 604800, 604800, 0)  # 1 week grace, no flags

# Format: compare with QuotaFormat.VFS_OLD, .VFS_V0, .VFS_V1
fmt = pq.get_user_quota_format("/dev/sda1")

# Sync quota usage to disk
pq.sync_user_quotas("/dev/sda1")
pq.sync_user_quotas(None)  # all filesystems with active user quotas
```

Replace `user` with `group` or `project` for group/project quotas. Project quota requires kernel >= 4.1.

## Error handling

Errors from the C API are raised as **`pyquota.APIError`** (or a subclass) with messages matching the [quotactl(2) ERRORS](http://man7.org/linux/man-pages/man2/quotactl.2.html#ERRORS) section. Each instance has an **`errno`** attribute; compare with **`QuotaErrno`** (IntEnum: `EACCES`, `EPERM`, `ENOENT`, etc.). When raised from the public API (get/set/iter, quota_on/off, etc.), **`device`** and **`id`** are set when applicable. Subclasses: **PermissionError** (EPERM), **NotFoundError** (ENOENT, ESRCH), **InvalidError** (EINVAL, etc.); catch `pq.APIError` or use `e.errno`.

```python
import pyquota as pq

try:
    pq.get_user_quota("/dev/sda1", 1000)
except pq.PermissionError:
    print("Need root or CAP_SYS_ADMIN")
except pq.NotFoundError as e:
    print("Not found:", e)
except pq.APIError as e:
    print(e, "errno:", e.errno)
    if e.errno == pq.QuotaErrno.EPERM:
        print("Permission denied")
```

Invalid arguments (e.g. empty device path, negative ID, non-int or negative limits in `set_*_quota`) raise `ValueError` or `TypeError` before calling the kernel.

## Reference

See the [man page](http://man7.org/linux/man-pages/man2/quotactl.2.html) for detailed semantics of each command. Type stubs (`.pyi`) are provided for IDE completion and type checkers. API documentation is built with Sphinx and published at [https://tjumyk.github.io/pyquota/](https://tjumyk.github.io/pyquota/) when available.
