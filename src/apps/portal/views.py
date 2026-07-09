"""
Customer portal views — Customer Experience Phase 1.

Every view: authenticate -> resolve the caller's own CustomerProfile ->
call exactly one existing service method -> render a template. Mirrors
apps.admin_portal's thin-controller shape (Module 19) and reuses every
domain service listed in the module's own architecture review — no
business logic lives here.
"""

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.services.care_recipients import CareRecipientService
from apps.accounts.services.errors import AccountsError
from apps.finance.services.party_service import FinancialPartyService
from apps.notifications.models import Notification
from apps.orders.models import CatalogStatus, Order, OrderStatus, ServiceCategory, ServiceType
from apps.orders.services.order_creation import OrderValidationError, create_public_order
from apps.orders.services.share_links import OrderShareLinkError, OrderShareLinkService
from apps.pricing.services.errors import PricingError
from apps.pricing.services.quote_service import QuoteService
from apps.wallet.services.wallet_service import WalletService

from .forms import (
    CareRecipientForm,
    WizardChooseAddressForm,
    WizardChooseCareRecipientForm,
    WizardChooseScheduleForm,
    WizardChooseServiceForm,
    WizardNotesForm,
)
from .permissions import require_authenticated, resolve_customer_profile, resolve_tenant_id

WIZARD_SESSION_KEY = "portal_request_wizard"
RECENT_ORDERS_LIMIT = 5
RECENT_NOTIFICATIONS_LIMIT = 5


def _guard(request):
    """require_authenticated + resolve_tenant_id + resolve_customer_profile, the
    shape every portal view (except the public share view) starts with."""
    require_authenticated(request)
    tenant_id = resolve_tenant_id(request)
    customer = resolve_customer_profile(request)
    return customer, tenant_id


# ============================================================
# Dashboard — Phase 3
# ============================================================

@require_http_methods(["GET"])
def dashboard_view(request):
    """GET /portal/ — My Requests, Care Recipients, Wallet Summary, Recent
    Activity, Notifications, Quick Actions."""
    customer, tenant_id = _guard(request)

    recent_orders = Order.objects.for_tenant(tenant_id).filter(
        customer_profile=customer,
    ).order_by("-created_at")[:RECENT_ORDERS_LIMIT]

    care_recipients = CareRecipientService.list_for_customer(customer)

    party = FinancialPartyService.resolve_party_for_customer(customer)
    wallet = WalletService.get_wallet_or_none(party=party)

    recent_notifications = Notification.objects.for_tenant(tenant_id).filter(
        recipient=customer.person_id,
    ).order_by("-created_at")[:RECENT_NOTIFICATIONS_LIMIT]

    unread_notification_count = Notification.objects.for_tenant(tenant_id).filter(
        recipient=customer.person_id, status="PENDING",
    ).count()

    context = {
        "customer": customer,
        "recent_orders": recent_orders,
        "care_recipients": care_recipients,
        "wallet": wallet,
        "recent_notifications": recent_notifications,
        "unread_notification_count": unread_notification_count,
    }
    return render(request, "portal/dashboard.html", context)


# ============================================================
# Care Recipients — Phase 2 UI
# ============================================================

@require_http_methods(["GET"])
def care_recipients_list_view(request):
    customer, tenant_id = _guard(request)
    care_recipients = CareRecipientService.list_for_customer(customer)
    return render(request, "portal/care_recipients_list.html", {"care_recipients": care_recipients})


@require_http_methods(["GET", "POST"])
def care_recipient_create_view(request):
    customer, tenant_id = _guard(request)

    if request.method == "POST":
        form = CareRecipientForm(request.POST)
        if form.is_valid():
            data = {k: v for k, v in form.cleaned_data.items() if k != "full_name" and v not in (None, "")}
            try:
                CareRecipientService.create(
                    customer_profile=customer, full_name=form.cleaned_data["full_name"], **data,
                )
                return redirect("portal:care-recipients")
            except AccountsError as exc:
                form.add_error(None, str(exc))
    else:
        form = CareRecipientForm()

    return render(request, "portal/care_recipient_form.html", {"form": form, "is_new": True})


