"""Seed demo orders using existing demo people. Idempotent."""

from django.core.management.base import BaseCommand

from apps.accounts.models import CaregiverProfile, CustomerProfile
from apps.orders.models import Order, ServiceCategory
from apps.orders.services import create_operator_order, create_public_order

DEMO_MARKER = "DEMO_SEED"


class Command(BaseCommand):
    help = "Seed demo orders (idempotent, requires seed_service_catalog + seed_demo_people first)."

    def handle(self, *args, **options):
        if Order.objects.filter(internal_note=DEMO_MARKER).exists():
            self.stdout.write(self.style.WARNING("Demo orders already exist."))
            return

        category = ServiceCategory.objects.filter(status="active").first()
        if not category:
            self.stdout.write(self.style.ERROR("No active service category. Run seed_service_catalog first."))
            return

        customer = CustomerProfile.objects.first()
        caregiver = CaregiverProfile.objects.first()

        # Public order
        order1 = create_public_order(
            service_category_id=category.id,
            description="نیاز به مراقب برای پدربزرگ ۸۰ ساله — سفارش نمایشی",
            phone="09121111111",
            address="تهران، خیابان ولیعصر",
            city="tehran",
            customer_profile=customer,
        )
        order1.internal_note = DEMO_MARKER
        order1.save(update_fields=["internal_note"])

        # Operator order without provider
        order2 = create_operator_order(
            service_category_id=category.id,
            description="درخواست تلفنی — مراقبت شبانه — سفارش نمایشی",
            phone="09122222222",
            address="تهران، سعادت‌آباد",
            city="tehran",
        )
        order2.internal_note = DEMO_MARKER
        order2.save(update_fields=["internal_note"])

        # Operator order with provider
        if caregiver:
            order3 = create_operator_order(
                service_category_id=category.id,
                description="مراقبت فوری — ارائه‌دهنده تخصیص شده — سفارش نمایشی",
                phone="09133333333",
                address="تهران، شهرک غرب",
                city="tehran",
                assigned_provider=caregiver,
            )
            order3.internal_note = DEMO_MARKER
            order3.save(update_fields=["internal_note"])

        self.stdout.write(self.style.SUCCESS("Demo orders seeded."))
