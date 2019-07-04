# PyQuota

PyQuota is a simple python wrapper for C apis of [quotactl](http://man7.org/linux/man-pages/man2/quotactl.2.html).

Supported kernel versions: `>=2.4.22, <5`.

Supported commands in C APIs:

- `Q_QUOTAON`
- `Q_QUOTAOFF`
- `Q_GETQUOTA`
- `Q_GETNEXTQUOTA` (requires kernel >= 4.6)
- `Q_SETQUOTA`
- `Q_GETINFO`
- `Q_SETINFO`
- `Q_GETFMT`
- `Q_SYNC`

Currently, none of the commands for XFS filesystem, e.g. `Q_XQUOTAON`, are supported due to lack of documentations and testing environments.

## Installation

```bash
pip install pyquota
```

## Usage 

For each of the supported commands, as listed above, this package provides 3 Python methods, which corresponds to operations on user quotas, group quotas and project quotas. Project quota methods requires kernel >=4.1.

For illustration purpose, only examples of user quota methods are provided here. To use group/project quota methods, you only need to replace 'user' in the method names with 'group' or 'project'.

```python
# Import package
import pyquota as pq

# Turn on user quota for a filesystem
pq.user_quota_on("/dev/sda1", pq.QFMT_VFS_V0, "/aquota.user")  # device path, quota format, quota file path 
# quota format can be either pq.QFMT_VFS_OLD, pq.QFMT_VFS_V0 or pq.QFMT_VFS_V1.

# Turn off user quota for a filesystem
pq.user_quota_off("/dev/sda1")

# Get quota of a user on a filesystem
quota = pq.get_user_quota("/dev/sda1", 1000) # 1000 is the uid, returns a tuple of 8 integers
block_hard_limit = quota[0] # unit: disk quota block (1024 Bytes)
block_soft_limit = quota[1] # unit: disk quota block (1024 Bytes)
block_current = quota[2] # unit: block (1 Byte)
inode_hard_limit = quota[3]
inode_soft_limit = quota[4]
inode_current = quota[5]
block_time = quota[6] # time limit for excessive disk use
inode_time = quota[7] # time limit for excessive files

# Get quota of the next user, whose ID is greater than or equal to the specified ID, on a filesystem
quota = pq.get_next_user_quota("/dev/sda1", 1000) # returns a tuple of 9 integers. 
# The first 8 integers are the same as the result of pg.get_user_quota while the last integer is the user id. 
uid = quota[8]

# Set quota of a user on a filesystem
pq.set_user_quota("/dev/sda1", 1000, 102400, 92160, 0, 0) # hard block limit 100MB, soft block limit 90MB, no inode limits 

# Get information about the user quotafile for a filesystem
info = pq.get_user_quota_info("/dev/sda1") # returns a tuple of 3 integers
block_grace = info[0] # time before block soft limit becomes hard limit. (unit: second)
inode_grace = info[1] # time before inode soft limit becomes hard limit. (unit: second)
flags = info[2] # flags for quotafile
is_root_squash_enabled = bool(flags & pq.DQF_ROOT_SQUASH)
is_stored_in_system_file = bool(flags & pq.DQF_SYS_FILE)

# Set information about the user quotafile for a filesystem
pq.set_user_quota_info("/dev/sda1", 604800, 604800, 0) # set both block grace and inode grace to 1 week (7*24*60*60), set flags as empty 

# Get quota format used for user quotas on a filesystem
fmt = pq.get_user_quota_format("/dev/sda1") # returns an integer 
# fmt should be either pq.QFMT_VFS_OLD, pq.QFMT_VFS_V0 or pq.QFMT_VFS_V1

# Update the on-disk copy of user quota usages for a filesystem
pq.sync_user_quotas("/dev/sda1")

# Update the on-disk copy of user quota usages for all filesystems with active quotas
pq.sync_user_quotas(None)
```

Since this package is only a wrapper for the C APIs, it almost keeps the original flavor and input/output formats. Thus, if you want more details about the what each of these commands do, meaning of the arguments and meaning of the returned values, please read the [man page](http://man7.org/linux/man-pages/man2/quotactl.2.html). 

## Error Messages

Any internal error that comes from the C apis is translated to a `pyquota.APIError` instance with a text description according to the [ERRORS section in the man page](http://man7.org/linux/man-pages/man2/quotactl.2.html#ERRORS).
  