# PyQuota

PyQuota is a Python wrapper for the Linux [quotactl(2)](http://man7.org/linux/man-pages/man2/quotactl.2.html) APIs.

## Requirements

- **Linux** with quota support (kernel built with `CONFIG_QUOTA`)
- **Privilege**: root or `CAP_SYS_ADMIN` for quota operations
- **Kernel**: >= 2.4.22; project quota requires >= 4.1; `Q_GETNEXTQUOTA` requires >= 4.6

XFS-specific quotactl commands (e.g. `Q_XQUOTAON`) are not supported.

**Future work:** Linux 5.13+ adds `quotactl_fd()`, which uses a file descriptor instead of a device path (useful for filesystems without a block device, e.g. UBIFS). This wrapper does not yet support it.

### Breaking changes (current release)

- **`get_user_quota`**, **`get_next_user_quota`**, **`get_user_quota_info`** (and group/project) now take an optional **`return_type`** and **default to named tuples**. Use `return_type="tuple"` to get the raw tuple (e.g. `pq.get_user_quota(device, uid, return_type="tuple")`).
- **`get_user_quota_named`** and other **`*_named`** functions are **removed**; use the corresponding `get_*` with default `return_type="named"`.
- **`get_user_quota_with_valid`** and other **`*_with_valid`** functions are **replaced by `get_*_quota_partial`** (and `get_*_quota_info_partial`), which return **named tuples only** (`QuotaPartial`, `NextQuotaPartial`, `QuotaInfoPartial`) with optional fields as `None` when not set.

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

**Return type:** `get_*_quota`, `get_next_*_quota`, and `get_*_quota_info` accept an optional **`return_type`** (`"named"` | `"tuple"`). Default is **`"named"`**, returning `Quota`, `NextQuota`, or `QuotaInfo`. Use `return_type="tuple"` for the raw tuple.

**Partial validity:** When the kernel may return incomplete data, use **`get_*_quota_partial`** or **`get_*_quota_info_partial`**. They return **named tuples** (`QuotaPartial`, etc.) where **fields the kernel did not set are `None`** (interpreted from the kernel’s valid mask per man 2 quotactl). Use e.g. `if q.block_hard_limit is not None:`. According to the man page, the kernel *currently* always fills all fields and sets the valid mask to QIF_ALL/IIF_ALL on get; the valid mask is used on *set* to indicate which fields the caller provides. The partial API exists for forward compatibility if a kernel ever returns incomplete data.

## Usage

```python
import pyquota as pq

# Turn on user quota for a filesystem
pq.user_quota_on("/dev/sda1", pq.QFMT_VFS_V0, "/aquota.user")

# Turn off user quota
pq.user_quota_off("/dev/sda1")

# Get quota (default: named tuple Quota)
quota = pq.get_user_quota("/dev/sda1", 1000)
print(quota.block_hard_limit, quota.block_current)

# Raw tuple: use return_type="tuple"
raw = pq.get_user_quota("/dev/sda1", 1000, return_type="tuple")

# Get next user with quota (kernel >= 4.6)
next_quota = pq.get_next_user_quota("/dev/sda1", 1000)  # next_quota.id is the uid

# Set user quota (hard 100MB, soft 90MB, no inode limits)
pq.set_user_quota("/dev/sda1", 1000, 102400, 92160, 0, 0)

# Or pass the result of get_user_quota (only the four limit fields are applied)
q = pq.get_user_quota("/dev/sda1", 1000)
pq.set_user_quota("/dev/sda1", 1000, quota=q)

# Quotafile info (grace periods in seconds, flags)
info = pq.get_user_quota_info("/dev/sda1")
print(info.block_grace, info.inode_grace)
print(bool(info.flags & pq.DQF_ROOT_SQUASH), bool(info.flags & pq.DQF_SYS_FILE))

pq.set_user_quota_info("/dev/sda1", 604800, 604800, 0)  # 1 week grace, no flags

# Format: QFMT_VFS_OLD, QFMT_VFS_V0, or QFMT_VFS_V1
fmt = pq.get_user_quota_format("/dev/sda1")

# Sync quota usage to disk
pq.sync_user_quotas("/dev/sda1")
pq.sync_user_quotas(None)  # all filesystems with active user quotas
```

Replace `user` with `group` or `project` for group/project quotas. Project quota requires kernel >= 4.1.

## Error handling

Errors from the C API are raised as **`pyquota.APIError`** (or a subclass) with messages matching the [quotactl(2) ERRORS](http://man7.org/linux/man-pages/man2/quotactl.2.html#ERRORS) section. Each instance has an `errno` attribute. Subclasses: **PermissionError** (EPERM), **NotFoundError** (ENOENT, ESRCH), **InvalidError** (EINVAL, etc.); catch `pq.APIError` or use `e.errno`.

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
```

Invalid arguments (e.g. empty device path, negative ID) raise `ValueError` before calling the kernel.

## Reference

See the [man page](http://man7.org/linux/man-pages/man2/quotactl.2.html) for detailed semantics of each command. Type stubs (`.pyi`) are provided for IDE completion and type checkers. API documentation is built with Sphinx and published at [https://tjumyk.github.io/pyquota/](https://tjumyk.github.io/pyquota/) when available.
