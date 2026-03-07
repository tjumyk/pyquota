PyQuota
=======

Python wrapper for the Linux **quotactl(2)** APIs.

Requirements
------------

- Linux with kernel quota support (CONFIG_QUOTA)
- Root or CAP_SYS_ADMIN
- Kernel >= 2.4.22; project quota >= 4.1; Q_GETNEXTQUOTA >= 4.6

Installation
------------

.. code-block:: bash

   pip install pyquota

Quick start
-----------

.. code-block:: python

   import pyquota as pq

   pq.user_quota_on("/dev/sda1", pq.QFMT_VFS_V0, "/aquota.user")
   q = pq.get_user_quota("/dev/sda1", 1000)
   print(q.block_hard_limit, q.block_current)

API Reference
-------------

.. toctree::
   :maxdepth: 2

   reference

Errors
------

All quotactl failures are raised as :exc:`pyquota.APIError` with messages matching the
`quotactl(2) ERRORS <https://man7.org/linux/man-pages/man2/quotactl.2.html#ERRORS>`_ section.
