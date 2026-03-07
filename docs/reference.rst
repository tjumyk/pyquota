API Reference
============

This page documents the public Python API. The C extension (``pyquota._native``) is not
documented here; use the man page for low-level semantics.

Module contents
---------------

.. automodule:: pyquota
   :members:
   :undoc-members:
   :exclude-members: _quota_from_tuple, _next_quota_from_tuple, _quota_info_from_tuple, _quota_partial_from_tuple, _next_quota_partial_from_tuple, _quota_info_partial_from_tuple, _limits_from_quota, _run_with_context, _validate_limits

Named types
-----------

- **Quota**: ``block_hard_limit``, ``block_soft_limit``, ``block_current`` (bytes), inode fields, ``block_time``, ``inode_time``. Block limits in 1024-byte blocks. Returned by ``get_*_quota`` (tuple-compatible).
- **NextQuota**: same as Quota plus ``id`` (uid/gid/projid). Returned by ``get_next_*_quota`` and yielded by ``iter_*_quotas`` (tuple-compatible).
- **QuotaInfo**: ``block_grace``, ``inode_grace`` (seconds), ``flags`` (DQF_*). Returned by ``get_*_quota_info`` (tuple-compatible). Properties **``.root_squash``** and **``.sys_file``** for DQF_* flags.
- **QuotaPartial**, **NextQuotaPartial**, **QuotaInfoPartial**: same fields as above but with ``Optional[int]``; fields the kernel did not set are ``None``. Returned by ``get_*_quota_partial`` and ``get_*_quota_info_partial``.

Enums and constants
-------------------

- **QuotaFormat** (IntEnum): ``VFS_OLD``, ``VFS_V0``, ``VFS_V1`` for ``quota_on`` / ``get_*_quota_format``.
- **QFMT_VFS_OLD**, **QFMT_VFS_V0**, **QFMT_VFS_V1**: same as QuotaFormat members (int).
- **DQF_ROOT_SQUASH**, **DQF_SYS_FILE**: flags from get_*_quota_info (or use ``QuotaInfo.root_squash`` / ``.sys_file``).
- **EACCES**, **EPERM**, etc.: errno constants for ``APIError.errno``.

Exceptions
----------

.. autoexception:: pyquota.APIError

   Base for quotactl failures. See quotactl(2) ERRORS. When raised from the public API, **``.device``** and **``.id``** are set when applicable. Subclasses:

   - **PermissionError** (EPERM)
   - **NotFoundError** (ENOENT, ESRCH)
   - **InvalidError** (EINVAL, ERANGE, EFAULT, etc.)

   All have an ``errno`` attribute.
