"""Sanity tests: app registration, model registration, service imports."""

from django.apps import apps as django_apps
from django.test import TestCase


class ReviewsAppSetupTest(TestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.reviews"))

    def test_models_are_registered(self):
        from apps.reviews.models import ReputationSnapshot, Review, ReviewRating

        self.assertEqual(Review._meta.app_label, "reviews")
        self.assertEqual(ReviewRating._meta.app_label, "reviews")
        self.assertEqual(ReputationSnapshot._meta.app_label, "reviews")

    def test_services_import_cleanly(self):
        from apps.reviews.services import (  # noqa: F401
            ReputationService,
            ReviewError,
            ReviewModerationService,
            ReviewSubmissionService,
        )
