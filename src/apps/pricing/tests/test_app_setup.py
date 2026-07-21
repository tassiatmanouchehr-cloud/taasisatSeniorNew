"""Sanity tests: app registration, model registration, migration parity."""

from django.apps import apps as django_apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TestCase


class PricingAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.pricing"))

    def test_models_are_registered(self):
        from apps.pricing.models import (
            PricingRule,
            Promotion,
            PromotionCondition,
            PromotionEffect,
            Quote,
            QuoteLine,
        )

        for model in (PricingRule, Promotion, PromotionCondition, PromotionEffect, Quote, QuoteLine):
            self.assertEqual(model._meta.app_label, "pricing")

    def test_services_import_cleanly(self):
        from apps.pricing.services import (  # noqa: F401
            PricingConfiguration,
            PricingError,
            PricingRuleService,
            PromotionService,
            QuoteService,
        )

    def test_no_missing_migrations_for_pricing(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(django_apps),
        )
        changes = autodetector.changes(graph=loader.graph)
        self.assertNotIn(
            "pricing",
            changes,
            f"Missing migrations detected for apps.pricing: {changes.get('pricing')}",
        )
