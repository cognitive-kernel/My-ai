# Security Policy

## Reporting

Do not disclose credentials, tokens, private repository contents, or exploitable details in public issues.
For a suspected security vulnerability, provide a minimal reproduction, affected component, impact, and the first known version/commit to the project maintainers through a private channel.

## Security boundaries

My-AI treats authentication, tool permissions, file confinement, code execution, external security analysis, backups, self-repair and self-update as security-sensitive surfaces.
Self-update is deny-by-default. A diagnostic result or generated patch is not authorization to activate it.

## Supported versions

Security fixes should target the current `main` branch unless a maintained release policy is explicitly established.