# DOMAIN AND MODULE MAP

**Last verified HEAD:** a5dbaf28703142edaa1d770ea8f3c2a45a12640f
**Last verified date:** 2026-07-14

---

## Domain Bounded Contexts

The system is organized into these bounded contexts:

### Identity & Access (kernel + accounts)
- **kernel**: Tenant, Person, UserAccount, Role, Permission, RoleAssignment, ServiceSupplier, EventOutbox, AuditLog, ConfigurationKey/Value, FeatureFlag, PolicyDefinition/Version
- **accounts**: OTPChallenge, CustomerProfile, ElderProfile, TrustedContact, CaregiverProfile, OrganizationProfile, OrganizationMembership, CompanyAffiliationRequest, PlatformTeamMember, VerificationDocument

### Order Lifecycle (orders)
- ServiceCategory, ServiceType, Order, OrderStatusHistory, OrderShareLink, OrderOffer (Phase 1), OrderOrganizationEligibility

### Matching (matching)
- MatchRound, MatchCandidate

### Booking (booking)
- SupplierAssignment

### Execution (execution)
- ExecutionSession

### Financial Core (finance + payments + wallet + commission)
- **finance**: FinancialParty, FinancialDocument/Item, FinancialObligation, PaymentTransaction, EscrowRecord/Movement, LedgerEntry, SettlementBatch/Item, WalletAccount/Transaction (legacy)
- **payments**: PaymentIntent, PaymentAttempt, PaymentCallback
- **wallet**: Wallet, WalletTransaction, WalletBalanceSnapshot
- **commission**: CommissionContract, PaymentDeadline/Extension, CommissionSnapshot, ObjectionPeriod/Extension, Dispute/Line/Resolution, ReleaseInstruction, RefundInstruction

### Pricing (pricing)
- PricingRule, Quote/Line, Promotion/Condition/Effect

### Discovery (discovery)
- Service-only: DiscoveryService, SearchService, RankingService

### Reviews (reviews)
- Review, ReviewRating, ReputationSnapshot

### Notifications (notifications)
- Notification, NotificationDeliveryAttempt

### Availability (availability)
- ProviderWorkingWindow, AvailabilityBlockedPeriod, CapacityRule

### Jobs (jobs)
- JobDefinition, JobRun

### Reporting (reporting)
- DTOs only: OrderCountsReport, ProviderPerformanceReport, MarketplaceStats, FinancialSummary

### Portals (portal, provider_portal, organization_portal, admin_portal, public_site)
- View-only apps with presentation services

### UI (showcase)
- Component library demo

---

## Cross-App Dependency Graph

```
kernel.Tenant <-------- (FK from every tenant-scoped model)
    |
    +-- kernel.ServiceSupplier <--- availability, booking, matching, orders,
    |                               pricing, reviews, commission
    |
finance.FinancialParty <--- finance (all models), commission, wallet, payments
    |
orders.Order <--- matching, booking, execution, commission, finance,
    |              pricing, reviews, orders (itself)
    |
booking.SupplierAssignment <--- execution, commission
execution.ExecutionSession <--- commission, finance
commission.CommissionSnapshot <--- finance (EscrowRecord), commission (DisputeResolution)
```

The system has a hub-and-spoke architecture with `orders.Order` as the central hub entity referenced by nearly every business module.
