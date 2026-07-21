"""
End-to-end workflow validation script.
Tests the complete customer journey using existing services.
"""

import os
import sys

import django

os.environ.setdefault("DATABASE_ENGINE", "django.db.backends.postgresql")
os.environ.setdefault("DATABASE_NAME", "marketplace")
os.environ.setdefault("DATABASE_USER", "marketplace")
os.environ.setdefault("DATABASE_PASSWORD", "marketplace")
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("GIS_ENABLED", "false")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")

django.setup()

from decimal import Decimal

from apps.accounts.models import CaregiverProfile, CustomerProfile
from apps.accounts.services.care_recipients import CareRecipientService
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver
from apps.booking.services.assignment_service import AssignmentService
from apps.booking.services.provider_actions import ProviderAssignmentActionService
from apps.execution.services.session_service import ExecutionService
from apps.finance.services.document_service import FinancialDocumentService
from apps.finance.services.party_service import FinancialPartyService
from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount
from apps.orders.models import ServiceCategory
from apps.orders.services.order_creation import create_public_order
from apps.orders.services.status_machine import approve_public_order
from apps.wallet.services.wallet_service import WalletService
from apps.wallet.services.wallet_transaction_service import WalletTransactionService

results = []


def step(name, func):
    try:
        result = func()
        results.append(f"  PASS: {name}")
        return result
    except Exception as e:
        import traceback

        results.append(f"  FAIL: {name} -- {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


print("=" * 60)
print("END-TO-END WORKFLOW VALIDATION")
print("=" * 60)


# Step 1: Get tenant
def get_tenant():
    return Tenant.objects.get(slug="dev")


tenant = step("1. Get tenant", get_tenant)
if not tenant:
    print("\n".join(results))
    sys.exit(1)


# Step 2: Create customer user and profile directly
def create_customer():
    import uuid

    suffix = uuid.uuid4().hex[:8]
    person = Person.objects.create(tenant=tenant, full_name="E2E Customer", status="ACTIVE")
    user = UserAccount.objects.create_user(
        email=f"e2e_customer_{suffix}@test.local",
        phone=f"+98912999{suffix[:4]}",
        password="testpass123",
        tenant=tenant,
        person=person,
    )
    profile = CustomerProfile.objects.create(
        user=user,
        person=person,
        phone=f"+98912999{suffix[:4]}",
        display_name="E2E Customer",
        city="Tehran",
        status="ACTIVE",
    )
    # Grant the customer the necessary permissions for the full workflow
    role, _ = Role.objects.get_or_create(
        tenant=tenant,
        slug="e2e-customer",
        defaults={
            "name": "E2E Customer",
            "permissions": ["booking.assignment.assign", "execution.session.close"],
            "is_system": False,
        },
    )
    RoleAssignment.objects.get_or_create(tenant=tenant, user=user, role=role, defaults={"is_active": True})
    return user, profile


user, customer_profile = step("2. Customer user + profile creation", create_customer) or (None, None)
if not user:
    print("\n".join(results))
    sys.exit(1)


# Step 3: Elder/care-recipient creation
def create_elder():
    return CareRecipientService.create(
        customer_profile=customer_profile,
        full_name="Test Elder",
        gender="FEMALE",
        city="Tehran",
        care_needs="Daily assistance needed",
        mobility_level="NEEDS_ASSISTANCE",
    )


elder = step("3. Elder/care-recipient creation", create_elder)
if not elder:
    print("\n".join(results))
    sys.exit(1)


# Step 4: Create caregiver user and profile directly
def create_caregiver():
    import uuid

    suffix = uuid.uuid4().hex[:8]
    person = Person.objects.create(tenant=tenant, full_name="E2E Caregiver", status="ACTIVE")
    user = UserAccount.objects.create_user(
        email=f"e2e_caregiver_{suffix}@test.local",
        phone=f"+98912998{suffix[:4]}",
        password="testpass123",
        tenant=tenant,
        person=person,
    )
    profile = CaregiverProfile.objects.create(
        user=user,
        person=person,
        phone=f"+98912998{suffix[:4]}",
        display_name="E2E Caregiver",
        city="Tehran",
        specialty="Elder Care",
        status="ACTIVE",
    )
    return user, profile


cg_user, cg_profile = step("4. Caregiver user + profile creation", create_caregiver) or (None, None)
if not cg_user:
    print("\n".join(results))
    sys.exit(1)


# Step 5: ServiceSupplier creation
def create_supplier():
    return get_or_create_supplier_for_caregiver(cg_profile)


supplier = step("5. ServiceSupplier creation", create_supplier)
if not supplier:
    print("\n".join(results))
    sys.exit(1)

# Verify supplier tenant
supplier.refresh_from_db()
if supplier.tenant_id != tenant.id:
    results.append(f"  FAIL: Supplier tenant ({supplier.tenant_id}) != order tenant ({tenant.id})")
    print("\n".join(results))
    sys.exit(1)


# Step 6: Order creation
def create_order():
    cat, _ = ServiceCategory.objects.get_or_create(tenant=tenant, slug="elder-care", defaults={"name": "Elder Care"})
    return create_public_order(
        tenant_id=tenant.id,
        service_category_id=cat.id,
        description="Test order for elder care",
        phone="+989129999901",
        address="123 Test St, Tehran",
        city="Tehran",
        created_by=user,
        customer_profile=customer_profile,
        elder_profile=elder,
    )


order = step("6. Order creation", create_order)
if not order:
    print("\n".join(results))
    sys.exit(1)


# Step 7: Order approval
def approve_order():
    return approve_public_order(order_id=order.id, reviewed_by=user)


order = step("7. Order approval", approve_order)
if not order:
    print("\n".join(results))
    sys.exit(1)


# Step 8: Supplier assignment
def assign_supplier_to_order():
    return AssignmentService.assign(
        order_id=order.id, supplier=supplier, assigned_by=None, ownership_authorized_by=user
    )


assignment = step("8. Supplier assignment", assign_supplier_to_order)
if not assignment:
    print("\n".join(results))
    sys.exit(1)


# Step 9: Provider acceptance
def provider_accept():
    return ProviderAssignmentActionService.confirm(assignment_id=assignment.id, actor=cg_user)


assignment = step("9. Provider accept", provider_accept)
if not assignment:
    print("\n".join(results))
    sys.exit(1)


# Step 10: Start execution session
def start_execution():
    session = ExecutionService.create_session(supplier_assignment=assignment)
    ExecutionService.start_session(session_id=session.id, changed_by=cg_user)
    return session


session = step("10. Service execution start", start_execution)
if not session:
    print("\n".join(results))
    sys.exit(1)


# Step 11: Complete execution session
def complete_execution():
    return ExecutionService.complete_session(session_id=session.id, changed_by=cg_user)


session = step("11. Execution complete (provider)", complete_execution)
if not session:
    print("\n".join(results))
    sys.exit(1)


# Step 12: Close execution session
def close_execution():
    return ExecutionService.close_session(session_id=session.id, changed_by=user)


session = step("12. Execution close (customer)", close_execution)
if not session:
    print("\n".join(results))
    sys.exit(1)


# Step 13: Financial party resolution
def resolve_financial_party():
    return FinancialPartyService.resolve_party_for_supplier(supplier)


party = step("13. Financial party resolution", resolve_financial_party)
if not party:
    print("\n".join(results))
    sys.exit(1)


# Step 14: Invoice creation
def create_invoice():
    return FinancialDocumentService.create_invoice_from_execution(
        execution_session_id=session.id,
        items=[
            {
                "item_type": "SERVICE",
                "description": "Elder care service",
                "quantity": Decimal("1"),
                "unit_price": Decimal("500000"),
                "total_amount": Decimal("500000"),
            }
        ],
        issued_by=user,
    )


invoice = step("14. Invoice creation", create_invoice)
if not invoice:
    print("\n".join(results))
    sys.exit(1)


# Step 15: Wallet setup
def setup_wallet():
    return WalletService.create_wallet(party=party)


wallet = step("15. Wallet creation", setup_wallet)
if not wallet:
    print("\n".join(results))
    sys.exit(1)


# Step 16: Wallet credit
def credit_wallet():
    return WalletTransactionService.credit(wallet_id=wallet.id, amount=Decimal("500000"), reason="E2E test payment")


tx = step("16. Wallet credit", credit_wallet)
if not tx:
    print("\n".join(results))
    sys.exit(1)


# Step 17: Check wallet balance
def check_balance():
    return WalletService.get_balance(wallet)


balance = step("17. Wallet balance check", check_balance)
if balance:
    results.append(f"       Balance: {balance} IRR")


# Step 18: Order final status
def check_order_status():
    order.refresh_from_db()
    return order.status


status = step("18. Order final status", check_order_status)
if status:
    results.append(f"       Status: {status}")

# Summary
print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print("\n".join(results))

passed = sum(1 for r in results if r.startswith("  PASS"))
failed = sum(1 for r in results if r.startswith("  FAIL"))
print(f"\nTotal: {passed + failed} steps, {passed} passed, {failed} failed")
