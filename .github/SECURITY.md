# Security Policy

## Supported versions

Only the latest release is supported with security updates.

| Version | Supported |
|---------|-----------|
| latest  | Yes       |
| < latest | No       |

## Reporting a vulnerability

This project handles sensitive credentials (GitHub App private keys and tokens). We take security seriously.

**Do NOT open a public issue for security vulnerabilities.**

Instead, please report vulnerabilities via [GitHub Security Advisories](https://github.com/quiquetech/github-token/security/advisories/new) or email the maintainers directly.

When reporting, please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We aim to acknowledge reports within **48 hours** and provide a fix within **7 days** for critical issues.

## Security considerations

- The Docker image runs as `nobody` (non-root) by default.
- Private keys should be mounted read-only via volume mounts, never baked into images.
- Generated tokens are short-lived (1 hour max, as enforced by GitHub).
- No secrets are logged or written to disk unless explicitly configured via `GITHUB_TOKEN_OUTPUT=file:...`.
