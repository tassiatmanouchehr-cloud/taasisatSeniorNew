# Permission Boundary Standard

## Permission Naming
`module.resource.action.scope`

Examples:
- module25.contract.read.platform
- module25.contract.publish.platform
- module25.dependency.validate.platform
- module25.freeze.publish.platform

## Permission Rules
- Permissions must be explicit and auditable.
- Role names are not security boundaries; permissions are.
- System actions require service actor identity.
- Impersonation must be visible in audit records.
- Cross-tenant permissions require elevated platform scope.
