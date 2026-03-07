# Security

## Privilege requirements

PyQuota wraps the Linux `quotactl(2)` system call. Quota operations require **root** or the **CAP_SYS_ADMIN** capability. Do not run untrusted code with these privileges. This library does not enforce or reduce privilege; it merely exposes the kernel API.

## Reporting vulnerabilities

If you believe you have found a security issue, please report it privately:

- **GitHub**: use [Security Advisories](https://github.com/tjumyk/pyquota/security/advisories/new) (if available) or contact the maintainers via the repository.
- Do not open a public issue for security-sensitive bugs.

We will acknowledge the report and work on a fix. Public disclosure will follow after a patch is available, coordinated with the reporter when possible.