@require_http_methods(["GET", "POST"])
def care_recipient_edit_view(request, care_recipient_id):
    customer, tenant_id = _guard(request)

    try:
        care_recipient = CareRecipientService.get_for_customer(customer, care_recipient_id)
    except AccountsError:
        raise PermissionDenied("Care recipient not found.")

    if request.method == "POST":
        form = CareRecipientForm(request.POST)
        if form.is_valid():
            data = {k: v for k, v in form.cleaned_data.items() if v not in (None, "")}
            try:
                CareRecipientService.update(care_recipient, **data)
                return redirect("portal:care-recipients")
            except AccountsError as exc:
                form.add_error(None, str(exc))
    else:
        initial = {
            field: getattr(care_recipient, field)
            for field in CareRecipientForm.base_fields
            if hasattr(care_recipient, field)
        }
        form = CareRecipientForm(initial=initial)

    return render(request, "portal/care_recipient_form.html", {
        "form": form, "is_new": False, "care_recipient": care_recipient,
    })


# ============================================================
# My Requests + Order Timeline — Phase 5
# ============================================================

TIMELINE_STEPS = [
    ("created", "ثبت درخواست"),
    ("matching", "در حال یافتن ارائه‌دهنده"),
    ("accepted", "تخصیص ارائه‌دهنده"),
    ("scheduled", "زمان‌بندی شده"),
    ("started", "شروع خدمت"),
    ("completed", "پایان خدمت"),
]


def _timeline_for_order(order):
    """Read-only presentation over OrderStatusHistory + existing Order state —
    no new persisted state, no new status values. Maps the existing
    OrderStatus machine onto the customer-facing timeline steps."""
    history = list(order.status_history.order_by("created_at"))

    reached = {"created"}
    if order.status in (OrderStatus.NEW, OrderStatus.WAITING_SERVICE, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED):
        reached.add("matching")
    if order.assigned_supplier_id:
        reached.add("accepted")
    if order.scheduled_for or order.requested_date:
        reached.add("scheduled")
    if order.started_at:
        reached.add("started")
    if order.completed_at:
        reached.add("completed")

    cancelled = order.status == OrderStatus.CANCELLED
    timeline = [
        {"key": key, "label": label, "reached": key in reached}
        for key, label in TIMELINE_STEPS
    ]
    return {"steps": timeline, "history": history, "cancelled": cancelled}


@require_http_methods(["GET"])
def requests_list_view(request):
    customer, tenant_id = _guard(request)
    orders = Order.objects.for_tenant(tenant_id).filter(customer_profile=customer).order_by("-created_at")
    return render(request, "portal/requests_list.html", {"orders": orders})


@require_http_methods(["GET"])
def request_detail_view(request, order_id):
    customer, tenant_id = _guard(request)
    order = get_object_or_404(Order.objects.for_tenant(tenant_id), id=order_id, customer_profile=customer)
    timeline = _timeline_for_order(order)
    share_links = OrderShareLinkService.list_for_order(order)
    return render(request, "portal/request_detail.html", {
        "order": order, "timeline": timeline, "share_links": share_links,
    })


# ============================================================
# Service Request Wizard — Phase 4
# ============================================================

def _wizard_data(request) -> dict:
    return request.session.setdefault(WIZARD_SESSION_KEY, {})


def _save_wizard_data(request, data):
    request.session[WIZARD_SESSION_KEY] = data
    request.session.modified = True


def _clear_wizard_data(request):
    request.session.pop(WIZARD_SESSION_KEY, None)


@require_http_methods(["GET", "POST"])
def wizard_care_recipient_view(request):
    customer, tenant_id = _guard(request)
    care_recipients = CareRecipientService.list_for_customer(customer)

    if request.method == "POST":
        form = WizardChooseCareRecipientForm(request.POST)
        if form.is_valid():
            care_recipient_id = str(form.cleaned_data["care_recipient_id"])
            if not care_recipients.filter(id=care_recipient_id).exists():
                form.add_error(None, "گیرنده خدمت انتخاب‌شده معتبر نیست.")
            else:
                data = _wizard_data(request)
                data["care_recipient_id"] = care_recipient_id
                _save_wizard_data(request, data)
                return redirect("portal:request-wizard-service")
    else:
        form = WizardChooseCareRecipientForm()

    return render(request, "portal/wizard_care_recipient.html", {
        "form": form, "care_recipients": care_recipients, "step": 1,
    })


