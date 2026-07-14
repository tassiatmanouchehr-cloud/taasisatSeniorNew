# Public, Private & Sensitive Profile Model

## Profile Types
- Provider Profile
- Organization Profile
- Platform Profile
- Customer Private Profile
- Staff Private Profile

## Provider Public Profile Fields
- display name
- profile photo/media
- biography
- skills/capabilities
- experience summary
- service areas
- availability summary when allowed
- portfolio items
- rating aggregates from governance module
- completed service statistics from execution module
- verified badges

## Organization Public Profile Fields
- public name
- logo/media
- biography/description
- service areas
- team/provider count where allowed
- verification badges
- rating aggregates
- portfolio/public evidence

## Platform Public Profile Fields
- marketplace identity
- platform verification/status claims
- terms links
- public trust pages
- official support channels

## Private Profile Fields
- legal identity details
- internal contact details
- operational addresses
- staff notes
- onboarding state
- membership metadata

## Sensitive Profile Fields
- identity documents
- professional licenses
- financial identifiers
- precise private addresses
- private phone/email unless explicitly public
- risk/security flags
- verification reviewer notes

## Visibility Classes
- `public`: visible to anyone according to publication policy.
- `authenticated`: visible only after authentication.
- `same_tenant`: visible inside tenant boundaries.
- `role_based`: visible only to actors with specific permissions.
- `owner_only`: visible only to the actor or account owner.
- `restricted`: visible only through explicit critical permission.
- `hidden`: never publicly exposed.

## Protection Rules
1. Public profile publication never implies private field exposure.
2. Contact information is masked by default.
3. Document visibility is restricted to verification and authorized compliance flows.
4. Address visibility is purpose-bound and should be minimized.
5. Media publication requires media review policy where configured.
6. Profile statistics are derived from source modules and must not be manually editable except through correction workflows.
