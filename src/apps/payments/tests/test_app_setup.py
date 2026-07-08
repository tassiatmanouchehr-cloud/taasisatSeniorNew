"""Sanity tests: app registration, model registration, service imports."""

from django.apps import apps as django_apps
from django.test import TestCase


class PaymentsAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.payments"))

    def test_models_are_registered(self):
        from apps.payments.models import PaymentAttempt, PaymentCallback, PaymentIntent

        self.assertEqual(PaymentIntent._meta.app_label, "payments")
        self.assertEqual(PaymentAttempt._meta.app_label, "payments")
        self.assertEqual(PaymentCallback._meta.app_label, "payments")

    def test_services_import_cleanly(self):
        from apps.payments.services import (  # noqa: F401
            PaymentCallbackService,
            PaymentConfiguration,
            PaymentError,
            PaymentIntentService,
            PaymentProviderRegistry,
            PaymentResult,
        )

    def test_fake_provider_adapter_imports_cleanly(self):
        from apps.payments.providers.fake import FakePaymentProviderAdapter  # noqa: F401