@require_http_methods(["GET", "POST"])
def wizard_service_view(request):
    customer, tenant_id = _guard(request)
    if "care_recipient_id" not in _wizard_data(request):
        return redirect("portal:request-wizard-care-recipient")

    categories = ServiceCategory.objects.for_tenant(tenant_id).filter(status=CatalogStatus.ACTIVE)

    if request.method == "POST":
        form = WizardChooseServiceForm(request.POST)
        if form.is_valid():
            category_id = str(form.cleaned_data["service_category_id"])
            if not categories.filter(id=category_id).exists():
                form.add_error(None, "دسته خدمت انتخاب‌شده معتبر نیست.")
            else:
                data = _wizard_data(request)
                data["service_category_id"] = category_id
                service_type_id = form.cleaned_data.get("service_type_id")
                data["service_type_id"] = str(service_type_id) if service_type_id else None
                _save_wizard_data(request, data)
                return redirect("portal:request-wizard-schedule")
    else:
        form = WizardChooseServiceForm()

    types_by_category = {
        str(c.id): [
            {"id": str(t.id), "name": t.name}
            for t in ServiceType.objects.for_tenant(tenant_id).filter(category=c, status=CatalogStatus.ACTIVE)
        ]
        for c in categories
    }
    return render(request, "portal/wizard_service.html", {
        "form": form, "categories": categories, "types_by_category": types_by_category, "step": 2,
    })


@require_http_methods(["GET", "POST"])
def wizard_schedule_view(request):
    _guard(request)
    if "service_category_id" not in _wizard_data(request):
        return redirect("portal:request-wizard-service")

    if request.method == "POST":
        form = WizardChooseScheduleForm(request.POST)
        if form.is_valid():
            data = _wizard_data(request)
            data["requested_date"] = str(form.cleaned_data["requested_date"] or "")
            data["requested_time_window"] = form.cleaned_data["requested_time_window"]
            _save_wizard_data(request, data)
            return redirect("portal:request-wizard-address")
    else:
        form = WizardChooseScheduleForm()

    return render(request, "portal/wizard_schedule.html", {"form": form, "step": 3})


@require_http_methods(["GET", "POST"])
def wizard_address_view(request):
    customer, tenant_id = _guard(request)
    if "service_category_id" not in _wizard_data(request):
        return redirect("portal:request-wizard-service")

    if request.method == "POST":
        form = WizardChooseAddressForm(request.POST)
        if form.is_valid():
            data = _wizard_data(request)
            data["city"] = form.cleaned_data["city"]
            data["address"] = form.cleaned_data["address"]
            data["phone"] = form.cleaned_data["phone"]
            _save_wizard_data(request, data)
            return redirect("portal:request-wizard-notes")
    else:
        initial = {"phone": customer.phone, "city": customer.city}
        form = WizardChooseAddressForm(initial=initial)

    return render(request, "portal/wizard_address.html", {"form": form, "step": 4})


@require_http_methods(["GET", "POST"])
def wizard_notes_view(request):
    _guard(request)
    if "address" not in _wizard_data(request):
        return redirect("portal:request-wizard-address")

    if request.method == "POST":
        form = WizardNotesForm(request.POST)
        if form.is_valid():
            data = _wizard_data(request)
            data["description"] = form.cleaned_data["description"]
            _save_wizard_data(request, data)
            return redirect("portal:request-wizard-review")
    else:
        form = WizardNotesForm()

    return render(request, "portal/wizard_notes.html", {"form": form, "step": 5})


