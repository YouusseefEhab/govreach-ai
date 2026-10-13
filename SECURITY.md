# Security guidance

GovReach AI is a local graduation-project prototype. Authentication and roles
are not implemented. Do not expose the current API publicly with real data or
unrestricted paid generation access.

Keep keys and credentials in local `.env` or a deployment secret manager. Only
development placeholders belong in `.env.example`. Browser environment values
are public; never put a Gemini key in a `VITE_*` value.

Revoke or rotate exposed credentials first. Removing them in a later commit does
not remove Git history. Keep credentials and private campaign data out of public
issues, screenshots, logs, and evaluation captures.

Use private vulnerability reporting if enabled, or contact the maintainer
privately. Provide reproduction steps without sharing live credentials.
No security certification is claimed for this prototype.
