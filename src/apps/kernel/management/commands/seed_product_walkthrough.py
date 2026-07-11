"""
Management command: seed_product_walkthrough

Populates a dedicated, deterministic local-development tenant
("demo-senior-platform") with a realistic dataset so a human can walk
through the existing customer/provider/organization/admin experiences
already implemented in this codebase — no new pages, no new business
behavior, no UI changes. Every write goes through the same services the
real application uses (RegistrationService-adjacent helpers,
OrganizationRoleSyncService, SupplierRegistry, OrderEligibilityService,
AssignmentService, ExecutionService, the real fake-PSP settlement chain,
ReviewSubmissionService) — nothing is written directly to a model that
has an approved service-layer writer.

Local development only:
  * refuses to run when settings.DEBUG is False
  * every record lives under the dedicated "demo-senior-platform" tenant
    (the tenant itself is the unambiguous "this is demo data" marker —
    Orders additionally carry an internal_note marker, matching the
    established apps.orders.management.commands.seed_demo_orders
    convention, since Order has no dedicated tenant-agnostic demo flag)
  * deterministic emails/phones — safe to re-run (idempotent throughout,
    via get_or_create / explicit lookups, matching every other seed
    command in this repository)
  * never calls a real SMS/email/push/payment provider — settlement uses
    the repository's own FakePaymentProviderAdapter (already the default
    provider in this environment; no network call is possible)
  * never deletes non-demo data — --reset-demo only ever touches rows
    scoped to this dedicated tenant

Usage:
    python manage.py seed_product_walkthrough
    python manage.py seed_product_walkthrough --reset-demo
"""

import uuid
from datetime import time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.models.profiles import (
    CaregiverProviderType,
    CustomerProfile,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    ProfileStatus,
)
from apps.accounts.services.care_recipients import CareRecipientService
from apps.accounts.services.organization_rbac import OrganizationRoleSyncService
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.accounts.services.profiles import ensure_caregiver_profile, ensure_customer_profile
from apps.accounts.services.supplier_bridge import (
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
)
from apps.availability.models import BlockedPeriodReason
from apps.availability.services import AvailabilityMutationService
from apps.booking.services import AssignmentService, OrganizationAssignmentService
from apps.execution.services import ExecutionService
from apps.finance.models import FinancialParty, FinancialPartyType
from apps.finance.services import FinancialDocumentService, FinancialPartyService
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount
from apps.kernel.models.supplier import AvailabilityStatus, SupplierType
from apps.kernel.role_catalog import DEFAULT_TENANT_ROLES
from apps.orders.models import (
    FINAL_STATUSES,
    EligibilityStatus,
    Order,
    OrderOrganizationEligibility,
    OrderStatus,
    ServiceCategory,
    ServiceType,
)
from apps.orders.services import (
    approve_cancellation,
    create_operator_order,
    create_public_order,
    request_cancellation,
)
from apps.orders.services.eligibility_service import OrderEligibilityService
from apps.payments.services import PaymentCallbackService, PaymentIntentService
from apps.reviews.services import ReviewSubmissionService
from apps.wallet.models import Wallet
from apps.wallet.services import WalletService

DEMO_TENANT_SLUG = "demo-senior-platform"
DEMO_TENANT_NAME = "پلتفرم مراقبت سالمندیار — محیط نمایشی"
DEMO_PASSWORD = "Demo12345!"
DEMO_ORDER_MARKER = "PRODUCT_WALKTHROUGH_DEMO"
DEMO_CATEGORY_SLUG = "product-walkthrough-daily-care"
DEMO_TYPE_SLUG = "product-walkthrough-hourly-care"

CUSTOMERS = [
    {"email": "demo.customer@example.test", "phone": "09000010001", "name": "سارا محمدی"},
    {"email": "demo.customer2@example.test", "phone": "09000010002", "name": "نگار حسینی"},
    {"email": "demo.customer3@example.test", "phone": "09000010003", "name": "پریسا کریمی"},
]

INDEPENDENT_PROVIDERS = [
    {
        "email": "demo.provider1@example.test",
        "phone": "09000020001",
        "name": "مریم احمدی",
        "specialty": "پرستار",
        "availability": "available",
    },
    {
        "email": "demo.provider2@example.test",
        "phone": "09000020002",
        "name": "زهرا موسوی",
        "specialty": "مراقب سالمند",
        "availability": "available",
    },
    {
        "email": "demo.provider3@example.test",
        "phone": "09000020003",
        "name": "الهام صادقی",
        "specialty": "فیزیوتراپیست",
        "availability": "available",
    },
    {
        "email": "demo.provider4@example.test",
        "phone": "09000020004",
        "name": "طاهره رضوانی",
        "specialty": "پرستار",
        "availability": "unavailable",
    },
    {
        "email": "demo.provider5@example.test",
        "phone": "09000020005",
        "name": "فرانک قاسمی",
        "specialty": "مراقب سالمند",
        "availability": "limited",
    },
]

ORGANIZATIONS = [
    {
        "code": "DEMO-WALKTHROUGH-ORG1",
        "name": "شرکت مراقبت مهر سالمند",
        "admin_email": "demo.org1.admin@example.test",
        "admin_phone": "09000030001",
        "admin_name": "بهنام طاهری",
        "providers": [
            {"email": "demo.org1.provider1@example.test", "phone": "09000040001", "name": "شیرین رستمی"},
            {"email": "demo.org1.provider2@example.test", "phone": "09000040002", "name": "لیلا نوروزی"},
            {"email": "demo.org1.provider3@example.test", "phone": "09000040003", "name": "آزاده یوسفی"},
        ],
    },
    {
        "code": "DEMO-WALKTHROUGH-ORG2",
        "name": "موسسه همراهان زندگی",
        "admin_email": "demo.org2.admin@example.test",
        "admin_phone": "09000030002",
        "admin_name": "کاوه شریفی",
        "providers": [
            {"email": "demo.org2.provider1@example.test", "phone": "09000040004", "name": "نسرین عباسی"},
            {"email": "demo.org2.provider2@example.test", "phone": "09000040005", "name": "مینا فرهادی"},
            {"email": "demo.org2.provider3@example.test", "phone": "09000040006", "name": "رویا کاظمی"},
        ],
    },
]