@require_http_methods(["GET"])
def wizard_review_view(request):
    customer, tenant_id = _guard(request)
    data = _wizard_data(request)
    if "description" not in data:
        return redirect("portal:request-wizard-notes")

    care_recipient = CareRecipientService.get_for_customer(customer, data["care_recipient_id"])
    category = get_object_or_404(ServiceCategory.objects.for_tenant(tenant_id), id=data["service_category_id"])
    service_type = None
    if data.get("service_type_id"):
        service_type = ServiceType.objects.for_tenant(tenant_id).filter(id=data["service_type_id"]).first()

    quote = None
    try:
        quote = QuoteService.generate_quote(
            tenant_id=tenant_id, service_category=category, customer_profile=customer,
        )
    except PricingError:
        quote = None  # Estimate unavailable — review page still works without one.

    return render(request, "portal/wizard_review.html", {
        "care_recipient": care_recipient, "category": category, "service_type": service_type,
        "data": data, "quote": quote, "step": 6,
    })


@require_http_methods(["POST"])
def wizard_submit_view(request):
    customer, tenant_id = _guard(request)
    data = _wizard_data(request)
    if "description" not in data:
        return redirect("portal:request-wizard-notes")

    try:
        care_recipient = CareRecipientService.get_for_customer(customer, data["care_recipient_id"])
        order = create_public_order(
            service_category_id=data["service_category_id"],
            service_type_id=data.get("service_type_id"),
            description=data["description"],
            phone=data["phone"],
            address=data["address"],
            city=data.get("city", ""),
            customer_profile=customer,
            elder_profile=care_recipient,
            requested_date=data.get("requested_date") or None,
            requested_time_window=data.get("requested_time_window", ""),
            created_by=request.user,
            tenant_id=tenant_id,
        )
    except (OrderValidationError, AccountsError) as exc:
        return render(request, "portal/wizard_error.html", {"error": str(exc)})

    _clear_wizard_data(request)
    return redirect("portal:request-detail", order_id=order.id)


# ============================================================
# Order Share Link — Phase 6
# ============================================================

@require_http_methods(["POST"])
def share_link_create_view(request, order_id):
    customer, tenant_id = _guard(request)
    order = get_object_or_404(Order.objects.for_tenant(tenant_id), id=order_id, customer_profile=customer)
    OrderShareLinkService.create(order=order, created_by=request.user)
    return redirect("portal:request-detail", order_id=order.id)


@require_http_methods(["POST"])
def share_link_revoke_view(request, order_id, link_id):
    customer, tenant_id = _guard(request)
    order = get_object_or_404(Order.objects.for_tenant(tenant_id), id=order_id, customer_profile=customer)
    try:
        OrderShareLinkService.revoke(order=order, link_id=link_id)
    except OrderShareLinkError:
        pass  # Already gone/revoked — revoking is idempotent from the caller's perspective.
    return redirect("portal:request-detail", order_id=order.id)


@require_http_methods(["GET"])
def shared_order_view(request, token):
    """Public, unauthenticated, read-only view of exactly one order.

    No require_authenticated(), no resolve_customer_profile() — the token
    itself is the only credential, scoped to exactly one order. Cannot
    reach wallet, payments, profile, notifications, other orders, or the
    dashboard: this view never resolves a CustomerProfile at all, so no
    code path here could touch them even by mistake.
    """
    try:
        order = OrderShareLinkService.resolve(token)
    except OrderShareLinkError as exc:
        return render(request, "portal/shared_order_invalid.html", {"error": str(exc)}, status=404)

    timeline = _timeline_for_order(order)
    return render(request, "portal/shared_order.html", {"order": order, "timeline": timeline})


# ============================================================
# Notification Center — Phase 7
# ============================================================

@require_http_methods(["GET"])
def notifications_view(request):
    customer, tenant_id = _guard(request)
    notifications = Notification.objects.for_tenant(tenant_id).filter(
        recipient=customer.person_id,
    ).order_by("-created_at")

    filter_param = request.GET.get("filter", "all")
    if filter_param == "unread":
        notifications = notifications.filter(status="PENDING")
    elif filter_param == "read":
        notifications = notifications.exclude(status="PENDING")

    return render(request, "portal/notifications.html", {
        "notifications": notifications, "filter": filter_param, "now": timezone.now(),
    })
