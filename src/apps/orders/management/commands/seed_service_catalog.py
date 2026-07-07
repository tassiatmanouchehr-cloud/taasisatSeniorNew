"""Seed initial senior-care service catalog. Idempotent."""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.orders.models import ServiceCategory, ServiceType

CATALOG = [
    {
        "name": "مراقبت روزانه سالمند",
        "slug": "daily-care",
        "icon": "🏠",
        "types": [
            {"name": "مراقبت ساعتی", "slug": "hourly-care", "duration": 120},
            {"name": "مراقبت نیمه‌وقت", "slug": "half-day-care", "duration": 360},
            {"name": "مراقبت تمام‌وقت", "slug": "full-day-care", "duration": 720},
        ],
    },
    {
        "name": "پرستاری در منزل",
        "slug": "home-nursing",
        "icon": "👩‍⚕️",
        "types": [
            {"name": "پرستاری عمومی", "slug": "general-nursing", "duration": 180},
            {"name": "مراقبت پس از عمل", "slug": "post-surgery-care", "duration": 240},
            {"name": "تزریقات و پانسمان", "slug": "injections", "duration": 60},
        ],
    },
    {
        "name": "همراهی و مراقبت شبانه",
        "slug": "night-care",
        "icon": "🌙",
        "types": [
            {"name": "مراقبت شبانه", "slug": "night-shift", "duration": 480},
            {"name": "همراهی شبانه‌روزی", "slug": "24h-companion", "duration": 1440},
        ],
    },
    {
        "name": "فیزیوتراپی و توانبخشی",
        "slug": "physiotherapy",
        "icon": "🏋️",
        "types": [
            {"name": "فیزیوتراپی در منزل", "slug": "home-physio", "duration": 60},
            {"name": "توانبخشی حرکتی", "slug": "movement-rehab", "duration": 90},
        ],
    },
    {
        "name": "خدمات پزشکی در منزل",
        "slug": "medical-home",
        "icon": "🩺",
        "types": [
            {"name": "ویزیت پزشک عمومی", "slug": "gp-visit", "duration": 30},
            {"name": "نمونه‌گیری آزمایش", "slug": "lab-sampling", "duration": 30},
        ],
    },
    {
        "name": "کمک در امور روزمره",
        "slug": "daily-assistance",
        "icon": "🤝",
        "types": [
            {"name": "همراهی بیرون از منزل", "slug": "outdoor-companion", "duration": 180},
            {"name": "خرید و تهیه مایحتاج", "slug": "shopping-help", "duration": 120},
            {"name": "کمک در نظافت و آشپزی", "slug": "household-help", "duration": 180},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the senior-care service catalog (idempotent)."

    def handle(self, *args, **options):
        created_cats = 0
        created_types = 0

        for i, cat_data in enumerate(CATALOG):
            cat, cat_created = ServiceCategory.objects.get_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "icon": cat_data.get("icon", ""),
                    "sort_order": i * 10,
                },
            )
            if cat_created:
                created_cats += 1

            for j, type_data in enumerate(cat_data.get("types", [])):
                _, type_created = ServiceType.objects.get_or_create(
                    category=cat,
                    slug=type_data["slug"],
                    defaults={
                        "name": type_data["name"],
                        "base_duration_minutes": type_data.get("duration"),
                        "sort_order": j * 10,
                    },
                )
                if type_created:
                    created_types += 1

        self.stdout.write(self.style.SUCCESS(
            f"Catalog seeded: {created_cats} categories, {created_types} types created."
        ))