PLATFORM_ADMIN = {"email": "demo.admin@example.test", "phone": "09000090001", "name": "مدیر پلتفرم نمایشی"}

# Discovered, real URL names (see PR description / final report for the
# provenance of each — derived from config/urls.py + each app's urls.py,
# never guessed).
ROUTE_NAMES = {
    "login": "accounts:login",
    "customer_workspace": "portal:dashboard",
    "care_recipients": "portal:care-recipients",
    "provider_dashboard": "provider_portal:dashboard",
    "provider_availability": "provider_portal:availability",
    "provider_assignments": "provider_portal:assignments",
    "provider_earnings": "provider_portal:earnings",
    "provider_profile": "provider_portal:profile",
    "provider_profile_edit": "provider_portal:profile-edit-basic",
    "organization_dashboard": "organization_portal:dashboard",
    "organization_staff": "organization_portal:staff",
    "assignment_center": "organization_portal:assignment-center",
    "organization_capacity": "organization_portal:capacity",
    "organization_reports": "organization_portal:reports",
    "organization_profile": "organization_portal:profile",
    "organization_profile_edit": "organization_portal:profile-edit",
}


class Command(BaseCommand):
    help = "Seed a deterministic local product-walkthrough dataset (development only, idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Delete and rebuild only records scoped to the demo-senior-platform tenant "
            "before re-seeding. Never touches any other tenant's data.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_product_walkthrough refuses to run when DEBUG=False. "
                "This command is strictly for local development."
            )

        self.stats = {"created": 0, "updated": 0, "already_correct": 0, "skipped": 0, "failed": 0}

        if options["reset_demo"]:
            self._reset_demo()

        tenant = self._ensure_tenant()
        self._ensure_roles(tenant)
        category, service_type = self._ensure_catalog(tenant)

        platform_admin = self._ensure_platform_admin(tenant)
        customers = self._ensure_customers(tenant)
        independent_providers = self._ensure_independent_providers(tenant)
        organizations = self._ensure_organizations(tenant, platform_admin)
        affiliated_providers = self._ensure_affiliated_providers(tenant, organizations)

        orders = self._ensure_orders(tenant, category, service_type, customers, organizations)
        self._ensure_assignments(orders, independent_providers, organizations, affiliated_providers)
        self._ensure_availability(independent_providers, affiliated_providers)
        finance_ok = self._ensure_execution_and_finance(orders, platform_admin)
        self._ensure_reviews(orders)

        self._print_report(
            tenant,
            customers,
            independent_providers,
            organizations,
            affiliated_providers,
            platform_admin,
            orders,
            finance_ok,
        )

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------

    def _record(self, outcome):
        """outcome: True (created) / False (already_correct) / 'updated' / 'skipped' / 'failed'."""
        if outcome is True:
            self.stats["created"] += 1
        elif outcome is False:
            self.stats["already_correct"] += 1
        elif outcome == "updated":
            self.stats["updated"] += 1
        elif outcome == "skipped":
            self.stats["skipped"] += 1
        elif outcome == "failed":
            self.stats["failed"] += 1

    # ------------------------------------------------------------------
    # --reset-demo
    # ------------------------------------------------------------------

    def _reset_demo(self):
        """Delete every row scoped to the demo tenant, in dependency-safe
        order (leaves first). Never touches any other tenant. The Tenant
        row itself is kept (idempotently re-used by _ensure_tenant), only
        its content is wiped, so re-seeding after this is identical to a
        first run against a stale demo tenant."""
        tenant = Tenant.objects.filter(slug=DEMO_TENANT_SLUG).first()
        if tenant is None:
            self.stdout.write("--reset-demo: no existing demo tenant found, nothing to reset.")
            return

        with transaction.atomic():
            from apps.finance.models import FinancialParty
            from apps.payments.models import PaymentAttempt, PaymentIntent
            from apps.reviews.models import Review
            from apps.wallet.models import Wallet, WalletTransaction

            person_ids = list(Person.objects.filter(tenant=tenant).values_list("id", flat=True))
            user_ids = list(UserAccount.objects.filter(tenant=tenant).values_list("id", flat=True))
            org_ids = list(OrganizationProfile.objects.filter(tenant=tenant).values_list("id", flat=True))

            from apps.payments.models import PaymentCallback

            Review.objects.filter(order__tenant_id=tenant.id).delete()
            WalletTransaction.objects.filter(wallet__tenant_id=tenant.id).delete()
            Wallet.objects.filter(tenant_id=tenant.id).delete()
            PaymentCallback.objects.filter(attempt__tenant_id=tenant.id).delete()
            PaymentAttempt.objects.filter(tenant_id=tenant.id).delete()
            PaymentIntent.objects.filter(tenant_id=tenant.id).delete()

            from apps.finance.models import FinancialDocument, FinancialObligation, LedgerEntry, PaymentTransaction

            LedgerEntry.objects.filter(tenant_id=tenant.id).delete()
            PaymentTransaction.objects.filter(tenant_id=tenant.id).delete()
            FinancialObligation.objects.filter(tenant_id=tenant.id).delete()
            FinancialDocument.objects.filter(tenant_id=tenant.id).delete()
            FinancialParty.objects.filter(tenant_id=tenant.id).delete()

            from apps.execution.models import ExecutionSession

            ExecutionSession.objects.filter(tenant_id=tenant.id).delete()

            from apps.booking.models import SupplierAssignment

            SupplierAssignment.objects.filter(order__tenant_id=tenant.id).delete()

            from apps.orders.models import OrderOrganizationEligibility, OrderStatusHistory

            OrderOrganizationEligibility.objects.filter(tenant_id=tenant.id).delete()
            OrderStatusHistory.objects.filter(order__tenant_id=tenant.id).delete()
            Order.objects.filter(tenant_id=tenant.id).delete()

            from apps.availability.models import AvailabilityBlockedPeriod, ProviderWorkingWindow
            from apps.kernel.models.supplier import ServiceSupplier

            supplier_ids = list(ServiceSupplier.objects.filter(tenant_id=tenant.id).values_list("id", flat=True))
            AvailabilityBlockedPeriod.objects.filter(supplier_id__in=supplier_ids).delete()
            ProviderWorkingWindow.objects.filter(supplier_id__in=supplier_ids).delete()
            ServiceSupplier.objects.filter(tenant_id=tenant.id).delete()

            OrganizationMembership.objects.filter(organization_id__in=org_ids).delete()
            from apps.accounts.models.profiles import CompanyAffiliationRequest

            CompanyAffiliationRequest.objects.filter(organization_id__in=org_ids).delete()
            OrganizationProfile.objects.filter(tenant=tenant).delete()

            from apps.accounts.models.profiles import CaregiverProfile, ElderProfile

            ElderProfile.objects.filter(customer_profile__user_id__in=user_ids).delete()
            CustomerProfile.objects.filter(user_id__in=user_ids).delete()
            CaregiverProfile.objects.filter(user_id__in=user_ids).delete()

            RoleAssignment.objects.filter(tenant=tenant).delete()
            Role.objects.filter(tenant=tenant).delete()

            ServiceType.objects.filter(tenant=tenant).delete()
            ServiceCategory.objects.filter(tenant=tenant).delete()

            UserAccount.objects.filter(id__in=user_ids).delete()
            Person.objects.filter(id__in=person_ids).delete()

        self.stdout.write(self.style.WARNING("--reset-demo: demo tenant content wiped, tenant row kept."))

    # ------------------------------------------------------------------
    # Tenant / roles / catalog
    # ------------------------------------------------------------------

    def _ensure_tenant(self):
        tenant, created = Tenant.objects.get_or_create(
            slug=DEMO_TENANT_SLUG,
            defaults={
                "name": DEMO_TENANT_NAME,
                "status": "active",
                "metadata": {"product_walkthrough_demo": True},
            },
        )
        self._record(created)
        return tenant

    def _ensure_roles(self, tenant):
        for role_def in DEFAULT_TENANT_ROLES:
            role, created = Role.objects.get_or_create(
                tenant=tenant,
                slug=role_def.slug,
                defaults={
                    "name": role_def.name,
                    "is_system": role_def.is_system,
                    "permissions": list(role_def.permissions),
                },
            )
            if created:
                self._record(True)
            elif role_def.permissions:
                missing = [key for key in role_def.permissions if key not in role.permissions]
                if missing:
                    role.permissions = [*role.permissions, *missing]
                    role.save(update_fields=["permissions", "updated_at", "version"])
                    self._record("updated")
                else:
                    self._record(False)
            else:
                self._record(False)

    def _ensure_catalog(self, tenant):
        category, created = ServiceCategory.objects.get_or_create(
            tenant=tenant,
            slug=DEMO_CATEGORY_SLUG,
            defaults={"name": "مراقبت روزانه سالمند (نمایشی)", "icon": "🏠", "sort_order": 0},
        )
        self._record(created)
        service_type, type_created = ServiceType.objects.get_or_create(
            tenant=tenant,
            category=category,
            slug=DEMO_TYPE_SLUG,
            defaults={"name": "مراقبت ساعتی (نمایشی)", "base_duration_minutes": 120, "sort_order": 0},
        )
        self._record(type_created)
        return category, service_type

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _ensure_user(self, tenant, *, email, phone, full_name, is_staff=False, is_superuser=False):
        user = UserAccount.objects.filter(email=email).first()
        if user:
            self._record(False)
            return user
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(
            email=email,
            phone=phone,
            password=DEMO_PASSWORD,
            person=person,
            tenant=tenant,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        self._record(True)
        return user

    def _ensure_platform_admin(self, tenant):
        existing = UserAccount.objects.filter(email=PLATFORM_ADMIN["email"]).first()
        if existing:
            if not existing.is_superuser or not existing.is_staff:
                # Never overwrite an existing NON-demo administrator's role, but this
                # account is our own deterministic demo account (matched by our own
                # fixed email) — safe to correct its flags if it was ever created
                # without them.
                existing.is_staff = True
                existing.is_superuser = True
                existing.save(update_fields=["is_staff", "is_superuser"])
                self._record("updated")
            else:
                self._record(False)
            return existing
        return self._ensure_user(
            tenant,
            email=PLATFORM_ADMIN["email"],
            phone=PLATFORM_ADMIN["phone"],
            full_name=PLATFORM_ADMIN["name"],
            is_staff=True,
            is_superuser=True,
        )

    # ------------------------------------------------------------------
    # A. Customers
    # ------------------------------------------------------------------

    def _ensure_customers(self, tenant):
        customers = []
        for spec in CUSTOMERS:
            user = self._ensure_user(tenant, email=spec["email"], phone=spec["phone"], full_name=spec["name"])
            profile = ensure_customer_profile(
                user,
                phone=spec["phone"],
                display_name=spec["name"],
                city="tehran",
                relation_to_elder="child",
            )
            customers.append((user, profile))

        primary_user, primary_profile = customers[0]

        if not primary_profile.elder_profiles.filter(full_name="پدر سارا محمدی").exists():
            CareRecipientService.create(
                customer_profile=primary_profile,
                full_name="پدر سارا محمدی",
                relationship="father",
                city="tehran",
                care_needs="کمک در امور روزمره و مراقبت پزشکی منظم",
                mobility_level="limited",
            )
            self._record(True)
        else:
            self._record(False)

        archived_name = "مادربزرگ سارا محمدی (بایگانی‌شده)"
        archived = primary_profile.elder_profiles.filter(full_name=archived_name).first()
        if not archived:
            archived = CareRecipientService.create(
                customer_profile=primary_profile,
                full_name=archived_name,
                relationship="grandparent",
                city="tehran",
            )
            CareRecipientService.archive(archived)
            self._record(True)
        else:
            self._record(False)

        return customers

    # ------------------------------------------------------------------
    # B. Independent caregivers
    # ------------------------------------------------------------------

    def _ensure_independent_providers(self, tenant):
        providers = []
        for spec in INDEPENDENT_PROVIDERS:
            user = self._ensure_user(tenant, email=spec["email"], phone=spec["phone"], full_name=spec["name"])
            profile = ensure_caregiver_profile(
                user,
                phone=spec["phone"],
                display_name=spec["name"],
                provider_type=CaregiverProviderType.INDEPENDENT,
                specialty=spec["specialty"],
                city="tehran",
                bio=f"{spec['name']} با سال‌ها تجربه در مراقبت از سالمندان، ارائه‌دهنده خدمات نمایشی است.",
                years_experience=6,
                service_radius_km=15,
                verification_status="verified",
            )
            supplier = get_or_create_supplier_for_caregiver(profile, tenant_id=tenant.id)
            self._ensure_supplier_financials(supplier)
            providers.append(
                {"user": user, "profile": profile, "supplier": supplier, "availability": spec["availability"]}
            )
        return providers

    def _ensure_supplier_financials(self, supplier):
        """Idempotently ensures a FinancialParty + Wallet exist for `supplier`
        without re-invoking FinancialPartyService.resolve_party_for_supplier()
        once they already do. That service is correctly get_or_create-safe at
        the row level, but — by design, for its real production callers —
        publishes a Finance.Party.Resolved event on every single invocation
        regardless of whether anything was actually created (see its own
        docstring/source; not a defect, just not idempotent-at-the-event-level,
        which every OTHER section of this command's re-run behavior depends
        on). Mirrors FinancialPartyService._resolve()'s own lookup key
        exactly, so this never diverges from what that service considers the
        canonical party for this supplier."""
        party_type = (
            FinancialPartyType.ORGANIZATION
            if supplier.supplier_type == SupplierType.ORGANIZATION
            else FinancialPartyType.SUPPLIER
        )
        party = FinancialParty.objects.filter(
            tenant_id=supplier.tenant_id,
            linked_entity_type="ServiceSupplier",
            linked_entity_id=supplier.id,
            party_type=party_type,
        ).first()
        if party is None:
            party = FinancialPartyService.resolve_party_for_supplier(supplier)
            WalletService.create_wallet(party=party)
            self._record(True)
            return
        if not Wallet.objects.filter(tenant_id=party.tenant_id, party=party).exists():
            WalletService.create_wallet(party=party)
            self._record(True)
        else:
            self._record(False)

    # ------------------------------------------------------------------
    # C. Organizations
    # ------------------------------------------------------------------

    def _ensure_organizations(self, tenant, platform_admin):
        organizations = []
        for org_spec in ORGANIZATIONS:
            admin_user = self._ensure_user(
                tenant,
                email=org_spec["admin_email"],
                phone=org_spec["admin_phone"],
                full_name=org_spec["admin_name"],
            )
            org, org_created = OrganizationProfile.objects.get_or_create(
                code=org_spec["code"],
                defaults={
                    "name": org_spec["name"],
                    "admin_user": admin_user,
                    "tenant": tenant,
                    "company_type": "care_agency",
                    "city": "tehran",
                    "phone": org_spec["admin_phone"],
                    "address": "تهران",
                    "status": ProfileStatus.ACTIVE,
                },
            )
            self._record(org_created)

            membership, membership_created = OrganizationMembership.objects.get_or_create(
                organization=org,
                user=admin_user,
                role_type=OrgMembershipRole.ADMIN,
                defaults={
                    "person": admin_user.person,
                    "status": OrgMembershipStatus.ACTIVE,
                    "joined_at": timezone.now(),
                    "approved_by": platform_admin,
                },
            )
            self._record(membership_created)

            # Organization-scoped RoleAssignment — required so the three
            # organization-admin permission keys are genuinely enforced,
            # not merely granted (see docs/architecture/rbac-permissions.md).
            # Only call the sync service when it would actually change
            # something: OrganizationRoleSyncService._audit() unconditionally
            # writes an AuditLog entry on every invocation (correct for its
            # real production callers — approve_membership()/
            # suspend_membership() — where every call is itself a genuine
            # state-changing action), so calling it unconditionally here on
            # every re-run would grow AuditLog forever even though nothing
            # about the assignment ever actually changes after the first run.
            existing_scoped_assignment = RoleAssignment.objects.filter(
                tenant=tenant,
                user=admin_user,
                scope_type="organization",
                scope_id=org.id,
            ).first()
            should_be_active = membership.status == OrgMembershipStatus.ACTIVE
            if existing_scoped_assignment is None or existing_scoped_assignment.is_active != should_be_active:
                OrganizationRoleSyncService.sync_for_membership(membership)
                self._record(True)
            else:
                self._record(False)

            organizations.append({"org": org, "admin_user": admin_user, "membership": membership, "spec": org_spec})
        return organizations

    # ------------------------------------------------------------------
    # D. Organization-affiliated caregivers
    # ------------------------------------------------------------------

    def _ensure_affiliated_providers(self, tenant, organizations):
        affiliated = []
        for org_index, org_entry in enumerate(organizations):
            org = org_entry["org"]
            provider_specs = org_entry["spec"]["providers"]
            for provider_index, spec in enumerate(provider_specs):
                user = self._ensure_user(tenant, email=spec["email"], phone=spec["phone"], full_name=spec["name"])
                profile = ensure_caregiver_profile(
                    user,
                    phone=spec["phone"],
                    display_name=spec["name"],
                    provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
                    specialty="مراقب سازمانی",
                    city="tehran",
                    bio=f"{spec['name']} عضو تیم مراقبتی {org.name} است.",
                    years_experience=4,
                    verification_status="verified",
                )

                # Last affiliated caregiver of the first organization is
                # created SUSPENDED, to make the inactive-member portal
                # state visible — remains ORGANIZATION_AFFILIATED throughout,
                # per the approved architecture (suspension is a membership
                # status change, not a provider_type change).
                is_suspended_example = org_index == 0 and provider_index == len(provider_specs) - 1

                membership, membership_created = OrganizationMembership.objects.get_or_create(
                    organization=org,
                    user=user,
                    role_type=OrgMembershipRole.CAREGIVER,
                    defaults={
                        "person": user.person,
                        "status": OrgMembershipStatus.ACTIVE,
                        "joined_at": timezone.now(),
                        "approved_by": org_entry["admin_user"],
                    },
                )
                self._record(membership_created)

                if is_suspended_example and membership.status != OrgMembershipStatus.SUSPENDED:
                    OrganizationStaffService.suspend_membership(membership, suspended_by=org_entry["admin_user"])
                    membership.refresh_from_db()
                    self._record("updated")

                supplier = get_or_create_supplier_for_caregiver(profile, tenant_id=tenant.id)
                self._ensure_supplier_financials(supplier)

                affiliated.append(
                    {
                        "user": user,
                        "profile": profile,
                        "supplier": supplier,
                        "organization": org,
                        "membership": membership,
                        "suspended": is_suspended_example,
                    }
                )
        return affiliated

    # ------------------------------------------------------------------
    # F. Orders and eligibility
    # ------------------------------------------------------------------

    def _create_order_if_missing(self, *, marker_suffix, **kwargs):
        internal_note = f"{DEMO_ORDER_MARKER}:{marker_suffix}"
        existing = Order.objects.filter(internal_note=internal_note).first()
        if existing:
            self._record(False)
            return existing, False
        is_public = kwargs.pop("_creator", None) == "public"
        if is_public:
            order = create_public_order(**kwargs)
            order.internal_note = internal_note
            order.save(update_fields=["internal_note"])
        else:
            kwargs["internal_note"] = internal_note
            order = create_operator_order(**kwargs)
        self._record(True)
        return order, True

    def _ensure_orders(self, tenant, category, service_type, customers, organizations):
        primary_user, primary_profile = customers[0]
        orders = {}

        common = {
            "service_category_id": category.id,
            "service_type_id": service_type.id,
            "phone": primary_profile.phone,
            "address": "تهران، خیابان ولیعصر",
            "city": "tehran",
            "customer_profile": primary_profile,
            "tenant_id": tenant.id,
        }

        orders["draft_1"], _ = self._create_order_if_missing(
            marker_suffix="draft-1",
            _creator="public",
            description="درخواست نمایشی — نیاز به مراقب برای پدر (در انتظار بررسی اپراتور)",
            **common,
        )
        orders["draft_2"], _ = self._create_order_if_missing(
            marker_suffix="draft-2",
            _creator="public",
            description="درخواست نمایشی — مراقبت شبانه (در انتظار بررسی اپراتور)",
            **common,
        )
        orders["unassigned_1"], _ = self._create_order_if_missing(
            marker_suffix="unassigned-1",
            description="سفارش نمایشی — نیازمند تخصیص ارائه‌دهنده مستقل",
            **common,
        )
        orders["unassigned_2"], _ = self._create_order_if_missing(
            marker_suffix="unassigned-2",
            description="سفارش نمایشی — نیازمند تخصیص ارائه‌دهنده سازمانی",
            **common,
        )
        orders["assigned_1"], _ = self._create_order_if_missing(
            marker_suffix="assigned-1",
            description="سفارش نمایشی — تخصیص‌یافته به ارائه‌دهنده مستقل",
            **common,
        )
        orders["assigned_2"], _ = self._create_order_if_missing(
            marker_suffix="assigned-2",
            description="سفارش نمایشی — تخصیص‌یافته به ارائه‌دهنده سازمانی",
            **common,
        )
        orders["in_progress"], _ = self._create_order_if_missing(
            marker_suffix="in-progress",
            description="سفارش نمایشی — در حال انجام",
            **common,
        )
        orders["completed_1"], _ = self._create_order_if_missing(
            marker_suffix="completed-1",
            description="سفارش نمایشی — تکمیل‌شده (ارائه‌دهنده مستقل، شامل تسویه مالی)",
            **common,
        )
        orders["completed_2"], _ = self._create_order_if_missing(
            marker_suffix="completed-2",
            description="سفارش نمایشی — تکمیل‌شده (بدون تسویه مالی)",
            **common,
        )
        orders["cancelled"], _ = self._create_order_if_missing(
            marker_suffix="cancelled",
            description="سفارش نمایشی — لغوشده",
            **common,
        )

        if orders["cancelled"].status not in FINAL_STATUSES:
            request_cancellation(
                order_id=orders["cancelled"].id, requested_by=primary_user, reason="نمایش گردش کار لغو سفارش"
            )
            approve_cancellation(order_id=orders["cancelled"].id, changed_by=primary_user)
            self._record("updated")

        # Organization-visible eligibility examples — always via the
        # service, never a direct model write.
        org1 = organizations[0]["org"]
        org2 = organizations[1]["org"]

        eligibility_only_org1, _ = self._create_order_if_missing(
            marker_suffix="eligible-org1-only",
            description="سفارش نمایشی — فقط سازمان ۱ واجد شرایط است",
            **common,
        )
        OrderEligibilityService.grant(order=eligibility_only_org1, organization=org1)

        eligibility_only_org2, _ = self._create_order_if_missing(
            marker_suffix="eligible-org2-only",
            description="سفارش نمایشی — فقط سازمان ۲ واجد شرایط است",
            **common,
        )
        OrderEligibilityService.grant(order=eligibility_only_org2, organization=org2)

        eligibility_both, _ = self._create_order_if_missing(
            marker_suffix="eligible-both",
            description="سفارش نمایشی — هر دو سازمان واجد شرایط هستند",
            **common,
        )
        OrderEligibilityService.grant(order=eligibility_both, organization=org1)
        OrderEligibilityService.grant(order=eligibility_both, organization=org2)

        eligibility_none, _ = self._create_order_if_missing(
            marker_suffix="eligible-none",
            description="سفارش نمایشی — هیچ سازمانی واجد شرایط نیست",
            **common,
        )

        eligibility_revoked, _ = self._create_order_if_missing(
            marker_suffix="eligible-revoked",
            description="سفارش نمایشی — واجدیت سازمان ۱ لغو شده است",
            **common,
        )
        # Only run the grant-then-revoke sequence if the pair isn't already
        # sitting in the final WITHDRAWN state — otherwise every re-run would
        # perform a real WITHDRAWN -> ACTIVE -> WITHDRAWN round trip through
        # OrderEligibilityService, each leg a genuine, audited, published
        # state transition (grant() correctly reactivates a WITHDRAWN row
        # rather than treating it as a no-op, since reactivation itself must
        # remain a real, auditable operation for its actual production
        # callers) — unbounded audit/event growth on an otherwise-idempotent
        # example. Reading current state directly (not via the service) adds
        # no additional write of its own.
        existing_revoked_eligibility = OrderOrganizationEligibility.objects.filter(
            order=eligibility_revoked,
            organization=org1,
        ).first()
        if existing_revoked_eligibility is None or existing_revoked_eligibility.status != EligibilityStatus.WITHDRAWN:
            OrderEligibilityService.grant(order=eligibility_revoked, organization=org1)
            OrderEligibilityService.revoke(order=eligibility_revoked, organization=org1)
            self._record(True)
        else:
            self._record(False)

        orders["eligibility_only_org1"] = eligibility_only_org1
        orders["eligibility_only_org2"] = eligibility_only_org2
        orders["eligibility_both"] = eligibility_both
        orders["eligibility_none"] = eligibility_none
        orders["eligibility_revoked"] = eligibility_revoked

        # assigned_2 is the order used for the organization-assignment
        # walkthrough — it needs org1 eligibility before assign_manual() will
        # accept it.
        OrderEligibilityService.grant(order=orders["assigned_2"], organization=org1)

        return orders

    # ------------------------------------------------------------------
    # G. Assignments
    # ------------------------------------------------------------------

    def _ensure_assignments(self, orders, independent_providers, organizations, affiliated_providers):
        independent_supplier = independent_providers[0]["supplier"]

        org1 = organizations[0]["org"]
        org1_membership = next(a for a in affiliated_providers if a["organization"] == org1 and not a["suspended"])
        org1_admin = organizations[0]["admin_user"]

        # No assigned_by/ownership_authorized_by passed: both None triggers
        # PermissionService's documented true-system-context path (no real
        # human actor exists at seed time) — the same convention every other
        # seed command in this repository uses to bypass RBAC entirely
        # rather than fabricate a fake authorized actor.
        for order in (orders["assigned_1"], orders["in_progress"], orders["completed_1"], orders["completed_2"]):
            if order.assigned_supplier_id is None:
                AssignmentService.assign(order_id=order.id, supplier=independent_supplier)
                self._record(True)
            else:
                self._record(False)

        order_2 = orders["assigned_2"]
        if order_2.assigned_supplier_id is None:
            OrganizationAssignmentService.assign_manual(
                organization=org1,
                order_id=order_2.id,
                membership_id=org1_membership["membership"].id,
                actor=org1_admin,
            )
            self._record(True)
        else:
            self._record(False)

    # ------------------------------------------------------------------
    # H. Availability
    # ------------------------------------------------------------------

    def _ensure_availability(self, independent_providers, affiliated_providers):
        today = timezone.now().date()
        for entry in independent_providers:
            supplier = entry["supplier"]
            desired_status = {
                "available": AvailabilityStatus.AVAILABLE,
                "unavailable": AvailabilityStatus.OFFLINE,
                "limited": AvailabilityStatus.BUSY,
            }[entry["availability"]]
            if supplier.availability_status != desired_status:
                supplier.availability_status = desired_status
                supplier.save(update_fields=["availability_status"])
                self._record("updated")
            else:
                self._record(False)

            if entry["availability"] == "available":
                for day in range(7):
                    _, created = self._ensure_working_window(supplier, day, time(8, 0), time(20, 0))
                    self._record(created)
            elif entry["availability"] == "limited":
                _, created = self._ensure_working_window(supplier, today.weekday(), time(14, 0), time(16, 0))
                self._record(created)
            else:
                self._ensure_blocked_period(supplier)

        for entry in affiliated_providers:
            supplier = entry["supplier"]
            desired_status = AvailabilityStatus.OFFLINE if entry["suspended"] else AvailabilityStatus.AVAILABLE
            if supplier.availability_status != desired_status:
                supplier.availability_status = desired_status
                supplier.save(update_fields=["availability_status"])
                self._record("updated")
            else:
                self._record(False)
            if not entry["suspended"]:
                for day in range(7):
                    _, created = self._ensure_working_window(supplier, day, time(9, 0), time(18, 0))
                    self._record(created)

    def _ensure_working_window(self, supplier, day_of_week, start_time, end_time):
        from apps.availability.models import ProviderWorkingWindow

        window = ProviderWorkingWindow.objects.filter(
            supplier=supplier,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        ).first()
        if window:
            return window, False
        window = AvailabilityMutationService.add_working_window(
            supplier=supplier,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        )
        return window, True

    def _ensure_blocked_period(self, supplier):
        from apps.availability.models import AvailabilityBlockedPeriod

        now = timezone.now()
        existing = AvailabilityBlockedPeriod.objects.filter(
            supplier=supplier,
            reason=BlockedPeriodReason.MANUAL_BLOCK,
        ).first()
        if existing:
            self._record(False)
            return
        AvailabilityMutationService.add_blocked_period(
            supplier=supplier,
            start_at=now,
            end_at=now + timedelta(days=30),
            reason=BlockedPeriodReason.MANUAL_BLOCK,
            notes="نمایشی — عدم دسترسی",
        )
        self._record(True)

    # ------------------------------------------------------------------
    # H. Execution, invoicing, settlement
    # ------------------------------------------------------------------

    def _drive_execution(self, order):
        from apps.booking.models import SupplierAssignment

        supplier_assignment = SupplierAssignment.objects.filter(order=order).order_by("-created_at").first()
        session = ExecutionService.create_session(supplier_assignment=supplier_assignment)
        # changed_by omitted (None): start_session()/complete_session() have
        # no permission gate at all (verified during research); close_session()
        # IS gated on EXECUTION_SESSION_CLOSE, but its signature only accepts
        # a single actor param (no ownership_authorized_by) — passing None
        # there is the documented true-system-context path, not a bypass
        # hack, matching every other seed command's convention in this repo.
        ExecutionService.start_session(session_id=session.id)
        return session

    def _ensure_execution_and_finance(self, orders, platform_admin):
        # Re-fetch rather than trust the in-memory object: _ensure_assignments()
        # mutates this order's database row (NEW -> WAITING_SERVICE) via
        # AssignmentService.assign(), but never refreshes the Python object
        # held in `orders` — checking the stale in-memory status here would
        # silently skip creating this order's ExecutionSession on the very
        # first run (only "catching up" a run later, one command execution
        # too late for the primary use case: run once, inspect immediately).
        in_progress_order = Order.objects.get(id=orders["in_progress"].id)
        if in_progress_order.status == OrderStatus.WAITING_SERVICE:
            self._drive_execution(in_progress_order)
            self._record(True)
        else:
            self._record(False)

        finance_created = False
        for key in ("completed_1", "completed_2"):
            order = orders[key]
            order.refresh_from_db()
            if order.status == OrderStatus.COMPLETED:
                self._record(False)
                continue
            session = self._drive_execution(order)
            ExecutionService.complete_session(session_id=session.id)
            session = ExecutionService.close_session(session_id=session.id)
            self._record(True)

            if key == "completed_1":
                try:
                    document = FinancialDocumentService.create_invoice_from_execution(
                        execution_session_id=session.id,
                        items=[
                            {
                                "item_type": "SERVICE",
                                "description": "خدمات مراقبتی نمایشی",
                                "quantity": 1,
                                "unit_price": "1500000",
                            }
                        ],
                        issued_by=platform_admin,
                    )
                    order.refresh_from_db()
                    customer_profile = order.customer_profile
                    payer_party = FinancialPartyService.resolve_party_for_customer(customer_profile)
                    intent = PaymentIntentService.create_intent(
                        payer_party=payer_party,
                        amount=document.total_amount,
                        idempotency_key=f"walkthrough-settlement-{order.id}",
                        reference_type="Order",
                        reference_id=order.id,
                    )
                    attempt = PaymentIntentService.start_attempt(intent_id=intent.id)
                    PaymentCallbackService.process_callback(
                        provider_reference=attempt.provider_reference,
                        payload={
                            "provider_reference": attempt.provider_reference,
                            "provider_event_id": f"evt-walkthrough-{uuid.uuid4().hex[:12]}",
                            "status": "SUCCEEDED",
                            "amount": str(intent.amount),
                            "currency": intent.currency,
                        },
                    )
                    finance_created = True
                    self._record(True)
                except Exception:  # noqa: BLE001 - report, don't crash the whole walkthrough
                    self.stderr.write(
                        self.style.WARNING(
                            "Finance walkthrough chain failed for completed_1 — skipping, reporting as a known limitation."
                        )
                    )
                    self._record("failed")

        return finance_created

    # ------------------------------------------------------------------
    # H. Reviews
    # ------------------------------------------------------------------

    def _ensure_reviews(self, orders):
        order = orders["completed_1"]
        order.refresh_from_db()
        if order.status != OrderStatus.COMPLETED or order.assigned_supplier_id is None:
            self._record("skipped")
            return
        from apps.reviews.models import Review

        if Review.objects.filter(order=order, supplier_id=order.assigned_supplier_id).exists():
            self._record(False)
            return
        try:
            ReviewSubmissionService.submit_review(
                order=order,
                reviewer_person_id=order.customer_profile.person_id,
                dimension_scores={"QUALITY": 5, "PUNCTUALITY": 4, "PROFESSIONALISM": 5, "COMMUNICATION": 4},
                written_text="تجربه بسیار خوبی بود — نمایشی.",
            )
            self._record(True)
        except Exception:  # noqa: BLE001
            self.stderr.write(self.style.WARNING("Review seeding failed — skipping, reporting as a known limitation."))
            self._record("failed")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _route(self, name):
        try:
            return reverse(name)
        except NoReverseMatch:
            return "(route not found)"

    def _route_kw(self, name, **kwargs):
        try:
            return reverse(name, kwargs=kwargs)
        except NoReverseMatch:
            return "(route not found)"

    def _print_report(
        self,
        tenant,
        customers,
        independent_providers,
        organizations,
        affiliated_providers,
        platform_admin,
        orders,
        finance_ok,
    ):
        w = self.stdout.write
        w("")
        w(self.style.SUCCESS("=== Product Walkthrough Seed Complete ==="))
        w(f"Tenant: {tenant.name} ({tenant.slug}) — id={tenant.id}")
        w("")
        w(f"--- Walkthrough accounts (development-only password for ALL accounts: {DEMO_PASSWORD}) ---")
        w(f"{'Role':<28} {'Name':<22} {'Email':<32} {'Landing URL':<28} Notes")
        rows = [
            (
                "Primary customer",
                customers[0][0].person.full_name,
                customers[0][0].email,
                self._route(ROUTE_NAMES["customer_workspace"]),
                "care recipients: " + self._route(ROUTE_NAMES["care_recipients"]),
            ),
            (
                "Independent provider",
                independent_providers[0]["user"].person.full_name,
                independent_providers[0]["user"].email,
                self._route(ROUTE_NAMES["provider_dashboard"]),
                "earnings: " + self._route(ROUTE_NAMES["provider_earnings"]),
            ),
            (
                "Org-affiliated provider",
                affiliated_providers[0]["user"].person.full_name,
                affiliated_providers[0]["user"].email,
                self._route(ROUTE_NAMES["provider_dashboard"]),
                f"org: {affiliated_providers[0]['organization'].name}",
            ),
            (
                "Organization admin",
                organizations[0]["admin_user"].person.full_name,
                organizations[0]["admin_user"].email,
                self._route(ROUTE_NAMES["organization_dashboard"]),
                "staff: " + self._route(ROUTE_NAMES["organization_staff"]),
            ),
            (
                "Platform admin",
                platform_admin.person.full_name,
                platform_admin.email,
                "/admin/",
                "Django admin (staff/superuser)",
            ),
        ]
        for role, name, email, url, notes in rows:
            w(f"{role:<28} {name:<22} {email:<32} {url:<28} {notes}")
        w("")
        provider_supplier_id = independent_providers[0]["supplier"].id
        organization_supplier = get_or_create_supplier_for_organization(organizations[0]["org"], tenant_id=tenant.id)
        w(
            "NOTE (route discovery): the customer/provider/organization portals use phone+OTP login "
            f"({self._route(ROUTE_NAMES['login'])}), not email+password — OTP delivery is console-only in "
            "this environment. The demo password above is set on every account and works for Django admin "
            "(/admin/) sign-in for staff/superuser accounts; it does not, by itself, log into the customer/"
            "provider/organization portals, since those never authenticate via email+password. Provider and "
            "organization self-profile pages exist as distinct URLs (added in Epic 06 Sprint 2): "
            f"provider self-profile {self._route(ROUTE_NAMES['provider_profile'])}, provider profile editing "
            f"{self._route(ROUTE_NAMES['provider_profile_edit'])}, provider public preview "
            f"{self._route_kw('public_site:caregiver-profile', supplier_id=provider_supplier_id)}, organization "
            f"self-profile {self._route(ROUTE_NAMES['organization_profile'])}, organization profile editing "
            f"{self._route(ROUTE_NAMES['organization_profile_edit'])}, organization public preview "
            f"{self._route_kw('public_site:organization-profile', supplier_id=organization_supplier.id)}. "
            'No customer "profile" page exists as a distinct URL in this codebase (confirmed by inspecting '
            "apps/portal/urls.py) — reported here rather than inventing one."
        )
        w("")
        w("--- Dataset ---")
        w(f"Tenant ID: {tenant.id} (slug: {tenant.slug})")
        org_labels = ", ".join(f"{o['org'].name} ({o['org'].id})" for o in organizations)
        w(f"Organizations: {org_labels}")
        w(f"Primary customer ID: {customers[0][1].id}")
        w(f"Sample order IDs: {', '.join(str(o.id) for o in list(orders.values())[:5])} ...")
        w(f"Sample provider IDs: {', '.join(str(p['supplier'].id) for p in independent_providers[:3])} ...")
        w(f"Financial walkthrough records created: {finance_ok}")
        w("")
        w("--- Route inventory (derived from config/urls.py, never guessed) ---")
        for label, name in ROUTE_NAMES.items():
            w(f"  {label:<24} {self._route(name)}")
        w(f"  {'django_admin':<24} /admin/")
        w("")
        w("--- Counts ---")
        w(
            f"created={self.stats['created']} updated={self.stats['updated']} "
            f"already_correct={self.stats['already_correct']} skipped={self.stats['skipped']} "
            f"failed={self.stats['failed']}"
        )
