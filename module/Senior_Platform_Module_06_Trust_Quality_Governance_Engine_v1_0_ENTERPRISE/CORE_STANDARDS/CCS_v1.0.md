# Core Configuration Specification — CCS v1.0

All module configuration must support:
- Versioning
- Scope
- Override
- Effective date
- Expiration
- Rollback
- Approval workflow
- Validation
- Audit

Resolution order:
Explicit Override
→ Booking
→ Trust Case
→ User
→ Role
→ Branch
→ Region
→ Service Type
→ Service Category
→ Department
→ Organization
→ Platform
→ Global Default
