"""
Canonical permission-key inventory — Epic 05 (Permission-Key Registry &
Authorization Hardening).

Every key here corresponds to a real `PermissionService.require()`/
`.check()` enforcement call site — see each key's own comment for exactly
which one. This module is imported once, at Django app-registry-ready
time (apps.kernel.apps.KernelConfig.ready(), see that file), so every key
is registered before any request/test can reference the registry.

Do not add a key without a real enforcement call site to back it — see
apps.kernel.permissions.registry's own module docstring for why (this is
not a place to pre-declare capabilities that might exist someday).
"""

from .registry import register

# --- apps.booking ------------------------------------------------------

BOOKING_ASSIGNMENT_ASSIGN = register(
    "booking.assignment.assign",
    domain="booking",
    resource="assignment",
    action="assign",
    description="Assign a supplier to an order. Guards AssignmentService.assign()/replace().",
    organization_scope=True,
)

# --- apps.commission ---------------------------------------------------

COMMISSION_POLICY_MANAGE = register(
    "commission.policy.manage",
    domain="commission",
    resource="policy",
    action="manage",
    description=(
        "Create/activate commission PolicyVersions (global defaults, "
        "cooperation-type defaults, platform-specific overrides). Guards "
        "CommissionPolicyService.set_global_defaults()/"
        "set_cooperation_default()/set_platform_override()."
    ),
    platform_scope=True,
)
COMMISSION_CONTRACT_PROPOSE = register(
    "commission.contract.propose",
    domain="commission",
    resource="contract",
    action="propose",
    description="Propose a company-caregiver commission contract. Guards CommissionContractService.propose().",
    organization_scope=True,
)
COMMISSION_CONTRACT_APPROVE = register(
    "commission.contract.approve",
    domain="commission",
    resource="contract",
    action="approve",
    description=(
        "Approve or reject a proposed company-caregiver commission contract "
        "(the caregiver's own approval). Guards CommissionContractService.approve()/reject()."
    ),
)
COMMISSION_CONTRACT_TERMINATE = register(
    "commission.contract.terminate",
    domain="commission",
    resource="contract",
    action="terminate",
    description="Terminate an active company-caregiver commission contract. Guards CommissionContractService.terminate().",
    platform_scope=True,
)
COMMISSION_DEADLINE_EXTEND = register(
    "commission.deadline.extend",
    domain="commission",
    resource="deadline",
    action="extend",
    description="Extend an order's payment deadline with a mandatory reason. Guards PaymentDeadlineService.extend().",
    platform_scope=True,
)

# --- apps.commission (Financial Core PR-B) ------------------------------
# Customer self-actions (approving own completion, opening own dispute) are
# NOT RBAC-key-guarded here — they follow the same "ownership is the
# security boundary, no RBAC permission keys" model as every other
# customer-facing action in apps.portal (see that app's own permissions.py
# docstring); ObjectionPeriodService.approve_by_customer() and
# DisputeService.open() enforce ownership directly (order.customer_profile
# must resolve to the acting customer), mirroring
# apps.commission.services.authorization.assert_actor_is_contract_caregiver's
# own precedent from the PR-A remediation.

COMMISSION_OBJECTION_EXTEND = register(
    "commission.objection.extend",
    domain="commission",
    resource="objection_period",
    action="extend",
    description=("Extend an order's objection period with a mandatory reason. Guards ObjectionPeriodService.extend()."),
    platform_scope=True,
)
COMMISSION_DISPUTE_RESOLVE = register(
    "commission.dispute.resolve",
    domain="commission",
    resource="dispute",
    action="resolve",
    description=(
        "Resolve an open dispute, allocating its blocked Escrow amount to "
        "customer refund and/or platform/company/caregiver release. Guards "
        "DisputeResolutionService.resolve()."
    ),
    platform_scope=True,
)
COMMISSION_REFUND_AUTHORIZE = register(
    "commission.refund.authorize",
    domain="commission",
    resource="refund",
    action="authorize",
    description=(
        "Authorize a held-Escrow refund not driven by a dispute resolution "
        "(e.g. manual/cancellation). Guards RefundInstructionService.create_manual()."
    ),
    platform_scope=True,
)
COMMISSION_ESCROW_VIEW = register(
    "commission.escrow.view",
    domain="commission",
    resource="escrow",
    action="view",
    description="View Escrow/dispute/release-instruction records platform-wide. Guards admin_portal's Escrow views.",
    platform_scope=True,
)

