# Privacy Classification Standard

## Classes
- public: safe for public documentation.
- internal: safe inside tenant/platform operations.
- restricted: limited access; business sensitive.
- sensitive: personal, financial, security, or regulated data.

## Rules
- Events and API responses must declare privacy class.
- Sensitive payloads must use minimization.
- Logs must not include secrets or sensitive raw payloads.
- Analytics projections must classify derived data.
