API Reference
============

This page documents the public Python API. The C extension (``pyquota._native``) is not
documented here; use the man page for low-level semantics.

Module contents
---------------

.. automodule:: pyquota
   :members:
   :undoc-members:
   :exclude-members: _quota_from_tuple, _next_quota_from_tuple, _quota_info_from_tuple, _quota_partial_from_tuple, _next_quota_partial_from_tuple, _quota_info_partial_from_tuple, _limits_from_quota

Named types
-----------

- **Quota**: ``block_hard_limit``, ``block_soft_limit``, ``block_current`` (bytes), inode fields, ``block_time``, ``inode_time``. Block limits in 1024-byte blocks. Returned by ``get_*_quota(..., return_type="named")`` (default).
- **NextQuota**: same as Quota plus ``id`` (uid/gid/projid). Returned by ``get_next_*_quota(..., return_type="named")``.
- **QuotaInfo**: ``block_grace``, ``inode_grace`` (seconds), ``flags`` (DQF_*). Returned by ``get_*_quota_info(..., return_type="named")``.
- **QuotaPartial**, **NextQuotaPartial**, **QuotaInfoPartial**: same fields as above but with ``Optional[int]``; fields the kernel did not set are ``None``. Returned by ``get_*_quota_partial`` and ``get_*_quota_info_partial``.

Constants
---------

- **QFMT_VFS_OLD**, **QFMT_VFS_V0**, **QFMT_VFS_V1**: quota format for quota_on / get_*_quota_format.
- **DQF_ROOT_SQUASH**, **DQF_SYS_FILE**: flags from get_*_quota_info.
- **EACCES**, **EPERM**, etc.: errno constants for ``APIError.errno``.

Exceptions
----------

.. autoexception:: pyquota.APIError

   Base for quotactl failures. See quotactl(2) ERRORS. Subclasses:

   - **PermissionError** (EPERM)
   - **NotFoundError** (ENOENT, ESRCH)
   - **InvalidError** (EINVAL, ERANGE, EFAULT, etc.)

   All have an ``errno`` attribute.