# --- apps.finance --------------------------------------------------------

FINANCE_LEDGER_POST = register(
    "finance.ledger.post",
    domain="finance",
    resource="ledger",
    action="post",
    description="Post balanced ledger entries. Guards LedgerService.post_entries().",
)
FINANCE_PAYMENT_RECORD = register(
    "finance.payment.record",
    domain="finance",
    resource="payment",
    action="record",
    description="Record a payment transaction. Guards PaymentService.record_payment() (or equivalent).",
)
FINANCE_SETTLEMENT_CREATE_BATCH = register(
    "finance.settlement.create_batch",
    domain="finance",
    resource="settlement",
    action="create_batch",
    description="Create a settlement batch. Guards SettlementService.create_batch().",
)
FINANCE_DOCUMENT_ISSUE = register(
    "finance.document.issue",
    domain="finance",
    resource="document",
    action="issue",
    description="Issue a financial document. Guards FinancialDocumentService's issue transition.",
)
FINANCE_DOCUMENT_LOCK = register(
    "finance.document.lock",
    domain="finance",
    resource="document",
    action="lock",
    description="Lock a financial document. Guards FinancialDocumentService's lock transition.",
)

# --- apps.execution --------------------------------------------------------

EXECUTION_SESSION_CLOSE = register(
    "execution.session.close",
    domain="execution",
    resource="session",
    action="close",
    description="Close an execution session. Guards ExecutionService's close transition.",
)

# --- apps.accounts / organization isolation (Epic 04, corrected in Epic 05) --

ACCOUNTS_DOCUMENT_REVIEW = register(
    "accounts.document.review",
    domain="accounts",
    resource="document",
    action="review",
    description=(
        "Approve, reject, or request correction on an uploaded VerificationDocument "
        "(caregiver or organization). Guards VerificationReviewService's review methods."
    ),
    platform_scope=True,
)

ACCOUNTS_PROFILE_ACTIVATE = register(
    "accounts.profile.activate",
    domain="accounts",
    resource="profile",
    action="activate",
    description=(
        "Formally activate an eligible caregiver's/organization's profile. Guards "
        "ProfileActivationService.activate_caregiver()/activate_organization()."
    ),
    platform_scope=True,
)

ORGANIZATION_MEMBERSHIP_APPROVE = register(
    "organization.membership.approve",
    domain="organization",
    resource="membership",
    action="approve",
    description="Approve an OrganizationMembership. Guards OrganizationStaffService.approve_membership().",
    organization_scope=True,
)
ORGANIZATION_MEMBERSHIP_SUSPEND = register(
    "organization.membership.suspend",
    domain="organization",
    resource="membership",
    action="suspend",
    description="Suspend an OrganizationMembership. Guards OrganizationStaffService.suspend_membership().",
    organization_scope=True,
)
ORGANIZATION_MEMBERSHIP_INVITE = register(
    "organization.membership.invite",
    domain="organization",
    resource="membership",
    action="invite",
    description=(
        "Invite a caregiver to join the organization (creates a PENDING "
        "OrganizationMembership). Guards apps.accounts.services.affiliations.invite_caregiver() "
        "(Phase 3 Sprint 3.1)."
    ),
    organization_scope=True,
)
ORGANIZATION_MEMBERSHIP_REJECT = register(
    "organization.membership.reject",
    domain="organization",
    resource="membership",
    action="reject",
    description=(
        "Reject a caregiver's affiliation request, or cancel a pending invitation the "
        "organization itself sent. Guards apps.accounts.services.affiliations"
        ".reject_affiliation_request()/cancel_invitation() (Phase 3 Sprint 3.1)."
    ),
    organization_scope=True,
)
ORGANIZATION_MEMBERSHIP_TERMINATE = register(
    "organization.membership.terminate",
    domain="organization",
    resource="membership",
    action="terminate",
    description=(
        "Terminate an ACTIVE OrganizationMembership from the organization's side. Guards "
        "apps.accounts.services.affiliations.terminate_membership() (Phase 3 Sprint 3.1). "
        "A caregiver terminating their own membership uses leave_organization() instead, "
        "which is ownership-authorized, not permission-gated."
    ),
    organization_scope=True,
)
ORGANIZATION_PROFILE_UPDATE = register(
    "organization.profile.update",
    domain="organization",
    resource="profile",
    action="update",
    description=(
        "Edit an OrganizationProfile's own public/contact fields, media, or documents. "
        "Guards OrganizationProfileUpdateService.update_profile() (Epic 06 Sprint 2)."
    ),
    organization_scope=True,
)

