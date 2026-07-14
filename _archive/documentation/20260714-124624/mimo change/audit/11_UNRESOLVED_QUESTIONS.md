# UNRESOLVED QUESTIONS

---

## Architecture Questions

1. **Should TenantAwareModel.tenant_id be changed to a ForeignKey?**
   - Current: UUIDField (no referential integrity)
   - Pro: Avoids circular dependency
   - Con: No CASCADE/PROTECT, no DB-level validation
   - Status: OPEN

2. **Should RBAC enforcement toggle be removed in production?**
   - Current: Configurable per-tenant
   - Pro: Useful for development/migration
   - Con: Security risk if misconfigured
   - Status: OPEN

3. **Should the ownership_authorized_by bypass be removed?**
   - Current: Caller-verified bypass
   - Pro: Simplifies customer-initiated flows
   - Con: Security depends on caller correctness
   - Status: OPEN

4. **Should tenant isolation be enforced via middleware?**
   - Current: Developer discipline
   - Pro: Prevents cross-tenant leaks
   - Con: Performance overhead, architectural change
   - Status: OPEN

## Implementation Questions

5. **Is the seed test race condition fixable without changing order number format?**
   - Current: Random 4-digit suffix
   - Option A: Use UUID or database sequence
   - Option B: Add retry logic
   - Status: OPEN

6. **Should the legacy wallet in finance be removed?**
   - Current: Superseded by apps.wallet
   - Pro: Reduces confusion
   - Con: May have hidden dependencies
   - Status: OPEN

7. **Should the common app have dedicated tests?**
   - Current: Zero tests
   - Pro: Regression protection for shared code
   - Con: Low risk (abstract models, enums, managers)
   - Status: OPEN

## Product Questions

8. **Should the showcase app be included in production?**
   - Current: UI component demos at /ui/
   - Pro: Useful for design review
   - Con: No business value, attack surface
   - Status: OPEN

9. **Should deadline expiry be enabled by default?**
   - Current: Disabled by default
   - Pro: Enables real deadline behavior
   - Con: May cause unexpected order reopenings
   - Status: OPEN

10. **Should pre-service payment be enabled by default?**
    - Current: Disabled by default
    - Pro: Enables escrow protection
    - Con: Changes financial flow significantly
    - Status: OPEN
