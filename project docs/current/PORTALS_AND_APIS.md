# PORTALS, APIS, AND ENTRY POINTS

**Last verified HEAD:** phase3-company-public-directory (from main @ 9929da5, PR #13 merged — Sprint 3.2 CLOSED; Sprint 3.3 implemented, PR open)
**Last verified date:** 2026-07-16

---

## URL Routing

Root URL config: `config/urls.py`

| URL Prefix | App | Auth Required |
|------------|-----|---------------|
| `/` | public_site | No |
| `/accounts/` | accounts | Partial |
| `/admin/` | Django admin | Yes (staff) |
| `/admin-portal/` | admin_portal | Yes (admin permission) |
| `/api/v1/` | api | Yes (permission-based) |
| `/organization/` | organization_portal | Yes (org membership) |
| `/portal/` | portal | Yes (customer) |
| `/provider/` | provider_portal | Yes (provider) |
| `/ui/` | showcase | No |

## Customer Portal (30+ views)

Dashboard, profile, care recipients (CRUD), requests (list/detail/financial), share links, wizard (7-step order creation), notifications.

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_customer_profile()`

## Provider Portal (37 views)

Dashboard (assignments/visits/notifications — pre-existing; work summary, financial overview, wallet movements, invoice summary, reviews/reputation, professional statistics — Sprint 2.5), assignments (list/detail/confirm/decline), visits (start/complete), availability (working windows — add/edit/toggle-active/remove; blocked periods — add/remove; public-summary preview — Phase 2.1 foundation, completed Sprint 2.4), earnings, profile, documents, skills (list/add/remove/toggle-visibility — Phase 2.1 + Sprint 2.3), experience (list/add/edit/delete, visibility via edit form — Phase 2.1 + Sprint 2.3), gallery (list/upload, edit, remove, move up/down — Sprint 2.2), **company (Sprint 3.1): join by code, respond to invitations (accept/decline), leave, history**.

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_supplier()`. Profile-editing and company-affiliation views additionally use `_guard_with_caregiver()`, resolving `request.user.caregiver_profile`.

## Organization Portal (23 views)

Dashboard, staff (list/approve/suspend, **+terminate, +invite-by-phone, +invitation-cancel, +affiliation-request-approve/reject — Sprint 3.1**), assignments, capacity, financial, reports, notifications, profile, documents.

Entry: `_guard()` → `require_authenticated()` → `resolve_tenant_id()` → `resolve_organization()`

## Admin Portal (12 views)

Home, tenants, suppliers, orders, finance, escrows, disputes, feature gates, system status.

Entry: `require_admin_permission()` → `require_authenticated()` → RBAC check

## API (12 endpoints)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health/` | GET | Health check |
| `/api/v1/sample/order-counts/` | GET | Sample order counts |
| `/api/v1/sample/providers/` | GET | Sample provider reports |
| `/api/v1/discovery/suppliers/` | GET | Supplier discovery (permission-gated `DISCOVERY_SUPPLIERS_READ`, granted to no role in `DEFAULT_TENANT_ROLES` — internal/operator tooling, not a public/anonymous surface; confirmed out of scope for the BG-022 public-visibility remediation, see `traceability/IMPLEMENTATION_JOURNAL.md`; re-confirmed Sprint 2.6 Section I — calls `apps.discovery.services.DiscoveryService.search()` directly, unrelated to the public `CaregiverPublicProfileService`; no new public caregiver-profile API created, existing public HTML surfaces already serve that need, see `ARCHITECTURE_DECISION_LOG.md` ADM-022 Decision 3) |
| `/api/v1/pricing/quotes/` | POST | Quote creation |
| `/api/v1/reviews/` | POST | Review submission |
| `/api/v1/suppliers/<id>/reputation/` | GET | Supplier reputation |
| `/api/v1/wallet/balance/` | GET | Wallet balance |
| `/api/v1/wallet/transactions/` | GET | Wallet transactions |
| `/api/v1/payments/intents/` | POST | Payment intent creation |
| `/api/v1/payments/intents/<id>/attempts/` | POST | Payment attempt |
| `/api/v1/payments/callbacks/fake/` | POST | Fake PSP callback (unauthenticated) |

## Public Site (19 views)

Home, about, services, how-it-work, contact, pricing, trust-safety, caregivers, organizations, find-a-caregiver, caregiver profile (now includes a Sprint 2.4 privacy-safe weekly-availability summary — day labels only, never exact times; Sprint 2.6 — SEO `page_url`/`canonical_url` now the profile's own URL, gallery alt-text fallback, redundant generic verification badge removed), **find-an-organization (Phase 3 Sprint 3.3 — the Company Public Directory: search/city/service-category filters, pagination, organization cards with logo/headline/rating/verification badge/city/service summary/active-caregiver count; route ordered before the existing `find-an-organization/<uuid:supplier_id>/` detail route)**, organization profile, FAQ, privacy, terms, accessibility, support, service-areas.

Phase 3 Sprint 3.3 (Company Public Directory and Discovery, 2026-07-16): added the public
Organization Directory (`OrganizationDirectoryService`, `apps.public_site.services
.organization_directory_service`), mirroring `CaregiverDirectoryService`'s architecture
exactly — reuses `SupplierSearchService.filter_suppliers()`/`DiscoveryRankingService.rank()`
unmodified and `common.bulk_supplier_attrs()`/`is_publicly_visible_attrs()` unchanged (no
second visibility policy). See `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-025 for the
full Option-B ADR (why `/organizations/` stays the unchanged B2B recruitment page and
`/find-an-organization/` is the new, separate directory route — mirrors the
`/caregivers/` vs `/find-a-caregiver/` precedent exactly). `common.py` gained two small
generic helpers, `parse_page()`/`build_pagination()`, extracted verbatim (zero behavior
change) from `CaregiverDirectoryService`'s own former private methods — both directory
services now call them as thin wrappers. `OrganizationStaffService` gained
`list_active_caregiver_counts_bulk()` (one grouped query regardless of organization count)
to avoid a KL-012-class N+1 when rendering up to 12 directory cards per page.

Sprint 2.6 (Public Profile Finalization): the caregiver profile page (`caregiver-profile`),
directory (`find-a-caregiver`), and home page were all re-verified — not changed — to
confirm they compose skills/experience/gallery/credentials/availability/reviews/highlights
consistently and resolve through the one canonical visibility policy
(`common.is_publicly_visible_attrs()`, workflow #25). `organization_profile.html` was found
to carry the identical SEO `page_url` bug the caregiver page had — deliberately left
unfixed, out of this sprint's caregiver-only scope (`quality/DEFECT_AND_RISK_REGISTER.md`
KL-021 / `quality/COMPLETION_BACKLOG.md` BG-027).

PR #11 review remediation (2026-07-15): the directory and home page's query counts (measured
above as growing with candidate count) were found to violate Phase 2's own "bounded query
behavior" acceptance criterion and were fixed — see `traceability/ARCHITECTURE_DECISION_LOG
.md` ADM-022's remediation note and `quality/DEFECT_AND_RISK_REGISTER.md` KL-012 (now
RESOLVED). `CaregiverDirectoryService.search()`/`.featured()` now build cards from a
precomputed, per-page bulk data map instead of per-card queries.

## Presentation Services

Each portal has presentation services that transform domain models into view-ready data:
- `CustomerDashboardPresentationService`, `CustomerProfilePresentationService`, etc. (portal)
- `ProviderProfilePresentationService` (provider_portal)
- `OrganizationProfilePresentationService` (organization_portal)
- `HomePageService`, `CaregiverDirectoryService`, `CaregiverPublicProfileService`, `OrganizationDirectoryService` (public_site) — all four resolve caregiver/organization public visibility through the same canonical function, `apps.public_site.services.common.is_publicly_visible_attrs()` (BG-022 remediation, 2026-07-15); there is exactly one implementation of "is this publicly visible," never a per-surface duplicate. `CaregiverDirectoryService._build_card()` (Sprint 2.6 PR #11 KL-012 remediation) and `OrganizationDirectoryService._build_card()` (Phase 3 Sprint 3.3, same shape) both resolve rating/completed-jobs/logo/active-provider-count data for an entire page of cards in one bulk pass (`_bulk_card_data()`), never per card — including service-category names, resolved once per `search()` call and looked up in Python per card, not queried per card.
- `CaregiverSkillService`, `CaregiverExperienceService`, `PublicCredentialSelector` (accounts, Phase 2.1 — domain services/selectors, not presentation services; called by provider_portal/public_site)
- `CaregiverGalleryService` (accounts, Sprint 2.2 — domain service, not a presentation service; called by provider_portal; `CaregiverPublicProfileService._gallery()` is the read-only public-facing counterpart, gated by the existing BG-022 canonical visibility policy, no second rule)
- `CaregiverPublicProfileService._highlights()`/`_verification_badges()` and `ProviderProfilePresentationService._highlights()` (Sprint 2.3 — pure, read-only aggregations over data each service already resolved elsewhere on the same page; the public versions add zero new queries, the provider-portal preview adds two fixed-cost `.count()` queries). **PR #7 remediation:** physical file deletion is deferred to `transaction.on_commit()` rather than performed inline before the row commits, and `apps.accounts.services.image_validation.validate_image()` (called from every route into this service) now also bounds decoded image width/height/pixel count, not just upload byte size.
- `AvailabilityQueryService.evaluate()`/`get_distinct_active_days()` (availability, Sprint 2.4 — the one canonical, structured, supplier-keyed availability evaluator; `CaregiverPublicProfileService._schedule_summary()` and `provider_portal/views.py::_public_summary_labels()` both call it directly rather than duplicating day-label logic — see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-020 Decision 1 for why this is not a caregiver-keyed service)
- `CaregiverDashboardPresentationService` (provider_portal, Sprint 2.5 — assembles the dashboard's work summary/financial overview/invoice summary/reputation/statistics sections; `build_for_supplier()` gathers data via `OrderQueryService`/`FinancialDocumentService`/`WalletService`/`ReputationService`/`PublicCredentialSelector` (all pre-existing, none newly invented), `build()` itself performs no query — see `traceability/ARCHITECTURE_DECISION_LOG.md` ADM-021)