# --- apps.api (Module 17A/17B) -------------------------------------------
# Re-registered here (not just left in apps.api.permission_keys) so the
# central registry is genuinely complete — apps.api.permission_keys
# becomes a re-export facade over these, see that module.

REPORTING_READ = register(
    "reporting.read",
    domain="reporting",
    resource="reporting",
    action="read",
    description="Read reporting endpoints. Guards GET /api/v1/sample/order-counts/, /providers/.",
)
DISCOVERY_SUPPLIERS_READ = register(
    "discovery.suppliers.read",
    domain="discovery",
    resource="suppliers",
    action="read",
    description="Read discovery supplier listings. Guards GET /api/v1/discovery/suppliers/.",
)
PRICING_QUOTES_CREATE = register(
    "pricing.quotes.create",
    domain="pricing",
    resource="quotes",
    action="create",
    description="Create a pricing quote. Guards POST /api/v1/pricing/quotes/.",
)
REVIEWS_SUBMIT = register(
    "reviews.submit",
    domain="reviews",
    resource="reviews",
    action="submit",
    description="Submit a review. Guards POST /api/v1/reviews/.",
)
REVIEWS_READ = register(
    "reviews.read",
    domain="reviews",
    resource="reviews",
    action="read",
    description="Read supplier reputation. Guards GET /api/v1/suppliers/{id}/reputation/.",
)
WALLET_READ = register(
    "wallet.read",
    domain="wallet",
    resource="wallet",
    action="read",
    description="Read wallet balance/transactions. Guards GET /api/v1/wallet/balance/, /transactions/.",
)
PAYMENTS_INTENTS_CREATE = register(
    "payments.intents.create",
    domain="payments",
    resource="intents",
    action="create",
    description="Create a payment intent. Guards POST /api/v1/payments/intents/.",
)
PAYMENTS_ATTEMPTS_CREATE = register(
    "payments.attempts.create",
    domain="payments",
    resource="attempts",
    action="create",
    description="Create a payment attempt. Guards POST /api/v1/payments/intents/{id}/attempts/.",
)

# --- apps.admin_portal (Module 19) ---------------------------------------

ADMIN_PORTAL_ACCESS = register(
    "admin.portal.access",
    domain="admin",
    resource="portal",
    action="access",
    description="Access the admin portal at all.",
    platform_scope=True,
)
ADMIN_TENANTS_READ = register(
    "admin.tenants.read",
    domain="admin",
    resource="tenants",
    action="read",
    description="Read tenant data in the admin portal.",
    platform_scope=True,
)
ADMIN_SUPPLIERS_READ = register(
    "admin.suppliers.read",
    domain="admin",
    resource="suppliers",
    action="read",
    description="Read supplier data in the admin portal.",
    platform_scope=True,
)
ADMIN_ORDERS_READ = register(
    "admin.orders.read",
    domain="admin",
    resource="orders",
    action="read",
    description="Read order data in the admin portal.",
    platform_scope=True,
)
ADMIN_FINANCE_READ = register(
    "admin.finance.read",
    domain="admin",
    resource="finance",
    action="read",
    description="Read finance data in the admin portal.",
    platform_scope=True,
)
ADMIN_SYSTEM_READ = register(
    "admin.system.read",
    domain="admin",
    resource="system",
    action="read",
    description="Read system data in the admin portal.",
    platform_scope=True,
)
